import discord
import os
from discord import ui
from src.database.session import db_session
from src.database.models import GenerationJob
from src.core.logger import setup_logger

logger = setup_logger(__name__)

class GenerationView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def _get_job_id(self, interaction: discord.Interaction):
        # 1. Try to get from custom_id (Preferred)
        custom_id = interaction.data.get("custom_id", "")
        job_id = None
        if "link_chain_" in custom_id:
            job_id = custom_id.split("|")[-1]
        elif "_" in custom_id:
            job_id = custom_id.split("_")[-1]
            
        if job_id and len(job_id) >= 32:
            return job_id
                
        # 2. Fallback to footer
        if not interaction.message or not interaction.message.embeds:
            return None
        footer = interaction.message.embeds[0].footer
        if footer and footer.text and "Job ID: " in footer.text:
            return footer.text.split("Job ID: ")[1].strip()
        return None

    @discord.ui.button(label="Regenerate", style=discord.ButtonStyle.primary, custom_id="link_gen_redo")
    async def regenerate(self, interaction: discord.Interaction, button: discord.ui.Button):
        # We now handle this globally in handle_smart_action to prevent double-processing
        pass

    @discord.ui.button(label="Options", style=discord.ButtonStyle.secondary, custom_id="link_gen_options")
    async def options(self, interaction: discord.Interaction, button: discord.ui.Button):
        # We now handle this globally in handle_smart_action to prevent double-processing
        pass

    @discord.ui.button(label="Delete", style=discord.ButtonStyle.danger, custom_id="link_gen_delete")
    async def delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        # We now handle this globally in handle_smart_action
        pass

async def handle_smart_action(interaction: discord.Interaction):
    """Global listener for smart actions (buttons from ui_config)."""
    if interaction.response.is_done():
        return

    if not interaction.type == discord.InteractionType.component:
        # Log to see if we're accidentally seeing slash commands here
        if interaction.type == discord.InteractionType.application_command:
            logger.debug(f"handle_smart_action ignoring slash command: {interaction.data.get('name')}")
        return
        
    custom_id = interaction.data.get("custom_id", "")
    if not custom_id.startswith("link_"):
        return
    
    # Get Job ID
    job_id = None
    if "link_chain_" in custom_id:
        job_id = custom_id.split("|")[-1]
    elif "_" in custom_id:
        job_id = custom_id.split("_")[-1]
    
    # Validate job_id looks like a UUID (at least 32 chars)
    if job_id and len(job_id) < 32:
        job_id = None
    
    if not job_id and interaction.message and interaction.message.embeds:
        footer = interaction.message.embeds[0].footer
        if footer and footer.text and "Job ID: " in footer.text:
            footer_text = footer.text
            if "Job ID: " in footer_text:
                job_id = footer_text.split("Job ID: ")[1].strip()
            
    if not job_id:
        # Fallback for legacy delete if no job ID is found
        if custom_id.startswith("link_gen_delete"):
            try:
                if not interaction.response.is_done():
                    await interaction.response.defer(ephemeral=True)
                return await interaction.message.delete()
            except Exception as e:
                if "Unknown Message" not in str(e):
                    logger.warning(f"Global legacy delete failed: {e}")
                return
        # If it's a regenerate/options button, it might be handled by the View class if custom_id was static
        # But we want to handle everything here for consistency if Job ID is missing.
        if "link_gen_" in custom_id: return
        return await interaction.response.send_message("❌ Could not find Job ID for this action. (Footer might be disabled)", ephemeral=True)
    
    try:
        job = None
        with db_session() as db:
            job = db.query(GenerationJob).filter(GenerationJob.id == job_id).first()
            if job:
                db.expunge(job)

        if not job:
            # Fallback for delete if the job is missing from DB but the message exists
            if custom_id.startswith("link_gen_delete"):
                try:
                    if not interaction.response.is_done():
                        await interaction.response.defer(ephemeral=True)
                    return await interaction.message.delete()
                except Exception as e:
                    if "Unknown Message" not in str(e):
                        logger.warning(f"Global delete failed for missing job: {e}")
                    return
            return await interaction.response.send_message("❌ Could not find original job data.", ephemeral=True)

        # Handle delete action (restricted to original generator or server admin)
        if custom_id.startswith("link_gen_delete"):
            is_owner = (job.user_id and str(interaction.user.id) == job.user_id)
            is_admin = False
            if interaction.guild and interaction.user.guild_permissions.administrator:
                is_admin = True
                
            if not (is_owner or is_admin):
                return await interaction.response.send_message("❌ Only the original generator or a server administrator can delete this.", ephemeral=True)

            try:
                if not interaction.response.is_done():
                    await interaction.response.defer(ephemeral=True)
                return await interaction.message.delete()
            except Exception as e:
                if "Unknown Message" not in str(e):
                    logger.warning(f"Global delete failed: {e}")
                return

        if custom_id.startswith("link_chain_"):
            raw_target = custom_id.replace("link_chain_", "")
            target_wf = raw_target.split("|")[0]
            await _execute_chain(interaction, job, target_wf)
        elif custom_id.startswith("link_selector_"):
            # New handler for curated selector
            wf_config = interaction.client.workflow_registry.get_workflow(job.workflow_name)
            manifest = wf_config.get("manifest", {})
            ui_cfg = manifest.get("discord", {}).get("ui") or manifest.get("ui", {})
            
            target_workflows = []
            for btn in ui_cfg.get("buttons", []):
                if btn.get("type") == "selector":
                    target_workflows = btn.get("target_workflows", [])
                    break
            
            if not target_workflows:
                return await interaction.response.send_message("❌ No target workflows configured for this selector.", ephemeral=True)

            from src.bot.ui import ChainSelectView
            
            async def on_select(sel_interaction, target_wf_name, original_job_id):
                # Use the original interaction's message for attachments
                original_msg = interaction.message
                # We need to re-fetch the job in the callback to ensure DB session is fresh
                _job = None
                with db_session() as _db:
                    _job = _db.query(GenerationJob).filter(GenerationJob.id == original_job_id).first()
                    if _job:
                        _db.expunge(_job)
                if _job:
                    await _execute_chain(sel_interaction, _job, target_wf_name, source_message=original_msg)

            view = ChainSelectView(target_workflows, job.id, on_select, registry=interaction.client.workflow_registry)
            await interaction.response.send_message("Choose a workflow to chain to:", view=view, ephemeral=True)
        elif custom_id.startswith("link_gen_redo"):
            gen_cog = interaction.client.get_cog("GenerationCog")
            if gen_cog:
                await gen_cog.handle_regeneration(interaction, job.id)
        elif custom_id.startswith("link_gen_options"):
            gen_cog = interaction.client.get_cog("GenerationCog")
            if gen_cog:
                await gen_cog.handle_options_request(interaction, job.id)
        else:
            # custom_id format: link_action_{target_wf}_{source_type}_{input_mapping}
            raw = custom_id.replace("link_action_", "")
            parts = raw.split("_", 2)
            if len(parts) < 3: return
            target_wf = parts[0]
            source_type = parts[1]
            input_mapping = parts[2]
            
            # ... (rest of legacy mapping logic)
            mapping_data = {}
            try:
                import json
                mapping_data = json.loads(input_mapping)
            except Exception:
                mapping_data = {input_mapping: "image" if source_type == "image" else source_type}

            prefilled = {}
            for target_field, source_ref in mapping_data.items():
                # (Keeping existing attachment matching logic for legacy support)
                if source_ref in ["image", "video", "audio"]:
                    if interaction.message and interaction.message.attachments:
                        match = None
                        for att in interaction.message.attachments:
                            ctype = (att.content_type or "").lower()
                            if source_ref == "image" and "image" in ctype: match = att
                            elif source_ref == "video" and ("video" in ctype or ctype == "image/gif"): match = att
                            elif source_ref == "audio" and "audio" in ctype: match = att
                        prefilled[target_field] = match.url if match else interaction.message.attachments[0].url
                elif source_ref == "prompt": prefilled[target_field] = job.input_params.get("prompt", "")
                elif source_ref == "seed": prefilled[target_field] = str(job.input_params.get("seed", ""))
                elif source_ref in job.input_params: prefilled[target_field] = job.input_params[source_ref]

            gen_cog = interaction.client.get_cog("GenerationCog")
            if gen_cog:
                await gen_cog.handle_generation_request(
                    interaction, 
                    target_wf, 
                    prefilled=prefilled
                )
            else:
                await interaction.response.send_message("❌ Generation system unavailable.", ephemeral=True)
    except Exception as e:
        logger.error(f"Error in handle_smart_action: {e}", exc_info=True)
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)
            else:
                await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)
        except Exception:
            pass

async def _execute_chain(interaction: discord.Interaction, job: GenerationJob, target_wf: str, source_message: discord.Message = None):
    """Internal helper to execute a chain request from a job result."""
    # Use provided source_message (from original button click) or fallback to current interaction message
    msg_with_attachments = source_message or interaction.message
    
    # Get target workflow manifest to find where to put things
    target_workflow = interaction.client.workflow_registry.get_workflow(target_wf)
    if not target_workflow:
        msg = f"❌ Target workflow '{target_wf}' not found."
        if not interaction.response.is_done():
            return await interaction.response.send_message(msg, ephemeral=True)
        else:
            return await interaction.followup.send(msg, ephemeral=True)
        
    target_manifest = target_workflow.get("manifest", {})
    target_inputs = target_manifest.get("inputs", [])
    
    prefilled = {}
    
    # Auto-detect mapping based on attachment types
    if msg_with_attachments and msg_with_attachments.attachments:
        for att in msg_with_attachments.attachments:
            ctype = (att.content_type or "").lower()
            
            # Filter candidates by type — match both explicit upload types AND name keywords
            candidates = []
            for inp in target_inputs:
                itype = inp.get("type", "")
                iid = inp.get("id", "").lower()
                label = inp.get("label", "").lower()
                
                is_image_field = itype == "image_upload" or (itype not in ["audio_upload","video_upload"] and any(k in iid or k in label for k in ["image","img","photo","picture","frame"]))
                is_video_field = itype == "video_upload" or (itype not in ["image_upload","audio_upload"] and any(k in iid or k in label for k in ["video","clip","film","footage"]))
                is_audio_field = itype == "audio_upload" or (itype not in ["image_upload","video_upload"] and any(k in iid or k in label for k in ["audio","sound","music","voice","track"]))
                
                if "image" in ctype and is_image_field: candidates.append(inp)
                elif ("video" in ctype or ctype == "image/gif") and is_video_field: candidates.append(inp)
                elif "audio" in ctype and is_audio_field: candidates.append(inp)
            
            if not candidates: continue
            
            # Rank candidates to find the "Main" one
            best_score = -1
            best_inp = None
            
            for c in candidates:
                cid = c.get("id", "").lower()
                clabel = c.get("label", "").lower()
                score = 0
                
                if cid in ["image", "video", "audio", "input", "source"]: score += 10
                if any(k in cid or k in clabel for k in ["main", "source", "input", "primary", "base"]): score += 5
                if any(k in cid or k in clabel for k in ["mask", "style", "control", "depth", "pose", "canny"]): score -= 5
                
                if score > best_score:
                    best_score = score
                    best_inp = c
            
            if best_inp and best_inp["id"] not in prefilled:
                local_asset_path = None
                try:
                    from src.database.models import Asset as AssetModel, GenerationJob as GenJob
                    with db_session() as _db:
                        ctype_check = (att.content_type or "").lower()
                        if "image" in ctype_check:
                            mime_like = "image%"
                        elif "video" in ctype_check or ctype_check == "image/gif":
                            mime_like = "video%"
                        elif "audio" in ctype_check:
                            mime_like = "audio%"
                        else:
                            mime_like = None
                        
                        if mime_like:
                            last_local = _db.query(AssetModel).filter(
                                AssetModel.job_id == job.id,
                                AssetModel.file_type.like(mime_like),
                                AssetModel.file_path.notlike("http%")
                            ).order_by(AssetModel.id.desc()).first()
                            if last_local and os.path.isfile(last_local.file_path):
                                local_asset_path = last_local.file_path
                except Exception as _e:
                    logger.warning(f"Could not query local asset from DB: {_e}")
                
                prefilled[best_inp["id"]] = local_asset_path if local_asset_path else att.url
    
    # Also pass prompt and seed if applicable
    for inp in target_inputs:
        iid = inp.get("id", "")
        if iid in prefilled: continue
        if "prompt" in iid.lower(): prefilled[iid] = job.input_params.get("prompt", "")
        if "seed" in iid.lower(): prefilled[iid] = str(job.input_params.get("seed", ""))

    gen_cog = interaction.client.get_cog("GenerationCog")
    if gen_cog:
        await gen_cog.handle_generation_request(interaction, target_wf, prefilled=prefilled)
    else:
        msg = "❌ Generation system unavailable."
        if not interaction.response.is_done():
            await interaction.response.send_message(msg, ephemeral=True)
        else:
            await interaction.followup.send(msg, ephemeral=True)

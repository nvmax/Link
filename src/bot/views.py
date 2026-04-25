import discord
from discord import ui
from src.database.session import SessionLocal
from src.database.models import GenerationJob
from src.core.logger import setup_logger

logger = setup_logger(__name__)

class GenerationView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def _get_job_id(self, interaction: discord.Interaction):
        if not interaction.message or not interaction.message.embeds:
            return None
        footer = interaction.message.embeds[0].footer.text
        if "Job ID: " in footer:
            return footer.split("Job ID: ")[1].strip()
        return None

    @discord.ui.button(label="Regenerate", style=discord.ButtonStyle.primary, custom_id="link_gen_redo")
    async def regenerate(self, interaction: discord.Interaction, button: discord.ui.Button):
        job_id = await self._get_job_id(interaction)
        if not job_id:
            return await interaction.response.send_message("❌ Could not find Job ID in message.", ephemeral=True)

        gen_cog = interaction.client.get_cog("GenerationCog")
        if gen_cog:
            await gen_cog.handle_regeneration(interaction, job_id)
        else:
            await interaction.response.send_message("❌ Generation system not available.", ephemeral=True)

    @discord.ui.button(label="Options", style=discord.ButtonStyle.secondary, custom_id="link_gen_options")
    async def options(self, interaction: discord.Interaction, button: discord.ui.Button):
        job_id = await self._get_job_id(interaction)
        if not job_id:
            return await interaction.response.send_message("❌ Could not find Job ID in message.", ephemeral=True)

        gen_cog = interaction.client.get_cog("GenerationCog")
        if gen_cog:
            await gen_cog.handle_options_request(interaction, job_id)
        else:
            await interaction.response.send_message("❌ Generation system not available.", ephemeral=True)

    @discord.ui.button(label="Delete", style=discord.ButtonStyle.danger, custom_id="link_gen_delete")
    async def delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.message.delete()
        except Exception:
            await interaction.response.send_message("❌ Could not delete message. Bot might lack permissions.", ephemeral=True)

async def handle_smart_action(interaction: discord.Interaction):
    """Global listener for smart actions (buttons from ui_config)."""
    if not interaction.type == discord.InteractionType.component:
        return
        
    custom_id = interaction.data.get("custom_id", "")
    if not (custom_id.startswith("link_action_") or custom_id.startswith("link_chain_")):
        return
        
    # Default values
    target_wf = ""
    # Get Job ID from message
    if not interaction.message or not interaction.message.embeds:
        return
    footer = interaction.message.embeds[0].footer.text
    if "Job ID: " not in footer:
        return
    job_id = footer.split("Job ID: ")[1].strip()
    
    db = SessionLocal()
    try:
        job = db.query(GenerationJob).filter(GenerationJob.id == job_id).first()
        if not job:
            return await interaction.response.send_message("❌ Could not find original job data.", ephemeral=True)

        if custom_id.startswith("link_chain_"):
            raw_target = custom_id.replace("link_chain_", "")
            target_wf = raw_target.split("|")[0]
            
            # Get target workflow manifest to find where to put things
            target_workflow = interaction.client.workflow_registry.get_workflow(target_wf)
            if not target_workflow:
                return await interaction.response.send_message(f"❌ Target workflow '{target_wf}' not found.", ephemeral=True)
                
            target_manifest = target_workflow.get("manifest", {})
            target_inputs = target_manifest.get("inputs", [])
            
            prefilled = {}
            
            # Auto-detect mapping based on attachment types
            if interaction.message and interaction.message.attachments:
                for att in interaction.message.attachments:
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
                    # Score based on keywords
                    best_score = -1
                    best_inp = None
                    
                    for c in candidates:
                        cid = c.get("id", "").lower()
                        clabel = c.get("label", "").lower()
                        score = 0
                        
                        # Exact matches
                        if cid in ["image", "video", "audio", "input", "source"]: score += 10
                        # Primary keywords
                        if any(k in cid or k in clabel for k in ["main", "source", "input", "primary", "base"]): score += 5
                        # Negative keywords (mask, style, control)
                        if any(k in cid or k in clabel for k in ["mask", "style", "control", "depth", "pose", "canny"]): score -= 5
                        
                        if score > best_score:
                            best_score = score
                            best_inp = c
                    
                    if best_inp and best_inp["id"] not in prefilled:
                        prefilled[best_inp["id"]] = att.url
                        logger.info(f"Auto-selected best input '{best_inp['id']}' (score {best_score}) for {ctype}")
            
            # Also pass prompt and seed if applicable
            for inp in target_inputs:
                iid = inp.get("id", "")
                if iid in prefilled: continue
                if "prompt" in iid.lower(): prefilled[iid] = job.input_params.get("prompt", "")
                if "seed" in iid.lower(): prefilled[iid] = str(job.input_params.get("seed", ""))
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
            except:
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
    finally:
        db.close()

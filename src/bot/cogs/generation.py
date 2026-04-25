import discord
from discord import app_commands
from discord.ext import commands
from src.bot.ui import DynamicModal, OptionsView
from src.api.workflows import PayloadBuilder
from src.database.models import GenerationJob, JobStatus
from src.database.session import SessionLocal
from src.core.logger import setup_logger
import uuid
import random
import os
from src.core.config import Config
from src.bot.loras import LoraSelectionView

logger = setup_logger(__name__)

class GenerationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.pending_uploads = {} # {user_id: {workflow_name, values, missing_fields, message_id}}

    @app_commands.command(name="gen", description="Generate an image using a workflow")
    @app_commands.describe(workflow="The name of the workflow to use")
    async def generate(self, interaction: discord.Interaction, workflow: str):
        # The generic /gen command will still trigger the modal flow
        await self.handle_generation_request(interaction, workflow)

    async def handle_generation_request(self, interaction: discord.Interaction, workflow_name: str, user_values: dict = None, prefilled: dict = None):
        """Common entry point for both slash commands and modal submissions."""
        # Channel Lockdown Check
        if Config.ALLOWED_CHANNEL_ID and interaction.channel_id != Config.ALLOWED_CHANNEL_ID:
            allowed_channel = f"<#{Config.ALLOWED_CHANNEL_ID}>"
            msg = f"⛔ This command can only be used in {allowed_channel}."
            if not interaction.response.is_done():
                return await interaction.response.send_message(msg, ephemeral=True)
            else:
                return await interaction.followup.send(msg, ephemeral=True)

        workflow = self.bot.workflow_registry.get_workflow(workflow_name)
        if not workflow:
            msg = f"Workflow {workflow_name} not found."
            if not interaction.response.is_done():
                return await interaction.response.send_message(msg, ephemeral=True)
            else:
                return await interaction.followup.send(msg, ephemeral=True)

        manifest = workflow["manifest"]
        inputs = manifest.get("inputs", [])


        # --- CONTEXT-AWARE AUTO-DETECTION ---
        # If we're missing a required image/audio and no user_values/prefilled provided,
        # or if they are explicitly missing, try to find the last asset.
        if prefilled is None: prefilled = {}
        
        for input_cfg in inputs:
            input_id = input_cfg.get("id")
            input_type = input_cfg.get("type")
            
            # If it's a file upload and not provided, check the database
            if input_type in ["image_upload", "audio_upload"] and input_id not in prefilled and (user_values is None or input_id not in user_values):
                db = SessionLocal()
                try:
                    from src.database.models import Asset, GenerationJob
                    # Find the last asset of this type (image or audio) for this user
                    last_asset = db.query(Asset).join(GenerationJob).filter(
                        GenerationJob.user_id == str(interaction.user.id),
                        Asset.file_type.like("image%" if "image" in input_type else "audio%")
                    ).order_by(Asset.id.desc()).first()
                    
                    if last_asset:
                        prefilled[input_id] = last_asset.file_path
                        logger.info(f"Auto-detected last asset for {input_id}: {last_asset.file_path}")
                finally:
                    db.close()
        
        # Check if there are any modal-compatible fields that aren't already in prefilled
        modal_fields = []
        for input_cfg in inputs:
            fid = input_cfg.get("id")
            itype = input_cfg.get("type")
            if itype not in ["image_upload", "audio_upload", "video_upload", "select"] and "lora" not in fid.lower() and "➕" not in fid:
                # Always show modal fields if they exist to allow user editing,
                # even if prefilled (so they can modify default/prefilled values).
                # But we MUST have at least one valid modal field to show the modal.
                modal_fields.append(input_cfg)
            elif itype == "select":
                # For select fields, only show in modal if NOT already prefilled with a URL
                # (i.e., the value was passed from Discord/chaining, not user selection)
                prefilled_val = prefilled.get(fid, "")
                if not (isinstance(prefilled_val, str) and prefilled_val.startswith("http")):
                    modal_fields.append(input_cfg)

        # If user_values is provided (from slash command), use them. 
        # Otherwise, show modal if there are inputs.
        if user_values is None and modal_fields:
            async def modal_callback(modal_interaction: discord.Interaction, values: dict):
                # Merge with prefilled (hidden) values
                final_values = prefilled.copy()
                final_values.update(values)
                
                if manifest.get("lora_list"):
                    await self.show_lora_selection(modal_interaction, workflow_name, workflow, manifest, final_values)
                else:
                    await modal_interaction.response.send_message(f"(Queue) Starting generation for '{workflow_name}'...")
                    message = await modal_interaction.original_response()
                    await self._execute_generation(modal_interaction, workflow_name, workflow, manifest, final_values, message_id=message.id)

            modal = DynamicModal(
                title=manifest.get("workflow_name", workflow_name)[:45],
                inputs=modal_fields,
                callback=modal_callback,
                prefilled=prefilled
            )
            await interaction.response.send_modal(modal)
            return

        # If we have values, merge with prefilled and proceed to selection or execution
        final_values = prefilled.copy()
        if user_values:
            final_values.update({k: v for k, v in user_values.items() if v is not None})

        # --- LORA SELECTION STEP ---
        # Support both legacy lora_list key AND the new dashboard discord.loras node assignments
        discord_loras = manifest.get('discord', {}).get('loras', {})
        # Pick the first non-empty lora list assignment as the list to present
        lora_list_name = manifest.get("lora_list")
        if not lora_list_name and discord_loras:
            lora_list_name = next((v for v in discord_loras.values() if v), None)
        
        if lora_list_name:
            # Store which node the lora should be injected into (from the dashboard assignment)
            if discord_loras:
                final_values['__lora_node_assignments__'] = discord_loras
            await self.show_lora_selection(interaction, workflow_name, workflow, manifest, final_values, lora_list=lora_list_name)
            return

        display_name = manifest.get("workflow_name") or manifest.get("discord_command") or workflow_name
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(f"Initializing generation for **{display_name}**...")
            else:
                await interaction.edit_original_response(content=f"Initializing generation for **{display_name}**...")
            
            message = await interaction.original_response()
            await self._execute_generation(interaction, workflow_name, workflow, manifest, final_values, message_id=message.id)
        except Exception as e:
            logger.error(f"Error during generation request for {workflow_name}: {e}", exc_info=True)
            try:
                err_msg = f"❌ An error occurred while starting generation: `{e}`"
                if not interaction.response.is_done():
                    await interaction.response.send_message(err_msg, ephemeral=True)
                else:
                    await interaction.followup.send(err_msg, ephemeral=True)
            except Exception:
                pass

    def _apply_workflow_overrides(self, manifest: dict, template: dict, values: dict):
        """Applies direct .env overrides for model and steps."""
        if manifest.get("workflow_name", "").lower() == "fluxdev":
            model_file = Config.FLUX_MODEL
            steps = Config.FLUX_STEPS
            
            logger.info(f"Applying direct overrides: Model={model_file}, Steps={steps}")
            
            # 1. Automatic Node Detection & Re-wiring
            # Node 287 = GGUF, Node 288 = Safetensors
            if "271" in template:
                target_node = "287" if model_file.endswith(".gguf") else "288"
                template["271"]["inputs"]["model"] = [target_node, 0]
                
                # Update the filename in the target loader node
                if target_node in template:
                    template[target_node]["inputs"]["unet_name"] = model_file
            
            # 2. Direct Step Injection
            if "198:1" in template:
                template["198:1"]["inputs"]["steps"] = steps
            
            # Store for display
            values["__profile__"] = f"{steps} Steps"
            values["__model__"] = model_file

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
            
        user_id = message.author.id
        if user_id in self.pending_uploads and message.attachments:
            state = self.pending_uploads.pop(user_id)
            field = state["missing_fields"].pop(0)
            
            logger.info(f"Captured file '{message.attachments[0].filename}' from user {user_id}")
            
            # Read the data BEFORE deleting the message
            try:
                # We store the actual bytes and filename to avoid CDN 404s after deletion
                attachment = message.attachments[0]
                file_bytes = await attachment.read()
                
                # We'll use a simple wrapper to mimic the attachment interface for the uploader
                class CapturedFile:
                    def __init__(self, bytes_data, filename):
                        self.bytes_data = bytes_data
                        self.filename = filename
                    async def read(self):
                        return self.bytes_data
                
                state["values"][field["id"]] = CapturedFile(file_bytes, attachment.filename)
                
                # NOW safe to delete
                await message.delete()
                logger.info(f"Successfully deleted upload message from {user_id}")
            except Exception as e:
                logger.error(f"Failed to capture/delete message from {user_id}: {e}")
                # If we failed to read, we shouldn't proceed with this field
                if "file_bytes" not in locals():
                    return 
                
            # If more fields are needed, ask for the next one
            if state["missing_fields"]:
                await self._process_generation(
                    user=message.author,
                    channel=message.channel,
                    workflow_name=state["workflow_name"],
                    wf=state["wf"],
                    manifest=state["manifest"],
                    values=state["values"],
                    message_id=state["message_id"],
                    missing_fields=state["missing_fields"]
                )
            else:
                # All files collected, continue to generation
                await self._process_generation(
                    user=message.author,
                    channel=message.channel,
                    workflow_name=state["workflow_name"],
                    wf=state["wf"],
                    manifest=state["manifest"],
                    values=state["values"],
                    message_id=state["message_id"]
                )

    async def _execute_generation(self, interaction: discord.Interaction, workflow_name: str, wf: dict, manifest: dict, values: dict, message_id: int = None):
        """Entry point for Interaction-based generations (Modals/Slash/LoRA select)."""
        display_name = manifest.get('workflow_name') or manifest.get('discord_command') or workflow_name

        # If no message_id we're coming from the LoRA picker (ephemeral flow).
        # Dismiss the picker and post a real visible channel message for progress tracking.
        if not message_id:
            try:
                if not interaction.response.is_done():
                    await interaction.response.defer()
                if interaction.message:
                    await interaction.message.delete()
                else:
                    await interaction.delete_original_response()
            except Exception:
                try:
                    if not interaction.response.is_done():
                        await interaction.response.defer(ephemeral=True)
                except Exception:
                    pass

            try:
                queue_msg = await interaction.channel.send(
                    f"🎨 **{interaction.user.display_name}** — Please wait while we spin this up..."
                )
                message_id = queue_msg.id
            except Exception as e:
                logger.error(f"Failed to send queue message: {e}")
        else:
            # Slash command path — interaction already responded to upstream
            if not interaction.response.is_done():
                try:
                    await interaction.response.defer(ephemeral=True)
                except Exception:
                    pass

        await self._process_generation(
            user=interaction.user,
            channel=interaction.channel,
            workflow_name=workflow_name,
            wf=wf,
            manifest=manifest,
            values=values,
            message_id=message_id,
            interaction=interaction
        )

    async def _process_generation(self, user: discord.User, channel: discord.abc.Messageable, workflow_name: str, wf: dict, manifest: dict, values: dict, message_id: int = None, interaction: discord.Interaction = None, missing_fields: list = None):
        logger.info(f"Processing generation for {user.display_name}: {workflow_name}")
        
        # 1. Detect missing required files
        if missing_fields is None:
            missing_fields = []
            for input_cfg in manifest.get("inputs", []):
                if input_cfg.get("type") in ["image_upload", "audio_upload", "video_upload"]:
                    fid = input_cfg["id"]
                    if not values.get(fid):
                        missing_fields.append(input_cfg)
        
        if missing_fields:
            field = missing_fields[0]
            self.pending_uploads[user.id] = {
                "workflow_name": workflow_name,
                "wf": wf,
                "manifest": manifest,
                "values": values,
                "missing_fields": missing_fields,
                "channel_id": channel.id,
                "message_id": message_id
            }
            
            if field.get("type") == "image_upload":
                emoji = "📸"
            elif field.get("type") == "audio_upload":
                emoji = "🎵"
            else:
                emoji = "🎥"
            msg = f"{emoji} **Action Required**: {user.mention}, please upload the **{field.get('label', 'file')}** now to complete your generation."
            
            if interaction and not interaction.response.is_done():
                await interaction.response.send_message(msg, ephemeral=True)
            else:
                # If we have a progress message already, update it or send a new prompt
                if message_id:
                    try:
                        m = await channel.fetch_message(message_id)
                        await m.edit(content=msg)
                    except:
                        await channel.send(msg)
                else:
                    await channel.send(msg)
            return

        # Proceed with generation
        db = SessionLocal()
        try:
            if message_id:
                try:
                    msg_obj = await channel.fetch_message(message_id)
                    await msg_obj.edit(content=f"Please wait while we spin this up...")
                except:
                    pass

            template = wf["template"].copy()
            self._apply_workflow_overrides(manifest, template, values)
            self._apply_lora_injection(template, values)
            
            # Handle file uploads (Attachments or CapturedFiles)
            for field_id, value in list(values.items()):
                if hasattr(value, 'read') and hasattr(value, 'filename'):
                    uploaded_filename = await self.bot.api_client.upload_file(value)
                    values[field_id] = uploaded_filename
                elif isinstance(value, str) and (value.startswith("http://") or value.startswith("https://")):
                    # (URL download logic remains same...)
                    try:
                        import aiohttp
                        from io import BytesIO
                        async with aiohttp.ClientSession() as session:
                            async with session.get(value, timeout=30) as resp:
                                if resp.status == 200:
                                    data = await resp.read()
                                    filename = f"url_{uuid.uuid4().hex[:8]}.png"
                                    
                                    class DummyAttachment:
                                        def __init__(self, data, name):
                                            self.data = data
                                            self.filename = name
                                        async def read(self): return self.data
                                        
                                    dummy = DummyAttachment(data, filename)
                                    values[field_id] = await self.bot.api_client.upload_file(dummy)
                    except Exception as e:
                        logger.error(f"URL download failed: {e}")
                elif isinstance(value, str) and not (value.startswith("http://") or value.startswith("https://")):
                    # Potential local file path or filename
                    possible_paths = [
                        os.path.abspath(value),
                        os.path.abspath(os.path.join("data", "assets", value)),
                        os.path.abspath(os.path.join("data", "assets", os.path.basename(value)))
                    ]
                    
                    found_path = None
                    for p in possible_paths:
                        if os.path.exists(p) and os.path.isfile(p):
                            found_path = p
                            break
                            
                    if found_path:
                        logger.info(f"Found local asset for {field_id}: {found_path}")
                        try:
                            with open(found_path, "rb") as f:
                                data = f.read()
                                filename = os.path.basename(found_path)
                                
                                class DummyAttachment:
                                    def __init__(self, data, name):
                                        self.data = data
                                        self.filename = name
                                    async def read(self): return self.data
                                    
                                dummy = DummyAttachment(data, filename)
                                uploaded_filename = await self.bot.api_client.upload_file(dummy)
                                values[field_id] = uploaded_filename
                                logger.info(f"Local asset uploaded as {uploaded_filename}")
                        except Exception as e:
                            logger.error(f"Local file upload failed for {field_id}: {e}")
                    elif "." in value and (value.endswith(".png") or value.endswith(".jpg") or value.endswith(".jpeg")):
                        logger.warning(f"Value '{value}' looks like an image but was not found in assets.")

            final_values = values.copy()
            
            # Model Sniffing
            model_name = "Unknown"
            for node_id, node_data in template.items():
                class_type = node_data.get("class_type", "")
                if class_type in ["UnetLoaderGGUF", "UNETLoader", "CheckpointLoaderSimple"]:
                    if "271" in template:
                        target_id = str(template["271"]["inputs"]["model"][0])
                        if node_id == target_id:
                            inputs = node_data.get("inputs", {})
                            model_name = inputs.get("unet_name") or inputs.get("ckpt_name") or model_name
                            break
                    else:
                        inputs = node_data.get("inputs", {})
                        model_name = inputs.get("unet_name") or inputs.get("ckpt_name") or model_name
                        if model_name != "Unknown": break
            
            final_values["__model__"] = model_name

            # Randomize Seeds — walk the template directly so every workflow gets fresh seeds
            # regardless of whether the seed node is in the manifest mapping.
            SEED_FIELDS = {'seed', 'noise_seed', 'rand_seed'}
            for node_id, node_data in template.items():
                node_inputs = node_data.get('inputs', {})
                for field_name in list(node_inputs.keys()):
                    if field_name.lower() in SEED_FIELDS or (
                        'seed' in field_name.lower() and isinstance(node_inputs[field_name], (int, float))
                        and not isinstance(node_inputs[field_name], list)
                    ):
                        new_seed = random.randint(10**14, 10**15 - 1)
                        node_inputs[field_name] = new_seed
                        final_values[f'__seed_{node_id}_{field_name}__'] = new_seed
                        logger.info(f"Randomized seed in node {node_id} field '{field_name}': {new_seed}")


            # Create DB Job
            job = GenerationJob(
                user_id=str(user.id),
                workflow_name=workflow_name,
                input_params=final_values,
                channel_id=str(channel.id),
                discord_message_id=str(message_id) if message_id else None,
                status=JobStatus.PENDING
            )
            db.add(job)
            db.commit()
            db.refresh(job)

            # Queue Prompt
            payload = PayloadBuilder.inject(template, manifest, final_values, shared_inputs=self.bot.workflow_registry.shared_inputs)
            prompt_id = await self.bot.api_client.queue_prompt(payload, self.bot.client_id)
            
            if prompt_id:
                job.comfy_prompt_id = prompt_id
                db.commit()
                logger.info(f"Queued job {job.id} with prompt_id {prompt_id}")
            else:
                error_msg = "❌ ComfyUI did not return a prompt ID. Check if ComfyUI is running."
                if interaction: await interaction.followup.send(error_msg, ephemeral=True)
                else: await channel.send(error_msg)

        except Exception as e:
            logger.error(f"Generation error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            err_msg = f"❌ Error: {e}"
            if interaction: await interaction.followup.send(err_msg, ephemeral=True)
            else: await channel.send(err_msg)
        finally:
            db.close()

    async def handle_regeneration(self, interaction: discord.Interaction, job_id: str):
        db = SessionLocal()
        old_job = db.query(GenerationJob).filter(GenerationJob.id == job_id).first()
        if not old_job:
            db.close()
            return await interaction.response.send_message("Job not found.", ephemeral=True)
            
        workflow_name = old_job.workflow_name
        values = old_job.input_params.copy()
        
        # Re-inject profile for the redo
        if "__profile__" in values:
            values["profile"] = values["__profile__"]
            
        # IMPORTANT: Reset all seeds to -1 for the new run
        for k in list(values.keys()):
            if "seed" in k.lower():
                values[k] = -1
        
        db.close()
        
        wf = self.bot.workflow_registry.get_workflow(workflow_name)
        if not wf:
            return await interaction.response.send_message("Workflow no longer exists.", ephemeral=True)

        await interaction.response.send_message(f"🔄 Regenerating '{workflow_name}'...")
        message = await interaction.original_response()
        await self._execute_generation(interaction, workflow_name, wf, wf["manifest"], values, message_id=message.id)

    async def handle_options_request(self, interaction: discord.Interaction, job_id: str):
        db = SessionLocal()
        old_job = db.query(GenerationJob).filter(GenerationJob.id == job_id).first()
        if not old_job:
            db.close()
            return await interaction.response.send_message("Job not found.", ephemeral=True)
            
        workflow_name = old_job.workflow_name
        current_values = dict(old_job.input_params)
        db.close()
        
        wf = self.bot.workflow_registry.get_workflow(workflow_name)
        if not wf:
            return await interaction.response.send_message("Workflow no longer exists.", ephemeral=True)

        manifest = wf["manifest"]
        inputs = manifest.get("inputs", [])

        async def on_options_confirm(confirm_interaction: discord.Interaction, new_values: dict):
            """Called when user clicks Confirm in OptionsView. Then route to LoRA picker or generate."""
            # Merge new values over current
            merged = {**current_values, **new_values}

            # Check for dynamic LoRAs
            discord_loras = manifest.get('discord', {}).get('loras', {})
            has_dynamic_loras = any(
                (c == 'list' if isinstance(c, str) else c.get('mode', 'list') == 'list')
                for c in discord_loras.values()
            ) if discord_loras else False

            lora_list_name = manifest.get('lora_list')
            if lora_list_name and has_dynamic_loras:
                if discord_loras:
                    merged['__lora_node_assignments__'] = discord_loras
                await self.show_lora_selection(
                    confirm_interaction, workflow_name, wf, manifest, merged,
                    lora_list=lora_list_name
                )
            else:
                # No LoRA — go straight to a new generation
                await confirm_interaction.response.edit_message(
                    content=f"✅ Options saved — queuing **{workflow_name}**…", view=None
                )
                try:
                    queue_msg = await confirm_interaction.channel.send(
                        f"🎨 **{confirm_interaction.user.display_name}** — queuing **{workflow_name}**…"
                    )
                    await self._process_generation(
                        user=confirm_interaction.user,
                        channel=confirm_interaction.channel,
                        workflow_name=workflow_name,
                        wf=wf,
                        manifest=manifest,
                        values=merged,
                        message_id=queue_msg.id,
                        interaction=confirm_interaction,
                    )
                except Exception as e:
                    logger.error(f"Options generation error: {e}", exc_info=True)

        view = OptionsView(
            inputs=inputs,
            current_values=current_values,
            on_confirm=on_options_confirm,
            workflow_name=workflow_name,
        )
        await interaction.response.send_message(
            content=view._status_text(),
            view=view,
            ephemeral=True,
        )

    @generate.autocomplete("workflow")
    async def workflow_autocomplete(self, interaction: discord.Interaction, current: str):
        workflows = self.bot.workflow_registry.list_workflows()
        return [
            app_commands.Choice(name=wf, value=wf)
            for wf in workflows if current.lower() in wf.lower()
        ]

    async def show_lora_selection(self, interaction: discord.Interaction, workflow_name: str, workflow: dict, manifest: dict, values: dict, message_id: int = None, lora_list: str = None):
        lora_list_name = lora_list or manifest.get("lora_list")
        if not lora_list_name:
            return await self._execute_generation(interaction, workflow_name, workflow, manifest, values, message_id)

        # Resolve path relative to LORAS_DIR
        lora_list_file = os.path.join(Config.LORAS_DIR, lora_list_name)

        if not os.path.exists(lora_list_file):
            logger.error(f"Lora list file {lora_list_file} not found.")
            return await self._execute_generation(interaction, workflow_name, workflow, manifest, values, message_id)

        view = LoraSelectionView(
            lora_file=lora_list_file,
            callback=self._execute_generation,
            workflow_name=workflow_name,
            workflow=workflow,
            manifest=manifest,
            values=values,
            message_id=message_id
        )

        msg = f"🎨 **Select a LoRA** for your `{workflow_name}` generation:"
        if interaction.response.is_done():
            await interaction.followup.send(msg, view=view, ephemeral=True)
        else:
            await interaction.response.send_message(msg, view=view, ephemeral=True)

    def _apply_lora_injection(self, template: dict, values: dict):
        selected_lora = values.get('__selected_lora__')
        if not selected_lora:
            return

        lora_file = selected_lora.get('file')
        lora_weight = selected_lora.get('weight', 1.0)
        add_prompt = selected_lora.get('add_prompt', '')

        logger.info(f"Injecting LoRA: {lora_file} with weight {lora_weight}")

        for node_id, node_data in template.items():
            title = node_data.get('_meta', {}).get('title', '').lower()
            class_type = node_data.get('class_type', '').lower()
            
            if 'lora' not in title and 'lora' not in class_type:
                continue

            inputs = node_data.get('inputs', {})
            
            # Standard LoraLoader / LoraLoaderModelOnly
            if 'lora_name' in inputs:
                inputs['lora_name'] = lora_file
                if 'strength_model' in inputs: inputs['strength_model'] = lora_weight
                if 'strength_clip' in inputs: inputs['strength_clip'] = lora_weight
            
            # Power Lora Loader (rgthree) - uses slot dicts: lora_1: {on, lora, strength}
            # Find the next available slot or slot 1
            elif 'PowerLoraLoaderHeaderWidget' in inputs:
                # Find an existing slot or create slot 1
                slot_key = None
                for key in inputs:
                    if key.startswith('lora_') and key != 'lora_count' and isinstance(inputs[key], dict):
                        slot_key = key
                        break
                if not slot_key:
                    slot_key = 'lora_1'
                
                inputs[slot_key] = {
                    'on': True,
                    'lora': lora_file,
                    'strength': lora_weight
                }
                logger.info(f"  Injected into Power LoRA slot '{slot_key}': {lora_file}")

        # 2. Append add_prompt to the positive prompt
        if add_prompt:
            for node_id, node_data in template.items():
                title = node_data.get('_meta', {}).get('title', '').lower()
                class_type = node_data.get('class_type', '').lower()
                
                # Look for the positive prompt encoder
                if class_type == 'cliptextencode' and ('positive' in title or 'prompt' in title):
                    current_text = node_data['inputs'].get('text', '')
                    if current_text:
                        node_data['inputs']['text'] = f"{current_text}, {add_prompt}"
                    else:
                        node_data['inputs']['text'] = add_prompt
                    logger.info(f"Appended LoRA prompt to node {node_id}")
                    break

async def setup(bot):
    await bot.add_cog(GenerationCog(bot))

import discord
import os
import aiofiles
from src.database.session import db_session
from src.database.models import GenerationJob, JobStatus, Asset
from src.bot.views import GenerationView
from src.core.config import Config
from src.core.logger import setup_logger

logger = setup_logger(__name__)

# ---------------------------------------------------------------------------
# Node-type → human-friendly label map
# Known node labels for common nodes in the comfymap (caching will be 5 mins for unknown nodes), no need to add more.
# ---------------------------------------------------------------------------
NODE_LABELS: dict[str, str] = {
    # ── Sampling ──────────────────────────────────────────────────────────
    "KSampler":                    "🎨 Sampling",
    "KSamplerAdvanced":            "🎨 Sampling (advanced)",
    "SamplerCustom":               "🎨 Custom sampling",
    "SamplerCustomAdvanced":       "🎨 Custom sampling (advanced)",
    "FluxGuidance":                "🎨 Flux sampling",
    "UNetSelfAttentionMultiply":   "🎨 Attention tuning",
    # ── Model loading ─────────────────────────────────────────────────────
    "CheckpointLoaderSimple":      "📦 Loading checkpoint",
    "CheckpointLoader":            "📦 Loading checkpoint",
    "UNETLoader":                  "📦 Loading UNet",
    "DualCLIPLoader":              "📦 Loading CLIP",
    "CLIPLoader":                  "📦 Loading CLIP",
    "LoraLoader":                  "🧩 Loading LoRA",
    "LoraLoaderModelOnly":         "🧩 Loading LoRA (model only)",
    "VAELoader":                   "📦 Loading VAE",
    "UpscaleModelLoader":          "📦 Loading upscale model",
    "IPAdapterModelLoader":        "📦 Loading IP-Adapter",
    "ControlNetLoader":            "📦 Loading ControlNet",
    # ── Encoding ──────────────────────────────────────────────────────────
    "CLIPTextEncode":              "✍️  Encoding prompt",
    "CLIPTextEncodeFlux":          "✍️  Encoding prompt (Flux)",
    "CLIPVisionEncode":            "✍️  Encoding image (CLIP)",
    "VAEEncode":                   "🗜️  VAE encoding",
    "VAEEncodeForInpaint":         "🗜️  VAE encoding (inpaint)",
    # ── Decoding ──────────────────────────────────────────────────────────
    "VAEDecode":                   "🖼️  Decoding image",
    "VAEDecodeTiled":              "🖼️  Decoding image (tiled)",
    # ── Image ops ─────────────────────────────────────────────────────────
    "ImageScale":                  "📐 Scaling image",
    "ImageScaleBy":                "📐 Scaling image",
    "ImageUpscaleWithModel":       "🔍 Upscaling image",
    "ImageSharpen":                "✨ Sharpening",
    "ImageBlur":                   "💧 Blurring",
    "ImageComposite":              "🖼️  Compositing",
    "ImageCrop":                   "✂️  Cropping",
    "ImagePadForOutpaint":         "🖼️  Padding for outpaint",
    "JWImageResizeByFactor":       "📐 Resizing image",
    "NVMaxAspectRatioResizer":     "📐 Resizing (aspect ratio)",
    # ── Saving / output ───────────────────────────────────────────────────
    "SaveImage":                   "💾 Saving image",
    "PreviewImage":                "💾 Saving preview",
    "SaveAnimatedWEBP":            "💾 Saving animated WEBP",
    # ── Video ─────────────────────────────────────────────────────────────
    "VHS_LoadVideo":               "🎬 Loading video",
    "VHS_VideoCombine":            "🎬 Encoding video",
    "VHS_VideoInfo":               "🎬 Reading video info",
    "WanVideoSampler":             "🎬 Video sampling (Wan)",
    "WanVideoEncode":              "🎬 Video encoding (Wan)",
    "WanVideoDecode":              "🎬 Video decoding (Wan)",
    "WanImageToVideo":             "🎬 Image-to-video (Wan)",
    "CogVideoSampler":             "🎬 Video sampling (CogVideo)",
    "LTXVSampler":                 "🎬 Video sampling (LTXV)",
    "HunyuanVideoSampler":         "🎬 Video sampling (Hunyuan)",
    "MochiSampler":                "🎬 Video sampling (Mochi)",
    # ── Audio ─────────────────────────────────────────────────────────────
    "SaveAudio":                   "🔊 Saving audio",
    "LoadAudio":                   "🔊 Loading audio",
    # ── IP-Adapter / ControlNet ───────────────────────────────────────────
    "IPAdapter":                   "🎭 Applying IP-Adapter",
    "IPAdapterAdvanced":           "🎭 Applying IP-Adapter",
    "ControlNetApply":             "🎛️  Applying ControlNet",
    "ControlNetApplyAdvanced":     "🎛️  Applying ControlNet",
    # ── Conditioning ──────────────────────────────────────────────────────
    "ConditioningCombine":         "⚗️  Combining conditions",
    "ConditioningSetArea":         "⚗️  Setting condition area",
    "InpaintModelConditioning":    "⚗️  Inpaint conditioning",
    # ── Latent ops ────────────────────────────────────────────────────────
    "EmptyLatentImage":            "⬜ Creating latent",
    "EmptySD3LatentImage":         "⬜ Creating latent (SD3)",
    "LatentUpscale":               "🔍 Upscaling latent",
    "LatentUpscaleBy":             "🔍 Upscaling latent",
    "LatentBlend":                 "⚗️  Blending latents",
    # ── Misc / utility ────────────────────────────────────────────────────
    "PrimitiveNode":               "⚙️  Setting values",
    "Note":                        "📝 Note",
    "EmptyLatentRatioSelectSDXL":  "⬜ Creating latent (ratio)",
    "EmptyLatentRatioSelectSD3":   "⬜ Creating latent (ratio)",
}

class ResultHandler:
    def __init__(self, bot):
        self.bot = bot

    def _friendly_node_label(self, node_type: str | None) -> str:
        """Return a friendly label for the given ComfyUI node class name."""
        if not node_type:
            return "⚙️  Processing"
        
        # Check if it's a raw node ID (e.g., "198" or "198:6")
        if isinstance(node_type, str) and node_type.replace(":", "").isdigit():
            return "⚙️  Processing"

        # 1. Check our hardcoded custom emojis
        if node_type in NODE_LABELS:
            return NODE_LABELS[node_type]
            
        # 2. Check the dynamic ComfyUI registry
        if hasattr(self.bot, 'node_display_names'):
            dynamic_name = self.bot.node_display_names.get(node_type)
            if dynamic_name:
                return f"⚙️  {dynamic_name}"
                
        # 3. Fallback
        return f"⚙️  {node_type}"

    async def handle_execution_done(self, prompt_id: str):
        logger.info(f"Processing finished execution for prompt {prompt_id}")
        
        job_data = None
        with db_session() as db:
            job = db.query(GenerationJob).filter(GenerationJob.comfy_prompt_id == prompt_id).first()
            if not job:
                logger.warning(f"No job found for prompt_id {prompt_id}")
                return
            
            if job.status == JobStatus.COMPLETED or job.status == JobStatus.FAILED:
                logger.info(f"Job {job.id} already processed ({job.status}), skipping redundant signal.")
                return
            
            job_data = {
                "id": job.id,
                "status": job.status,
                "channel_id": job.channel_id,
                "discord_message_id": job.discord_message_id,
                "workflow_name": job.workflow_name,
                "user_id": job.user_id,
                "input_params": dict(job.input_params) if job.input_params else {},
                "node_map": dict(job.node_map) if job.node_map else {},
            }

        try:
            # 1. Get history from ComfyUI
            history = await self.bot.api_client.get_history(prompt_id)
            prompt_history = history.get(prompt_id, {})
            outputs = prompt_history.get("outputs", {})
            
            files_to_upload = []
            assets_to_add = []
            
            # 2. Scan ALL output nodes for any media files
            SCAN_KEYS = ["images", "gifs", "video", "videos", "audio", "output"]
            
            for node_id, node_output in outputs.items():
                for key in SCAN_KEYS:
                    if key in node_output:
                        items = node_output[key]
                        if isinstance(items, dict):
                            items = [items]
                        for file_info in items:
                            if not isinstance(file_info, dict):
                                continue
                            filename = file_info.get("filename")
                            subfolder = file_info.get("subfolder", "")
                            folder_type = file_info.get("type", "output")
                            
                            if not filename:
                                continue

                            logger.info(f"Found output in node {node_id} [{key}]: {filename} (subfolder={subfolder}, type={folder_type})")
                            
                            try:
                                img_data = await self.bot.api_client.get_image(filename, subfolder, folder_type)
                                
                                # Save locally with unique name
                                local_filename = f"{prompt_id}_{filename}"
                                local_path = os.path.join(Config.ASSETS_DIR, local_filename)
                                async with aiofiles.open(local_path, mode='wb') as f:
                                    await f.write(img_data)
                                
                                # Determine MIME type for DB asset
                                ext = filename.rsplit('.', 1)[-1].lower()
                                mime = (
                                    "video/mp4" if ext in ["mp4", "webm", "mov"] else
                                    "audio/wav" if ext in ["wav", "mp3", "flac", "ogg"] else
                                    "image/gif" if ext == "gif" else
                                    "image/png"
                                )
                                
                                # Save asset metadata details to register in DB later
                                assets_to_add.append((local_path, mime))
                                files_to_upload.append(discord.File(local_path, filename=filename))
                            except Exception as e:
                                logger.error(f"Failed to download file {filename}: {e}")

            # 3. Deliver to Discord (Recycle the progress message)
            channel = self.bot.get_channel(int(job_data["channel_id"]))
            if channel and job_data["discord_message_id"]:
                try:
                    msg = await channel.fetch_message(int(job_data["discord_message_id"]))
                    
                    if files_to_upload:
                        # Get UI Config from manifest
                        # Get UI Config from manifest
                        wf = self.bot.workflow_registry.get_workflow(job_data["workflow_name"])
                        manifest = wf.get("manifest", {})
                        ui_cfg = manifest.get("discord", {}).get("ui") or manifest.get("ui", {})
                        layout_version = ui_cfg.get("layout_version", "v1")
                        
                        if layout_version == "v2":
                            # V2 Layout Components implementation
                            from discord.ui import LayoutView, Container, Section, TextDisplay, MediaGallery, Separator, Thumbnail
                            from discord import MediaGalleryItem
                            
                            view = LayoutView()
                            
                            buttons = []
                            existing_ids = set()
                            for btn_cfg in ui_cfg.get("buttons", []):
                                btn_type = btn_cfg.get("type", "action")
                                label = btn_cfg.get("label", "Button")
                                style_str = btn_cfg.get("style", "secondary")
                                emoji = btn_cfg.get("emoji")
                                if not emoji: emoji = None
                                
                                style = discord.ButtonStyle.secondary
                                if style_str == "primary": style = discord.ButtonStyle.primary
                                elif style_str == "success": style = discord.ButtonStyle.success
                                elif style_str == "danger": style = discord.ButtonStyle.danger

                                if btn_type == "action":
                                    target = btn_cfg.get("target_workflow", "")
                                    source = btn_cfg.get("source_type", "image")
                                    mapping = btn_cfg.get("input_mapping", "")
                                    
                                    import json
                                    mapping_str = json.dumps(mapping) if isinstance(mapping, dict) else mapping
                                    custom_id = f"link_action_{target}_{source}_{mapping_str}_{job_data['id']}"
                                    
                                    if custom_id not in existing_ids:
                                        btn = discord.ui.Button(label=label, style=style, custom_id=custom_id, emoji=emoji)
                                        buttons.append(btn)
                                        existing_ids.add(custom_id)
                                        
                                elif btn_type == "chain":
                                    target = btn_cfg.get("target_workflow", "")
                                    pass_data = btn_cfg.get("pass_data", "image")
                                    target_input = btn_cfg.get("target_input", "image")
                                    custom_id = f"link_chain_{target}|{pass_data}|{target_input}|{job_data['id']}"
                                    
                                    if custom_id not in existing_ids:
                                        btn = discord.ui.Button(label=label, style=style, custom_id=custom_id, emoji=emoji)
                                        buttons.append(btn)
                                        existing_ids.add(custom_id)
                                        
                                elif btn_type == "selector":
                                    custom_id = f"link_selector_{job_data['id']}"
                                    if custom_id not in existing_ids:
                                        btn = discord.ui.Button(label=label, style=style, custom_id=custom_id, emoji=emoji)
                                        buttons.append(btn)
                                        existing_ids.add(custom_id)
                                        
                                elif btn_type == "delete":
                                    custom_id = f"link_gen_delete_{job_data['id']}"
                                    if custom_id not in existing_ids:
                                        btn = discord.ui.Button(label=label, style=style, custom_id=custom_id, emoji=emoji)
                                        buttons.append(btn)
                                        existing_ids.add(custom_id)
                                            
                                elif btn_type == "regenerate":
                                    custom_id = f"link_gen_redo_{job_data['id']}"
                                    if custom_id not in existing_ids:
                                        btn = discord.ui.Button(label=label, style=style, custom_id=custom_id, emoji=emoji)
                                        buttons.append(btn)
                                        existing_ids.add(custom_id)
                                            
                                elif btn_type == "options":
                                    custom_id = f"link_gen_options_{job_data['id']}"
                                    if custom_id not in existing_ids:
                                        btn = discord.ui.Button(label=label, style=style, custom_id=custom_id, emoji=emoji)
                                        buttons.append(btn)
                                        existing_ids.add(custom_id)
                                        
                            # 3. Build Result Container (V2 Layout)
                            v2_cfg = ui_cfg.get("v2_layout", {})
                            use_role_color = v2_cfg.get("use_role_color", True)
                            color = None
                            
                            if use_role_color and job_data["user_id"]:
                                try:
                                    guild = channel.guild if channel and hasattr(channel, 'guild') else None
                                    member = None
                                    if guild:
                                        member = guild.get_member(int(job_data["user_id"])) or await guild.fetch_member(int(job_data["user_id"]))
                                    
                                    if member and member.color != discord.Color.default():
                                        color = member.color
                                except Exception as e:
                                    logger.debug(f"Could not resolve role color for user {job_data['user_id']}: {e}")
                                    
                            if color is None:
                                color_hex = v2_cfg.get("color", "#5865F2").replace("#", "")
                                color = int(color_hex, 16)
                            
                            user = None
                            try:
                                user = self.bot.get_user(int(job_data["user_id"]))
                                if not user: user = await self.bot.fetch_user(int(job_data["user_id"]))
                            except Exception: pass

                            title_text = v2_cfg.get('title_template', '{user}\'s Generation')
                            if user: title_text = title_text.replace('{user}', user.display_name)
                            else: title_text = title_text.replace('{user}', 'User')

                            title_display = TextDisplay(f"### ✨ {title_text}")
                            
                            meta_fields = v2_cfg.get("show_metadata", [])
                            prompt_val = None
                            meta_text = ""
                            
                            if meta_fields:
                                meta_map = {
                                    "prompt": ("Prompt", "📝"),
                                    "seed": ("Seed", "🎲"),
                                    "model": ("Model", "🤖"),
                                    "ratio": ("Resolution", "📐"),
                                    "lora": ("LoRAs", "🧩"),
                                    "steps": ("Steps", "⏱️"),
                                    "cfg": ("CFG", "⚙️"),
                                    "sampler": ("Sampler", "🧪"),
                                    "upscale": ("Upscale", "🔍")
                                }
                                
                                if "prompt" in meta_fields:
                                    p_val = job_data["input_params"].get("prompt")
                                    if not p_val: p_val = job_data["input_params"].get("text")
                                    if not p_val: p_val = job_data["input_params"].get("positive")
                                    if not p_val: p_val = "—"
                                    prompt_val = p_val
                                
                                meta_lines = []
                                for field in meta_fields:
                                    if field == "prompt": continue
                                    label, emoji = meta_map.get(field, (field.title(), "🔹"))
                                    val = "—"
                                    
                                    if field == "seed":
                                        val = job_data["input_params"].get('seed')
                                        if not val:
                                            seed_key = next((k for k in job_data["input_params"].keys() if k.startswith('__seed_')), None)
                                            if seed_key: val = job_data["input_params"][seed_key]
                                        if not val: val = "Random"
                                        val = f"`{val}`"
                                    elif field == "model": val = f"`{job_data['input_params'].get('__model__', '—')}`"
                                    elif field == "lora":
                                        lora_data = job_data["input_params"].get("__selected_lora__")
                                        if lora_data:
                                            l_name = lora_data.get("name") or lora_data.get("file", "—").split(".")[0]
                                            l_weight = lora_data.get("weight", 1.0)
                                            val = f"`{l_name}` ({l_weight})"
                                        else:
                                            val = "—"
                                    elif field == "ratio":
                                        val = job_data["input_params"].get("ratio_selected")
                                        if not val: val = job_data["input_params"].get("resolution")
                                        if not val: val = job_data["input_params"].get("aspect_ratio", "—")
                                    elif field in job_data["input_params"]:
                                        val = str(job_data["input_params"][field])
                                    
                                    meta_lines.append(f"{emoji} **{label}:** {val}")
                                
                                meta_text = "\n".join(meta_lines) if meta_lines else ""

                            prompt_display = TextDisplay(f"📝 **Prompt:**\n{prompt_val}") if prompt_val else None
                            meta_display = TextDisplay(meta_text) if meta_text else None

                            show_footer = v2_cfg.get("show_footer", ui_cfg.get("show_footer", True))
                            footer_display = None
                            if show_footer:
                                profile = job_data['input_params'].get('__profile__', 'Standard')
                                job_id = job_data['id']
                                footer_display = TextDisplay(f"_*Link | Profile: {profile} | Job ID: {job_id}*_")

                            media_position = v2_cfg.get("media_position", "left")

                            if media_position in ["left", "right"] and files_to_upload and len(files_to_upload) == 1:
                                first_file = files_to_upload[0]
                                thumbnail = Thumbnail(media=f"attachment://{first_file.filename}")
                                
                                section_children = [title_display]
                                if prompt_display:
                                    section_children.append(prompt_display)
                                if meta_display:
                                    section_children.append(meta_display)
                                    
                                section = Section(*section_children, accessory=thumbnail)
                                
                                container_items = [section]
                                if footer_display:
                                    container_items.append(Separator())
                                    container_items.append(footer_display)
                                    
                                container = Container(*container_items, accent_color=color)
                            else:
                                container_children = [title_display]
                                
                                media_gallery = None
                                if files_to_upload:
                                    gallery_items = []
                                    for file in files_to_upload:
                                        gallery_items.append(MediaGalleryItem(media=f"attachment://{file.filename}"))
                                    media_gallery = MediaGallery(*gallery_items)
                                    
                                if media_position == 'top':
                                    if media_gallery:
                                        container_children.append(media_gallery)
                                        if prompt_display or meta_display or footer_display:
                                            container_children.append(Separator())
                                    if prompt_display:
                                        container_children.append(prompt_display)
                                    if meta_display:
                                        container_children.append(meta_display)
                                    if footer_display:
                                        if not prompt_display and not meta_display:
                                            pass
                                        else:
                                            container_children.append(Separator())
                                        container_children.append(footer_display)
                                else:
                                    if prompt_display:
                                        container_children.append(prompt_display)
                                    if meta_display:
                                        container_children.append(meta_display)
                                    if media_gallery:
                                        if len(container_children) > 1:
                                            container_children.append(Separator())
                                        container_children.append(media_gallery)
                                    if footer_display:
                                        container_children.append(Separator())
                                        container_children.append(footer_display)
                                        
                                container = Container(*container_children, accent_color=color)

                            view.add_item(container)
                            
                            if buttons:
                                for i in range(0, len(buttons), 5):
                                    action_row = discord.ui.ActionRow()
                                    for btn in buttons[i:i+5]:
                                        action_row.add_item(btn)
                                    view.add_item(action_row)

                            try:
                                await msg.edit(content=None, embed=None, attachments=files_to_upload, view=view)
                            except Exception as e:
                                logger.warning(f"Failed to edit message with V2 layout: {e}. Falling back to fresh message...")
                                try:
                                    try: await msg.delete()
                                    except Exception: pass
                                    await channel.send(content=None, embed=None, files=files_to_upload, view=view)
                                except Exception as e2:
                                    logger.error(f"Critical failure delivering V2 generation result: {e2}")
                                    await channel.send(files=files_to_upload)
                        else:
                            # Legacy V1 Layout Embed implementation
                            embed_cfg = ui_cfg.get("embed", {})
                            
                            # Create View and sync with configured buttons
                            from src.bot.views import GenerationView
                            view = GenerationView()
                            
                            # Grab existing items to retain their callbacks
                            existing_items = {item.custom_id: item for item in view.children if hasattr(item, 'custom_id')}
                            view.clear_items()
                            
                            existing_ids = set()
                            for btn_cfg in ui_cfg.get("buttons", []):
                                btn_type = btn_cfg.get("type", "action")
                                label = btn_cfg.get("label", "Button")
                                style_str = btn_cfg.get("style", "secondary")
                                emoji = btn_cfg.get("emoji")
                                if not emoji: emoji = None
                                
                                style = discord.ButtonStyle.secondary
                                if style_str == "primary": style = discord.ButtonStyle.primary
                                elif style_str == "success": style = discord.ButtonStyle.success
                                elif style_str == "danger": style = discord.ButtonStyle.danger

                                if btn_type == "action":
                                    target = btn_cfg.get("target_workflow", "")
                                    source = btn_cfg.get("source_type", "image")
                                    mapping = btn_cfg.get("input_mapping", "")
                                    
                                    import json
                                    mapping_str = json.dumps(mapping) if isinstance(mapping, dict) else mapping
                                    custom_id = f"link_action_{target}_{source}_{mapping_str}_{job_data['id']}"
                                    
                                    if custom_id not in existing_ids:
                                        btn = discord.ui.Button(label=label, style=style, custom_id=custom_id, emoji=emoji)
                                        view.add_item(btn)
                                        existing_ids.add(custom_id)
                                        
                                elif btn_type == "chain":
                                    target = btn_cfg.get("target_workflow", "")
                                    pass_data = btn_cfg.get("pass_data", "image")
                                    target_input = btn_cfg.get("target_input", "image")
                                    custom_id = f"link_chain_{target}|{pass_data}|{target_input}|{job_data['id']}"
                                    
                                    if custom_id not in existing_ids:
                                        btn = discord.ui.Button(label=label, style=style, custom_id=custom_id, emoji=emoji)
                                        view.add_item(btn)
                                        existing_ids.add(custom_id)
                                        
                                elif btn_type == "selector":
                                    custom_id = f"link_selector_{job_data['id']}"
                                    if custom_id not in existing_ids:
                                        btn = discord.ui.Button(label=label, style=style, custom_id=custom_id, emoji=emoji)
                                        view.add_item(btn)
                                        existing_ids.add(custom_id)
                                        
                                elif btn_type == "delete":
                                    if "link_gen_delete" not in existing_ids:
                                        btn = existing_items.get("link_gen_delete")
                                        if btn:
                                            btn.label = label
                                            btn.style = style
                                            btn.emoji = emoji
                                            btn.custom_id = f"link_gen_delete_{job_data['id']}"
                                            view.add_item(btn)
                                            existing_ids.add("link_gen_delete")
                                            
                                elif btn_type == "regenerate":
                                    if "link_gen_redo" not in existing_ids:
                                        btn = existing_items.get("link_gen_redo")
                                        if btn:
                                            btn.label = label
                                            btn.style = style
                                            btn.emoji = emoji
                                            btn.custom_id = f"link_gen_redo_{job_data['id']}"
                                            view.add_item(btn)
                                            existing_ids.add("link_gen_redo")
                                            
                                elif btn_type == "options":
                                    if "link_gen_options" not in existing_ids:
                                        btn = existing_items.get("link_gen_options")
                                        if btn:
                                            btn.label = label
                                            btn.style = style
                                            btn.emoji = emoji
                                            btn.custom_id = f"link_gen_options_{job_data['id']}"
                                            view.add_item(btn)
                                            existing_ids.add("link_gen_options")

                            # 3. Build Result Embed (High-Detail "Workstation" Style)
                            use_role_color = embed_cfg.get("use_role_color", True)
                            color = None
                            
                            if use_role_color and job_data["user_id"]:
                                try:
                                    guild = channel.guild if channel and hasattr(channel, 'guild') else None
                                    member = None
                                    if guild:
                                        member = guild.get_member(int(job_data["user_id"])) or await guild.fetch_member(int(job_data["user_id"]))
                                    
                                    if member and member.color != discord.Color.default():
                                        color = member.color
                                except Exception as e:
                                    logger.debug(f"Could not resolve role color for user {job_data['user_id']}: {e}")
                                    
                            if color is None:
                                color_hex = embed_cfg.get("color", "#5865F2").replace("#", "")
                                color = int(color_hex, 16)
                            
                            user = None
                            try:
                                user = self.bot.get_user(int(job_data["user_id"]))
                                if not user: user = await self.bot.fetch_user(int(job_data["user_id"]))
                            except Exception: pass

                            embed = discord.Embed(color=color)
                            
                            title_text = embed_cfg.get('title_template', '{user}\'s Generation')
                            if user: title_text = title_text.replace('{user}', user.display_name)
                            else: title_text = title_text.replace('{user}', 'User')
                            embed.title = f"✨ {title_text}"

                            # Metadata fields
                            meta_fields = embed_cfg.get("show_metadata", [])
                            if meta_fields:
                                meta_map = {
                                    "prompt": ("Prompt", "📝"),
                                    "seed": ("Seed", "🎲"),
                                    "model": ("Model", "🤖"),
                                    "ratio": ("Resolution", "📐"),
                                    "lora": ("LoRAs", "🧩"),
                                    "steps": ("Steps", "⏱️"),
                                    "cfg": ("CFG", "⚙️"),
                                    "sampler": ("Sampler", "🧪"),
                                    "upscale": ("Upscale", "🔍")
                                }
                                
                                if "prompt" in meta_fields:
                                    p_val = job_data["input_params"].get("prompt")
                                    if not p_val: p_val = job_data["input_params"].get("text")
                                    if not p_val: p_val = job_data["input_params"].get("positive")
                                    if not p_val: p_val = "—"
                                    embed.description = f"📝 **Prompt:**\n{p_val}"
                                
                                for field in meta_fields:
                                    if field == "prompt": continue
                                    label, emoji = meta_map.get(field, (field.title(), "🔹"))
                                    val = "Unknown"
                                    
                                    if field == "seed": 
                                        val = job_data["input_params"].get('seed')
                                        if not val:
                                            seed_key = next((k for k in job_data["input_params"].keys() if k.startswith('__seed_')), None)
                                            if seed_key: val = job_data["input_params"][seed_key]
                                        if not val: val = "Random"
                                        val = f"`{val}`"
                                        
                                    elif field == "model": val = f"`{job_data['input_params'].get('__model__', '—')}`"
                                    elif field == "lora":
                                        lora_data = job_data["input_params"].get("__selected_lora__")
                                        if lora_data:
                                            l_name = lora_data.get("name") or lora_data.get("file", "—").split(".")[0]
                                            l_weight = lora_data.get("weight", 1.0)
                                            val = f"`{l_name}` ({l_weight})"
                                        else:
                                            val = "—"
                                    elif field == "ratio": 
                                        val = job_data["input_params"].get("ratio_selected")
                                        if not val: val = job_data["input_params"].get("resolution")
                                        if not val: val = job_data["input_params"].get("aspect_ratio", "—")
                                        
                                    elif field in job_data["input_params"]: 
                                        val = str(job_data["input_params"][field])
                                    else:
                                        val = "—"
                                    
                                    embed.add_field(name=f"{emoji} **{label}:**", value=val, inline=True)

                            # Footer section
                            if embed_cfg.get("show_footer", True):
                                embed.set_footer(text=f"Link | Profile: {job_data['input_params'].get('__profile__', 'Standard')} | Job ID: {job_data['id']}")

                            if files_to_upload:
                                first_filename = files_to_upload[0].filename.lower()
                                is_image = any(first_filename.endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp'])
                                
                                if is_image and embed_cfg.get("image_position") == "bottom":
                                    embed.set_image(url=f"attachment://{files_to_upload[0].filename}")

                            try:
                                await msg.edit(content=None, embed=embed, attachments=files_to_upload, view=view)
                            except Exception as e:
                                logger.warning(f"Failed to edit message with files: {e}. Falling back to fresh message...")
                                try:
                                    try: await msg.delete()
                                    except Exception: pass
                                    await channel.send(content=None, embed=embed, files=files_to_upload, view=view)
                                except Exception as e2:
                                    logger.error(f"Critical failure delivering generation result: {e2}")
                                    await channel.send(files=files_to_upload)
                    else:
                        await msg.edit(content="Generation complete, but no output files were found.", embed=None)
                except Exception as e:
                    logger.error(f"Failed to process execution results: {e}")
                    if files_to_upload:
                        await channel.send(content="Generation ready!", embed=embed if 'embed' in locals() else None, files=files_to_upload, view=view if 'view' in locals() else None)

            # 4. Update Job Status and register assets in database
            with db_session() as db:
                for file_path, mime in assets_to_add:
                    asset = Asset(job_id=job_data["id"], file_path=file_path, file_type=mime)
                    db.add(asset)
                
                db.query(GenerationJob).filter(GenerationJob.id == job_data["id"]).update({
                    "status": JobStatus.COMPLETED
                })
            logger.info(f"Job {job_data['id']} marked as COMPLETED")

        except Exception as e:
            logger.error(f"Error handling execution results for job {job_data['id'] if job_data else 'unknown'}: {e}")
            if job_data:
                try:
                    with db_session() as db:
                        db.query(GenerationJob).filter(GenerationJob.id == job_data["id"]).update({
                            "status": JobStatus.FAILED
                        })
                except Exception as db_err:
                    logger.error(f"Failed to mark job as failed in DB: {db_err}")
        finally:
            if hasattr(self.bot, 'queue_manager') and self.bot.queue_manager:
                await self.bot.queue_manager.on_job_completed(prompt_id)

    async def handle_execution_error(self, prompt_id: str, node_type: str, message: str):
        """Called when ComfyUI reports execution_error or execution_interrupted."""
        logger.error(f"Handling execution error for prompt {prompt_id}: [{node_type}] {message}")

        job_data = None
        with db_session() as db:
            job = db.query(GenerationJob).filter(GenerationJob.comfy_prompt_id == prompt_id).first()
            if not job:
                logger.warning(f"No job found for prompt_id {prompt_id} during error handling")
                return

            if job.status in (JobStatus.COMPLETED, JobStatus.FAILED):
                return  # already handled

            job.status = JobStatus.FAILED
            job_data = {
                "id": job.id,
                "channel_id": job.channel_id,
                "discord_message_id": job.discord_message_id,
            }

        if job_data:
            try:
                channel = self.bot.get_channel(int(job_data["channel_id"]))
                if channel and job_data["discord_message_id"]:
                    try:
                        msg = await channel.fetch_message(int(job_data["discord_message_id"]))
                        friendly = self._friendly_node_label(node_type)
                        short_msg = message[:200] if message else "An unknown error occurred"
                        await msg.edit(
                            content=f"❌ **Generation failed** while {friendly}\n> `{short_msg}`",
                            embed=None,
                            attachments=[],
                            view=None,
                        )
                    except Exception as e:
                        logger.error(f"Failed to post error message to Discord: {e}")
            finally:
                if hasattr(self.bot, 'queue_manager') and self.bot.queue_manager:
                    await self.bot.queue_manager.on_job_completed(prompt_id)

    def _resolve_node_name(self, job, node_info: str | None) -> str | None:
        """Resolve a numeric node ID to its class name using the job's node_map."""
        if not node_info:
            return None
        
        node_str = str(node_info)
        if hasattr(job, 'node_map') and job.node_map:
            if node_str in job.node_map:
                return job.node_map[node_str]
            
            # Handle grouped/nested nodes like "198:6" -> "198"
            base_node = node_str.split(":")[0]
            if base_node in job.node_map:
                return job.node_map[base_node]
            
        return node_info

    async def update_node_status(self, prompt_id: str, node_info: str | None):
        """Edit the Discord progress message to show which node just started."""
        if not prompt_id or not node_info:
            return

        node_type = None
        job_data = None
        with db_session() as db:
            job = db.query(GenerationJob).filter(GenerationJob.comfy_prompt_id == prompt_id).first()
            if not job or not job.discord_message_id or not job.channel_id:
                return

            # Resolve ID to Type
            node_type = self._resolve_node_name(job, node_info)
            job_data = {
                "id": job.id,
                "channel_id": job.channel_id,
                "discord_message_id": job.discord_message_id,
            }

        if node_type and job_data:
            # Skip nodes that are noisy / near-instant (loaders flicker too fast)
            SKIP_TYPES = {"PrimitiveNode", "Note", "ConditioningCombine", "ConditioningSetArea"}
            if node_type in SKIP_TYPES:
                return

            channel = self.bot.get_channel(int(job_data["channel_id"]))
            if channel:
                try:
                    msg = await channel.fetch_message(int(job_data["discord_message_id"]))
                    label = self._friendly_node_label(node_type)
                    # Show an initial 0% bar when a node starts so it feels like a reset
                    empty_bar = "░" * 10
                    content = f"{label}…\n`[{empty_bar}]` **0%**"
                    if msg.content != content:
                        await msg.edit(content=content)
                        logger.debug(f"Node status → '{label}' (0%) for job {job_data['id']}")
                except Exception:
                    pass

    async def update_progress(self, prompt_id: str, value: int, max_val: int, node_type: str | None = None):
        if not prompt_id or max_val <= 0:
            return
            
        percent = int((value / max_val) * 100)
        
        # THROTTLING: 
        # 1. Always update for small step counts (<= 20) so they don't feel "stuck"
        # 2. For large step counts, update at 25% milestones
        # 3. Always update at 0% and 100%
        is_low_steps = max_val <= 20
        is_milestone = percent % 25 == 0 or percent >= 99 or percent == 0 or is_low_steps
        
        if not is_milestone:
            return

        resolved_node_type = None
        job_data = None
        with db_session() as db:
            job = db.query(GenerationJob).filter(GenerationJob.comfy_prompt_id == prompt_id).first()
            if job and job.discord_message_id and job.channel_id:
                resolved_node_type = self._resolve_node_name(job, node_type)
                job_data = {
                    "id": job.id,
                    "channel_id": job.channel_id,
                    "discord_message_id": job.discord_message_id,
                }

        if job_data:
            bar_length = 10
            filled = int(bar_length * value // max_val)
            bar = "█" * filled + "░" * (bar_length - filled)
            
            label = self._friendly_node_label(resolved_node_type)

            try:
                channel = self.bot.get_channel(int(job_data["channel_id"]))
                if channel:
                    msg = await channel.fetch_message(int(job_data["discord_message_id"]))
                    content = f"{label}…\n`[{bar}]` **{percent}%**"
                    if msg.content != content:
                        await msg.edit(content=content)
                        logger.info(f"Updated Discord progress to {percent}% ({label}) for job {job_data['id']}")
            except Exception:
                pass


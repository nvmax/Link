import discord
import os
import aiofiles
from src.database.session import SessionLocal
from src.database.models import GenerationJob, JobStatus, Asset
from src.bot.views import GenerationView
from src.core.config import Config
from src.core.logger import setup_logger

logger = setup_logger(__name__)

class ResultHandler:
    def __init__(self, bot):
        self.bot = bot

    async def handle_execution_done(self, prompt_id: str):
        logger.info(f"Processing finished execution for prompt {prompt_id}")
        
        db = SessionLocal()
        job = db.query(GenerationJob).filter(GenerationJob.comfy_prompt_id == prompt_id).first()
        
        if not job:
            logger.warning(f"No job found for prompt_id {prompt_id}")
            db.close()
            return
        
        if job.status == JobStatus.COMPLETED or job.status == JobStatus.FAILED:
            logger.info(f"Job {job.id} already processed ({job.status}), skipping redundant signal.")
            db.close()
            return

        try:
            # 1. Get history from ComfyUI
            history = await self.bot.api_client.get_history(prompt_id)
            prompt_history = history.get(prompt_id, {})
            outputs = prompt_history.get("outputs", {})
            
            files_to_upload = []
            
            # 2. Scan ALL nodes for images
            for node_id, node_output in outputs.items():
                # Some nodes put images in 'images', others in 'gifs', etc.
                for key in ["images", "gifs", "output"]:
                    if key in node_output:
                        for img_info in node_output[key]:
                            filename = img_info.get("filename")
                            subfolder = img_info.get("subfolder", "")
                            folder_type = img_info.get("type", "output")
                            
                            if not filename:
                                continue

                            logger.info(f"Found output in node {node_id}: {filename} (subfolder: {subfolder})")
                            
                            try:
                                img_data = await self.bot.api_client.get_image(filename, subfolder, folder_type)
                                
                                # Save locally with unique name
                                local_filename = f"{prompt_id}_{filename}"
                                local_path = os.path.join(Config.ASSETS_DIR, local_filename)
                                async with aiofiles.open(local_path, mode='wb') as f:
                                    await f.write(img_data)
                                
                                # Register asset in DB for workflow chaining
                                asset = Asset(job_id=job.id, file_path=local_filename, file_type="image/png")
                                db.add(asset)
                                
                                files_to_upload.append(discord.File(local_path, filename=filename))
                            except Exception as e:
                                logger.error(f"Failed to download image {filename}: {e}")

            # 3. Deliver to Discord (Recycle the progress message)
            channel = self.bot.get_channel(int(job.channel_id))
            if channel and job.discord_message_id:
                try:
                    msg = await channel.fetch_message(int(job.discord_message_id))
                    
                    if files_to_upload:
                        # Get UI Config from manifest
                        wf = self.bot.workflow_registry.get_workflow(job.workflow_name)
                        ui_cfg = wf.get("manifest", {}).get("ui_config", {})
                        embed_cfg = ui_cfg.get("embed", {})
                        
                        # Get User for title formatting
                        try:
                            user = self.bot.get_user(int(job.user_id))
                            if not user:
                                user = await self.bot.fetch_user(int(job.user_id))
                            user_name = user.display_name
                        except:
                            user_name = "User"
                        
                        title = embed_cfg.get("title_template", "✨ Generation Complete").replace("{user}", user_name)
                        color_hex = embed_cfg.get("color", "#2b2d31")
                        
                        # Detect the prompt field (might be 'prompt' or 'text' from Architect)
                        display_prompt = job.input_params.get('prompt') or job.input_params.get('text', 'N/A')

                        # Create a beautiful Embed
                        embed = discord.Embed(
                            title=title,
                            description=f"**Prompt:**\n{display_prompt}",
                            color=discord.Color.from_str(color_hex)
                        )
                        
                        show_meta = embed_cfg.get("show_metadata", ["prompt", "seed", "model", "ratio"])
                        
                        if "ratio" in show_meta:
                            res_val = job.input_params.get("ratio") or job.input_params.get("ratio_selected", "Standard")
                            embed.add_field(name="📐 Resolution", value=res_val, inline=True)
                        if "seed" in show_meta:
                            seed_val = job.input_params.get("seed", "Random")
                            embed.add_field(name="🎲 Seed", value=f"`{seed_val}`", inline=True)
                        if "model" in show_meta:
                            model_val = job.input_params.get("__model__", "Unknown")
                            embed.add_field(name="🤖 Model", value=f"`{model_val}`", inline=False)
                        if "steps" in show_meta:
                            embed.add_field(name="⏱️ Steps", value=f"`{job.input_params.get('steps', '20')}`", inline=True)
                        
                        # Create View and sync with configured buttons
                        from src.bot.views import GenerationView
                        view = GenerationView()
                        
                        # Track existing custom_ids in the base view to avoid duplicates
                        existing_ids = {item.custom_id for item in view.children if hasattr(item, 'custom_id')}
                        
                        for btn_cfg in ui_cfg.get("buttons", []):
                            btn_type = btn_cfg.get("type", "action")
                            label = btn_cfg.get("label", "Button")
                            style_str = btn_cfg.get("style", "secondary")
                            
                            style = discord.ButtonStyle.secondary
                            if style_str == "primary": style = discord.ButtonStyle.primary
                            elif style_str == "success": style = discord.ButtonStyle.success
                            elif style_str == "danger": style = discord.ButtonStyle.danger

                            if btn_type == "action":
                                target = btn_cfg.get("target_workflow", "")
                                source = btn_cfg.get("source_type", "image")
                                mapping = btn_cfg.get("input_mapping", "")
                                
                                # If mapping is a dict, serialize it to JSON
                                import json
                                if isinstance(mapping, dict):
                                    mapping_str = json.dumps(mapping)
                                else:
                                    mapping_str = mapping
                                    
                                custom_id = f"link_action_{target}_{source}_{mapping_str}"
                                
                                if custom_id not in existing_ids:
                                    btn = discord.ui.Button(label=label, style=style, custom_id=custom_id)
                                    view.add_item(btn)
                                    existing_ids.add(custom_id)
                            elif btn_type == "delete":
                                if "link_gen_delete" not in existing_ids:
                                    btn = discord.ui.Button(label=label, style=discord.ButtonStyle.danger, custom_id="link_gen_delete")
                                    view.add_item(btn)
                                    existing_ids.add("link_gen_delete")
                            # Add more types here if needed (e.g. regenerate, options are already in base)

                        # Instead, just attach it and Discord will render the player below the embed
                        main_file = files_to_upload[0]
                        filename_lower = main_file.filename.lower()
                        is_video = any(ext in filename_lower for ext in [".mp4", ".webm", ".mov", ".gif", ".m4v"])
                        
                        if not is_video:
                            embed.set_image(url=f"attachment://{main_file.filename}")
                        else:
                            logger.info(f"Video detected ({main_file.filename}), skipping embed.set_image for native playback.")
                        
                        embed.set_footer(text=f"Atlas Creative Suite | Profile: {job.input_params.get('__profile__', 'Standard')} | Job ID: {job.id}")

                        await msg.edit(content=None, embed=embed, attachments=files_to_upload, view=view)
                    else:
                        await msg.edit(content="Generation complete, but no output files were found.", embed=None)
                except Exception as e:
                    logger.error(f"Failed to edit progress message: {e}")
                    if files_to_upload:
                        await channel.send(content="Generation ready!", files=files_to_upload)
            elif channel and files_to_upload:
                await channel.send(content="Generation ready!", files=files_to_upload)

            # 4. Update Job Status
            job.status = JobStatus.COMPLETED
            db.commit()
            logger.info(f"Job {job.id} marked as COMPLETED")

        except Exception as e:
            logger.error(f"Error handling execution results for job {job.id}: {e}")
            job.status = JobStatus.FAILED
            db.commit()
        finally:
            db.close()

    async def update_progress(self, prompt_id: str, value: int, max_val: int):
        if not prompt_id or max_val <= 0:
            return
            
        db = SessionLocal()
        job = db.query(GenerationJob).filter(GenerationJob.comfy_prompt_id == prompt_id).first()
        if job and job.discord_message_id and job.channel_id:
            percent = int((value / max_val) * 100)
            
            # THROTTLING: Only update Discord for major milestones (25%, 50%, 75%, 100%)
            # This prevents rate limiting and keeps the bot snappy.
            is_milestone = percent % 25 == 0 or percent >= 99
            
            if is_milestone:
                bar_length = 10
                filled = int(bar_length * value // max_val)
                bar = "=" * filled + "-" * (bar_length - filled)
                
                try:
                    channel = self.bot.get_channel(int(job.channel_id))
                    if channel:
                        msg = await channel.fetch_message(int(job.discord_message_id))
                        content = f"Generating: **{percent}%**\n`[{bar}]`"
                        if msg.content != content:
                            await msg.edit(content=content)
                            logger.info(f"Updated Discord progress to {percent}% for job {job.id}")
                except Exception:
                    pass
        db.close()

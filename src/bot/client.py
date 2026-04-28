import discord
from discord import app_commands
from discord.ext import commands
import os
import yaml
import inspect
import re
import logging
from typing import Dict, Any, List
from src.core.config import Config
from src.core.logger import setup_logger

logger = setup_logger(__name__)

class LinkBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guild_messages = True
        super().__init__(command_prefix="!", intents=intents)
        self.workflow_registry = None
        self.api_client = None
        self.client_id = None

    async def setup_hook(self):
        # Load Cogs
        await self.load_extension("src.bot.cogs.generation")
        await self.load_extension("src.bot.cogs.utility")
        
        # Register dynamic commands from workflows
        await self.register_workflow_commands()
        
        # Register global interaction listener for smart actions
        from src.bot.views import handle_smart_action
        self.add_listener(handle_smart_action, "on_interaction")
        
        # Sync commands to Discord
        # For development, we sync to a specific guild for instant updates
        if Config.ALLOWED_GUILD_ID:
            guild = discord.Object(id=Config.ALLOWED_GUILD_ID)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            logger.info(f"Synced slash commands to guild {Config.ALLOWED_GUILD_ID}")
        else:
            await self.tree.sync()
            logger.info("Synced slash commands")

    async def register_workflow_commands(self):
        """Dynamically register a slash command for each workflow in the registry."""
        workflows = self.workflow_registry.list_workflows()
        
        for workflow_name in workflows:
            wf_data = self.workflow_registry.get_workflow(workflow_name)
            manifest = wf_data.get("manifest", {})
            command_name = manifest.get("discord_command", workflow_name).lower()
            
            # Safety check for valid Discord command name
            if not command_name or not re.match(r'^[\w-]{1,32}$', command_name):
                logger.warning(f"Skipping workflow '{workflow_name}': Invalid discord_command '{command_name}'")
                continue
                
            description = manifest.get("description", f"Generate using {workflow_name}")

            inputs = manifest.get("inputs", [])
            
            # Create a dynamic callback
            def create_callback(wf_name, workflow, manifest_data):
                async def callback(interaction: discord.Interaction, **kwargs):
                    # Defer immediately to prevent "Application did not respond"
                    try:
                        if not interaction.response.is_done():
                            await interaction.response.defer(ephemeral=False)
                    except:
                        pass
                        
                    try:
                        gen_cog = self.get_cog("GenerationCog")
                        if gen_cog:
                            # ... rest of logic
                            discord_loras = manifest_data.get('discord', {}).get('loras', {})
                            has_dynamic_loras = False
                            for node_id, config in discord_loras.items():
                                if isinstance(config, str):
                                    if config == 'list': has_dynamic_loras = True
                                elif isinstance(config, dict):
                                    if config.get('mode', 'list') == 'list': has_dynamic_loras = True
                                else:
                                    has_dynamic_loras = True
                                    
                            if manifest_data.get('lora_list') and has_dynamic_loras:
                                kwargs['__lora_node_assignments__'] = discord_loras
                                await gen_cog.show_lora_selection(
                                    interaction, wf_name, workflow, manifest_data, kwargs, 
                                    lora_list=manifest_data.get('lora_list')
                                )
                            else:
                                # Use handle_generation_request instead of _execute_generation 
                                # to ensure status messages and initialization logic are handled
                                await gen_cog.handle_generation_request(interaction, wf_name, user_values=kwargs)
                        else:
                            if not interaction.response.is_done():
                                await interaction.response.send_message("Generation system not loaded.", ephemeral=True)
                            else:
                                await interaction.followup.send("Generation system not loaded.", ephemeral=True)
                    except Exception as e:
                        logger.error(f"Error in dynamic command {wf_name}: {e}", exc_info=True)
                        err_msg = f"❌ Error executing command: `{e}`"
                        if not interaction.response.is_done():
                            await interaction.response.send_message(err_msg, ephemeral=True)
                        else:
                            await interaction.followup.send(err_msg, ephemeral=True)
                return callback

            callback = create_callback(workflow_name, wf_data, manifest)
            
            # Build parameters for the slash command
            workflow_params = []
            interaction_param = inspect.Parameter(
                "interaction", 
                inspect.Parameter.POSITIONAL_OR_KEYWORD, 
                annotation=discord.Interaction
            )
            
            # Add each input from YAML as a parameter
            for input_cfg in inputs:
                param_name = input_cfg["id"]
                param_type = input_cfg.get("type", "text")

                # Force image-like fields to upload even if manifest says select
                if param_type == "select":
                    choices_data = input_cfg.get("choices", [])
                    if isinstance(choices_data, list) and choices_data:
                        first = str(choices_data[0]).lower()
                        if any(first.endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.webp', '.mp4']):
                            param_type = "image_upload"
                            logger.info(f"Auto-converting select field '{param_name}' to image_upload based on content")

                # Sanitize the param name to a valid Python identifier
                safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', param_name).lstrip('_') or '_input'
                if not safe_name[0].isalpha() and safe_name[0] != '_':
                    safe_name = '_' + safe_name

                # Skip LoRA-type inputs from the initial slash command
                # They will be handled interactively after the command is sent.
                lora_node_ids = set()
                discord_loras = manifest.get('discord', {}).get('loras', {})
                for node_id in discord_loras.keys():
                    lora_node_ids.add(str(node_id))
                    
                is_lora_field = (
                    'lora' in param_name.lower() or 
                    '➕' in param_name or
                    param_name in ['lora_name', 'lora_1_name'] or
                    any(param_name == manifest.get('mapping', {}).get(k, [None, None, None])[2] 
                        and str(manifest.get('mapping', {}).get(k, [''])[0]) in lora_node_ids
                        for k in manifest.get('mapping', {}))
                )
                
                if is_lora_field:
                    safe_log_name = param_name.encode('ascii', errors='replace').decode('ascii')
                    logger.info(f"Skipping LoRA field '{safe_log_name}' from slash command (handled by LoRA picker)")
                    continue

                # Default to str unless it's a number or upload
                annotation = str
                if param_type == "number":
                    annotation = int
                elif param_type in ["image_upload", "audio_upload", "video_upload"]:
                    annotation = discord.Attachment
                
                # Use the 'required' flag from YAML
                is_required = input_cfg.get("required", False)
                
                if is_required:
                    default = inspect.Parameter.empty
                else:
                    default = input_cfg.get("default", None)
                    if input_cfg.get("type") in ["image_upload", "audio_upload"]:
                        default = None

                workflow_params.append(inspect.Parameter(
                    safe_name,
                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    annotation=annotation,
                    default=default
                ))

            # Sort workflow params so required (no default) come BEFORE optional (with default)
            workflow_params.sort(key=lambda p: p.default is not inspect.Parameter.empty)
            
            # Combine: interaction MUST be first
            final_params = [interaction_param] + workflow_params
            callback.__signature__ = inspect.Signature(final_params)
            
            choices_to_apply = {}
            autocomplete_to_apply = {}

            for input_cfg in inputs:
                fid = input_cfg["id"]
                choices_data = input_cfg.get("choices")
                if not choices_data:
                    continue
                if "lora" in fid.lower() or "➕" in fid:
                    continue
                if input_cfg.get("type") in ["image_upload", "audio_upload", "video_upload"]:
                    continue
                
                # Check if it was auto-converted
                if isinstance(choices_data, list) and choices_data:
                    first = str(choices_data[0]).lower()
                    if any(first.endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.webp', '.mp4']):
                        continue

                if isinstance(choices_data, list):
                    all_choices = choices_data
                elif isinstance(choices_data, dict):
                    all_choices = list(choices_data.keys())
                else:
                    continue

                safe_fid = re.sub(r'[^a-zA-Z0-9_]', '_', fid).lstrip('_') or '_input'

                if len(all_choices) <= 25:
                    choices_to_apply[safe_fid] = [
                        app_commands.Choice(name=str(c)[:100], value=str(c)[:100])
                        for c in all_choices
                    ]
                else:
                    autocomplete_to_apply[safe_fid] = [str(c) for c in all_choices]

            if choices_to_apply:
                callback = app_commands.choices(**choices_to_apply)(callback)

            for safe_fid, all_vals in autocomplete_to_apply.items():
                def make_ac(values):
                    async def autocomplete_cb(ac_interaction: discord.Interaction, current: str):
                        filtered = [v for v in values if current.lower() in v.lower()][:25]
                        return [app_commands.Choice(name=v[:100], value=v[:100]) for v in filtered]
                    return autocomplete_cb
                callback = app_commands.autocomplete(**{safe_fid: make_ac(all_vals)})(callback)

            new_command = app_commands.Command(
                name=command_name,
                description=description,
                callback=callback
            )

            self.tree.add_command(new_command)
            logger.info(f"Registered dynamic command /{command_name} with {len(new_command.parameters)} parameters")

    async def on_ready(self):
        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        logger.info("------")

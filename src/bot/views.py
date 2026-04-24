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
    if not custom_id.startswith("link_action_"):
        return
        
    # custom_id format: link_action_{target_wf}_{source_type}_{input_mapping}
    raw = custom_id.replace("link_action_", "")
    parts = raw.split("_", 2)
    
    if len(parts) < 3:
        return
        
    target_wf = parts[0]
    source_type = parts[1]
    input_mapping = parts[2]
    
    # Get Job ID from message
    if not interaction.message or not interaction.message.embeds:
        return
    footer = interaction.message.embeds[0].footer.text
    if "Job ID: " not in footer:
        return
    job_id = footer.split("Job ID: ")[1].strip()
    
    db = SessionLocal()
    try:
        # Get Job ID and original data
        job = db.query(GenerationJob).filter(GenerationJob.id == job_id).first()
        if not job:
            return await interaction.response.send_message("❌ Could not find original job data.", ephemeral=True)

        prefilled = {}
        
        # 1. Resolve Mapping (Supports string or dict)
        mapping_data = {}
        try:
            import json
            mapping_data = json.loads(input_mapping)
        except:
            mapping_data = {input_mapping: "image" if source_type == "image" else source_type}

        # 2. Extract and prefill based on mapping
        for target_field, source_ref in mapping_data.items():
            if source_ref == "image":
                # Grab the image URL directly from the message attachments
                if interaction.message and interaction.message.attachments:
                    prefilled[target_field] = interaction.message.attachments[0].url
                    logger.info(f"Pre-filled {target_field} with Discord URL: {prefilled[target_field]}")
                else:
                    # Fallback to DB if for some reason message is missing
                    from src.database.models import Asset
                    asset = db.query(Asset).filter(Asset.job_id == job_id).first()
                    if asset:
                        prefilled[target_field] = asset.file_path
            elif source_ref == "prompt":
                prefilled[target_field] = job.input_params.get("prompt", "")
            elif source_ref == "seed":
                prefilled[target_field] = str(job.input_params.get("seed", ""))
            elif source_ref in job.input_params:
                prefilled[target_field] = job.input_params[source_ref]

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

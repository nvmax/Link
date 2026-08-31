import discord
from discord import ui
from src.core.logger import setup_logger

logger = setup_logger(__name__)


class AIReviewModal(ui.Modal):
    def __init__(self, title: str, prompt_label: str, initial_content: str, callback):
        super().__init__(title=(title or "AI Prompt Enhancement")[:45])
        self.callback = callback
        
        default_val = str(initial_content or "")
        if len(default_val) > 4000:
            default_val = default_val[:4000]

        self.prompt_input = ui.TextInput(
            label=(prompt_label or "Prompt")[:45],
            style=discord.TextStyle.paragraph,
            placeholder="AI-Enhanced Prompt...",
            default=default_val,
            min_length=1,
            max_length=4000,
        )
        self.add_item(self.prompt_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            await self.callback(interaction, self.prompt_input.value)
        except Exception as e:
            logger.error(f"AIReviewModal on_submit error: {e}", exc_info=True)
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)
                else:
                    await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)
            except Exception:
                pass

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        logger.error(f"AIReviewModal error: {error}", exc_info=True)
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(f"❌ Error: {error}", ephemeral=True)
            else:
                await interaction.followup.send(f"❌ Error: {error}", ephemeral=True)
        except Exception:
            pass


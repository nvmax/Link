import discord
import os
from src.database.session import db_session
from src.database.models import ServerLimit, UserAgreement
from src.core.config import Config
from src.core.logger import setup_logger

logger = setup_logger("bot_tos")

class TOSAgreementView(discord.ui.View):
    def __init__(self, user_id: str):
        super().__init__(timeout=300)
        self.user_id = user_id
        
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("❌ This is not your request.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Agree", style=discord.ButtonStyle.success, emoji="✅")
    async def agree(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            with db_session() as db:
                agreement = UserAgreement(user_id=self.user_id, agreed=True)
                db.merge(agreement)
                db.commit()
            await interaction.response.edit_message(
                content="✅ **Terms of Service Accepted!** You can now run the generation command.",
                embed=None,
                view=None
            )
        except Exception as e:
            logger.error(f"Error saving terms of service agreement: {e}")
            await interaction.response.send_message("❌ Failed to save your agreement. Please try again later.", ephemeral=True)

    @discord.ui.button(label="Decline", style=discord.ButtonStyle.danger, emoji="❌")
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            content="❌ You declined the Terms of Service. Generation cancelled.",
            embed=None,
            view=None
        )

async def check_tos_agreement(interaction: discord.Interaction) -> bool:
    """
    Checks if Terms of Service agreement is required and if the user has agreed to it.
    If required and not agreed, sends an ephemeral message with the terms and returns False.
    Otherwise returns True.
    """
    if not interaction.guild:
        return True

    guild_id = str(interaction.guild.id)
    user_id = str(interaction.user.id)

    # Check if ToS is required for this guild
    tos_required = False
    try:
        with db_session() as db:
            limits = db.query(ServerLimit).filter(ServerLimit.guild_id == guild_id).first()
            if limits and limits.tos_required:
                tos_required = True
    except Exception as e:
        logger.error(f"Failed to check server limit ToS flag: {e}")

    if not tos_required:
        return True

    # Check if the user has agreed
    has_agreed = False
    try:
        with db_session() as db:
            agreement = db.query(UserAgreement).filter(UserAgreement.user_id == user_id).first()
            if agreement and agreement.agreed:
                has_agreed = True
    except Exception as e:
        logger.error(f"Failed to check user agreement: {e}")

    if has_agreed:
        return True

    # Prompt the user to agree
    embed = discord.Embed(
        title="📜 Terms of Service Agreement",
        description=(
            "Welcome! Before running your first generation on this server, please review and agree to the "
            "**Terms of Service**.\n\n"
            "By clicking **Agree**, you confirm that you will comply with these terms, "
            "including acceptable use guidelines (no harmful/illegal content, respect copyrights).\n\n"
            "Read the full document here: [Terms of Service](https://github.com/nvmax/Link/blob/main/docs/terms_of_service.md)."
        ),
        color=discord.Color.blue()
    )

    view = TOSAgreementView(user_id)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    return False

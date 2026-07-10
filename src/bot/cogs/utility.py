import discord
from discord import app_commands
from discord.ext import commands
from src.database.session import db_session
from src.database.models import GenerationJob
import logging
import asyncio
from src.core.logger import setup_logger

logger = setup_logger(__name__)

class Utility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Removed prefix commands to conform to Discord requirements and avoid privileged intents.

    @app_commands.command(name="feedback", description="Submit a bug, feature request, or feedback")
    async def feedback(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message("❌ This command must be used within a server.", ephemeral=True)
            return
            
        view = FeedbackCategoryView(self.bot)
        await interaction.response.send_message(
            content="📝 **Submit Feedback**\nPlease select a category below to start:",
            view=view,
            ephemeral=True
        )


class FeedbackCategoryView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=120)
        self.bot = bot

        self.category_select = discord.ui.Select(
            placeholder="Choose category...",
            min_values=1,
            max_values=1,
            options=[
                discord.SelectOption(label="Bug", value="Bug", emoji="🐛"),
                discord.SelectOption(label="Feature Request", value="Feature Request", emoji="💡"),
                discord.SelectOption(label="Other", value="Other", emoji="💬")
            ]
        )
        self.category_select.callback = self.select_callback
        self.add_item(self.category_select)

    async def select_callback(self, interaction: discord.Interaction):
        category = self.category_select.values[0] if self.category_select.values else "Other"
        modal = FeedbackModal(self.bot, category)
        await interaction.response.send_modal(modal)


class FeedbackModal(discord.ui.Modal):
    def __init__(self, bot, category):
        super().__init__(title=f"Submit Feedback ({category})", custom_id="feedback_modal_v2")
        self.bot = bot
        self.category = category

        # Note input
        placeholder_text = "Describe your feature request... (Note: Please upload your full workflow, not API .json)" if category == "Feature Request" else "Describe the bug, feature request or note..."
        self.note_input = discord.ui.TextInput(
            label="Feedback Details / Note",
            style=discord.TextStyle.paragraph,
            placeholder=placeholder_text,
            min_length=1,
            max_length=2000,
            required=True
        )
        self.add_item(self.note_input)

        # File upload component (V2 Layout Modal support)
        max_files = 1 if category == "Feature Request" else 10
        self.file_upload = discord.ui.FileUpload(
            custom_id="feedback_files",
            required=False,
            max_values=max_files,
            min_values=0
        )
        self.add_item(self.file_upload)

    async def on_submit(self, interaction: discord.Interaction):
        note = self.note_input.value

        # Validate files if category is Feature Request
        if self.category == "Feature Request" and self.file_upload.values:
            invalid_files = [att for att in self.file_upload.values if not att.filename.lower().endswith(".json")]
            if invalid_files:
                await interaction.response.send_message(
                    content="❌ **Error**: Only `.json` files are allowed for Feature Requests. *Please upload your full workflow, not API .json.*",
                    ephemeral=True
                )
                return

        await interaction.response.defer(ephemeral=True)

        guild_id = interaction.guild.id if interaction.guild else None
        guild_name = interaction.guild.name if interaction.guild else "Direct Message"

        # Read file bytes in memory
        files_data = []
        for att in self.file_upload.values:
            try:
                file_bytes = await att.read()
                files_data.append((file_bytes, att.filename))
            except Exception as e:
                logger.error(f"Failed to read attachment {att.filename}: {e}")

        await self.send_feedback(interaction, note, files_data, guild_id, guild_name)

    async def send_feedback(self, interaction: discord.Interaction, note: str, files_data: list, guild_id: int, guild_name: str):
        from src.core.config import Config
        import json
        import os
        import io
        
        permissions_path = os.path.join(Config.DATA_DIR, "permissions.json")
        feedback_admins = {}
        feedback_channels = {}
        if os.path.exists(permissions_path):
            try:
                with open(permissions_path, "r", encoding="utf-8") as f:
                    permissions_data = json.load(f)
                    feedback_admins = permissions_data.get("feedback_admins", {})
                    feedback_channels = permissions_data.get("feedback_channels", {})
            except Exception as e:
                logger.error(f"Error reading permissions.json: {e}")

        guild = self.bot.get_guild(guild_id)
        if not guild:
            await interaction.edit_original_response(content="❌ **Error**: Guild not found.")
            return

        # Try to resolve target channel first
        target_channel_id = feedback_channels.get(str(guild_id))
        target_channel = None
        if target_channel_id:
            try:
                target_channel = guild.get_channel(int(target_channel_id))
                if not target_channel:
                    target_channel = await guild.fetch_channel(int(target_channel_id))
            except Exception as e:
                logger.warning(f"Could not resolve feedback channel {target_channel_id}: {e}")

        destinations = []
        if target_channel:
            destinations.append(target_channel)

        # Also append configured admin ID if specified
        target_admin_id = feedback_admins.get(str(guild_id))
        if target_admin_id:
            try:
                admin_member = guild.get_member(int(target_admin_id))
                if not admin_member:
                    admin_member = await guild.fetch_member(int(target_admin_id))
                if admin_member:
                    destinations.append(admin_member)
            except Exception as e:
                logger.warning(f"Could not resolve feedback admin member {target_admin_id}: {e}")
                
            if not any(isinstance(d, (discord.Member, discord.User)) for d in destinations):
                try:
                    admin_user = await self.bot.fetch_user(int(target_admin_id))
                    if admin_user:
                        destinations.append(admin_user)
                except Exception as e:
                    logger.error(f"Could not resolve feedback admin user {target_admin_id}: {e}")
        
        # Absolute fallback to guild owner (requires no intents) if nothing else was resolved
        if not destinations:
            owner = guild.owner
            if not owner and guild.owner_id:
                try:
                    owner = await guild.fetch_member(guild.owner_id)
                except Exception:
                    pass
            if owner:
                destinations.append(owner)

        if not destinations:
            await interaction.edit_original_response(content="❌ **Error**: No administrator or target channel found to notify.")
            return

        color_map = {
            "Bug": 0xda373c,
            "Feature Request": 0xf1c40f,
            "Other": 0x4e5058,
        }
        accent_color = color_map.get(self.category, 0x5865F2)

        fallback_embed = discord.Embed(
            title=f"📥 New Feedback Received ({self.category})",
            color=accent_color,
            description=f"📝 **Details:**\n{note}"
        )
        fallback_embed.add_field(name="Submitted by", value=f"<@{interaction.user.id}> (ID: `{interaction.user.id}`)")
        fallback_embed.add_field(name="Server", value=f"**{guild_name}** (ID: `{guild_id}`)")

        use_v2 = False
        try:
            from discord.ui import LayoutView, Container, TextDisplay, MediaGallery, Separator
            from discord import MediaGalleryItem
            use_v2 = True
        except ImportError:
            pass

        if use_v2:
            view = LayoutView()
            title = TextDisplay(f"### 📥 New Feedback Received ({self.category})")
            sender = TextDisplay(f"👤 **Submitted by:** <@{interaction.user.id}> (ID: `{interaction.user.id}`)\n🖥️ **Server:** **{guild_name}** (ID: `{guild_id}`)")
            note_display = TextDisplay(f"📝 **Details:**\n{note}")

            section_children = [title, sender, note_display]

            gallery_items = []
            file_components = []
            if files_data:
                for file_bytes, filename in files_data:
                    ext = filename.rsplit('.', 1)[-1].lower()
                    if ext in ["png", "jpg", "jpeg", "gif", "webp"]:
                        gallery_items.append(MediaGalleryItem(media=f"attachment://{filename}"))
                    else:
                        file_components.append(discord.ui.File(media=f"attachment://{filename}"))

            if file_components:
                section_children.append(Separator())
                for fc in file_components:
                    section_children.append(fc)

            if gallery_items:
                section_children.append(Separator())
                section_children.append(MediaGallery(*gallery_items))

            container = Container(*section_children, accent_color=accent_color)
            view.add_item(container)

        success_count = 0
        for dest in destinations:
            try:
                # Create fresh discord.File objects from memory bytes for each send attempt
                files_to_send = []
                if files_data:
                    for file_bytes, filename in files_data:
                        files_to_send.append(discord.File(io.BytesIO(file_bytes), filename=filename))

                try:
                    if use_v2:
                        await dest.send(content=None, view=view, files=files_to_send)
                    else:
                        await dest.send(embed=fallback_embed, files=files_to_send)
                    success_count += 1
                except Exception as e:
                    logger.warning(f"Failed to send feedback to destination {dest}: {e}. Trying fallback embed...")
                    for f in files_to_send:
                        try:
                            f.close()
                        except Exception:
                            pass
                    
                    files_to_send_fallback = []
                    if files_data:
                        for file_bytes, filename in files_data:
                            files_to_send_fallback.append(discord.File(io.BytesIO(file_bytes), filename=filename))
                    try:
                        await dest.send(embed=fallback_embed, files=files_to_send_fallback)
                        success_count += 1
                    finally:
                        for f in files_to_send_fallback:
                            try:
                                f.close()
                            except Exception:
                                pass
                else:
                    success_count += 1
                    for f in files_to_send:
                        try:
                            f.close()
                        except Exception:
                            pass
            except Exception as e:
                logger.error(f"Could not send feedback to destination {dest}: {e}")

        if success_count > 0:
            if target_channel:
                await interaction.edit_original_response(content="✅ **Feedback sent successfully!** It has been posted to the server's feedback channel.")
            else:
                await interaction.edit_original_response(content="✅ **Feedback sent successfully!** Thank you for your feedback.")
        else:
            await interaction.edit_original_response(content="❌ **Error**: Failed to deliver feedback (DMs may be disabled or invalid channel permissions).")


async def setup(bot):
    await bot.add_cog(Utility(bot))

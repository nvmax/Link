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

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def setup_persistence(self, ctx):
        """Registers the persistent GenerationView manually if needed."""
        from src.bot.views import GenerationView
        self.bot.add_view(GenerationView())
        await ctx.send("✅ Persistent GenerationView registered.")

    @commands.command()
    async def last_job(self, ctx):
        """Show your last generation job ID."""
        job_id = None
        job_status = None
        with db_session() as db:
            job = db.query(GenerationJob).filter(GenerationJob.user_id == str(ctx.author.id)).order_by(GenerationJob.created_at.desc()).first()
            if job:
                job_id = job.id
                job_status = job.status.value

        if job_id:
            await ctx.send(f"Your last Job ID: `{job_id}` (Status: {job_status})")
        else:
            await ctx.send("You haven't run any jobs yet.")

    @commands.command()
    async def help(self, ctx: commands.Context, command: str = None):
        """Show this help message or give help for a specific command."""
        if command:
            command_obj = self.bot.get_command(command)
            if command_obj:
                embed = discord.Embed(title=f"Command: {command_obj.name}", description=command_obj.help or "No description provided.", color=0x3498db)
                embed.add_field(name="Usage", value=f"`{ctx.prefix}{command_obj.qualified_name} {command_obj.signature}`")
                await ctx.send(embed=embed)
            else:
                await ctx.send(f"Command `{command}` not found.")
        else:
            embed = discord.Embed(title="Help", description="List of available commands:", color=0x3498db)
            
            cogs_dict = {}
            for cmd in self.bot.commands:
                if cmd.hidden:
                    continue
                cog_name = cmd.cog.qualified_name if cmd.cog else "General"
                if cog_name not in cogs_dict:
                    cogs_dict[cog_name] = []
                cogs_dict[cog_name].append(cmd)
            
            for cog_name, commands_list in cogs_dict.items():
                cmds_str = ", ".join([f"`{c.name}`" for c in commands_list])
                embed.add_field(name=cog_name, value=cmds_str, inline=False)
                
            await ctx.send(embed=embed)

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
        if os.path.exists(permissions_path):
            try:
                with open(permissions_path, "r", encoding="utf-8") as f:
                    permissions_data = json.load(f)
                    feedback_admins = permissions_data.get("feedback_admins", {})
            except Exception as e:
                logger.error(f"Error reading permissions.json: {e}")

        guild = self.bot.get_guild(guild_id)
        if not guild:
            await interaction.edit_original_response(content="❌ **Error**: Guild not found.")
            return

        target_admin_id = feedback_admins.get(str(guild_id))
        admins = []

        if target_admin_id:
            try:
                admin_member = guild.get_member(int(target_admin_id))
                if not admin_member:
                    admin_member = await guild.fetch_member(int(target_admin_id))
                if admin_member:
                    admins.append(admin_member)
            except Exception as e:
                logger.warning(f"Could not resolve feedback admin member {target_admin_id}: {e}")
                
            if not admins:
                try:
                    admin_user = await self.bot.fetch_user(int(target_admin_id))
                    if admin_user:
                        admins.append(admin_user)
                except Exception as e:
                    logger.error(f"Could not resolve feedback admin user {target_admin_id}: {e}")
        
        if not admins:
            if not guild.chunked:
                try:
                    await asyncio.wait_for(guild.chunk_members(), timeout=5.0)
                except Exception as e:
                    logger.warning(f"Could not chunk guild members: {e}")
            for m in guild.members:
                if m.guild_permissions.administrator and not m.bot:
                    admins.append(m)

        if not admins:
            await interaction.edit_original_response(content="❌ **Error**: No administrator found to notify.")
            return

        from discord.ui import LayoutView, Container, TextDisplay, MediaGallery, Separator
        from discord import MediaGalleryItem

        view = LayoutView()
        color_map = {
            "Bug": 0xda373c,
            "Feature Request": 0xf1c40f,
            "Other": 0x4e5058,
        }
        accent_color = color_map.get(self.category, 0x5865F2)

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

        fallback_embed = discord.Embed(
            title=f"📥 New Feedback Received ({self.category})",
            color=accent_color,
            description=f"📝 **Details:**\n{note}"
        )
        fallback_embed.add_field(name="Submitted by", value=f"<@{interaction.user.id}> (ID: `{interaction.user.id}`)")
        fallback_embed.add_field(name="Server", value=f"**{guild_name}** (ID: `{guild_id}`)")

        success_count = 0
        for admin in admins:
            try:
                # Create fresh discord.File objects from memory bytes for each send attempt
                admin_files = []
                if files_data:
                    for file_bytes, filename in files_data:
                        admin_files.append(discord.File(io.BytesIO(file_bytes), filename=filename))

                try:
                    await admin.send(content=None, view=view, files=admin_files)
                except Exception as e:
                    logger.warning(f"Failed to send V2 layout feedback to admin {admin.id}: {e}. Trying fallback embed...")
                    for f in admin_files:
                        try:
                            f.close()
                        except Exception:
                            pass
                    
                    admin_files_fallback = []
                    if files_data:
                        for file_bytes, filename in files_data:
                            admin_files_fallback.append(discord.File(io.BytesIO(file_bytes), filename=filename))
                    try:
                        await admin.send(embed=fallback_embed, files=admin_files_fallback)
                        success_count += 1
                    finally:
                        for f in admin_files_fallback:
                            try:
                                f.close()
                            except Exception:
                                pass
                else:
                    success_count += 1
                    for f in admin_files:
                        try:
                            f.close()
                        except Exception:
                            pass
            except Exception as e:
                logger.error(f"Could not send feedback DM to admin {admin.id}: {e}")

        if success_count > 0:
            await interaction.edit_original_response(content="✅ **Feedback sent successfully!** Thank you for your feedback.")
        else:
            await interaction.edit_original_response(content="❌ **Error**: Failed to deliver feedback to any administrator DMs (they may have DMs disabled).")


async def setup(bot):
    if bot.get_command('help'):
        bot.remove_command('help')
    await bot.add_cog(Utility(bot))

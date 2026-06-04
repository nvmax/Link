import discord
from discord.ext import commands
from src.database.session import db_session
from src.database.models import GenerationJob
import logging

logger = logging.getLogger(__name__)

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

async def setup(bot):
    if bot.get_command('help'):
        bot.remove_command('help')
    await bot.add_cog(Utility(bot))

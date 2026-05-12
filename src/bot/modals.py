import discord
from discord import ui

class AIReviewModal(ui.Modal):
    def __init__(self, title, prompt_label, initial_content, callback):
        super().__init__(title=title)
        self.callback = callback
        
        self.prompt_input = ui.TextInput(
            label=prompt_label,
            style=discord.TextStyle.paragraph,
            placeholder="AI-Enhanced Prompt...",
            default=initial_content,
            min_length=1,
            max_length=4000,
        )
        self.add_item(self.prompt_input)

    async def on_submit(self, interaction: discord.Interaction):
        await self.callback(interaction, self.prompt_input.value)

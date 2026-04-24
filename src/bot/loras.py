import discord
from discord import ui
import json
import os
import math
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)

# Category display names / emojis
CATEGORY_META = {
    'aidma':          ('🎨', 'Aidma Series'),
    'animal':         ('🐾', 'Animals'),
    'anime':          ('🌸', 'Anime'),
    'architecture':   ('🏛️', 'Architecture'),
    'artistic':       ('🖌️', 'Artistic Styles'),
    'cartoon':        ('🃏', 'Cartoon'),
    'celebrity':      ('⭐', 'Celebrities'),
    'character':      ('🧝', 'Characters'),
    'fantasy':        ('🧙', 'Fantasy'),
    'modern-art':     ('🖼️', 'Modern Art'),
    'nsfw':           ('🔞', 'NSFW'),
    'photography':    ('📷', 'Photography'),
    'photorealistic': ('📸', 'Photorealistic'),
    'retro-art':      ('📼', 'Retro Art'),
    'scifi':          ('🚀', 'Sci-Fi'),
}

def _cat_label(cat: str) -> str:
    emoji, name = CATEGORY_META.get(cat, ('📁', cat.replace('-', ' ').title()))
    return f"{emoji} {name}"


class CategorySelect(ui.Select):
    def __init__(self, categories: list):
        options = []
        for cat, loras in categories:
            count = len(loras)
            options.append(discord.SelectOption(
                label=_cat_label(cat),
                value=cat,
                description=f"{count} LoRA{'s' if count != 1 else ''}",
            ))
        super().__init__(
            placeholder="🗂️ Choose a category first…",
            min_values=1,
            max_values=1,
            options=options,
            row=0,
        )

    async def callback(self, interaction: discord.Interaction):
        try:
            cat = self.values[0]
            # self.view is set automatically by discord.py when add_item() is called
            lv = self.view
            lv.selected_category = cat
            lv.lora_page = 0
            lv._show_lora_step()
            await interaction.response.edit_message(
                content=f"🎨 **{_cat_label(cat)}** — pick a LoRA:",
                view=lv,
            )
        except Exception as e:
            logger.error(f"CategorySelect error: {e}", exc_info=True)
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)
            except Exception:
                pass


class LoraSelect(ui.Select):
    def __init__(self, loras: list, page: int, total_pages: int):
        options = []
        for lora in loras:
            name = lora.get('name', lora.get('file', 'Unknown'))[:100]
            desc = (lora.get('description') or '')[:100]
            options.append(discord.SelectOption(
                label=name,
                value=lora.get('file', name),
                description=desc or None,
            ))
        super().__init__(
            placeholder=f"Select a LoRA — Page {page + 1}/{total_pages}",
            min_values=1,
            max_values=1,
            options=options,
            row=0,
        )

    async def callback(self, interaction: discord.Interaction):
        try:
            selected_file = self.values[0]
            lv = self.view
            cat = lv.selected_category
            lora_data = next(
                (l for l in lv.by_category.get(cat, []) if l.get('file') == selected_file),
                {'file': selected_file, 'weight': 1.0, 'add_prompt': ''}
            )
            lv.values['__selected_lora__'] = {
                'file': lora_data.get('file', selected_file),
                'weight': lora_data.get('weight', 1.0),
                'add_prompt': lora_data.get('add_prompt', ''),
            }
            await lv.final_callback(
                interaction, lv.workflow_name, lv.workflow,
                lv.manifest, lv.values, lv.message_id,
            )
            lv.stop()
        except Exception as e:
            logger.error(f"LoraSelect error: {e}", exc_info=True)
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(f"❌ Error selecting LoRA: {e}", ephemeral=True)
            except Exception:
                pass


class LoraSelectionView(ui.View):
    """Two-step LoRA picker: Category → LoRA within category."""

    def __init__(self, lora_file: str, callback, workflow_name: str, workflow: dict,
                 manifest: dict, values: dict, message_id: int = None):
        super().__init__(timeout=300)
        self.final_callback = callback
        self.workflow_name = workflow_name
        self.workflow = workflow
        self.manifest = manifest
        self.values = values
        self.message_id = message_id
        self.selected_category = None
        self.lora_page = 0
        self.page_size = 25

        # Load and bucket loras by category
        self.by_category = defaultdict(list)
        try:
            with open(lora_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            for lora in data.get('available_loras', []):
                if lora.get('is_active', True):
                    cat = lora.get('category', 'uncategorized')
                    self.by_category[cat].append(lora)
        except Exception as e:
            logger.error(f"Error loading lora file {lora_file}: {e}")

        self._show_category_step()

    # ── Step 1: Category ────────────────────────────────────────────────────

    def _show_category_step(self):
        self.clear_items()
        categories = sorted(self.by_category.items(), key=lambda x: x[0])

        if not categories:
            return

        self.add_item(CategorySelect(categories))

        skip = ui.Button(label="Skip LoRA", style=discord.ButtonStyle.danger, row=1)
        skip.callback = self._skip_lora
        self.add_item(skip)

    # ── Step 2: LoRA within category ────────────────────────────────────────

    def _show_lora_step(self):
        self.clear_items()
        loras = list(self.by_category.get(self.selected_category, []))
        total_pages = max(1, math.ceil(len(loras) / self.page_size))
        start = self.lora_page * self.page_size
        page_loras = loras[start:start + self.page_size]

        if page_loras:
            self.add_item(LoraSelect(page_loras, self.lora_page, total_pages))

        # Navigation row (only if multiple pages)
        if total_pages > 1:
            prev_btn = ui.Button(label="◀ Prev", style=discord.ButtonStyle.secondary,
                                 disabled=(self.lora_page == 0), row=1)
            prev_btn.callback = self._prev_page
            self.add_item(prev_btn)

            page_lbl = ui.Button(
                label=f"Page {self.lora_page + 1}/{total_pages}",
                style=discord.ButtonStyle.secondary, disabled=True, row=1,
            )
            self.add_item(page_lbl)

            nxt_btn = ui.Button(label="Next ▶", style=discord.ButtonStyle.secondary,
                                disabled=(self.lora_page >= total_pages - 1), row=1)
            nxt_btn.callback = self._next_page
            self.add_item(nxt_btn)

        back_btn = ui.Button(label="← Categories", style=discord.ButtonStyle.primary, row=2)
        back_btn.callback = self._back_to_categories
        self.add_item(back_btn)

        skip = ui.Button(label="Skip LoRA", style=discord.ButtonStyle.danger, row=2)
        skip.callback = self._skip_lora
        self.add_item(skip)

    # ── Button callbacks ─────────────────────────────────────────────────────

    async def _prev_page(self, interaction: discord.Interaction):
        try:
            self.lora_page -= 1
            self._show_lora_step()
            await interaction.response.edit_message(view=self)
        except Exception as e:
            logger.error(f"Prev page error: {e}", exc_info=True)

    async def _next_page(self, interaction: discord.Interaction):
        try:
            self.lora_page += 1
            self._show_lora_step()
            await interaction.response.edit_message(view=self)
        except Exception as e:
            logger.error(f"Next page error: {e}", exc_info=True)

    async def _back_to_categories(self, interaction: discord.Interaction):
        try:
            self.selected_category = None
            self.lora_page = 0
            self._show_category_step()
            await interaction.response.edit_message(
                content="🎨 **Select a LoRA** for your generation:",
                view=self,
            )
        except Exception as e:
            logger.error(f"Back to categories error: {e}", exc_info=True)

    async def _skip_lora(self, interaction: discord.Interaction):
        try:
            await self.final_callback(
                interaction, self.workflow_name, self.workflow,
                self.manifest, self.values, self.message_id,
            )
            self.stop()
        except Exception as e:
            logger.error(f"Skip lora error: {e}", exc_info=True)

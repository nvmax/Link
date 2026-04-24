import discord
from discord import ui
from typing import Dict, Any, List, Callable, Awaitable


class DynamicModal(ui.Modal):
    """Simple text-only modal for prompt-style inputs (max 5 items)."""
    def __init__(self, title: str, inputs: List[Dict[str, Any]],
                 callback: Callable[[discord.Interaction, Dict[str, Any]], Awaitable[None]],
                 prefilled: Dict[str, Any] = None):
        super().__init__(title=title)
        self.submit_callback = callback
        self.fields: Dict[str, ui.TextInput] = {}
        prefilled = prefilled or {}

        for input_cfg in inputs:
            if input_cfg.get("type") in ["image_upload", "audio_upload", "select"]:
                continue
            # Skip LoRA fields
            fid = input_cfg["id"]
            if "lora" in fid.lower() or "➕" in fid:
                continue

            label = input_cfg.get("label", fid)[:45]
            default = str(prefilled.get(fid, input_cfg.get("default", "")))
            required = input_cfg.get("required", True)

            text_input = ui.TextInput(
                label=label,
                placeholder=input_cfg.get("placeholder", ""),
                default=default,
                required=required,
                style=discord.TextStyle.paragraph if input_cfg.get("type") in ["text_area", "string"] else discord.TextStyle.short
            )
            self.add_item(text_input)
            self.fields[fid] = text_input

    async def on_submit(self, interaction: discord.Interaction):
        user_values = {fid: field.value for fid, field in self.fields.items()}
        await self.submit_callback(interaction, user_values)


class OptionsView(ui.View):
    """
    Ephemeral options panel shown when the user clicks 'Options'.
    - Select menus for fields with choices (e.g. resolution)
    - A button to open a text modal for freetext fields (e.g. prompt)
    - Confirm button to kick off generation
    LoRA selection is intentionally excluded here — it gets its own picker.
    """

    def __init__(self, inputs: List[Dict[str, Any]], current_values: Dict[str, Any],
                 on_confirm: Callable, workflow_name: str):
        super().__init__(timeout=300)
        self.inputs = inputs
        self.values = current_values.copy()
        self.on_confirm = on_confirm
        self.workflow_name = workflow_name

        # Strip LoRA and upload fields
        self.visible_inputs = [
            cfg for cfg in inputs
            if cfg.get("type") not in ["image_upload", "audio_upload"]
            and "lora" not in cfg["id"].lower()
            and "➕" not in cfg["id"]
        ]

        self._build()

    def _build(self):
        self.clear_items()
        row = 0

        for cfg in self.visible_inputs:
            if cfg.get("type") == "select" and cfg.get("choices"):
                if row > 2:
                    break  # Discord max 5 rows; save rows for buttons
                choices = cfg["choices"][:25]
                current = self.values.get(cfg["id"], choices[0])

                options = [
                    discord.SelectOption(
                        label=c[:100],
                        value=c[:100],
                        default=(c == current)
                    )
                    for c in choices
                ]

                sel = _FieldSelect(
                    field_id=cfg["id"],
                    placeholder=cfg.get("label", cfg["id"])[:150],
                    options=options,
                    row=row,
                )
                self.add_item(sel)
                row += 1

        # Text fields button (prompt etc.)
        text_fields = [c for c in self.visible_inputs if c.get("type") not in ["select"]]
        if text_fields:
            edit_btn = ui.Button(
                label="✏️ Edit Text Fields",
                style=discord.ButtonStyle.secondary,
                row=row,
            )
            edit_btn.callback = self._open_text_modal
            self.add_item(edit_btn)
            row += 1

        confirm_btn = ui.Button(
            label="✅ Confirm & Generate",
            style=discord.ButtonStyle.success,
            row=row,
        )
        confirm_btn.callback = self._confirm
        self.add_item(confirm_btn)

        cancel_btn = ui.Button(
            label="Cancel",
            style=discord.ButtonStyle.danger,
            row=row,
        )
        cancel_btn.callback = self._cancel
        self.add_item(cancel_btn)

    async def _open_text_modal(self, interaction: discord.Interaction):
        text_fields = [c for c in self.visible_inputs if c.get("type") not in ["select"]]

        async def text_callback(modal_interaction: discord.Interaction, new_vals: dict):
            self.values.update(new_vals)
            # Re-build to keep selects current, then update the ephemeral message
            self._build()
            await modal_interaction.response.edit_message(
                content=self._status_text(),
                view=self,
            )

        modal = DynamicModal(
            title=f"Edit {self.workflow_name}",
            inputs=text_fields,
            callback=text_callback,
            prefilled=self.values,
        )
        await interaction.response.send_modal(modal)

    async def _confirm(self, interaction: discord.Interaction):
        await self.on_confirm(interaction, self.values)
        self.stop()

    async def _cancel(self, interaction: discord.Interaction):
        await interaction.response.edit_message(content="❌ Cancelled.", view=None)
        self.stop()

    def _status_text(self) -> str:
        lines = [f"⚙️ **Options — {self.workflow_name}**"]
        for cfg in self.visible_inputs:
            fid = cfg["id"]
            val = self.values.get(fid, cfg.get("default", "—"))
            lines.append(f"• **{cfg.get('label', fid)}**: {val}")
        return "\n".join(lines)


class _FieldSelect(ui.Select):
    """A Select that writes its chosen value back to the parent OptionsView."""
    def __init__(self, field_id: str, placeholder: str,
                 options: List[discord.SelectOption], row: int):
        self.field_id = field_id
        super().__init__(
            placeholder=placeholder,
            min_values=1,
            max_values=1,
            options=options,
            row=row,
        )

    async def callback(self, interaction: discord.Interaction):
        try:
            ov: OptionsView = self.view
            ov.values[self.field_id] = self.values[0]
            ov._build()
            await interaction.response.edit_message(
                content=ov._status_text(),
                view=ov,
            )
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"FieldSelect error: {e}", exc_info=True)

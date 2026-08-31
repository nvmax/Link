import discord
from discord import ui
from typing import Dict, Any, List, Callable, Awaitable
from src.core.logger import setup_logger

logger = setup_logger(__name__)


class DynamicModal(ui.Modal):
    """Simple text-only modal for prompt-style inputs (max 5 items)."""
    def __init__(self, title: str, inputs: List[Dict[str, Any]],
                 callback: Callable[[discord.Interaction, Dict[str, Any]], Awaitable[None]],
                 prefilled: Dict[str, Any] = None):
        super().__init__(title=(title or "Edit")[:45])
        self.submit_callback = callback
        self.fields: Dict[str, ui.TextInput] = {}
        prefilled = prefilled or {}

        for input_cfg in inputs:
            itype = input_cfg.get("type", "")
            fid = input_cfg.get("id", "")
            fid_lower = fid.lower()
            # Skip all file-upload, inpaint, and select types
            FILE_UPLOAD_TYPES = ["image_upload", "audio_upload", "video_upload", "inpaint", "select", "file", "image", "audio", "video"]
            if itype in FILE_UPLOAD_TYPES:
                continue
            # Skip LoRA fields
            if "lora" in fid_lower or "➕" in fid:
                continue

            # Hard limit: Discord allows max 5 components in a modal
            if len(self.fields) >= 5:
                break

            label = (input_cfg.get("label") or fid or "Field")[:45]
            val = prefilled.get(fid)
            if val is None:
                val = input_cfg.get("default", "")
            default = str(val) if val is not None else ""
            
            # Discord limit for TextInput default/value is 4000 characters
            if len(default) > 4000:
                default = default[:4000]

            placeholder = input_cfg.get("placeholder")
            if placeholder:
                placeholder = str(placeholder)[:100]
            else:
                placeholder = None

            required = bool(input_cfg.get("required", False))

            # Determine text style:
            # Discord TextStyle.short throws 400 Bad Request if default value has ANY newlines (\n).
            # If type is text/prompt/string/text_area, or contains newlines, or is long, use paragraph.
            is_paragraph = (
                input_cfg.get("type") in ["text_area", "string", "text", "prompt", "text_input", "paragraph"]
                or "\n" in default
                or len(default) > 80
                or "prompt" in fid_lower
                or "text" in fid_lower
                or "desc" in fid_lower
            )

            style = discord.TextStyle.paragraph if is_paragraph else discord.TextStyle.short
            # If style is short, sanitize any newlines to avoid Discord 400 Bad Request
            if style == discord.TextStyle.short and "\n" in default:
                default = default.replace("\r\n", " ").replace("\n", " ")

            text_input = ui.TextInput(
                label=label,
                placeholder=placeholder,
                default=default,
                required=required,
                style=style
            )
            self.add_item(text_input)
            self.fields[fid] = text_input

    async def on_submit(self, interaction: discord.Interaction):
        try:
            user_values = {fid: field.value for fid, field in self.fields.items()}
            await self.submit_callback(interaction, user_values)
        except Exception as e:
            logger.error(f"DynamicModal submit error: {e}", exc_info=True)
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(f"❌ Error submitting form: {e}", ephemeral=True)
                else:
                    await interaction.followup.send(f"❌ Error submitting form: {e}", ephemeral=True)
            except Exception:
                pass

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        logger.error(f"DynamicModal error: {error}", exc_info=True)
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(f"❌ Modal error: {error}", ephemeral=True)
            else:
                await interaction.followup.send(f"❌ Modal error: {error}", ephemeral=True)
        except Exception:
            pass


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

        # Strip LoRA, upload, and inpaint fields
        self.visible_inputs = [
            cfg for cfg in inputs
            if cfg.get("type") not in ["image_upload", "audio_upload", "video_upload", "inpaint", "file", "image", "audio", "video"]
            and "lora" not in cfg.get("id", "").lower()
            and "➕" not in cfg.get("id", "")
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
                        label=str(c)[:100],
                        value=str(c)[:100],
                        default=(c == current)
                    )
                    for c in choices
                ]

                sel = _FieldSelect(
                    field_id=cfg["id"],
                    placeholder=(cfg.get("label") or cfg["id"])[:100],
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
        row += 1

        cancel_btn = ui.Button(
            label="Cancel",
            style=discord.ButtonStyle.danger,
            row=row,
        )
        cancel_btn.callback = self._cancel
        self.add_item(cancel_btn)

    async def _open_text_modal(self, interaction: discord.Interaction):
        try:
            text_fields = [c for c in self.visible_inputs if c.get("type") not in ["select"]]

            async def text_callback(modal_interaction: discord.Interaction, new_vals: dict):
                try:
                    self.values.update(new_vals)
                    # Re-build to keep selects current, then update the ephemeral message
                    self._build()
                    await modal_interaction.response.edit_message(
                        content=self._status_text(),
                        view=self,
                    )
                except Exception as e:
                    logger.error(f"Error updating options from modal: {e}", exc_info=True)
                    try:
                        if not modal_interaction.response.is_done():
                            await modal_interaction.response.send_message(f"❌ Failed to update options: {e}", ephemeral=True)
                        else:
                            await modal_interaction.followup.send(f"❌ Failed to update options: {e}", ephemeral=True)
                    except Exception:
                        pass

            modal = DynamicModal(
                title=f"Edit {self.workflow_name}"[:45],
                inputs=text_fields,
                callback=text_callback,
                prefilled=self.values,
            )

            if not modal.fields:
                return await interaction.response.send_message("❌ No editable text fields found.", ephemeral=True)

            await interaction.response.send_modal(modal)
        except Exception as e:
            logger.error(f"Error opening text modal: {e}", exc_info=True)
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(f"❌ Failed to open edit modal: {e}", ephemeral=True)
                else:
                    await interaction.followup.send(f"❌ Failed to open edit modal: {e}", ephemeral=True)
            except Exception:
                pass

    async def _confirm(self, interaction: discord.Interaction):
        try:
            await self.on_confirm(interaction, self.values)
            self.stop()
        except Exception as e:
            logger.error(f"Error in OptionsView._confirm: {e}", exc_info=True)
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(f"❌ Confirmation failed: {e}", ephemeral=True)
                else:
                    await interaction.followup.send(f"❌ Confirmation failed: {e}", ephemeral=True)
            except Exception:
                pass

    async def _cancel(self, interaction: discord.Interaction):
        try:
            await interaction.response.edit_message(content="❌ Cancelled.", view=None)
            self.stop()
        except Exception as e:
            logger.error(f"Error in OptionsView._cancel: {e}", exc_info=True)

    async def on_error(self, interaction: discord.Interaction, error: Exception, item: ui.Item) -> None:
        logger.error(f"OptionsView error on item {item}: {error}", exc_info=True)
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(f"❌ Interaction error: {error}", ephemeral=True)
            else:
                await interaction.followup.send(f"❌ Interaction error: {error}", ephemeral=True)
        except Exception:
            pass

    def _status_text(self) -> str:
        lines = [f"⚙️ **Options — {self.workflow_name}**"]
        for cfg in self.visible_inputs:
            fid = cfg.get("id", "")
            val = self.values.get(fid, cfg.get("default", "—"))
            val_str = str(val) if val is not None else "—"
            if len(val_str) > 250:
                val_str = val_str[:247] + "..."
            lines.append(f"• **{cfg.get('label', fid)}**: {val_str}")
        full_text = "\n".join(lines)
        if len(full_text) > 1950:
            full_text = full_text[:1940] + "\n..."
        return full_text


class _FieldSelect(ui.Select):
    """A Select that writes its chosen value back to the parent OptionsView."""
    def __init__(self, field_id: str, placeholder: str,
                 options: List[discord.SelectOption], row: int):
        self.field_id = field_id
        super().__init__(
            placeholder=(placeholder or "Select option")[:100],
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
            logger.error(f"FieldSelect error: {e}", exc_info=True)
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(f"❌ Selection error: {e}", ephemeral=True)
                else:
                    await interaction.followup.send(f"❌ Selection error: {e}", ephemeral=True)
            except Exception:
                pass


class ChainSelect(ui.Select):
    """Dropdown menu for curated workflow selection."""
    def __init__(self, workflow_names: List[str], job_id: str, callback: Callable):
        self.job_id = job_id
        self.trigger_callback = callback
        self.workflow_names = workflow_names
        
        options = [
            discord.SelectOption(label=name[:100], value=name[:100], emoji="🪄")
            for name in workflow_names[:25]
        ]
        super().__init__(placeholder="Choose a workflow to chain to...", options=options)

    async def callback(self, interaction: discord.Interaction):
        try:
            await self.trigger_callback(interaction, self.values[0], self.job_id)
        except Exception as e:
            logger.error(f"ChainSelect error: {e}", exc_info=True)
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(f"❌ Chain error: {e}", ephemeral=True)
                else:
                    await interaction.followup.send(f"❌ Chain error: {e}", ephemeral=True)
            except Exception:
                pass


class ChainSelectView(ui.View):
    """View containing the workflow selection dropdown."""
    def __init__(self, workflow_names: List[str], job_id: str, callback: Callable, registry=None):
        super().__init__(timeout=120)
        select = ChainSelect(workflow_names, job_id, callback)
        
        if registry:
            refined_options = []
            for name in workflow_names[:25]:
                wf_data = registry.get_workflow(name)
                label = name
                if wf_data:
                    manifest = wf_data.get("manifest", {})
                    # Priority: display_name > workflow_name > discord_command > internal name
                    label = manifest.get("display_name") or manifest.get("workflow_name") or manifest.get("discord_command") or name
                
                refined_options.append(
                    discord.SelectOption(label=label[:100], value=name[:100], emoji="🪄")
                )
            select.options = refined_options
            
        self.add_item(select)

    async def on_error(self, interaction: discord.Interaction, error: Exception, item: ui.Item) -> None:
        logger.error(f"ChainSelectView error: {error}", exc_info=True)
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(f"❌ Interaction error: {error}", ephemeral=True)
            else:
                await interaction.followup.send(f"❌ Interaction error: {error}", ephemeral=True)
        except Exception:
            pass


import unittest
import discord
from src.bot.ui import DynamicModal, OptionsView, _FieldSelect
from src.bot.modals import AIReviewModal
from src.api.workflows import WorkflowRegistry


class TestUIOptionsModal(unittest.TestCase):
    def setUp(self):
        self.registry = WorkflowRegistry()

    def test_dynamic_modal_with_multiline_prompt(self):
        inputs = [
            {"id": "prompt", "type": "text", "label": "prompt", "required": True},
        ]
        multiline_prompt = "A cinematic video of a sunset.\nCamera slowly zooms in.\nGolden hour lighting."
        prefilled = {"prompt": multiline_prompt}

        modal = DynamicModal(
            title="Edit video_ltx2_5_i2v2",
            inputs=inputs,
            callback=None,
            prefilled=prefilled,
        )

        self.assertEqual(len(modal.children), 1)
        text_input = modal.children[0]
        self.assertEqual(text_input.label, "prompt")
        self.assertEqual(text_input.default, multiline_prompt)
        self.assertEqual(text_input.style, discord.TextStyle.paragraph)

        modal_dict = modal.to_dict()
        # Discord TextStyle.paragraph corresponds to type 2 in discord component payload
        self.assertEqual(modal_dict["components"][0]["components"][0]["style"], 2)

    def test_dynamic_modal_discord_limits(self):
        long_title = "A" * 60
        long_label = "B" * 60
        long_placeholder = "C" * 150
        long_default = "D" * 5000

        inputs = [
            {
                "id": f"field_{i}",
                "type": "text",
                "label": long_label,
                "placeholder": long_placeholder,
                "default": long_default,
            }
            for i in range(8)
        ]

        modal = DynamicModal(
            title=long_title,
            inputs=inputs,
            callback=None,
            prefilled=None,
        )

        self.assertLessEqual(len(modal.title), 45)
        self.assertLessEqual(len(modal.children), 5)

        for child in modal.children:
            self.assertLessEqual(len(child.label), 45)
            self.assertLessEqual(len(child.placeholder), 100)
            self.assertLessEqual(len(child.default), 4000)

    def test_dynamic_modal_none_prefilled(self):
        inputs = [
            {"id": "prompt", "type": "text", "label": "prompt", "default": ""},
        ]
        prefilled = {"prompt": None}

        modal = DynamicModal(
            title="Edit Prompt",
            inputs=inputs,
            callback=None,
            prefilled=prefilled,
        )

        self.assertEqual(modal.children[0].default, "")
        self.assertNotEqual(modal.children[0].default, "None")

    def test_options_view_ltx25_manifest(self):
        wf = self.registry.get_workflow("video_ltx2_5_i2v2")
        self.assertIsNotNone(wf)
        manifest = wf["manifest"]
        inputs = manifest.get("inputs", [])

        long_prompt = "A detailed prompt for video generation " * 50
        current_values = {
            "prompt": long_prompt,
            "duration": "10",
            "image": "https://example.com/image.png",
        }

        view = OptionsView(
            inputs=inputs,
            current_values=current_values,
            on_confirm=None,
            workflow_name="video_ltx2_5_i2v2",
        )

        # Ensure image_upload is excluded from visible inputs
        visible_ids = [c["id"] for c in view.visible_inputs]
        self.assertIn("prompt", visible_ids)
        self.assertIn("duration", visible_ids)
        self.assertNotIn("image", visible_ids)

        # Status text must be within Discord 2000-char message limit
        status_text = view._status_text()
        self.assertLess(len(status_text), 2000)
        self.assertIn("Options — video_ltx2_5_i2v2", status_text)

    def test_ai_review_modal_limits(self):
        long_content = "X" * 6000
        modal = AIReviewModal(
            title="AI Enhancement " * 5,
            prompt_label="Prompt Label " * 5,
            initial_content=long_content,
            callback=None,
        )

        self.assertLessEqual(len(modal.title), 45)
        self.assertLessEqual(len(modal.prompt_input.label), 45)
        self.assertLessEqual(len(modal.prompt_input.default), 4000)
        self.assertEqual(modal.prompt_input.style, discord.TextStyle.paragraph)


if __name__ == "__main__":
    unittest.main()

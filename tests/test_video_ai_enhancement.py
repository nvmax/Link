import unittest
from unittest.mock import AsyncMock, MagicMock, patch
import os
import asyncio

from src.core.utils import CapturedFile
from src.bot.cogs.generation import GenerationCog
from src.core.config import Config

class TestVideoAIEnhancement(unittest.IsolatedAsyncioTestCase):
    async def test_video_modality_auto_enhances_with_image(self):
        bot = MagicMock()
        cog = GenerationCog(bot)

        # Mock workflow manifest with category: video
        mock_manifest = {
            "workflow_name": "video_ltx2_5_i2v2",
            "display_name": "LTX 2.5",
            "inputs": [
                {"id": "image", "type": "image_upload", "required": True},
                {"id": "prompt", "type": "text", "required": True}
            ],
            "ai_prompt": {
                "enabled": True,
                "category": "video",
                "prompt_id": "prompt-1787071640300",
                "target_input": "prompt",
                "include_image": True,
                "target_image": "image"
            },
            "discord": {
                "inputs": [
                    {"id": "image", "type": "image_upload", "required": True},
                    {"id": "prompt", "type": "text", "required": True}
                ]
            }
        }
        
        bot.workflow_registry.get_workflow.return_value = {
            "manifest": mock_manifest,
            "workflow": {}
        }

        mock_interaction = MagicMock()
        mock_interaction.guild = None
        mock_interaction.channel_id = "12345"
        mock_interaction.user.id = "user123"
        mock_interaction.user.display_name = "TestUser"
        mock_interaction.response.is_done.return_value = True
        mock_interaction.followup.send = AsyncMock()

        fake_image_bytes = b'\x89PNG\r\n\x1a\nfake-keyframe-data'
        user_values = {
            "image": CapturedFile(fake_image_bytes, "anchor.png"),
            "prompt": "The character turns and speaks."
        }

        with patch("src.bot.cogs.generation.AiService") as MockAiService, \
             patch.object(cog, "_execute_generation", new_callable=AsyncMock) as mock_exec_gen, \
             patch.object(Config, "ALLOWED_CHANNEL_IDS", []):
            
            mock_ai_instance = MagicMock()
            mock_ai_instance.enhance_prompt = AsyncMock(return_value="[ENHANCED]: Highly detailed camera movement with dialogue.")
            MockAiService.return_value = mock_ai_instance

            await cog.handle_generation_request(
                mock_interaction,
                "video_ltx2_5_i2v2",
                user_values=user_values
            )

            # 1. Verify enhance_prompt was called automatically
            mock_ai_instance.enhance_prompt.assert_called_once()
            call_args = mock_ai_instance.enhance_prompt.call_args
            prompt_arg = call_args[0][0]
            prompt_id_arg = call_args[0][1]
            image_kwarg = call_args[1].get("image_data")

            self.assertEqual(prompt_arg, "The character turns and speaks.")
            self.assertEqual(prompt_id_arg, "prompt-1787071640300")
            self.assertEqual(image_kwarg, fake_image_bytes)

            # 2. Verify generation proceeded directly with enhanced prompt
            mock_exec_gen.assert_called_once()
            exec_values = mock_exec_gen.call_args[0][4]
            self.assertEqual(exec_values["prompt"], "[ENHANCED]: Highly detailed camera movement with dialogue.")

if __name__ == "__main__":
    unittest.main()

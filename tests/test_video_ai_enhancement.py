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

    async def test_video_auto_false_user_declines(self):
        """When auto is False, bot must ask user. If user declines, prompt is not changed and generation proceeds."""
        bot = MagicMock()
        cog = GenerationCog(bot)

        mock_manifest = {
            "workflow_name": "video_ltx2_5_i2v2",
            "display_name": "LTX 2.5",
            "inputs": [
                {"id": "image", "type": "image_upload", "required": True},
                {"id": "prompt", "type": "text", "required": True}
            ],
            "ai_prompt": {
                "enabled": True,
                "auto": False,  # Ask User mode!
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
            "prompt": "The original user prompt remains intact."
        }

        with patch("src.bot.cogs.generation.AiService") as MockAiService, \
             patch.object(cog, "_execute_generation", new_callable=AsyncMock) as mock_exec_gen, \
             patch.object(Config, "ALLOWED_CHANNEL_IDS", []):
            
            mock_ai_instance = MagicMock()
            mock_ai_instance.enhance_prompt = AsyncMock()
            MockAiService.return_value = mock_ai_instance

            await cog.handle_generation_request(
                mock_interaction,
                "video_ltx2_5_i2v2",
                user_values=user_values
            )

            # 1. Verify enhance_prompt was NOT called automatically
            mock_ai_instance.enhance_prompt.assert_not_called()

            # 2. Verify AIQueryView was sent asking the user
            mock_interaction.followup.send.assert_called_once()
            call_kwargs = mock_interaction.followup.send.call_args[1]
            view = call_kwargs.get("view")
            self.assertIsNotNone(view)

            # 3. Simulate user clicking "No, Keep Original"
            button_interaction = MagicMock()
            button_interaction.user.id = "user123"
            button_interaction.response.edit_message = AsyncMock()

            await view.no_skip(button_interaction)

            # 4. Verify enhance_prompt was still NOT called
            mock_ai_instance.enhance_prompt.assert_not_called()

            # 5. Verify generation proceeded with original unchanged prompt
            mock_exec_gen.assert_called_once()
            exec_values = mock_exec_gen.call_args[0][4]
            self.assertEqual(exec_values["prompt"], "The original user prompt remains intact.")

    async def test_video_auto_false_user_enhances_and_generates(self):
        """When auto is False and user clicks enhance, prompt is enhanced and review view offers Generate Now."""
        bot = MagicMock()
        cog = GenerationCog(bot)

        mock_manifest = {
            "workflow_name": "video_ltx2_5_i2v2",
            "display_name": "LTX 2.5",
            "inputs": [
                {"id": "image", "type": "image_upload", "required": True},
                {"id": "prompt", "type": "text", "required": True}
            ],
            "ai_prompt": {
                "enabled": True,
                "auto": False,
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
            "prompt": "Camera pans slowly across the mountain."
        }

        with patch("src.bot.cogs.generation.AiService") as MockAiService, \
             patch.object(cog, "_execute_generation", new_callable=AsyncMock) as mock_exec_gen, \
             patch.object(Config, "ALLOWED_CHANNEL_IDS", []):
            
            mock_ai_instance = MagicMock()
            mock_ai_instance.enhance_prompt = AsyncMock(return_value="[ENHANCED]: Epic cinematic sweeping drone shot.")
            MockAiService.return_value = mock_ai_instance

            await cog.handle_generation_request(
                mock_interaction,
                "video_ltx2_5_i2v2",
                user_values=user_values
            )

            # 1. Query view sent
            view = mock_interaction.followup.send.call_args[1].get("view")
            self.assertIsNotNone(view)

            # 2. User clicks enhance with image
            btn_inter = MagicMock()
            btn_inter.user.id = "user123"
            btn_inter.response.is_done.return_value = True
            btn_inter.response.edit_message = AsyncMock()
            btn_inter.edit_original_response = AsyncMock()

            await view.enhance_with_img(btn_inter)

            # 3. Enhance called with image
            mock_ai_instance.enhance_prompt.assert_called_once()
            self.assertEqual(mock_ai_instance.enhance_prompt.call_args[1]["image_data"], fake_image_bytes)

            # 4. Review view presented
            btn_inter.edit_original_response.assert_called_once()
            review_view = btn_inter.edit_original_response.call_args[1].get("view")
            self.assertIsNotNone(review_view)

            # 5. User clicks Generate Now
            gen_btn_inter = MagicMock()
            gen_btn_inter.user.id = "user123"
            gen_btn_inter.response.edit_message = AsyncMock()

            await review_view.generate_now.callback(gen_btn_inter)

            # 6. Generation ran with enhanced prompt
            mock_exec_gen.assert_called_once()
            exec_values = mock_exec_gen.call_args[0][4]
            self.assertEqual(exec_values["prompt"], "[ENHANCED]: Epic cinematic sweeping drone shot.")

    async def test_video_auto_explicit_true(self):
        """When auto is explicitly True, it enhances and proceeds directly without asking."""
        bot = MagicMock()
        cog = GenerationCog(bot)

        mock_manifest = {
            "workflow_name": "video_ltx2_5_i2v2",
            "display_name": "LTX 2.5",
            "inputs": [
                {"id": "prompt", "type": "text", "required": True}
            ],
            "ai_prompt": {
                "enabled": True,
                "auto": True,
                "category": "video",
                "prompt_id": "prompt-1787071640300",
                "target_input": "prompt"
            },
            "discord": {
                "inputs": [
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

        user_values = {"prompt": "Sunset over ocean."}

        with patch("src.bot.cogs.generation.AiService") as MockAiService, \
             patch.object(cog, "_execute_generation", new_callable=AsyncMock) as mock_exec_gen, \
             patch.object(Config, "ALLOWED_CHANNEL_IDS", []):
            
            mock_ai_instance = MagicMock()
            mock_ai_instance.enhance_prompt = AsyncMock(return_value="[ENHANCED]: Golden hour reflections on gentle waves.")
            MockAiService.return_value = mock_ai_instance

            await cog.handle_generation_request(
                mock_interaction,
                "video_ltx2_5_i2v2",
                user_values=user_values
            )

            mock_ai_instance.enhance_prompt.assert_called_once()
            mock_exec_gen.assert_called_once()
            exec_values = mock_exec_gen.call_args[0][4]
            self.assertEqual(exec_values["prompt"], "[ENHANCED]: Golden hour reflections on gentle waves.")

    async def test_video_auto_false_user_enhances_and_uses_original(self):
        """When auto is False and user clicks enhance but chooses 'Use Original' on review, original prompt is used."""
        bot = MagicMock()
        cog = GenerationCog(bot)

        mock_manifest = {
            "workflow_name": "video_ltx2_5_i2v2",
            "display_name": "LTX 2.5",
            "inputs": [
                {"id": "prompt", "type": "text", "required": True}
            ],
            "ai_prompt": {
                "enabled": True,
                "auto": False,
                "category": "video",
                "prompt_id": "prompt-1787071640300",
                "target_input": "prompt"
            },
            "discord": {
                "inputs": [
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

        user_values = {"prompt": "My custom unenhanced prompt."}

        with patch("src.bot.cogs.generation.AiService") as MockAiService, \
             patch.object(cog, "_execute_generation", new_callable=AsyncMock) as mock_exec_gen, \
             patch.object(Config, "ALLOWED_CHANNEL_IDS", []):
            
            mock_ai_instance = MagicMock()
            mock_ai_instance.enhance_prompt = AsyncMock(return_value="[ENHANCED]: Too fancy description.")
            MockAiService.return_value = mock_ai_instance

            await cog.handle_generation_request(
                mock_interaction,
                "video_ltx2_5_i2v2",
                user_values=user_values
            )

            view = mock_interaction.followup.send.call_args[1].get("view")
            
            # User clicks enhance
            btn_inter = MagicMock()
            btn_inter.user.id = "user123"
            btn_inter.response.is_done.return_value = True
            btn_inter.response.edit_message = AsyncMock()
            btn_inter.edit_original_response = AsyncMock()

            await view.enhance_text_only(btn_inter)

            # Review view presented
            review_view = btn_inter.edit_original_response.call_args[1].get("view")

            # User clicks "Use Original"
            use_orig_btn_inter = MagicMock()
            use_orig_btn_inter.user.id = "user123"
            use_orig_btn_inter.response.edit_message = AsyncMock()

            await review_view.use_original.callback(use_orig_btn_inter)

            mock_exec_gen.assert_called_once()
            exec_values = mock_exec_gen.call_args[0][4]
            self.assertEqual(exec_values["prompt"], "My custom unenhanced prompt.")

if __name__ == "__main__":
    unittest.main()

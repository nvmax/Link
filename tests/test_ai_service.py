import unittest
import base64
from unittest.mock import patch, AsyncMock
from src.api.ai_service import AiService, _normalize_image
from src.api.ai_models import AIConfig, SystemPrompt

class TestAiService(unittest.IsolatedAsyncioTestCase):
    def test_normalize_image_bytes(self):
        png_bytes = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR'
        data_url, raw_b64, mime = _normalize_image(png_bytes)
        self.assertEqual(mime, "image/png")
        self.assertTrue(data_url.startswith("data:image/png;base64,"))
        self.assertEqual(raw_b64, base64.b64encode(png_bytes).decode('utf-8'))

        jpg_bytes = b'\xff\xd8\xff\xe0\x00\x10JFIF'
        data_url, raw_b64, mime = _normalize_image(jpg_bytes)
        self.assertEqual(mime, "image/jpeg")
        self.assertTrue(data_url.startswith("data:image/jpeg;base64,"))

    def test_normalize_image_data_url(self):
        data_url_in = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        data_url, raw_b64, mime = _normalize_image(data_url_in)
        self.assertEqual(mime, "image/png")
        self.assertEqual(data_url, data_url_in)
        self.assertTrue(raw_b64.startswith("iVBORw0KGgo"))

    async def test_enhance_prompt_with_image_openai_format(self):
        service = AiService()
        
        mock_config = AIConfig(
            active_provider="gemini",
            providers={
                "gemini": {"model": "gemini-1.5-flash", "active": True, "base_url": None}
            }
        )
        mock_prompts = [
            SystemPrompt(id="test-prompt", name="Test", category="video", content="You are a cinematographer.")
        ]
        
        with patch.object(service, 'load_config', return_value=mock_config), \
             patch.object(service, 'load_prompts', return_value=mock_prompts), \
             patch('aiohttp.ClientSession.post') as mock_post:
            
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={
                "choices": [{"message": {"content": "Enhanced cinematic prompt with keyframe anchor."}}]
            })
            mock_post.return_value.__aenter__.return_value = mock_response
            
            test_img = b'\x89PNG\r\n\x1a\nfakeimage'
            result = await service.enhance_prompt(
                user_prompt="A man speaking into microphone",
                system_prompt_id="test-prompt",
                image_data=test_img
            )
            
            self.assertEqual(result, "Enhanced cinematic prompt with keyframe anchor.")
            
            # Verify the payload sent to the LLM
            call_kwargs = mock_post.call_args[1]
            payload = call_kwargs["json"]
            self.assertEqual(payload["model"], "gemini-1.5-flash")
            messages = payload["messages"]
            self.assertEqual(len(messages), 2)
            self.assertEqual(messages[0]["role"], "system")
            self.assertEqual(messages[1]["role"], "user")
            
            user_content = messages[1]["content"]
            self.assertIsInstance(user_content, list)
            self.assertEqual(user_content[0]["type"], "text")
            self.assertEqual(user_content[0]["text"], "A man speaking into microphone")
            self.assertEqual(user_content[1]["type"], "image_url")
            self.assertTrue(user_content[1]["image_url"]["url"].startswith("data:image/png;base64,"))

    async def test_enhance_prompt_with_image_anthropic_format(self):
        service = AiService()
        
        mock_config = AIConfig(
            active_provider="anthropic",
            providers={
                "anthropic": {"model": "claude-3-5-sonnet-20241022", "active": True, "base_url": "https://api.anthropic.com/v1"}
            }
        )
        mock_prompts = [
            SystemPrompt(id="test-prompt", name="Test", category="video", content="You are a video expert.")
        ]
        
        with patch.object(service, 'load_config', return_value=mock_config), \
             patch.object(service, 'load_prompts', return_value=mock_prompts), \
             patch('aiohttp.ClientSession.post') as mock_post:
            
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={
                "content": [{"text": "Anthropic enhanced prompt"}]
            })
            mock_post.return_value.__aenter__.return_value = mock_response
            
            test_img = b'\xff\xd8\xff\xe0fakejpeg'
            result = await service.enhance_prompt(
                user_prompt="Camera moves forward",
                system_prompt_id="test-prompt",
                image_data=test_img
            )
            
            self.assertEqual(result, "Anthropic enhanced prompt")
            call_kwargs = mock_post.call_args[1]
            payload = call_kwargs["json"]
            self.assertEqual(payload["model"], "claude-3-5-sonnet-20241022")
            user_content = payload["messages"][0]["content"]
            self.assertEqual(user_content[0]["type"], "image")
            self.assertEqual(user_content[0]["source"]["type"], "base64")
            self.assertEqual(user_content[0]["source"]["media_type"], "image/jpeg")
            self.assertEqual(user_content[1]["type"], "text")

if __name__ == '__main__':
    unittest.main()

import aiohttp
import yaml
import json
import os
from typing import Optional, List, Dict
from src.core.config import Config
from src.api.ai_models import AIConfig, SystemPrompt

import base64
import mimetypes

def _normalize_image(image_data: bytes | str) -> tuple[str, str, str]:
    """
    Returns (data_url, raw_base64, mime_type).
    """
    if isinstance(image_data, bytes):
        if image_data.startswith(b'\x89PNG\r\n\x1a\n'):
            mime_type = "image/png"
        elif image_data.startswith(b'\xff\xd8\xff'):
            mime_type = "image/jpeg"
        elif image_data.startswith(b'RIFF') and b'WEBP' in image_data[:12]:
            mime_type = "image/webp"
        elif image_data.startswith(b'GIF87a') or image_data.startswith(b'GIF89a'):
            mime_type = "image/gif"
        else:
            mime_type = "image/jpeg"
        
        raw_b64 = base64.b64encode(image_data).decode('utf-8')
        data_url = f"data:{mime_type};base64,{raw_b64}"
        return data_url, raw_b64, mime_type
        
    elif isinstance(image_data, str):
        if image_data.startswith("data:"):
            header, b64 = image_data.split(",", 1)
            mime_type = header.split(";")[0].replace("data:", "") or "image/jpeg"
            return image_data, b64, mime_type
        elif image_data.startswith("http://") or image_data.startswith("https://"):
            return image_data, "", "image/jpeg"
        else:
            raw_b64 = image_data.strip()
            mime_type = "image/jpeg"
            data_url = f"data:{mime_type};base64,{raw_b64}"
            return data_url, raw_b64, mime_type
    return "", "", "image/jpeg"

class AiService:
    def __init__(self):
        self.config_path = os.path.join(Config.AI_STUDIO_DIR, "ai_config.yaml")
        self.prompts_path = os.path.join(Config.AI_STUDIO_DIR, "prompts.json")

    def load_config(self) -> AIConfig:
        if not os.path.exists(self.config_path):
            return AIConfig(
                active_provider="ollama", 
                providers={"ollama": {"model": "llama3:8b", "active": True}}
            )
        with open(self.config_path, 'r') as f:
            data = yaml.safe_load(f)
            return AIConfig(**data)

    def save_config(self, config: Dict):
        with open(self.config_path, 'w') as f:
            yaml.dump(config, f)

    def load_prompts(self) -> List[SystemPrompt]:
        if not os.path.exists(self.prompts_path): return []
        with open(self.prompts_path, 'r') as f:
            try:
                data = json.load(f)
                return [SystemPrompt(**p) for p in data]
            except json.JSONDecodeError:
                return []

    def save_prompts(self, prompts: List[Dict]):
        with open(self.prompts_path, 'w') as f:
            json.dump(prompts, f, indent=2)

    async def enhance_prompt(self, user_prompt: str, system_prompt_id: str, image_data: Optional[bytes | str] = None) -> str:
        config = self.load_config()
        prompts = self.load_prompts()
        system_prompt = next((p for p in prompts if p.id == system_prompt_id), None)
        
        if not system_prompt:
            raise ValueError(f"System prompt {system_prompt_id} not found")

        provider_id = config.active_provider
        provider_cfg = config.providers.get(provider_id)
        
        if not provider_cfg:
            raise ValueError(f"Provider {provider_id} configuration not found")

        # Get API Key from env
        env_key = f"{provider_id.upper()}_API_KEY"
        api_key = os.getenv(env_key, "")
        
        async with aiohttp.ClientSession() as session:
            url = provider_cfg.base_url
            if not url:
                if provider_id == "openai": url = "https://api.openai.com/v1"
                elif provider_id == "gemini": url = "https://generativelanguage.googleapis.com/v1beta/openai"
                elif provider_id == "anthropic": url = "https://api.anthropic.com/v1"
                elif provider_id == "grok": url = "https://api.x.ai/v1"
                else: url = "http://localhost:11434/v1"

            # Check if Anthropic direct API vs standard OpenAI chat/completions
            is_anthropic_direct = (provider_id == "anthropic" and "api.anthropic.com" in url)
            
            if is_anthropic_direct:
                chat_url = f"{url.rstrip('/')}/messages"
                headers = {
                    "Content-Type": "application/json",
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01"
                }
                user_content = []
                if image_data:
                    data_url, raw_b64, mime_type = _normalize_image(image_data)
                    if raw_b64:
                        user_content.append({
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": mime_type,
                                "data": raw_b64
                            }
                        })
                user_content.append({"type": "text", "text": user_prompt})
                
                payload = {
                    "model": provider_cfg.model,
                    "system": system_prompt.content,
                    "messages": [
                        {"role": "user", "content": user_content}
                    ],
                    "max_tokens": 1500,
                    "temperature": 0.7
                }
                async with session.post(chat_url, json=payload, headers=headers) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        raise Exception(f"Anthropic error ({resp.status}): {error_text}")
                    data = await resp.json()
                    return data['content'][0]['text']

            # OpenAI / Gemini / Grok / LM Studio / Ollama / vLLM (OpenAI-compatible format)
            chat_url = f"{url.rstrip('/')}/chat/completions"
            headers = {
                "Content-Type": "application/json"
            }
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            
            if image_data:
                data_url, raw_b64, mime_type = _normalize_image(image_data)
                user_content = [
                    {"type": "text", "text": user_prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": data_url
                        }
                    }
                ]
            else:
                user_content = user_prompt

            payload = {
                "model": provider_cfg.model,
                "messages": [
                    {"role": "system", "content": system_prompt.content},
                    {"role": "user", "content": user_content}
                ],
                "temperature": 0.7
            }
            
            async with session.post(chat_url, json=payload, headers=headers) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    raise Exception(f"AI Provider error ({resp.status}): {error_text}")
                
                data = await resp.json()
                return data['choices'][0]['message']['content']

    async def test_connection(self) -> str:
        config = self.load_config()
        provider_id = config.active_provider
        provider_cfg = config.providers.get(provider_id)
        
        if not provider_cfg:
            raise ValueError(f"Provider {provider_id} configuration not found")

        env_key = f"{provider_id.upper()}_API_KEY"
        api_key = os.getenv(env_key, "")
        
        async with aiohttp.ClientSession() as session:
            url = provider_cfg.base_url
            if not url:
                if provider_id == "openai": url = "https://api.openai.com/v1"
                elif provider_id == "gemini": url = "https://generativelanguage.googleapis.com/v1beta/openai"
                elif provider_id == "anthropic": url = "https://api.anthropic.com/v1" # Note: Anthropic might need a special adapter if not using OpenAI-compatible proxy
                else: url = "http://localhost:11434/v1" # Default fallback

            chat_url = f"{url.rstrip('/')}/chat/completions"
            headers = {"Content-Type": "application/json"}
            if api_key: headers["Authorization"] = f"Bearer {api_key}"
            
            payload = {
                "model": provider_cfg.model,
                "messages": [{"role": "user", "content": "Respond with only 'Connected!'. No other text."}],
                "max_tokens": 10
            }
            
            async with session.post(chat_url, json=payload, headers=headers) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    raise Exception(f"AI Provider error ({resp.status}): {error_text}")
                data = await resp.json()
                return data['choices'][0]['message']['content']

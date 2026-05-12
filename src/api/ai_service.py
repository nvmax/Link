import aiohttp
import yaml
import json
import os
from typing import Optional, List, Dict
from src.core.config import Config
from src.api.ai_models import AIConfig, SystemPrompt

class AiService:
    def __init__(self):
        self.config_path = os.path.join(Config.AI_STUDIO_DIR, "ai_config.yaml")
        self.prompts_path = os.path.join(Config.AI_STUDIO_DIR, "prompts.json")

    def load_config(self) -> AIConfig:
        if not os.path.exists(self.config_path):
            # Return a default config if file doesn't exist
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

    async def enhance_prompt(self, user_prompt: str, system_prompt_id: str) -> str:
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
        # Convention: OPENAI_API_KEY, GEMINI_API_KEY, etc.
        env_key = f"{provider_id.upper()}_API_KEY"
        api_key = os.getenv(env_key, "")
        
        async with aiohttp.ClientSession() as session:
            url = provider_cfg.base_url
            if not url:
                if provider_id == "openai": url = "https://api.openai.com/v1"
                elif provider_id == "gemini": url = "https://generativelanguage.googleapis.com/v1beta/openai"
                elif provider_id == "anthropic": url = "https://api.anthropic.com/v1"
                else: url = "http://localhost:11434/v1"

            chat_url = f"{url.rstrip('/')}/chat/completions"
            
            headers = {
                "Content-Type": "application/json"
            }
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            
            payload = {
                "model": provider_cfg.model,
                "messages": [
                    {"role": "system", "content": system_prompt.content},
                    {"role": "user", "content": user_prompt}
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

import aiohttp
import json
import uuid
import os
from typing import Dict, Any, Optional
from src.core.config import Config
from src.core.logger import setup_logger

logger = setup_logger(__name__)

class ComfyClient:
    def __init__(self, base_url: str = Config.COMFY_URL):
        self.base_url = base_url
        self.client_id = str(uuid.uuid4())
        self.session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()

    async def upload_file(self, attachment, overwrite: bool = True) -> str:
        session = await self._get_session()
        file_bytes = await attachment.read()
        data = aiohttp.FormData()
        data.add_field('image', file_bytes, filename=attachment.filename)
        data.add_field('overwrite', str(overwrite).lower())
        
        async with session.post(f"{self.base_url}/upload/image", data=data) as resp:
            result = await resp.json()
            return result.get("name")

    async def queue_prompt(self, prompt: Dict[str, Any], client_id: str) -> str:
        session = await self._get_session()
        payload = {
            "prompt": prompt,
            "client_id": client_id
        }
        async with session.post(f"{self.base_url}/prompt", json=payload) as resp:
            result = await resp.json()
            logger.info(f"ComfyUI /prompt response: {result}")
            return result.get("prompt_id")

    async def get_history(self, prompt_id: str) -> Dict[str, Any]:
        session = await self._get_session()
        async with session.get(f"{self.base_url}/history/{prompt_id}") as resp:
            return await resp.json()

    async def get_image(self, filename: str, subfolder: str = "", folder_type: str = "output") -> bytes:
        session = await self._get_session()
        params = {
            "filename": filename,
            "subfolder": subfolder,
            "type": folder_type
        }
        async with session.get(f"{self.base_url}/view", params=params) as resp:
            return await resp.read()

    async def get_object_info(self) -> Dict[str, Any]:
        """Fetches metadata for all available nodes in ComfyUI, including their display names."""
        session = await self._get_session()
        async with session.get(f"{self.base_url}/object_info") as resp:
            return await resp.json()

    async def check_connection(self) -> bool:
        """Verifies if the ComfyUI backend is reachable."""
        try:
            session = await self._get_session()
            async with session.get(f"{self.base_url}/system_stats", timeout=2) as resp:
                return resp.status == 200
        except Exception:
            return False


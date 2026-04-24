import asyncio
import websockets
import json
from typing import Callable, Awaitable, Dict, Any
from src.core.config import Config
from src.core.logger import setup_logger

logger = setup_logger(__name__)

class ComfyWebSocket:
    def __init__(self, uri: str = Config.COMFY_WS_URL, client_id: str = None):
        self.uri = f"{uri}?clientId={client_id}" if client_id else uri
        self.client_id = client_id
        self.ws = None
        self.handlers: Dict[str, Callable[[Dict[str, Any]], Awaitable[None]]] = {}

    def register_handler(self, event_type: str, handler: Callable[[Dict[str, Any]], Awaitable[None]]):
        self.handlers[event_type] = handler

    async def connect(self):
        while True:
            try:
                async with websockets.connect(self.uri) as ws:
                    self.ws = ws
                    logger.info(f"Connected to ComfyUI WebSocket at {self.uri}")
                    async for message in ws:
                        if isinstance(message, str):
                            data = json.loads(message)
                            event_type = data.get("type")
                            if event_type in self.handlers:
                                # Pass the full message so handlers can see top-level fields like prompt_id
                                await self.handlers[event_type](data)
            except Exception as e:
                logger.error(f"WebSocket error: {e}. Retrying in 5s...")
                await asyncio.sleep(5)

    async def listen(self):
        await self.connect()

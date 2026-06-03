import asyncio
from typing import Callable, Any, Dict

class CacheManager:
    def __init__(self):
        self._cache: Dict[str, tuple[Any, float]] = {}

    async def get_or_set(self, key: str, fetch_fn: Callable[[], Any], ttl: int = 300) -> Any:
        loop = asyncio.get_event_loop()
        now = loop.time()
        
        if key in self._cache:
            value, expiry = self._cache[key]
            if now < expiry:
                return value
        
        if asyncio.iscoroutinefunction(fetch_fn):
            value = await fetch_fn()
        else:
            value = fetch_fn()
            if asyncio.iscoroutine(value):
                value = await value
                
        self._cache[key] = (value, now + ttl)
        return value

    def clear(self):
        self._cache.clear()

cache = CacheManager()

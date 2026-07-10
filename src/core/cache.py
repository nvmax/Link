import asyncio
from typing import Callable, Any, Dict

class CacheManager:
    def __init__(self, max_size: int = 1000):
        self._cache: Dict[str, tuple[Any, float]] = {}
        self.max_size = max_size

    async def get_or_set(self, key: str, fetch_fn: Callable[[], Any], ttl: int = 300, cache_none: bool = False) -> Any:
        loop = asyncio.get_event_loop()
        now = loop.time()
        
        # Evict expired entries to free memory
        expired_keys = [k for k, (_, expiry) in self._cache.items() if now >= expiry]
        for k in expired_keys:
            self._cache.pop(k, None)
            
        if key in self._cache:
            value, expiry = self._cache[key]
            if now < expiry:
                # Refresh LRU position by popping and re-inserting at the end
                self._cache.pop(key)
                self._cache[key] = (value, expiry)
                return value
        
        if asyncio.iscoroutinefunction(fetch_fn):
            value = await fetch_fn()
        else:
            value = fetch_fn()
            if asyncio.iscoroutine(value):
                value = await value
                
        # Enforce max size limit: if full, evict the oldest insertion (first key in dict)
        if len(self._cache) >= self.max_size:
            oldest_key = next(iter(self._cache))
            self._cache.pop(oldest_key, None)
            
        # By default, do not cache None/falsy results — a failed lookup should
        # always be retried next time rather than locking the caller out for TTL.
        if value is None and not cache_none:
            return value

        self._cache[key] = (value, now + ttl)
        return value

    def clear(self):
        self._cache.clear()

    def delete(self, key: str) -> bool:
        """Remove a single key. Returns True if it existed."""
        return self._cache.pop(key, None) is not None

cache = CacheManager()

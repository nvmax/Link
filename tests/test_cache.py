import pytest
import asyncio
from src.core.cache import CacheManager

@pytest.mark.anyio
async def test_cache_expiration():
    cache = CacheManager()
    
    call_count = 0
    async def fetch():
        nonlocal call_count
        call_count += 1
        return f"val_{call_count}"

    # First fetch should call the function
    res1 = await cache.get_or_set("key1", fetch, ttl=1)
    assert res1 == "val_1"
    assert call_count == 1

    # Second fetch before TTL should hit cache
    res2 = await cache.get_or_set("key1", fetch, ttl=1)
    assert res2 == "val_1"
    assert call_count == 1

    # Wait for expiration (loop time based, so we sleep)
    await asyncio.sleep(1.1)

    # Third fetch after TTL should fetch again
    res3 = await cache.get_or_set("key1", fetch, ttl=1)
    assert res3 == "val_2"
    assert call_count == 2

@pytest.mark.anyio
async def test_cache_max_size_eviction():
    # Cache with max size of 2
    cache = CacheManager(max_size=2)
    
    async def fetch_val(v):
        return v

    await cache.get_or_set("a", lambda: fetch_val("a_val"), ttl=100)
    await cache.get_or_set("b", lambda: fetch_val("b_val"), ttl=100)
    
    assert "a" in cache._cache
    assert "b" in cache._cache

    # Setting "c" should evict the oldest "a"
    await cache.get_or_set("c", lambda: fetch_val("c_val"), ttl=100)
    
    assert "a" not in cache._cache
    assert "b" in cache._cache
    assert "c" in cache._cache

@pytest.mark.anyio
async def test_cache_lru_hit_ordering():
    # Cache with max size of 2
    cache = CacheManager(max_size=2)
    
    async def fetch_val(v):
        return v

    await cache.get_or_set("a", lambda: fetch_val("a_val"), ttl=100)
    await cache.get_or_set("b", lambda: fetch_val("b_val"), ttl=100)
    
    # Hit "a" to refresh its LRU position (making "b" the oldest)
    await cache.get_or_set("a", lambda: fetch_val("a_val"), ttl=100)
    
    # Setting "c" should now evict "b" instead of "a"
    await cache.get_or_set("c", lambda: fetch_val("c_val"), ttl=100)
    
    assert "b" not in cache._cache
    assert "a" in cache._cache
    assert "c" in cache._cache

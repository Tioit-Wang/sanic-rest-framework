from rest_framework.cache.backends.base import BaseCache
import redis.asyncio as redis

DEFAULT_TIMEOUT = 300
CACHE_MAX_ENTRIES = 300
DEFAULT_VERSION = 1


class RedisCache(BaseCache):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "password" in self.options:
            url_str = f"redis://:{self.options['password']}@{self.options['host']}:{self.options['port']}/{self.options['db']}"
        else:
            url_str = f"redis://{self.options['host']}:{self.options['port']}/{self.options['db']}"
        self.client: redis.Redis = redis.Redis(connection_pool=redis.ConnectionPool.from_url(url_str, decode_responses=True))

    async def add(self, key, value, timeout=DEFAULT_TIMEOUT, version=None):
        key = self.make_cache_key(key, version)
        if await self.client.setnx(key, value):
            if timeout != 0:
                await self.client.expire(key, timeout)
            return True
        return False

    async def get(self, key, default=None, version=None):
        key = self.make_cache_key(key, version)
        value = await self.client.get(key)
        return value if value is not None else default

    async def set(self, key, value, timeout=DEFAULT_TIMEOUT, version=None):
        key = self.make_cache_key(key, version)
        await self.client.set(key, value, ex=timeout)

    async def touch(self, key, timeout=DEFAULT_TIMEOUT, version=None):
        key = self.make_cache_key(key, version)
        return await self.client.expire(key, timeout)

    async def delete(self, key, version=None):
        key = self.make_cache_key(key, version)
        return await self.client.delete(key)

    async def incr(self, key, delta=1, version=None):
        key = self.make_cache_key(key, version)
        return await self.client.incrby(key, delta)

    async def clear(self):
        await self.client.flushdb()

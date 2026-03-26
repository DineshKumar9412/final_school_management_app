# database/redis_cache.py
import os
import json
import redis.asyncio as redis
from typing import Optional, Any

class RedisCache:
    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        db: Optional[int] = None,
        password: Optional[str] = None,
        decode_responses: Optional[bool] = True
    ):
        self.host = host or os.getenv("REDIS_HOST", "127.0.0.1")
        self.port = port or int(os.getenv("REDIS_PORT", 6379))
        self.db = db or int(os.getenv("REDIS_DB", 0))
        self.password = password or os.getenv("REDIS_PASSWORD")
        self.decode_responses = decode_responses

        self.client = redis.Redis(
            host=self.host,
            port=self.port,
            db=self.db,
            password=self.password,
            decode_responses=self.decode_responses
        )

    async def get(self, key: str) -> Optional[Any]:
        data = await self.client.get(key)
        if data is None:
            return None
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            return data

    async def set(self, key: str, value: Any, expire: Optional[int] = None):
        if not isinstance(value, str):
            value = json.dumps(value)
        if expire:
            await self.client.set(key, value, ex=expire)
        else:
            await self.client.set(key, value)

    async def delete(self, key: str):
        await self.client.delete(key)

    async def exists(self, key: str) -> bool:
        return await self.client.exists(key) > 0

    async def ping(self) -> bool:
        return await self.client.ping()

    async def incr(self, key: str) -> int:
        return await self.client.incr(key)

    async def flush_all(self) -> int:
        """Delete ALL keys in the current Redis DB"""
        return await self.client.flushdb()

    async def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching a pattern e.g. 'session:*' """
        keys = await self.client.keys(pattern)
        if keys:
            return await self.client.delete(*keys)
        return 0

    async def count_keys(self, pattern: str = "*") -> int:
        """Count keys matching a pattern"""
        keys = await self.client.keys(pattern)
        return len(keys)


cache = RedisCache()

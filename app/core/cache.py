"""
Caching utilities for VivaCripto API.
Provides Redis-based caching with TTL support for expensive operations.
"""
import hashlib
import json
from typing import Any, Optional

import redis.asyncio as redis
from loguru import logger

from app.core.config import settings


class CacheManager:
    """
    Redis-based cache manager for expensive operations.

    Usage:
        cache = CacheManager()
        await cache.connect()

        # Cache a value
        await cache.set("key", {"data": "value"}, ttl=3600)

        # Get a cached value
        value = await cache.get("key")

        await cache.disconnect()
    """

    def __init__(self, prefix: str = "vivacripto"):
        self.prefix = prefix
        self._client: Optional[redis.Redis] = None

    @property
    def client(self) -> redis.Redis:
        """Get Redis client, raising if not connected."""
        if self._client is None:
            raise RuntimeError("Cache not connected. Call connect() first.")
        return self._client

    async def connect(self) -> bool:
        """
        Connect to Redis.

        Returns:
            True if connected successfully, False otherwise.
        """
        if not settings.REDIS_URL:
            logger.warning("REDIS_URL not configured, cache disabled")
            return False

        try:
            self._client = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
            )
            await self._client.ping()
            logger.info("Connected to Redis cache")
            return True
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}")
            self._client = None
            return False

    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self._client:
            await self._client.aclose()
            self._client = None
            logger.info("Disconnected from Redis cache")

    def _make_key(self, key: str) -> str:
        """Create a namespaced cache key."""
        return f"{self.prefix}:{key}"

    async def get(self, key: str) -> Optional[Any]:
        """
        Get a cached value.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        if self._client is None:
            return None

        try:
            value = await self._client.get(self._make_key(key))
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.warning(f"Cache get error for {key}: {e}")
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int = 3600,
    ) -> bool:
        """
        Set a cached value.

        Args:
            key: Cache key
            value: Value to cache (must be JSON serializable)
            ttl: Time to live in seconds (default: 1 hour)

        Returns:
            True if cached successfully
        """
        if self._client is None:
            return False

        try:
            serialized = json.dumps(value)
            await self._client.setex(
                self._make_key(key),
                ttl,
                serialized,
            )
            return True
        except Exception as e:
            logger.warning(f"Cache set error for {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """
        Delete a cached value.

        Args:
            key: Cache key

        Returns:
            True if deleted successfully
        """
        if self._client is None:
            return False

        try:
            await self._client.delete(self._make_key(key))
            return True
        except Exception as e:
            logger.warning(f"Cache delete error for {key}: {e}")
            return False

    async def clear_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching a pattern.

        Args:
            pattern: Key pattern (e.g., "embeddings:*")

        Returns:
            Number of keys deleted
        """
        if self._client is None:
            return 0

        try:
            full_pattern = self._make_key(pattern)
            keys = []
            async for key in self._client.scan_iter(match=full_pattern):
                keys.append(key)

            if keys:
                deleted = await self._client.delete(*keys)
                logger.info(f"Cleared {deleted} keys matching {pattern}")
                return deleted
            return 0
        except Exception as e:
            logger.warning(f"Cache clear error for {pattern}: {e}")
            return 0


class EmbeddingCache:
    """
    Specialized cache for text embeddings.
    Uses content hash as key to avoid storing large texts.
    """

    def __init__(self, cache: CacheManager, ttl: int = 86400):
        """
        Initialize embedding cache.

        Args:
            cache: CacheManager instance
            ttl: TTL for embeddings in seconds (default: 24 hours)
        """
        self.cache = cache
        self.ttl = ttl

    def _hash_text(self, text: str) -> str:
        """Create a hash of the text for use as cache key."""
        return hashlib.sha256(text.encode()).hexdigest()[:16]

    async def get_embedding(self, text: str) -> Optional[list]:
        """
        Get cached embedding for text.

        Args:
            text: Text to get embedding for

        Returns:
            Cached embedding vector or None
        """
        key = f"embedding:{self._hash_text(text)}"
        return await self.cache.get(key)

    async def set_embedding(self, text: str, embedding: list) -> bool:
        """
        Cache an embedding for text.

        Args:
            text: Text the embedding is for
            embedding: Embedding vector

        Returns:
            True if cached successfully
        """
        key = f"embedding:{self._hash_text(text)}"
        return await self.cache.set(key, embedding, ttl=self.ttl)

    async def clear_all(self) -> int:
        """Clear all cached embeddings."""
        return await self.cache.clear_pattern("embedding:*")


# Global cache instance
cache_manager = CacheManager()
embedding_cache = EmbeddingCache(cache_manager)


async def init_cache() -> None:
    """Initialize the cache on application startup."""
    await cache_manager.connect()


async def close_cache() -> None:
    """Close the cache on application shutdown."""
    await cache_manager.disconnect()

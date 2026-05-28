"""Caching abstraction layer with Redis and memory fallback."""

import asyncio
import json
import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class CacheEntry:
    """Represents a cached item with metadata."""

    def __init__(self, key: str, value: Any, ttl: Optional[int] = None):
        self.key = key
        self.value = value
        self.created_at = time.time()
        self.ttl = ttl
        self.access_count = 0
        self.last_accessed = self.created_at

    @property
    def is_expired(self) -> bool:
        """Check if the cache entry has expired."""
        if self.ttl is None:
            return False
        return (time.time() - self.created_at) >= self.ttl

    @property
    def age(self) -> float:
        """Get the age of the cache entry in seconds."""
        return time.time() - self.created_at

    def to_dict(self) -> Dict[str, Any]:
        """Convert cache entry to dictionary for serialization."""
        return {
            "key": self.key,
            "value": self.value,
            "created_at": self.created_at,
            "ttl": self.ttl,
            "access_count": self.access_count,
            "last_accessed": self.last_accessed,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CacheEntry":
        """Create cache entry from dictionary."""
        entry = cls(data["key"], data["value"], data["ttl"])
        entry.created_at = data["created_at"]
        entry.access_count = data.get("access_count", 0)
        entry.last_accessed = data.get("last_accessed", entry.created_at)
        return entry


class CacheBackend(ABC):
    """Abstract base class for cache backends."""

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Retrieve a value from cache."""
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Store a value in cache with optional TTL."""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete a value from cache."""
        pass

    @abstractmethod
    async def clear(self) -> bool:
        """Clear all cached values."""
        pass

    @abstractmethod
    async def has_key(self, key: str) -> bool:
        """Check if key exists in cache."""
        pass

    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close cache backend connections."""
        pass


class MemoryCacheBackend(CacheBackend):
    """In-memory cache backend using dictionary."""

    def __init__(self, max_size: int = 1000):
        self._cache: Dict[str, CacheEntry] = {}
        self.max_size = max_size
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        """Retrieve a value from memory cache."""
        async with self._lock:
            entry = self._cache.get(key)
            if entry is None or entry.is_expired:
                if entry and entry.is_expired:
                    del self._cache[key]
                return None

            entry.access_count += 1
            entry.last_accessed = time.time()
            return entry.value

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Store a value in memory cache."""
        async with self._lock:
            # Evict oldest entries if at capacity
            if len(self._cache) >= self.max_size and key not in self._cache:
                # Find oldest entry
                oldest_key = min(
                    self._cache.keys(), key=lambda k: self._cache[k].last_accessed
                )
                del self._cache[oldest_key]
                logger.debug(f"Evicted cache entry: {oldest_key}")

            self._cache[key] = CacheEntry(key, value, ttl)
            return True

    async def delete(self, key: str) -> bool:
        """Delete a value from memory cache."""
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    async def clear(self) -> bool:
        """Clear all cached values."""
        async with self._lock:
            self._cache.clear()
            return True

    async def has_key(self, key: str) -> bool:
        """Check if key exists in memory cache."""
        async with self._lock:
            entry = self._cache.get(key)
            if entry is None or entry.is_expired:
                if entry and entry.is_expired:
                    del self._cache[key]
                return False
            return True

    async def get_stats(self) -> Dict[str, Any]:
        """Get memory cache statistics."""
        async with self._lock:
            total_entries = len(self._cache)
            expired_entries = sum(
                1 for entry in self._cache.values() if entry.is_expired
            )

            if total_entries > 0:
                avg_age = (
                    sum(entry.age for entry in self._cache.values()) / total_entries
                )
                total_accesses = sum(
                    entry.access_count for entry in self._cache.values()
                )
            else:
                avg_age = 0
                total_accesses = 0

            return {
                "backend": "memory",
                "total_entries": total_entries,
                "expired_entries": expired_entries,
                "max_size": self.max_size,
                "utilization_percent": (total_entries / self.max_size) * 100,
                "average_age_seconds": avg_age,
                "total_accesses": total_accesses,
            }

    async def close(self) -> None:
        """Close memory cache (no-op)."""
        pass


class RedisCacheBackend(CacheBackend):
    """Redis cache backend."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        max_connections: int = 10,
        decode_responses: bool = True,
    ):
        try:
            import redis.asyncio as redis
        except ImportError:
            raise ImportError("redis package is required for RedisCacheBackend")

        self.redis = redis.Redis(
            host=host,
            port=port,
            db=db,
            password=password,
            max_connections=max_connections,
            decode_responses=decode_responses,
            retry_on_timeout=True,
        )
        self._connected = False

    async def _ensure_connection(self) -> None:
        """Ensure Redis connection is established."""
        if not self._connected:
            try:
                await self.redis.ping()
                self._connected = True
                logger.debug("Redis connection established")
            except Exception as e:
                logger.warning(f"Redis connection failed: {e}")
                raise

    async def get(self, key: str) -> Optional[Any]:
        """Retrieve a value from Redis cache."""
        try:
            await self._ensure_connection()
            value = await self.redis.get(key)
            if value is None:
                return None

            # Try to parse JSON, fallback to raw value
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
        except Exception as e:
            logger.warning(f"Redis get failed: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Store a value in Redis cache."""
        try:
            await self._ensure_connection()

            # Serialize value to JSON if it's not a string
            if not isinstance(value, str):
                try:
                    serialized_value = json.dumps(value)
                except (TypeError, ValueError):
                    serialized_value = str(value)
            else:
                serialized_value = value

            if ttl is not None:
                result = await self.redis.setex(key, ttl, serialized_value)
            else:
                result = await self.redis.set(key, serialized_value)

            return result
        except Exception as e:
            logger.warning(f"Redis set failed: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete a value from Redis cache."""
        try:
            await self._ensure_connection()
            result = await self.redis.delete(key)
            return result > 0
        except Exception as e:
            logger.warning(f"Redis delete failed: {e}")
            return False

    async def clear(self) -> bool:
        """Clear all cached values in Redis."""
        try:
            await self._ensure_connection()
            await self.redis.flushdb()
            return True
        except Exception as e:
            logger.warning(f"Redis clear failed: {e}")
            return False

    async def has_key(self, key: str) -> bool:
        """Check if key exists in Redis cache."""
        try:
            await self._ensure_connection()
            return await self.redis.exists(key) > 0
        except Exception as e:
            logger.warning(f"Redis exists check failed: {e}")
            return False

    async def get_stats(self) -> Dict[str, Any]:
        """Get Redis cache statistics."""
        try:
            await self._ensure_connection()
            info = await self.redis.info()

            return {
                "backend": "redis",
                "connected": self._connected,
                "total_keys": await self.redis.dbsize(),
                "used_memory": info.get("used_memory_human", "unknown"),
                "connected_clients": info.get("connected_clients", 0),
                "uptime_days": info.get("uptime_in_days", 0),
                "hit_rate": info.get("keyspace_hits", 0)
                / max(info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0), 1)
                * 100,
            }
        except Exception as e:
            logger.warning(f"Redis stats failed: {e}")
            return {"backend": "redis", "connected": False, "error": str(e)}

    async def close(self) -> None:
        """Close Redis connections."""
        try:
            await self.redis.close()
            self._connected = False
        except Exception as e:
            logger.warning(f"Redis close failed: {e}")


class Cache:
    """Unified cache interface with automatic backend selection and fallback."""

    def __init__(
        self,
        primary_backend: CacheBackend,
        fallback_backend: Optional[CacheBackend] = None,
    ):
        self.primary = primary_backend
        self.fallback = fallback_backend or MemoryCacheBackend()
        self._stats = {"hits": 0, "misses": 0, "errors": 0}

    def _make_key(self, key: str, namespace: str = "") -> str:
        """Create a namespaced cache key."""
        if namespace:
            return f"{namespace}:{key}"
        return key

    async def get(self, key: str, namespace: str = "") -> Optional[Any]:
        """Retrieve a value from cache with fallback."""
        cache_key = self._make_key(key, namespace)

        # Try primary backend first
        try:
            value = await self.primary.get(cache_key)
            if value is not None:
                self._stats["hits"] += 1
                return value
        except Exception as e:
            logger.debug(f"Primary cache get failed: {e}")
            self._stats["errors"] += 1

        # Try fallback backend
        if self.fallback:
            try:
                value = await self.fallback.get(cache_key)
                if value is not None:
                    self._stats["hits"] += 1
                    # Promote to primary if possible
                    try:
                        await self.primary.set(cache_key, value)
                    except Exception:
                        pass  # Ignore promotion failures
                    return value
            except Exception as e:
                logger.debug(f"Fallback cache get failed: {e}")
                self._stats["errors"] += 1

        self._stats["misses"] += 1
        return None

    async def set(
        self, key: str, value: Any, ttl: Optional[int] = None, namespace: str = ""
    ) -> bool:
        """Store a value in cache with fallback."""
        cache_key = self._make_key(key, namespace)

        # Try primary backend first
        primary_success = False
        try:
            primary_success = await self.primary.set(cache_key, value, ttl)
        except Exception as e:
            logger.debug(f"Primary cache set failed: {e}")

        # Always try fallback backend
        fallback_success = False
        if self.fallback:
            try:
                fallback_success = await self.fallback.set(cache_key, value, ttl)
            except Exception as e:
                logger.debug(f"Fallback cache set failed: {e}")

        return primary_success or fallback_success

    async def delete(self, key: str, namespace: str = "") -> bool:
        """Delete a value from cache."""
        cache_key = self._make_key(key, namespace)

        primary_success = False
        fallback_success = False

        try:
            primary_success = await self.primary.delete(cache_key)
        except Exception as e:
            logger.debug(f"Primary cache delete failed: {e}")

        if self.fallback:
            try:
                fallback_success = await self.fallback.delete(cache_key)
            except Exception as e:
                logger.debug(f"Fallback cache delete failed: {e}")

        return primary_success or fallback_success

    async def clear(self, namespace: str = "") -> bool:
        """Clear all cached values."""
        # For namespaced clear, we'd need to scan keys which is expensive
        # For now, just clear everything
        primary_success = False
        fallback_success = False

        try:
            primary_success = await self.primary.clear()
        except Exception as e:
            logger.debug(f"Primary cache clear failed: {e}")

        if self.fallback:
            try:
                fallback_success = await self.fallback.clear()
            except Exception as e:
                logger.debug(f"Fallback cache clear failed: {e}")

        return primary_success or fallback_success

    async def has_key(self, key: str, namespace: str = "") -> bool:
        """Check if key exists in cache."""
        cache_key = self._make_key(key, namespace)

        try:
            if await self.primary.has_key(cache_key):
                return True
        except Exception:
            pass

        if self.fallback:
            try:
                return await self.fallback.has_key(cache_key)
            except Exception:
                pass

        return False

    async def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        primary_stats = {}
        fallback_stats = {}

        try:
            primary_stats = await self.primary.get_stats()
        except Exception as e:
            primary_stats = {"error": str(e)}

        if self.fallback:
            try:
                fallback_stats = await self.fallback.get_stats()
            except Exception as e:
                fallback_stats = {"error": str(e)}

        return {
            "overall": self._stats,
            "primary": primary_stats,
            "fallback": fallback_stats,
            "hit_rate": self._stats["hits"]
            / max(self._stats["hits"] + self._stats["misses"], 1)
            * 100,
        }

    async def close(self) -> None:
        """Close all cache backend connections."""
        try:
            await self.primary.close()
        except Exception:
            pass

        if self.fallback:
            try:
                await self.fallback.close()
            except Exception:
                pass


class CacheFactory:
    """Factory for creating cache instances."""

    @staticmethod
    def create_cache() -> Cache:
        """Create a cache instance based on configuration."""
        from ...core.config import get_settings

        settings = get_settings()

        # Try to create Redis backend first
        primary_backend = None
        try:
            primary_backend = RedisCacheBackend(
                host=settings.redis.host,
                port=settings.redis.port,
                db=settings.redis.db,
                password=settings.redis.password,
                max_connections=settings.redis.max_connections,
                decode_responses=settings.redis.decode_responses,
            )
            logger.info("Using Redis cache backend")
        except Exception as e:
            logger.warning(f"Failed to create Redis backend: {e}")

        # Fallback to memory cache
        if primary_backend is None:
            primary_backend = MemoryCacheBackend(max_size=1000)
            logger.info("Using memory cache backend")

        # Always have memory as fallback
        fallback_backend = MemoryCacheBackend(max_size=500)

        return Cache(primary_backend, fallback_backend)

"""
Cache manager for motion drafting system
Implements context caching to reduce costs and improve performance
"""

import hashlib
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
import asyncio
from dataclasses import dataclass, field
import pickle
from functools import wraps

from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class CacheEntry:
    """Single cache entry with metadata"""

    key: str
    value: Any
    created_at: datetime
    accessed_at: datetime
    access_count: int = 0
    size_bytes: int = 0
    ttl_seconds: int = 3600
    tags: List[str] = field(default_factory=list)

    def is_expired(self) -> bool:
        """Check if cache entry has expired"""
        return (datetime.utcnow() - self.created_at).total_seconds() > self.ttl_seconds

    def touch(self):
        """Update access time and count"""
        self.accessed_at = datetime.utcnow()
        self.access_count += 1


class MotionDraftingCache:
    """Specialized cache for motion drafting operations"""

    def __init__(self, max_size_mb: int = 500, default_ttl: int = 3600):
        """
        Initialize cache manager

        Args:
            max_size_mb: Maximum cache size in megabytes
            default_ttl: Default time-to-live in seconds
        """
        self.cache: Dict[str, CacheEntry] = {}
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.current_size_bytes = 0
        self.default_ttl = default_ttl

        # Cache statistics
        self.hits = 0
        self.misses = 0
        self.evictions = 0

        # Lock for thread safety
        self._lock = asyncio.Lock()

        logger.info(f"Initialized motion cache with {max_size_mb}MB limit")

    def _generate_key(self, operation: str, **kwargs) -> str:
        """Generate cache key from operation and parameters"""
        # Sort kwargs for consistent key generation
        sorted_params = sorted(kwargs.items())
        key_data = f"{operation}:{json.dumps(sorted_params, sort_keys=True)}"

        # Use SHA256 for consistent, fixed-length keys
        return hashlib.sha256(key_data.encode()).hexdigest()

    def _estimate_size(self, value: Any) -> int:
        """Estimate size of value in bytes"""
        try:
            return len(pickle.dumps(value))
        except:
            # Fallback for non-pickleable objects
            return len(str(value).encode())

    async def get(self, operation: str, **kwargs) -> Optional[Any]:
        """Get value from cache"""
        async with self._lock:
            key = self._generate_key(operation, **kwargs)

            if key in self.cache:
                entry = self.cache[key]

                # Check expiration
                if entry.is_expired():
                    self._remove_entry(key)
                    self.misses += 1
                    return None

                # Update access info
                entry.touch()
                self.hits += 1

                logger.debug(f"Cache hit for {operation}")
                return entry.value

            self.misses += 1
            return None

    async def set(
        self,
        operation: str,
        value: Any,
        ttl: Optional[int] = None,
        tags: Optional[List[str]] = None,
        **kwargs,
    ):
        """Set value in cache"""
        async with self._lock:
            key = self._generate_key(operation, **kwargs)
            size = self._estimate_size(value)

            # Check if we need to evict entries
            while self.current_size_bytes + size > self.max_size_bytes:
                if not self._evict_lru():
                    logger.warning("Cannot evict more entries, cache might be full")
                    break

            # Create cache entry
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=datetime.utcnow(),
                accessed_at=datetime.utcnow(),
                size_bytes=size,
                ttl_seconds=ttl or self.default_ttl,
                tags=tags or [],
            )

            # Store entry
            self.cache[key] = entry
            self.current_size_bytes += size

            logger.debug(f"Cached {operation} ({size} bytes)")

    def _remove_entry(self, key: str):
        """Remove entry from cache"""
        if key in self.cache:
            entry = self.cache[key]
            self.current_size_bytes -= entry.size_bytes
            del self.cache[key]

    def _evict_lru(self) -> bool:
        """Evict least recently used entry"""
        if not self.cache:
            return False

        # Find LRU entry
        lru_key = min(self.cache.keys(), key=lambda k: self.cache[k].accessed_at)

        self._remove_entry(lru_key)
        self.evictions += 1

        logger.debug(f"Evicted LRU entry: {lru_key[:8]}...")
        return True

    async def invalidate_by_tags(self, tags: List[str]):
        """Invalidate all entries with specified tags"""
        async with self._lock:
            keys_to_remove = []

            for key, entry in self.cache.items():
                if any(tag in entry.tags for tag in tags):
                    keys_to_remove.append(key)

            for key in keys_to_remove:
                self._remove_entry(key)

            logger.info(f"Invalidated {len(keys_to_remove)} entries with tags {tags}")

    async def clear(self):
        """Clear entire cache"""
        async with self._lock:
            self.cache.clear()
            self.current_size_bytes = 0
            logger.info("Cache cleared")

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = self.hits + self.misses
        hit_rate = self.hits / total_requests if total_requests > 0 else 0

        return {
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions,
            "hit_rate": hit_rate,
            "entries": len(self.cache),
            "size_bytes": self.current_size_bytes,
            "size_mb": self.current_size_bytes / (1024 * 1024),
        }


class ContextCache:
    """Cache for AI context to enable efficient section-by-section generation"""

    def __init__(self):
        self.context_cache: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def store_section_context(
        self, motion_id: str, section_id: str, context: Dict[str, Any]
    ):
        """Store context for a section"""
        async with self._lock:
            if motion_id not in self.context_cache:
                self.context_cache[motion_id] = {}

            self.context_cache[motion_id][section_id] = {
                "content": context,
                "timestamp": datetime.utcnow(),
                "tokens": context.get("token_count", 0),
            }

    async def get_motion_context(self, motion_id: str) -> Dict[str, Any]:
        """Get all context for a motion"""
        async with self._lock:
            return self.context_cache.get(motion_id, {})

    async def get_section_context(
        self, motion_id: str, section_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get context for a specific section"""
        async with self._lock:
            motion_context = self.context_cache.get(motion_id, {})
            return motion_context.get(section_id)

    async def build_cumulative_context(
        self, motion_id: str, up_to_section: str
    ) -> Dict[str, Any]:
        """Build cumulative context up to a specific section"""
        async with self._lock:
            motion_context = self.context_cache.get(motion_id, {})

            cumulative = {
                "sections": [],
                "total_tokens": 0,
                "key_points": [],
                "citations_used": set(),
            }

            for section_id, section_data in motion_context.items():
                if section_id == up_to_section:
                    break

                cumulative["sections"].append(
                    {
                        "id": section_id,
                        "summary": section_data["content"].get("summary", ""),
                        "key_points": section_data["content"].get("key_points", []),
                    }
                )

                cumulative["total_tokens"] += section_data.get("tokens", 0)
                cumulative["key_points"].extend(
                    section_data["content"].get("key_points", [])
                )
                cumulative["citations_used"].update(
                    section_data["content"].get("citations", [])
                )

            cumulative["citations_used"] = list(cumulative["citations_used"])
            return cumulative

    async def clear_motion_context(self, motion_id: str):
        """Clear context for a specific motion"""
        async with self._lock:
            if motion_id in self.context_cache:
                del self.context_cache[motion_id]
                logger.debug(f"Cleared context for motion {motion_id}")


# Global cache instances
motion_cache = MotionDraftingCache(max_size_mb=500, default_ttl=3600)
context_cache = ContextCache()


# Cache decorators
def cache_result(operation: str, ttl: int = 3600, tags: Optional[List[str]] = None):
    """Decorator to cache function results"""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Try to get from cache
            cache_key_params = {"args": str(args), "kwargs": str(kwargs)}

            cached = await motion_cache.get(operation, **cache_key_params)
            if cached is not None:
                return cached

            # Execute function
            result = await func(*args, **kwargs)

            # Cache result
            await motion_cache.set(
                operation, result, ttl=ttl, tags=tags, **cache_key_params
            )

            return result

        return wrapper

    return decorator


def invalidate_cache(*tags: str):
    """Decorator to invalidate cache entries with specified tags after function execution"""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            await motion_cache.invalidate_by_tags(list(tags))
            return result

        return wrapper

    return decorator

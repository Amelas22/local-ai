"""
Intelligent Caching Manager for Legal Document Management System

This module provides comprehensive caching strategies including Redis-based caching,
query result caching, document metadata caching, and materialized views for
complex aggregations. It optimizes performance while maintaining data consistency.

Key Features:
1. Multi-tier caching (L1: memory, L2: Redis, L3: materialized views)
2. Intelligent cache invalidation
3. Query result caching with TTL management
4. Document metadata caching
5. Search result caching
6. Aggregation result caching
7. Cache warming strategies
8. Performance monitoring and analytics
"""

import asyncio
import json
import hashlib
import pickle
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Set, Tuple, Union
from dataclasses import dataclass
from enum import Enum
import time

try:
    import redis.asyncio as redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

from ..vector_storage.qdrant_store import QdrantVectorStore
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class CacheLevel(str, Enum):
    """Cache levels in the hierarchy"""

    L1_MEMORY = "l1_memory"
    L2_REDIS = "l2_redis"
    L3_MATERIALIZED = "l3_materialized"


class CacheStrategy(str, Enum):
    """Caching strategies"""

    WRITE_THROUGH = "write_through"
    WRITE_BACK = "write_back"
    WRITE_AROUND = "write_around"
    READ_THROUGH = "read_through"
    LAZY_LOADING = "lazy_loading"


@dataclass
class CacheConfig:
    """Configuration for cache behavior"""

    default_ttl_seconds: int = 3600  # 1 hour
    memory_cache_size: int = 1000  # Max items in memory
    redis_max_memory_mb: int = 512  # Max Redis memory
    enable_compression: bool = True
    enable_materialized_views: bool = True
    cache_warming_enabled: bool = True
    invalidation_strategy: str = "smart"  # smart, immediate, lazy


@dataclass
class CacheKey:
    """Standardized cache key structure"""

    namespace: str
    entity_type: str
    entity_id: str
    operation: str
    filters_hash: Optional[str] = None

    def to_string(self) -> str:
        """Convert to string key"""
        parts = [self.namespace, self.entity_type, self.entity_id, self.operation]
        if self.filters_hash:
            parts.append(self.filters_hash)
        return ":".join(parts)


@dataclass
class CacheEntry:
    """Cache entry with metadata"""

    key: str
    value: Any
    created_at: datetime
    last_accessed: datetime
    access_count: int = 0
    ttl_seconds: Optional[int] = None
    size_bytes: int = 0
    cache_level: CacheLevel = CacheLevel.L1_MEMORY

    @property
    def is_expired(self) -> bool:
        """Check if cache entry is expired"""
        if not self.ttl_seconds:
            return False
        return (datetime.now() - self.created_at).total_seconds() > self.ttl_seconds

    @property
    def age_seconds(self) -> float:
        """Get age in seconds"""
        return (datetime.now() - self.created_at).total_seconds()


@dataclass
class CacheStats:
    """Cache performance statistics"""

    hits: int = 0
    misses: int = 0
    evictions: int = 0
    memory_usage_bytes: int = 0
    redis_usage_bytes: int = 0
    avg_response_time_ms: float = 0.0
    hit_rate: float = 0.0

    def update_hit_rate(self):
        """Update hit rate calculation"""
        total = self.hits + self.misses
        self.hit_rate = self.hits / total if total > 0 else 0.0


class InMemoryCache:
    """L1 in-memory cache with LRU eviction"""

    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.cache: Dict[str, CacheEntry] = {}
        self.access_order: List[str] = []  # For LRU
        self.total_size_bytes = 0

    def get(self, key: str) -> Optional[CacheEntry]:
        """Get item from cache"""
        if key in self.cache:
            entry = self.cache[key]
            if not entry.is_expired:
                # Update access tracking
                entry.last_accessed = datetime.now()
                entry.access_count += 1

                # Move to end for LRU
                if key in self.access_order:
                    self.access_order.remove(key)
                self.access_order.append(key)

                return entry
            else:
                # Remove expired entry
                self.remove(key)

        return None

    def put(self, key: str, entry: CacheEntry) -> bool:
        """Put item in cache"""
        # Remove existing entry if present
        if key in self.cache:
            self.remove(key)

        # Check if we need to evict
        while len(self.cache) >= self.max_size:
            self._evict_lru()

        # Add new entry
        self.cache[key] = entry
        self.access_order.append(key)
        self.total_size_bytes += entry.size_bytes

        return True

    def remove(self, key: str) -> bool:
        """Remove item from cache"""
        if key in self.cache:
            entry = self.cache[key]
            del self.cache[key]
            if key in self.access_order:
                self.access_order.remove(key)
            self.total_size_bytes -= entry.size_bytes
            return True
        return False

    def _evict_lru(self):
        """Evict least recently used item"""
        if self.access_order:
            lru_key = self.access_order[0]
            self.remove(lru_key)

    def clear(self):
        """Clear all cache entries"""
        self.cache.clear()
        self.access_order.clear()
        self.total_size_bytes = 0

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "memory_usage_bytes": self.total_size_bytes,
            "utilization": len(self.cache) / self.max_size if self.max_size > 0 else 0,
        }


class RedisCache:
    """L2 Redis-based cache"""

    def __init__(self, redis_url: str = "redis://localhost:6379", db: int = 0):
        self.redis_url = redis_url
        self.db = db
        self.redis_client: Optional[redis.Redis] = None
        self.connected = False

    async def connect(self):
        """Connect to Redis"""
        if not REDIS_AVAILABLE:
            logger.warning("Redis not available, skipping Redis cache")
            return False

        try:
            self.redis_client = redis.Redis.from_url(self.redis_url, db=self.db)
            await self.redis_client.ping()
            self.connected = True
            logger.info("Connected to Redis cache")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.connected = False
            return False

    async def get(self, key: str) -> Optional[Any]:
        """Get item from Redis cache"""
        if not self.connected or not self.redis_client:
            return None

        try:
            data = await self.redis_client.get(key)
            if data:
                return pickle.loads(data)
        except Exception as e:
            logger.error(f"Redis get failed for key {key}: {e}")

        return None

    async def put(
        self, key: str, value: Any, ttl_seconds: Optional[int] = None
    ) -> bool:
        """Put item in Redis cache"""
        if not self.connected or not self.redis_client:
            return False

        try:
            serialized = pickle.dumps(value)
            if ttl_seconds:
                await self.redis_client.setex(key, ttl_seconds, serialized)
            else:
                await self.redis_client.set(key, serialized)
            return True
        except Exception as e:
            logger.error(f"Redis put failed for key {key}: {e}")
            return False

    async def remove(self, key: str) -> bool:
        """Remove item from Redis cache"""
        if not self.connected or not self.redis_client:
            return False

        try:
            result = await self.redis_client.delete(key)
            return result > 0
        except Exception as e:
            logger.error(f"Redis remove failed for key {key}: {e}")
            return False

    async def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern"""
        if not self.connected or not self.redis_client:
            return 0

        try:
            keys = await self.redis_client.keys(pattern)
            if keys:
                return await self.redis_client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Redis clear pattern failed for {pattern}: {e}")
            return 0

    async def get_stats(self) -> Dict[str, Any]:
        """Get Redis statistics"""
        if not self.connected or not self.redis_client:
            return {}

        try:
            info = await self.redis_client.info("memory")
            return {
                "used_memory": info.get("used_memory", 0),
                "used_memory_human": info.get("used_memory_human", "0B"),
                "connected_clients": info.get("connected_clients", 0),
            }
        except Exception as e:
            logger.error(f"Failed to get Redis stats: {e}")
            return {}


class MaterializedViewManager:
    """L3 materialized views for complex aggregations"""

    def __init__(self, qdrant_store: QdrantVectorStore):
        self.qdrant_store = qdrant_store
        self.materialized_views: Dict[str, Dict[str, Any]] = {}
        self.view_refresh_schedule: Dict[str, datetime] = {}
        self.logger = logger

    async def create_materialized_view(
        self,
        view_name: str,
        query_config: Dict[str, Any],
        refresh_interval_hours: int = 24,
    ) -> bool:
        """Create a materialized view"""
        try:
            # Execute the aggregation query
            result = await self._execute_aggregation_query(query_config)

            # Store the materialized view
            self.materialized_views[view_name] = {
                "data": result,
                "config": query_config,
                "created_at": datetime.now(),
                "last_refreshed": datetime.now(),
                "refresh_interval_hours": refresh_interval_hours,
                "access_count": 0,
            }

            # Schedule next refresh
            next_refresh = datetime.now() + timedelta(hours=refresh_interval_hours)
            self.view_refresh_schedule[view_name] = next_refresh

            self.logger.info(f"Created materialized view: {view_name}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to create materialized view {view_name}: {e}")
            return False

    async def get_materialized_view(self, view_name: str) -> Optional[Dict[str, Any]]:
        """Get data from materialized view"""
        if view_name not in self.materialized_views:
            return None

        view = self.materialized_views[view_name]
        view["access_count"] += 1

        # Check if refresh is needed
        if self._needs_refresh(view_name):
            await self.refresh_materialized_view(view_name)

        return view["data"]

    async def refresh_materialized_view(self, view_name: str) -> bool:
        """Refresh a materialized view"""
        if view_name not in self.materialized_views:
            return False

        try:
            view = self.materialized_views[view_name]
            result = await self._execute_aggregation_query(view["config"])

            view["data"] = result
            view["last_refreshed"] = datetime.now()

            # Schedule next refresh
            next_refresh = datetime.now() + timedelta(
                hours=view["refresh_interval_hours"]
            )
            self.view_refresh_schedule[view_name] = next_refresh

            self.logger.info(f"Refreshed materialized view: {view_name}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to refresh materialized view {view_name}: {e}")
            return False

    def _needs_refresh(self, view_name: str) -> bool:
        """Check if view needs refresh"""
        if view_name not in self.view_refresh_schedule:
            return True

        return datetime.now() > self.view_refresh_schedule[view_name]

    async def _execute_aggregation_query(
        self, query_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute aggregation query"""
        # This would implement complex aggregation queries
        # For now, return a placeholder
        return {
            "query_type": query_config.get("type", "unknown"),
            "result_count": 0,
            "aggregations": {},
            "computed_at": datetime.now(),
        }


class CachingManager:
    """
    Comprehensive caching manager coordinating all cache levels
    """

    def __init__(
        self,
        qdrant_store: QdrantVectorStore,
        config: Optional[CacheConfig] = None,
        redis_url: str = "redis://localhost:6379",
    ):
        """
        Initialize the caching manager

        Args:
            qdrant_store: Vector database store
            config: Cache configuration
            redis_url: Redis connection URL
        """
        self.qdrant_store = qdrant_store
        self.config = config or CacheConfig()
        self.logger = logger

        # Initialize cache levels
        self.l1_cache = InMemoryCache(self.config.memory_cache_size)
        self.l2_cache = RedisCache(redis_url)
        self.l3_cache = MaterializedViewManager(qdrant_store)

        # Cache statistics
        self.stats = CacheStats()
        self.operation_stats: Dict[str, CacheStats] = {}

        # Cache invalidation tracking
        self.invalidation_rules: Dict[
            str, Set[str]
        ] = {}  # entity_type -> cache_patterns
        self.dependency_graph: Dict[str, Set[str]] = {}  # cache_key -> dependent_keys

        # Background tasks
        self._background_tasks: List[asyncio.Task] = []
        self._running = False

    async def initialize(self):
        """Initialize all cache components"""
        try:
            # Connect to Redis
            await self.l2_cache.connect()

            # Create common materialized views
            if self.config.enable_materialized_views:
                await self._create_common_materialized_views()

            # Start background tasks
            if self.config.cache_warming_enabled:
                await self._start_background_tasks()

            self.logger.info("Caching manager initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize caching manager: {e}")
            raise

    async def get(
        self, cache_key: Union[str, CacheKey], fallback_func: Optional[callable] = None
    ) -> Tuple[Optional[Any], CacheLevel]:
        """
        Get item from cache hierarchy

        Args:
            cache_key: Cache key (string or CacheKey object)
            fallback_func: Function to call if cache miss

        Returns:
            Tuple of (value, cache_level_found)
        """
        start_time = time.time()

        try:
            key_str = (
                cache_key.to_string() if isinstance(cache_key, CacheKey) else cache_key
            )

            # Try L1 cache first
            l1_entry = self.l1_cache.get(key_str)
            if l1_entry:
                self._record_hit(CacheLevel.L1_MEMORY, start_time)
                return l1_entry.value, CacheLevel.L1_MEMORY

            # Try L2 cache (Redis)
            l2_value = await self.l2_cache.get(key_str)
            if l2_value is not None:
                # Promote to L1
                await self._promote_to_l1(key_str, l2_value)
                self._record_hit(CacheLevel.L2_REDIS, start_time)
                return l2_value, CacheLevel.L2_REDIS

            # Try L3 cache (Materialized Views) for specific patterns
            if self._is_materialized_view_candidate(key_str):
                l3_value = await self._check_materialized_views(key_str)
                if l3_value is not None:
                    # Promote to L2 and L1
                    await self._promote_to_l2(key_str, l3_value)
                    await self._promote_to_l1(key_str, l3_value)
                    self._record_hit(CacheLevel.L3_MATERIALIZED, start_time)
                    return l3_value, CacheLevel.L3_MATERIALIZED

            # Cache miss - use fallback if provided
            if fallback_func:
                value = (
                    await fallback_func()
                    if asyncio.iscoroutinefunction(fallback_func)
                    else fallback_func()
                )
                if value is not None:
                    await self.put(cache_key, value)
                self._record_miss(start_time)
                return value, None

            self._record_miss(start_time)
            return None, None

        except Exception as e:
            self.logger.error(f"Cache get failed for key {cache_key}: {e}")
            self._record_miss(start_time)
            return None, None

    async def put(
        self,
        cache_key: Union[str, CacheKey],
        value: Any,
        ttl_seconds: Optional[int] = None,
    ) -> bool:
        """
        Put item in cache hierarchy

        Args:
            cache_key: Cache key
            value: Value to cache
            ttl_seconds: Time to live in seconds

        Returns:
            Success status
        """
        try:
            key_str = (
                cache_key.to_string() if isinstance(cache_key, CacheKey) else cache_key
            )
            ttl = ttl_seconds or self.config.default_ttl_seconds

            # Calculate size
            size_bytes = (
                len(pickle.dumps(value))
                if self.config.enable_compression
                else len(str(value))
            )

            # Store in L1
            l1_entry = CacheEntry(
                key=key_str,
                value=value,
                created_at=datetime.now(),
                last_accessed=datetime.now(),
                ttl_seconds=ttl,
                size_bytes=size_bytes,
                cache_level=CacheLevel.L1_MEMORY,
            )
            self.l1_cache.put(key_str, l1_entry)

            # Store in L2 (Redis)
            await self.l2_cache.put(key_str, value, ttl)

            return True

        except Exception as e:
            self.logger.error(f"Cache put failed for key {cache_key}: {e}")
            return False

    async def invalidate(
        self, cache_key: Union[str, CacheKey, List[str]], cascade: bool = True
    ) -> int:
        """
        Invalidate cache entries

        Args:
            cache_key: Key(s) to invalidate
            cascade: Whether to cascade invalidation to dependent keys

        Returns:
            Number of keys invalidated
        """
        try:
            keys_to_invalidate = []

            if isinstance(cache_key, list):
                keys_to_invalidate = cache_key
            elif isinstance(cache_key, CacheKey):
                keys_to_invalidate = [cache_key.to_string()]
            else:
                keys_to_invalidate = [cache_key]

            # Add dependent keys if cascading
            if cascade:
                for key in keys_to_invalidate.copy():
                    if key in self.dependency_graph:
                        keys_to_invalidate.extend(self.dependency_graph[key])

            # Remove from all cache levels
            invalidated_count = 0
            for key in set(keys_to_invalidate):  # Remove duplicates
                # L1 cache
                if self.l1_cache.remove(key):
                    invalidated_count += 1

                # L2 cache
                if await self.l2_cache.remove(key):
                    invalidated_count += 1

            self.logger.info(f"Invalidated {invalidated_count} cache entries")
            return invalidated_count

        except Exception as e:
            self.logger.error(f"Cache invalidation failed: {e}")
            return 0

    async def invalidate_by_pattern(self, pattern: str) -> int:
        """Invalidate cache entries matching pattern"""
        try:
            # Clear from L1 cache
            l1_cleared = 0
            keys_to_remove = []
            for key in self.l1_cache.cache.keys():
                if self._matches_pattern(key, pattern):
                    keys_to_remove.append(key)

            for key in keys_to_remove:
                if self.l1_cache.remove(key):
                    l1_cleared += 1

            # Clear from L2 cache (Redis)
            l2_cleared = await self.l2_cache.clear_pattern(pattern)

            total_cleared = l1_cleared + l2_cleared
            self.logger.info(
                f"Cleared {total_cleared} cache entries matching pattern: {pattern}"
            )
            return total_cleared

        except Exception as e:
            self.logger.error(f"Pattern invalidation failed for {pattern}: {e}")
            return 0

    def _matches_pattern(self, key: str, pattern: str) -> bool:
        """Check if key matches pattern (simple glob-style matching)"""
        import fnmatch

        return fnmatch.fnmatch(key, pattern)

    async def _promote_to_l1(self, key: str, value: Any):
        """Promote value to L1 cache"""
        l1_entry = CacheEntry(
            key=key,
            value=value,
            created_at=datetime.now(),
            last_accessed=datetime.now(),
            ttl_seconds=self.config.default_ttl_seconds,
            size_bytes=len(str(value)),
            cache_level=CacheLevel.L1_MEMORY,
        )
        self.l1_cache.put(key, l1_entry)

    async def _promote_to_l2(self, key: str, value: Any):
        """Promote value to L2 cache"""
        await self.l2_cache.put(key, value, self.config.default_ttl_seconds)

    def _is_materialized_view_candidate(self, key: str) -> bool:
        """Check if key is a candidate for materialized views"""
        # Check for aggregation or complex query patterns
        return any(
            pattern in key for pattern in ["aggregation", "stats", "summary", "count"]
        )

    async def _check_materialized_views(self, key: str) -> Optional[Any]:
        """Check materialized views for the key"""
        # Extract view name from key
        for view_name in self.l3_cache.materialized_views.keys():
            if view_name in key:
                return await self.l3_cache.get_materialized_view(view_name)
        return None

    def _record_hit(self, cache_level: CacheLevel, start_time: float):
        """Record cache hit statistics"""
        self.stats.hits += 1
        response_time = (time.time() - start_time) * 1000  # ms
        self.stats.avg_response_time_ms = (
            self.stats.avg_response_time_ms * (self.stats.hits - 1) + response_time
        ) / self.stats.hits
        self.stats.update_hit_rate()

    def _record_miss(self, start_time: float):
        """Record cache miss statistics"""
        self.stats.misses += 1
        self.stats.update_hit_rate()

    async def _create_common_materialized_views(self):
        """Create commonly used materialized views"""
        try:
            # Case document counts
            await self.l3_cache.create_materialized_view(
                "case_document_counts",
                {
                    "type": "aggregation",
                    "collection": "document_case_junctions",
                    "group_by": "case_id",
                    "aggregations": ["count"],
                },
                refresh_interval_hours=24,
            )

            # Document type distribution
            await self.l3_cache.create_materialized_view(
                "document_type_distribution",
                {
                    "type": "aggregation",
                    "collection": "document_metadata",
                    "group_by": "document_type",
                    "aggregations": ["count"],
                },
                refresh_interval_hours=12,
            )

            self.logger.info("Created common materialized views")

        except Exception as e:
            self.logger.error(f"Failed to create materialized views: {e}")

    async def _start_background_tasks(self):
        """Start background maintenance tasks"""
        self._running = True

        # Cache cleanup task
        cleanup_task = asyncio.create_task(self._background_cleanup())
        self._background_tasks.append(cleanup_task)

        # Cache warming task
        warming_task = asyncio.create_task(self._background_warming())
        self._background_tasks.append(warming_task)

        # Statistics update task
        stats_task = asyncio.create_task(self._background_stats_update())
        self._background_tasks.append(stats_task)

        self.logger.info("Started background caching tasks")

    async def _background_cleanup(self):
        """Background task for cache cleanup"""
        while self._running:
            try:
                # Clean expired entries from L1 cache
                expired_keys = []
                for key, entry in self.l1_cache.cache.items():
                    if entry.is_expired:
                        expired_keys.append(key)

                for key in expired_keys:
                    self.l1_cache.remove(key)
                    self.stats.evictions += 1

                if expired_keys:
                    self.logger.info(
                        f"Cleaned {len(expired_keys)} expired cache entries"
                    )

                await asyncio.sleep(300)  # Run every 5 minutes

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Background cleanup error: {e}")
                await asyncio.sleep(60)

    async def _background_warming(self):
        """Background task for cache warming"""
        while self._running:
            try:
                # Warm frequently accessed data
                await self._warm_document_metadata()
                await self._warm_case_statistics()

                await asyncio.sleep(3600)  # Run every hour

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Background warming error: {e}")
                await asyncio.sleep(300)

    async def _warm_document_metadata(self):
        """Warm document metadata cache"""
        try:
            # Pre-load metadata for recently accessed documents
            # This would integrate with access tracking
            self.logger.debug("Warming document metadata cache")
        except Exception as e:
            self.logger.error(f"Document metadata warming failed: {e}")

    async def _warm_case_statistics(self):
        """Warm case statistics cache"""
        try:
            # Pre-calculate case statistics
            self.logger.debug("Warming case statistics cache")
        except Exception as e:
            self.logger.error(f"Case statistics warming failed: {e}")

    async def _background_stats_update(self):
        """Background task for updating statistics"""
        while self._running:
            try:
                # Update memory usage
                self.stats.memory_usage_bytes = self.l1_cache.total_size_bytes

                # Update Redis usage if available
                redis_stats = await self.l2_cache.get_stats()
                self.stats.redis_usage_bytes = redis_stats.get("used_memory", 0)

                await asyncio.sleep(60)  # Update every minute

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Background stats update error: {e}")
                await asyncio.sleep(60)

    async def stop_background_tasks(self):
        """Stop all background tasks"""
        self._running = False
        for task in self._background_tasks:
            task.cancel()

        # Wait for tasks to complete
        await asyncio.gather(*self._background_tasks, return_exceptions=True)
        self._background_tasks.clear()

        self.logger.info("Stopped background caching tasks")

    def get_cache_statistics(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics"""
        l1_stats = self.l1_cache.get_stats()

        return {
            "overall": {
                "hits": self.stats.hits,
                "misses": self.stats.misses,
                "hit_rate": self.stats.hit_rate,
                "evictions": self.stats.evictions,
                "avg_response_time_ms": self.stats.avg_response_time_ms,
            },
            "l1_memory": l1_stats,
            "l2_redis": {
                "connected": self.l2_cache.connected,
                "usage_bytes": self.stats.redis_usage_bytes,
            },
            "l3_materialized": {
                "views_count": len(self.l3_cache.materialized_views),
                "views": list(self.l3_cache.materialized_views.keys()),
            },
        }

    async def clear_all_caches(self):
        """Clear all cache levels"""
        try:
            # Clear L1
            self.l1_cache.clear()

            # Clear L2 (Redis)
            if self.l2_cache.connected:
                await self.l2_cache.clear_pattern("*")

            # Clear L3 materialized views would require recreation
            self.l3_cache.materialized_views.clear()

            self.logger.info("Cleared all cache levels")

        except Exception as e:
            self.logger.error(f"Failed to clear all caches: {e}")


# Utility functions for creating cache keys


def create_document_cache_key(document_id: str, operation: str = "get") -> CacheKey:
    """Create cache key for document operations"""
    return CacheKey(
        namespace="legal_docs",
        entity_type="document",
        entity_id=document_id,
        operation=operation,
    )


def create_search_cache_key(query: str, filters: Dict[str, Any]) -> CacheKey:
    """Create cache key for search operations"""
    filters_str = json.dumps(filters, sort_keys=True)
    filters_hash = hashlib.md5(filters_str.encode()).hexdigest()[:8]
    query_hash = hashlib.md5(query.encode()).hexdigest()[:8]

    return CacheKey(
        namespace="legal_docs",
        entity_type="search",
        entity_id=query_hash,
        operation="results",
        filters_hash=filters_hash,
    )


def create_case_cache_key(case_id: str, operation: str = "stats") -> CacheKey:
    """Create cache key for case operations"""
    return CacheKey(
        namespace="legal_docs",
        entity_type="case",
        entity_id=case_id,
        operation=operation,
    )

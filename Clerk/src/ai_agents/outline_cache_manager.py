"""
Outline Cache Manager
Handles caching and retrieval of large legal outlines for efficient processing
"""

import json
import hashlib
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import asyncio
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class CachedOutline:
    """Represents a cached outline with metadata"""

    outline_id: str
    outline_data: Dict[str, Any]
    database_name: str
    created_at: datetime
    expires_at: datetime
    section_count: int
    total_size: int
    section_index: Dict[str, int]  # Maps section IDs to their position


class OutlineCacheManager:
    """Manages caching of large legal outlines"""

    def __init__(self, ttl_hours: int = 24):
        self._cache: Dict[str, CachedOutline] = {}
        self._ttl = timedelta(hours=ttl_hours)
        self._lock = asyncio.Lock()
        logger.info(f"OutlineCacheManager initialized with {ttl_hours}h TTL")

    def _generate_outline_id(self, outline: Dict[str, Any], database_name: str) -> str:
        """Generate unique ID for outline based on content"""
        # Create a hash of the outline content and database name
        content = json.dumps(outline, sort_keys=True) + database_name
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _build_section_index(self, outline: Dict[str, Any]) -> Dict[str, int]:
        """Build an index mapping section IDs to their positions"""
        index = {}

        sections = outline.get("sections", [])
        for i, section in enumerate(sections):
            # Use the section heading as a key
            section_key = section.get("heading", section.get("title", f"section_{i}"))
            index[section_key] = i

            # Also index by type if available
            section_type = section.get("type", "")
            if section_type:
                index[f"type:{section_type}"] = i

        return index

    async def cache_outline(self, outline: Dict[str, Any], database_name: str) -> str:
        """Cache an outline and return its ID"""
        async with self._lock:
            outline_id = self._generate_outline_id(outline, database_name)

            # Calculate outline size
            outline_str = json.dumps(outline)
            total_size = len(outline_str)

            # Extract sections
            sections = outline.get("sections", [])
            section_count = len(sections)

            # Build section index
            section_index = self._build_section_index(outline)

            # Create cached outline
            cached = CachedOutline(
                outline_id=outline_id,
                outline_data=outline,
                database_name=database_name,
                created_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + self._ttl,
                section_count=section_count,
                total_size=total_size,
                section_index=section_index,
            )

            self._cache[outline_id] = cached

            logger.info(
                f"Cached outline {outline_id} for {database_name}: "
                f"{section_count} sections, {total_size} bytes"
            )

            # Clean expired entries
            await self._cleanup_expired()

            return outline_id

    async def get_outline(self, outline_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve full outline by ID"""
        async with self._lock:
            cached = self._cache.get(outline_id)

            if not cached:
                logger.warning(f"Outline {outline_id} not found in cache")
                return None

            if datetime.utcnow() > cached.expires_at:
                logger.warning(f"Outline {outline_id} has expired")
                del self._cache[outline_id]
                return None

            logger.info(f"Retrieved outline {outline_id} from cache")
            return cached.outline_data

    async def get_section(
        self, outline_id: str, section_index: int
    ) -> Optional[Dict[str, Any]]:
        """Retrieve a specific section by index"""
        outline = await self.get_outline(outline_id)
        if not outline:
            return None

        sections = outline.get("sections", [])
        if 0 <= section_index < len(sections):
            return sections[section_index]

        logger.warning(
            f"Section index {section_index} out of range for outline {outline_id}"
        )
        return None

    async def get_section_by_key(
        self, outline_id: str, section_key: str
    ) -> Optional[Dict[str, Any]]:
        """Retrieve a section by its key (heading or type)"""
        async with self._lock:
            cached = self._cache.get(outline_id)
            if not cached:
                return None

            # Check if key exists in index
            section_index = cached.section_index.get(section_key)
            if section_index is None:
                logger.warning(
                    f"Section key '{section_key}' not found in outline {outline_id}"
                )
                return None

        return await self.get_section(outline_id, section_index)

    async def get_outline_metadata(self, outline_id: str) -> Optional[Dict[str, Any]]:
        """Get metadata about cached outline without loading full content"""
        async with self._lock:
            cached = self._cache.get(outline_id)
            if not cached:
                return None

            return {
                "outline_id": cached.outline_id,
                "database_name": cached.database_name,
                "created_at": cached.created_at.isoformat(),
                "expires_at": cached.expires_at.isoformat(),
                "section_count": cached.section_count,
                "total_size": cached.total_size,
                "section_keys": list(cached.section_index.keys()),
            }

    async def get_outline_structure(
        self, outline_id: str
    ) -> Optional[List[Dict[str, Any]]]:
        """Get simplified outline structure for navigation"""
        outline = await self.get_outline(outline_id)
        if not outline:
            return None

        structure = []
        sections = outline.get("sections", [])

        for i, section in enumerate(sections):
            structure.append(
                {
                    "index": i,
                    "heading": section.get(
                        "heading", section.get("title", f"Section {i + 1}")
                    ),
                    "type": section.get("type", "standard"),
                    "content_items": len(section.get("content", [])),
                    "has_subsections": bool(section.get("subsections", [])),
                }
            )

        return structure

    async def chunk_outline_for_processing(
        self, outline_id: str, chunk_size: int = 3
    ) -> List[List[int]]:
        """Split outline into chunks of sections for batch processing"""
        metadata = await self.get_outline_metadata(outline_id)
        if not metadata:
            return []

        section_count = metadata["section_count"]
        chunks = []

        for i in range(0, section_count, chunk_size):
            chunk = list(range(i, min(i + chunk_size, section_count)))
            chunks.append(chunk)

        return chunks

    async def _cleanup_expired(self):
        """Remove expired outlines from cache"""
        current_time = datetime.utcnow()
        expired_ids = [
            oid
            for oid, cached in self._cache.items()
            if current_time > cached.expires_at
        ]

        for oid in expired_ids:
            del self._cache[oid]
            logger.info(f"Removed expired outline {oid}")

    async def clear_cache(self):
        """Clear all cached outlines"""
        async with self._lock:
            count = len(self._cache)
            self._cache.clear()
            logger.info(f"Cleared {count} outlines from cache")

    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        async with self._lock:
            total_size = sum(c.total_size for c in self._cache.values())

            return {
                "cached_outlines": len(self._cache),
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "oldest_outline": min(
                    (c.created_at for c in self._cache.values()), default=None
                ),
                "newest_outline": max(
                    (c.created_at for c in self._cache.values()), default=None
                ),
            }


# Global instance
outline_cache = OutlineCacheManager(ttl_hours=24)

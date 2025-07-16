"""
Shared Resource Configuration for multi-tenant legal AI system.
Defines collections that are shared across all cases and law firms.
"""

import os
from typing import List, Set
from functools import lru_cache

# Environment variable for shared collections (comma-separated)
SHARED_COLLECTIONS_ENV = os.getenv(
    "SHARED_COLLECTIONS",
    "florida_statutes,fmcsr_regulations,federal_rules,case_law_precedents",
)

# Parse shared collections from environment
SHARED_COLLECTIONS: Set[str] = set(
    collection.strip().lower()
    for collection in SHARED_COLLECTIONS_ENV.split(",")
    if collection.strip()
)

# Additional shared resource patterns (for future expansion)
SHARED_RESOURCE_PATTERNS = [
    "*_statutes",  # Any collection ending with _statutes
    "*_regulations",  # Any collection ending with _regulations
    "federal_*",  # Any collection starting with federal_
    "*_precedents",  # Any collection ending with _precedents
]


@lru_cache(maxsize=128)
def is_shared_resource(collection_name: str) -> bool:
    """
    Determine if a collection is a shared resource.

    Args:
        collection_name: Name of the collection to check

    Returns:
        True if the collection is a shared resource
    """
    if not collection_name:
        return False

    # Normalize collection name
    normalized_name = collection_name.strip().lower()

    # Check exact matches first
    if normalized_name in SHARED_COLLECTIONS:
        return True

    # Check patterns (if needed in future)
    # This is commented out for now but can be enabled if pattern matching is needed
    # for pattern in SHARED_RESOURCE_PATTERNS:
    #     if pattern.startswith("*") and pattern.endswith("*"):
    #         # Contains pattern
    #         if pattern[1:-1] in normalized_name:
    #             return True
    #     elif pattern.startswith("*"):
    #         # Ends with pattern
    #         if normalized_name.endswith(pattern[1:]):
    #             return True
    #     elif pattern.endswith("*"):
    #         # Starts with pattern
    #         if normalized_name.startswith(pattern[:-1]):
    #             return True

    return False


def get_shared_collections() -> List[str]:
    """
    Get list of all shared collection names.

    Returns:
        List of shared collection names
    """
    return sorted(list(SHARED_COLLECTIONS))


def add_shared_collection(collection_name: str) -> None:
    """
    Add a collection to the shared resources set.
    For runtime configuration changes.

    Args:
        collection_name: Name of collection to add
    """
    if collection_name:
        SHARED_COLLECTIONS.add(collection_name.strip().lower())
        # Clear cache when configuration changes
        is_shared_resource.cache_clear()


def remove_shared_collection(collection_name: str) -> None:
    """
    Remove a collection from the shared resources set.
    For runtime configuration changes.

    Args:
        collection_name: Name of collection to remove
    """
    if collection_name:
        SHARED_COLLECTIONS.discard(collection_name.strip().lower())
        # Clear cache when configuration changes
        is_shared_resource.cache_clear()


def filter_case_specific_collections(
    all_collections: List[str], include_shared: bool = False
) -> List[str]:
    """
    Filter collections to include only case-specific ones.

    Args:
        all_collections: List of all collection names
        include_shared: Whether to include shared resources

    Returns:
        Filtered list of collection names
    """
    if include_shared:
        return all_collections

    return [
        collection
        for collection in all_collections
        if not is_shared_resource(collection)
    ]


# Configuration class for type safety
class SharedResourceConfig:
    """Configuration for shared resources"""

    def __init__(self):
        self.collections = SHARED_COLLECTIONS
        self.patterns = SHARED_RESOURCE_PATTERNS

    def is_shared(self, resource_name: str) -> bool:
        """Check if a resource is shared"""
        return is_shared_resource(resource_name)

    def get_all_shared(self) -> List[str]:
        """Get all shared collection names"""
        return get_shared_collections()

    def __contains__(self, item: str) -> bool:
        """Support 'in' operator"""
        return is_shared_resource(item)


# Global instance
shared_resources = SharedResourceConfig()

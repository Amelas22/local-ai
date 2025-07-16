"""
Vector storage package for Clerk legal AI system.
Provides Qdrant vector storage with hybrid search capabilities.
"""

from .embeddings import EmbeddingGenerator
from .qdrant_store import QdrantVectorStore, SearchResult
from .sparse_encoder import SparseVectorEncoder, LegalQueryAnalyzer

__all__ = [
    "EmbeddingGenerator",
    "QdrantVectorStore",
    "SearchResult",
    "SparseVectorEncoder",
    "LegalQueryAnalyzer",
]

__version__ = "2.0.0"  # Major version bump for Qdrant migration

"""
Qdrant vector storage module.
Manages storing and retrieving vectors from Qdrant with folder-based isolation and hybrid search.
"""

import asyncio
import uuid
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field
import re
import hashlib
import cohere
from collections import defaultdict

from qdrant_client import QdrantClient, AsyncQdrantClient
from qdrant_client.http import models
from qdrant_client.models import (
    Distance,
    VectorParams,
    HnswConfigDiff,
    OptimizersConfigDiff,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    ScalarQuantization,
    ScalarQuantizationConfig,
    ScalarType,
    SparseVectorParams,
    SparseIndexParams,
    SparseVector,
)
from config.settings import settings
from src.utils.logger import get_logger
from src.vector_storage.sparse_encoder import SparseVectorEncoder

logger = get_logger(__name__)


@dataclass
class SearchResult:
    """Result from vector search with ranking tracking"""

    id: str
    content: str
    case_name: str
    document_id: str
    score: float
    metadata: Dict[str, Any]
    search_type: str = "vector"  # "vector", "keyword", "citation", "hybrid", "reranked"

    # Ranking tracking fields
    ranking_history: Dict[str, Optional[int]] = field(
        default_factory=lambda: {
            "semantic_rank": None,
            "keyword_rank": None,
            "citation_rank": None,
            "rrf_rank": None,
            "final_rank": None,
        }
    )

    # Score tracking fields
    score_history: Dict[str, Optional[float]] = field(
        default_factory=lambda: {
            "semantic_score": None,
            "keyword_score": None,
            "citation_score": None,
            "rrf_score": None,
            "cohere_score": None,
        }
    )


class QdrantVectorStore:
    """Manages vector storage in Qdrant with folder-based isolation and hybrid search"""

    def __init__(self, database_name: Optional[str] = None):
        """Initialize Qdrant client

        Args:
            database_name: Optional database name for case-specific collections
        """
        self.config = settings.qdrant
        self.database_name = database_name

        # Build URL with database name if provided
        base_url = self.config.url
        if database_name:
            if base_url.endswith("/"):
                base_url = base_url[:-1]
            base_url = f"{base_url}/{database_name}"

        # Initialize synchronous client
        self.client = QdrantClient(
            url=base_url,
            api_key=self.config.api_key,
            prefer_grpc=self.config.prefer_grpc,
            timeout=self.config.timeout,
            check_compatibility=False,  # Skip version check for Docker/Cloud setups
        )

        # Initialize async client for batch operations
        self.async_client = AsyncQdrantClient(
            url=base_url,
            api_key=self.config.api_key,
            prefer_grpc=self.config.prefer_grpc,
            timeout=self.config.timeout,
            check_compatibility=False,  # Skip version check for Docker/Cloud setups
        )

        # Initialize sparse encoder for hybrid search
        self.sparse_encoder = SparseVectorEncoder()

        # Initialize Cohere client for reranking
        self.cohere_client = (
            cohere.Client(settings.cohere.api_key) if settings.cohere.api_key else None
        )
        if not self.cohere_client:
            logger.warning("Cohere API key not found. Reranking will be disabled.")

    def get_collection_name(self, folder_name: str) -> str:
        """Generate safe collection name from folder name"""
        # Sanitize folder name to valid Qdrant collection name
        sanitized = re.sub(r"[^a-zA-Z0-9_]", "_", folder_name)
        return f"{sanitized}" if settings.legal.enable_hybrid_search else sanitized

    def ensure_collection_exists(self, folder_name: str, use_case_manager: bool = True):
        """Ensure collection exists for a specific folder

        Args:
            folder_name: Name of the folder/case
            use_case_manager: Whether to use case manager for collection naming

        Returns:
            Collection name
        """
        # Import here to avoid circular dependency
        from src.services.case_manager import case_manager
        from src.config.shared_resources import is_shared_resource

        # For shared resources, use the folder name directly
        if is_shared_resource(folder_name):
            collection_name = self.get_collection_name(folder_name)
        elif use_case_manager and case_manager._client:
            # Try to get collection name from case manager
            try:
                # This assumes we have law_firm_id in context or use a default
                law_firm_id = "default-firm"  # TODO: Get from context
                collection_name = case_manager.case_name_to_collection(
                    folder_name, law_firm_id
                )
            except Exception:
                # Fall back to legacy method
                collection_name = self.get_collection_name(folder_name)
        else:
            # Use legacy collection naming
            collection_name = self.get_collection_name(folder_name)

        try:
            # Check if collection exists
            exists = self.client.collection_exists(collection_name)
            logger.debug(f"Collection '{collection_name}' exists: {exists}")

            if not exists:
                logger.info(f"Creating new collection: {collection_name}")
                self.create_collection(collection_name)

                # Verify creation
                if self.client.collection_exists(collection_name):
                    logger.info(f"Successfully created collection: {collection_name}")
                else:
                    raise Exception(
                        f"Collection creation failed - collection still doesn't exist: {collection_name}"
                    )

            return collection_name

        except Exception as e:
            logger.error(f"Error ensuring collection exists: {str(e)}")
            logger.error(f"Folder: {folder_name}, Collection: {collection_name}")
            logger.error(f"Qdrant URL: {self.config.url}")

            # Try to create collection with minimal config as fallback
            try:
                logger.warning(
                    "Attempting to create collection with minimal configuration..."
                )
                self._create_minimal_collection(collection_name)
                return collection_name
            except Exception as fallback_error:
                logger.error(
                    f"Fallback collection creation also failed: {str(fallback_error)}"
                )
                raise Exception(
                    f"Failed to create collection '{collection_name}': {str(e)}"
                )

    def create_collection(self, collection_name: str):
        """Create a new collection with hybrid configuration"""
        if settings.legal.enable_hybrid_search:
            self._create_hybrid_collection(collection_name)
        else:
            self._create_standard_collection(collection_name)

    def _create_standard_collection(self, collection_name: str):
        """Create standard vector collection"""
        quantization_config = None
        if hasattr(settings.vector, "quantization") and settings.vector.quantization:
            quantization_config = ScalarQuantization(
                scalar=ScalarQuantizationConfig(
                    type=ScalarType.INT8, quantile=0.99, always_ram=True
                )
            )

        self.client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=settings.vector.embedding_dimensions, distance=Distance.COSINE
            ),
            hnsw_config=HnswConfigDiff(
                m=settings.vector.hnsw_m,
                ef_construct=settings.vector.hnsw_ef_construct,
                on_disk=False,
                max_indexing_threads=8,
            ),
            quantization_config=quantization_config,
            on_disk_payload=False,
        )
        self._create_payload_indexes(collection_name)

    def _create_hybrid_collection(self, collection_name: str):
        """Create hybrid collection with multiple vector types"""
        self.client.create_collection(
            collection_name=collection_name,
            vectors_config={
                "semantic": VectorParams(
                    size=settings.vector.embedding_dimensions, distance=Distance.COSINE
                ),
                "legal_concepts": VectorParams(
                    size=settings.vector.embedding_dimensions, distance=Distance.COSINE
                ),
            },
            sparse_vectors_config={
                "keywords": SparseVectorParams(index=SparseIndexParams(on_disk=False)),
                "citations": SparseVectorParams(index=SparseIndexParams(on_disk=False)),
            },
            hnsw_config=HnswConfigDiff(
                m=settings.vector.hnsw_m,
                ef_construct=settings.vector.hnsw_ef_construct,
                on_disk=False,
                max_indexing_threads=8,
            ),
            on_disk_payload=False,
        )
        self._create_payload_indexes(collection_name)

    def _create_payload_indexes(self, collection_name: str):
        """Create payload indexes for efficient filtering"""
        # Essential legal document fields
        index_fields = [
            ("case_name", "keyword"),  # CRITICAL for case isolation
            ("document_id", "keyword"),  # Document tracking
            ("document_type", "keyword"),  # Document categorization
            ("jurisdiction", "keyword"),  # Legal jurisdiction
            ("practice_areas", "keyword"),  # Multi-value field
            ("date_filed", "datetime"),  # Temporal filtering
            ("court_level", "keyword"),  # Court hierarchy
            ("has_citations", "bool"),  # Citation presence
            ("chunk_index", "integer"),  # Chunk ordering
            ("created_at", "datetime"),  # Processing time
        ]

        for field_name, field_type in index_fields:
            try:
                self.client.create_payload_index(
                    collection_name=collection_name,
                    field_name=field_name,
                    field_schema=field_type,
                )
                logger.debug(f"Created index for {field_name} in {collection_name}")
            except Exception as e:
                # Index might already exist
                logger.debug(f"Index {field_name} might already exist: {str(e)}")

    async def create_case_collections(self, collection_name: str) -> Dict[str, bool]:
        """
        Create all collections for a new case.

        Args:
            collection_name: Base collection name for the case

        Returns:
            Dict mapping collection name to creation success status
        """
        collections = [
            (collection_name, "Main case documents"),
            (f"{collection_name}_facts", "Extracted facts"),
            (f"{collection_name}_timeline", "Chronological events"),
            (f"{collection_name}_depositions", "Deposition citations"),
        ]

        results = {}

        for coll_name, description in collections:
            try:
                # Check length constraint (max 63 chars)
                if len(coll_name) > 63:
                    # Truncate intelligently
                    suffix_len = len(coll_name.split("_")[-1])
                    base_max_len = 62 - suffix_len - 1
                    base = coll_name[:base_max_len]
                    suffix = coll_name.split("_")[-1]
                    coll_name = f"{base}_{suffix}"

                # Check if exists
                exists = await self.async_client.collection_exists(coll_name)
                if not exists:
                    # Create based on settings
                    if settings.legal.enable_hybrid_search:
                        await self._create_hybrid_collection_async(coll_name)
                    else:
                        await self._create_standard_collection_async(coll_name)

                    # Verify creation
                    exists = await self.async_client.collection_exists(coll_name)
                    results[coll_name] = exists
                else:
                    results[coll_name] = True  # Already exists

            except Exception as e:
                logger.error(f"Failed to create collection {coll_name}: {e}")
                results[coll_name] = False

        return results

    async def _create_standard_collection_async(self, collection_name: str):
        """Async version of standard collection creation"""
        quantization_config = None
        if hasattr(settings.vector, "quantization") and settings.vector.quantization:
            quantization_config = ScalarQuantization(
                scalar=ScalarQuantizationConfig(
                    type=ScalarType.INT8, quantile=0.99, always_ram=True
                )
            )

        await self.async_client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=settings.vector.embedding_dimensions, distance=Distance.COSINE
            ),
            hnsw_config=HnswConfigDiff(
                m=settings.vector.hnsw_m,
                ef_construct=settings.vector.hnsw_ef_construct,
                on_disk=False,
                max_indexing_threads=8,
            ),
            quantization_config=quantization_config,
            on_disk_payload=False,
        )
        await self._create_payload_indexes_async(collection_name)

    async def _create_hybrid_collection_async(self, collection_name: str):
        """Async version of hybrid collection creation"""
        # Note: Using same embedding dimensions for legal_concepts as semantic for now
        # In the future, this could be configured separately
        await self.async_client.create_collection(
            collection_name=collection_name,
            vectors_config={
                "semantic": VectorParams(
                    size=settings.vector.embedding_dimensions,
                    distance=Distance.COSINE,
                    hnsw_config=HnswConfigDiff(
                        m=settings.vector.hnsw_m,
                        ef_construct=settings.vector.hnsw_ef_construct,
                    ),
                    quantization_config=ScalarQuantization(
                        scalar=ScalarQuantizationConfig(
                            type=ScalarType.INT8, quantile=0.99, always_ram=True
                        )
                    )
                    if settings.vector.quantization
                    else None,
                ),
                "legal_concepts": VectorParams(
                    size=settings.vector.embedding_dimensions, distance=Distance.COSINE
                ),
            },
            sparse_vectors_config={
                "keywords": SparseVectorParams(index=SparseIndexParams(on_disk=False)),
                "citations": SparseVectorParams(index=SparseIndexParams(on_disk=False)),
            },
            on_disk_payload=False,
        )
        await self._create_payload_indexes_async(collection_name)

    async def _create_payload_indexes_async(self, collection_name: str):
        """Async version of payload index creation"""
        indexes = [
            ("case_name", "keyword"),
            ("document_id", "keyword"),
            ("document_type", "keyword"),
            ("chunk_index", "integer"),
            ("page_number", "integer"),
            ("sentence_count", "integer"),
            ("has_citations", "bool"),
            ("citation_density", "float"),
            ("created_at", "datetime"),
        ]

        for field_name, field_type in indexes:
            try:
                await self.async_client.create_payload_index(
                    collection_name=collection_name,
                    field_name=field_name,
                    field_schema=field_type,
                )
            except Exception as e:
                logger.warning(f"Failed to create index {field_name}: {e}")

    def index_document(self, folder_name: str, document):
        """Index a document in folder-specific collection"""
        collection_name = self.ensure_collection_exists(folder_name)

        if not document:
            return []

        logger.info(f"Indexing document in folder '{folder_name}'")

        stored_ids = []
        points = []

        try:
            # Generate unique ID for document
            document_id = str(uuid.uuid4())
            stored_ids.append(document_id)

            # Get document metadata safely
            document_metadata = document.get("metadata", {})

            # Build payload with folder-based isolation
            payload = {
                # Primary fields for filtering - DO NOT NEST THESE
                "folder_name": folder_name,
                "document_id": document_id,
                # Content
                "content": document["content"],
                "search_text": document.get("search_text", document["content"]),
                # Document metadata
                "document_type": document.get("document_type", ""),
                # System metadata
                "indexed_at": datetime.utcnow().isoformat(),
                "vector_version": "1.0",
            }

            # Add document metadata fields individually to avoid overwriting critical fields
            # Skip folder_name if it exists in metadata to prevent overwriting
            for key, value in document_metadata.items():
                if key not in ["folder_name", "document_id"]:
                    payload[key] = value

            # Create point for standard collection
            if settings.legal.enable_hybrid_search:
                # For hybrid collections, we need to specify multiple vectors
                point = PointStruct(
                    id=document_id,
                    vector={
                        "semantic": document["embedding"],
                        "legal_concepts": document["embedding"],
                    },
                    payload=payload,
                )
            else:
                # For standard collections, use single vector
                point = PointStruct(
                    id=document_id, vector=document["embedding"], payload=payload
                )

            points.append(point)

            # Batch upload
            self.client.upsert(
                collection_name=collection_name, points=points, wait=True
            )

            logger.info(f"Successfully indexed {len(stored_ids)} documents")
            return stored_ids

        except Exception as e:
            logger.error(f"Error indexing document: {str(e)}")
            raise

    def _store_hybrid_document(
        self, folder_name: str, document, document_ids: List[str]
    ):
        """Store document in hybrid collection with multiple vector types"""
        try:
            hybrid_points = []

            # Extract sparse vectors if available
            keywords_sparse = document.get("keywords_sparse", {})
            citations_sparse = document.get("citations_sparse", {})

            # Get document metadata safely
            document_metadata = document.get("metadata", {})

            # Build payload - same structure as standard collection
            payload = {
                # Primary fields for filtering - DO NOT NEST THESE
                "folder_name": folder_name,
                "document_id": document_ids[0],
                "content": document["content"],
                "search_text": document.get("search_text", document["content"]),
            }

            # Add metadata fields individually
            for key, value in document_metadata.items():
                if key not in ["folder_name", "document_id"]:
                    payload[key] = value

            # Prepare sparse vectors with proper formatting
            sparse_vectors = {}

            # Format keywords sparse vector if available
            if keywords_sparse:
                sparse_vectors["keywords"] = {
                    "indices": [int(idx) for idx in keywords_sparse.keys()],
                    "values": [float(val) for val in keywords_sparse.values()],
                }
            else:
                # Provide empty sparse vector structure
                sparse_vectors["keywords"] = {"indices": [], "values": []}

            # Format citations sparse vector if available
            if citations_sparse:
                sparse_vectors["citations"] = {
                    "indices": [int(idx) for idx in citations_sparse.keys()],
                    "values": [float(val) for val in citations_sparse.values()],
                }
            else:
                # Provide empty sparse vector structure
                sparse_vectors["citations"] = {"indices": [], "values": []}

            # Create hybrid point with vectors in dictionary format
            point = PointStruct(
                id=document_ids[0],
                vector={
                    "semantic": document["embedding"],
                    "legal_concepts": document["embedding"],  # Same for now
                    **sparse_vectors,  # Add sparse vectors
                },
                payload=payload,
            )

            hybrid_points.append(point)

            # Batch upload to hybrid collection
            self.client.upsert(
                collection_name=self.get_collection_name(folder_name),
                points=hybrid_points,
                wait=True,
            )

        except Exception as e:
            logger.error(f"Error storing hybrid document: {str(e)}")
            # Don't raise - hybrid is optional enhancement

    def search_documents(
        self,
        collection_name: str,
        query_embedding: List[float],
        limit: int = 10,
        threshold: float = 0.7,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """Search for similar documents in collection (no folder filtering needed)

        Args:
            collection_name: Name of the collection to search
            query_embedding: Query vector
            limit: Maximum number of results
            threshold: Minimum similarity threshold
            filters: Additional filters to apply

        Returns:
            List of search results with similarity scores
        """
        try:
            # Validate inputs
            if not isinstance(query_embedding, (list, tuple)) or not query_embedding:
                raise ValueError(
                    f"query_embedding must be a non-empty list, got: {type(query_embedding)}"
                )

            logger.debug(
                f"Searching collection '{collection_name}' with embedding of length {len(query_embedding)}"
            )

            # Build filter if provided
            query_filter = None
            if filters:
                conditions = []
                for key, value in filters.items():
                    conditions.append(
                        FieldCondition(key=key, match=MatchValue(value=value))
                    )
                query_filter = Filter(must=conditions)
                logger.debug(f"Applied filters: {filters}")

            # Check if collection has multiple vector configurations
            try:
                collection_info = self.client.get_collection(collection_name)
                has_multiple_vectors = isinstance(
                    collection_info.config.params.vectors, dict
                )

                if has_multiple_vectors:
                    # Use named vector for hybrid collections
                    results = self.client.search(
                        collection_name=collection_name,
                        query_vector=models.NamedVector(
                            name="semantic", vector=query_embedding
                        ),
                        query_filter=query_filter,
                        limit=limit,
                        score_threshold=threshold,
                        with_payload=True,
                        with_vectors=False,
                    )
                else:
                    # Use regular vector for standard collections
                    results = self.client.search(
                        collection_name=collection_name,
                        query_vector=query_embedding,
                        query_filter=query_filter,
                        limit=limit,
                        score_threshold=threshold,
                        with_payload=True,
                        with_vectors=False,
                    )
            except Exception as e:
                logger.warning(
                    f"Could not determine collection vector config, using default: {str(e)}"
                )
                # Fallback to regular search
                results = self.client.search(
                    collection_name=collection_name,
                    query_vector=query_embedding,
                    query_filter=query_filter,
                    limit=limit,
                    score_threshold=threshold,
                    with_payload=True,
                    with_vectors=False,
                )

            # Convert to SearchResult objects
            search_results = []
            for point in results:
                search_results.append(
                    SearchResult(
                        id=str(point.id),
                        content=point.payload.get("content", ""),
                        case_name=point.payload.get("case_name", ""),
                        document_id=point.payload.get("document_id", ""),
                        score=point.score,
                        metadata=point.payload,
                        search_type="vector",
                    )
                )

            logger.debug(f"Found {len(search_results)} vector results")
            return search_results

        except Exception as e:
            logger.error(f"Error searching documents: {str(e)}")
            raise

    def reciprocal_rank_fusion_with_tracking(
        self, *result_lists, k: int = 60
    ) -> List[SearchResult]:
        """Combine multiple result lists using Reciprocal Rank Fusion while preserving ranking history

        Args:
            result_lists: Multiple lists of SearchResult objects
            k: RRF parameter (typically 60)

        Returns:
            Fused and ranked list of SearchResult objects with preserved ranking history
        """
        # Track scores for each document
        doc_scores = defaultdict(float)
        doc_objects = {}

        for results in result_lists:
            for rank, result in enumerate(results, 1):
                # RRF formula: 1 / (k + rank)
                rrf_score = 1.0 / (k + rank)
                doc_scores[result.id] += rrf_score

                # Store or merge the result object
                if result.id not in doc_objects:
                    doc_objects[result.id] = result
                else:
                    # Merge ranking history from different search types
                    existing = doc_objects[result.id]
                    for key, value in result.ranking_history.items():
                        if value is not None:
                            existing.ranking_history[key] = value
                    for key, value in result.score_history.items():
                        if value is not None:
                            existing.score_history[key] = value
                    # Keep the result with the highest individual score
                    if result.score > existing.score:
                        # Preserve merged ranking history
                        merged_ranking = existing.ranking_history.copy()
                        merged_scores = existing.score_history.copy()
                        doc_objects[result.id] = result
                        doc_objects[result.id].ranking_history.update(merged_ranking)
                        doc_objects[result.id].score_history.update(merged_scores)

        # Sort by RRF score and create final results
        fused_results = []
        for doc_id, rrf_score in sorted(
            doc_scores.items(), key=lambda x: x[1], reverse=True
        ):
            result = doc_objects[doc_id]
            # Update score to RRF score and mark as hybrid
            result.score = rrf_score
            result.search_type = "hybrid"
            fused_results.append(result)

        return fused_results

    async def cohere_rerank_with_tracking(
        self, query: str, results: List[SearchResult], top_n: int = 4
    ) -> List[SearchResult]:
        """Rerank results using Cohere Rerank v3.5 while preserving ranking history

        Args:
            query: Original search query
            results: List of SearchResult objects to rerank
            top_n: Number of top results to return

        Returns:
            Reranked list of SearchResult objects with preserved ranking history
        """
        if not self.cohere_client or not results:
            logger.warning("Cohere client not available or no results to rerank")
            return results[:top_n]

        try:
            # Prepare documents for reranking
            documents = []
            for result in results:
                # Format document content for Cohere
                doc_text = result.content
                if result.metadata.get("document_type"):
                    doc_text = (
                        f"Document Type: {result.metadata['document_type']}\n{doc_text}"
                    )
                documents.append(doc_text)

            # Call Cohere Rerank API
            response = self.cohere_client.rerank(
                model="rerank-v3.5",
                query=query,
                documents=documents,
                top_n=min(top_n, len(documents)),
            )

            # Map reranked results back to SearchResult objects
            reranked_results = []
            for rerank_result in response.results:
                original_result = results[rerank_result.index]
                # Update score with Cohere relevance score
                original_result.score = rerank_result.relevance_score
                original_result.search_type = "reranked"
                original_result.score_history["cohere_score"] = (
                    rerank_result.relevance_score
                )
                reranked_results.append(original_result)

            logger.debug(
                f"Reranked {len(results)} results to top {len(reranked_results)}"
            )
            return reranked_results

        except Exception as e:
            logger.error(f"Error in Cohere reranking: {str(e)}")
            # Fallback to original results
            return results[:top_n]

    async def hybrid_search(
        self,
        collection_name: str,
        query: str,
        query_embedding: List[float],
        limit: int = 20,
        final_limit: int = 4,
        enable_reranking: bool = True,
    ) -> List[SearchResult]:
        """Perform comprehensive hybrid search with RRF and optional Cohere reranking

        Now includes ranking tracking at each stage of the pipeline.

        Args:
            collection_name: Name of the collection to search
            query: Original text query
            query_embedding: Dense vector for semantic search
            limit: Number of results to retrieve for RRF (default 20)
            final_limit: Final number of results to return (default 4)
            enable_reranking: Whether to use Cohere reranking (default True)

        Returns:
            List of reranked SearchResult objects with ranking history
        """
        try:
            # Ensure collection exists - create if it doesn't
            if not self.client.collection_exists(collection_name):
                logger.warning(
                    f"Collection {collection_name} does not exist. Creating it..."
                )
                try:
                    self.create_collection(collection_name)
                    logger.info(f"Successfully created collection: {collection_name}")
                except Exception as create_error:
                    logger.error(
                        f"Failed to create collection {collection_name}: {str(create_error)}"
                    )
                    # Try creating with minimal configuration as fallback
                    self._create_minimal_collection(collection_name)
                    logger.info(f"Created minimal collection: {collection_name}")

            # Generate sparse vectors for keyword and citation search
            keywords_sparse, citations_sparse = (
                self.sparse_encoder.encode_for_hybrid_search(query)
            )

            # 1. Semantic search using dense vectors
            semantic_results = []
            try:
                semantic_results = self.search_documents(
                    collection_name=collection_name,
                    query_embedding=query_embedding,
                    limit=limit,
                    threshold=0.0,  # Lower threshold for RRF
                )

                # Add ranking information
                for rank, result in enumerate(semantic_results, 1):
                    result.ranking_history["semantic_rank"] = rank
                    result.score_history["semantic_score"] = result.score

                logger.debug(
                    f"Semantic search returned {len(semantic_results)} results"
                )
            except Exception as e:
                logger.error(f"Semantic search failed: {str(e)}")
                # If semantic search fails, return empty results
                return []

            # Check if collection supports sparse vectors
            try:
                collection_info = self.client.get_collection(collection_name)
                params = collection_info.config.params
                has_sparse_vectors = bool(getattr(params, "sparse_vectors", None))
                logger.debug(
                    f"Collection {collection_name} sparse vector support: {has_sparse_vectors}"
                )
            except Exception as e:
                logger.warning(f"Could not check collection info: {str(e)}")
                has_sparse_vectors = False

            # 2. Keyword search using sparse vectors (only if supported)
            keyword_results = []
            if keywords_sparse and has_sparse_vectors:
                try:
                    # Ensure we have valid indices and values
                    indices = [int(k) for k in keywords_sparse.keys()]
                    values = [float(v) for v in keywords_sparse.values()]

                    if indices and values and len(indices) == len(values):
                        keyword_search_results = self.client.search(
                            collection_name=collection_name,
                            query_vector=models.NamedSparseVector(
                                name="keywords",
                                vector=models.SparseVector(
                                    indices=indices, values=values
                                ),
                            ),
                            limit=limit,
                            with_payload=True,
                            with_vectors=False,
                        )

                        for rank, point in enumerate(keyword_search_results, 1):
                            result = SearchResult(
                                id=str(point.id),
                                content=point.payload.get("content", ""),
                                case_name=point.payload.get("case_name", ""),
                                document_id=point.payload.get("document_id", ""),
                                score=point.score,
                                metadata=point.payload,
                                search_type="keyword",
                            )
                            result.ranking_history["keyword_rank"] = rank
                            result.score_history["keyword_score"] = point.score
                            keyword_results.append(result)

                        logger.debug(
                            f"Keyword search returned {len(keyword_results)} results"
                        )
                    else:
                        logger.warning("Invalid sparse vector data for keyword search")
                except Exception as e:
                    logger.warning(f"Keyword search failed: {str(e)}")
            else:
                logger.debug(
                    "Skipping keyword search - no sparse vector support or empty vectors"
                )

            # 3. Citation search using sparse vectors (only if supported)
            citation_results = []
            if citations_sparse and has_sparse_vectors:
                try:
                    # Ensure we have valid indices and values
                    indices = [int(k) for k in citations_sparse.keys()]
                    values = [float(v) for v in citations_sparse.values()]

                    if indices and values and len(indices) == len(values):
                        citation_search_results = self.client.search(
                            collection_name=collection_name,
                            query_vector=models.NamedSparseVector(
                                name="citations",
                                vector=models.SparseVector(
                                    indices=indices, values=values
                                ),
                            ),
                            limit=limit,
                            with_payload=True,
                            with_vectors=False,
                        )

                        for rank, point in enumerate(citation_search_results, 1):
                            result = SearchResult(
                                id=str(point.id),
                                content=point.payload.get("content", ""),
                                case_name=point.payload.get("case_name", ""),
                                document_id=point.payload.get("document_id", ""),
                                score=point.score,
                                metadata=point.payload,
                                search_type="citation",
                            )
                            result.ranking_history["citation_rank"] = rank
                            result.score_history["citation_score"] = point.score
                            citation_results.append(result)

                        logger.debug(
                            f"Citation search returned {len(citation_results)} results"
                        )
                    else:
                        logger.warning("Invalid sparse vector data for citation search")
                except Exception as e:
                    logger.warning(f"Citation search failed: {str(e)}")
            else:
                logger.debug(
                    "Skipping citation search - no sparse vector support or empty vectors"
                )

            # 4. Apply Reciprocal Rank Fusion with ranking tracking
            search_lists = [semantic_results]
            if keyword_results:
                search_lists.append(keyword_results)
            if citation_results:
                search_lists.append(citation_results)

            fused_results = self.reciprocal_rank_fusion_with_tracking(*search_lists)

            # Add RRF ranking
            for rank, result in enumerate(fused_results, 1):
                result.ranking_history["rrf_rank"] = rank
                result.score_history["rrf_score"] = result.score

            # Take top results for reranking
            top_results = fused_results[:limit]

            # 5. Optional Cohere reranking
            if (
                enable_reranking
                and self.cohere_client
                and len(top_results) > final_limit
            ):
                final_results = await self.cohere_rerank_with_tracking(
                    query, top_results, final_limit
                )
            else:
                final_results = top_results[:final_limit]

            # Add final ranking
            for rank, result in enumerate(final_results, 1):
                result.ranking_history["final_rank"] = rank

            # Log ranking journey for top results
            logger.info(
                f"Hybrid search completed: {len(semantic_results)} semantic, {len(keyword_results)} keyword, {len(citation_results)} citation -> {len(final_results)} final"
            )

            for i, result in enumerate(final_results[:3], 1):  # Log top 3
                logger.debug(
                    f"Result {i} ranking journey: "
                    f"Semantic #{result.ranking_history.get('semantic_rank', 'N/A')}, "
                    f"Keyword #{result.ranking_history.get('keyword_rank', 'N/A')}, "
                    f"Citation #{result.ranking_history.get('citation_rank', 'N/A')} -> "
                    f"RRF #{result.ranking_history.get('rrf_rank', 'N/A')} -> "
                    f"Final #{result.ranking_history.get('final_rank', 'N/A')}"
                )

            return final_results

        except Exception as e:
            logger.error(f"Error in hybrid search: {str(e)}")
            # Fallback to semantic search only
            return self.search_documents(
                collection_name=collection_name,
                query_embedding=query_embedding,
                limit=final_limit,
            )

    def _process_results(self, results):
        # Convert to SearchResult objects
        search_results = []
        for point in results:
            search_results.append(
                SearchResult(
                    id=str(point.id),
                    content=point.payload.get("content", ""),
                    case_name=point.payload.get("case_name", ""),
                    document_id=point.payload.get("document_id", ""),
                    score=point.score,
                    metadata=point.payload,
                    search_type="hybrid",
                )
            )

        return search_results

    def _combine_search_results(self, results: List, limit: int):
        """Combine search results by sorting by score, handling both ScoredPoint and tuples"""
        # Convert tuples to ScoredPoint if necessary
        from qdrant_client.models import ScoredPoint

        converted_results = []
        for item in results:
            if isinstance(item, ScoredPoint):
                converted_results.append(item)
            elif isinstance(item, tuple):
                # Try to convert tuple to ScoredPoint
                # Assuming the tuple has the same order as ScoredPoint fields
                if len(item) >= 6:
                    # We'll create a ScoredPoint object from the tuple
                    try:
                        scored_point = ScoredPoint(
                            id=item[0],
                            version=item[1],
                            score=item[2],
                            payload=item[3],
                            vector=item[4] if len(item) > 4 else None,
                            vector_name=item[5] if len(item) > 5 else None,
                        )
                        converted_results.append(scored_point)
                    except Exception as e:
                        logger.error(f"Error converting tuple to ScoredPoint: {e}")
                else:
                    logger.error(
                        "Cannot convert tuple to ScoredPoint: insufficient fields"
                    )
            else:
                logger.error(f"Unsupported result type: {type(item)}")

        # Sort by score
        sorted_results = sorted(converted_results, key=lambda x: x.score, reverse=True)
        return sorted_results[:limit]

    def delete_document_vectors(self, folder_name: str, document_id: str) -> int:
        """Delete all vectors for a specific document

        Args:
            folder_name: Folder name (for verification)
            document_id: Document to delete

        Returns:
            Number of vectors deleted
        """
        try:
            # Build filter for document within folder
            standard_filter = Filter(
                must=[
                    FieldCondition(
                        key="folder_name", match=MatchValue(value=folder_name)
                    ),
                    FieldCondition(
                        key="document_id", match=MatchValue(value=document_id)
                    ),
                ]
            )

            # Count before deletion
            count_before = self.client.count(
                collection_name=self.get_collection_name(folder_name),
                count_filter=standard_filter,
            ).count

            # Delete points
            self.client.delete(
                collection_name=self.get_collection_name(folder_name),
                points_selector=standard_filter,
            )

            # Also delete from hybrid collection
            if settings.legal.enable_hybrid_search:
                try:
                    self.client.delete(
                        collection_name=self.get_collection_name(folder_name),
                        points_selector=standard_filter,
                    )
                except Exception as e:
                    logger.warning(f"Could not delete from hybrid collection: {str(e)}")

            logger.info(f"Deleted {count_before} vectors for document {document_id}")
            return count_before

        except Exception as e:
            logger.error(f"Error deleting document vectors: {str(e)}")
            raise

    def store_document_chunks(
        self,
        case_name: str,
        document_id: str,
        chunks: List[Dict[str, Any]],
        use_hybrid: bool = False,
    ) -> List[str]:
        """Store multiple chunks for a document in the case-specific collection

        Args:
            case_name: Case name (used as collection name after sanitization)
            document_id: Unique document identifier
            chunks: List of chunk dictionaries with embeddings and metadata
            use_hybrid: Whether to use hybrid search features

        Returns:
            List of chunk IDs that were stored
        """
        if not chunks:
            return []

        # Ensure collection exists for this case
        # Use legacy naming to avoid double hashing issue
        collection_name = self.ensure_collection_exists(case_name, use_case_manager=False)

        logger.info(
            f"Storing {len(chunks)} chunks for document {document_id} in collection '{collection_name}'"
        )

        stored_ids = []
        points = []

        # Generate base ID using timestamp + hash for uniqueness
        # This ensures unique IDs even if multiple documents are processed simultaneously
        timestamp_part = int(
            datetime.utcnow().timestamp() * 1000
        )  # Millisecond precision
        hash_part = abs(hash(document_id)) % 1000000  # 6 digits from doc hash
        base_id = timestamp_part * 1000000 + hash_part

        try:
            for i, chunk in enumerate(chunks):
                # Generate unique integer ID for this chunk
                chunk_id = base_id + i
                stored_ids.append(str(chunk_id))

                # Get chunk metadata safely
                chunk_metadata = chunk.get("metadata", {})

                # Build comprehensive payload
                payload = {
                    # Primary identifiers
                    "case_name": case_name,
                    "document_id": document_id,
                    "chunk_index": i,
                    "chunk_reference": f"{document_id}_{i}",
                    # Content fields
                    "content": chunk["content"],
                    "search_text": chunk.get("search_text", chunk["content"]),
                    # Document metadata
                    "document_name": chunk_metadata.get("document_name", ""),
                    "document_type": chunk_metadata.get("document_type", ""),
                    "document_path": chunk_metadata.get("document_path", ""),
                    "document_link": chunk_metadata.get("document_link", ""),
                    "subfolder": chunk_metadata.get("subfolder", "root"),
                    "folder_path": chunk_metadata.get("folder_path", ""),
                    # Processing metadata
                    "has_context": chunk_metadata.get("has_context", False),
                    "original_length": chunk_metadata.get("original_length", 0),
                    "context_length": chunk_metadata.get("context_length", 0),
                    # Legal entity flags
                    "has_citations": chunk_metadata.get("has_citations", False),
                    "citation_count": chunk_metadata.get("citation_count", 0),
                    "has_monetary": chunk_metadata.get("has_monetary", False),
                    "has_dates": chunk_metadata.get("has_dates", False),
                    # Document info
                    "page_count": chunk_metadata.get("page_count", 0),
                    "file_size": chunk_metadata.get("file_size", 0),
                    "modified_at": chunk_metadata.get("modified_at", ""),
                    # System metadata
                    "indexed_at": datetime.utcnow().isoformat(),
                    "vector_version": "1.0",
                    "total_chunks": chunk_metadata.get("total_chunks", len(chunks)),
                }

                # Create point based on collection type
                if getattr(settings.legal, "enable_hybrid_search", False):
                    # For hybrid collections - prepare vectors dictionary
                    vectors = {"semantic": chunk["embedding"]}

                    # Only add legal_concepts if it's different from semantic
                    # For now, they're the same, so we'll skip to save space
                    # vectors["legal_concepts"] = chunk["embedding"]

                    # Handle sparse vectors if present and valid
                    if "keywords_sparse" in chunk and isinstance(
                        chunk["keywords_sparse"], dict
                    ):
                        sparse_indices, sparse_values = self._convert_sparse_to_lists(
                            chunk["keywords_sparse"]
                        )
                        if sparse_indices:  # Only add if we have valid data
                            try:
                                vectors["keywords"] = SparseVector(
                                    indices=sparse_indices, values=sparse_values
                                )
                            except Exception as e:
                                logger.warning(
                                    f"Could not add keywords sparse vector: {e}"
                                )

                    if "citations_sparse" in chunk and isinstance(
                        chunk["citations_sparse"], dict
                    ):
                        sparse_indices, sparse_values = self._convert_sparse_to_lists(
                            chunk["citations_sparse"]
                        )
                        if sparse_indices:
                            try:
                                vectors["citations"] = SparseVector(
                                    indices=sparse_indices, values=sparse_values
                                )
                            except Exception as e:
                                logger.warning(
                                    f"Could not add citations sparse vector: {e}"
                                )

                    # Create point with multiple vectors
                    point = PointStruct(id=chunk_id, vector=vectors, payload=payload)
                else:
                    # Standard collection - single embedding vector
                    point = PointStruct(
                        id=chunk_id, vector=chunk["embedding"], payload=payload
                    )

                points.append(point)

            # Batch upload all points
            self.client.upsert(
                collection_name=collection_name, points=points, wait=True
            )

            logger.info(
                f"Successfully stored {len(stored_ids)} chunks in collection '{collection_name}'"
            )

            return stored_ids

        except Exception as e:
            logger.error(f"Error storing document chunks: {str(e)}")
            # Only log collection name if it was successfully created
            if "collection_name" in locals():
                logger.error(f"Collection: {collection_name}, Document: {document_id}")
            else:
                logger.error(f"Case: {case_name}, Document: {document_id}")
            if "points" in locals() and points:
                logger.debug(f"Failed with {len(points)} points prepared")
            raise

    def _convert_sparse_to_lists(
        self, sparse_dict: Dict[Any, float]
    ) -> Tuple[List[int], List[float]]:
        """Convert sparse vector dictionary to lists of indices and values

        Args:
            sparse_dict: Dictionary with either int or string keys

        Returns:
            Tuple of (indices, values) lists
        """
        indices = []
        values = []

        try:
            for key, value in sparse_dict.items():
                if isinstance(key, int):
                    # Already an integer index
                    indices.append(key)
                    values.append(float(value))
                elif isinstance(key, str) and key.isdigit():
                    # String that represents an integer
                    indices.append(int(key))
                    values.append(float(value))
                else:
                    # String key - hash to index
                    # Use consistent hashing for reproducibility
                    idx = abs(hash(str(key))) % 100000
                    indices.append(idx)
                    values.append(float(value))

            # Sort by indices for consistency
            if indices:
                sorted_pairs = sorted(zip(indices, values), key=lambda x: x[0])
                indices, values = zip(*sorted_pairs)
                return list(indices), list(values)

        except Exception as e:
            logger.warning(f"Error converting sparse vector: {e}")

        return [], []

    def _convert_sparse_vector_for_storage(
        self, sparse_dict: Dict[str, float]
    ) -> Dict[str, List]:
        """Convert string-keyed sparse vector to Qdrant format

        The sparse encoder returns vectors with string keys (tokens),
        but Qdrant needs integer indices.

        Args:
            sparse_dict: Dictionary with string keys and float values

        Returns:
            Dictionary with 'indices' and 'values' lists
        """
        # For now, we'll use a simple hash-based approach
        # In production, you'd want a consistent vocabulary mapping
        indices = []
        values = []

        for token, value in sparse_dict.items():
            # Simple hash to get an index (mod by large prime for distribution)
            index = abs(hash(token)) % 1000000
            indices.append(index)
            values.append(float(value))

        return {"indices": indices, "values": values}

    def sanitize_collection_name(self, case_name: str) -> str:
        """Sanitize and truncate collection name for Qdrant

        Args:
            case_name: Original case/folder name

        Returns:
            Sanitized collection name (max 63 chars, alphanumeric + underscore)
        """
        # Remove special characters, keep only alphanumeric and spaces
        sanitized = re.sub(r"[^a-zA-Z0-9\s]", "", case_name)

        # Replace spaces with underscores
        sanitized = re.sub(r"\s+", "_", sanitized.strip())

        # Remove multiple underscores
        sanitized = re.sub(r"_+", "_", sanitized)

        # Convert to lowercase for consistency
        sanitized = sanitized.lower()

        # Handle empty result
        if not sanitized:
            sanitized = "unnamed_case"

        # If name is too long, truncate and add hash
        max_length = 63  # Safe limit for most filesystems

        if len(sanitized) > max_length:
            # Keep first part of name and add hash suffix
            hash_suffix = hashlib.md5(case_name.encode()).hexdigest()[:8]

            # Calculate how much of the name we can keep
            # Format: name_hash (1 underscore + 8 chars for hash)
            available_length = max_length - 9

            sanitized = f"{sanitized[:available_length]}_{hash_suffix}"

        # Ensure it doesn't start with a number (some systems don't like this)
        if sanitized[0].isdigit():
            sanitized = f"case_{sanitized}"

        # Final length check
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length]

        logger.debug(f"Collection name: '{case_name}' -> '{sanitized}'")

        return sanitized

    def get_case_name_mapping(self) -> Dict[str, str]:
        """Get mapping of sanitized collection names to original case names

        Returns:
            Dictionary mapping collection names to original case names
        """
        try:
            # Get all collections
            collections = self.client.get_collections().collections

            mapping = {}
            for collection in collections:
                # Try to get original case name from collection metadata
                try:
                    # First, check if we stored the original name in the collection
                    # This would require updating the create_collection method
                    info = self.client.get_collection(collection.name)

                    # For now, just store the collection name
                    mapping[collection.name] = collection.name

                except Exception as e:
                    logger.debug(
                        f"Could not get info for collection {collection.name}: {e}"
                    )
                    mapping[collection.name] = collection.name

            return mapping

        except Exception as e:
            logger.error(f"Error getting case name mapping: {str(e)}")
            return {}

    def list_cases(self, include_shared: bool = False) -> List[Dict[str, Any]]:
        """List all cases (collections) in the system

        Args:
            include_shared: Whether to include shared resource collections

        Returns:
            List of case information dictionaries
        """
        # Import here to avoid circular dependency
        from src.config.shared_resources import is_shared_resource

        try:
            collections = self.client.get_collections().collections
            cases = []

            for collection in collections:
                # Skip shared resources unless explicitly requested
                if not include_shared and is_shared_resource(collection.name):
                    continue

                try:
                    # Get collection info
                    info = self.client.get_collection(collection.name)

                    case_info = {
                        "collection_name": collection.name,
                        "original_name": collection.name,  # Would be from metadata
                        "vector_count": info.vectors_count,
                        "points_count": info.points_count,
                        "indexed_vectors_count": getattr(
                            info, "indexed_vectors_count", 0
                        ),
                        "status": info.status,
                        "is_shared": is_shared_resource(collection.name),
                    }

                    cases.append(case_info)

                except Exception as e:
                    logger.warning(f"Could not get details for {collection.name}: {e}")
                    cases.append(
                        {
                            "collection_name": collection.name,
                            "error": str(e),
                            "is_shared": is_shared_resource(collection.name),
                        }
                    )

            return cases

        except Exception as e:
            logger.error(f"Error listing cases: {str(e)}")
            return []

    def get_folder_statistics(self, folder_name: str) -> Dict[str, Any]:
        """Get statistics for a specific folder

        Args:
            folder_name: Folder to get statistics for

        Returns:
            Dictionary with folder statistics
        """
        try:
            folder_filter = Filter(
                must=[
                    FieldCondition(
                        key="folder_name", match=MatchValue(value=folder_name)
                    )
                ]
            )

            # Get counts
            total_chunks = self.client.count(
                collection_name=self.get_collection_name(folder_name),
                count_filter=folder_filter,
            ).count

            # Get unique documents (this is approximate)
            # In production, you might want to maintain a separate index
            search_results = self.client.scroll(
                collection_name=self.get_collection_name(folder_name),
                scroll_filter=folder_filter,
                limit=10000,  # Adjust based on expected folder size
                with_payload=["document_id"],
                with_vectors=False,
            )

            unique_documents = set()
            for point in search_results[0]:
                unique_documents.add(point.payload.get("document_id"))

            return {
                "folder_name": folder_name,
                "total_chunks": total_chunks,
                "unique_documents": len(unique_documents),
                "document_ids": list(unique_documents),
            }

        except Exception as e:
            logger.error(f"Error getting folder statistics: {str(e)}")
            return {
                "folder_name": folder_name,
                "total_chunks": 0,
                "unique_documents": 0,
                "error": str(e),
            }

    def optimize_collection(self, folder_name: str):
        """Optimize collection for better performance"""
        try:
            logger.info("Starting collection optimization...")

            # Update optimizer config for faster indexing
            self.client.update_collection(
                collection_name=self.get_collection_name(folder_name),
                optimizer_config=OptimizersConfigDiff(
                    indexing_threshold=50000,
                    flush_interval_sec=5,
                    max_optimization_threads=8,
                ),
            )

            # Trigger optimization
            self.client.update_collection(
                collection_name=self.get_collection_name(folder_name),
                optimizers_config=OptimizersConfigDiff(max_optimization_threads=8),
            )

            logger.info("Collection optimization completed")

        except Exception as e:
            logger.error(f"Error optimizing collection: {str(e)}")
            raise

    def close(self):
        """Close client connections"""
        try:
            if hasattr(self.async_client, "close"):
                asyncio.run(self.async_client.close())
            logger.info("Closed Qdrant connections")
        except Exception as e:
            logger.warning(f"Error closing connections: {str(e)}")

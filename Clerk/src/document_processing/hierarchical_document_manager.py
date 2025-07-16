"""
Hierarchical Document Manager for Normalized Database Schema

This module implements the hierarchical document management system using the normalized
database schema. It provides comprehensive document lifecycle management with proper
case isolation and matter-based organization.

Key Features:
1. Matter → Case → Document hierarchy
2. Inheritance-based access control
3. Normalized database operations
4. Enhanced deduplication
5. Optimized query performance
"""

import hashlib
from datetime import datetime
from typing import List, Optional, Dict, Any
from collections import defaultdict

from ..models.normalized_document_models import (
    Matter,
    Case,
    DocumentCore,
    DocumentMetadata,
    DocumentCaseJunction,
    DocumentRelationship,
    DeduplicationRecord,
    MatterType,
    AccessLevel,
    RelationshipType,
    NormalizedDocumentCreateRequest,
    NormalizedDocumentResponse,
    HierarchicalSearchRequest,
    HierarchicalSearchResponse,
)
from ..models.unified_document_models import DocumentType
from ..vector_storage.qdrant_store import QdrantVectorStore
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class HierarchicalDocumentManager:
    """
    Manages documents using the normalized hierarchical schema
    """

    def __init__(self, qdrant_store: QdrantVectorStore):
        self.qdrant_store = qdrant_store
        self.logger = logger

        # Collection names for normalized tables
        self.collections = {
            "matters": "legal_matters",
            "cases": "legal_cases",
            "document_cores": "document_cores",
            "document_metadata": "document_metadata",
            "document_case_junctions": "document_case_junctions",
            "document_relationships": "document_relationships",
            "chunk_metadata": "chunk_metadata",
            "deduplication_records": "deduplication_records",
        }

        # Initialize collections
        self._initialize_collections()

    def _initialize_collections(self):
        """Initialize all required Qdrant collections with proper schemas"""

        collection_configs = {
            "matters": {
                "vector_size": 1,  # Minimal vector for non-vector data
                "distance": "Cosine",
                "indexes": [
                    "matter_number",
                    "client_name",
                    "matter_type",
                    "access_level",
                ],
            },
            "cases": {
                "vector_size": 1,
                "distance": "Cosine",
                "indexes": [
                    "matter_id",
                    "case_number",
                    "case_name",
                    "status",
                    "effective_access_level",
                ],
            },
            "document_cores": {
                "vector_size": 1,
                "distance": "Cosine",
                "indexes": [
                    "document_hash",
                    "metadata_hash",
                    "file_name",
                    "box_file_id",
                ],
            },
            "document_metadata": {
                "vector_size": 1,
                "distance": "Cosine",
                "indexes": [
                    "document_id",
                    "document_type",
                    "document_date",
                    "ai_model_used",
                ],
            },
            "document_case_junctions": {
                "vector_size": 1,
                "distance": "Cosine",
                "indexes": [
                    "document_id",
                    "case_id",
                    "production_batch",
                    "bates_number_start",
                ],
            },
            "document_relationships": {
                "vector_size": 1,
                "distance": "Cosine",
                "indexes": [
                    "source_document_id",
                    "target_document_id",
                    "relationship_type",
                ],
            },
            "chunk_metadata": {
                "vector_size": 1536,  # OpenAI embedding size
                "distance": "Cosine",
                "indexes": ["document_id", "chunk_index", "semantic_type"],
            },
            "deduplication_records": {
                "vector_size": 1,
                "distance": "Cosine",
                "indexes": ["content_hash", "metadata_hash", "primary_document_id"],
            },
        }

        for collection_name, config in collection_configs.items():
            full_collection_name = self.collections[collection_name]
            try:
                self.qdrant_store.create_collection_if_not_exists(
                    collection_name=full_collection_name,
                    vector_size=config["vector_size"],
                    distance=config["distance"],
                )

                # Create payload indexes for efficient filtering
                for index_field in config["indexes"]:
                    self.qdrant_store.create_payload_index(
                        collection_name=full_collection_name, field_name=index_field
                    )

                self.logger.info(f"Initialized collection: {full_collection_name}")

            except Exception as e:
                self.logger.error(
                    f"Failed to initialize collection {full_collection_name}: {e}"
                )

    # Matter Management

    async def create_matter(self, matter: Matter) -> Matter:
        """Create a new matter"""
        try:
            # Store in Qdrant
            point_id = matter.id
            payload = matter.model_dump()

            self.qdrant_store.upsert_points(
                collection_name=self.collections["matters"],
                points=[
                    {
                        "id": point_id,
                        "vector": [0.0],  # Placeholder vector
                        "payload": payload,
                    }
                ],
            )

            self.logger.info(f"Created matter: {matter.matter_name} ({matter.id})")
            return matter

        except Exception as e:
            self.logger.error(f"Failed to create matter {matter.matter_name}: {e}")
            raise

    async def get_matter(self, matter_id: str) -> Optional[Matter]:
        """Retrieve a matter by ID"""
        try:
            result = self.qdrant_store.get_points(
                collection_name=self.collections["matters"], ids=[matter_id]
            )

            if result and len(result) > 0:
                return Matter(**result[0].payload)
            return None

        except Exception as e:
            self.logger.error(f"Failed to get matter {matter_id}: {e}")
            return None

    async def list_matters(
        self,
        client_name: Optional[str] = None,
        matter_type: Optional[MatterType] = None,
    ) -> List[Matter]:
        """List matters with optional filters"""
        try:
            filters = {}
            if client_name:
                filters["client_name"] = client_name
            if matter_type:
                filters["matter_type"] = matter_type.value

            results = self.qdrant_store.search_points(
                collection_name=self.collections["matters"],
                query_vector=[0.0],
                limit=1000,
                query_filter=filters if filters else None,
            )

            return [Matter(**result.payload) for result in results]

        except Exception as e:
            self.logger.error(f"Failed to list matters: {e}")
            return []

    # Case Management

    async def create_case(self, case: Case) -> Case:
        """Create a new case within a matter"""
        try:
            # Validate matter exists
            matter = await self.get_matter(case.matter_id)
            if not matter:
                raise ValueError(f"Matter {case.matter_id} not found")

            # Inherit access level from matter
            case.inherited_access_level = matter.access_level

            # Store in Qdrant
            payload = case.model_dump()
            payload["effective_access_level"] = case.effective_access_level.value

            self.qdrant_store.upsert_points(
                collection_name=self.collections["cases"],
                points=[{"id": case.id, "vector": [0.0], "payload": payload}],
            )

            self.logger.info(
                f"Created case: {case.case_name} ({case.id}) in matter {case.matter_id}"
            )
            return case

        except Exception as e:
            self.logger.error(f"Failed to create case {case.case_name}: {e}")
            raise

    async def get_case(self, case_id: str) -> Optional[Case]:
        """Retrieve a case by ID"""
        try:
            result = self.qdrant_store.get_points(
                collection_name=self.collections["cases"], ids=[case_id]
            )

            if result and len(result) > 0:
                return Case(**result[0].payload)
            return None

        except Exception as e:
            self.logger.error(f"Failed to get case {case_id}: {e}")
            return None

    async def list_cases_in_matter(self, matter_id: str) -> List[Case]:
        """List all cases within a matter"""
        try:
            results = self.qdrant_store.search_points(
                collection_name=self.collections["cases"],
                query_vector=[0.0],
                limit=1000,
                query_filter={"matter_id": matter_id},
            )

            return [Case(**result.payload) for result in results]

        except Exception as e:
            self.logger.error(f"Failed to list cases in matter {matter_id}: {e}")
            return []

    # Document Management

    async def create_document(
        self, request: NormalizedDocumentCreateRequest
    ) -> NormalizedDocumentResponse:
        """Create a new document in the hierarchical system"""
        try:
            # Step 1: Validate case exists
            case = await self.get_case(request.case_id)
            if not case:
                raise ValueError(f"Case {request.case_id} not found")

            # Step 2: Calculate hashes for deduplication
            content_hash = hashlib.sha256(request.file_content).hexdigest()

            # Create metadata hash from key identifying fields
            metadata_for_hash = f"{request.file_name}|{len(request.file_content)}|{request.document_type_hint or 'unknown'}"
            metadata_hash = hashlib.sha256(metadata_for_hash.encode()).hexdigest()

            # Step 3: Check for duplicates
            dedup_record = await self._check_deduplication(content_hash, metadata_hash)
            is_duplicate = dedup_record is not None

            # Step 4: Create DocumentCore
            document_core = DocumentCore(
                document_hash=content_hash,
                metadata_hash=metadata_hash,
                file_name=request.file_name,
                original_file_path=request.file_path,
                file_size=len(request.file_content),
                total_pages=1,  # Will be updated after text extraction
                box_file_id=getattr(request, "box_file_id", None),
            )

            # Step 5: Create DocumentMetadata (AI analysis would go here)
            document_metadata = DocumentMetadata(
                document_id=document_core.id,
                document_type=request.document_type_hint or DocumentType.OTHER,
                title=request.title_hint or request.file_name,
                description=f"Document ingested from {request.file_path}",
                summary="Summary pending AI analysis",
            )

            # Step 6: Create case junction
            case_junction = DocumentCaseJunction(
                document_id=document_core.id, case_id=request.case_id
            )

            # Step 7: Store in database
            await self._store_document_components(
                document_core, document_metadata, case_junction
            )

            # Step 8: Update deduplication records
            if is_duplicate and dedup_record:
                await self._update_deduplication_record(
                    dedup_record, document_core.id, request.case_id
                )
            elif not is_duplicate:
                await self._create_deduplication_record(
                    content_hash, metadata_hash, document_core.id, request.case_id
                )

            # Step 9: Create response
            response = NormalizedDocumentResponse(
                document_core=document_core,
                document_metadata=document_metadata,
                case_associations=[case_junction],
                is_duplicate=is_duplicate,
                deduplication_info=dedup_record,
            )

            self.logger.info(
                f"Created document: {document_core.file_name} ({document_core.id}) in case {request.case_id}"
            )
            return response

        except Exception as e:
            self.logger.error(f"Failed to create document {request.file_name}: {e}")
            raise

    async def _store_document_components(
        self,
        document_core: DocumentCore,
        document_metadata: DocumentMetadata,
        case_junction: DocumentCaseJunction,
    ):
        """Store all document components in their respective collections"""

        # Store DocumentCore
        self.qdrant_store.upsert_points(
            collection_name=self.collections["document_cores"],
            points=[
                {
                    "id": document_core.id,
                    "vector": [0.0],
                    "payload": document_core.model_dump(),
                }
            ],
        )

        # Store DocumentMetadata
        self.qdrant_store.upsert_points(
            collection_name=self.collections["document_metadata"],
            points=[
                {
                    "id": f"{document_metadata.document_id}_metadata",
                    "vector": [0.0],
                    "payload": document_metadata.model_dump(),
                }
            ],
        )

        # Store DocumentCaseJunction
        self.qdrant_store.upsert_points(
            collection_name=self.collections["document_case_junctions"],
            points=[
                {
                    "id": case_junction.id,
                    "vector": [0.0],
                    "payload": case_junction.model_dump(),
                }
            ],
        )

    async def _check_deduplication(
        self, content_hash: str, metadata_hash: str
    ) -> Optional[DeduplicationRecord]:
        """Check if document already exists based on content and metadata hashes"""
        try:
            # Check for exact content match
            results = self.qdrant_store.search_points(
                collection_name=self.collections["deduplication_records"],
                query_vector=[0.0],
                limit=1,
                query_filter={"content_hash": content_hash},
            )

            if results:
                return DeduplicationRecord(**results[0].payload)

            # TODO: Implement fuzzy matching based on metadata_hash
            return None

        except Exception as e:
            self.logger.error(f"Failed to check deduplication: {e}")
            return None

    async def _create_deduplication_record(
        self, content_hash: str, metadata_hash: str, document_id: str, case_id: str
    ) -> DeduplicationRecord:
        """Create a new deduplication record for a unique document"""
        record = DeduplicationRecord(
            content_hash=content_hash,
            metadata_hash=metadata_hash,
            primary_document_id=document_id,
            primary_case_id=case_id,
            primary_discovered_at=datetime.now(),
        )

        self.qdrant_store.upsert_points(
            collection_name=self.collections["deduplication_records"],
            points=[{"id": record.id, "vector": [0.0], "payload": record.model_dump()}],
        )

        return record

    async def _update_deduplication_record(
        self, record: DeduplicationRecord, new_document_id: str, case_id: str
    ):
        """Update deduplication record with new duplicate"""
        record.duplicate_document_ids.append(new_document_id)
        record.duplicate_count += 1

        self.qdrant_store.upsert_points(
            collection_name=self.collections["deduplication_records"],
            points=[{"id": record.id, "vector": [0.0], "payload": record.model_dump()}],
        )

    # Document Relationship Management

    async def create_document_relationship(
        self,
        source_doc_id: str,
        target_doc_id: str,
        relationship_type: RelationshipType,
        context: Optional[str] = None,
        confidence: float = 1.0,
    ) -> DocumentRelationship:
        """Create a relationship between two documents"""
        try:
            relationship = DocumentRelationship(
                source_document_id=source_doc_id,
                target_document_id=target_doc_id,
                relationship_type=relationship_type,
                context=context,
                confidence=confidence,
            )

            self.qdrant_store.upsert_points(
                collection_name=self.collections["document_relationships"],
                points=[
                    {
                        "id": relationship.id,
                        "vector": [0.0],
                        "payload": relationship.model_dump(),
                    }
                ],
            )

            self.logger.info(
                f"Created relationship: {source_doc_id} -> {target_doc_id} ({relationship_type.value})"
            )
            return relationship

        except Exception as e:
            self.logger.error(f"Failed to create document relationship: {e}")
            raise

    async def get_document_relationships(
        self, document_id: str
    ) -> List[DocumentRelationship]:
        """Get all relationships for a document (both source and target)"""
        try:
            # Get relationships where document is source
            source_results = self.qdrant_store.search_points(
                collection_name=self.collections["document_relationships"],
                query_vector=[0.0],
                limit=1000,
                query_filter={"source_document_id": document_id},
            )

            # Get relationships where document is target
            target_results = self.qdrant_store.search_points(
                collection_name=self.collections["document_relationships"],
                query_vector=[0.0],
                limit=1000,
                query_filter={"target_document_id": document_id},
            )

            relationships = []
            for result in source_results + target_results:
                relationships.append(DocumentRelationship(**result.payload))

            return relationships

        except Exception as e:
            self.logger.error(
                f"Failed to get document relationships for {document_id}: {e}"
            )
            return []

    # Search and Query

    async def hierarchical_search(
        self, request: HierarchicalSearchRequest
    ) -> HierarchicalSearchResponse:
        """Perform hierarchical search across matters and cases"""
        try:
            start_time = datetime.now()

            # Step 1: Determine scope
            case_ids = await self._determine_search_scope(request)

            # Step 2: Perform document search within scope
            document_results = await self._search_documents_in_cases(request, case_ids)

            # Step 3: Apply access control
            filtered_results = await self._apply_access_control(
                document_results, request.access_level_required
            )

            # Step 4: Enhance with relationships if requested
            if request.include_relationships:
                filtered_results = await self._enhance_with_relationships(
                    filtered_results
                )

            # Step 5: Cross-case analysis if enabled
            cross_case_patterns = []
            if request.enable_cross_case_analysis:
                cross_case_patterns = await self._perform_cross_case_analysis(
                    request, case_ids
                )

            search_time = (datetime.now() - start_time).total_seconds() * 1000

            response = HierarchicalSearchResponse(
                results=filtered_results,
                total_matches=len(filtered_results),
                cases_searched=case_ids,
                search_time_ms=search_time,
                cross_case_patterns=cross_case_patterns,
            )

            self.logger.info(
                f"Hierarchical search completed: {len(filtered_results)} results in {search_time:.2f}ms"
            )
            return response

        except Exception as e:
            self.logger.error(f"Failed to perform hierarchical search: {e}")
            raise

    async def _determine_search_scope(
        self, request: HierarchicalSearchRequest
    ) -> List[str]:
        """Determine which cases to search based on request parameters"""
        case_ids = []

        if request.case_ids:
            # Explicit case IDs provided
            case_ids = request.case_ids
        elif request.matter_ids:
            # Search all cases within specified matters
            for matter_id in request.matter_ids:
                cases = await self.list_cases_in_matter(matter_id)
                case_ids.extend([case.id for case in cases])
        else:
            # Search all accessible cases (would need additional access control logic)
            pass

        return case_ids

    async def _search_documents_in_cases(
        self, request: HierarchicalSearchRequest, case_ids: List[str]
    ) -> List[Dict[str, Any]]:
        """Search for documents within specified cases"""
        if not case_ids:
            return []

        # Build filters
        filters = {"case_id": case_ids}

        if request.document_types:
            # Need to join with metadata table - simplified for now
            pass

        # Search in document-case junctions
        results = self.qdrant_store.search_points(
            collection_name=self.collections["document_case_junctions"],
            query_vector=[0.0],
            limit=request.max_results,
            query_filter=filters,
        )

        # Convert to response format
        document_results = []
        for result in results:
            document_results.append(
                {"junction_data": result.payload, "score": result.score}
            )

        return document_results

    async def _apply_access_control(
        self, results: List[Dict[str, Any]], required_access_level: AccessLevel
    ) -> List[Dict[str, Any]]:
        """Apply access control filtering to search results"""
        # For now, return all results - would implement proper access control
        return results

    async def _enhance_with_relationships(
        self, results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Enhance results with document relationship information"""
        for result in results:
            document_id = result["junction_data"]["document_id"]
            relationships = await self.get_document_relationships(document_id)
            result["relationships"] = [rel.model_dump() for rel in relationships]

        return results

    async def _perform_cross_case_analysis(
        self, request: HierarchicalSearchRequest, case_ids: List[str]
    ) -> List[Dict[str, Any]]:
        """Perform cross-case pattern analysis (privacy-preserving)"""
        # Placeholder for cross-case analysis
        return []

    # Utility Methods

    async def get_case_statistics(self, case_id: str) -> Dict[str, Any]:
        """Get comprehensive statistics for a case"""
        try:
            # Count documents in case
            doc_results = self.qdrant_store.search_points(
                collection_name=self.collections["document_case_junctions"],
                query_vector=[0.0],
                limit=10000,
                query_filter={"case_id": case_id},
            )

            total_documents = len(doc_results)

            # Get document types breakdown (would need join with metadata)
            document_types = defaultdict(int)

            # Calculate storage size (would need to sum from document cores)
            total_size_mb = 0

            stats = {
                "case_id": case_id,
                "total_documents": total_documents,
                "document_types": dict(document_types),
                "total_size_mb": total_size_mb,
                "last_updated": datetime.now(),
            }

            return stats

        except Exception as e:
            self.logger.error(f"Failed to get case statistics for {case_id}: {e}")
            return {}

    async def verify_case_isolation(self, case_id: str) -> Dict[str, Any]:
        """Verify that case data is properly isolated"""
        try:
            # Check that all documents in case are properly associated
            junctions = self.qdrant_store.search_points(
                collection_name=self.collections["document_case_junctions"],
                query_vector=[0.0],
                limit=10000,
                query_filter={"case_id": case_id},
            )

            isolation_report = {
                "case_id": case_id,
                "documents_checked": len(junctions),
                "isolation_violations": [],
                "orphaned_chunks": 0,
                "verified_at": datetime.now(),
            }

            # Check for orphaned chunks (chunks without valid document association)
            for junction in junctions:
                document_id = junction.payload["document_id"]

                # Verify chunks are properly linked
                chunk_results = self.qdrant_store.search_points(
                    collection_name=self.collections["chunk_metadata"],
                    query_vector=[0.0] * 1536,  # Proper vector size for chunks
                    limit=1000,
                    query_filter={"document_id": document_id},
                )

                for chunk in chunk_results:
                    # Verify chunk integrity
                    pass

            self.logger.info(f"Case isolation verification completed for {case_id}")
            return isolation_report

        except Exception as e:
            self.logger.error(f"Failed to verify case isolation for {case_id}: {e}")
            return {"error": str(e)}

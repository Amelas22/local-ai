"""
Discovery Normalized Adapter

This module provides the bridge between the existing discovery processing system
and the new normalized database schema. It converts between unified and normalized
models while maintaining backward compatibility.

Key Features:
1. Model conversion utilities
2. Discovery metadata preservation
3. Segment-to-document mapping
4. Bates number tracking
5. Production batch management
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import hashlib

from ..models.unified_document_models import (
    UnifiedDocument, DiscoverySegment, DiscoveryProductionResult,
    DiscoveryProcessingRequest, DiscoveryMetadata, DocumentBoundary
)
from ..models.normalized_document_models import (
    DocumentCore, DocumentMetadata, DocumentCaseJunction,
    DocumentRelationship, ChunkMetadata, RelationshipType,
    NormalizedDocumentCreateRequest, NormalizedDocumentResponse
)
from ..document_processing.hierarchical_document_manager import HierarchicalDocumentManager
from ..document_processing.normalized_document_service import NormalizedDocumentService
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


@dataclass
class DiscoveryConversionResult:
    """Result of converting discovery documents to normalized format"""
    documents_created: List[DocumentCore] = None
    segments_mapped: List[Tuple[DiscoverySegment, DocumentCore]] = None
    relationships_created: List[DocumentRelationship] = None
    errors: List[str] = None
    
    def __post_init__(self):
        if self.documents_created is None:
            self.documents_created = []
        if self.segments_mapped is None:
            self.segments_mapped = []
        if self.relationships_created is None:
            self.relationships_created = []
        if self.errors is None:
            self.errors = []


class DiscoveryNormalizedAdapter:
    """
    Adapter for bridging discovery processing with normalized schema
    """
    
    def __init__(self,
                 hierarchical_manager: HierarchicalDocumentManager,
                 normalized_service: NormalizedDocumentService):
        """
        Initialize the adapter
        
        Args:
            hierarchical_manager: Manager for normalized hierarchy
            normalized_service: Service for normalized document operations
        """
        self.hierarchical_manager = hierarchical_manager
        self.normalized_service = normalized_service
        self.logger = logger
    
    async def convert_discovery_production(self,
                                         production_result: DiscoveryProductionResult,
                                         case_id: str,
                                         discovery_request: DiscoveryProcessingRequest) -> DiscoveryConversionResult:
        """
        Convert a discovery production result to normalized format
        
        Args:
            production_result: Result from discovery processing
            case_id: ID of the case in normalized system
            discovery_request: Original discovery request
            
        Returns:
            Conversion results
        """
        try:
            conversion_result = DiscoveryConversionResult()
            
            # Step 1: Create documents for each segment
            for segment in production_result.segments_found:
                try:
                    document_core = await self._create_document_from_segment(
                        segment, production_result, discovery_request
                    )
                    conversion_result.documents_created.append(document_core)
                    conversion_result.segments_mapped.append((segment, document_core))
                    
                except Exception as e:
                    error_msg = f"Failed to convert segment {segment.segment_id}: {e}"
                    conversion_result.errors.append(error_msg)
                    self.logger.error(error_msg)
            
            # Step 2: Create document relationships for multi-part documents
            relationships = await self._create_segment_relationships(
                conversion_result.segments_mapped, production_result
            )
            conversion_result.relationships_created.extend(relationships)
            
            # Step 3: Create case junctions with discovery metadata
            await self._create_case_junctions(
                conversion_result.documents_created,
                case_id,
                discovery_request,
                production_result
            )
            
            self.logger.info(
                f"Converted discovery production: {len(conversion_result.documents_created)} documents, "
                f"{len(conversion_result.relationships_created)} relationships"
            )
            
            return conversion_result
            
        except Exception as e:
            self.logger.error(f"Discovery production conversion failed: {e}")
            raise
    
    async def _create_document_from_segment(self,
                                          segment: DiscoverySegment,
                                          production_result: DiscoveryProductionResult,
                                          discovery_request: DiscoveryProcessingRequest) -> DocumentCore:
        """Create a normalized document from a discovery segment"""
        
        # Generate content hash (would need actual content in practice)
        content_hash = hashlib.sha256(
            f"{production_result.source_pdf_path}:{segment.start_page}:{segment.end_page}".encode()
        ).hexdigest()
        
        # Create metadata hash
        metadata_str = f"{segment.document_type.value}|{segment.title or 'untitled'}|{segment.page_count}"
        metadata_hash = hashlib.sha256(metadata_str.encode()).hexdigest()
        
        # Create DocumentCore
        document_core = DocumentCore(
            document_hash=content_hash,
            metadata_hash=metadata_hash,
            file_name=f"{production_result.production_batch}_segment_{segment.segment_id}.pdf",
            original_file_path=production_result.source_pdf_path,
            file_size=0,  # Would calculate from actual content
            total_pages=segment.page_count,
            first_ingested_at=production_result.processing_started,
            box_file_id=None  # Would set if from Box
        )
        
        # Create DocumentMetadata
        document_metadata = DocumentMetadata(
            document_id=document_core.id,
            document_type=segment.document_type,
            title=segment.title or f"Document {segment.segment_id}",
            description=f"Segment {segment.start_page}-{segment.end_page} from {production_result.production_batch}",
            summary=f"Document extracted from discovery production",
            key_pages=list(range(1, min(5, segment.page_count + 1))),  # First few pages
            ai_classification_confidence=segment.confidence_score,
            ai_model_used="gpt-4.1-mini-2025-04-14"
        )
        
        # Store in normalized system
        await self.hierarchical_manager._store_document_components(
            document_core, document_metadata, None  # Junction created separately
        )
        
        return document_core
    
    async def _create_segment_relationships(self,
                                          segments_mapped: List[Tuple[DiscoverySegment, DocumentCore]],
                                          production_result: DiscoveryProductionResult) -> List[DocumentRelationship]:
        """Create relationships between document segments"""
        relationships = []
        
        # Group segments by continuation ID for multi-part documents
        continuation_groups = {}
        for segment, doc_core in segments_mapped:
            if segment.continuation_id:
                if segment.continuation_id not in continuation_groups:
                    continuation_groups[segment.continuation_id] = []
                continuation_groups[segment.continuation_id].append((segment, doc_core))
        
        # Create continuation relationships
        for continuation_id, group in continuation_groups.items():
            # Sort by part number
            group.sort(key=lambda x: x[0].part_number)
            
            # Create relationships between consecutive parts
            for i in range(len(group) - 1):
                current_segment, current_doc = group[i]
                next_segment, next_doc = group[i + 1]
                
                relationship = await self.hierarchical_manager.create_document_relationship(
                    source_doc_id=current_doc.id,
                    target_doc_id=next_doc.id,
                    relationship_type=RelationshipType.CONTINUATION,
                    context=f"Part {current_segment.part_number} continues to part {next_segment.part_number}",
                    confidence=min(current_segment.confidence_score, next_segment.confidence_score)
                )
                relationships.append(relationship)
        
        # Create production batch relationships
        all_docs = [doc for _, doc in segments_mapped]
        if len(all_docs) > 1:
            # Link all documents as part of same production
            for i in range(len(all_docs) - 1):
                for j in range(i + 1, len(all_docs)):
                    relationship = await self.hierarchical_manager.create_document_relationship(
                        source_doc_id=all_docs[i].id,
                        target_doc_id=all_docs[j].id,
                        relationship_type=RelationshipType.RELATED,
                        context=f"Same production batch: {production_result.production_batch}",
                        confidence=1.0
                    )
                    relationships.append(relationship)
        
        return relationships
    
    async def _create_case_junctions(self,
                                   documents: List[DocumentCore],
                                   case_id: str,
                                   discovery_request: DiscoveryProcessingRequest,
                                   production_result: DiscoveryProductionResult):
        """Create case junctions with discovery metadata"""
        
        segments_by_doc_id = {}
        for segment, doc in production_result.segments_found:
            if hasattr(doc, 'id'):
                segments_by_doc_id[doc.id] = segment
        
        for i, document in enumerate(documents):
            # Get corresponding segment
            segment = None
            if i < len(production_result.segments_found):
                segment = production_result.segments_found[i]
            
            # Extract Bates numbers from segment if available
            bates_start = None
            bates_end = None
            if segment and segment.bates_range:
                bates_start = segment.bates_range.get('start')
                bates_end = segment.bates_range.get('end')
            
            # Create junction with discovery metadata
            junction = DocumentCaseJunction(
                document_id=document.id,
                case_id=case_id,
                production_batch=discovery_request.production_batch,
                production_date=discovery_request.production_date,
                bates_number_start=bates_start,
                bates_number_end=bates_end,
                confidentiality_designation=discovery_request.confidentiality_designation,
                producing_party=discovery_request.producing_party,
                responsive_to_requests=discovery_request.responsive_to_requests,
                is_segment_of_production=True,
                segment_id=segment.segment_id if segment else None,
                segment_number=i + 1,
                total_segments=len(documents)
            )
            
            # Store junction
            await self.hierarchical_manager.qdrant_store.upsert_points(
                collection_name=self.hierarchical_manager.collections['document_case_junctions'],
                points=[{
                    'id': junction.id,
                    'vector': [0.0],
                    'payload': junction.model_dump()
                }]
            )
    
    async def convert_unified_to_normalized(self,
                                          unified_doc: UnifiedDocument,
                                          case_id: str) -> NormalizedDocumentResponse:
        """
        Convert a unified document to normalized format
        
        Args:
            unified_doc: Unified document to convert
            case_id: Case ID in normalized system
            
        Returns:
            Normalized document response
        """
        try:
            # Create DocumentCore
            document_core = DocumentCore(
                document_hash=unified_doc.document_hash,
                metadata_hash=hashlib.sha256(
                    f"{unified_doc.file_name}|{unified_doc.file_size}|{unified_doc.document_type.value}".encode()
                ).hexdigest(),
                file_name=unified_doc.file_name,
                original_file_path=unified_doc.file_path,
                file_size=unified_doc.file_size,
                mime_type=unified_doc.mime_type,
                total_pages=unified_doc.total_pages,
                first_ingested_at=unified_doc.first_seen_at,
                file_modified_at=unified_doc.last_modified,
                box_file_id=unified_doc.box_file_id
            )
            
            # Create DocumentMetadata
            document_metadata = DocumentMetadata(
                document_id=document_core.id,
                document_type=unified_doc.document_type,
                title=unified_doc.title,
                description=unified_doc.description,
                summary=unified_doc.summary,
                document_date=unified_doc.document_date,
                key_facts=unified_doc.key_facts,
                relevance_tags=unified_doc.relevance_tags,
                mentioned_parties=unified_doc.mentioned_parties,
                mentioned_dates=unified_doc.mentioned_dates,
                author=unified_doc.author,
                recipient=unified_doc.recipient,
                witness=unified_doc.witness,
                key_pages=unified_doc.key_pages,
                ai_classification_confidence=unified_doc.classification_confidence,
                human_verified=unified_doc.verified
            )
            
            # Create DocumentCaseJunction
            case_junction = DocumentCaseJunction(
                document_id=document_core.id,
                case_id=case_id,
                times_accessed_in_case=unified_doc.times_accessed,
                last_accessed_in_case=unified_doc.last_accessed,
                used_in_motions=unified_doc.used_in_motions
            )
            
            # Store components
            await self.hierarchical_manager._store_document_components(
                document_core, document_metadata, case_junction
            )
            
            # Create response
            response = NormalizedDocumentResponse(
                document_core=document_core,
                document_metadata=document_metadata,
                case_associations=[case_junction],
                is_duplicate=unified_doc.is_duplicate,
                chunks_created=0  # Would be updated after chunk creation
            )
            
            return response
            
        except Exception as e:
            self.logger.error(f"Failed to convert unified document {unified_doc.id}: {e}")
            raise
    
    def create_chunk_metadata_from_unified(self,
                                         chunk_data: Dict[str, Any],
                                         document_id: str,
                                         chunk_index: int) -> ChunkMetadata:
        """
        Create normalized chunk metadata from unified chunk data
        
        Args:
            chunk_data: Chunk data from unified system
            document_id: Document ID in normalized system
            chunk_index: Index of chunk
            
        Returns:
            Normalized chunk metadata
        """
        # Extract chunk text and metadata
        chunk_text = chunk_data.get('chunk', '')
        metadata = chunk_data.get('metadata', {})
        
        # Calculate chunk hash
        chunk_hash = hashlib.sha256(chunk_text.encode()).hexdigest()
        
        # Create ChunkMetadata
        chunk_metadata = ChunkMetadata(
            document_id=document_id,
            chunk_text=chunk_text,
            chunk_index=chunk_index,
            chunk_hash=chunk_hash,
            start_page=metadata.get('start_page'),
            end_page=metadata.get('end_page'),
            section_title=metadata.get('section_title'),
            semantic_type=metadata.get('semantic_type', 'paragraph'),
            context_summary=metadata.get('context_prepend', ''),
            dense_vector=chunk_data.get('dense_vector'),
            sparse_vector=chunk_data.get('sparse_vector'),
            embedding_model=metadata.get('embedding_model', 'text-embedding-3-small'),
            text_quality_score=1.0,
            extraction_confidence=metadata.get('extraction_confidence', 1.0)
        )
        
        return chunk_metadata
    
    async def search_discovery_documents(self,
                                       case_id: str,
                                       production_batch: Optional[str] = None,
                                       bates_range: Optional[Tuple[str, str]] = None,
                                       document_types: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Search for discovery documents using normalized schema
        
        Args:
            case_id: Case ID to search within
            production_batch: Filter by production batch
            bates_range: Filter by Bates number range
            document_types: Filter by document types
            
        Returns:
            List of matching documents with metadata
        """
        try:
            # Build filters for junction search
            filters = {'case_id': case_id}
            
            if production_batch:
                filters['production_batch'] = production_batch
            
            if bates_range:
                # Would need range query support
                filters['bates_number_start'] = {'gte': bates_range[0]}
                filters['bates_number_end'] = {'lte': bates_range[1]}
            
            # Search junctions
            junction_results = self.hierarchical_manager.qdrant_store.search_points(
                collection_name=self.hierarchical_manager.collections['document_case_junctions'],
                query_vector=[0.0],
                limit=1000,
                query_filter=filters
            )
            
            # Get document details
            results = []
            for junction_result in junction_results:
                junction_data = junction_result.payload
                document_id = junction_data['document_id']
                
                # Get document core
                doc_core_results = self.hierarchical_manager.qdrant_store.get_points(
                    collection_name=self.hierarchical_manager.collections['document_cores'],
                    ids=[document_id]
                )
                
                if doc_core_results:
                    doc_core = doc_core_results[0].payload
                    
                    # Get document metadata
                    metadata_results = self.hierarchical_manager.qdrant_store.search_points(
                        collection_name=self.hierarchical_manager.collections['document_metadata'],
                        query_vector=[0.0],
                        limit=1,
                        query_filter={'document_id': document_id}
                    )
                    
                    doc_metadata = metadata_results[0].payload if metadata_results else {}
                    
                    # Filter by document type if specified
                    if document_types and doc_metadata.get('document_type') not in document_types:
                        continue
                    
                    # Combine results
                    results.append({
                        'document_core': doc_core,
                        'document_metadata': doc_metadata,
                        'junction_data': junction_data,
                        'is_discovery': True,
                        'production_info': {
                            'batch': junction_data.get('production_batch'),
                            'date': junction_data.get('production_date'),
                            'producing_party': junction_data.get('producing_party'),
                            'bates_range': {
                                'start': junction_data.get('bates_number_start'),
                                'end': junction_data.get('bates_number_end')
                            }
                        }
                    })
            
            return results
            
        except Exception as e:
            self.logger.error(f"Discovery document search failed: {e}")
            return []


class DiscoveryBackwardCompatibility:
    """
    Provides backward compatibility for existing discovery processing code
    """
    
    def __init__(self, adapter: DiscoveryNormalizedAdapter):
        self.adapter = adapter
        self.logger = logger
    
    async def process_discovery_production_legacy(self,
                                                production_result: DiscoveryProductionResult,
                                                case_name: str,
                                                discovery_request: DiscoveryProcessingRequest) -> Dict[str, Any]:
        """
        Process discovery production using legacy interface but normalized backend
        
        Args:
            production_result: Discovery production result
            case_name: Legacy case name
            discovery_request: Discovery request
            
        Returns:
            Legacy-compatible response
        """
        try:
            # Resolve case name to case ID
            case_id = await self._resolve_case_id(case_name)
            if not case_id:
                # Create case if not exists
                case_id = await self._create_case_for_discovery(case_name, discovery_request)
            
            # Convert to normalized format
            conversion_result = await self.adapter.convert_discovery_production(
                production_result, case_id, discovery_request
            )
            
            # Build legacy response
            legacy_response = {
                'status': 'success',
                'documents_processed': len(conversion_result.documents_created),
                'segments_created': len(conversion_result.segments_mapped),
                'relationships_created': len(conversion_result.relationships_created),
                'errors': conversion_result.errors,
                'case_name': case_name,
                'production_batch': discovery_request.production_batch,
                'documents': []
            }
            
            # Add document summaries in legacy format
            for doc_core in conversion_result.documents_created:
                legacy_response['documents'].append({
                    'id': doc_core.id,
                    'file_name': doc_core.file_name,
                    'document_hash': doc_core.document_hash,
                    'total_pages': doc_core.total_pages
                })
            
            return legacy_response
            
        except Exception as e:
            self.logger.error(f"Legacy discovery processing failed: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'documents_processed': 0
            }
    
    async def _resolve_case_id(self, case_name: str) -> Optional[str]:
        """Resolve case name to case ID"""
        # Search for case by name
        cases = await self.adapter.hierarchical_manager.qdrant_store.search_points(
            collection_name=self.adapter.hierarchical_manager.collections['cases'],
            query_vector=[0.0],
            limit=1,
            query_filter={'case_name': case_name}
        )
        
        if cases:
            return cases[0].payload['id']
        return None
    
    async def _create_case_for_discovery(self, 
                                       case_name: str, 
                                       discovery_request: DiscoveryProcessingRequest) -> str:
        """Create a case for discovery processing"""
        # Extract parties from case name
        parties = case_name.split(' v. ') if ' v. ' in case_name else [case_name]
        
        # Create matter first
        matter = await self.adapter.normalized_service.create_matter(
            matter_number=f"DISCOVERY_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            client_name=parties[0] if parties else "Unknown",
            matter_name=f"Discovery Production - {case_name}",
            matter_type="LITIGATION",
            description=f"Created for discovery processing: {discovery_request.production_batch}"
        )
        
        # Create case
        case = await self.adapter.normalized_service.create_case(
            matter_id=matter.id,
            case_number=case_name,
            case_name=case_name,
            plaintiffs=[parties[0]] if parties else ["Unknown"],
            defendants=[parties[1]] if len(parties) > 1 else ["Unknown"]
        )
        
        return case.id
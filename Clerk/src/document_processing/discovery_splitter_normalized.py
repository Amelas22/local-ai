"""
Enhanced Discovery Splitter for Normalized Database Schema

This module extends the existing discovery splitter to work with the normalized
database schema. It creates normalized documents, relationships, and enhanced
chunk metadata while maintaining all existing functionality.

Key Features:
1. Normalized document creation from segments
2. Multi-part document relationship tracking
3. Enhanced chunk metadata with discovery context
4. Bates number indexing
5. Production batch organization
"""

from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
import hashlib

from .discovery_splitter import (
    DiscoveryDocumentProcessor,
    DiscoveryProductionProcessor,
    DiscoverySegment,
    DiscoveryProductionResult,
)
from .hierarchical_document_manager import HierarchicalDocumentManager
from .normalized_document_service import NormalizedDocumentService
from .enhanced_chunker import EnhancedChunker
from ..models.normalized_document_models import (
    DocumentCore,
    DocumentMetadata,
    DocumentCaseJunction,
    RelationshipType,
)
from ..models.unified_document_models import DocumentType, DiscoveryProcessingRequest
from ..vector_storage.embeddings import EmbeddingGenerator
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class NormalizedDiscoveryDocumentProcessor(DiscoveryDocumentProcessor):
    """
    Enhanced discovery document processor that creates normalized documents
    """

    def __init__(
        self,
        normalized_service: NormalizedDocumentService,
        enhanced_chunker: EnhancedChunker,
        *args,
        **kwargs,
    ):
        """
        Initialize the normalized discovery processor

        Args:
            normalized_service: Service for normalized document operations
            enhanced_chunker: Enhanced chunker for chunk metadata
            *args, **kwargs: Arguments passed to parent class
        """
        super().__init__(*args, **kwargs)
        self.normalized_service = normalized_service
        self.enhanced_chunker = enhanced_chunker
        self.logger = logger  # Inherit logger from module level

    async def process_segment_normalized(
        self,
        segment: DiscoverySegment,
        segment_text: str,
        case_id: str,
        discovery_request: DiscoveryProcessingRequest,
    ) -> DocumentCore:
        """
        Process a segment and create normalized document

        Args:
            segment: Discovery segment
            segment_text: Extracted text
            case_id: Case ID in normalized system
            discovery_request: Discovery processing request

        Returns:
            Created document core
        """
        try:
            # Generate hashes
            content_hash = hashlib.sha256(segment_text.encode()).hexdigest()
            metadata_hash = hashlib.sha256(
                f"{segment.document_type.value}|{segment.title or 'untitled'}|{segment.page_count}".encode()
            ).hexdigest()

            # Create DocumentCore
            document_core = DocumentCore(
                document_hash=content_hash,
                metadata_hash=metadata_hash,
                file_name=f"{discovery_request.production_batch}_segment_{segment.segment_id}.pdf",
                original_file_path=f"discovery://{discovery_request.folder_id}/{segment.segment_id}",
                file_size=len(segment_text.encode()),
                total_pages=segment.page_count,
                first_ingested_at=datetime.now(),
            )

            # Create DocumentMetadata with enhanced information
            document_metadata = DocumentMetadata(
                document_id=document_core.id,
                document_type=segment.document_type,
                title=segment.title
                or f"Discovery Document - {segment.document_type.value}",
                description=f"Pages {segment.start_page}-{segment.end_page} from {discovery_request.production_batch}",
                summary=await self._generate_segment_summary(segment, segment_text),
                key_pages=self._identify_key_pages(segment, segment_text),
                ai_classification_confidence=segment.confidence_score,
                ai_model_used="gpt-4.1-mini-2025-04-14",
            )

            # Extract metadata specific to discovery
            if segment.bates_range:
                document_metadata.mentioned_dates.append(
                    f"Bates: {segment.bates_range['start']}-{segment.bates_range['end']}"
                )

            # Create DocumentCaseJunction with discovery metadata
            case_junction = DocumentCaseJunction(
                document_id=document_core.id,
                case_id=case_id,
                production_batch=discovery_request.production_batch,
                production_date=discovery_request.production_date,
                bates_number_start=segment.bates_range.get("start")
                if segment.bates_range
                else None,
                bates_number_end=segment.bates_range.get("end")
                if segment.bates_range
                else None,
                confidentiality_designation=discovery_request.confidentiality_designation,
                producing_party=discovery_request.producing_party,
                responsive_to_requests=discovery_request.responsive_to_requests,
                is_segment_of_production=True,
                segment_id=segment.segment_id,
                segment_number=segment.part_number
                if hasattr(segment, "part_number")
                else 1,
                total_segments=segment.total_parts
                if hasattr(segment, "total_parts")
                else 1,
            )

            # Store components
            await self.normalized_service.document_manager._store_document_components(
                document_core, document_metadata, case_junction
            )

            # Process chunks with enhanced metadata
            await self._process_chunks_normalized(
                document_core, segment_text, segment, discovery_request
            )

            self.logger.info(
                f"Created normalized document for segment {segment.segment_id}"
            )
            return document_core

        except Exception as e:
            self.logger.error(f"Failed to process segment {segment.segment_id}: {e}")
            raise

    async def _process_chunks_normalized(
        self,
        document_core: DocumentCore,
        segment_text: str,
        segment: DiscoverySegment,
        discovery_request: DiscoveryProcessingRequest,
    ):
        """Process chunks with enhanced metadata for discovery"""
        try:
            # Create chunks using enhanced chunker
            chunks = await self.enhanced_chunker.create_chunks(
                document_core=document_core,
                document_text=segment_text,
                page_boundaries=None,  # Would extract from PDF
            )

            # Enhance chunks with discovery context
            for chunk in chunks:
                # Add discovery-specific metadata
                chunk.section_title = f"{discovery_request.production_batch} - {segment.document_type.value}"

                # Add Bates reference if available
                if segment.bates_range:
                    chunk.context_summary = f"[Bates: {segment.bates_range['start']}-{segment.bates_range['end']}] {chunk.context_summary}"

                # Set semantic type based on document type
                if segment.document_type in [
                    DocumentType.DEPOSITION,
                    DocumentType.INTERROGATORY_RESPONSE,
                ]:
                    chunk.semantic_type = "testimony"
                elif segment.document_type in [
                    DocumentType.EXPERT_REPORT,
                    DocumentType.MEDICAL_RECORD,
                ]:
                    chunk.semantic_type = "expert_opinion"
                elif segment.document_type in [
                    DocumentType.POLICY,
                    DocumentType.SAFETY_MANUAL,
                ]:
                    chunk.semantic_type = "procedural"

            # Store chunks
            await self.normalized_service._store_chunks_batch(chunks)

            self.logger.info(
                f"Created {len(chunks)} normalized chunks for document {document_core.id}"
            )

        except Exception as e:
            self.logger.error(
                f"Failed to process chunks for document {document_core.id}: {e}"
            )
            raise

    async def _generate_segment_summary(
        self, segment: DiscoverySegment, text: str
    ) -> str:
        """Generate AI summary for segment"""
        # Would use AI to generate summary
        # For now, return a structured summary
        summary_parts = [
            f"{segment.document_type.value} document",
            f"Pages {segment.start_page}-{segment.end_page}",
            f"Confidence: {segment.confidence_score:.2f}",
        ]

        if segment.bates_range:
            summary_parts.append(
                f"Bates: {segment.bates_range['start']}-{segment.bates_range['end']}"
            )

        return ". ".join(summary_parts)

    def _identify_key_pages(self, segment: DiscoverySegment, text: str) -> List[int]:
        """Identify key pages within the segment"""
        key_pages = []

        # First and last pages are often important
        key_pages.append(1)
        if segment.page_count > 1:
            key_pages.append(segment.page_count)

        # For depositions, look for examination changes
        if segment.document_type == DocumentType.DEPOSITION:
            # Would analyze text for "CROSS-EXAMINATION", "REDIRECT", etc.
            pass

        # For expert reports, look for opinion sections
        elif segment.document_type == DocumentType.EXPERT_REPORT:
            # Would analyze text for "OPINION", "CONCLUSION", etc.
            pass

        return sorted(set(key_pages))[:5]  # Limit to 5 key pages


class NormalizedDiscoveryProductionProcessor(DiscoveryProductionProcessor):
    """
    Enhanced production processor that creates document relationships
    """

    def __init__(
        self,
        normalized_service: NormalizedDocumentService,
        hierarchical_manager: HierarchicalDocumentManager,
        case_name: str,
        *args,
        **kwargs,
    ):
        """
        Initialize the normalized production processor

        Args:
            normalized_service: Service for normalized operations
            hierarchical_manager: Manager for document relationships
            case_name: Name of the case being processed
            *args, **kwargs: Arguments passed to parent class
        """
        super().__init__(case_name, *args, **kwargs)
        self.normalized_service = normalized_service
        self.hierarchical_manager = hierarchical_manager
        self.logger = logger  # Inherit logger from module level

        # Replace document processor with normalized version
        self.document_processor = NormalizedDiscoveryDocumentProcessor(
            normalized_service=normalized_service,
            enhanced_chunker=EnhancedChunker(EmbeddingGenerator()),
            case_name=case_name,
        )

    async def process_production_normalized(
        self, pdf_path: str, case_id: str, discovery_request: DiscoveryProcessingRequest
    ) -> DiscoveryProductionResult:
        """
        Process a discovery production with normalized document creation

        Args:
            pdf_path: Path to production PDF
            case_id: Case ID in normalized system
            discovery_request: Discovery processing request

        Returns:
            Production processing result
        """
        try:
            # Run standard processing to get segments
            result = self.process_discovery_production(
                pdf_path=pdf_path,
                production_metadata={
                    "production_batch": discovery_request.production_batch,
                    "producing_party": discovery_request.producing_party,
                },
            )

            # Process each segment with normalized system
            normalized_documents = []
            for segment in result.segments_found:
                # Extract text for segment
                segment_text = await self._extract_segment_text(pdf_path, segment)

                # Create normalized document
                doc_core = await self.document_processor.process_segment_normalized(
                    segment=segment,
                    segment_text=segment_text,
                    case_id=case_id,
                    discovery_request=discovery_request,
                )
                normalized_documents.append((segment, doc_core))

            # Create relationships between documents
            await self._create_production_relationships(normalized_documents, result)

            # Store normalized documents info in result (if needed in future)
            # For now, we've already processed the documents

            self.logger.info(
                f"Processed production with {len(normalized_documents)} normalized documents"
            )

            return result

        except Exception as e:
            self.logger.error(f"Normalized production processing failed: {e}")
            raise

    async def _extract_segment_text(
        self, pdf_path: str, segment: DiscoverySegment
    ) -> str:
        """Extract text for a specific segment"""
        # Would extract actual text from PDF pages
        # For now, return placeholder
        return f"Text content for segment {segment.segment_id} pages {segment.start_page}-{segment.end_page}"

    async def _create_production_relationships(
        self,
        normalized_documents: List[Tuple[DiscoverySegment, DocumentCore]],
        result: DiscoveryProductionResult,
    ):
        """Create relationships between documents in production"""
        try:
            # Create continuation relationships for multi-part documents
            continuation_groups = {}
            for segment, doc_core in normalized_documents:
                if segment.continuation_id:
                    if segment.continuation_id not in continuation_groups:
                        continuation_groups[segment.continuation_id] = []
                    continuation_groups[segment.continuation_id].append(
                        (segment, doc_core)
                    )

            for continuation_id, group in continuation_groups.items():
                # Sort by part number
                group.sort(key=lambda x: x[0].part_number)

                # Create relationships
                for i in range(len(group) - 1):
                    current_seg, current_doc = group[i]
                    next_seg, next_doc = group[i + 1]

                    await self.hierarchical_manager.create_document_relationship(
                        source_doc_id=current_doc.id,
                        target_doc_id=next_doc.id,
                        relationship_type=RelationshipType.CONTINUATION,
                        context=f"Part {current_seg.part_number} of {current_seg.total_parts}",
                        confidence=min(
                            current_seg.confidence_score, next_seg.confidence_score
                        ),
                    )

            # Create exhibit relationships
            exhibit_docs = [
                (seg, doc)
                for seg, doc in normalized_documents
                if "exhibit" in seg.title.lower()
                if seg.title
            ]

            for exhibit_seg, exhibit_doc in exhibit_docs:
                # Find potential parent documents
                for seg, doc in normalized_documents:
                    if seg != exhibit_seg and self._is_exhibit_reference(
                        exhibit_seg, seg
                    ):
                        await self.hierarchical_manager.create_document_relationship(
                            source_doc_id=doc.id,
                            target_doc_id=exhibit_doc.id,
                            relationship_type=RelationshipType.EXHIBIT,
                            context=f"Exhibit to {seg.document_type.value}",
                            confidence=0.8,
                        )

            # Create temporal relationships based on dates
            dated_docs = [
                (seg, doc)
                for seg, doc in normalized_documents
                if seg.document_type
                in [DocumentType.CORRESPONDENCE, DocumentType.EMAIL_CORRESPONDENCE]
            ]

            # Would implement temporal relationship logic

            self.logger.info(
                f"Created relationships for {len(normalized_documents)} documents"
            )

        except Exception as e:
            self.logger.error(f"Failed to create production relationships: {e}")

    def _is_exhibit_reference(
        self, exhibit_seg: DiscoverySegment, potential_parent: DiscoverySegment
    ) -> bool:
        """Check if exhibit is referenced by potential parent"""
        # Simple heuristic - would be more sophisticated in practice
        if not exhibit_seg.bates_range or not potential_parent.bates_range:
            return False

        # Check if exhibit immediately follows parent
        try:
            exhibit_start = int(exhibit_seg.bates_range["start"].replace("DEF", ""))
            parent_end = int(potential_parent.bates_range["end"].replace("DEF", ""))
            return exhibit_start == parent_end + 1
        except:
            return False


class DiscoveryBatesIndexer:
    """
    Specialized indexer for Bates number search and navigation
    """

    def __init__(self, hierarchical_manager: HierarchicalDocumentManager):
        self.hierarchical_manager = hierarchical_manager
        self.logger = logger

    async def build_bates_index(self, case_id: str) -> Dict[str, Any]:
        """
        Build an index of Bates numbers for a case

        Args:
            case_id: Case ID to index

        Returns:
            Bates index information
        """
        try:
            # Get all document-case junctions for the case
            junctions = self.hierarchical_manager.qdrant_store.search_points(
                collection_name=self.hierarchical_manager.collections[
                    "document_case_junctions"
                ],
                query_vector=[0.0],
                limit=10000,
                query_filter={"case_id": case_id, "is_segment_of_production": True},
            )

            # Build Bates index
            bates_index = {}
            bates_ranges = []

            for junction in junctions:
                data = junction.payload
                if data.get("bates_number_start") and data.get("bates_number_end"):
                    bates_ranges.append(
                        {
                            "start": data["bates_number_start"],
                            "end": data["bates_number_end"],
                            "document_id": data["document_id"],
                            "production_batch": data.get("production_batch"),
                            "producing_party": data.get("producing_party"),
                        }
                    )

                    # Create individual Bates entries
                    try:
                        start_num = int(
                            data["bates_number_start"]
                            .replace("DEF", "")
                            .replace("PLF", "")
                        )
                        end_num = int(
                            data["bates_number_end"]
                            .replace("DEF", "")
                            .replace("PLF", "")
                        )
                        prefix = "DEF" if "DEF" in data["bates_number_start"] else "PLF"

                        for num in range(start_num, end_num + 1):
                            bates_num = f"{prefix}{num:05d}"
                            bates_index[bates_num] = data["document_id"]
                    except:
                        # Handle non-standard Bates formats
                        pass

            # Sort ranges
            bates_ranges.sort(key=lambda x: x["start"])

            index_info = {
                "case_id": case_id,
                "total_documents": len(junctions),
                "bates_ranges": bates_ranges,
                "total_bates_numbers": len(bates_index),
                "productions": list(
                    set(
                        r["production_batch"]
                        for r in bates_ranges
                        if r.get("production_batch")
                    )
                ),
            }

            self.logger.info(
                f"Built Bates index for case {case_id}: {len(bates_index)} numbers"
            )
            return index_info

        except Exception as e:
            self.logger.error(f"Failed to build Bates index: {e}")
            return {}

    async def find_document_by_bates(
        self, case_id: str, bates_number: str
    ) -> Optional[Dict[str, Any]]:
        """
        Find a document by Bates number

        Args:
            case_id: Case ID
            bates_number: Bates number to find

        Returns:
            Document information if found
        """
        try:
            # Search for junction with Bates range containing the number
            junctions = self.hierarchical_manager.qdrant_store.search_points(
                collection_name=self.hierarchical_manager.collections[
                    "document_case_junctions"
                ],
                query_vector=[0.0],
                limit=1000,
                query_filter={"case_id": case_id},
            )

            for junction in junctions:
                data = junction.payload
                if self._bates_in_range(
                    bates_number,
                    data.get("bates_number_start"),
                    data.get("bates_number_end"),
                ):
                    # Get document details
                    doc_core = await self.hierarchical_manager.get_document_core(
                        data["document_id"]
                    )
                    doc_metadata = (
                        await self.hierarchical_manager.get_document_metadata(
                            data["document_id"]
                        )
                    )

                    return {
                        "document_core": doc_core,
                        "document_metadata": doc_metadata,
                        "junction_data": data,
                        "bates_info": {
                            "requested": bates_number,
                            "document_range": f"{data['bates_number_start']}-{data['bates_number_end']}",
                            "production": data.get("production_batch"),
                            "producing_party": data.get("producing_party"),
                        },
                    }

            return None

        except Exception as e:
            self.logger.error(f"Failed to find document by Bates {bates_number}: {e}")
            return None

    def _bates_in_range(
        self, bates_number: str, start: Optional[str], end: Optional[str]
    ) -> bool:
        """Check if Bates number is in range"""
        if not start or not end:
            return False

        try:
            # Extract numeric parts
            num = int("".join(filter(str.isdigit, bates_number)))
            start_num = int("".join(filter(str.isdigit, start)))
            end_num = int("".join(filter(str.isdigit, end)))

            # Check prefix matches
            prefix = "".join(filter(str.isalpha, bates_number))
            start_prefix = "".join(filter(str.isalpha, start))

            return prefix == start_prefix and start_num <= num <= end_num
        except:
            # Fallback to string comparison
            return start <= bates_number <= end

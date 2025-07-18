"""
Unified Document Injector Module
Uses the new unified document management system for deduplication and discovery
"""

import logging
import asyncio
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

from src.document_processing.box_client import BoxClient, BoxDocument
from src.document_processing.pdf_extractor import PDFExtractor
from src.document_processing.chunker import DocumentChunker
from src.document_processing.unified_document_manager import UnifiedDocumentManager
from src.document_processing.context_generator import ContextGenerator
from src.vector_storage.embeddings import EmbeddingGenerator
from src.vector_storage.qdrant_store import QdrantVectorStore
from src.vector_storage.sparse_encoder import SparseVectorEncoder, LegalQueryAnalyzer
from config.settings import settings
from src.utils.cost_tracker import CostTracker

# Fact extraction imports (still using existing system)
from src.ai_agents.fact_extractor import FactExtractor
from src.document_processing.deposition_parser import DepositionParser
from src.models.unified_document_models import DocumentType
from src.document_processing.discovery_splitter import DiscoveryProductionProcessor

logger = logging.getLogger(__name__)

# Document types allowed for fact extraction
# Exclude legal filings and discovery requests which contain derivative/disputed facts
ALLOWED_FACT_EXTRACTION_TYPES = {
    # Primary evidence documents
    DocumentType.MEDICAL_RECORD,
    DocumentType.POLICE_REPORT,
    DocumentType.INCIDENT_REPORT,
    DocumentType.EXPERT_REPORT,
    # Sworn testimony
    DocumentType.DEPOSITION,
    DocumentType.AFFIDAVIT,
    DocumentType.WITNESS_STATEMENT,
    DocumentType.WITNESS_STATEMENT_TRANSCRIPT,
    # Business/Financial records
    DocumentType.INVOICE,
    DocumentType.CONTRACT,
    DocumentType.FINANCIAL_RECORD,
    DocumentType.EMPLOYMENT_RECORD,
    DocumentType.INSURANCE_POLICY,
    DocumentType.INSURANCE_DECLARATION,
    # Discovery responses (verified facts)
    DocumentType.INTERROGATORY_RESPONSE,
    DocumentType.ADMISSION_RESPONSE,
    # Driver/Employee documentation
    DocumentType.DRIVER_QUALIFICATION_FILE,
    DocumentType.EMPLOYMENT_APPLICATION,
    DocumentType.DRIVER_INVESTIGATION_REPORT,
    DocumentType.DRIVING_RECORD_INQUIRY,
    DocumentType.MEDICAL_EXAMINER_CERTIFICATE,
    DocumentType.DRIVER_TRAINING_CERTIFICATE,
    DocumentType.DRUG_TEST_RESULT,
    DocumentType.BACKGROUND_CHECK_REPORT,
    DocumentType.PRE_EMPLOYMENT_SCREENING,
    # Vehicle/Equipment records
    DocumentType.VEHICLE_TITLE,
    DocumentType.VEHICLE_REGISTRATION,
    DocumentType.MAINTENANCE_RECORD,
    DocumentType.INSPECTION_REPORT,
    DocumentType.REPAIR_RECORD,
    DocumentType.ECM_DATA,
    DocumentType.EDR_DATA,
    DocumentType.EOBR_DATA,
    DocumentType.DVIR,
    # Hours of Service documentation
    DocumentType.HOS_LOG,
    DocumentType.TIME_SHEET,
    DocumentType.TRIP_REPORT,
    DocumentType.BILL_OF_LADING,
    DocumentType.FREIGHT_BILL,
    DocumentType.FUEL_RECEIPT,
    DocumentType.TOLL_RECEIPT,
    DocumentType.WEIGHT_TICKET,
    DocumentType.DISPATCH_RECORD,
    # Communication records (factual content)
    DocumentType.EMAIL_CORRESPONDENCE,
    DocumentType.SATELLITE_COMMUNICATION,
    DocumentType.CELLULAR_COMMUNICATION,
    DocumentType.DRIVER_CALL_IN_REPORT,
    DocumentType.TEXT_MESSAGE,
    DocumentType.ONBOARD_SYSTEM_MESSAGE,
    # Other factual records
    DocumentType.COMPENSATION_RECORD,
    DocumentType.PAYROLL_RECORD,
    DocumentType.LEASE_AGREEMENT,
    DocumentType.SAFETY_VIOLATION_REPORT,
    DocumentType.DISCIPLINARY_ACTION,
    DocumentType.ACCIDENT_REGISTER,
    DocumentType.CSA_INTERVENTION_DOCUMENT,
    DocumentType.OUT_OF_SERVICE_REPORT,
    DocumentType.CITATION,
    DocumentType.WARNING,
    DocumentType.COMPLAINT_RECORD,
    DocumentType.ACCIDENT_INVESTIGATION_REPORT,
    DocumentType.ACCIDENT_REVIEW_BOARD_REPORT,
    DocumentType.PREVENTABILITY_DETERMINATION,
    DocumentType.DAMAGE_ESTIMATE,
    DocumentType.REPAIR_INVOICE,
    # Other
    DocumentType.CORRESPONDENCE,
    DocumentType.OTHER,
}


@dataclass
class UnifiedProcessingResult:
    """Result of processing a single document with unified system"""

    document_id: str
    file_name: str
    case_name: str
    status: str  # "success", "duplicate", "failed"
    chunks_created: int
    error_message: Optional[str] = None
    processing_time: Optional[float] = None
    facts_extracted: int = 0
    depositions_parsed: int = 0
    is_duplicate: bool = False
    original_document_id: Optional[str] = None
    document_type: Optional[str] = None
    document_title: Optional[str] = None


class UnifiedDocumentInjector:
    """Document processing pipeline using unified document management"""

    def __init__(
        self,
        enable_cost_tracking: bool = True,
        no_context: bool = False,
        enable_fact_extraction: bool = True,
        force_fact_extraction: bool = False,
    ):
        """Initialize all components

        Args:
            enable_cost_tracking: Whether to track API costs
            no_context: Whether to skip context generation
            enable_fact_extraction: Whether to extract facts and depositions
            force_fact_extraction: Force fact extraction regardless of document type
        """
        logger.info("Initializing Unified Document Injector")

        # Initialize components
        self.box_client = BoxClient()
        self.pdf_extractor = PDFExtractor()
        self.chunker = DocumentChunker()
        self.context_generator = ContextGenerator()
        self.embedding_generator = EmbeddingGenerator()

        # Note: UnifiedDocumentManager will be created per-case
        self.document_manager = None

        # Initialize Qdrant vector store for chunks
        self.vector_store = QdrantVectorStore()

        # Initialize sparse encoder for hybrid search
        self.sparse_encoder = SparseVectorEncoder()
        self.query_analyzer = LegalQueryAnalyzer(self.sparse_encoder)

        # Cost tracking
        self.enable_cost_tracking = enable_cost_tracking
        if enable_cost_tracking:
            self.cost_tracker = CostTracker()

        # Conditional context generation
        self.no_context = no_context

        # Fact extraction flags
        self.enable_fact_extraction = enable_fact_extraction
        self.force_fact_extraction = force_fact_extraction

        # Processing statistics
        self.stats = {
            "total_processed": 0,
            "successful": 0,
            "duplicates": 0,
            "failed": 0,
            "facts_extracted": 0,
            "depositions_parsed": 0,
        }

    def process_case_folder(
        self, folder_id: str, max_documents: Optional[int] = None
    ) -> List[UnifiedProcessingResult]:
        """Process all documents in a case folder

        Args:
            folder_id: Box folder ID to process
            max_documents: Maximum number of documents to process (for testing)

        Returns:
            List of processing results
        """
        logger.info(f"Starting to process case folder: {folder_id}")

        # Get all PDFs from folder
        documents = list(self.box_client.traverse_folder(folder_id))

        if max_documents:
            documents = documents[:max_documents]
            logger.info(f"Limited to processing {max_documents} documents")

        logger.info(f"Found {len(documents)} documents to process")

        # Extract case name from first document
        if documents:
            case_name = documents[0].case_name
            logger.info(f"Processing case: {case_name}")

            # Create case-specific unified document manager
            self.document_manager = UnifiedDocumentManager(case_name=case_name)
            logger.info(f"Created unified document manager for: {case_name}")
        else:
            logger.warning("No documents found in folder")
            return []

        # Process each document
        results = []
        for i, box_doc in enumerate(documents, 1):
            logger.info(f"Processing document {i}/{len(documents)}: {box_doc.name}")

            result = self._process_single_document(box_doc)
            results.append(result)

            # Update statistics
            self.stats["total_processed"] += 1
            if result.status == "success":
                self.stats["successful"] += 1
                self.stats["facts_extracted"] += result.facts_extracted
                self.stats["depositions_parsed"] += result.depositions_parsed
            elif result.is_duplicate:
                self.stats["duplicates"] += 1
            else:
                self.stats["failed"] += 1

        # Log summary
        self._log_processing_summary()

        return results

    def _process_single_document(self, box_doc: BoxDocument) -> UnifiedProcessingResult:
        """Process a single document through the unified pipeline"""
        start_time = datetime.utcnow()

        # Track costs if enabled
        if self.enable_cost_tracking:
            doc_cost = self.cost_tracker.start_document(
                box_doc.name, box_doc.file_id, box_doc.case_name
            )

        try:
            # Step 1: Download document
            logger.debug(f"Downloading {box_doc.name}")
            content = self.box_client.download_file(box_doc.file_id)

            # Step 2: Extract text
            extracted = self.pdf_extractor.extract_text(content, box_doc.name)

            if not self.pdf_extractor.validate_extraction(extracted):
                raise ValueError("Text extraction failed or produced invalid results")

            # Step 3: Get Box shared link
            doc_link = self.box_client.get_shared_link(box_doc.file_id)

            # Step 4: Process with unified document manager
            metadata = {
                "name": box_doc.name,
                "size": box_doc.size,
                "modified_at": box_doc.modified_at.isoformat(),
                "folder_path": box_doc.folder_path,
                "subfolder": box_doc.subfolder_name or "root",
                "extracted_text": extracted.text,
                "box_file_id": box_doc.file_id,
                "box_shared_link": doc_link,
            }

            # Run async processing
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                doc_result = loop.run_until_complete(
                    self.document_manager.process_document(
                        file_path=box_doc.path,
                        file_content=content,
                        file_metadata=metadata,
                    )
                )
            finally:
                loop.close()

            # If duplicate, return early
            if doc_result.is_duplicate:
                logger.info(f"Duplicate found: {box_doc.name}")

                if self.enable_cost_tracking:
                    self.cost_tracker.finish_document(
                        doc_result.original_document_id,
                        0,
                        (datetime.utcnow() - start_time).total_seconds(),
                    )

                return UnifiedProcessingResult(
                    document_id=doc_result.document_id,
                    file_name=box_doc.name,
                    case_name=box_doc.case_name,
                    status="duplicate",
                    chunks_created=0,
                    processing_time=(datetime.utcnow() - start_time).total_seconds(),
                    is_duplicate=True,
                    original_document_id=doc_result.original_document_id,
                    document_type=doc_result.document_type.value,
                    document_title=doc_result.title,
                )

            # Step 5: Extract facts and depositions if enabled
            facts_extracted = 0
            depositions_parsed = 0

            if self.enable_fact_extraction:
                # Check if document type is allowed for fact extraction (unless forced)
                if (
                    self.force_fact_extraction
                    or doc_result.document_type in ALLOWED_FACT_EXTRACTION_TYPES
                ):
                    if (
                        self.force_fact_extraction
                        and doc_result.document_type
                        not in ALLOWED_FACT_EXTRACTION_TYPES
                    ):
                        logger.info(
                            f"Force extracting facts from {box_doc.name} (type: {doc_result.document_type.value}) - discovery material"
                        )
                    else:
                        logger.info(
                            f"Extracting facts from {box_doc.name} (type: {doc_result.document_type.value})"
                        )

                    # Extract facts
                    fact_result = self._extract_facts_sync(
                        box_doc.case_name,
                        doc_result.document_id,
                        extracted.text,
                        {
                            "document_name": box_doc.name,
                            "document_type": doc_result.document_type.value,
                        },
                    )
                    if fact_result:
                        facts_extracted = fact_result["facts"]
                        logger.info(f"Extracted {facts_extracted} facts")

                    # Parse depositions if applicable
                    if doc_result.document_type.value == "deposition":
                        depo_result = self._parse_depositions_sync(
                            box_doc.case_name,
                            box_doc.path,
                            extracted.text,
                            {"document_name": box_doc.name},
                        )
                        if depo_result:
                            depositions_parsed = depo_result["depositions"]
                            logger.info(
                                f"Parsed {depositions_parsed} deposition citations"
                            )
                else:
                    logger.info(
                        f"Skipping fact extraction for {box_doc.name} - document type '{doc_result.document_type.value}' is not allowed for fact extraction"
                    )

            # Step 6: Chunk document
            doc_metadata = {
                "case_name": box_doc.case_name,
                "document_name": box_doc.name,
                "document_path": box_doc.path,
                "document_id": doc_result.document_id,  # Link to unified document
                "document_hash": self.document_manager.calculate_document_hash(content),
                "document_link": doc_link,
                "page_count": extracted.page_count,
                "document_type": doc_result.document_type.value,
                "document_title": doc_result.title,
                "folder_path": "/".join(box_doc.folder_path),
                "subfolder": box_doc.subfolder_name or "root",
                "file_size": box_doc.size,
                "modified_at": box_doc.modified_at.isoformat(),
            }

            # Add discovery metadata if present
            if (
                hasattr(box_doc, "metadata")
                and "discovery_production" in box_doc.metadata
            ):
                discovery_info = box_doc.metadata["discovery_production"]
                doc_metadata.update(
                    {
                        "production_batch": discovery_info.get("production_batch"),
                        "production_date": discovery_info.get("production_date"),
                        "producing_party": discovery_info.get("producing_party"),
                        "responsive_to_requests": discovery_info.get(
                            "responsive_to_requests", []
                        ),
                        "confidentiality_designation": discovery_info.get(
                            "confidentiality_designation"
                        ),
                        "custodian": discovery_info.get("custodian"),
                    }
                )

                # Extract Bates number if present in the document
                bates_info = self._extract_bates_number(extracted.text, box_doc.name)
                if bates_info:
                    doc_metadata.update(bates_info)

            chunks = self.chunker.chunk_document(extracted.text, doc_metadata)
            logger.info(f"Created {len(chunks)} chunks from {box_doc.name}")

            # Step 7: Generate contexts if enabled
            if self.no_context:
                chunks_with_context = chunks
                context_usage = None
            else:
                chunk_texts = [chunk.content for chunk in chunks]
                chunks_with_context, context_usage = (
                    self.context_generator.generate_contexts_sync(
                        chunk_texts, extracted.text
                    )
                )

            # Track context generation costs
            if self.enable_cost_tracking and context_usage:
                self.cost_tracker.track_context_usage(
                    box_doc.file_id,
                    context_usage["prompt_tokens"],
                    context_usage["completion_tokens"],
                    model=self.context_generator.model,
                )

            # Step 8: Generate embeddings and prepare for storage
            storage_chunks = []

            for chunk, context_chunk in zip(chunks, chunks_with_context):
                # Prepare search text
                search_text = self.sparse_encoder.prepare_search_text(
                    getattr(
                        context_chunk, "combined_content", context_chunk.original_chunk
                    )
                )

                # Generate dense embedding
                embedding, embedding_tokens = (
                    self.embedding_generator.generate_embedding(
                        getattr(
                            context_chunk,
                            "combined_content",
                            context_chunk.original_chunk,
                        )
                    )
                )

                # Generate sparse vectors
                keyword_sparse, citation_sparse = (
                    self.sparse_encoder.encode_for_hybrid_search(
                        getattr(
                            context_chunk,
                            "combined_content",
                            context_chunk.original_chunk,
                        )
                    )
                )

                # Track embedding costs
                if self.enable_cost_tracking:
                    self.cost_tracker.track_embedding_usage(
                        box_doc.file_id,
                        embedding_tokens,
                        model=self.embedding_generator.model,
                    )

                # Extract legal entities
                entities = self.sparse_encoder.extract_legal_entities(
                    getattr(
                        context_chunk, "combined_content", context_chunk.original_chunk
                    )
                )

                # Prepare chunk data
                chunk_data = {
                    "content": getattr(
                        context_chunk, "combined_content", context_chunk.original_chunk
                    ),
                    "embedding": embedding,
                    "search_text": search_text,
                    "keywords_sparse": keyword_sparse,
                    "citations_sparse": citation_sparse,
                    "metadata": {
                        **chunk.metadata,
                        "has_context": bool(getattr(context_chunk, "context", None)),
                        "original_length": len(chunk.content),
                        "context_length": len(getattr(context_chunk, "context", "")),
                        "has_citations": bool(entities["citations"]),
                        "citation_count": len(entities["citations"]),
                        "has_monetary": bool(entities["monetary"]),
                        "has_dates": bool(entities["dates"]),
                    },
                }
                storage_chunks.append(chunk_data)

            # Step 9: Store chunks in Qdrant
            chunk_ids = self.vector_store.store_document_chunks(
                case_name=box_doc.case_name,
                document_id=doc_result.document_id,
                chunks=storage_chunks,
                use_hybrid=True,
            )

            logger.info(
                f"Successfully stored {len(chunk_ids)} chunks for {box_doc.name}"
            )

            # Complete cost tracking
            if self.enable_cost_tracking:
                self.cost_tracker.finish_document(
                    doc_result.document_id,
                    len(chunk_ids),
                    (datetime.utcnow() - start_time).total_seconds(),
                )

            return UnifiedProcessingResult(
                document_id=doc_result.document_id,
                file_name=box_doc.name,
                case_name=box_doc.case_name,
                status="success",
                chunks_created=len(chunk_ids),
                processing_time=(datetime.utcnow() - start_time).total_seconds(),
                facts_extracted=facts_extracted,
                depositions_parsed=depositions_parsed,
                document_type=doc_result.document_type.value,
                document_title=doc_result.title,
            )

        except Exception as e:
            logger.error(f"Error processing {box_doc.name}: {str(e)}")

            # Track failed document
            if self.enable_cost_tracking and "doc_result" in locals():
                self.cost_tracker.finish_document(
                    doc_result.document_id
                    if "doc_result" in locals()
                    else box_doc.file_id,
                    0,
                    (datetime.utcnow() - start_time).total_seconds(),
                )

            return UnifiedProcessingResult(
                document_id=box_doc.file_id,
                file_name=box_doc.name,
                case_name=box_doc.case_name,
                status="failed",
                chunks_created=0,
                error_message=str(e),
                processing_time=(datetime.utcnow() - start_time).total_seconds(),
            )

    def _extract_facts_sync(
        self, case_name: str, doc_id: str, content: str, metadata: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Synchronous wrapper for async fact extraction"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            fact_extractor = FactExtractor(case_name)
            fact_collection = loop.run_until_complete(
                fact_extractor.extract_facts_from_document(doc_id, content, metadata)
            )
            return {
                "facts": len(fact_collection.facts),
                "fact_list": fact_collection.facts,
            }
        except Exception as e:
            logger.error(f"Error extracting facts: {e}")
            return None
        finally:
            loop.close()

    def _parse_depositions_sync(
        self, case_name: str, doc_path: str, content: str, metadata: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Synchronous wrapper for async deposition parsing"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            depo_parser = DepositionParser(case_name)
            depositions = loop.run_until_complete(
                depo_parser.parse_deposition(doc_path, content, metadata)
            )
            return {"depositions": len(depositions), "citations": depositions}
        except Exception as e:
            logger.error(f"Error parsing depositions: {e}")
            return None
        finally:
            loop.close()

    def _extract_bates_number(
        self, text: str, filename: str
    ) -> Optional[Dict[str, str]]:
        """Extract Bates number from document text or filename

        Args:
            text: Document text content
            filename: Document filename

        Returns:
            Dictionary with bates_start and bates_end if found
        """
        import re

        # Common Bates patterns
        bates_patterns = [
            r"([A-Z]+[-_]?\d{4,})",  # DEF00001, ABC-12345
            r"(\d{4,}[-_]?[A-Z]+)",  # 00001-DEF, 12345_ABC
            r"([A-Z]+\s*\d{4,})",  # DEF 00001
            r"(\d{4,}\s*[A-Z]+)",  # 00001 DEF
        ]

        bates_info = {}

        # Check filename first
        for pattern in bates_patterns:
            match = re.search(pattern, filename)
            if match:
                bates_info["bates_number"] = match.group(1)
                logger.debug(f"Found Bates number in filename: {match.group(1)}")
                break

        # Check document header/footer (first and last 500 chars)
        if not bates_info:
            search_text = text[:500] + "\n" + text[-500:] if len(text) > 1000 else text

            for pattern in bates_patterns:
                matches = re.findall(pattern, search_text, re.IGNORECASE)
                if matches:
                    # Take first and last if multiple found
                    bates_info["bates_start"] = matches[0]
                    if len(matches) > 1:
                        bates_info["bates_end"] = matches[-1]
                    logger.debug(f"Found Bates numbers in text: {bates_info}")
                    break

        return bates_info if bates_info else None

    def _log_processing_summary(self):
        """Log processing summary statistics"""
        logger.info("=" * 50)
        logger.info("Processing Summary:")
        logger.info(f"Total documents processed: {self.stats['total_processed']}")
        logger.info(f"Successful: {self.stats['successful']}")
        logger.info(f"Duplicates: {self.stats['duplicates']}")
        logger.info(f"Failed: {self.stats['failed']}")

        if self.enable_fact_extraction:
            logger.info(f"Facts extracted: {self.stats['facts_extracted']}")
            logger.info(f"Depositions parsed: {self.stats['depositions_parsed']}")

        # Get document statistics from unified manager
        if self.document_manager:
            doc_stats = self.document_manager.get_statistics()
            logger.info(
                f"Total unique documents in case: {doc_stats.get('unique_documents', 0)}"
            )
            logger.info(f"Document types: {doc_stats.get('document_types', {})}")

        logger.info("Qdrant collections initialized and ready")
        logger.info("=" * 50)

    def get_cost_report(self) -> Dict[str, Any]:
        """Get the current cost report"""
        if self.enable_cost_tracking:
            return self.cost_tracker.get_session_report()
        return {}

    def search_documents(
        self,
        case_name: str,
        query: str,
        document_types: Optional[List[str]] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Search for documents using the unified system"""
        if not self.document_manager or self.document_manager.case_name != case_name:
            self.document_manager = UnifiedDocumentManager(case_name=case_name)

        from src.models.unified_document_models import (
            DocumentSearchRequest,
            DocumentType,
        )

        search_request = DocumentSearchRequest(
            case_name=case_name,
            query=query,
            document_types=[DocumentType(dt) for dt in document_types]
            if document_types
            else None,
            limit=limit,
        )

        # Run async search
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            results = loop.run_until_complete(
                self.document_manager.search_documents(search_request)
            )

            # Convert to simple dict format
            return [
                {
                    "document_id": result.document.id,
                    "title": result.document.title,
                    "type": result.document.document_type.value,
                    "summary": result.document.summary,
                    "score": result.score,
                    "file_path": result.document.file_path,
                    "key_facts": result.document.key_facts,
                    "relevance": [tag.value for tag in result.document.relevance_tags],
                }
                for result in results
            ]
        finally:
            loop.close()

    def process_discovery_folder(
        self, folder_id: str, case_name: str, discovery_metadata: Dict[str, Any]
    ) -> List[UnifiedProcessingResult]:
        """Process discovery materials with special handling

        Args:
            folder_id: Box folder ID containing discovery materials
            case_name: Case name for isolation
            discovery_metadata: Metadata about the production (batch, date, etc.)

        Returns:
            List of processing results
        """
        logger.info(f"Processing discovery folder: {folder_id} for case: {case_name}")
        logger.info(f"Discovery metadata: {discovery_metadata}")

        # Store original state and force fact extraction
        original_force_fact = self.force_fact_extraction
        self.force_fact_extraction = True

        try:
            # Get all PDFs from folder
            documents = list(self.box_client.traverse_folder(folder_id))
            logger.info(f"Found {len(documents)} documents in discovery folder")

            # Override case name for all documents
            for doc in documents:
                doc.case_name = case_name

            # Create case-specific unified document manager
            self.document_manager = UnifiedDocumentManager(case_name=case_name)
            logger.info(f"Created unified document manager for: {case_name}")

            # Process each document
            results = []
            for i, box_doc in enumerate(documents, 1):
                logger.info(
                    f"Processing discovery document {i}/{len(documents)}: {box_doc.name}"
                )

                # Check if this is a large multi-document production
                if self._is_multi_document_production(box_doc):
                    logger.info(f"Detected multi-document production: {box_doc.name}")
                    production_results = self._process_discovery_production(
                        box_doc, case_name, discovery_metadata
                    )
                    results.extend(production_results)
                else:
                    # Process as single document
                    box_doc.metadata = {
                        **getattr(box_doc, "metadata", {}),
                        "discovery_production": discovery_metadata,
                    }

                    result = self._process_single_discovery_document(
                        box_doc, discovery_metadata
                    )
                    results.append(result)

                # Update statistics
                for result in (
                    results[-1:]
                    if not isinstance(results[-1], list)
                    else results[len(results) - len(production_results) :]
                ):
                    self.stats["total_processed"] += 1
                    if result.status == "success":
                        self.stats["successful"] += 1
                        self.stats["facts_extracted"] += result.facts_extracted
                        self.stats["depositions_parsed"] += result.depositions_parsed
                    elif result.is_duplicate:
                        self.stats["duplicates"] += 1
                    else:
                        self.stats["failed"] += 1

            # Log summary
            logger.info(
                f"Discovery processing complete: {len(results)} documents processed"
            )
            self._log_processing_summary()

            return results

        finally:
            # Restore original state
            self.force_fact_extraction = original_force_fact

    def _is_multi_document_production(self, box_doc: BoxDocument) -> bool:
        """Check if document is likely a multi-document production"""
        # Check if multi-doc detection is enabled
        if not settings.discovery.enable_multi_doc_detection:
            return False

        # Heuristics for multi-document productions:
        # 1. Large file size (configurable threshold)
        # 2. High page count (> 50 pages)
        # 3. Filename patterns suggesting production

        # Check file size (Box provides size in bytes)
        size_threshold_bytes = (
            settings.discovery.multi_doc_size_threshold_mb * 1024 * 1024
        )
        if box_doc.size > size_threshold_bytes:
            return True

        # Check filename patterns
        production_patterns = [
            r"production[\s_-]?\d+",
            r"bates[\s_-]?\d+",
            r"discovery[\s_-]?response",
            r"responsive[\s_-]?documents",
            r"combined[\s_-]?pdf",
            r"merged[\s_-]?documents",
        ]

        filename_lower = box_doc.name.lower()
        for pattern in production_patterns:
            if re.search(pattern, filename_lower):
                return True

        # If we can quickly check page count (would need to download first page)
        # For now, return False if no other indicators
        return False

    def _process_discovery_production(
        self, box_doc: BoxDocument, case_name: str, discovery_metadata: Dict[str, Any]
    ) -> List[UnifiedProcessingResult]:
        """Process a multi-document discovery production using the splitter"""
        logger.info(f"Processing multi-document production: {box_doc.name}")

        results = []

        try:
            # Download the PDF to a temporary location
            import tempfile

            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
                content = self.box_client.download_file(box_doc.file_id)
                tmp_file.write(content)
                tmp_path = tmp_file.name

            # Process with discovery splitter
            production_processor = DiscoveryProductionProcessor(case_name)
            production_result = production_processor.process_discovery_production(
                tmp_path, discovery_metadata
            )

            # Process each segment found
            for segment in production_result.segments_found:
                if segment.extraction_successful:
                    # Create a virtual BoxDocument for each segment
                    segment_doc = self._create_segment_box_document(
                        box_doc, segment, production_result
                    )

                    # Process the segment
                    result = self._process_single_discovery_document(
                        segment_doc, discovery_metadata
                    )
                    results.append(result)
                else:
                    # Create failed result for unsuccessful segments
                    results.append(
                        UnifiedProcessingResult(
                            document_id=segment.segment_id,
                            file_name=f"{box_doc.name}_pages_{segment.start_page}-{segment.end_page}",
                            case_name=case_name,
                            status="failed",
                            chunks_created=0,
                            error_message="Segment extraction failed",
                        )
                    )

            # Clean up temp file
            import os

            os.unlink(tmp_path)

            # Log production summary
            logger.info(
                f"Production processing complete: {len(production_result.segments_found)} documents found"
            )
            if production_result.errors:
                logger.warning(f"Production errors: {production_result.errors}")

        except Exception as e:
            logger.error(f"Error processing discovery production: {str(e)}")
            results.append(
                UnifiedProcessingResult(
                    document_id=box_doc.file_id,
                    file_name=box_doc.name,
                    case_name=case_name,
                    status="failed",
                    chunks_created=0,
                    error_message=f"Production processing failed: {str(e)}",
                )
            )

        return results

    def _create_segment_box_document(
        self, original_doc: BoxDocument, segment: Any, production_result: Any
    ) -> BoxDocument:
        """Create a virtual BoxDocument for a segment of a production"""

        # Create a copy with segment-specific information
        segment_doc = BoxDocument(
            name=f"{original_doc.name}_segment_{segment.segment_id}",
            file_id=f"{original_doc.file_id}_{segment.segment_id}",
            size=0,  # Will be calculated during processing
            modified_at=original_doc.modified_at,
            path=original_doc.path,
            folder_path=original_doc.folder_path,
            case_name=original_doc.case_name,
            subfolder_name=original_doc.subfolder_name,
        )

        # Add segment metadata
        segment_doc.metadata = {
            "is_segment": True,
            "original_file_id": original_doc.file_id,
            "original_file_name": original_doc.name,
            "segment_id": segment.segment_id,
            "segment_pages": f"{segment.start_page + 1}-{segment.end_page + 1}",
            "segment_type": segment.document_type.value,
            "segment_confidence": segment.confidence_score,
            "segment_bates_range": segment.bates_range,
            "production_id": production_result.production_id,
        }

        return segment_doc

    def _process_single_discovery_document(
        self, box_doc: BoxDocument, discovery_metadata: Dict[str, Any]
    ) -> UnifiedProcessingResult:
        """Process a single discovery document with enhanced metadata"""
        # Check if this is a segment from a production
        if hasattr(box_doc, "metadata") and box_doc.metadata.get("is_segment"):
            # This is a segment - it's already been extracted and classified
            # We need to process it with the segment-aware pipeline
            return self._process_discovery_segment(box_doc, discovery_metadata)
        else:
            # Regular single document processing
            result = self._process_single_document(box_doc)
            return result

    def _process_discovery_segment(
        self, segment_doc: BoxDocument, discovery_metadata: Dict[str, Any]
    ) -> UnifiedProcessingResult:
        """Process a pre-segmented discovery document"""
        logger.info(
            f"Processing discovery segment: {segment_doc.metadata['segment_type']}"
        )

        # The segment has already been extracted and classified
        # We need to chunk it with document-specific context

        # Note: This would need the actual text extraction from the segment
        # For now, using standard processing
        return self._process_single_document(segment_doc)


# Utility function for testing
def test_unified_connection():
    """Test unified document injector connections"""
    logger.info("Testing Unified Document Injector connections...")

    try:
        injector = UnifiedDocumentInjector()

        # Test Box connection
        if injector.box_client.check_connection():
            logger.info("✓ Box connection successful")
        else:
            logger.error("✗ Box connection failed")

        # Test Qdrant connection
        try:
            collections = injector.vector_store.client.get_collections()
            logger.info(
                f"✓ Qdrant connection successful - Collections: {[c.name for c in collections.collections]}"
            )
        except Exception as e:
            logger.error(f"✗ Qdrant connection failed: {str(e)}")

        # Test OpenAI connection
        try:
            test_embedding, _ = injector.embedding_generator.generate_embedding("test")
            logger.info("✓ OpenAI connection successful")
        except:
            logger.error("✗ OpenAI connection failed")

        logger.info("✓ Unified document manager will be created per-case")
        logger.info("Connection tests complete")

    except Exception as e:
        logger.error(f"Error during connection test: {str(e)}")


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Run connection test
    test_unified_connection()

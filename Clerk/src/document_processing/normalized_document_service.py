"""
Normalized Document Processing Service

This service orchestrates the complete document processing pipeline using the normalized
database schema. It integrates all components for efficient document lifecycle management.

Key Features:
1. End-to-end document processing pipeline
2. Transaction-based operations
3. Enhanced error handling and recovery
4. Performance monitoring and optimization
5. Batch processing capabilities
6. Quality assurance and validation
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

from .hierarchical_document_manager import HierarchicalDocumentManager
from .enhanced_chunker import EnhancedChunker
from .pdf_extractor import PDFExtractor
from .box_client import BoxClient
from ..models.normalized_document_models import (
    Matter, Case, DocumentCore, DocumentMetadata, ChunkMetadata,
    NormalizedDocumentCreateRequest, NormalizedDocumentResponse,
    HierarchicalSearchRequest, HierarchicalSearchResponse,
    MatterType, CaseStatus, AccessLevel
)
from ..models.unified_document_models import DocumentType
from ..vector_storage.qdrant_store import QdrantVectorStore
from ..vector_storage.embeddings import EmbeddingGenerator
from ..ai_agents.fact_extractor import FactExtractor
from ..utils.logger import setup_logger
from ..utils.cost_tracker import CostTracker

logger = setup_logger(__name__)


@dataclass
class ProcessingMetrics:
    """Metrics for document processing operations"""
    documents_processed: int = 0
    chunks_created: int = 0
    duplicates_found: int = 0
    processing_time_seconds: float = 0.0
    api_calls_made: int = 0
    total_cost_usd: float = 0.0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class BatchProcessingConfig:
    """Configuration for batch processing operations"""
    max_concurrent_documents: int = 5
    max_concurrent_chunks: int = 20
    retry_attempts: int = 3
    retry_delay_seconds: float = 1.0
    enable_cost_tracking: bool = True
    enable_fact_extraction: bool = True
    quality_threshold: float = 0.7


class NormalizedDocumentService:
    """
    Complete document processing service using normalized database schema
    """
    
    def __init__(self,
                 qdrant_store: QdrantVectorStore,
                 embedding_generator: EmbeddingGenerator,
                 box_client: Optional[BoxClient] = None,
                 fact_extractor: Optional[FactExtractor] = None,
                 cost_tracker: Optional[CostTracker] = None):
        """
        Initialize the normalized document service
        
        Args:
            qdrant_store: Vector database store
            embedding_generator: For generating embeddings
            box_client: For Box integration (optional)
            fact_extractor: For extracting legal facts (optional)
            cost_tracker: For tracking API costs (optional)
        """
        self.qdrant_store = qdrant_store
        self.embedding_generator = embedding_generator
        self.box_client = box_client
        self.fact_extractor = fact_extractor
        self.cost_tracker = cost_tracker or CostTracker()
        
        # Core components
        self.document_manager = HierarchicalDocumentManager(qdrant_store)
        self.chunker = EnhancedChunker(embedding_generator)
        self.pdf_extractor = PDFExtractor()
        
        self.logger = logger
        
        # Processing state
        self._processing_stats = ProcessingMetrics()
        self._active_transactions = {}
    
    # Matter and Case Management
    
    async def create_matter(self, 
                          matter_number: str,
                          client_name: str,
                          matter_name: str,
                          matter_type: MatterType,
                          description: Optional[str] = None,
                          partner_in_charge: Optional[str] = None) -> Matter:
        """Create a new legal matter"""
        try:
            matter = Matter(
                matter_number=matter_number,
                client_name=client_name,
                matter_name=matter_name,
                matter_type=matter_type,
                description=description,
                partner_in_charge=partner_in_charge,
                opened_date=datetime.now()
            )
            
            result = await self.document_manager.create_matter(matter)
            self.logger.info(f"Created matter: {matter_name} ({result.id})")
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to create matter {matter_name}: {e}")
            raise
    
    async def create_case(self,
                        matter_id: str,
                        case_number: str,
                        case_name: str,
                        plaintiffs: List[str],
                        defendants: List[str],
                        court_name: Optional[str] = None,
                        judge_name: Optional[str] = None) -> Case:
        """Create a new case within a matter"""
        try:
            case = Case(
                matter_id=matter_id,
                case_number=case_number,
                case_name=case_name,
                plaintiffs=plaintiffs,
                defendants=defendants,
                court_name=court_name,
                judge_name=judge_name,
                status=CaseStatus.ACTIVE
            )
            
            result = await self.document_manager.create_case(case)
            self.logger.info(f"Created case: {case_name} ({result.id}) in matter {matter_id}")
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to create case {case_name}: {e}")
            raise
    
    # Document Processing
    
    async def process_document(self,
                             file_path: str,
                             case_id: str,
                             file_content: Optional[bytes] = None,
                             document_type_hint: Optional[DocumentType] = None,
                             title_hint: Optional[str] = None,
                             enable_fact_extraction: bool = True) -> NormalizedDocumentResponse:
        """
        Process a single document through the complete pipeline
        
        Args:
            file_path: Path to the document file
            case_id: ID of the case to associate document with
            file_content: Document content bytes (if not provided, will be read)
            document_type_hint: Suggested document type
            title_hint: Suggested document title
            enable_fact_extraction: Whether to extract legal facts
            
        Returns:
            Complete processing response with all metadata
        """
        start_time = datetime.now()
        transaction_id = f"doc_process_{start_time.isoformat()}"
        
        try:
            async with self._transaction_context(transaction_id):
                # Step 1: Load document content if not provided
                if file_content is None:
                    if self.box_client and file_path.startswith('box://'):
                        file_content = await self._load_from_box(file_path)
                    else:
                        with open(file_path, 'rb') as f:
                            file_content = f.read()
                
                # Step 2: Extract text content
                extracted_text, page_boundaries = await self._extract_text_content(
                    file_content, file_path
                )
                
                # Step 3: Create document in normalized system
                create_request = NormalizedDocumentCreateRequest(
                    file_name=file_path.split('/')[-1],
                    file_path=file_path,
                    file_content=file_content,
                    case_id=case_id,
                    document_type_hint=document_type_hint,
                    title_hint=title_hint
                )
                
                document_response = await self.document_manager.create_document(create_request)
                
                # Step 4: Create enhanced chunks
                chunks = await self.chunker.create_chunks(
                    document_core=document_response.document_core,
                    document_text=extracted_text,
                    page_boundaries=page_boundaries
                )
                
                # Step 5: Store chunks in database
                await self._store_chunks_batch(chunks)
                
                # Step 6: Extract facts if enabled
                if enable_fact_extraction and self.fact_extractor:
                    await self._extract_document_facts(
                        document_response.document_core,
                        extracted_text,
                        chunks
                    )
                
                # Step 7: Update response with chunk information
                document_response.chunks_created = len(chunks)
                document_response.processing_time_seconds = (
                    datetime.now() - start_time
                ).total_seconds()
                
                # Step 8: Update processing metrics
                self._processing_stats.documents_processed += 1
                self._processing_stats.chunks_created += len(chunks)
                if document_response.is_duplicate:
                    self._processing_stats.duplicates_found += 1
                
                self.logger.info(
                    f"Successfully processed document: {file_path} "
                    f"({len(chunks)} chunks, {document_response.processing_time_seconds:.2f}s)"
                )
                
                return document_response
                
        except Exception as e:
            self.logger.error(f"Failed to process document {file_path}: {e}")
            self._processing_stats.errors.append(f"Document {file_path}: {str(e)}")
            raise
    
    async def process_documents_batch(self,
                                    documents: List[Dict[str, Any]],
                                    config: Optional[BatchProcessingConfig] = None) -> List[NormalizedDocumentResponse]:
        """
        Process multiple documents in parallel with optimization
        
        Args:
            documents: List of document processing requests
            config: Batch processing configuration
            
        Returns:
            List of processing responses
        """
        if config is None:
            config = BatchProcessingConfig()
        
        start_time = datetime.now()
        results = []
        
        try:
            # Process documents in batches to control concurrency
            semaphore = asyncio.Semaphore(config.max_concurrent_documents)
            
            async def process_single_with_semaphore(doc_info):
                async with semaphore:
                    return await self._process_with_retry(doc_info, config)
            
            # Create tasks for all documents
            tasks = [
                process_single_with_semaphore(doc_info) 
                for doc_info in documents
            ]
            
            # Execute with progress tracking
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results and handle exceptions
            processed_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    self.logger.error(f"Failed to process document {i}: {result}")
                    self._processing_stats.errors.append(f"Document {i}: {str(result)}")
                else:
                    processed_results.append(result)
            
            # Update batch metrics
            processing_time = (datetime.now() - start_time).total_seconds()
            self._processing_stats.processing_time_seconds += processing_time
            
            self.logger.info(
                f"Batch processing completed: {len(processed_results)}/{len(documents)} documents "
                f"processed successfully in {processing_time:.2f}s"
            )
            
            return processed_results
            
        except Exception as e:
            self.logger.error(f"Batch processing failed: {e}")
            raise
    
    async def _process_with_retry(self,
                                doc_info: Dict[str, Any],
                                config: BatchProcessingConfig) -> NormalizedDocumentResponse:
        """Process a document with retry logic"""
        last_exception = None
        
        for attempt in range(config.retry_attempts):
            try:
                return await self.process_document(**doc_info)
            except Exception as e:
                last_exception = e
                if attempt < config.retry_attempts - 1:
                    await asyncio.sleep(config.retry_delay_seconds * (2 ** attempt))
                    self.logger.warning(
                        f"Retry {attempt + 1}/{config.retry_attempts} for document "
                        f"{doc_info.get('file_path', 'unknown')}: {e}"
                    )
        
        raise last_exception
    
    # Search and Retrieval
    
    async def hierarchical_search(self,
                                request: HierarchicalSearchRequest) -> HierarchicalSearchResponse:
        """Perform hierarchical search across the normalized schema"""
        try:
            return await self.document_manager.hierarchical_search(request)
        except Exception as e:
            self.logger.error(f"Hierarchical search failed: {e}")
            raise
    
    async def search_documents_in_case(self,
                                     case_id: str,
                                     query: str,
                                     document_types: Optional[List[DocumentType]] = None,
                                     limit: int = 20) -> List[Dict[str, Any]]:
        """Search for documents within a specific case"""
        try:
            search_request = HierarchicalSearchRequest(
                query=query,
                case_ids=[case_id],
                document_types=document_types,
                max_results=limit
            )
            
            response = await self.hierarchical_search(search_request)
            return response.results
            
        except Exception as e:
            self.logger.error(f"Case search failed for case {case_id}: {e}")
            raise
    
    # Utility Methods
    
    async def _load_from_box(self, box_path: str) -> bytes:
        """Load document content from Box"""
        if not self.box_client:
            raise ValueError("Box client not configured")
        
        # Extract file ID from box:// path
        file_id = box_path.replace('box://', '')
        return await self.box_client.download_file(file_id)
    
    async def _extract_text_content(self, 
                                  file_content: bytes, 
                                  file_path: str) -> Tuple[str, Optional[List[int]]]:
        """Extract text content and page boundaries from document"""
        try:
            if file_path.lower().endswith('.pdf'):
                result = self.pdf_extractor.extract_text_with_metadata(file_content)
                return result['text'], result.get('page_boundaries')
            else:
                # Handle other file types
                text = file_content.decode('utf-8', errors='ignore')
                return text, None
                
        except Exception as e:
            self.logger.error(f"Text extraction failed for {file_path}: {e}")
            raise
    
    async def _store_chunks_batch(self, chunks: List[ChunkMetadata]):
        """Store chunks in the database with batch optimization"""
        try:
            # Prepare points for batch insertion
            points = []
            for chunk in chunks:
                point = {
                    'id': chunk.id,
                    'vector': chunk.dense_vector or [0.0] * 1536,
                    'payload': chunk.model_dump()
                }
                points.append(point)
            
            # Store in batches
            batch_size = 100
            for i in range(0, len(points), batch_size):
                batch = points[i:i + batch_size]
                self.qdrant_store.upsert_points(
                    collection_name=self.document_manager.collections['chunk_metadata'],
                    points=batch
                )
            
            self.logger.info(f"Stored {len(chunks)} chunks in database")
            
        except Exception as e:
            self.logger.error(f"Failed to store chunks batch: {e}")
            raise
    
    async def _extract_document_facts(self,
                                    document_core: DocumentCore,
                                    document_text: str,
                                    chunks: List[ChunkMetadata]):
        """Extract legal facts from document using AI"""
        if not self.fact_extractor:
            return
        
        try:
            # Extract facts using the fact extractor
            facts = await self.fact_extractor.extract_facts(
                document_text=document_text,
                document_type=DocumentType.OTHER,  # Would be from metadata
                case_context=""
            )
            
            # Store facts (would need a facts storage system)
            self.logger.info(f"Extracted {len(facts)} facts from document {document_core.id}")
            
        except Exception as e:
            self.logger.error(f"Fact extraction failed for document {document_core.id}: {e}")
    
    @asynccontextmanager
    async def _transaction_context(self, transaction_id: str):
        """Context manager for transaction-like operations"""
        self._active_transactions[transaction_id] = {
            'started_at': datetime.now(),
            'operations': []
        }
        
        try:
            yield transaction_id
        except Exception as e:
            # Handle rollback logic here
            self.logger.error(f"Transaction {transaction_id} failed: {e}")
            raise
        finally:
            # Cleanup transaction
            self._active_transactions.pop(transaction_id, None)
    
    # Monitoring and Statistics
    
    def get_processing_metrics(self) -> ProcessingMetrics:
        """Get current processing metrics"""
        return self._processing_stats
    
    async def get_case_statistics(self, case_id: str) -> Dict[str, Any]:
        """Get comprehensive statistics for a case"""
        try:
            return await self.document_manager.get_case_statistics(case_id)
        except Exception as e:
            self.logger.error(f"Failed to get case statistics for {case_id}: {e}")
            return {}
    
    async def verify_data_integrity(self, case_id: str) -> Dict[str, Any]:
        """Verify data integrity for a case"""
        try:
            return await self.document_manager.verify_case_isolation(case_id)
        except Exception as e:
            self.logger.error(f"Data integrity verification failed for {case_id}: {e}")
            return {'error': str(e)}
    
    def reset_processing_metrics(self):
        """Reset processing metrics"""
        self._processing_stats = ProcessingMetrics()
    
    async def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health status"""
        try:
            health = {
                'status': 'healthy',
                'timestamp': datetime.now(),
                'components': {
                    'qdrant_store': 'unknown',
                    'embedding_generator': 'unknown',
                    'box_client': 'unknown',
                    'fact_extractor': 'unknown'
                },
                'processing_metrics': self._processing_stats,
                'active_transactions': len(self._active_transactions)
            }
            
            # Test core components
            try:
                await self.qdrant_store.test_connection()
                health['components']['qdrant_store'] = 'healthy'
            except Exception:
                health['components']['qdrant_store'] = 'unhealthy'
                health['status'] = 'degraded'
            
            if self.box_client:
                try:
                    await self.box_client.test_connection()
                    health['components']['box_client'] = 'healthy'
                except Exception:
                    health['components']['box_client'] = 'unhealthy'
            
            return health
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.now()
            }
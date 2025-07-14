"""
Refactored Discovery Processing System
This replaces the complex normalized processing with direct case collection usage
while maintaining all robust features like document type detection and classification.
"""

import logging
import os
import tempfile
from datetime import datetime
from typing import List, Dict, Any, Optional
import uuid

from src.api.discovery_endpoints import (
    ExtractedFactWithSource,
    DiscoveryProcessingStatus,
    processing_status
)
from src.document_processing.discovery_splitter import (
    DiscoveryProductionProcessor,
    DiscoverySegment,
    DiscoveryProductionResult,
)
from src.document_processing.unified_document_manager import UnifiedDocumentManager
from src.document_processing.enhanced_chunker import EnhancedChunker
from src.vector_storage.embeddings import EmbeddingGenerator
from src.vector_storage.qdrant_store import QdrantVectorStore
from src.models.unified_document_models import DocumentType, UnifiedDocument
from src.ai_agents.fact_extractor import FactExtractor
from src.websocket.socket_server import sio
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


async def process_discovery_async_refactored(
    processing_id: str,
    case_name: str,
    request: Any,
    discovery_files: List[Dict[str, Any]],
    rfp_file: Optional[Any],
    production_batch: str,
    producing_party: str,
    production_date: Optional[str],
    responsive_to_requests: List[str],
    confidentiality_designation: Optional[str],
    enable_fact_extraction: bool,
):
    """
    Refactored background task for processing discovery documents.
    Uses existing case collections directly without hierarchical document manager.
    """
    # Initialize core services
    vector_store = QdrantVectorStore()
    embedding_generator = EmbeddingGenerator()
    
    # Use the basic discovery processor - no normalized wrapper
    discovery_processor = DiscoveryProductionProcessor(case_name=case_name)
    
    # Document manager for deduplication
    document_manager = UnifiedDocumentManager(case_name, vector_store)
    
    # Fact extractor if enabled
    fact_extractor = FactExtractor(case_name=case_name) if enable_fact_extraction else None
    
    # Enhanced chunker for creating chunks
    chunker = EnhancedChunker(
        embedding_generator=embedding_generator,
        chunk_size=1400,
        chunk_overlap=200
    )
    
    # Track processing status
    processing_result = {
        "processing_id": processing_id,
        "status": "in_progress",
        "total_documents_found": 0,
        "documents_processed": 0,
        "facts_extracted": 0,
        "errors": []
    }
    
    try:
        # Emit start event
        await sio.emit("discovery:started", {
            "processing_id": processing_id,
            "case_name": case_name,
            "total_files": len(discovery_files or [])
        })
        
        # Process each uploaded PDF
        for idx, file_data in enumerate(discovery_files or []):
            filename = file_data.get("filename", f"discovery_{idx}.pdf")
            content = file_data.get("content", b"")
            
            # Save PDF temporarily
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
                tmp_file.write(content)
                temp_pdf_path = tmp_file.name
            
            try:
                # Create metadata for discovery processing
                production_metadata = {
                    "production_batch": production_batch or f"batch_{idx}",
                    "producing_party": producing_party or "Unknown",
                    "production_date": production_date or datetime.now().isoformat(),
                    "responsive_to_requests": responsive_to_requests or [],
                    "confidentiality_designation": confidentiality_designation,
                }
                
                # Process with discovery splitter to find document boundaries
                logger.info(f"Processing discovery production: {filename}")
                production_result = discovery_processor.process_discovery_production(
                    pdf_path=temp_pdf_path,
                    production_metadata=production_metadata
                )
                
                # Update total documents found
                processing_result["total_documents_found"] += len(production_result.segments_found)
                logger.info(f"Found {len(production_result.segments_found)} documents in {filename}")
                
                # Process each segment as a separate document
                for segment_idx, segment in enumerate(production_result.segments_found):
                    try:
                        # Emit document found event
                        await sio.emit("discovery:document_found", {
                            "processing_id": processing_id,
                            "document_id": f"{processing_id}_seg_{segment_idx}",
                            "title": segment.title or f"Document {segment.document_type}",
                            "type": segment.document_type.value,
                            "pages": f"{segment.start_page}-{segment.end_page}",
                            "bates_range": segment.bates_range,
                            "confidence": segment.confidence_score
                        })
                        
                        # Extract text for this segment
                        segment_text = extract_text_from_pages(
                            temp_pdf_path, 
                            segment.start_page, 
                            segment.end_page
                        )
                        
                        # Check for duplicates
                        doc_hash = document_manager.generate_document_hash(segment_text)
                        if await document_manager.is_duplicate(doc_hash):
                            logger.info(f"Skipping duplicate document: {segment.title}")
                            continue
                        
                        # Create unified document
                        unified_doc = UnifiedDocument(
                            # Required fields
                            case_name=case_name,
                            document_hash=doc_hash,
                            file_name=f"{segment.title or 'document'}.pdf",
                            file_path=f"discovery/{production_batch}/{segment.title or 'document'}.pdf",
                            file_size=len(segment_text.encode('utf-8')),
                            document_type=segment.document_type,
                            title=segment.title or f"{segment.document_type} Document",
                            description=f"Discovery document: {segment.document_type.value} from {producing_party}",
                            last_modified=datetime.utcnow(),
                            total_pages=segment.end_page - segment.start_page + 1,
                            summary=f"Pages {segment.start_page}-{segment.end_page} of discovery production",
                            search_text=segment_text,
                            # Discovery-specific metadata
                            metadata={
                                "producing_party": producing_party,
                                "production_batch": production_batch,
                                "bates_range": segment.bates_range,
                                "page_range": f"{segment.start_page}-{segment.end_page}",
                                "confidence_score": segment.confidence_score,
                                "processing_id": processing_id,
                                "document_boundaries": segment.boundary_indicators,
                                "is_complete": segment.is_complete,
                                "responsive_to_requests": responsive_to_requests,
                                "confidentiality_designation": confidentiality_designation,
                            }
                        )
                        
                        # Store document metadata
                        doc_id = await document_manager.add_document(unified_doc)
                        logger.info(f"Added document {doc_id} to case {case_name}")
                        
                        # Create chunks with context
                        await sio.emit("discovery:chunking", {
                            "processing_id": processing_id,
                            "document_id": doc_id,
                            "status": "started"
                        })
                        
                        chunks = chunker.create_chunks_with_context(
                            text=segment_text,
                            document_id=doc_id,
                            metadata=unified_doc.metadata
                        )
                        
                        # Prepare chunks for storage
                        await sio.emit("discovery:embedding", {
                            "processing_id": processing_id,
                            "document_id": doc_id,
                            "total_chunks": len(chunks)
                        })
                        
                        # Prepare all chunks for batch storage
                        chunk_data = []
                        for chunk_idx, chunk in enumerate(chunks):
                            # Generate embedding
                            embedding = await embedding_generator.generate_embedding(chunk.text)
                            
                            chunk_data.append({
                                "content": chunk.text,
                                "embedding": embedding,
                                "metadata": {
                                    **chunk.metadata,
                                    "chunk_index": chunk_idx,
                                    "total_chunks": len(chunks),
                                    "document_name": segment.title or f"Document {segment.document_type}",
                                    "document_type": segment.document_type.value,
                                    "document_path": f"discovery/{production_batch}/{segment.title or 'document'}.pdf",
                                    "bates_range": segment.bates_range,
                                    "producing_party": producing_party,
                                    "production_batch": production_batch,
                                }
                            })
                        
                        # Store all chunks in the main case collection
                        if chunk_data:
                            try:
                                stored_ids = vector_store.store_document_chunks(
                                    case_name=case_name,  # Uses the main case collection
                                    document_id=doc_id,
                                    chunks=chunk_data,
                                    use_hybrid=True
                                )
                                logger.info(f"Stored {len(stored_ids)} chunks for document {doc_id}")
                            except Exception as e:
                                logger.error(f"Failed to store chunks: {e}")
                                raise
                        
                        # Extract facts if enabled and store in case_facts collection
                        if enable_fact_extraction and fact_extractor:
                            facts_result = await fact_extractor.extract_facts_from_document(
                                document_id=doc_id,
                                document_content=segment_text,
                                document_type=segment.document_type.value,
                                metadata={
                                    "bates_range": segment.bates_range,
                                    "producing_party": producing_party,
                                    "production_batch": production_batch
                                }
                            )
                            
                            # Stream facts as they're extracted
                            for fact in facts_result.facts:
                                await sio.emit("discovery:fact_extracted", {
                                    "processing_id": processing_id,
                                    "document_id": doc_id,
                                    "fact": {
                                        "fact_id": fact.id,
                                        "text": fact.content,
                                        "category": fact.category,
                                        "confidence": fact.confidence,
                                        "entities": fact.entities,
                                        "dates": fact.dates,
                                        "source_metadata": {
                                            "bates_range": segment.bates_range,
                                            "page_range": f"{segment.start_page}-{segment.end_page}"
                                        }
                                    }
                                })
                                processing_result["facts_extracted"] += 1
                        
                        # Update processed count
                        processing_result["documents_processed"] += 1
                        
                        # Check if this is a deposition and store in depositions collection
                        if segment.document_type == DocumentType.DEPOSITION:
                            await store_deposition_metadata(
                                vector_store, case_name, doc_id, segment, segment_text
                            )
                        
                    except Exception as segment_error:
                        logger.error(f"Error processing segment {segment_idx}: {str(segment_error)}")
                        processing_result["errors"].append({
                            "segment": segment_idx,
                            "error": str(segment_error)
                        })
                        
                        await sio.emit("discovery:error", {
                            "processing_id": processing_id,
                            "document_id": f"{processing_id}_seg_{segment_idx}",
                            "error": str(segment_error)
                        })
                        
            finally:
                # Clean up temp file
                if os.path.exists(temp_pdf_path):
                    os.unlink(temp_pdf_path)
        
        # Update final status
        processing_result["status"] = "completed"
        processing_result["completed_at"] = datetime.utcnow().isoformat()
        
        # Update processing status
        processing_status[processing_id].status = "completed"
        processing_status[processing_id].total_documents = processing_result["total_documents_found"]
        processing_status[processing_id].processed_documents = processing_result["documents_processed"]
        processing_status[processing_id].total_facts = processing_result["facts_extracted"]
        processing_status[processing_id].completed_at = datetime.utcnow()
        
        # Emit completion event
        await sio.emit("discovery:completed", processing_result)
        
        logger.info(f"Discovery processing completed: {processing_result}")
        
    except Exception as e:
        logger.error(f"Error in discovery processing: {str(e)}")
        processing_result["status"] = "failed"
        processing_result["error"] = str(e)
        
        processing_status[processing_id].status = "error"
        processing_status[processing_id].error_message = str(e)
        
        await sio.emit("discovery:error", {
            "processing_id": processing_id,
            "error": str(e)
        })


def extract_text_from_pages(pdf_path: str, start_page: int, end_page: int) -> str:
    """Extract text from specific page range in PDF."""
    import pdfplumber
    
    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num in range(start_page - 1, min(end_page, len(pdf.pages))):
                page = pdf.pages[page_num]
                page_text = page.extract_text() or ""
                text += page_text + "\n"
    except Exception as e:
        logger.error(f"Error extracting text from pages {start_page}-{end_page}: {e}")
        raise
    return text


async def store_deposition_metadata(
    vector_store: QdrantVectorStore,
    case_name: str,
    document_id: str,
    segment: DiscoverySegment,
    text: str
):
    """Store deposition-specific metadata in the depositions collection."""
    try:
        # Extract deponent name if possible
        deponent_name = None
        if segment.title and "DEPOSITION OF" in segment.title.upper():
            deponent_name = segment.title.upper().replace("DEPOSITION OF", "").strip()
        
        # Create deposition entry
        deposition_data = {
            "document_id": document_id,
            "deponent_name": deponent_name,
            "deposition_date": segment.metadata.get("date"),
            "page_range": f"{segment.start_page}-{segment.end_page}",
            "bates_range": segment.bates_range,
            "case_name": case_name,
            "indexed_at": datetime.utcnow().isoformat()
        }
        
        # Store in depositions collection
        collection_name = f"{case_name}_depositions"
        # Note: Implementation depends on how depositions are stored
        # This is a placeholder for the deposition-specific logic
        
    except Exception as e:
        logger.error(f"Error storing deposition metadata: {e}")
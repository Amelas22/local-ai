"""
Enhanced Discovery Processing API Endpoints

This module provides comprehensive API endpoints for discovery document processing,
fact extraction, and real-time review capabilities.
"""

from fastapi import (
    APIRouter,
    HTTPException,
    Depends,
    File,
    Form,
    BackgroundTasks,
    Request,
)
from starlette.datastructures import UploadFile
from typing import List, Optional, Dict, Any
import uuid
import base64
import asyncio
import hashlib

from ..models.discovery_models import (
    DiscoveryProcessingRequest as EndpointDiscoveryRequest,
    DiscoveryProcessingResponse,
    DiscoveryProcessingStatus,
    ExtractedFactWithSource,
    FactUpdateRequest,
    FactSearchRequest,
    FactSearchResponse,
    FactBulkOperation,
)
from ..services.fact_manager import FactManager
from ..document_processing.unified_document_manager import UnifiedDocumentManager
from ..document_processing.enhanced_chunker import EnhancedChunker
from ..vector_storage.embeddings import EmbeddingGenerator
from ..models.unified_document_models import DocumentType, UnifiedDocument, DiscoveryProcessingRequest
from ..ai_agents.fact_extractor import FactExtractor
from ..websocket.socket_server import (
    sio,
    emit_discovery_started,
    emit_document_found,
    emit_chunking_progress,
    emit_embedding_progress,
    emit_document_stored,
    emit_processing_completed,
    emit_processing_error
)

# MVP Mode conditional imports
import os
import tempfile
from datetime import datetime
import pdfplumber

if os.getenv("MVP_MODE", "false").lower() == "true":
    from ..utils.mock_auth import (
        get_mock_case_context as get_case_context,
        mock_require_case_context as require_case_context,
    )
    from types import SimpleNamespace as CaseContext
else:
    from ..middleware.case_context import (
        get_case_context,
        require_case_context,
        CaseContext,
    )

from ..document_processing.box_client import BoxClient
from ..document_processing.pdf_extractor import PDFExtractor
from ..vector_storage.qdrant_store import QdrantVectorStore
from ..utils.logger import setup_logger

logger = setup_logger(__name__)

if os.getenv("MVP_MODE", "false").lower() == "true":
    logger.warning("Discovery endpoints using MVP mode - case permissions bypassed")
router = APIRouter(prefix="/api/discovery", tags=["discovery"])

# Global dictionary to track processing status
processing_status: Dict[str, DiscoveryProcessingStatus] = {}


@router.post("/process", response_model=DiscoveryProcessingResponse)
async def process_discovery(
    request: Request,
    background_tasks: BackgroundTasks,
    case_context: CaseContext = Depends(require_case_context("write")),
) -> DiscoveryProcessingResponse:
    """
    Process discovery documents with real-time WebSocket updates.

    Supports multiple input sources:
    - Direct file uploads (base64 encoded)
    - Box folder selection
    - Optional RFP document for context
    """
    processing_id = str(uuid.uuid4())
    
    # Check content type to handle different request formats
    content_type = request.headers.get("content-type", "")
    logger.info(f"Discovery request content-type: {content_type}")
    
    # Initialize default values
    discovery_files = []
    box_folder_id = None
    rfp_file = None
    defense_response_file = None
    production_batch = "Batch001"
    producing_party = "Opposing Counsel"
    production_date = None
    responsive_to_requests = []
    confidentiality_designation = None
    enable_fact_extraction = True
    
    try:
        if "application/json" in content_type:
            # Handle JSON request with base64-encoded files
            request_data = await request.json()
            
            # Extract fields from JSON request
            discovery_files = request_data.get("discovery_files", [])
            box_folder_id = request_data.get("box_folder_id")
            rfp_file = request_data.get("rfp_file")
            defense_response_file = request_data.get("defense_response_file")
            production_batch = request_data.get("production_batch", "Batch001")
            producing_party = request_data.get("producing_party", "Opposing Counsel")
            production_date = request_data.get("production_date")
            responsive_to_requests = request_data.get("responsive_to_requests", [])
            confidentiality_designation = request_data.get("confidentiality_designation")
            enable_fact_extraction = request_data.get("enable_fact_extraction", True)
        else:
            # Handle multipart/form-data or raw binary upload
            # Try to parse as form data first
            try:
                form = await request.form()
                logger.info(f"Form keys: {list(form.keys())}")
                
                # Get files from form
                files = []
                
                # Get the discovery_files specifically
                discovery_file = form.get("discovery_files")
                logger.info(f"Got discovery_file directly: {type(discovery_file)}, is UploadFile: {isinstance(discovery_file, UploadFile)}")
                if discovery_file and isinstance(discovery_file, UploadFile):
                        logger.info(f"Found UploadFile: {discovery_file.filename}, size: {discovery_file.size}")
                        # Read file content
                        content = await discovery_file.read()
                        logger.info(f"Read {len(content)} bytes from file")
                        files.append({
                            "filename": discovery_file.filename,
                            "content": base64.b64encode(content).decode('utf-8'),
                            "content_type": discovery_file.content_type
                        })
                        await discovery_file.close()
                
                logger.info(f"Total files found: {len(files)}")
                if files:
                    discovery_files = files
                    logger.info(f"Set discovery_files to {len(discovery_files)} files")
                
                # Handle RFP file
                rfp_upload = form.get("rfp_file")
                if rfp_upload and isinstance(rfp_upload, UploadFile):
                    logger.info(f"Found RFP file: {rfp_upload.filename}")
                    content = await rfp_upload.read()
                    rfp_file = {
                        "filename": rfp_upload.filename,
                        "content": base64.b64encode(content).decode('utf-8'),
                        "content_type": rfp_upload.content_type
                    }
                    await rfp_upload.close()
                
                # Handle Defense Response file
                defense_upload = form.get("defense_response_file")
                if defense_upload and isinstance(defense_upload, UploadFile):
                    logger.info(f"Found Defense Response file: {defense_upload.filename}")
                    content = await defense_upload.read()
                    defense_response_file = {
                        "filename": defense_upload.filename,
                        "content": base64.b64encode(content).decode('utf-8'),
                        "content_type": defense_upload.content_type
                    }
                    await defense_upload.close()
                
                # Get other form fields
                production_batch = form.get("production_batch", "Batch001")
                producing_party = form.get("producing_party", "Opposing Counsel")
                production_date = form.get("production_date")
                responsive_to_requests = form.getlist("responsive_to_requests") or []
                confidentiality_designation = form.get("confidentiality_designation")
                enable_fact_extraction = form.get("enable_fact_extraction", "true").lower() == "true"
                
            except Exception as form_error:
                # If form parsing fails, treat as raw binary upload
                logger.warning(f"Form parsing failed, attempting raw binary: {form_error}")
                
                # Read raw body as binary
                body = await request.body()
                if body:
                    # Assume it's a PDF file
                    discovery_files = [{
                        "filename": "discovery_upload.pdf",
                        "content": base64.b64encode(body).decode('utf-8'),
                        "content_type": "application/pdf"
                    }]
                    
    except Exception as e:
        logger.error(f"Error parsing request: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid request format. Please send either JSON with base64-encoded files or multipart/form-data. Error: {str(e)}"
        )

    # Initialize processing status
    status = DiscoveryProcessingStatus(
        processing_id=processing_id,
        case_id=case_context.case_id,
        case_name=case_context.case_name,
        total_documents=0,
        processed_documents=0,
        total_facts=0,
        status="processing",
    )
    processing_status[processing_id] = status

    logger.info(f"Before background task - discovery_files: {len(discovery_files)}")
    
    # Create a simple request object for the background task
    # We'll handle the file data manually to avoid encoding issues
    discovery_request = type('DiscoveryRequest', (), {
        'discovery_files': [f.get("filename", f"file_{i}.pdf") for i, f in enumerate(discovery_files)],
        'box_folder_id': box_folder_id,
        'rfp_file': None
    })()
    logger.info(f"Created discovery_request with files: {discovery_request.discovery_files}")

    # Handle file uploads - files come as base64 encoded in JSON
    file_contents = []
    if discovery_files:
        logger.info(f"Processing {len(discovery_files)} discovery files")
        for idx, file_data in enumerate(discovery_files):
            logger.info(f"File {idx}: type={type(file_data)}, keys={file_data.keys() if isinstance(file_data, dict) else 'not a dict'}")
            if isinstance(file_data, dict):
                filename = file_data.get("filename", f"discovery_{idx}.pdf")
                content_b64 = file_data.get("content", "")
                
                # Decode base64 content
                try:
                    content = base64.b64decode(content_b64) if content_b64 else b""
                except Exception as e:
                    logger.error(f"Failed to decode base64 content for {filename}: {e}")
                    content = b""
                    
                file_contents.append({
                    "filename": filename,
                    "content": content,
                    "content_type": "application/pdf"
                })
    
    background_tasks.add_task(
        _process_discovery_async,
        processing_id,
        case_context.case_name,
        discovery_request,
        file_contents,  # Pass file contents instead of UploadFile objects
        rfp_file,
        defense_response_file,
        production_batch,
        producing_party,
        production_date,
        responsive_to_requests,
        confidentiality_designation,
        enable_fact_extraction,
    )

    # Emit WebSocket event to case room
    from src.websocket.socket_server import emit_discovery_started
    await emit_discovery_started(
        processing_id=processing_id,
        case_id=case_context.case_id,
        total_files=len(discovery_files) if discovery_files else 0
    )

    return DiscoveryProcessingResponse(
        processing_id=processing_id,
        status="started",
        message="Discovery processing started",
    )


async def _process_discovery_async(
    processing_id: str,
    case_name: str,
    request: EndpointDiscoveryRequest,
    discovery_files: List[Dict[str, Any]],
    rfp_file: Optional[UploadFile],
    defense_response_file: Optional[Dict[str, Any]],
    production_batch: str,
    producing_party: str,
    production_date: Optional[str],
    responsive_to_requests: List[str],
    confidentiality_designation: Optional[str],
    enable_fact_extraction: bool,
):
    """Background task for processing discovery documents with document splitting"""
    logger.info(f"🚀 Starting async discovery processing for {processing_id}")
    logger.info(f"📋 Case: {case_name}, Files: {len(discovery_files or [])}")
    logger.info(f"📋 Production batch: {production_batch}, Producing party: {producing_party}")
    logger.info(f"📋 Fact extraction enabled: {enable_fact_extraction}")
    
    # Initialize processors
    vector_store = QdrantVectorStore()
    embedding_generator = EmbeddingGenerator()
    
    # Use the basic discovery processor directly - no normalized wrapper
    from src.document_processing.discovery_splitter import DiscoveryProductionProcessor
    
    # Document manager for deduplication
    document_manager = UnifiedDocumentManager(case_name)
    
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
        "started_at": datetime.utcnow().isoformat(),
        "total_documents_found": 0,
        "documents_processed": 0,
        "facts_extracted": 0,
        "chunks_created": 0,
        "vectors_stored": 0,
        "errors": []
    }
    
    try:
        logger.info(f"Emitting discovery:started event")
        # Emit start event
        await emit_discovery_started(
            processing_id=processing_id,
            case_id=case_name,
            total_files=len(discovery_files or [])
        )
        logger.info(f"Event emitted, processing {len(discovery_files or [])} files")
        
        # Process each uploaded PDF
        for idx, file_data in enumerate(discovery_files or []):
            filename = file_data.get("filename", f"discovery_{idx}.pdf")
            content = file_data.get("content", b"")
            
            # Save PDF temporarily
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
                tmp_file.write(content)
                temp_pdf_path = tmp_file.name
            
            try:
                
                # Process with discovery splitter
                logger.info(f"📄 [Discovery {processing_id}] Processing PDF: {filename}")
                production_metadata = {
                    "production_batch": production_batch or f"batch_{idx}",
                    "producing_party": producing_party or "Unknown",
                    "production_date": production_date or datetime.now().isoformat(),
                    "responsive_to_requests": responsive_to_requests or [],
                    "confidentiality_designation": confidentiality_designation,
                }
                logger.info(f"📝 [Discovery {processing_id}] Production metadata: {production_metadata}")
                
                # Create progress callback to emit WebSocket events
                async def emit_progress(event_type: str, data: dict):
                    """Emit progress events during discovery processing"""
                    if event_type == "boundary_detection_started":
                        await sio.emit(
                            "discovery:boundary_detection_started",
                            {
                                "processingId": processing_id,
                                "message": data.get("message"),
                                "totalPages": data.get("total_pages")
                            },
                            room=f"case_{case_name}"
                        )
                    elif event_type == "boundary_detection_progress":
                        await sio.emit(
                            "discovery:boundary_detection_progress",
                            {
                                "processingId": processing_id,
                                "message": data.get("message"),
                                "currentWindow": data.get("current_window"),
                                "totalWindows": data.get("total_windows"),
                                "progressPercent": data.get("progress_percent")
                            },
                            room=f"case_{case_name}"
                        )
                    elif event_type == "boundary_detection_completed":
                        await sio.emit(
                            "discovery:boundary_detection_completed",
                            {
                                "processingId": processing_id,
                                "message": data.get("message"),
                                "boundariesFound": data.get("boundaries_found")
                            },
                            room=f"case_{case_name}"
                        )
                
                logger.info(f"🔍 [Discovery {processing_id}] Calling discovery processor for {filename}")
                discovery_processor = DiscoveryProductionProcessor(case_name, progress_callback=emit_progress)
                production_result = await discovery_processor.process_discovery_production(
                    pdf_path=temp_pdf_path,
                    production_metadata=production_metadata
                )
                
                # Log discovery results
                logger.info(f"✅ [Discovery {processing_id}] Found {len(production_result.segments_found)} segments")
                logger.info(f"📊 [Discovery {processing_id}] Average confidence: {production_result.average_confidence}")
                for idx, seg in enumerate(production_result.segments_found):
                    logger.info(f"  📑 Segment {idx}: {seg.document_type.value} '{seg.title}' pages {seg.start_page}-{seg.end_page}")
                
                # Update total documents found
                processing_result["total_documents_found"] += len(production_result.segments_found)
                
                # Process each segment as a separate document
                for segment_idx, segment in enumerate(production_result.segments_found):
                    try:
                        # Emit document found event
                        doc_id = f"{processing_id}_seg_{segment_idx}"
                        page_count = segment.end_page - segment.start_page + 1
                        logger.info(f"📤 [Discovery {processing_id}] Emitting discovery:document_found for segment {segment_idx}")
                        logger.info(f"   - Document ID: {doc_id}")
                        logger.info(f"   - Title: {segment.title}")
                        logger.info(f"   - Type: {segment.document_type.value}")
                        logger.info(f"   - Page count: {page_count}")
                        await emit_document_found(
                            processing_id=processing_id,
                            case_id=case_name,
                            document_id=doc_id,
                            title=segment.title or f"Document {segment.document_type}",
                            doc_type=segment.document_type.value,
                            page_count=page_count,
                            bates_range=segment.bates_range,
                            confidence=segment.confidence_score
                        )
                        
                        # Extract text for this segment in a thread to avoid blocking
                        loop = asyncio.get_event_loop()
                        segment_text = await loop.run_in_executor(
                            None,
                            extract_text_from_pages,
                            temp_pdf_path, 
                            segment.start_page, 
                            segment.end_page
                        )
                        
                        # Check for duplicates
                        logger.info(f"Checking for duplicates - manager type: {type(document_manager)}")
                        logger.info(f"Has is_duplicate method: {hasattr(document_manager, 'is_duplicate')}")
                        doc_hash = document_manager.calculate_document_hash(segment_text.encode('utf-8'))
                        logger.info(f"Document hash calculated: {doc_hash}")
                        
                        try:
                            is_dup = await document_manager.is_duplicate(doc_hash)
                            if is_dup:
                                logger.info(f"Skipping duplicate document: {segment.title}")
                                continue
                        except Exception as e:
                            logger.error(f"Error checking duplicate: {type(e).__name__}: {str(e)}")
                            await emit_processing_error(
                                processing_id=processing_id,
                                case_id=case_name,
                                error=f"Duplicate check failed: {str(e)}",
                                stage="duplicate_check"
                            )
                            raise
                        
                        # Create unified document with correct fields
                        unified_doc = UnifiedDocument(
                            # Required fields
                            case_name=case_name,
                            document_hash=doc_hash,
                            file_name=f"{segment.title or 'document'}.pdf",
                            file_path=f"discovery/{production_batch}/{segment.title or 'document'}.pdf",
                            file_size=len(segment_text.encode('utf-8')),  # Approximate size
                            document_type=segment.document_type,
                            title=segment.title or f"{segment.document_type} Document",
                            description=f"Discovery document: {segment.document_type.value} from {producing_party}",
                            last_modified=datetime.utcnow(),
                            total_pages=segment.end_page - segment.start_page + 1,
                            summary=f"Pages {segment.start_page}-{segment.end_page} of discovery production",
                            search_text=segment_text,
                            # Optional fields with discovery metadata
                            metadata={
                                "producing_party": producing_party,
                                "production_batch": production_batch,
                                "bates_range": segment.bates_range,
                                "page_range": f"{segment.start_page}-{segment.end_page}",
                                "confidence_score": segment.confidence_score,
                                "processing_id": processing_id,
                            }
                        )
                        
                        # Store document metadata
                        stored_doc_id = await document_manager.add_document(unified_doc)
                        
                        # Create chunks with context
                        logger.info(f"🔪 [Discovery {processing_id}] Starting chunking for document {stored_doc_id}")
                        await emit_chunking_progress(
                            processing_id=processing_id,
                            case_id=case_name,
                            document_id=stored_doc_id,
                            progress=0.0,
                            chunks_created=0
                        )
                        
                        # Create document core for chunker
                        from src.models.normalized_document_models import DocumentCore
                        
                        # Calculate metadata hash if needed
                        metadata_str = str(sorted(unified_doc.metadata.items()))
                        metadata_hash = hashlib.sha256(metadata_str.encode()).hexdigest()
                        
                        doc_core = DocumentCore(
                            id=stored_doc_id,
                            document_hash=doc_hash,
                            metadata_hash=metadata_hash,
                            file_name=unified_doc.file_name,
                            original_file_path=unified_doc.file_path,
                            file_size=unified_doc.file_size,
                            mime_type="application/pdf",
                            total_pages=unified_doc.total_pages,
                            file_created_at=unified_doc.last_modified,
                            file_modified_at=unified_doc.last_modified
                        )
                        
                        try:
                            chunks = await chunker.create_chunks(
                                document_core=doc_core,
                                document_text=segment_text
                            )
                            logger.info(f"Created {len(chunks)} chunks for segment {segment_idx}")
                        except Exception as e:
                            logger.error(f"Failed to create chunks for segment {segment_idx}: {str(e)}")
                            await emit_processing_error(
                                processing_id=processing_id,
                                case_id=case_name,
                                error=f"Chunking failed for segment {segment_idx}: {str(e)}",
                                stage="chunking"
                            )
                            raise
                        
                        # Generate embeddings and store chunks
                        logger.info(f"🧮 [Discovery {processing_id}] Starting embedding generation for {len(chunks)} chunks")
                        await emit_embedding_progress(
                            processing_id=processing_id,
                            case_id=case_name,
                            document_id=stored_doc_id,
                            chunk_id="all",
                            progress=0.0
                        )
                        
                        # Prepare all chunks for batch storage
                        chunk_data = []
                        logger.info(f"📦 [Discovery {processing_id}] Preparing {len(chunks)} chunks for batch storage")
                        
                        for chunk_idx, chunk in enumerate(chunks):
                            # Generate embedding
                            try:
                                # Get chunk text from ChunkMetadata object
                                chunk_text = chunk.chunk_text
                                logger.debug(f"Chunk {chunk_idx}: text length = {len(chunk_text)} chars")
                                embedding, token_count = await embedding_generator.generate_embedding_async(chunk_text)
                                logger.debug(f"Generated embedding for chunk {chunk_idx} with {token_count} tokens")
                            except Exception as e:
                                logger.error(f"Failed to generate embedding for chunk {chunk_idx}: {str(e)}")
                                await emit_processing_error(
                                    processing_id=processing_id,
                                    case_id=case_name,
                                    error=f"Embedding generation failed for chunk {chunk_idx}: {str(e)}",
                                    stage="embedding_generation"
                                )
                                raise
                            
                            # Use the actual chunk text field
                            chunk_content = chunk_text
                            
                            # Build metadata from chunk attributes
                            chunk_metadata = {
                                "chunk_index": chunk_idx,
                                "total_chunks": len(chunks),
                                "document_id": stored_doc_id,
                                "document_name": segment.title or f"Document {segment.document_type}",
                                "document_type": segment.document_type.value,
                                "document_path": f"discovery/{production_batch}/{segment.title or 'document'}.pdf",
                                "bates_range": segment.bates_range,
                                "producing_party": producing_party,
                                "production_batch": production_batch,
                                "section_title": chunk.section_title,
                                "semantic_type": chunk.semantic_type,
                                "start_page": chunk.start_page,
                                "end_page": chunk.end_page,
                            }
                            
                            chunk_data.append({
                                "content": chunk_content,
                                "embedding": embedding,
                                "metadata": chunk_metadata
                            })
                        
                        # Store all chunks at once
                        if chunk_data:
                            try:
                                stored_ids = vector_store.store_document_chunks(
                                    case_name=case_name,
                                    document_id=stored_doc_id,
                                    chunks=chunk_data,
                                    use_hybrid=True
                                )
                                logger.info(f"Stored {len(stored_ids)} chunks for document {stored_doc_id}")
                                
                                # Emit stored event for frontend
                                await emit_document_stored(
                                    processing_id=processing_id,
                                    case_id=case_name,
                                    document_id=stored_doc_id,
                                    vectors_stored=len(stored_ids)
                                )
                            except Exception as e:
                                logger.error(f"Failed to store chunks: {e}")
                                await emit_processing_error(
                                    processing_id=processing_id,
                                    case_id=case_name,
                                    error=f"Vector storage failed: {str(e)}",
                                    stage="vector_storage"
                                )
                                raise
                        
                        # Extract facts if enabled
                        if enable_fact_extraction and fact_extractor:
                            logger.info(f"🔍 [Discovery {processing_id}] Extracting facts from document {stored_doc_id}")
                            facts_result = await fact_extractor.extract_facts_from_document(
                                document_id=doc_id,
                                document_content=segment_text,
                                metadata={
                                    "document_type": segment.document_type.value,
                                    "bates_range": segment.bates_range,
                                    "producing_party": producing_party,
                                    "production_batch": production_batch
                                }
                            )
                            
                            logger.info(f"📊 [Discovery {processing_id}] Extracted {len(facts_result.facts)} facts")
                            
                            # Stream facts as they're extracted
                            for fact in facts_result.facts:
                                logger.info(f"📤 [Discovery {processing_id}] Emitting discovery:fact_extracted")
                                logger.info(f"   - Fact ID: {fact.id}")
                                logger.info(f"   - Category: {fact.category}")
                                logger.info(f"   - Confidence: {fact.confidence_score}")
                                await sio.emit("discovery:fact_extracted", {
                                    "processing_id": processing_id,
                                    "document_id": stored_doc_id,
                                    "fact": {
                                        "fact_id": fact.id,
                                        "text": fact.content,
                                        "category": fact.category,
                                        "confidence": fact.confidence_score,
                                        "entities": fact.entities,
                                        "dates": [ref.date_text for ref in fact.date_references],
                                        "source_metadata": {
                                            "bates_range": segment.bates_range,
                                            "page_range": f"{segment.start_page}-{segment.end_page}"
                                        }
                                    }
                                }, room=f"case_{case_name}")
                                processing_result["facts_extracted"] += 1
                        
                        # Update processed count
                        processing_result["documents_processed"] += 1
                        logger.info(f"Successfully processed segment {segment_idx}. Total processed: {processing_result['documents_processed']}")
                        
                        # Emit document completed event
                        facts_count = len(facts_result.facts) if enable_fact_extraction and facts_result else 0
                        logger.info(f"✅ [Discovery {processing_id}] Document {stored_doc_id} completed")
                        logger.info(f"   - Segment index: {segment_idx}")
                        logger.info(f"   - Facts extracted: {facts_count}")
                        await sio.emit("discovery:document_completed", {
                            "processing_id": processing_id,
                            "document_id": stored_doc_id,
                            "segment_idx": segment_idx,
                            "facts_extracted": facts_count
                        }, room=f"case_{case_name}")
                        
                    except Exception as segment_error:
                        logger.error(f"Error processing segment {segment_idx}: {str(segment_error)}")
                        processing_result["errors"].append({
                            "segment": segment_idx,
                            "error": str(segment_error)
                        })
                        
                        await emit_processing_error(
                            processing_id=processing_id,
                            case_id=case_name,
                            error=str(segment_error),
                            stage="processing_segment"
                        )
                        
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
        summary = {
            "totalDocuments": processing_result.get("total_documents_found", 0),
            "processedDocuments": processing_result.get("documents_processed", 0),
            "totalChunks": processing_result.get("chunks_created", 0),
            "totalVectors": processing_result.get("vectors_stored", 0),
            "totalErrors": len(processing_result.get("errors", [])),
            "totalFacts": processing_result.get("facts_extracted", 0),
            "processingTime": (datetime.utcnow() - datetime.fromisoformat(processing_result["started_at"])).total_seconds()
        }
        logger.info(f"🎉 [Discovery {processing_id}] Processing completed!")
        logger.info(f"   - Total documents found: {summary['totalDocuments']}")
        logger.info(f"   - Documents processed: {summary['processedDocuments']}")
        logger.info(f"   - Total facts extracted: {summary['totalFacts']}")
        logger.info(f"   - Processing time: {summary['processingTime']:.2f}s")
        await emit_processing_completed(
            processing_id=processing_id,
            case_id=case_name,
            summary=summary
        )
        
        # Store processing result
        await store_processing_result(processing_id, processing_result)
        
    except Exception as e:
        logger.error(f"Error in discovery processing: {str(e)}", exc_info=True)
        processing_result["status"] = "failed"
        processing_result["error"] = str(e)
        
        processing_status[processing_id].status = "error"
        processing_status[processing_id].error_message = str(e)
        
        await emit_processing_error(
            processing_id=processing_id,
            case_id=case_name,
            error=str(e),
            stage="discovery_processing"
        )


@router.get("/status/{processing_id}", response_model=DiscoveryProcessingStatus)
async def get_processing_status(
    processing_id: str,
    case_context: CaseContext = Depends(get_case_context),
) -> DiscoveryProcessingStatus:
    """Get the status of a discovery processing job"""
    if processing_id not in processing_status:
        raise HTTPException(404, "Processing ID not found")

    status = processing_status[processing_id]
    if case_context and status.case_id != case_context.case_id:
        raise HTTPException(403, "Access denied")

    return status


@router.post("/facts/search", response_model=FactSearchResponse)
async def search_facts(
    request: FactSearchRequest,
    case_context: CaseContext = Depends(require_case_context("read")),
) -> FactSearchResponse:
    """Search for facts within a case"""
    fact_manager = FactManager()

    # Ensure case isolation
    if request.case_name != case_context.case_name:
        raise HTTPException(403, "Case mismatch")

    facts = await fact_manager.search_facts(
        case_name=request.case_name,
        query=request.query,
        category=request.category,
        confidence_min=request.confidence_min,
        confidence_max=request.confidence_max,
        document_ids=request.document_ids,
        review_status=request.review_status,
        is_edited=request.is_edited,
        limit=request.limit or 100,
        offset=request.offset or 0,
    )

    return FactSearchResponse(
        facts=facts,
        total=len(facts),
        limit=request.limit or 100,
        offset=request.offset or 0,
    )


@router.get("/facts/{fact_id}", response_model=ExtractedFactWithSource)
async def get_fact(
    fact_id: str,
    case_context: CaseContext = Depends(require_case_context("read")),
) -> ExtractedFactWithSource:
    """Get a specific fact by ID"""
    fact_manager = FactManager()

    fact = await fact_manager.get_fact(fact_id, case_context.case_name)
    if not fact:
        raise HTTPException(404, "Fact not found")

    return fact


@router.put("/facts/{fact_id}", response_model=ExtractedFactWithSource)
async def update_fact(
    fact_id: str,
    request: FactUpdateRequest,
    case_context: CaseContext = Depends(require_case_context("write")),
) -> ExtractedFactWithSource:
    """Update a fact's content or category"""
    fact_manager = FactManager()

    updated_fact = await fact_manager.update_fact(
        case_name=case_context.case_name,
        fact_id=fact_id,
        new_content=request.content,
        user_id=case_context.user_id,
        reason=request.reason,
        new_category=request.category,
    )

    # Emit WebSocket update
    await sio.emit(
        "fact:updated",
        {
            "fact_id": fact_id,
            "content": request.content,
            "updated_by": case_context.user_id,
        },
        room=f"case_{case_context.case_id}",
    )

    return updated_fact


@router.delete("/facts/{fact_id}")
async def delete_fact(
    fact_id: str,
    case_context: CaseContext = Depends(require_case_context("write")),
):
    """Delete a fact (soft delete)"""
    fact_manager = FactManager()

    await fact_manager.delete_fact(fact_id, case_context.case_name)

    # Emit WebSocket update
    await sio.emit(
        "fact:deleted",
        {
            "fact_id": fact_id,
            "deleted_by": case_context.user_id,
        },
        room=f"case_{case_context.case_id}",
    )

    return {"message": "Fact deleted successfully"}


@router.post("/facts/bulk")
async def bulk_fact_operation(
    operation: FactBulkOperation,
    case_context: CaseContext = Depends(require_case_context("write")),
) -> Dict[str, int]:
    """Perform bulk operations on facts"""
    fact_manager = FactManager()

    if operation.operation == "mark_reviewed":
        result = await fact_manager.bulk_update_facts(
            case_name=case_context.case_name,
            fact_ids=operation.fact_ids,
            updates={"review_status": "reviewed"},
        )
        return {"updated": result}

    elif operation.operation == "delete":
        result = await fact_manager.bulk_delete_facts(
            case_name=case_context.case_name,
            fact_ids=operation.fact_ids,
        )
        return {"deleted": result}

    elif operation.operation == "change_category" and operation.category:
        result = await fact_manager.bulk_update_facts(
            case_name=case_context.case_name,
            fact_ids=operation.fact_ids,
            updates={"category": operation.category},
        )
        return {"updated": result}

    else:
        raise HTTPException(400, "Invalid bulk operation")


@router.get("/documents/{document_id}/pdf")
async def get_document_pdf(
    document_id: str,
    case_context: CaseContext = Depends(require_case_context("read")),
):
    """Get the PDF file for a document"""
    # This would retrieve the PDF from storage (Box, S3, etc.)
    # For now, return a placeholder
    raise HTTPException(501, "PDF retrieval not implemented")


@router.get("/box/folders")
async def list_box_folders(
    parent_id: str = "0",
    case_context: CaseContext = Depends(require_case_context("read")),
) -> List[Dict[str, Any]]:
    """List Box folders for selection"""
    box_client = BoxClient()
    folders = await box_client.list_folders(parent_id)
    return folders


@router.get("/box/files")
async def list_box_files(
    folder_id: str,
    case_context: CaseContext = Depends(require_case_context("read")),
) -> List[Dict[str, Any]]:
    """List files in a Box folder"""
    box_client = BoxClient()
    files = await box_client.get_folder_files(folder_id)
    return [f for f in files if f["name"].endswith(".pdf")]


@router.get("/websocket-status")
async def get_websocket_status() -> Dict[str, Any]:
    """Get current WebSocket connection status"""
    from src.websocket.socket_server import sio, active_connections
    
    status = {
        "connected_clients": len(active_connections),
        "clients": [],
        "rooms": {}
    }
    
    for sid, info in active_connections.items():
        client_info = {
            "sid": sid,
            "case_id": info.get("case_id"),
            "connected_at": str(info.get("connected_at")),
            "rooms": list(sio.rooms(sid)) if hasattr(sio, 'rooms') else []
        }
        status["clients"].append(client_info)
    
    # Get all rooms
    try:
        for sid, rooms in sio.manager.rooms.get('/', {}).items():
            for room in rooms:
                if room not in status["rooms"]:
                    status["rooms"][room] = []
                status["rooms"][room].append(sid)
    except:
        pass
    
    return status


@router.post("/test-events")
async def test_discovery_events(
    case_context: CaseContext = Depends(get_case_context),
) -> Dict[str, Any]:
    """Test WebSocket event emission with proper snake_case naming"""
    import asyncio
    
    test_id = str(uuid.uuid4())
    logger.info(f"🧪 Starting WebSocket event test: {test_id}")
    
    try:
        # Emit test events with correct snake_case naming
        await emit_discovery_started(
            processing_id=test_id,
            case_id=case_context.case_id if case_context else "test_case",
            total_files=1
        )
        logger.info(f"✅ Emitted discovery:started for test {test_id}")
        
        await asyncio.sleep(1)
        
        # Emit document found event
        doc_id = f"test_doc_{uuid.uuid4()}"
        await emit_document_found(
            processing_id=test_id,
            case_id=case_context.case_id if case_context else "test_case",
            document_id=doc_id,
            title="Test Document",
            doc_type="motion",
            page_count=10,
            bates_range={"start": "001", "end": "010"},
            confidence=0.95
        )
        logger.info(f"✅ Emitted discovery:document_found for document {doc_id}")
        
        await asyncio.sleep(1)
        
        # Emit chunking progress
        await emit_chunking_progress(
            processing_id=test_id,
            case_id=case_context.case_id if case_context else "test_case",
            document_id=doc_id,
            progress=0.5,
            chunks_created=5
        )
        logger.info(f"✅ Emitted discovery:chunking for document {doc_id}")
        
        await asyncio.sleep(1)
        
        # Emit fact extracted
        fact_data = {
            "processing_id": test_id,
            "document_id": doc_id,
            "fact": {
                "fact_id": f"fact_{uuid.uuid4()}",
                "text": "This is a test fact extracted from the document",
                "category": "substantive",
                "confidence": 0.9,
                "entities": ["Test Entity"],
                "dates": ["2024-01-15"],
                "source_metadata": {
                    "document_title": "Test Document",
                    "page": 5,
                    "bbox": [100, 200, 300, 400],
                    "text_snippet": "This is a test fact..."
                }
            }
        }
        await sio.emit("discovery:fact_extracted", fact_data, room=f"case_{case_context.case_id if case_context else 'test_case'}")
        logger.info(f"✅ Emitted discovery:fact_extracted")
        
        await asyncio.sleep(1)
        
        # Emit document completed
        await sio.emit("discovery:document_completed", {
            "processing_id": test_id,
            "document_id": doc_id,
            "facts_extracted": 1
        }, room=f"case_{case_context.case_id if case_context else 'test_case'}")
        logger.info(f"✅ Emitted discovery:document_completed")
        
        await asyncio.sleep(1)
        
        # Emit processing completed
        await emit_processing_completed(
            processing_id=test_id,
            case_id=case_context.case_id if case_context else "test_case",
            summary={
                "totalDocuments": 1,
                "processedDocuments": 1,
                "totalChunks": 5,
                "totalVectors": 5,
                "totalErrors": 0,
                "totalFacts": 1,
                "processingTime": 5.0
            }
        )
        logger.info(f"✅ Emitted discovery:completed")
        
        return {
            "message": "Test events emitted successfully",
            "processing_id": test_id,
            "document_id": doc_id,
            "events_emitted": [
                "discovery:started",
                "discovery:document_found",
                "discovery:chunking",
                "discovery:fact_extracted",
                "discovery:document_completed",
                "discovery:completed"
            ],
            "note": "Check browser console for WebSocket events"
        }
        
    except Exception as e:
        logger.error(f"Error emitting test events: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Test failed: {str(e)}")


# Helper functions for discovery processing
def extract_text_from_pages(pdf_path: str, start_page: int, end_page: int) -> str:
    """
    Extract text from specific page range in PDF.
    
    Args:
        pdf_path: Path to the PDF file
        start_page: Starting page number (1-indexed)
        end_page: Ending page number (inclusive)
    
    Returns:
        Extracted text from the specified page range
    """
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


async def store_processing_result(processing_id: str, result: Dict[str, Any]):
    """
    Store processing result for retrieval.
    
    Args:
        processing_id: Unique ID for the processing job
        result: Processing result data
    """
    # For now, store in the in-memory processing_status dictionary
    # In production, this could be stored in Redis, database, or cache
    if processing_id in processing_status:
        processing_status[processing_id].documents = result.get("documents", {})
        processing_status[processing_id].total_documents = result.get("total_documents_found", 0)
        processing_status[processing_id].processed_documents = result.get("documents_processed", 0)
        processing_status[processing_id].total_facts = result.get("facts_extracted", 0)
        processing_status[processing_id].status = result.get("status", "completed")
        if result.get("completed_at"):
            processing_status[processing_id].completed_at = datetime.fromisoformat(result["completed_at"])
        if result.get("error"):
            processing_status[processing_id].error_message = result["error"]


async def emit_processing_completed(processing_id: str, case_id: str, summary: Dict[str, Any]):
    """
    Emit processing completed event via WebSocket.
    
    Args:
        processing_id: Unique ID for the processing job
        case_id: Case ID for room-based event emission
        summary: Summary of processing results
    """
    await sio.emit(
        "discovery:completed",
        {
            "processingId": processing_id,
            "summary": summary
        },
        room=f"case_{case_id}"
    )


async def emit_processing_error(processing_id: str, case_id: str, error: str, stage: str):
    """
    Emit processing error event via WebSocket.
    
    Args:
        processing_id: Unique ID for the processing job
        case_id: Case ID for room-based event emission
        error: Error message
        stage: Stage where error occurred
    """
    await sio.emit(
        "discovery:error",
        {
            "processingId": processing_id,
            "error": error,
            "stage": stage
        },
        room=f"case_{case_id}"
    )

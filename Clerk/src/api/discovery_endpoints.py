"""
Enhanced Discovery Processing API Endpoints

This module provides comprehensive API endpoints for discovery document processing,
fact extraction, and real-time review capabilities.
"""

from fastapi import (
    APIRouter,
    HTTPException,
    Depends,
    UploadFile,
    File,
    Form,
    BackgroundTasks,
)
from typing import List, Optional, Dict, Any
import uuid

from ..models.discovery_models import (
    DiscoveryProcessingRequest,
    DiscoveryProcessingResponse,
    DiscoveryProcessingStatus,
    ExtractedFactWithSource,
    FactUpdateRequest,
    FactSearchRequest,
    FactSearchResponse,
    FactBulkOperation,
)
from ..services.fact_manager import FactManager
from ..document_processing.discovery_splitter_normalized import (
    NormalizedDiscoveryProductionProcessor,
)
from ..ai_agents.fact_extractor import FactExtractor
from ..websocket.socket_server import sio

# MVP Mode conditional imports
import os

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
    background_tasks: BackgroundTasks,
    case_context: CaseContext = Depends(require_case_context("write")),
    discovery_files: List[UploadFile] = File(None),
    box_folder_id: Optional[str] = Form(None),
    rfp_file: Optional[UploadFile] = File(None),
    production_batch: str = Form(default="Batch001"),
    producing_party: str = Form(default="Opposing Counsel"),
    production_date: Optional[str] = Form(None),
    responsive_to_requests: List[str] = Form(default_factory=list),
    confidentiality_designation: Optional[str] = Form(None),
    enable_fact_extraction: bool = Form(default=True),
) -> DiscoveryProcessingResponse:
    """
    Process discovery documents with real-time WebSocket updates.

    Supports multiple input sources:
    - Direct file uploads
    - Box folder selection
    - Optional RFP document for context
    """
    processing_id = str(uuid.uuid4())

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

    # Prepare request
    request = DiscoveryProcessingRequest(
        discovery_files=[],
        box_folder_id=box_folder_id,
        rfp_file=None,
    )

    # Handle file uploads
    if discovery_files:
        for file in discovery_files:
            if file.content_type != "application/pdf":
                raise HTTPException(400, f"File {file.filename} must be PDF")
            request.discovery_files.append(file.filename)

    # Start background processing
    # Read file contents before passing to background task
    file_contents = []
    if discovery_files:
        for file in discovery_files:
            content = await file.read()
            file_contents.append({
                "filename": file.filename,
                "content": content,
                "content_type": file.content_type
            })
    
    background_tasks.add_task(
        _process_discovery_async,
        processing_id,
        case_context.case_name,
        request,
        file_contents,  # Pass file contents instead of UploadFile objects
        rfp_file,
        production_batch,
        producing_party,
        production_date,
        responsive_to_requests,
        confidentiality_designation,
        enable_fact_extraction,
    )

    # Emit WebSocket event
    await sio.emit(
        "discovery:started",
        {
            "processing_id": processing_id,
            "case_id": case_context.case_id,
            "total_files": len(discovery_files) if discovery_files else 0,
        },
    )

    return DiscoveryProcessingResponse(
        processing_id=processing_id,
        status="started",
        message="Discovery processing started",
    )


async def _process_discovery_async(
    processing_id: str,
    case_name: str,
    request: DiscoveryProcessingRequest,
    discovery_files: List[Dict[str, Any]],  # Changed from UploadFile to dict with content
    rfp_file: Optional[UploadFile],
    production_batch: str,
    producing_party: str,
    production_date: Optional[str],
    responsive_to_requests: List[str],
    confidentiality_designation: Optional[str],
    enable_fact_extraction: bool,
):
    """Background task for processing discovery documents"""
    try:
        qdrant_store = QdrantVectorStore()
        fact_extractor = FactExtractor(case_name=case_name)
        pdf_extractor = PDFExtractor()

        # Process Box folder if specified
        if request.box_folder_id:
            box_client = BoxClient()
            box_files = await box_client.get_folder_files(request.box_folder_id)

            for box_file in box_files:
                if box_file["name"].endswith(".pdf"):
                    await sio.emit(
                        "discovery:document_found",
                        {
                            "processing_id": processing_id,
                            "document_id": box_file["id"],
                            "title": box_file["name"],
                            "type": "unknown",
                            "page_count": 0,
                        },
                    )

        # Process uploaded files
        for idx, file_data in enumerate(discovery_files or []):
            document_id = f"{processing_id}_{idx}"
            filename = file_data.get("filename", f"document_{idx}.pdf")
            content = file_data.get("content", b"")

            await sio.emit(
                "discovery:document_found",
                {
                    "processing_id": processing_id,
                    "document_id": document_id,
                    "title": filename,
                    "type": "unknown",
                    "page_count": 0,
                },
            )

            # Extract text from PDF if it's a PDF file
            text_content = None
            extraction_error = None
            
            if filename.lower().endswith('.pdf') and isinstance(content, bytes):
                logger.info(f"Extracting text from PDF: {filename}")
                try:
                    extracted_doc = pdf_extractor.extract_text(content, filename)
                    text_content = extracted_doc.text
                    logger.info(f"Successfully extracted {len(text_content)} characters from {extracted_doc.page_count} pages")
                except Exception as e:
                    extraction_error = str(e)
                    logger.error(f"Failed to extract text from PDF: {e}")
            else:
                # For non-PDF files, try to decode as text
                if isinstance(content, bytes):
                    try:
                        text_content = content.decode("utf-8")
                    except UnicodeDecodeError:
                        extraction_error = "Unable to decode file as text"
                else:
                    text_content = content
            
            # Emit chunking event
            await sio.emit(
                "discovery:chunking",
                {
                    "processing_id": processing_id,
                    "document_id": document_id,
                    "progress": 50,
                    "chunks_created": 1,
                    "extraction_status": "success" if text_content else "failed",
                    "extraction_error": extraction_error,
                },
            )

            # Extract facts if enabled and we have text content
            if enable_fact_extraction and text_content:
                logger.info(f"Extracting facts from document: {filename}")
                facts = await fact_extractor.extract_facts_from_document(
                    document_id=document_id,
                    document_content=text_content,
                )
                
                for fact in facts.facts:
                    await sio.emit(
                        "discovery:fact_extracted",
                        {
                            "processing_id": processing_id,
                            "fact_id": fact.id,
                            "document_id": document_id,
                            "content": fact.content,
                            "category": fact.category,
                            "confidence": fact.confidence,
                        },
                    )

                processing_status[processing_id].total_facts += len(facts.facts)
            else:
                if not text_content:
                    logger.warning(f"No text content extracted from {filename}, skipping fact extraction")

            processing_status[processing_id].processed_documents += 1

        # Update total documents
        processing_status[processing_id].total_documents = len(discovery_files) if discovery_files else 0
        
        # Mark as completed
        processing_status[processing_id].status = "completed"

        await sio.emit(
            "discovery:completed",
            {
                "processing_id": processing_id,
                "summary": {
                    "total_documents": processing_status[processing_id].total_documents,
                    "processed_documents": processing_status[
                        processing_id
                    ].processed_documents,
                    "total_chunks": 0,
                    "total_vectors": 0,
                    "total_errors": 0,
                    "average_confidence": 0.85,
                    "processing_time": 0,
                },
            },
        )

    except Exception as e:
        logger.error(f"Discovery processing error: {e}")
        processing_status[processing_id].status = "error"
        processing_status[processing_id].error_message = str(e)

        await sio.emit(
            "discovery:error",
            {
                "processing_id": processing_id,
                "error": str(e),
                "stage": "processing",
            },
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

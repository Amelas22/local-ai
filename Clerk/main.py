"""
FastAPI application for Clerk Legal AI System
Provides HTTP API endpoints for document processing and search
"""

import io
import aiohttp
import asyncio
import os
import json
import tempfile
import uuid

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

from fastapi import (
    FastAPI,
    HTTPException,
    BackgroundTasks,
    Depends,
    File,
    UploadFile,
    Form,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, Field

from src.document_injector_unified import UnifiedDocumentInjector
from src.vector_storage.qdrant_store import QdrantVectorStore
from src.vector_storage.embeddings import EmbeddingGenerator
from src.ai_agents.legal_document_agent import legal_document_agent
from src.ai_agents.motion_drafter import motion_drafter, DocumentLength
from src.ai_agents.outline_cache_manager import outline_cache
from src.utils.logger import setup_logging
from src.utils.env_validator import (
    validate_all as validate_environment,
    EnvironmentError,
)
from config.settings import settings
from src.models.unified_document_models import DiscoveryProcessingRequest
from src.document_processing.websocket_document_processor import get_websocket_processor
from src.websocket import socket_app
from src.middleware.mock_user_middleware import MockUserMiddleware
from src.middleware.case_context import CaseContextMiddleware

# MVP Mode conditional imports
if os.getenv("MVP_MODE", "false").lower() == "true":
    from src.utils.mock_auth import get_mock_case_context as get_case_context
else:
    from src.middleware.case_context import get_case_context

from src.database.connection import init_db, close_db

# Import new routers
from src.api.auth_endpoints import router as auth_router
from src.api.case_endpoints import router as case_router
from src.api.discovery_endpoints import router as discovery_router
from src.api.agent_endpoints import router as agent_router
from src.api.deficiency_endpoints import router as deficiency_router
from src.api.agents.good_faith_letter_endpoints import router as good_faith_letter_router

# Setup logging
logger = setup_logging("clerk_api", "INFO")

# Global instances
document_injector = None
vector_store = None
embedding_generator = None
_openai_health_cache = {"status": None, "last_check": None}
HEALTH_CACHE_DURATION = 3600


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    global document_injector, vector_store, embedding_generator

    # Startup
    logger.info("Starting Clerk API service...")
    
    # Initialize temp file cleanup
    from src.utils.temp_file_manager import startup_cleanup, shutdown_cleanup
    await startup_cleanup()
    
    # Initialize rate limiters
    from src.middleware.rate_limiter import init_rate_limiters
    await init_rate_limiters()

    # MVP Mode Warning
    if os.getenv("MVP_MODE", "false").lower() == "true":
        logger.warning("🚨 MVP MODE ACTIVE - NO AUTHENTICATION 🚨")
        logger.warning("All requests will use mock user: dev@clerk.ai")
        logger.warning("DO NOT USE IN PRODUCTION!")
        logger.warning(
            "To disable: Set MVP_MODE=false and restore AuthMiddleware in main.py"
        )

    # Validate settings
    if not settings.validate():
        logger.error("Invalid configuration. Please check environment variables.")
        raise RuntimeError("Invalid configuration")

    # Validate environment variables
    try:
        validate_environment()
        logger.info("Environment validation passed")
    except EnvironmentError as e:
        logger.error(f"Environment validation failed: {str(e)}")
        # Continue startup but log the issue - some services may work without all configs
        logger.warning(
            "Starting with incomplete configuration - some features may not work"
        )

    # Initialize database
    try:
        logger.info("Initializing database...")
        await init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        # Continue - the app might work with existing database

    # Initialize components
    try:
        document_injector = UnifiedDocumentInjector(enable_cost_tracking=True)
        vector_store = QdrantVectorStore()  # Default instance for legacy endpoints
        embedding_generator = EmbeddingGenerator()

        # Test connections
        if not document_injector.box_client.check_connection():
            logger.warning(
                "Box API connection failed - document processing will be limited"
            )

        logger.info("Clerk API service started successfully")

    except Exception as e:
        logger.error(f"Failed to initialize Clerk API: {str(e)}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down Clerk API service...")
    
    # Stop temp file cleanup
    await shutdown_cleanup()
    
    # Shutdown rate limiters
    from src.middleware.rate_limiter import shutdown_rate_limiters
    await shutdown_rate_limiters()
    
    if vector_store:
        vector_store.close()

    # Close database connections
    await close_db()


# Create FastAPI app
app = FastAPI(
    title="Clerk Legal AI API",
    description="API for legal document processing and search",
    version="1.0.0",
    lifespan=lifespan,
)

# Mount WebSocket app
app.mount("/ws", socket_app)

# Configure CORS
cors_origins = os.getenv(
    "CORS_ORIGINS", "http://localhost:3000,http://localhost:8010"
).split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add Authentication Middleware
# MVP MODE: Auth middleware is commented out - RESTORE FOR PRODUCTION
# from src.middleware.auth_middleware import AuthMiddleware

# MVP MODE: Using MockUserMiddleware instead of AuthMiddleware
# To restore auth: Comment out MockUserMiddleware and uncomment AuthMiddleware
# app.add_middleware(AuthMiddleware)
app.add_middleware(MockUserMiddleware)

# Add Case Context Middleware (must be after auth)
app.add_middleware(CaseContextMiddleware)

# Include routers
app.include_router(auth_router)
app.include_router(case_router)
app.include_router(discovery_router)
app.include_router(agent_router)
app.include_router(deficiency_router)
app.include_router(good_faith_letter_router)


# Pydantic models for API
class ProcessFolderRequest(BaseModel):
    folder_id: str = Field(..., description="Box folder ID to process")
    max_documents: Optional[int] = Field(
        None, description="Maximum number of documents to process"
    )


class SearchRequest(BaseModel):
    case_name: Optional[str] = Field(
        None,
        description="Case name to search within (deprecated, use X-Case-ID header)",
    )
    query: str = Field(..., description="Search query")
    limit: int = Field(10, ge=1, le=50, description="Maximum results to return")
    use_hybrid: bool = Field(True, description="Use hybrid search")
    document_types: Optional[List[str]] = Field(
        None, description="Filter by document types (e.g., 'motion', 'deposition')"
    )


class HybridSearchRequest(BaseModel):
    query: str = Field(..., description="Search query")
    database_name: str = Field(
        ..., description="Database name for case-specific collection"
    )
    limit: int = Field(default=20, description="Number of results for RRF fusion")
    final_limit: int = Field(default=4, description="Final number of results to return")
    enable_reranking: bool = Field(default=True, description="Enable Cohere reranking")


class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    services: Dict[str, str]


class ProcessingStatus(BaseModel):
    status: str
    message: str
    details: Optional[Dict[str, Any]] = None


class UploadResponse(BaseModel):
    status: str
    message: str
    file_id: Optional[str] = None
    file_name: Optional[str] = None
    web_link: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


# Add this model for cached requests
class CachedMotionDraftingRequest(BaseModel):
    outline_id: str  # ID of cached outline
    database_name: str
    target_length: str = "MEDIUM"
    motion_title: Optional[str] = None
    opposing_motion_text: Optional[str] = None
    export_format: str = "json"
    upload_to_box: bool = False
    box_folder_id: Optional[str] = None


# Motion drafting models
class MotionDraftingRequest(BaseModel):
    """Enhanced request model for motion drafting"""

    outline: Dict[str, Any] = Field(
        ..., description="Structured outline from doc-converter"
    )
    database_name: str = Field(
        ..., description="Name of the Qdrant database/collection"
    )
    target_length: str = Field(
        "MEDIUM", description="Target length: SHORT, MEDIUM, LONG, COMPREHENSIVE"
    )
    motion_title: Optional[str] = Field(
        None, description="Optional title for the motion"
    )
    export_format: str = Field("docx", description="Export format: docx, json, or both")
    upload_to_box: bool = Field(False, description="Whether to upload to Box")
    box_folder_id: Optional[str] = Field(None, description="Box folder ID for upload")
    opposing_motion_text: Optional[str] = Field(
        None, description="Raw text of the opposing motion to respond to"
    )  # NEW FIELD


class MotionDraftingResponse(BaseModel):
    status: str
    message: str
    draft_id: str
    title: str
    total_pages: int
    total_words: int
    quality_score: float
    export_links: Dict[str, str] = Field(default_factory=dict)
    box_file_id: Optional[str] = None
    box_web_link: Optional[str] = None
    review_notes: List[str] = Field(default_factory=list)
    quality_metrics: Dict[str, float] = Field(default_factory=dict)
    processing_time_seconds: Optional[float] = None
    outline_id: Optional[str] = None


# Debug endpoint to check settings
@app.get("/debug/settings")
async def debug_settings():
    """Debug endpoint to check current settings"""
    return {
        "auth_enabled": settings.auth.auth_enabled,
        "environment": settings.environment,
        "is_development": settings.is_development,
        "dev_mock_token": settings.auth.dev_mock_token[:10] + "..."
        if settings.auth.dev_mock_token
        else None,
    }


# Health check endpoint
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Check health status of the Clerk API and its dependencies"""
    services = {}

    # Check Qdrant
    try:
        vector_store.client.get_collections()
        services["qdrant"] = "healthy"
    except Exception as e:
        logger.error(f"Qdrant health check failed: {str(e)}")
        services["qdrant"] = "unhealthy"

    # Check Box (if initialized)
    try:
        if document_injector and document_injector.box_client.check_connection():
            services["box"] = "healthy"
        else:
            services["box"] = "not configured"
    except Exception as e:
        logger.error(f"Box health check failed: {str(e)}")
        services["box"] = "unhealthy"

    # Check OpenAI
    now = datetime.now()
    if not embedding_generator:
        services["openai"] = "not configured"
    elif _openai_health_cache["last_check"] is None or now - _openai_health_cache[
        "last_check"
    ] > timedelta(seconds=HEALTH_CACHE_DURATION):
        try:
            test_embedding, _ = embedding_generator.generate_embedding("test")
            _openai_health_cache["status"] = "healthy"
        except Exception as e:
            logger.error(f"OpenAI health check failed: {str(e)}")
            _openai_health_cache["status"] = "unhealthy"
        _openai_health_cache["last_check"] = now

    services["openai"] = _openai_health_cache.get("status", "unknown")

    overall_status = (
        "healthy"
        if all(s in ["healthy", "not configured"] for s in services.values())
        else "degraded"
    )

    return HealthResponse(status=overall_status, timestamp=now, services=services)


# WebSocket status endpoint
@app.get("/websocket/status")
async def websocket_status():
    """Get WebSocket connection status"""
    from src.websocket import get_active_connections

    return {
        "status": "active",
        "connections": get_active_connections(),
        "endpoint": "/ws/socket.io",
        "test_url": "ws://localhost:8000/ws",
    }


# Test WebSocket endpoint
@app.get("/websocket/test")
async def websocket_test():
    """Test WebSocket functionality"""
    from src.websocket import sio

    try:
        # Emit a test event to all connected clients
        await sio.emit(
            "test_broadcast",
            {
                "message": "Test broadcast from server",
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

        from src.websocket import get_active_connections
        
        return {
            "status": "success",
            "message": "Test event broadcast to all connected clients",
            "connected_clients": get_active_connections(),
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


# Document processing endpoint
@app.post("/process/folder", response_model=ProcessingStatus)
async def process_folder(
    request: ProcessFolderRequest, background_tasks: BackgroundTasks
):
    """Process documents from a Box folder"""
    if not document_injector:
        raise HTTPException(status_code=503, detail="Document processing not available")

    # Run processing in background
    background_tasks.add_task(
        document_injector.process_case_folder, request.folder_id, request.max_documents
    )

    return ProcessingStatus(
        status="processing",
        message=f"Started processing folder {request.folder_id}",
        details={
            "folder_id": request.folder_id,
            "max_documents": request.max_documents,
        },
    )


# Discovery processing endpoint
@app.post("/process/discovery", response_model=ProcessingStatus)
async def process_discovery(
    request: DiscoveryProcessingRequest, background_tasks: BackgroundTasks
):
    """Process discovery materials with enhanced fact extraction

    All documents in the specified folder are treated as verified discovery materials.
    Fact extraction is forced regardless of document type.
    """
    if not document_injector:
        raise HTTPException(status_code=503, detail="Document processing not available")

    # Prepare discovery metadata
    discovery_metadata = {
        "production_batch": request.production_batch,
        "production_date": request.production_date.isoformat()
        if request.production_date
        else datetime.now().isoformat(),
        "producing_party": request.producing_party,
        "responsive_to_requests": request.responsive_to_requests,
        "confidentiality_designation": request.confidentiality_designation,
    }

    # Run processing in background
    background_tasks.add_task(
        document_injector.process_discovery_folder,
        request.folder_id,
        request.case_name,
        discovery_metadata,
    )

    return ProcessingStatus(
        status="processing",
        message=f"Started processing discovery folder {request.folder_id} for {request.case_name}",
        details={
            "folder_id": request.folder_id,
            "case_name": request.case_name,
            "production_batch": request.production_batch,
            "producing_party": request.producing_party,
            "responsive_to_requests": request.responsive_to_requests,
        },
    )


# WebSocket-enabled discovery processing endpoint
@app.post("/discovery/process", response_model=Dict[str, Any])
async def process_discovery_websocket(
    request: DiscoveryProcessingRequest, background_tasks: BackgroundTasks
):
    """
    Process discovery materials with real-time WebSocket updates

    This endpoint processes discovery documents and emits real-time progress updates
    via WebSocket events. Connect to the WebSocket endpoint at /ws/socket.io to receive updates.
    """
    try:
        # Get the WebSocket-enabled processor
        ws_processor = get_websocket_processor()

        # Start processing in the background
        background_tasks.add_task(ws_processor.process_discovery_with_updates, request)

        # Return immediately with processing ID
        processing_id = str(uuid.uuid4())
        return {
            "processing_id": processing_id,
            "status": "started",
            "message": f"Discovery processing started for {request.case_name}",
            "websocket_url": "/ws/socket.io",
        }

    except Exception as e:
        logger.error(f"Failed to start discovery processing: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Mock discovery processing endpoint for frontend testing
@app.post("/discovery/process/mock", response_model=Dict[str, Any])
async def process_discovery_mock(
    request: DiscoveryProcessingRequest, background_tasks: BackgroundTasks
):
    """Mock endpoint for testing frontend WebSocket integration"""

    processing_id = str(uuid.uuid4())

    # Import mock processing function
    from mock_discovery_endpoint import mock_process_discovery

    # Run mock processing in background
    background_tasks.add_task(mock_process_discovery, processing_id, request.case_name)

    return {
        "processing_id": processing_id,
        "status": "started",
        "message": f"Mock discovery processing started for {request.case_name}",
        "websocket_url": "/ws/socket.io",
    }


# Search endpoint
@app.post("/search")
async def search_documents(
    request: SearchRequest, case_context=Depends(get_case_context)
):
    """Search for documents within a case"""
    try:
        # Use case from context if available, otherwise fall back to request
        case_name = case_context.case_name if case_context else request.case_name
        if not case_name:
            raise HTTPException(status_code=400, detail="Case context required")

        # Generate embedding for query
        query_embedding, _ = embedding_generator.generate_embedding(request.query)

        # Perform search
        if request.use_hybrid and hasattr(document_injector, "search_case"):
            results = document_injector.search_case(
                case_name, request.query, request.limit, request.use_hybrid
            )
        else:
            results = vector_store.search_documents(
                request.case_name, query_embedding, request.limit
            )

        # Format results
        formatted_results = []
        for result in results:
            formatted_results.append(
                {
                    "id": result.id,
                    "content": result.content,
                    "score": result.score,
                    "metadata": result.metadata,
                }
            )

        return {
            "query": request.query,
            "case_name": request.case_name,
            "results": formatted_results,
            "count": len(formatted_results),
        }

    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


# Unified document search endpoint
@app.post("/search/documents")
async def search_unified_documents(request: SearchRequest):
    """Search for documents using the unified document management system"""
    try:
        # Use the unified search from document injector
        results = document_injector.search_documents(
            case_name=request.case_name,
            query=request.query,
            document_types=request.document_types
            if hasattr(request, "document_types")
            else None,
            limit=request.limit,
        )

        return {
            "query": request.query,
            "case_name": request.case_name,
            "results": results,
            "count": len(results),
        }

    except Exception as e:
        logger.error(f"Unified search error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


# Legacy endpoint for backward compatibility
@app.get("/cases")
async def list_cases_legacy():
    """List all available cases (legacy endpoint for compatibility)"""
    try:
        # Fall back to vector store listing
        cases_data = vector_store.list_cases()
        case_names = [
            case.get("collection_name", case.get("original_name", ""))
            for case in cases_data
            if case.get("collection_name") or case.get("original_name")
        ]
        return {"cases": case_names}
    except Exception as e:
        logger.error(f"Error listing cases: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list cases: {str(e)}")


# Hybrid search endpoint for n8n integration
@app.post("/hybrid-search")
async def hybrid_search_endpoint(request: HybridSearchRequest):
    """Hybrid search endpoint for n8n workflow integration

    Performs semantic + keyword + citation search with RRF fusion and Cohere reranking.
    Now includes detailed ranking history for each result.
    """
    try:
        # Initialize vector store (database_name is used as collection name in hybrid search)
        case_vector_store = QdrantVectorStore()

        # Generate query embedding - properly unpack the tuple
        query_embedding, token_count = embedding_generator.generate_embedding(
            request.query
        )

        # Perform hybrid search with RRF and reranking
        results = await case_vector_store.hybrid_search(
            collection_name=request.database_name,  # Use database_name as collection name
            query=request.query,
            query_embedding=query_embedding,  # Now passing just the embedding vector
            limit=request.limit,
            final_limit=request.final_limit,
            enable_reranking=request.enable_reranking,
        )

        # Format results for n8n consumption with ranking history
        formatted_results = []
        for result in results:
            formatted_results.append(
                {
                    "id": result.id,
                    "content": result.content,
                    "score": result.score,
                    "search_type": result.search_type,
                    "document_id": result.document_id,
                    "case_name": result.case_name,
                    "metadata": result.metadata,
                    # Add ranking history
                    "ranking_journey": {
                        "semantic_rank": result.ranking_history.get("semantic_rank"),
                        "keyword_rank": result.ranking_history.get("keyword_rank"),
                        "citation_rank": result.ranking_history.get("citation_rank"),
                        "rrf_rank": result.ranking_history.get("rrf_rank"),
                        "final_rank": result.ranking_history.get("final_rank"),
                    },
                    # Add score history
                    "score_journey": {
                        "semantic_score": result.score_history.get("semantic_score"),
                        "keyword_score": result.score_history.get("keyword_score"),
                        "citation_score": result.score_history.get("citation_score"),
                        "rrf_score": result.score_history.get("rrf_score"),
                        "cohere_score": result.score_history.get("cohere_score"),
                    },
                }
            )

        # Calculate ranking statistics for the response
        ranking_stats = calculate_ranking_statistics(formatted_results)

        return {
            "query": request.query,
            "database_name": request.database_name,
            "results": formatted_results,
            "count": len(formatted_results),
            "search_pipeline": {
                "semantic_search": True,
                "keyword_search": True,
                "citation_search": True,
                "rrf_fusion": True,
                "cohere_reranking": request.enable_reranking,
            },
            "ranking_statistics": ranking_stats,
        }

    except Exception as e:
        logger.error(f"Hybrid search error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Hybrid search failed: {str(e)}")


def calculate_ranking_statistics(results: List[Dict]) -> Dict[str, Any]:
    """Calculate statistics about ranking changes through the pipeline"""

    stats = {
        "average_rank_changes": {},
        "ranking_improvements": {},
        "cohere_impact": None,
    }

    if not results:
        return stats

    # Calculate average rank changes
    semantic_to_rrf = []
    rrf_to_final = []
    semantic_to_final = []

    for result in results:
        journey = result["ranking_journey"]

        # Semantic to RRF change
        if journey.get("semantic_rank") and journey.get("rrf_rank"):
            change = journey["semantic_rank"] - journey["rrf_rank"]
            semantic_to_rrf.append(change)

        # RRF to final change
        if journey.get("rrf_rank") and journey.get("final_rank"):
            change = journey["rrf_rank"] - journey["final_rank"]
            rrf_to_final.append(change)

        # Semantic to final change
        if journey.get("semantic_rank") and journey.get("final_rank"):
            change = journey["semantic_rank"] - journey["final_rank"]
            semantic_to_final.append(change)

    # Calculate averages
    if semantic_to_rrf:
        stats["average_rank_changes"]["semantic_to_rrf"] = sum(semantic_to_rrf) / len(
            semantic_to_rrf
        )
    if rrf_to_final:
        stats["average_rank_changes"]["rrf_to_final"] = sum(rrf_to_final) / len(
            rrf_to_final
        )
    if semantic_to_final:
        stats["average_rank_changes"]["semantic_to_final"] = sum(
            semantic_to_final
        ) / len(semantic_to_final)

    # Calculate how many results improved their ranking
    stats["ranking_improvements"]["improved_by_rrf"] = sum(
        1 for x in semantic_to_rrf if x > 0
    )
    stats["ranking_improvements"]["improved_by_reranking"] = sum(
        1 for x in rrf_to_final if x > 0
    )
    stats["ranking_improvements"]["improved_overall"] = sum(
        1 for x in semantic_to_final if x > 0
    )

    # Analyze Cohere impact if available
    cohere_scores = [
        r["score_journey"].get("cohere_score")
        for r in results
        if r["score_journey"].get("cohere_score") is not None
    ]
    if cohere_scores:
        stats["cohere_impact"] = {
            "average_confidence": sum(cohere_scores) / len(cohere_scores),
            "min_confidence": min(cohere_scores),
            "max_confidence": max(cohere_scores),
            "results_reranked": len(cohere_scores),
        }

    return stats


# AI query endpoint (using the legal document agent)
@app.post("/ai/query")
async def ai_query(case_name: str, query: str, user_id: str = "api_user"):
    """Query documents using AI agent"""
    try:
        response = await legal_document_agent.query_documents(
            user_query=query, user_id=user_id
        )

        return {
            "query": query,
            "answer": response.answer,
            "confidence": response.confidence,
            "sources": [
                {
                    "document_name": source.document_name,
                    "excerpt": source.excerpt,
                    "relevance_score": source.relevance_score,
                }
                for source in response.sources
            ],
            "disclaimers": response.legal_disclaimers,
            "follow_ups": response.suggested_follow_ups,
        }

    except Exception as e:
        logger.error(f"AI query error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"AI query failed: {str(e)}")


@app.post("/upload/file", response_model=UploadResponse)
async def upload_file_to_box(
    file: UploadFile = File(...),
    folder_id: str = Form(...),
    description: Optional[str] = Form(None),
):
    """Upload a file to a specific Box folder

    Args:
        file: The file to upload
        folder_id: Box folder ID where the file should be uploaded
        description: Optional description for the file

    Returns:
        UploadResponse with file details
    """
    if not document_injector or not document_injector.box_client:
        raise HTTPException(status_code=503, detail="Box service not available")

    try:
        # Read the file content
        file_content = await file.read()
        file_stream = io.BytesIO(file_content)

        # Upload to Box
        uploaded_file = document_injector.box_client.upload_file(
            file_stream=file_stream,
            file_name=file.filename,
            parent_folder_id=folder_id,
            description=description,
        )

        # Get the web link for the file
        web_link = None
        try:
            file_info = document_injector.box_client.client.file(uploaded_file.id).get()
            if hasattr(file_info, "shared_link") and file_info.shared_link:
                web_link = file_info.shared_link.get("url")
        except Exception as e:
            logger.warning(f"Could not retrieve web link for uploaded file: {str(e)}")

        return UploadResponse(
            status="success",
            message="File uploaded successfully to Box",
            file_id=uploaded_file.id,
            file_name=uploaded_file.name,
            web_link=web_link,
            details={
                "size": len(file_content),
                "folder_id": folder_id,
                "content_type": file.content_type,
            },
        )

    except Exception as e:
        logger.error(f"Error uploading file to Box: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@app.post("/generate-and-upload-outline")
async def generate_and_upload_outline(
    background_tasks: BackgroundTasks,
    motion_text: str = Form(...),
    counter_arguments: str = Form(...),
    folder_id: str = Form("327679822937"),
    reasoning_effort: str = Form("high"),
):
    """Generate legal outline and upload directly to Box"""

    # Validate inputs
    if not motion_text or not counter_arguments:
        raise HTTPException(
            status_code=400, detail="Motion text and counter arguments are required"
        )

    # Call outline drafter service
    outline_drafter_url = os.getenv(
        "OUTLINE_DRAFTER_URL", "http://outline-drafter:8000"
    )

    timeout = aiohttp.ClientTimeout(total=600)  # 10 minute timeout for o3 model

    async with aiohttp.ClientSession(timeout=timeout) as session:
        try:
            logger.info(f"Calling outline drafter service at {outline_drafter_url}")

            # Generate outline with Box upload
            async with session.post(
                f"{outline_drafter_url}/generate-outline-docx",
                json={
                    "motion_text": motion_text,
                    "counter_arguments": counter_arguments,
                    "reasoning_effort": reasoning_effort,
                    "upload_to_box": True,
                    "box_folder_id": folder_id,
                },
            ) as response:
                logger.info(f"Outline drafter response status: {response.status}")

                if response.status == 200:
                    # Get DOCX content
                    docx_bytes = await response.read()

                    # Get metadata from header
                    metadata_str = response.headers.get("X-Metadata", "{}")
                    try:
                        metadata = json.loads(metadata_str)
                    except json.JSONDecodeError:
                        metadata = {}

                    # Check if Box upload was successful
                    box_upload = metadata.get("box_upload", {})

                    if box_upload.get("file_id"):
                        return {
                            "status": "success",
                            "message": "Outline generated and uploaded to Box",
                            "box_file_id": box_upload.get("file_id"),
                            "box_web_link": box_upload.get("web_link"),
                            "folder_id": box_upload.get("folder_id", folder_id),
                            "generation_metadata": metadata,
                        }
                    else:
                        # Box upload might have failed, but we have the DOCX
                        # Try to upload it ourselves
                        logger.warning(
                            "Box upload not found in metadata, attempting direct upload"
                        )

                        # Upload the DOCX we received
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = f"legal_outline_{timestamp}.docx"

                        file_stream = io.BytesIO(docx_bytes)
                        uploaded_file = document_injector.box_client.upload_file(
                            file_stream=file_stream,
                            file_name=filename,
                            parent_folder_id=folder_id,
                            description=f"Legal outline generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                        )

                        return {
                            "status": "success",
                            "message": "Outline generated and uploaded to Box",
                            "box_file_id": uploaded_file.id,
                            "box_web_link": f"https://app.box.com/file/{uploaded_file.id}",
                            "folder_id": folder_id,
                            "generation_metadata": metadata,
                        }
                else:
                    # Try to get error details
                    try:
                        error_data = await response.json()
                        error_msg = error_data.get(
                            "error", error_data.get("detail", "Unknown error")
                        )
                    except Exception:
                        error_msg = await response.text()

                    logger.error(f"Outline drafter error: {error_msg}")
                    raise HTTPException(
                        status_code=response.status,
                        detail=f"Outline generation failed: {error_msg}",
                    )

        except asyncio.TimeoutError:
            logger.error("Outline generation timed out")
            raise HTTPException(status_code=504, detail="Outline generation timed out")
        except aiohttp.ClientError as e:
            logger.error(f"HTTP client error: {e}")
            raise HTTPException(
                status_code=502, detail=f"Error connecting to outline service: {str(e)}"
            )
        except HTTPException:
            raise  # Re-raise HTTP exceptions
        except Exception as e:
            logger.error(
                f"Unexpected error in generate and upload workflow: {e}", exc_info=True
            )
            raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


# Motion drafting endpoint
@app.post("/draft-motion", response_model=MotionDraftingResponse)
async def draft_motion(request: MotionDraftingRequest):
    """
    Draft a complete legal motion from an outline
    """
    start_time = datetime.utcnow()
    
    try:
        logger.info(f"Starting motion draft for database: {request.database_name}")

        # Preprocess the outline to prevent issues
        outline_data = request.outline

        # Log the structure
        logger.info(f"Received outline type: {type(outline_data)}")
        if isinstance(outline_data, dict):
            logger.info(f"Outline keys: {list(outline_data.keys())}")

        # Ensure we have a properly structured outline
        if isinstance(outline_data, list):
            # If it's a list, take the first element
            outline_data = outline_data[0] if outline_data else {}

        # Clean extremely long content that might cause issues
        def clean_field_value(value):
            if isinstance(value, str) and len(value) > 1000:
                # For very long content with options, just take the first option
                if "||" in value:
                    value = value.split("||")[0].strip()
                return value[:1000] + "..."
            return value

        # Recursively clean the outline
        def clean_outline(obj):
            if isinstance(obj, dict):
                return {k: clean_outline(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [clean_outline(item) for item in obj]
            elif isinstance(obj, str):
                return clean_field_value(obj)
            return obj

        # Apply the cleaning function to the outline data
        cleaned_outline = clean_outline(outline_data)

        if isinstance(cleaned_outline, dict) and "sections" in cleaned_outline:
            for i, section in enumerate(
                cleaned_outline["sections"][:2]
            ):  # Log first 2 sections
                logger.info(
                    f"Section {i} content items: {len(section.get('content', []))}"
                )
                if "content" in section and section["content"]:
                    first_item = section["content"][0]
                    logger.info(
                        f"First content item type: {first_item.get('type', 'unknown')}"
                    )
                    if first_item.get("type") == "field" and "value" in first_item:
                        logger.info(
                            f"First content value length: {len(first_item['value'])}"
                        )

        # Convert target_length string to DocumentLength enum
        try:
            target_length_enum = DocumentLength[request.target_length]
        except KeyError:
            logger.warning(
                f"Invalid target_length '{request.target_length}', defaulting to MEDIUM"
            )
            target_length_enum = DocumentLength.MEDIUM

        # Continue with the motion drafting...
        motion_draft = await motion_drafter.draft_motion(
            outline=cleaned_outline,
            database_name=request.database_name,
            target_length=target_length_enum,
            motion_title=request.motion_title,
            opposing_motion_text=request.opposing_motion_text,
        )

        # Generate draft ID
        draft_id = (
            f"{request.database_name}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        )

        # Prepare response
        response = MotionDraftingResponse(
            status="success",
            message=f"Motion drafted successfully: {motion_draft.total_page_estimate} pages",
            draft_id=draft_id,
            title=motion_draft.title,
            total_pages=motion_draft.total_page_estimate,
            total_words=motion_draft.total_word_count,
            quality_score=motion_draft.coherence_score,
            review_notes=motion_draft.review_notes,
            quality_metrics=motion_draft.quality_metrics,
        )

        # Handle export formats
        if request.export_format in ["docx", "both"]:
            # Export to DOCX
            with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp_file:
                docx_path = tmp_file.name
                motion_drafter.export_to_docx(motion_draft, docx_path)

                # If upload to Box requested
                if request.upload_to_box and request.box_folder_id:
                    try:
                        with open(docx_path, "rb") as f:
                            uploaded_file = document_injector.box_client.upload_file(
                                file_stream=f,
                                file_name=f"{motion_draft.title}_{draft_id}.docx",
                                parent_folder_id=request.box_folder_id,
                                description=f"AI-drafted motion created on {motion_draft.creation_timestamp}",
                            )

                        response.box_file_id = uploaded_file.id
                        response.box_web_link = (
                            f"https://app.box.com/file/{uploaded_file.id}"
                        )
                        logger.info(f"Motion uploaded to Box: {uploaded_file.id}")
                    except Exception as e:
                        logger.error(f"Failed to upload to Box: {str(e)}")
                        response.review_notes.append(f"Box upload failed: {str(e)}")

                # Store path for download link
                response.export_links["docx"] = f"/download-draft/{draft_id}/docx"

        if request.export_format in ["json", "both"]:
            # Store JSON representation
            response.export_links["json"] = f"/download-draft/{draft_id}/json"

        # Store draft data temporarily (in production, use persistent storage)
        # For now, we'll keep it in memory for a limited time
        if not hasattr(app, "draft_storage"):
            app.draft_storage = {}

        app.draft_storage[draft_id] = {
            "motion_draft": motion_draft,
            "docx_path": docx_path
            if request.export_format in ["docx", "both"]
            else None,
            "created_at": datetime.utcnow(),
        }

        return response

    except Exception as e:
        error_time = datetime.utcnow()
        total_time = error_time - start_time if "start_time" in locals() else "unknown"
        logger.error(
            f"Error drafting motion after {total_time}: {str(e)}", exc_info=True
        )

        # Log additional context for debugging
        logger.error(
            f"Request details - database: {request.database_name}, target_length: {request.target_length}"
        )
        logger.error(
            f"Outline sections count: {len(request.outline.get('sections', request.outline.get('arguments', [])))}"
        )

        raise HTTPException(status_code=500, detail=f"Motion drafting failed: {str(e)}")


@app.post("/draft-motion-cached", response_model=MotionDraftingResponse)
async def draft_motion_cached(request: MotionDraftingRequest):
    """
    Draft a motion using intelligent outline caching
    """
    start_time = datetime.utcnow()

    try:
        logger.info(
            f"Starting cached motion draft for database: {request.database_name}"
        )

        # First, cache the outline
        outline_data = request.outline

        # Handle list wrapper if present
        if isinstance(outline_data, list) and len(outline_data) > 0:
            outline_data = outline_data[0]

        # Log outline info
        logger.info(f"Outline type: {type(outline_data)}")
        logger.info(f"Outline keys: {list(outline_data.keys())}")
        sections_count = len(outline_data.get("sections", []))
        logger.info(f"Sections count: {sections_count}")

        # Cache the outline
        outline_id = await outline_cache.cache_outline(
            outline_data, request.database_name
        )
        logger.info(f"Cached outline with ID: {outline_id}")

        # Get cache stats
        cache_stats = await outline_cache.get_cache_stats()
        logger.info(f"Cache stats: {cache_stats}")

        # Convert target_length to enum
        try:
            target_length_enum = DocumentLength[request.target_length]
        except KeyError:
            logger.warning(
                f"Invalid target_length '{request.target_length}', defaulting to MEDIUM"
            )
            target_length_enum = DocumentLength.MEDIUM

        # Use the new cached drafting method
        motion_draft = await motion_drafter.draft_motion_with_cache(
            outline=outline_data,
            database_name=request.database_name,
            target_length=target_length_enum,
            motion_title=request.motion_title,
            opposing_motion_text=request.opposing_motion_text,
            outline_id=outline_id,
        )

        # Generate draft ID
        draft_id = (
            f"{request.database_name}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        )

        # Prepare response
        response = MotionDraftingResponse(
            status="success",
            message=f"Motion drafted successfully: {motion_draft.total_page_estimate} pages",
            draft_id=draft_id,
            title=motion_draft.title,
            total_pages=motion_draft.total_page_estimate,
            total_words=motion_draft.total_word_count,
            quality_score=motion_draft.coherence_score,
            review_notes=motion_draft.review_notes,
            quality_metrics=motion_draft.quality_metrics,
            outline_id=outline_id,  # Include for reference
        )

        # Handle export formats (same as before)
        if request.export_format in ["docx", "both"]:
            with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp_file:
                docx_path = tmp_file.name
                motion_drafter.export_to_docx(motion_draft, docx_path)

                if request.upload_to_box and request.box_folder_id:
                    try:
                        with open(docx_path, "rb") as f:
                            uploaded_file = document_injector.box_client.upload_file(
                                file_stream=f,
                                file_name=f"{motion_draft.title}_{draft_id}.docx",
                                parent_folder_id=request.box_folder_id,
                                description=f"AI-drafted motion created on {motion_draft.creation_timestamp}",
                            )

                        response.box_file_id = uploaded_file.id
                        response.box_web_link = (
                            f"https://app.box.com/file/{uploaded_file.id}"
                        )
                        logger.info(f"Motion uploaded to Box: {uploaded_file.id}")
                    except Exception as e:
                        logger.error(f"Failed to upload to Box: {str(e)}")
                        response.review_notes.append(f"Box upload failed: {str(e)}")

                response.export_links["docx"] = f"/download-draft/{draft_id}/docx"

        if request.export_format in ["json", "both"]:
            response.export_links["json"] = f"/download-draft/{draft_id}/json"

        # Store draft data
        if not hasattr(app, "draft_storage"):
            app.draft_storage = {}

        app.draft_storage[draft_id] = {
            "motion_draft": motion_draft,
            "docx_path": docx_path
            if request.export_format in ["docx", "both"]
            else None,
            "created_at": datetime.utcnow(),
            "outline_id": outline_id,
        }

        # Calculate duration
        duration = datetime.utcnow() - start_time
        logger.info(f"Motion drafting completed in {duration}")
        response.processing_time_seconds = duration.total_seconds()

        return response

    except Exception as e:
        error_time = datetime.utcnow()
        duration = error_time - start_time
        logger.error(f"Error drafting motion after {duration}: {str(e)}", exc_info=True)

        raise HTTPException(status_code=500, detail=f"Motion drafting failed: {str(e)}")


# Add endpoint to use already cached outline
@app.post("/draft-motion-from-cache", response_model=MotionDraftingResponse)
async def draft_motion_from_cache(request: CachedMotionDraftingRequest):
    """
    Draft a motion from an already cached outline
    """
    try:
        logger.info(f"Drafting from cached outline: {request.outline_id}")

        # Retrieve outline from cache
        outline_data = await outline_cache.get_outline(request.outline_id)
        if not outline_data:
            raise HTTPException(
                status_code=404,
                detail=f"Outline {request.outline_id} not found in cache",
            )

        # Convert target_length to enum
        try:
            target_length_enum = DocumentLength[request.target_length]
        except KeyError:
            target_length_enum = DocumentLength.MEDIUM

        # Draft using cached outline
        motion_draft = await motion_drafter.draft_motion_with_cache(
            outline=outline_data,
            database_name=request.database_name,
            target_length=target_length_enum,
            motion_title=request.motion_title,
            opposing_motion_text=request.opposing_motion_text,
            outline_id=request.outline_id,
        )

        # Rest is same as above...
        draft_id = (
            f"{request.database_name}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        )

        response = MotionDraftingResponse(
            status="success",
            message=f"Motion drafted successfully from cache: {motion_draft.total_page_estimate} pages",
            draft_id=draft_id,
            title=motion_draft.title,
            total_pages=motion_draft.total_page_estimate,
            total_words=motion_draft.total_word_count,
            quality_score=motion_draft.coherence_score,
            review_notes=motion_draft.review_notes,
            quality_metrics=motion_draft.quality_metrics,
            outline_id=request.outline_id,
        )

        return response

    except Exception as e:
        logger.error(f"Error drafting from cache: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Motion drafting failed: {str(e)}")


# Add endpoint to check outline cache status
@app.get("/outline-cache/status")
async def get_outline_cache_status():
    """Get status of the outline cache"""
    try:
        stats = await outline_cache.get_cache_stats()
        return {"status": "ok", "cache_stats": stats}
    except Exception as e:
        logger.error(f"Error getting cache status: {str(e)}")
        return {"status": "error", "error": str(e)}


# Add endpoint to get outline metadata
@app.get("/outline-cache/{outline_id}")
async def get_cached_outline_info(outline_id: str):
    """Get information about a cached outline"""
    try:
        metadata = await outline_cache.get_outline_metadata(outline_id)
        if not metadata:
            raise HTTPException(status_code=404, detail="Outline not found in cache")

        structure = await outline_cache.get_outline_structure(outline_id)

        return {"metadata": metadata, "structure": structure}
    except Exception as e:
        logger.error(f"Error getting outline info: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/download-draft/{draft_id}/{format}")
async def download_draft(draft_id: str, format: str):
    """Download a drafted motion in the specified format"""

    if not hasattr(app, "draft_storage") or draft_id not in app.draft_storage:
        raise HTTPException(status_code=404, detail="Draft not found")

    draft_data = app.draft_storage[draft_id]

    # Clean up old drafts (older than 1 hour)
    cutoff_time = datetime.utcnow() - timedelta(hours=1)
    for old_id, old_data in list(app.draft_storage.items()):
        if old_data["created_at"] < cutoff_time:
            if old_data.get("docx_path") and os.path.exists(old_data["docx_path"]):
                os.remove(old_data["docx_path"])
            del app.draft_storage[old_id]

    if format == "docx":
        if not draft_data.get("docx_path") or not os.path.exists(
            draft_data["docx_path"]
        ):
            raise HTTPException(status_code=404, detail="DOCX file not found")

        return FileResponse(
            draft_data["docx_path"],
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename=f"{draft_data['motion_draft'].title}.docx",
        )

    elif format == "json":
        # Convert motion draft to JSON
        motion_dict = {
            "title": draft_data["motion_draft"].title,
            "case_name": draft_data["motion_draft"].case_name,
            "total_pages": draft_data["motion_draft"].total_page_estimate,
            "total_words": draft_data["motion_draft"].total_word_count,
            "creation_timestamp": draft_data[
                "motion_draft"
            ].creation_timestamp.isoformat(),
            "coherence_score": draft_data["motion_draft"].coherence_score,
            "quality_metrics": draft_data["motion_draft"].quality_metrics,
            "review_notes": draft_data["motion_draft"].review_notes,
            "citation_index": draft_data["motion_draft"].citation_index,
            "sections": [],
        }

        for section in draft_data["motion_draft"].sections:
            section_dict = {
                "id": section.outline_section.id,
                "title": section.outline_section.title,
                "type": section.outline_section.section_type.value,
                "content": section.content,
                "word_count": section.word_count,
                "citations_used": section.citations_used,
                "confidence_score": section.confidence_score,
                "needs_revision": section.needs_revision,
                "revision_notes": section.revision_notes,
            }
            motion_dict["sections"].append(section_dict)

        return JSONResponse(content=motion_dict)

    else:
        raise HTTPException(
            status_code=400, detail="Invalid format. Use 'docx' or 'json'"
        )



@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Clerk Legal AI API",
        "version": "1.0.0",
        "endpoints": [
            "/health",
            "/process/folder",
            "/search",
            "/cases",
            "/ai/query",
            "/draft-motion",
            "/websocket/status",
            "/docs",
        ],
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

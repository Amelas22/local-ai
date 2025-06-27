"""
FastAPI application for Clerk Legal AI System
Provides HTTP API endpoints for document processing and search
"""

import logging
import io
import aiohttp
import asyncio
import os
import json

from typing import List, Dict, Any, Optional, BinaryIO
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, File, UploadFile, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from src.document_injector import DocumentInjector
from src.vector_storage.qdrant_store import QdrantVectorStore
from src.vector_storage.embeddings import EmbeddingGenerator
from src.ai_agents.legal_document_agent import legal_document_agent
from src.utils.logger import setup_logging
from config.settings import settings

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
    
    # Validate settings
    if not settings.validate():
        logger.error("Invalid configuration. Please check environment variables.")
        raise RuntimeError("Invalid configuration")
    
    # Initialize components
    try:
        document_injector = DocumentInjector(enable_cost_tracking=True)
        vector_store = QdrantVectorStore()  # Default instance for legacy endpoints
        embedding_generator = EmbeddingGenerator()
        
        # Test connections
        if not document_injector.box_client.check_connection():
            logger.warning("Box API connection failed - document processing will be limited")
        
        logger.info("Clerk API service started successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize Clerk API: {str(e)}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Clerk API service...")
    if vector_store:
        vector_store.close()

# Create FastAPI app
app = FastAPI(
    title="Clerk Legal AI API",
    description="API for legal document processing and search",
    version="1.0.0",
    lifespan=lifespan
)

# Pydantic models for API
class ProcessFolderRequest(BaseModel):
    folder_id: str = Field(..., description="Box folder ID to process")
    max_documents: Optional[int] = Field(None, description="Maximum number of documents to process")

class SearchRequest(BaseModel):
    case_name: str = Field(..., description="Case name to search within")
    query: str = Field(..., description="Search query")
    limit: int = Field(10, ge=1, le=50, description="Maximum results to return")
    use_hybrid: bool = Field(True, description="Use hybrid search")

class HybridSearchRequest(BaseModel):
    query: str = Field(..., description="Search query")
    database_name: str = Field(..., description="Database name for case-specific collection")
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

# Health check endpoint
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Check health status of the Clerk API and its dependencies"""
    services = {}
    
    # Check Qdrant
    try:
        vector_store.client.get_collections()
        services["qdrant"] = "healthy"
    except:
        services["qdrant"] = "unhealthy"
    
    # Check Box (if initialized)
    try:
        if document_injector and document_injector.box_client.check_connection():
            services["box"] = "healthy"
        else:
            services["box"] = "not configured"
    except:
        services["box"] = "unhealthy"
    
    # Check OpenAI
    now = datetime.now()
    if not embedding_generator:
        services["openai"] = "not configured"
    elif (_openai_health_cache["last_check"] is None or 
          now - _openai_health_cache["last_check"] > timedelta(seconds=HEALTH_CACHE_DURATION)):
        
        try:
            test_embedding, _ = embedding_generator.generate_embedding("test")
            _openai_health_cache["status"] = "healthy"
        except:
            _openai_health_cache["status"] = "unhealthy"
        _openai_health_cache["last_check"] = now
    
    services["openai"] = _openai_health_cache.get("status", "unknown")
    
    overall_status = "healthy" if all(s in ["healthy", "not configured"] for s in services.values()) else "degraded"
    
    return HealthResponse(
        status=overall_status,
        timestamp=now,
        services=services
    )

# Document processing endpoint
@app.post("/process/folder", response_model=ProcessingStatus)
async def process_folder(request: ProcessFolderRequest, background_tasks: BackgroundTasks):
    """Process documents from a Box folder"""
    if not document_injector:
        raise HTTPException(status_code=503, detail="Document processing not available")
    
    # Run processing in background
    background_tasks.add_task(
        document_injector.process_case_folder,
        request.folder_id,
        request.max_documents
    )
    
    return ProcessingStatus(
        status="processing",
        message=f"Started processing folder {request.folder_id}",
        details={"folder_id": request.folder_id, "max_documents": request.max_documents}
    )

# Search endpoint
@app.post("/search")
async def search_documents(request: SearchRequest):
    """Search for documents within a case"""
    try:
        # Generate embedding for query
        query_embedding, _ = embedding_generator.generate_embedding(request.query)
        
        # Perform search
        if request.use_hybrid and hasattr(document_injector, 'search_case'):
            results = document_injector.search_case(
                request.case_name,
                request.query,
                request.limit,
                request.use_hybrid
            )
        else:
            results = vector_store.search_documents(
                request.case_name,
                query_embedding,
                request.limit
            )
        
        # Format results
        formatted_results = []
        for result in results:
            formatted_results.append({
                "id": result.id,
                "content": result.content,
                "score": result.score,
                "metadata": result.metadata
            })
        
        return {
            "query": request.query,
            "case_name": request.case_name,
            "results": formatted_results,
            "count": len(formatted_results)
        }
        
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

# Case listing endpoint
@app.get("/cases")
async def list_cases():
    """List all available cases"""
    try:
        cases = vector_store.list_cases()
        return {"cases": cases}
    except Exception as e:
        logger.error(f"Error listing cases: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list cases: {str(e)}")

# Hybrid search endpoint for n8n integration
@app.post("/hybrid-search")
async def hybrid_search_endpoint(request: HybridSearchRequest):
    """Hybrid search endpoint for n8n workflow integration
    
    Performs semantic + keyword + citation search with RRF fusion and Cohere reranking
    """
    try:
        # Initialize vector store (database_name is used as collection name in hybrid search)
        case_vector_store = QdrantVectorStore()
        
        # Generate query embedding
        query_embedding = embedding_generator.generate_embedding(request.query)
        
        # Perform hybrid search with RRF and reranking
        results = await case_vector_store.hybrid_search(
            collection_name=request.database_name,  # Use database_name as collection name
            query=request.query,
            query_embedding=query_embedding,
            limit=request.limit,
            final_limit=request.final_limit,
            enable_reranking=request.enable_reranking
        )
        
        # Format results for n8n consumption
        formatted_results = []
        for result in results:
            formatted_results.append({
                "id": result.id,
                "content": result.content,
                "score": result.score,
                "search_type": result.search_type,
                "document_id": result.document_id,
                "case_name": result.case_name,
                "metadata": result.metadata
            })
        
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
                "cohere_reranking": request.enable_reranking
            }
        }
        
    except Exception as e:
        logger.error(f"Hybrid search error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Hybrid search failed: {str(e)}")

# AI query endpoint (using the legal document agent)
@app.post("/ai/query")
async def ai_query(case_name: str, query: str, user_id: str = "api_user"):
    """Query documents using AI agent"""
    try:
        response = await legal_document_agent.query_documents(
            user_query=query,
            user_id=user_id
        )
        
        return {
            "query": query,
            "answer": response.answer,
            "confidence": response.confidence,
            "sources": [
                {
                    "document_name": source.document_name,
                    "excerpt": source.excerpt,
                    "relevance_score": source.relevance_score
                }
                for source in response.sources
            ],
            "disclaimers": response.legal_disclaimers,
            "follow_ups": response.suggested_follow_ups
        }
        
    except Exception as e:
        logger.error(f"AI query error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"AI query failed: {str(e)}")

@app.post("/upload/file", response_model=UploadResponse)
async def upload_file_to_box(
    file: UploadFile = File(...),
    folder_id: str = Form(...),
    description: Optional[str] = Form(None)
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
            description=description
        )
        
        # Get the web link for the file
        web_link = None
        try:
            file_info = document_injector.box_client.client.file(uploaded_file.id).get()
            if hasattr(file_info, 'shared_link') and file_info.shared_link:
                web_link = file_info.shared_link.get('url')
        except:
            logger.warning("Could not retrieve web link for uploaded file")
        
        return UploadResponse(
            status="success",
            message=f"File uploaded successfully to Box",
            file_id=uploaded_file.id,
            file_name=uploaded_file.name,
            web_link=web_link,
            details={
                "size": len(file_content),
                "folder_id": folder_id,
                "content_type": file.content_type
            }
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
    reasoning_effort: str = Form("high")
):
    """Generate legal outline and upload directly to Box"""
    
    # Validate inputs
    if not motion_text or not counter_arguments:
        raise HTTPException(status_code=400, detail="Motion text and counter arguments are required")
    
    # Call outline drafter service
    outline_drafter_url = os.getenv("OUTLINE_DRAFTER_URL", "http://outline-drafter:8000")
    
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
                    "box_folder_id": folder_id
                }
            ) as response:
                logger.info(f"Outline drafter response status: {response.status}")
                
                if response.status == 200:
                    # Get DOCX content
                    docx_bytes = await response.read()
                    
                    # Get metadata from header
                    metadata_str = response.headers.get('X-Metadata', '{}')
                    try:
                        metadata = json.loads(metadata_str)
                    except:
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
                            "generation_metadata": metadata
                        }
                    else:
                        # Box upload might have failed, but we have the DOCX
                        # Try to upload it ourselves
                        logger.warning("Box upload not found in metadata, attempting direct upload")
                        
                        # Upload the DOCX we received
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = f"legal_outline_{timestamp}.docx"
                        
                        file_stream = io.BytesIO(docx_bytes)
                        uploaded_file = document_injector.box_client.upload_file(
                            file_stream=file_stream,
                            file_name=filename,
                            parent_folder_id=folder_id,
                            description=f"Legal outline generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                        )
                        
                        return {
                            "status": "success",
                            "message": "Outline generated and uploaded to Box",
                            "box_file_id": uploaded_file.id,
                            "box_web_link": f"https://app.box.com/file/{uploaded_file.id}",
                            "folder_id": folder_id,
                            "generation_metadata": metadata
                        }
                else:
                    # Try to get error details
                    try:
                        error_data = await response.json()
                        error_msg = error_data.get("error", error_data.get("detail", "Unknown error"))
                    except:
                        error_msg = await response.text()
                    
                    logger.error(f"Outline drafter error: {error_msg}")
                    raise HTTPException(status_code=response.status, detail=f"Outline generation failed: {error_msg}")
                    
        except asyncio.TimeoutError:
            logger.error("Outline generation timed out")
            raise HTTPException(status_code=504, detail="Outline generation timed out")
        except aiohttp.ClientError as e:
            logger.error(f"HTTP client error: {e}")
            raise HTTPException(status_code=502, detail=f"Error connecting to outline service: {str(e)}")
        except HTTPException:
            raise  # Re-raise HTTP exceptions
        except Exception as e:
            logger.error(f"Unexpected error in generate and upload workflow: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

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
            "/docs"
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
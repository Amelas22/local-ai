"""
FastAPI application for Clerk Legal AI System
Provides HTTP API endpoints for document processing and search
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
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
        vector_store = QdrantVectorStore()
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

class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    services: Dict[str, str]

class ProcessingStatus(BaseModel):
    status: str
    message: str
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
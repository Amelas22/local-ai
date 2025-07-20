"""
FastAPI endpoints for BMad agent commands.

Provides REST API access to agent functionality with case isolation,
WebSocket progress tracking, and comprehensive error handling.
"""

from typing import Optional, Dict, Any, List
from uuid import uuid4
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, Query, status, Request
from fastapi.responses import Response
from pydantic import BaseModel, UUID4, Field, validator
from slowapi import Limiter
from slowapi.util import get_remote_address

from src.middleware.case_context import require_case_context
from src.ai_agents.bmad_framework import AgentLoader, AgentExecutor
from src.ai_agents.bmad_framework.security import get_agent_security_context
from src.ai_agents.bmad_framework.websocket_progress import track_progress
from src.ai_agents.bmad_framework.exceptions import (
    AgentLoadError,
)
from src.utils.logger import get_logger

logger = get_logger("clerk_api")

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# Create router
router = APIRouter(prefix="/api/agents", tags=["agents"])


# Request/Response Models
class AnalyzeRequest(BaseModel):
    """Request model for deficiency analysis."""

    production_id: UUID4 = Field(..., description="Production document batch ID")
    rtp_document_id: UUID4 = Field(..., description="RTP document ID")
    oc_response_id: Optional[UUID4] = Field(None, description="OC response document ID")
    options: Optional[Dict[str, Any]] = Field(default_factory=dict)

    @validator("options")
    def validate_options(cls, v):
        """Validate analysis options."""
        if "confidence_threshold" in v:
            if not 0 <= v["confidence_threshold"] <= 1:
                raise ValueError("confidence_threshold must be between 0 and 1")
        return v


class AnalyzeResponse(BaseModel):
    """Response model for analysis initiation."""

    processing_id: UUID4
    websocket_channel: str
    estimated_duration_seconds: int


class SearchRequest(BaseModel):
    """Request model for document search."""

    query: str = Field(..., min_length=1, max_length=1000)
    case_name: str = Field(..., min_length=1, max_length=50)
    filters: Optional[Dict[str, Any]] = Field(default_factory=dict)
    limit: int = Field(50, ge=1, le=200)
    offset: int = Field(0, ge=0)


class SearchResult(BaseModel):
    """Individual search result."""

    document_id: UUID4
    chunk_text: str
    relevance_score: float
    metadata: Dict[str, Any]


class SearchResponse(BaseModel):
    """Response model for search results."""

    results: List[SearchResult]
    total_count: int
    has_more: bool


class CategorizeRequest(BaseModel):
    """Request model for compliance categorization."""

    request_number: str = Field(..., description="RTP request number")
    request_text: str = Field(..., description="Full RTP request text")
    search_results: List[str] = Field(..., description="Search result IDs")
    oc_response_text: Optional[str] = Field(None, description="OC response text")


class CategorizeResponse(BaseModel):
    """Response model for categorization result."""

    classification: str = Field(
        ...,
        pattern="^(fully_produced|partially_produced|not_produced|no_responsive_docs)$",
    )
    confidence_score: float = Field(..., ge=0, le=1)
    evidence_summary: str
    recommendation: Optional[str]


class ErrorDetail(BaseModel):
    """Error detail for structured error responses."""

    field: str
    issue: str


class ErrorResponse(BaseModel):
    """Structured error response."""

    error: Dict[str, Any]


# Endpoint implementations
@router.post(
    "/{agent_id}/analyze",
    response_model=AnalyzeResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid input parameters"},
        401: {"model": ErrorResponse, "description": "Missing authentication"},
        403: {"model": ErrorResponse, "description": "No case access permission"},
        404: {"model": ErrorResponse, "description": "Agent or documents not found"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
    },
)
@limiter.limit("10/hour")
async def analyze_production(
    request: Request,
    agent_id: str,
    body: AnalyzeRequest,
    case_context=Depends(require_case_context("write")),
) -> AnalyzeResponse:
    """
    Start deficiency analysis for a production against RTP requests.

    Long-running operation that returns immediately with processing details.
    Monitor progress via WebSocket using the returned channel.
    """
    try:
        # Load agent
        loader = AgentLoader()
        agent_def = await loader.load_agent(agent_id)

        # Validate agent supports analyze command
        if "analyze" not in [
            cmd.split(":")[0] for cmd in agent_def.get("commands", [])
        ]:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": {
                        "code": "UNSUPPORTED_COMMAND",
                        "message": f"Agent {agent_id} does not support analyze command",
                    }
                },
            )

        # Get security context
        security_context = get_agent_security_context(
            agent_id=agent_id, case_context=case_context, required_permission="write"
        )

        # Generate processing ID
        processing_id = uuid4()
        websocket_channel = f"agent:{agent_id}:{processing_id}"

        # Start analysis in background
        executor = AgentExecutor()

        # Track progress
        async with track_progress(
            case_id=case_context.case_id,
            agent_id=agent_id,
            task_name="analyze_production",
            total_steps=5,
        ) as tracker:
            await tracker.emit_progress(message="Analysis started")

            # Execute analysis asynchronously
            await executor.execute_command_async(
                agent_def=agent_def,
                command="analyze",
                case_name=case_context.case_name,
                security_context=security_context,
                parameters={
                    "production_id": str(body.production_id),
                    "rtp_document_id": str(body.rtp_document_id),
                    "oc_response_id": str(body.oc_response_id)
                    if body.oc_response_id
                    else None,
                    "options": body.options,
                    "processing_id": str(processing_id),
                },
            )

        logger.info(
            f"Started analysis {processing_id} for case {case_context.case_name}"
        )

        return AnalyzeResponse(
            processing_id=processing_id,
            websocket_channel=websocket_channel,
            estimated_duration_seconds=300,  # 5 minutes estimate
        )

    except AgentLoadError as e:
        logger.error(f"Failed to load agent {agent_id}: {e}")
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "AGENT_NOT_FOUND",
                    "message": f"Agent {agent_id} not found",
                }
            },
        )
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "ANALYSIS_FAILED",
                    "message": "Failed to start analysis",
                    "details": str(e),
                }
            },
        )


@router.post(
    "/{agent_id}/search",
    response_model=SearchResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid search parameters"},
        403: {"model": ErrorResponse, "description": "No case access permission"},
        404: {"model": ErrorResponse, "description": "Agent not found"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
    },
)
@limiter.limit("100/minute")
async def search_production(
    request: Request,
    agent_id: str,
    body: SearchRequest,
    case_context=Depends(require_case_context("read")),
) -> SearchResponse:
    """
    Search production documents for specific RTP-related content.

    Uses hybrid search combining semantic and keyword matching.
    """
    try:
        # Validate case name matches context
        if body.case_name != case_context.case_name:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": {
                        "code": "CASE_MISMATCH",
                        "message": "Case name does not match authenticated context",
                    }
                },
            )

        # Load agent
        loader = AgentLoader()
        agent_def = await loader.load_agent(agent_id)

        # Get security context
        security_context = get_agent_security_context(
            agent_id=agent_id, case_context=case_context, required_permission="read"
        )

        # Execute search
        executor = AgentExecutor()
        result = await executor.execute_command(
            agent_def=agent_def,
            command="search",
            case_name=case_context.case_name,
            security_context=security_context,
            parameters={
                "query": body.query,
                "filters": body.filters,
                "limit": body.limit,
                "offset": body.offset,
            },
        )

        # Format response
        results = [
            SearchResult(
                document_id=r["document_id"],
                chunk_text=r["chunk_text"],
                relevance_score=r["relevance_score"],
                metadata=r["metadata"],
            )
            for r in result.get("results", [])
        ]

        return SearchResponse(
            results=results,
            total_count=result.get("total_count", len(results)),
            has_more=result.get("has_more", False),
        )

    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "SEARCH_FAILED",
                    "message": "Search operation failed",
                    "details": str(e),
                }
            },
        )


@router.post(
    "/{agent_id}/categorize",
    response_model=CategorizeResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid categorization data"},
        403: {"model": ErrorResponse, "description": "No case access permission"},
        404: {"model": ErrorResponse, "description": "Agent not found"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
    },
)
@limiter.limit("50/minute")
async def categorize_compliance(
    request: Request,
    agent_id: str,
    body: CategorizeRequest,
    case_context=Depends(require_case_context("write")),
) -> CategorizeResponse:
    """
    Categorize RTP request compliance status based on search results.

    Analyzes evidence to classify as fully_produced, partially_produced,
    not_produced, or no_responsive_docs.
    """
    try:
        # Load agent
        loader = AgentLoader()
        agent_def = await loader.load_agent(agent_id)

        # Get security context
        security_context = get_agent_security_context(
            agent_id=agent_id, case_context=case_context, required_permission="write"
        )

        # Execute categorization
        executor = AgentExecutor()
        result = await executor.execute_command(
            agent_def=agent_def,
            command="categorize",
            case_name=case_context.case_name,
            security_context=security_context,
            parameters={
                "request_number": body.request_number,
                "request_text": body.request_text,
                "search_results": body.search_results,
                "oc_response_text": body.oc_response_text,
            },
        )

        return CategorizeResponse(
            classification=result["classification"],
            confidence_score=result["confidence_score"],
            evidence_summary=result["evidence_summary"],
            recommendation=result.get("recommendation"),
        )

    except Exception as e:
        logger.error(f"Categorization failed: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "CATEGORIZATION_FAILED",
                    "message": "Failed to categorize compliance",
                    "details": str(e),
                }
            },
        )


@router.get(
    "/{agent_id}/report/{report_id}",
    responses={
        200: {"description": "Report retrieved successfully"},
        403: {"model": ErrorResponse, "description": "No case access permission"},
        404: {"model": ErrorResponse, "description": "Report not found"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
    },
)
@limiter.limit("30/minute")
async def get_report(
    request: Request,
    agent_id: str,
    report_id: str,
    format: str = Query("json", pattern="^(json|html|pdf)$"),
    include_evidence: bool = Query(True),
    case_context=Depends(require_case_context("read")),
) -> Response:
    """
    Retrieve generated deficiency analysis report.

    Supports multiple formats: json, html, pdf.
    """
    try:
        # Load agent
        loader = AgentLoader()
        agent_def = await loader.load_agent(agent_id)

        # Get security context
        security_context = get_agent_security_context(
            agent_id=agent_id, case_context=case_context, required_permission="read"
        )

        # Execute report retrieval
        executor = AgentExecutor()
        result = await executor.execute_command(
            agent_def=agent_def,
            command="report",
            case_name=case_context.case_name,
            security_context=security_context,
            parameters={
                "report_id": report_id,
                "format": format,
                "include_evidence": include_evidence,
            },
        )

        # Set appropriate content type and headers
        content_types = {
            "json": "application/json",
            "html": "text/html",
            "pdf": "application/pdf",
        }

        headers = {"Content-Type": content_types[format]}

        if format == "pdf":
            headers["Content-Disposition"] = (
                f'attachment; filename="deficiency_report_{report_id}.pdf"'
            )

        return Response(
            content=result["content"], headers=headers, media_type=content_types[format]
        )

    except Exception as e:
        logger.error(f"Report retrieval failed: {e}")
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "REPORT_NOT_FOUND",
                    "message": f"Report {report_id} not found",
                    "details": str(e),
                }
            },
        )


# Health check endpoint
@router.get("/health")
async def agent_health():
    """Check agent system health."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
    }

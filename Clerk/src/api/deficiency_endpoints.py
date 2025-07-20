"""
API endpoints for deficiency report generation and retrieval.

Provides RESTful endpoints for generating, storing, and retrieving
deficiency analysis reports with case isolation.
"""

from datetime import datetime
from typing import Dict, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.connection import get_db
from src.middleware.case_context import require_case_context
from src.models.deficiency_models import DeficiencyItem, DeficiencyReport
from src.services.report_generator import ReportGenerator
from src.services.report_storage import ReportStorage
from src.utils.logger import get_logger
from src.websocket.socket_server import sio

logger = get_logger("clerk_api")

router = APIRouter(
    prefix="/api/deficiency",
    tags=["deficiency"],
    responses={404: {"description": "Not found"}},
)


class ReportGenerationRequest(BaseModel):
    """Request model for report generation."""

    analysis_id: UUID = Field(..., description="Deficiency analysis ID")
    format: str = Field(
        default="json",
        description="Output format",
        pattern="^(json|html|markdown|pdf)$",
    )
    options: Optional[Dict] = Field(default=None, description="Format-specific options")


class ReportGenerationResponse(BaseModel):
    """Response model for report generation."""

    report_id: UUID = Field(..., description="Generated report ID")
    status: str = Field(..., description="Generation status")
    format: str = Field(..., description="Report format")
    message: str = Field(..., description="Status message")
    processing_id: Optional[UUID] = Field(
        None, description="ID for tracking async processing"
    )


@router.post(
    "/report/generate",
    response_model=ReportGenerationResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Generate deficiency report",
    description="Generate a deficiency report in specified format",
)
async def generate_report(
    request: ReportGenerationRequest,
    case_context=Depends(require_case_context("write")),
    db: AsyncSession = Depends(get_db),
) -> ReportGenerationResponse:
    """
    Generate a deficiency report for analysis results.

    Requires write permission on the case. Report generation is
    processed asynchronously with WebSocket progress updates.

    Args:
        request: Report generation parameters.
        case_context: Validated case context.
        db: Database session.

    Returns:
        ReportGenerationResponse: Processing status and report ID.

    Raises:
        HTTPException: If analysis not found or generation fails.
    """
    try:
        # Validate analysis exists and belongs to case
        storage = ReportStorage(db)
        report = await storage.get_report(request.analysis_id, case_context.case_name)

        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Analysis {request.analysis_id} not found in case",
            )

        if report.analysis_status != "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Report can only be generated for completed analysis",
            )

        # Emit start event
        await sio.emit(
            "deficiency:report_generation_started",
            {
                "analysis_id": str(request.analysis_id),
                "format": request.format,
                "case_id": case_context.case_id,
            },
            room=f"case_{case_context.case_id}",
        )

        logger.info(
            f"Starting {request.format} report generation for "
            f"analysis {request.analysis_id}"
        )

        # Get deficiency items
        items = await storage.get_report_items(request.analysis_id)

        # Generate and store report
        generator = ReportGenerator(db)
        result = await generator.generate_and_store_report(
            report=report,
            deficiency_items=items,
            format=request.format,
            options=request.options,
            created_by=case_context.user_id,
        )

        # Emit completion event
        await sio.emit(
            "deficiency:report_generation_completed",
            {
                "analysis_id": str(request.analysis_id),
                "report_id": result["report_id"],
                "format": request.format,
                "version": result["version"],
            },
            room=f"case_{case_context.case_id}",
        )

        return ReportGenerationResponse(
            report_id=UUID(result["report_id"]),
            status="processing",
            format=request.format,
            message=(
                f"Report generation started. Monitor WebSocket events "
                f"for progress. Report expires at {result['expires_at']}"
            ),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Report generation failed: {e}")

        # Emit error event
        await sio.emit(
            "deficiency:report_generation_failed",
            {
                "analysis_id": str(request.analysis_id),
                "format": request.format,
                "error": str(e),
            },
            room=f"case_{case_context.case_id}",
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Report generation failed: {str(e)}",
        )


@router.get(
    "/report/{report_id}",
    summary="Get deficiency report",
    description="Retrieve a generated report in specified format",
)
async def get_report(
    report_id: UUID,
    format: str = Query(
        default="json",
        description="Desired format",
        pattern="^(json|html|markdown|pdf)$",
    ),
    version: Optional[int] = Query(
        default=None, description="Specific version to retrieve", ge=1
    ),
    case_context=Depends(require_case_context("read")),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """
    Retrieve a generated deficiency report.

    Returns the report in the requested format. If a specific version
    is requested, retrieves that version. Otherwise returns the latest.

    Args:
        report_id: Report identifier.
        format: Desired output format.
        version: Optional version number.
        case_context: Validated case context.
        db: Database session.

    Returns:
        Response: Report content with appropriate content-type.

    Raises:
        HTTPException: If report not found or access denied.
    """
    try:
        storage = ReportStorage(db)

        # Validate report belongs to case
        report = await storage.get_report(report_id, case_context.case_name)
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Report {report_id} not found",
            )

        # Check for cached generated report
        generated = await storage.get_generated_report(report_id, format)

        if generated and not version:
            # Return cached version
            content_type = _get_content_type(format)
            return Response(
                content=generated.content,
                media_type=content_type,
                headers={
                    "Content-Disposition": (
                        f'inline; filename="deficiency_report_'
                        f"{report.case_name}_{datetime.utcnow().strftime('%Y%m%d')}"
                        f'.{_get_file_extension(format)}"'
                    )
                },
            )

        # Generate fresh report or specific version
        if version:
            # Get specific version
            report_version = await storage.get_report_version(report_id, version)
            if not report_version:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Version {version} not found for report",
                )

            # Reconstruct report from version
            report = DeficiencyReport(**report_version.content["report"])
            items = [DeficiencyItem(**item) for item in report_version.content["items"]]
        else:
            # Get current items
            items = await storage.get_report_items(report_id)

        # Generate report
        generator = ReportGenerator(db)
        content = await generator.generate_report(
            report=report, deficiency_items=items, format=format
        )

        # Cache if not versioned request
        if not version:
            await storage.save_generated_report(
                report_id=report_id, format=format, content=content
            )

        content_type = _get_content_type(format)
        return Response(
            content=content,
            media_type=content_type,
            headers={
                "Content-Disposition": (
                    f'inline; filename="deficiency_report_'
                    f"{report.case_name}_v{version or report.version}"
                    f'.{_get_file_extension(format)}"'
                )
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve report: {str(e)}",
        )


def _get_content_type(format: str) -> str:
    """Get content type for format."""
    content_types = {
        "json": "application/json",
        "html": "text/html",
        "markdown": "text/markdown",
        "pdf": "text/html",  # PDF prep returns HTML
    }
    return content_types.get(format, "application/octet-stream")


def _get_file_extension(format: str) -> str:
    """Get file extension for format."""
    extensions = {
        "json": "json",
        "html": "html",
        "markdown": "md",
        "pdf": "html",  # PDF prep
    }
    return extensions.get(format, "txt")

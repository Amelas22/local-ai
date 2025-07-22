"""
API endpoints for Good Faith Letter BMad agent.
"""

from typing import Dict, Any, Optional, List
from uuid import UUID
from datetime import datetime
import io
from pydantic import BaseModel, Field, field_validator
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse

from src.ai_agents.bmad_framework import AgentLoader, AgentExecutor
from src.ai_agents.bmad_framework.security import (
    get_agent_security_context,
    AgentSecurityContext,
)
from src.ai_agents.bmad_framework.websocket_progress import emit_progress_update as emit_agent_event
from src.services.good_faith_letter_agent_service import GoodFaithLetterAgentService
from src.services.letter_customization_service import (
    LetterCustomizationService,
    LetterStatus,
)
from src.models.deficiency_models import GeneratedLetter, LetterEdit
from src.utils.logger import get_logger
from src.middleware.rate_limiter import (
    check_letter_generation_limit,
    check_general_api_limit,
)
from src.utils.audit_logger import api_audit_logger, security_audit_logger

logger = get_logger("good_faith_letter_api")

router = APIRouter(
    prefix="/api/agents/good-faith-letter", tags=["good-faith-letter-agent"]
)


class AgentCommandRequest(BaseModel):
    """Request model for agent command execution."""

    command: str
    parameters: Dict[str, Any] = Field(default_factory=dict)


class AgentCommandResponse(BaseModel):
    """Response model for agent command execution."""

    command: str
    status: str
    output: Dict[str, Any]
    execution_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class GenerateLetterRequest(BaseModel):
    """Request model for letter generation."""

    report_id: UUID
    jurisdiction: str = "federal"
    state_code: Optional[str] = None
    include_evidence: bool = True
    evidence_format: str = "inline"
    attorney_info: Dict[str, Any]
    additional_variables: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("attorney_info")
    @classmethod
    def validate_attorney_info(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate required attorney information fields."""
        required_fields = ["name", "firm", "email"]
        missing_fields = [field for field in required_fields if field not in v]

        if missing_fields:
            raise ValueError(
                f"attorney_info missing required fields: {', '.join(missing_fields)}"
            )

        # Validate email format
        import re

        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, v["email"]):
            raise ValueError("Invalid email format in attorney_info")

        return v


class GenerateLetterResponse(BaseModel):
    """Response model for letter generation."""

    letter_id: UUID
    status: LetterStatus
    agent_execution_id: str
    preview_url: str


class CustomizeLetterRequest(BaseModel):
    """Request model for letter customization."""

    section_edits: List[Dict[str, str]]
    editor_notes: Optional[str] = None

    @field_validator("section_edits")
    @classmethod
    def validate_section_edits(cls, v: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Validate section edits are not empty."""
        if not v:
            raise ValueError("At least one edit must be provided")
        return v


class FinalizeLetterRequest(BaseModel):
    """Request model for letter finalization."""

    approved_by: str
    export_formats: List[str] = Field(default=["pdf", "docx"])


@router.post("/execute", response_model=AgentCommandResponse)
async def execute_agent_command(
    request: AgentCommandRequest,
    security_context: AgentSecurityContext = Depends(get_agent_security_context),
) -> AgentCommandResponse:
    """
    Execute any Good Faith Letter agent command.

    Available commands:
    - generate-letter: Generate letter from deficiency report
    - select-template: Choose jurisdiction-appropriate template
    - preview-letter: Preview generated letter
    - customize-letter: Apply customizations
    - finalize-letter: Finalize for sending
    """
    try:
        # Validate command
        valid_commands = [
            "generate-letter",
            "select-template",
            "preview-letter",
            "customize-letter",
            "finalize-letter",
        ]

        if request.command not in valid_commands:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid command. Must be one of: {', '.join(valid_commands)}",
            )

        # Emit agent activation event
        await emit_agent_event(
            case_id=security_context.case_id,
            agent_id="good-faith-letter",
            task_name=request.command,
            message=f"Agent activated for command: {request.command}",
            percentage=0,
            status="started",
            metadata={"command": request.command},
        )

        # Execute via BMad framework
        loader = AgentLoader()
        executor = AgentExecutor()

        agent_def = await loader.load_agent("good-faith-letter")

        result = await executor.execute_command(
            agent_def=agent_def,
            command=request.command,
            case_name=security_context.case_name,
            security_context=security_context,
            parameters=request.parameters,
        )

        return AgentCommandResponse(
            command=request.command,
            status=result.status,
            output=result.output,
            execution_id=result.execution_id,
        )

    except HTTPException:
        # Re-raise HTTPExceptions to preserve status codes
        raise
    except Exception as e:
        logger.error(f"Agent command execution failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-letter", response_model=GenerateLetterResponse)
async def generate_letter_via_agent(
    request: GenerateLetterRequest,
    background_tasks: BackgroundTasks,
    security_context: AgentSecurityContext = Depends(get_agent_security_context),
    _: None = Depends(check_letter_generation_limit),
) -> GenerateLetterResponse:
    """Generate Good Faith letter using BMad agent."""
    try:
        # Emit WebSocket event for agent activation
        await emit_agent_event(
            case_id=security_context.case_id,
            agent_id="good-faith-letter",
            task_name="generate-letter",
            message="Generating Good Faith letter",
            percentage=0,
            status="started",
            metadata={
                "report_id": str(request.report_id),
                "jurisdiction": request.jurisdiction,
            },
        )

        # Initialize service
        service = GoodFaithLetterAgentService()

        # Prepare parameters for agent
        agent_params = {
            "report_id": str(request.report_id),
            "jurisdiction": request.jurisdiction,
            "state_code": request.state_code,
            "include_evidence": request.include_evidence,
            "evidence_format": request.evidence_format,
            "attorney_info": request.attorney_info,
            "additional_variables": request.additional_variables,
        }

        # Execute letter generation
        letter = await service.generate_letter(
            parameters=agent_params, security_context=security_context
        )

        # Emit completion event
        await emit_agent_event(
            case_id=security_context.case_id,
            agent_id="good-faith-letter",
            task_name="generate-letter",
            message="Letter generation completed",
            percentage=100,
            status="completed",
            metadata={
                "letter_id": str(letter.id),
                "execution_id": letter.agent_execution_id,
            },
        )

        return GenerateLetterResponse(
            letter_id=letter.id,
            status=letter.status,
            agent_execution_id=letter.agent_execution_id,
            preview_url=f"/api/agents/good-faith-letter/preview/{letter.id}",
        )

    except HTTPException:
        # Re-raise HTTPExceptions to preserve status codes
        raise
    except Exception as e:
        logger.error(f"Letter generation failed: {str(e)}")

        await emit_agent_event(
            case_id=security_context.case_id,
            agent_id="good-faith-letter",
            task_name="generate-letter",
            message=f"Letter generation failed: {str(e)}",
            percentage=0,
            status="failed",
            metadata={"error": str(e)},
        )

        raise HTTPException(status_code=500, detail=str(e))


@router.get("/preview/{letter_id}")
async def preview_letter(
    letter_id: UUID,
    security_context: AgentSecurityContext = Depends(get_agent_security_context),
    _: None = Depends(check_general_api_limit),
) -> Dict[str, Any]:
    """Preview generated letter."""
    try:
        service = GoodFaithLetterAgentService()

        # Get letter with security validation
        letter = await service.get_letter(
            letter_id=letter_id, security_context=security_context
        )

        if not letter:
            # Log access attempt for non-existent or inaccessible letter
            security_audit_logger.log_access_denied(
                user_id=security_context.user_id,
                resource_type="letter",
                resource_id=str(letter_id),
                case_name=security_context.case_name,
                reason="Letter not found or access denied",
            )
            raise HTTPException(status_code=404, detail="Letter not found")

        return {
            "letter_id": str(letter.id),
            "status": letter.status,
            "content": letter.content,
            "metadata": {
                "jurisdiction": letter.jurisdiction,
                "created_at": letter.created_at.isoformat(),
                "version": letter.version,
                "editable": letter.status == LetterStatus.DRAFT,
            },
        }

    except HTTPException:
        # Re-raise HTTPExceptions to preserve status codes
        raise
    except Exception as e:
        logger.error(f"Letter preview failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/customize/{letter_id}")
async def customize_letter(
    letter_id: UUID,
    request: CustomizeLetterRequest,
    security_context: AgentSecurityContext = Depends(get_agent_security_context),
    _: None = Depends(check_general_api_limit),
) -> Dict[str, Any]:
    """Apply customizations to generated letter."""
    try:
        # Emit customization start event
        await emit_agent_event(
            case_id=security_context.case_id,
            agent_id="good-faith-letter",
            task_name="customize-letter",
            message="Starting letter customization",
            percentage=0,
            status="started",
            metadata={
                "letter_id": str(letter_id),
                "edit_count": len(request.section_edits),
            },
        )

        # Apply customizations
        customization_service = LetterCustomizationService()

        updated_letter = await customization_service.apply_edits(
            letter_id=letter_id,
            section_edits=request.section_edits,
            editor_id=security_context.user_id,
            editor_notes=request.editor_notes,
        )

        # Emit completion event
        await emit_agent_event(
            case_id=security_context.case_id,
            agent_id="good-faith-letter",
            task_name="customize-letter",
            message="Letter customization completed",
            percentage=100,
            status="completed",
            metadata={
                "letter_id": str(letter_id),
                "version": updated_letter.version,
                "changes": len(request.section_edits),
            },
        )

        return {
            "letter_id": str(updated_letter.id),
            "version": updated_letter.version,
            "status": updated_letter.status,
            "edit_history_count": len(updated_letter.edit_history),
        }

    except HTTPException:
        # Re-raise HTTPExceptions to preserve status codes
        raise
    except Exception as e:
        logger.error(f"Letter customization failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/finalize/{letter_id}")
async def finalize_letter(
    letter_id: UUID,
    request: FinalizeLetterRequest,
    security_context: AgentSecurityContext = Depends(get_agent_security_context),
    _: None = Depends(check_general_api_limit),
) -> Dict[str, Any]:
    """Finalize letter for sending."""
    try:
        service = GoodFaithLetterAgentService()

        # Finalize letter
        finalized = await service.finalize_letter(
            letter_id=letter_id,
            approved_by=request.approved_by,
            security_context=security_context,
        )

        # Emit finalization event
        await emit_agent_event(
            case_id=security_context.case_id,
            agent_id="good-faith-letter",
            task_name="finalize-letter",
            message="Letter finalized and approved",
            percentage=100,
            status="completed",
            metadata={
                "letter_id": str(letter_id),
                "approved_by": request.approved_by,
            },
        )

        # Generate export URLs
        export_urls = {}
        for format in request.export_formats:
            export_urls[format] = (
                f"/api/agents/good-faith-letter/export/{letter_id}/{format}"
            )

        return {
            "letter_id": str(finalized.id),
            "status": finalized.status,
            "approved_by": finalized.approved_by,
            "approved_at": finalized.approved_at.isoformat(),
            "export_urls": export_urls,
        }

    except HTTPException:
        # Re-raise HTTPExceptions to preserve status codes
        raise
    except Exception as e:
        logger.error(f"Letter finalization failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export/{letter_id}/{format}")
async def export_letter(
    letter_id: UUID,
    format: str,
    security_context: AgentSecurityContext = Depends(get_agent_security_context),
) -> StreamingResponse:
    """Export finalized letter in specified format."""
    try:
        if format not in ["pdf", "docx", "html"]:
            raise HTTPException(
                status_code=400, detail="Invalid format. Must be: pdf, docx, or html"
            )

        service = GoodFaithLetterAgentService()

        # Get letter
        letter = await service.get_letter(letter_id, security_context)

        if letter.status != LetterStatus.FINALIZED:
            raise HTTPException(
                status_code=400, detail="Letter must be finalized before export"
            )

        # Generate export using BMad create-doc task
        export_data = await service.export_letter(
            letter_id=letter_id, format=format, security_context=security_context
        )

        # Determine content type
        content_types = {
            "pdf": "application/pdf",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "html": "text/html",
        }

        # Handle bytes content
        if isinstance(export_data["content"], bytes):
            content = io.BytesIO(export_data["content"])
        else:
            content = io.BytesIO(export_data["content"].encode())

        return StreamingResponse(
            content,
            media_type=content_types[format],
            headers={
                "Content-Disposition": f"attachment; filename={export_data['filename']}"
            },
        )

    except HTTPException:
        # Re-raise HTTPExceptions to preserve status codes
        raise
    except Exception as e:
        logger.error(f"Letter export failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/templates")
async def list_available_templates(
    security_context: AgentSecurityContext = Depends(get_agent_security_context),
) -> List[Dict[str, Any]]:
    """List available Good Faith letter templates."""
    try:
        service = GoodFaithLetterAgentService()
        templates = await service.list_templates()

        return [
            {
                "template_id": t["id"],
                "jurisdiction": t["jurisdiction"],
                "title": t["title"],
                "description": t["description"],
                "required_variables": t["required_variables"],
            }
            for t in templates
        ]

    except HTTPException:
        # Re-raise HTTPExceptions to preserve status codes
        raise
    except Exception as e:
        logger.error(f"Template listing failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

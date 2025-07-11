"""
FastAPI endpoints for motion drafting functionality
Add these to your main.py or create a separate router
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Response
from fastapi.responses import FileResponse
from typing import Optional, Dict, Any
import os
import uuid
import json

from src.ai_agents.motion_drafter import motion_drafter, DocumentLength
from src.ai_agents.motion_models import (
    DraftingRequest,
    DraftingProgress,
    MotionDraftResponse,
    RevisionRequest,
    ExportRequest,
    QualityMetrics,
    validate_outline_structure,
)
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Create router
motion_router = APIRouter(prefix="/motion", tags=["motion_drafting"])

# In-memory storage for drafts (use Redis or database in production)
draft_storage: Dict[str, Any] = {}
draft_progress: Dict[str, DraftingProgress] = {}


@motion_router.post("/draft", response_model=Dict[str, str])
async def start_motion_draft(
    request: DraftingRequest, background_tasks: BackgroundTasks
):
    """
    Start drafting a legal motion from an outline.
    Returns a draft ID for tracking progress.
    """
    try:
        # Validate outline structure
        if not validate_outline_structure(request.outline):
            raise HTTPException(
                status_code=400,
                detail="Invalid outline structure for the specified motion type",
            )

        # Generate draft ID
        draft_id = str(uuid.uuid4())

        # Initialize progress tracking
        total_sections = len(request.outline.sections)
        for section in request.outline.sections:
            if section.subsections:
                total_sections += len(section.subsections)

        draft_progress[draft_id] = DraftingProgress(
            status="initializing",
            total_sections=total_sections,
            messages=["Draft request received"],
        )

        # Start drafting in background
        background_tasks.add_task(draft_motion_background, draft_id, request)

        return {
            "draft_id": draft_id,
            "message": "Motion drafting started",
            "estimated_sections": total_sections,
        }

    except Exception as e:
        logger.error(f"Error starting motion draft: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@motion_router.get("/draft/{draft_id}/progress", response_model=DraftingProgress)
async def get_draft_progress(draft_id: str):
    """Get the current progress of a motion draft"""
    if draft_id not in draft_progress:
        raise HTTPException(status_code=404, detail="Draft not found")

    return draft_progress[draft_id]


@motion_router.get("/draft/{draft_id}", response_model=MotionDraftResponse)
async def get_draft(draft_id: str):
    """Get the completed motion draft"""
    if draft_id not in draft_storage:
        if draft_id in draft_progress:
            return Response(
                content=json.dumps(
                    {
                        "status": draft_progress[draft_id].status,
                        "message": "Draft still in progress",
                    }
                ),
                status_code=202,
            )
        else:
            raise HTTPException(status_code=404, detail="Draft not found")

    draft = draft_storage[draft_id]

    # Convert to response model
    return MotionDraftResponse(
        title=draft.title,
        case_name=draft.case_name,
        sections=[
            {
                "section_id": section.outline_section.id,
                "title": section.outline_section.title,
                "content": section.content,
                "word_count": section.word_count,
                "citations": section.citations_used,
                "confidence_score": section.confidence_score,
                "expansion_cycles": section.expansion_cycles,
                "needs_revision": section.needs_revision,
            }
            for section in draft.sections
        ],
        total_word_count=draft.total_word_count,
        total_pages=draft.total_page_estimate,
        creation_timestamp=draft.creation_timestamp,
        coherence_score=draft.coherence_score,
        review_notes=draft.review_notes,
        export_links={
            "docx": f"/motion/draft/{draft_id}/export/docx",
            "pdf": f"/motion/draft/{draft_id}/export/pdf",
            "txt": f"/motion/draft/{draft_id}/export/txt",
        },
    )


@motion_router.post("/draft/{draft_id}/revise")
async def revise_draft(
    draft_id: str, request: RevisionRequest, background_tasks: BackgroundTasks
):
    """Revise specific sections of a draft"""
    if draft_id not in draft_storage:
        raise HTTPException(status_code=404, detail="Draft not found")

    # Start revision in background
    background_tasks.add_task(revise_motion_background, draft_id, request)

    return {
        "message": "Revision started",
        "sections_to_revise": len(request.section_ids),
    }


@motion_router.get("/draft/{draft_id}/export/{format}")
async def export_draft(draft_id: str, format: str):
    """Export draft in specified format"""
    if draft_id not in draft_storage:
        raise HTTPException(status_code=404, detail="Draft not found")

    if format not in ["docx", "pdf", "txt"]:
        raise HTTPException(status_code=400, detail="Invalid format")

    draft = draft_storage[draft_id]

    try:
        if format == "docx":
            # Export to DOCX
            output_path = f"/tmp/motion_{draft_id}.docx"
            motion_drafter.export_to_docx(draft, output_path)

            return FileResponse(
                output_path,
                media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                filename=f"{draft.title.replace(' ', '_')}.docx",
            )

        elif format == "txt":
            # Export as plain text
            content = f"{draft.title}\n\n{draft.case_name}\n\n"
            for section in draft.sections:
                content += f"\n{section.outline_section.title}\n\n"
                content += section.content + "\n\n"

            return Response(
                content=content,
                media_type="text/plain",
                headers={
                    "Content-Disposition": f"attachment; filename={draft.title.replace(' ', '_')}.txt"
                },
            )

        elif format == "pdf":
            # PDF export would require additional libraries
            raise HTTPException(
                status_code=501,
                detail="PDF export not implemented. Use DOCX and convert.",
            )

    except Exception as e:
        logger.error(f"Error exporting draft: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@motion_router.post("/draft/{draft_id}/upload-to-box")
async def upload_draft_to_box(draft_id: str, request: ExportRequest):
    """Upload draft to Box folder"""
    if draft_id not in draft_storage:
        raise HTTPException(status_code=404, detail="Draft not found")

    if not request.box_folder_id:
        raise HTTPException(status_code=400, detail="Box folder ID required")

    try:
        # Export to DOCX
        draft = draft_storage[draft_id]
        output_path = f"/tmp/motion_{draft_id}.docx"
        motion_drafter.export_to_docx(draft, output_path)

        # Upload to Box (requires Box client from document_injector)
        from src.document_injector import document_injector

        with open(output_path, "rb") as f:
            uploaded_file = document_injector.box_client.upload_file(
                file_stream=f,
                file_name=f"{draft.title}.docx",
                parent_folder_id=request.box_folder_id,
                description=f"AI-generated motion draft created on {draft.creation_timestamp}",
            )

        # Clean up temp file
        os.remove(output_path)

        return {
            "success": True,
            "box_file_id": uploaded_file.id,
            "box_file_name": uploaded_file.name,
            "message": "Draft uploaded to Box successfully",
        }

    except Exception as e:
        logger.error(f"Error uploading to Box: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@motion_router.get("/draft/{draft_id}/quality", response_model=QualityMetrics)
async def get_draft_quality(draft_id: str):
    """Get quality metrics for a draft"""
    if draft_id not in draft_storage:
        raise HTTPException(status_code=404, detail="Draft not found")

    draft = draft_storage[draft_id]

    # Calculate quality metrics
    metrics = calculate_quality_metrics(draft)

    return metrics


# Background tasks
async def draft_motion_background(draft_id: str, request: DraftingRequest):
    """Background task to draft motion"""
    try:
        # Update progress
        draft_progress[draft_id].status = "preparing"
        draft_progress[draft_id].messages.append(
            "Preparing outline and retrieving case documents"
        )

        # Convert target length
        length_map = {
            "SHORT": DocumentLength.SHORT,
            "MEDIUM": DocumentLength.MEDIUM,
            "LONG": DocumentLength.LONG,
        }
        target_length = length_map.get(request.target_length, DocumentLength.MEDIUM)

        # Create progress callback
        def progress_callback(message: str, section: Optional[str] = None):
            if section:
                draft_progress[draft_id].current_section = section
                draft_progress[draft_id].sections_completed += 1
            draft_progress[draft_id].messages.append(message)
            draft_progress[draft_id].status = "drafting"

        # Start drafting
        motion_draft = await motion_drafter.draft_motion(
            outline=request.outline.dict(),
            case_name=request.case_name,
            target_length=target_length,
            motion_title=request.outline.title,
        )

        # Store completed draft
        draft_storage[draft_id] = motion_draft

        # Update progress
        draft_progress[draft_id].status = "completed"
        draft_progress[draft_id].current_word_count = motion_draft.total_word_count
        draft_progress[draft_id].estimated_pages = motion_draft.total_page_estimate
        draft_progress[draft_id].messages.append(
            f"Draft completed: {motion_draft.total_page_estimate} pages"
        )

    except Exception as e:
        logger.error(f"Error in background drafting: {str(e)}")
        draft_progress[draft_id].status = "failed"
        draft_progress[draft_id].messages.append(f"Error: {str(e)}")


async def revise_motion_background(draft_id: str, request: RevisionRequest):
    """Background task to revise motion sections"""
    try:
        draft = draft_storage[draft_id]

        # Update progress
        if draft_id not in draft_progress:
            draft_progress[draft_id] = DraftingProgress(status="revising")

        draft_progress[draft_id].status = "revising"
        draft_progress[draft_id].messages.append(
            f"Starting revision of {len(request.section_ids)} sections"
        )

        # Revise each requested section
        for section_id in request.section_ids:
            # Find the section
            section_to_revise = None
            for section in draft.sections:
                if section.outline_section.id == section_id:
                    section_to_revise = section
                    break

            if section_to_revise and section_id in request.revision_instructions:
                instruction = request.revision_instructions[section_id]

                # Create revision prompt
                revision_prompt = f"""Revise the following section based on these instructions:

Instructions: {instruction}

Current Section:
{section_to_revise.content}

Maintain the same general structure and citations while addressing the revision request."""

                # Get revision from AI
                revised_content = await motion_drafter.section_writer.run(
                    revision_prompt
                )

                # Update section
                section_to_revise.content = revised_content
                section_to_revise.word_count = len(revised_content.split())
                section_to_revise.needs_revision = False

                draft_progress[draft_id].messages.append(
                    f"Revised section: {section_to_revise.outline_section.title}"
                )

        # Recalculate totals
        draft.total_word_count = sum(s.word_count for s in draft.sections)
        draft.total_page_estimate = (
            draft.total_word_count // motion_drafter.words_per_page
        )

        # Re-review document
        draft = await motion_drafter._review_and_refine(draft, {})

        # Update storage
        draft_storage[draft_id] = draft

        # Update progress
        draft_progress[draft_id].status = "revision_completed"
        draft_progress[draft_id].messages.append("Revision completed successfully")

    except Exception as e:
        logger.error(f"Error in revision: {str(e)}")
        draft_progress[draft_id].status = "revision_failed"
        draft_progress[draft_id].messages.append(f"Revision error: {str(e)}")


def calculate_quality_metrics(draft) -> QualityMetrics:
    """Calculate quality metrics for a draft"""
    # Basic implementation - would be more sophisticated in production

    # Citation accuracy (check if all required citations are present)
    total_required_citations = sum(
        len(section.outline_section.legal_authorities) for section in draft.sections
    )
    total_found_citations = sum(
        len(section.citations_used) for section in draft.sections
    )
    citation_accuracy = min(
        1.0, total_found_citations / max(total_required_citations, 1)
    )

    # Argument strength (based on confidence scores)
    avg_confidence = sum(s.confidence_score for s in draft.sections) / len(
        draft.sections
    )

    # Factual consistency (simplified - would check against case docs)
    factual_consistency = 0.9 if draft.coherence_score > 0.7 else 0.6

    # Overall readiness
    readiness = int(
        (draft.coherence_score * 0.4 + citation_accuracy * 0.3 + avg_confidence * 0.3)
        * 10
    )

    # Identify issues
    issues = []
    if citation_accuracy < 0.8:
        issues.append(
            {
                "type": "missing_citations",
                "severity": "medium",
                "description": "Some required citations may be missing",
            }
        )

    if any(s.needs_revision for s in draft.sections):
        issues.append(
            {
                "type": "sections_need_revision",
                "severity": "high",
                "sections": [
                    s.outline_section.id for s in draft.sections if s.needs_revision
                ],
            }
        )

    return QualityMetrics(
        coherence_score=draft.coherence_score,
        citation_accuracy=citation_accuracy,
        argument_strength=avg_confidence,
        factual_consistency=factual_consistency,
        readiness_score=readiness,
        issues_found=issues,
        suggestions=draft.review_notes,
    )


# Add router to main app in main.py:
# app.include_router(motion_router)

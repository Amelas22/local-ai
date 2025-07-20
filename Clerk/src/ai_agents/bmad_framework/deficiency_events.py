"""
Deficiency analysis specific WebSocket events.

Extends the base websocket_progress module with events specific to 
deficiency analysis workflows.
"""

from typing import Dict, Any, Optional
from datetime import datetime

from .websocket_progress import ProgressTracker


class DeficiencyProgressTracker(ProgressTracker):
    """
    Extended progress tracker for deficiency analysis tasks.
    
    Adds specific event types for RTP parsing, document search,
    categorization, and report generation.
    """
    
    # Deficiency-specific event types
    ANALYSIS_STARTED = "agent:analysis_started"
    RTP_PARSING_PROGRESS = "agent:rtp_parsing_progress"
    SEARCH_PROGRESS = "agent:search_progress"
    CATEGORIZATION_PROGRESS = "agent:categorization_progress"
    REPORT_GENERATION_PROGRESS = "agent:report_generation_progress"
    ANALYSIS_COMPLETED = "agent:analysis_completed"
    ANALYSIS_FAILED = "agent:analysis_failed"
    
    async def emit_analysis_started(
        self,
        production_id: str,
        rtp_document_id: str,
        total_requests: Optional[int] = None
    ) -> None:
        """
        Emit analysis started event.
        
        Args:
            production_id: Production document batch ID.
            rtp_document_id: RTP document ID.
            total_requests: Total RTP requests to analyze.
        """
        metadata = {
            "production_id": production_id,
            "rtp_document_id": rtp_document_id,
            "total_requests": total_requests
        }
        
        await self._emit_update(
            self.ANALYSIS_STARTED,
            self._create_update(
                status="started",
                message="Deficiency analysis started",
                metadata=metadata
            )
        )
    
    async def emit_rtp_parsing_progress(
        self,
        pages_processed: int,
        total_pages: int,
        requests_found: int
    ) -> None:
        """
        Emit RTP parsing progress.
        
        Args:
            pages_processed: Number of pages processed.
            total_pages: Total pages in document.
            requests_found: Number of requests found so far.
        """
        metadata = {
            "pages_processed": pages_processed,
            "total_pages": total_pages,
            "requests_found": requests_found,
            "parsing_percentage": int((pages_processed / total_pages) * 100)
        }
        
        await self._emit_update(
            self.RTP_PARSING_PROGRESS,
            self._create_update(
                status="processing",
                message=f"Parsing RTP: {pages_processed}/{total_pages} pages",
                metadata=metadata
            )
        )
    
    async def emit_search_progress(
        self,
        request_number: str,
        request_index: int,
        total_requests: int,
        documents_searched: int
    ) -> None:
        """
        Emit document search progress.
        
        Args:
            request_number: Current RTP request number.
            request_index: Index of current request.
            total_requests: Total requests to search.
            documents_searched: Documents searched for this request.
        """
        metadata = {
            "request_number": request_number,
            "request_index": request_index,
            "total_requests": total_requests,
            "documents_searched": documents_searched,
            "search_percentage": int((request_index / total_requests) * 100)
        }
        
        await self._emit_update(
            self.SEARCH_PROGRESS,
            self._create_update(
                status="processing",
                message=f"Searching for Request {request_number}",
                metadata=metadata
            )
        )
    
    async def emit_categorization_progress(
        self,
        request_number: str,
        category: str,
        confidence: float,
        deficiencies_found: int
    ) -> None:
        """
        Emit categorization progress.
        
        Args:
            request_number: RTP request number.
            category: Assigned category.
            confidence: Confidence score.
            deficiencies_found: Total deficiencies found so far.
        """
        metadata = {
            "request_number": request_number,
            "category": category,
            "confidence": confidence,
            "deficiencies_found": deficiencies_found
        }
        
        await self._emit_update(
            self.CATEGORIZATION_PROGRESS,
            self._create_update(
                status="processing",
                message=f"Categorized {request_number} as {category}",
                metadata=metadata
            )
        )
    
    async def emit_report_generation_progress(
        self,
        sections_completed: int,
        total_sections: int,
        format_type: str
    ) -> None:
        """
        Emit report generation progress.
        
        Args:
            sections_completed: Report sections completed.
            total_sections: Total sections to generate.
            format_type: Report format being generated.
        """
        metadata = {
            "sections_completed": sections_completed,
            "total_sections": total_sections,
            "format_type": format_type,
            "generation_percentage": int((sections_completed / total_sections) * 100)
        }
        
        await self._emit_update(
            self.REPORT_GENERATION_PROGRESS,
            self._create_update(
                status="processing",
                message=f"Generating {format_type} report",
                metadata=metadata
            )
        )
    
    async def emit_analysis_completed(
        self,
        report_id: str,
        total_deficiencies: int,
        summary_stats: Dict[str, int]
    ) -> None:
        """
        Emit analysis completed event.
        
        Args:
            report_id: Generated report ID.
            total_deficiencies: Total deficiencies found.
            summary_stats: Summary statistics.
        """
        metadata = {
            "report_id": report_id,
            "total_deficiencies": total_deficiencies,
            "summary_stats": summary_stats,
            "completion_time": datetime.utcnow().isoformat()
        }
        
        await self._emit_update(
            self.ANALYSIS_COMPLETED,
            self._create_update(
                status="completed",
                message="Deficiency analysis completed successfully",
                metadata=metadata
            )
        )
    
    async def emit_analysis_failed(
        self,
        error_message: str,
        error_stage: str,
        partial_results: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Emit analysis failed event.
        
        Args:
            error_message: Error description.
            error_stage: Stage where failure occurred.
            partial_results: Any partial results available.
        """
        metadata = {
            "error_stage": error_stage,
            "partial_results": partial_results,
            "failure_time": datetime.utcnow().isoformat()
        }
        
        await self._emit_update(
            self.ANALYSIS_FAILED,
            self._create_update(
                status="failed",
                message=f"Analysis failed: {error_message}",
                metadata=metadata
            )
        )
    
    def _create_update(
        self,
        status: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Helper to create progress update with current state."""
        from .websocket_progress import ProgressUpdate
        
        return ProgressUpdate(
            task_name=self.task_name,
            current_step=self.current_step,
            total_steps=self.total_steps,
            percentage=self.percentage,
            status=status,
            message=message,
            metadata=metadata or {}
        )


async def emit_deficiency_event(
    event_type: str,
    case_id: str,
    data: Dict[str, Any]
) -> None:
    """
    Emit a deficiency-specific WebSocket event.
    
    Convenience function for one-off events.
    
    Args:
        event_type: Type of event to emit.
        case_id: Case ID for room isolation.
        data: Event data to emit.
    """
    try:
        from src.websocket.socket_server import sio
        
        if sio:
            await sio.emit(
                event_type,
                {
                    "case_id": case_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    **data
                },
                room=f"case_{case_id}"
            )
    except Exception as e:
        import logging
        logger = logging.getLogger("clerk_api")
        logger.error(f"Failed to emit deficiency event: {str(e)}")
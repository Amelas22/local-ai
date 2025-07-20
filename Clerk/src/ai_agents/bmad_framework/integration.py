"""
Integration module for BMad framework with existing Clerk systems.

This module provides adapters and utilities to integrate BMad agents
with existing services like case management, PDF processing, and vector storage.
"""

import logging
from typing import Dict, List, Optional, Any, Union
from pathlib import Path

from src.services.case_manager import case_manager
from src.document_processing.pdf_extractor import PDFExtractor
from src.document_processing.rtp_parser import RTPParser
from src.vector_storage.qdrant_store import QdrantVectorStore
from src.models.case_models import CaseContext
from src.models.unified_document_models import UnifiedDocument
from src.websocket.socket_server import sio

from .agent_executor import AgentExecutor, ExecutionContext
from .security import AgentSecurityContext
from .websocket_progress import ProgressTracker
from .exceptions import TaskExecutionError, ValidationError

logger = logging.getLogger("clerk_api")


class ClerkIntegration:
    """
    Integrates BMad framework with existing Clerk systems.
    """

    def __init__(self):
        """Initialize integration with Clerk services."""
        self.case_manager = case_manager
        self.pdf_extractor = PDFExtractor()
        self.rtp_parser = RTPParser()
        self.vector_store = QdrantVectorStore()
        self._service_cache: Dict[str, Any] = {}

    async def validate_case_access(
        self, case_name: str, user_id: str, required_permission: str = "read"
    ) -> bool:
        """
        Validate user has access to case.

        Args:
            case_name: Case name to validate.
            user_id: User ID requesting access.
            required_permission: Required permission level.

        Returns:
            True if access granted, False otherwise.
        """
        try:
            # Get case by name
            case = await self.case_manager.get_case_by_name(case_name)
            if not case:
                logger.warning(f"Case not found: {case_name}")
                return False

            # Validate access
            return await self.case_manager.validate_case_access(
                case_id=case.id,
                user_id=user_id,
                required_permission=required_permission,
            )
        except Exception as e:
            logger.error(f"Error validating case access: {str(e)}")
            return False

    async def process_pdf_document(
        self,
        file_path: Union[str, Path],
        case_name: str,
        progress_tracker: Optional[ProgressTracker] = None,
    ) -> Dict[str, Any]:
        """
        Process PDF document using existing PDF extractor.

        Args:
            file_path: Path to PDF file.
            case_name: Case name for isolation.
            progress_tracker: Optional progress tracker.

        Returns:
            Extracted document data.
        """
        try:
            file_path = Path(file_path)

            if progress_tracker:
                await progress_tracker.emit_progress(
                    message=f"Processing PDF: {file_path.name}"
                )

            # Extract text
            extracted_data = self.pdf_extractor.extract_text_from_pdf(str(file_path))

            # Add case isolation
            extracted_data["case_name"] = case_name

            if progress_tracker:
                await progress_tracker.emit_progress(
                    message=f"Extracted {len(extracted_data.get('pages', []))} pages"
                )

            return extracted_data

        except Exception as e:
            raise TaskExecutionError("process_pdf", f"PDF processing failed: {str(e)}")

    async def parse_rtp_document(
        self,
        file_path: Union[str, Path],
        case_name: str,
        progress_tracker: Optional[ProgressTracker] = None,
    ) -> List[Dict[str, Any]]:
        """
        Parse RTP document using existing RTP parser.

        Args:
            file_path: Path to RTP PDF file.
            case_name: Case name for isolation.
            progress_tracker: Optional progress tracker.

        Returns:
            List of parsed RTP requests.
        """
        try:
            if progress_tracker:
                await progress_tracker.emit_progress(message="Parsing RTP document")

            # Use RTP parser
            requests = self.rtp_parser.parse_rtp_document(str(file_path))

            # Convert to dict format and add case
            parsed_requests = []
            for req in requests:
                parsed_requests.append(
                    {
                        "request_number": req.request_number,
                        "request_text": req.request_text,
                        "category": req.category.value,
                        "page_range": req.page_range,
                        "confidence_score": req.confidence_score,
                        "case_name": case_name,
                    }
                )

            if progress_tracker:
                await progress_tracker.emit_progress(
                    message=f"Parsed {len(parsed_requests)} requests"
                )

            return parsed_requests

        except Exception as e:
            raise TaskExecutionError("parse_rtp", f"RTP parsing failed: {str(e)}")

    async def search_vector_store(
        self,
        case_name: str,
        query: str,
        limit: int = 50,
        vector_weight: float = 0.7,
        text_weight: float = 0.3,
        progress_tracker: Optional[ProgressTracker] = None,
    ) -> List[UnifiedDocument]:
        """
        Search vector store using existing Qdrant integration.

        Args:
            case_name: Case name for isolation.
            query: Search query.
            limit: Maximum results.
            vector_weight: Weight for vector similarity.
            text_weight: Weight for text search.
            progress_tracker: Optional progress tracker.

        Returns:
            List of matching documents.
        """
        try:
            if progress_tracker:
                await progress_tracker.emit_progress(message="Searching vector store")

            # Perform hybrid search
            results = await self.vector_store.hybrid_search(
                case_name=case_name,
                query_text=query,
                limit=limit,
                vector_weight=vector_weight,
                text_weight=text_weight,
            )

            if progress_tracker:
                await progress_tracker.emit_progress(
                    message=f"Found {len(results)} matching documents"
                )

            return results

        except Exception as e:
            raise TaskExecutionError("vector_search", f"Vector search failed: {str(e)}")

    async def save_document(
        self, document: Dict[str, Any], case_name: str, document_type: str = "generated"
    ) -> str:
        """
        Save document to case storage.

        Args:
            document: Document data.
            case_name: Case name.
            document_type: Type of document.

        Returns:
            Document ID.
        """
        try:
            # Get case
            case = await self.case_manager.get_case_by_name(case_name)
            if not case:
                raise ValidationError("Case", f"Case not found: {case_name}")

            # Create document metadata
            metadata = {
                "case_id": case.id,
                "case_name": case_name,
                "document_type": document_type,
                "created_by": "bmad_agent",
                **document.get("metadata", {}),
            }

            # In real implementation, save to Box or database
            # For now, return mock ID
            document_id = f"doc_{case.id}_{document_type}_{len(metadata)}"

            logger.info(f"Saved document {document_id} to case {case_name}")

            return document_id

        except Exception as e:
            raise TaskExecutionError("save_document", f"Document save failed: {str(e)}")

    def create_agent_executor_with_integration(
        self, agent_id: str, security_context: AgentSecurityContext
    ) -> AgentExecutor:
        """
        Create agent executor with Clerk integration.

        Args:
            agent_id: Agent ID to execute.
            security_context: Security context.

        Returns:
            Configured agent executor.
        """
        executor = AgentExecutor()

        # Register integration handlers
        executor.register_command_handler(
            "search_case_documents", lambda ctx: self._handle_search_command(ctx)
        )

        executor.register_command_handler(
            "parse_rtp", lambda ctx: self._handle_parse_rtp_command(ctx)
        )

        executor.register_command_handler(
            "save_generated_document",
            lambda ctx: self._handle_save_document_command(ctx),
        )

        return executor

    async def _handle_search_command(self, context: ExecutionContext) -> Any:
        """Handle search command with integration."""
        query = context.parameters.get("query", "")
        limit = context.parameters.get("limit", 50)

        return await self.search_vector_store(
            case_name=context.case_name, query=query, limit=limit
        )

    async def _handle_parse_rtp_command(self, context: ExecutionContext) -> Any:
        """Handle RTP parsing command."""
        file_path = context.parameters.get("file_path")
        if not file_path:
            raise ValidationError("Parameter", "file_path is required")

        return await self.parse_rtp_document(
            file_path=file_path, case_name=context.case_name
        )

    async def _handle_save_document_command(self, context: ExecutionContext) -> Any:
        """Handle document save command."""
        document = context.parameters.get("document", {})
        document_type = context.parameters.get("document_type", "generated")

        return await self.save_document(
            document=document, case_name=context.case_name, document_type=document_type
        )

    async def emit_case_event(
        self, case_id: str, event_type: str, data: Dict[str, Any]
    ) -> None:
        """
        Emit WebSocket event for case.

        Args:
            case_id: Case ID.
            event_type: Event type.
            data: Event data.
        """
        try:
            await sio.emit(event_type, data, room=f"case_{case_id}")
        except Exception as e:
            logger.error(f"Failed to emit case event: {str(e)}")

    async def get_case_context(
        self, case_name: str, user_id: str
    ) -> Optional[CaseContext]:
        """
        Get case context for agent execution.

        Args:
            case_name: Case name.
            user_id: User ID.

        Returns:
            Case context if available.
        """
        try:
            case = await self.case_manager.get_case_by_name(case_name)
            if not case:
                return None

            # Build case context
            permissions = await self.case_manager.get_user_permissions(
                user_id=user_id, case_id=case.id
            )

            return CaseContext(
                case_id=case.id,
                case_name=case.name,
                law_firm_id=case.law_firm_id,
                user_id=user_id,
                permissions=permissions,
            )

        except Exception as e:
            logger.error(f"Error getting case context: {str(e)}")
            return None


# Singleton instance
clerk_integration = ClerkIntegration()

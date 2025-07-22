"""
Service wrapper for Good Faith Letter BMad agent.
"""

from typing import Dict, Any, List, Optional
from uuid import UUID
from datetime import datetime
from contextlib import asynccontextmanager

from src.ai_agents.bmad_framework import AgentLoader, AgentExecutor
from src.ai_agents.bmad_framework.security import AgentSecurityContext
from src.ai_agents.bmad_framework.websocket_progress import emit_progress_update as emit_agent_event
from src.models.deficiency_models import GeneratedLetter, LetterStatus
from src.services.letter_template_service import LetterTemplateService
from src.services.letter_export_service import LetterExportService
from src.utils.logger import get_logger
from src.utils.audit_logger import letter_audit_logger
from src.database.letter_repository import LetterRepository
from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger("good_faith_letter_service")


class GoodFaithLetterAgentService:
    """Service to execute Good Faith Letter agent commands."""

    def __init__(self, db_session: Optional[AsyncSession] = None):
        """
        Initialize service.

        Args:
            db_session: Optional database session for testing
        """
        self.agent_loader = AgentLoader()
        self.agent_executor = AgentExecutor()
        self.agent_id = "good-faith-letter"
        self.template_service = LetterTemplateService()
        self.export_service = LetterExportService()
        self._db_session = db_session

    @asynccontextmanager
    async def _get_db_session(self):
        """
        Get database session as async context manager.

        Yields:
            AsyncSession: Database session
        """
        if self._db_session:
            yield self._db_session
        else:
            # Create a new session using the factory
            from src.database.connection import AsyncSessionLocal

            async with AsyncSessionLocal() as session:
                yield session

    async def generate_letter(
        self, parameters: Dict[str, Any], security_context: AgentSecurityContext
    ) -> GeneratedLetter:
        """
        Generate letter using BMad agent.

        Args:
            parameters: Generation parameters including report_id, jurisdiction, etc.
            security_context: Security context with case isolation

        Returns:
            GeneratedLetter: Generated letter with agent tracking
        """
        try:
            # Load agent definition
            agent_def = await self.agent_loader.load_agent(self.agent_id)

            # Execute generate-letter command
            result = await self.agent_executor.execute_command(
                agent_def=agent_def,
                command="generate-letter",
                case_name=security_context.case_name,
                security_context=security_context,
                parameters=parameters,
            )

            # Create GeneratedLetter from result
            letter = GeneratedLetter(
                report_id=UUID(parameters["report_id"]),
                case_name=security_context.case_name,
                jurisdiction=parameters["jurisdiction"],
                content=result.output.get("content", ""),
                status=LetterStatus.DRAFT,
                agent_execution_id=result.execution_id,
                metadata=result.output.get("metadata", {}),
            )

            # Store letter in database
            async with self._get_db_session() as session:
                repository = LetterRepository(session)
                letter = await repository.create_letter(letter)

            logger.info(
                f"Generated letter {letter.id} for case {security_context.case_name}"
            )

            # Audit log the generation
            letter_audit_logger.log_letter_generation(
                letter_id=str(letter.id),
                case_name=security_context.case_name,
                user_id=security_context.user_id,
                report_id=parameters["report_id"],
                jurisdiction=parameters["jurisdiction"],
                metadata={
                    "agent_execution_id": result.execution_id,
                    "include_evidence": parameters.get("include_evidence", True),
                },
            )

            return letter

        except Exception as e:
            logger.error(f"Letter generation failed: {str(e)}")

            # Audit log the failure
            letter_audit_logger.log_error(
                operation="generate_letter",
                error_message=str(e),
                user_id=security_context.user_id,
            )

            raise

    async def get_letter(
        self, letter_id: UUID, security_context: AgentSecurityContext
    ) -> Optional[GeneratedLetter]:
        """
        Get letter with security validation.

        Args:
            letter_id: Letter ID
            security_context: Security context

        Returns:
            GeneratedLetter if found and accessible
        """
        async with self._get_db_session() as session:
            repository = LetterRepository(session)
            letter = await repository.get_letter(letter_id, security_context.case_name)

        return letter

    async def finalize_letter(
        self, letter_id: UUID, approved_by: str, security_context: AgentSecurityContext
    ) -> GeneratedLetter:
        """
        Finalize letter for sending.

        Args:
            letter_id: Letter to finalize
            approved_by: User approving the letter
            security_context: Security context

        Returns:
            Updated GeneratedLetter
        """
        async with self._get_db_session() as session:
            repository = LetterRepository(session)
            letter = await repository.get_letter(letter_id, security_context.case_name)

            if not letter:
                raise ValueError(f"Letter {letter_id} not found")

            if letter.status == LetterStatus.FINALIZED:
                raise ValueError("Letter already finalized")

            # Update letter status
            old_status = letter.status
            letter.status = LetterStatus.FINALIZED
            letter.approved_by = approved_by
            letter.approved_at = datetime.utcnow()
            letter.updated_at = datetime.utcnow()

            # Save updated letter
            letter = await repository.update_letter(letter)

            # Emit finalization event
            await emit_agent_event(
                case_id=security_context.case_id,
                agent_id=self.agent_id,
                task_name="finalize_letter",
                message=f"Letter finalized by {approved_by}",
                percentage=100,
                status="completed",
                metadata={
                    "letter_id": str(letter_id),
                    "old_status": old_status,
                    "new_status": LetterStatus.FINALIZED,
                    "approved_by": approved_by,
                },
            )

            logger.info(f"Finalized letter {letter_id}")

            # Audit log the finalization
            letter_audit_logger.log_letter_finalization(
                letter_id=str(letter_id),
                case_name=security_context.case_name,
                finalizer_id=approved_by,
            )

            return letter

    async def export_letter(
        self, letter_id: UUID, format: str, security_context: AgentSecurityContext
    ) -> Dict[str, Any]:
        """
        Export letter using export service.

        Args:
            letter_id: Letter to export
            format: Export format (pdf, docx, html)
            security_context: Security context

        Returns:
            Export data with content
        """
        async with self._get_db_session() as session:
            repository = LetterRepository(session)
            letter = await repository.get_letter(letter_id, security_context.case_name)

        if not letter:
            raise ValueError(f"Letter {letter_id} not found")

        # Use export service based on format
        try:
            if format == "pdf":
                content = await self.export_service.export_to_pdf(letter)
            elif format == "docx":
                content = await self.export_service.export_to_docx(letter)
            elif format == "html":
                content = await self.export_service.export_to_html(letter)
            else:
                raise ValueError(f"Unsupported export format: {format}")

            # Emit export event
            await emit_agent_event(
                case_id=security_context.case_id,
                agent_id=self.agent_id,
                task_name="export_letter",
                message=f"Letter exported as {format}",
                percentage=100,
                status="completed",
                metadata={
                    "letter_id": str(letter_id),
                    "format": format,
                    "case_name": security_context.case_name,
                },
            )

            logger.info(f"Exported letter {letter_id} as {format}")

            # Calculate file size for audit
            file_content = content if isinstance(content, bytes) else content.encode()
            file_size = len(file_content)

            # Audit log the export
            letter_audit_logger.log_letter_export(
                letter_id=str(letter_id),
                case_name=security_context.case_name,
                user_id=security_context.user_id,
                export_format=format,
                file_size=file_size,
            )

            return {
                "content": file_content,
                "format": format,
                "filename": f"good-faith-letter-{letter.case_name}-{letter_id}.{format}",
            }

        except Exception as e:
            logger.error(f"Letter export failed: {str(e)}")

            # Audit log the failure
            letter_audit_logger.log_error(
                operation="export_letter",
                error_message=str(e),
                user_id=security_context.user_id,
                letter_id=str(letter_id),
            )

            raise

    async def list_templates(self) -> List[Dict[str, Any]]:
        """
        List available letter templates.

        Returns:
            List of template metadata
        """
        # Get templates from template service
        federal_meta = await self.template_service.get_template_requirements("federal")
        state_meta = await self.template_service.get_template_requirements("state")

        templates = []

        if federal_meta:
            templates.append(
                {
                    "id": "good-faith-letter-federal",
                    "jurisdiction": "federal",
                    "title": "Federal Good Faith Letter",
                    "description": "FRCP Rule 37 compliant letter template",
                    "required_variables": federal_meta.get("required_variables", []),
                }
            )

        if state_meta:
            templates.append(
                {
                    "id": "good-faith-letter-state",
                    "jurisdiction": "state",
                    "title": "State Good Faith Letter",
                    "description": "State-specific discovery deficiency letter",
                    "required_variables": state_meta.get("required_variables", []),
                }
            )

        return templates

    async def list_letters_by_report(
        self,
        report_id: UUID,
        security_context: AgentSecurityContext,
        status: Optional[str] = None,
    ) -> List[GeneratedLetter]:
        """
        List all letters for a deficiency report.

        Args:
            report_id: DeficiencyReport ID
            security_context: Security context
            status: Optional status filter

        Returns:
            List[GeneratedLetter]: Letters for the report
        """
        async with self._get_db_session() as session:
            repository = LetterRepository(session)
            letters = await repository.list_letters_by_report(
                report_id, security_context.case_name, status
            )

        return letters

    async def list_letters_by_case(
        self,
        security_context: AgentSecurityContext,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[GeneratedLetter]:
        """
        List all letters for a case with pagination.

        Args:
            security_context: Security context
            status: Optional status filter
            limit: Maximum results
            offset: Results offset

        Returns:
            List[GeneratedLetter]: Letters for the case
        """
        async with self._get_db_session() as session:
            repository = LetterRepository(session)
            letters = await repository.list_letters_by_case(
                security_context.case_name, status, limit, offset
            )

        return letters

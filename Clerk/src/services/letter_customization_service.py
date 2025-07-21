"""
Service for managing Good Faith letter customizations and edits.
"""

from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime

from src.models.deficiency_models import GeneratedLetter, LetterEdit, LetterStatus
from src.utils.logger import get_logger
from src.utils.audit_logger import letter_audit_logger
from src.ai_agents.bmad_framework.websocket_progress import emit_progress_update as emit_agent_event
from src.database.connection import AsyncSessionLocal
from contextlib import asynccontextmanager

logger = get_logger("letter_customization_service")


class LetterCustomizationService:
    """
    Handles letter customization, versioning, and approval workflow.

    Maintains edit history and ensures template compliance during edits.
    """

    def __init__(self, db_session=None):
        """
        Initialize service.

        Args:
            db_session: Optional database session for testing
        """
        self._db_session = db_session
        # TODO: Remove this in-memory storage once all methods are updated
        # to use database with proper case isolation
        self._letter_storage: Dict[UUID, GeneratedLetter] = {}

    @asynccontextmanager
    async def _get_db_session(self):
        """Get database session as async context manager."""
        if self._db_session:
            yield self._db_session
        else:
            async with AsyncSessionLocal() as session:
                yield session

    async def apply_edits(
        self,
        letter_id: UUID,
        section_edits: List[Dict[str, str]],
        editor_id: str,
        editor_notes: Optional[str] = None,
    ) -> GeneratedLetter:
        """
        Apply edits to a letter and track changes.

        Args:
            letter_id: Letter to edit
            section_edits: List of section edits with 'section' and 'content'
            editor_id: User making the edits
            editor_notes: Optional notes about the edits

        Returns:
            Updated GeneratedLetter with new version

        Raises:
            ValueError: If letter not found or not editable
        """
        letter = self._get_letter(letter_id)

        if not letter:
            raise ValueError(f"Letter {letter_id} not found")

        if letter.status not in [LetterStatus.DRAFT, LetterStatus.REVIEW]:
            raise ValueError(f"Letter cannot be edited in {letter.status} status")

        # Parse current content into sections
        current_sections = self._parse_letter_sections(letter.content)

        # Track edits
        edit_records = []

        for edit in section_edits:
            section_name = edit.get("section")
            new_content = edit.get("content")

            if not section_name or new_content is None:
                logger.warning(f"Invalid edit format: {edit}")
                continue

            # Get original content
            original_content = current_sections.get(section_name, "")

            # Create edit record
            edit_record = LetterEdit(
                section_name=section_name,
                original_content=original_content,
                new_content=new_content,
                editor_id=editor_id,
                editor_notes=editor_notes,
            )

            edit_records.append(edit_record)

            # Apply edit
            current_sections[section_name] = new_content

            logger.info(f"Applied edit to section '{section_name}' by {editor_id}")

        # Reconstruct letter content
        updated_content = self._reconstruct_letter(current_sections)

        # Validate against template requirements
        validation_result = await self._validate_content(
            updated_content, letter.jurisdiction
        )

        if not validation_result["valid"]:
            logger.warning(
                f"Content validation warnings: {validation_result['warnings']}"
            )

        # Update letter
        letter.content = updated_content
        letter.version += 1
        letter.updated_at = datetime.utcnow()
        letter.edit_history.extend(edit_records)

        # Update status if in draft
        if letter.status == LetterStatus.DRAFT and len(edit_records) > 0:
            letter.status = LetterStatus.REVIEW

        # Emit WebSocket event
        await emit_agent_event(
            event_type="letter:edited",
            agent_id="good-faith-letter",
            data={
                "letter_id": str(letter_id),
                "version": letter.version,
                "edits_applied": len(edit_records),
                "editor": editor_id,
            },
        )

        logger.info(f"Letter {letter_id} updated to version {letter.version}")

        # Audit log the edits
        if edit_records:
            letter_audit_logger.log_letter_edit(
                letter_id=str(letter_id),
                case_name=letter.case_name,
                editor_id=editor_id,
                version_before=letter.version - 1,
                version_after=letter.version,
                sections_modified=[e.section_name for e in edit_records],
                edit_notes=editor_notes,
            )

        return letter

    async def approve_letter(
        self, letter_id: UUID, approver_id: str, approval_notes: Optional[str] = None
    ) -> GeneratedLetter:
        """
        Approve a letter for finalization.

        Args:
            letter_id: Letter to approve
            approver_id: User approving the letter
            approval_notes: Optional approval notes

        Returns:
            Approved GeneratedLetter
        """
        letter = self._get_letter(letter_id)

        if not letter:
            raise ValueError(f"Letter {letter_id} not found")

        if letter.status != LetterStatus.REVIEW:
            raise ValueError(
                f"Letter must be in REVIEW status to approve, currently {letter.status}"
            )

        # Update status
        letter.status = LetterStatus.APPROVED
        letter.approved_by = approver_id
        letter.approved_at = datetime.utcnow()
        letter.updated_at = datetime.utcnow()

        # Add approval to metadata
        letter.metadata["approval"] = {
            "approver": approver_id,
            "timestamp": letter.approved_at.isoformat(),
            "notes": approval_notes,
        }

        # Emit event
        await emit_agent_event(
            event_type="letter:approved",
            agent_id="good-faith-letter",
            data={"letter_id": str(letter_id), "approver": approver_id},
        )

        logger.info(f"Letter {letter_id} approved by {approver_id}")

        # Audit log the approval
        letter_audit_logger.log_letter_approval(
            letter_id=str(letter_id),
            case_name=letter.case_name,
            approver_id=approver_id,
            approval_notes=approval_notes,
        )

        return letter

    async def revert_to_version(
        self, letter_id: UUID, version: int, reverter_id: str, reason: str
    ) -> GeneratedLetter:
        """
        Revert letter to a previous version.

        Args:
            letter_id: Letter to revert
            version: Version number to revert to
            reverter_id: User performing reversion
            reason: Reason for reversion

        Returns:
            Reverted GeneratedLetter
        """
        letter = self._get_letter(letter_id)

        if not letter:
            raise ValueError(f"Letter {letter_id} not found")

        if version >= letter.version:
            raise ValueError(
                f"Cannot revert to version {version}, current version is {letter.version}"
            )

        if letter.status == LetterStatus.FINALIZED:
            raise ValueError("Cannot revert finalized letter")

        # Find edits to reverse
        edits_to_reverse = [
            edit
            for edit in letter.edit_history
            if self._get_edit_version(edit, letter.edit_history) > version
        ]

        # Reverse edits in reverse chronological order
        current_sections = self._parse_letter_sections(letter.content)

        for edit in reversed(edits_to_reverse):
            current_sections[edit.section_name] = edit.original_content

        # Create reversion edit
        reversion_edit = LetterEdit(
            section_name="[FULL_LETTER]",
            original_content=letter.content,
            new_content=self._reconstruct_letter(current_sections),
            editor_id=reverter_id,
            editor_notes=f"Reverted to version {version}: {reason}",
        )

        # Update letter
        letter.content = reversion_edit.new_content
        letter.version += 1
        letter.updated_at = datetime.utcnow()
        letter.edit_history.append(reversion_edit)
        letter.status = LetterStatus.REVIEW

        # Clear approval if exists
        letter.approved_by = None
        letter.approved_at = None

        logger.info(
            f"Letter {letter_id} reverted from v{letter.version - 1} to v{version} content"
        )

        return letter

    def get_edit_history(
        self, letter_id: UUID, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get edit history for a letter.

        Args:
            letter_id: Letter ID
            limit: Maximum edits to return

        Returns:
            List of edit summaries
        """
        letter = self._get_letter(letter_id)

        if not letter:
            return []

        history = []
        edits = letter.edit_history[-limit:] if limit else letter.edit_history

        for idx, edit in enumerate(edits):
            history.append(
                {
                    "edit_number": idx + 1,
                    "section": edit.section_name,
                    "editor": edit.editor_id,
                    "timestamp": edit.edited_at.isoformat(),
                    "notes": edit.editor_notes,
                    "content_changed": len(edit.new_content)
                    != len(edit.original_content),
                }
            )

        return history

    async def _validate_content(
        self, content: str, jurisdiction: str
    ) -> Dict[str, Any]:
        """
        Validate letter content against requirements.

        Args:
            content: Letter content
            jurisdiction: federal or state

        Returns:
            Validation result with warnings
        """
        warnings = []

        # Check for required elements based on jurisdiction
        if jurisdiction == "federal":
            if "Rule 37" not in content and "FRCP" not in content:
                warnings.append("Missing Rule 37 reference")
            if "meet and confer" not in content.lower():
                warnings.append("Missing meet and confer language")

        # Check professional tone
        avoid_phrases = ["you failed", "your refusal", "bad faith", "frivolous"]

        content_lower = content.lower()
        for phrase in avoid_phrases:
            if phrase in content_lower:
                warnings.append(f"Unprofessional phrase detected: '{phrase}'")

        # Check structure
        if "Dear" not in content:
            warnings.append("Missing salutation")
        if "Sincerely" not in content and "Respectfully" not in content:
            warnings.append("Missing professional closing")

        return {"valid": len(warnings) == 0, "warnings": warnings}

    def _parse_letter_sections(self, content: str) -> Dict[str, str]:
        """
        Parse letter content into sections.

        Identifies sections based on template markers and headers.
        """
        import re

        sections = {}

        # Common section markers in legal letters
        section_patterns = [
            (
                r"(Dear\s+[\w\s,\.]+:.*?)(?=\n\n[A-Z]|\n\n\s*Sincerely|$)",
                "salutation",
                re.DOTALL,
            ),
            (r"(RE:.*?)\n", "subject_line", 0),
            (r"(\n\s*DEFICIENCIES.*?)(?=\n\s*[A-Z]{2,}:|$)", "deficiencies", re.DOTALL),
            (r"(\n\s*CONCLUSION.*?)(?=\n\s*Sincerely|$)", "conclusion", re.DOTALL),
            (r"(Sincerely,.*?$)", "closing", re.DOTALL),
        ]

        # Extract sections based on patterns
        for pattern, section_name, flags in section_patterns:
            match = re.search(pattern, content, flags)
            if match:
                sections[section_name] = match.group(1).strip()

        # Store any unmatched content as body
        matched_content = "".join(sections.values())
        if len(content) > len(matched_content):
            sections["body"] = content

        # Fallback to full content if no sections identified
        if not sections:
            sections["full_content"] = content

        return sections

    def _reconstruct_letter(self, sections: Dict[str, str]) -> str:
        """
        Reconstruct letter from sections.

        Maintains proper order and formatting for legal letters.
        """
        # If full_content section exists, it means no sections were parsed
        if "full_content" in sections:
            return sections["full_content"]

        # Reconstruct in proper order for legal letters
        parts = []

        # Add salutation if exists
        if "salutation" in sections:
            parts.append(sections["salutation"])

        # Add subject line
        if "subject_line" in sections:
            parts.append(sections["subject_line"])

        # Add body content (everything else except specific sections)
        if "body" in sections:
            # Extract body without already handled sections
            body_content = sections["body"]

            # Remove sections we'll add separately
            for section_name in [
                "salutation",
                "subject_line",
                "deficiencies",
                "conclusion",
                "closing",
            ]:
                if section_name in sections and sections[section_name] in body_content:
                    body_content = body_content.replace(
                        sections[section_name], ""
                    ).strip()

            if body_content:
                parts.append(body_content)

        # Add deficiencies section
        if "deficiencies" in sections:
            parts.append(sections["deficiencies"])

        # Add conclusion
        if "conclusion" in sections:
            parts.append(sections["conclusion"])

        # Add closing
        if "closing" in sections:
            parts.append(sections["closing"])

        # Join with appropriate spacing
        return "\n\n".join(filter(None, parts))

    def _get_letter(self, letter_id: UUID) -> Optional[GeneratedLetter]:
        """
        Get letter from storage.

        TODO: This method needs to be updated to use the database repository
        with proper case isolation. Currently using in-memory storage for
        backwards compatibility.
        """
        # In production, fetch from database with case_name parameter
        return getattr(self, "_letter_storage", {}).get(letter_id)

    def _get_edit_version(self, edit: LetterEdit, all_edits: List[LetterEdit]) -> int:
        """Determine which version an edit belongs to."""
        # Simple implementation - count edits before this one
        edit_index = all_edits.index(edit)
        return edit_index + 1

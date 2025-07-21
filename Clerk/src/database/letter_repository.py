"""
Repository for Good Faith Letter database operations.

Provides async database operations for letter persistence with
proper case isolation and audit trail.
"""

from typing import List, Optional
from uuid import UUID
from datetime import datetime
from sqlalchemy import select, and_, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.database.letter_models import GeneratedLetterDB, LetterEditDB
from src.models.deficiency_models import GeneratedLetter, LetterEdit
from src.utils.logger import get_logger

logger = get_logger("letter_repository")


class LetterRepository:
    """Repository for letter database operations."""

    def __init__(self, session: AsyncSession):
        """
        Initialize repository with database session.

        Args:
            session: AsyncSession for database operations
        """
        self.session = session

    async def create_letter(self, letter: GeneratedLetter) -> GeneratedLetter:
        """
        Create a new letter in the database.

        Args:
            letter: GeneratedLetter to persist

        Returns:
            GeneratedLetter: Created letter with database-generated fields
        """
        db_letter = GeneratedLetterDB(
            id=str(letter.id),
            report_id=str(letter.report_id),
            case_name=letter.case_name,
            jurisdiction=letter.jurisdiction,
            content=letter.content,
            status=letter.status,
            version=letter.version,
            agent_execution_id=letter.agent_execution_id,
            letter_metadata=letter.metadata,
            created_at=letter.created_at,
            updated_at=letter.updated_at,
            approved_by=letter.approved_by,
            approved_at=letter.approved_at,
        )

        self.session.add(db_letter)
        await self.session.commit()
        await self.session.refresh(db_letter)

        logger.info(f"Created letter {db_letter.id} for case {db_letter.case_name}")

        return self._db_to_model(db_letter)

    async def get_letter(
        self, letter_id: UUID, case_name: str
    ) -> Optional[GeneratedLetter]:
        """
        Get a letter by ID with case isolation.

        Args:
            letter_id: Letter ID
            case_name: Case name for isolation

        Returns:
            GeneratedLetter if found and accessible, None otherwise
        """
        result = await self.session.execute(
            select(GeneratedLetterDB)
            .where(
                and_(
                    GeneratedLetterDB.id == str(letter_id),
                    GeneratedLetterDB.case_name == case_name,
                )
            )
            .options(selectinload(GeneratedLetterDB.edits))
        )

        db_letter = result.scalar_one_or_none()

        if db_letter:
            logger.info(f"Retrieved letter {letter_id} for case {case_name}")
            return self._db_to_model(db_letter)

        logger.warning(f"Letter {letter_id} not found for case {case_name}")
        return None

    async def update_letter(self, letter: GeneratedLetter) -> GeneratedLetter:
        """
        Update an existing letter.

        Args:
            letter: GeneratedLetter with updates

        Returns:
            GeneratedLetter: Updated letter
        """
        stmt = (
            update(GeneratedLetterDB)
            .where(
                and_(
                    GeneratedLetterDB.id == str(letter.id),
                    GeneratedLetterDB.case_name == letter.case_name,
                )
            )
            .values(
                content=letter.content,
                status=letter.status,
                version=letter.version,
                updated_at=datetime.utcnow(),
                approved_by=letter.approved_by,
                approved_at=letter.approved_at,
                letter_metadata=letter.metadata,
            )
        )

        await self.session.execute(stmt)
        await self.session.commit()

        logger.info(f"Updated letter {letter.id} to version {letter.version}")

        # Retrieve updated letter
        return await self.get_letter(letter.id, letter.case_name)

    async def add_edit(self, letter_id: UUID, edit: LetterEdit, case_name: str) -> bool:
        """
        Add an edit record to a letter.

        Args:
            letter_id: Letter ID
            edit: LetterEdit to add
            case_name: Case name for validation

        Returns:
            bool: True if edit added successfully
        """
        # Verify letter exists and belongs to case
        letter = await self.get_letter(letter_id, case_name)
        if not letter:
            logger.error(
                f"Cannot add edit - letter {letter_id} not found for case {case_name}"
            )
            return False

        db_edit = LetterEditDB(
            id=str(edit.id),
            letter_id=str(letter_id),
            section_name=edit.section_name,
            original_content=edit.original_content,
            new_content=edit.new_content,
            editor_id=edit.editor_id,
            editor_notes=edit.editor_notes,
            edited_at=edit.edited_at,
        )

        self.session.add(db_edit)
        await self.session.commit()

        logger.info(f"Added edit to letter {letter_id} by {edit.editor_id}")
        return True

    async def list_letters_by_report(
        self, report_id: UUID, case_name: str, status: Optional[str] = None
    ) -> List[GeneratedLetter]:
        """
        List all letters for a deficiency report.

        Args:
            report_id: DeficiencyReport ID
            case_name: Case name for isolation
            status: Optional status filter

        Returns:
            List[GeneratedLetter]: Letters for the report
        """
        query = select(GeneratedLetterDB).where(
            and_(
                GeneratedLetterDB.report_id == str(report_id),
                GeneratedLetterDB.case_name == case_name,
            )
        )

        if status:
            query = query.where(GeneratedLetterDB.status == status)

        query = query.order_by(GeneratedLetterDB.created_at.desc())

        result = await self.session.execute(query)
        db_letters = result.scalars().all()

        logger.info(f"Found {len(db_letters)} letters for report {report_id}")

        return [self._db_to_model(db_letter) for db_letter in db_letters]

    async def list_letters_by_case(
        self,
        case_name: str,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[GeneratedLetter]:
        """
        List all letters for a case with pagination.

        Args:
            case_name: Case name
            status: Optional status filter
            limit: Maximum results
            offset: Results offset

        Returns:
            List[GeneratedLetter]: Letters for the case
        """
        query = select(GeneratedLetterDB).where(
            GeneratedLetterDB.case_name == case_name
        )

        if status:
            query = query.where(GeneratedLetterDB.status == status)

        query = query.order_by(GeneratedLetterDB.created_at.desc())
        query = query.limit(limit).offset(offset)

        result = await self.session.execute(query)
        db_letters = result.scalars().all()

        logger.info(f"Found {len(db_letters)} letters for case {case_name}")

        return [self._db_to_model(db_letter) for db_letter in db_letters]

    async def delete_letter(self, letter_id: UUID, case_name: str) -> bool:
        """
        Delete a letter and its edit history.

        Args:
            letter_id: Letter ID
            case_name: Case name for validation

        Returns:
            bool: True if deleted successfully
        """
        stmt = delete(GeneratedLetterDB).where(
            and_(
                GeneratedLetterDB.id == str(letter_id),
                GeneratedLetterDB.case_name == case_name,
            )
        )

        result = await self.session.execute(stmt)
        await self.session.commit()

        if result.rowcount > 0:
            logger.info(f"Deleted letter {letter_id} from case {case_name}")
            return True

        logger.warning(f"Letter {letter_id} not found for deletion in case {case_name}")
        return False

    def _db_to_model(self, db_letter: GeneratedLetterDB) -> GeneratedLetter:
        """
        Convert database model to Pydantic model.

        Args:
            db_letter: Database letter model

        Returns:
            GeneratedLetter: Pydantic model
        """
        # Convert edits if loaded
        edits = []
        if hasattr(db_letter, "edits") and db_letter.edits:
            edits = [
                LetterEdit(
                    id=UUID(edit.id),
                    section_name=edit.section_name,
                    original_content=edit.original_content,
                    new_content=edit.new_content,
                    editor_id=edit.editor_id,
                    editor_notes=edit.editor_notes,
                    edited_at=edit.edited_at,
                )
                for edit in db_letter.edits
            ]

        return GeneratedLetter(
            id=UUID(db_letter.id),
            report_id=UUID(db_letter.report_id),
            case_name=db_letter.case_name,
            jurisdiction=db_letter.jurisdiction,
            content=db_letter.content,
            status=db_letter.status,
            version=db_letter.version,
            agent_execution_id=db_letter.agent_execution_id,
            created_at=db_letter.created_at,
            updated_at=db_letter.updated_at,
            approved_by=db_letter.approved_by,
            approved_at=db_letter.approved_at,
            edit_history=edits,
            metadata=db_letter.letter_metadata or {},
        )

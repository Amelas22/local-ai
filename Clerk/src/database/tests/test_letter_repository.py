"""
Tests for Letter Repository database operations.
"""
import pytest
from uuid import uuid4, UUID
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from src.database.letter_models import GeneratedLetterDB, LetterEditDB
from src.database.letter_repository import LetterRepository
from src.models.deficiency_models import GeneratedLetter, LetterEdit, LetterStatus
from src.database.connection import Base


class TestLetterRepository:
    """Test suite for letter repository database operations."""
    
    @pytest.fixture
    async def db_session(self):
        """Create test database session."""
        # Use in-memory SQLite for tests
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        
        # Create tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        # Create session
        async_session = async_sessionmaker(engine, class_=AsyncSession)
        
        async with async_session() as session:
            yield session
        
        await engine.dispose()
    
    @pytest.fixture
    def repository(self, db_session):
        """Create repository instance."""
        return LetterRepository(db_session)
    
    @pytest.mark.asyncio
    async def test_create_letter(self, repository, db_session):
        """Test creating a new letter."""
        letter = GeneratedLetter(
            report_id=uuid4(),
            case_name="Test_Case_2024",
            jurisdiction="federal",
            content="Test letter content",
            agent_execution_id="test-exec-123"
        )
        
        result = await repository.create_letter(letter)
        
        # Verify returned letter
        assert result.id == letter.id
        assert result.case_name == "Test_Case_2024"
        assert result.jurisdiction == "federal"
        
        # Verify in database
        stmt = select(GeneratedLetterDB).where(GeneratedLetterDB.id == str(letter.id))
        db_result = await db_session.execute(stmt)
        db_letter = db_result.scalar_one()
        
        assert db_letter is not None
        assert db_letter.case_name == "Test_Case_2024"
        assert db_letter.content == "Test letter content"
    
    @pytest.mark.asyncio
    async def test_get_letter_found(self, repository, db_session):
        """Test retrieving existing letter."""
        # Create letter in database
        letter_id = uuid4()
        db_letter = GeneratedLetterDB(
            id=str(letter_id),
            report_id=str(uuid4()),
            case_name="Test_Case_2024",
            jurisdiction="state",
            content="Existing letter",
            agent_execution_id="exec-456"
        )
        db_session.add(db_letter)
        await db_session.commit()
        
        # Retrieve letter
        result = await repository.get_letter(letter_id, "Test_Case_2024")
        
        assert result is not None
        assert result.id == letter_id
        assert result.content == "Existing letter"
        assert result.jurisdiction == "state"
    
    @pytest.mark.asyncio
    async def test_get_letter_wrong_case(self, repository, db_session):
        """Test case isolation prevents access."""
        # Create letter in database
        letter_id = uuid4()
        db_letter = GeneratedLetterDB(
            id=str(letter_id),
            report_id=str(uuid4()),
            case_name="Other_Case_2024",
            jurisdiction="federal",
            content="Other case letter",
            agent_execution_id="exec-789"
        )
        db_session.add(db_letter)
        await db_session.commit()
        
        # Try to retrieve with different case name
        result = await repository.get_letter(letter_id, "Test_Case_2024")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_update_letter(self, repository, db_session):
        """Test updating letter fields."""
        # Create letter
        letter = GeneratedLetter(
            report_id=uuid4(),
            case_name="Test_Case_2024",
            jurisdiction="federal",
            content="Original content",
            agent_execution_id="exec-original"
        )
        created = await repository.create_letter(letter)
        
        # Update letter
        created.content = "Updated content"
        created.status = LetterStatus.FINALIZED
        created.version = 2
        created.approved_by = "senior.attorney"
        created.approved_at = datetime.utcnow()
        
        updated = await repository.update_letter(created)
        
        assert updated.content == "Updated content"
        assert updated.status == LetterStatus.FINALIZED
        assert updated.version == 2
        assert updated.approved_by == "senior.attorney"
        assert updated.approved_at is not None
        assert updated.updated_at is not None
    
    @pytest.mark.asyncio
    async def test_add_edit(self, repository, db_session):
        """Test adding edit history."""
        # Create letter
        letter = GeneratedLetter(
            report_id=uuid4(),
            case_name="Test_Case_2024",
            jurisdiction="federal",
            content="Original",
            agent_execution_id="exec-edit"
        )
        created = await repository.create_letter(letter)
        
        # Add edit
        edit = LetterEdit(
            section_name="opening",
            original_content="Dear Sir",
            new_content="Dear Counsel",
            editor_id="editor@firm.com",
            editor_notes="More formal greeting"
        )
        
        success = await repository.add_edit(created.id, edit, "Test_Case_2024")
        
        assert success is True
        
        # Verify edit in database
        stmt = select(LetterEditDB).where(LetterEditDB.letter_id == str(created.id))
        result = await db_session.execute(stmt)
        db_edit = result.scalar_one()
        
        assert db_edit.section_name == "opening"
        assert db_edit.new_content == "Dear Counsel"
        assert db_edit.editor_notes == "More formal greeting"
    
    @pytest.mark.asyncio
    async def test_add_edit_wrong_case(self, repository, db_session):
        """Test edit fails with wrong case name."""
        # Create letter
        letter = GeneratedLetter(
            report_id=uuid4(),
            case_name="Test_Case_2024",
            jurisdiction="federal",
            content="Original",
            agent_execution_id="exec-edit-fail"
        )
        created = await repository.create_letter(letter)
        
        # Try to add edit with wrong case name
        edit = LetterEdit(
            section_name="test",
            original_content="old",
            new_content="new",
            editor_id="editor"
        )
        
        success = await repository.add_edit(created.id, edit, "Wrong_Case")
        
        assert success is False
    
    @pytest.mark.asyncio
    async def test_list_letters_by_report(self, repository, db_session):
        """Test listing letters for a report."""
        report_id = uuid4()
        case_name = "Test_Case_2024"
        
        # Create multiple letters for same report
        for i in range(3):
            letter = GeneratedLetter(
                report_id=report_id,
                case_name=case_name,
                jurisdiction="federal",
                content=f"Letter {i}",
                status=LetterStatus.DRAFT if i < 2 else LetterStatus.FINALIZED,
                agent_execution_id=f"exec-{i}"
            )
            await repository.create_letter(letter)
        
        # Create letter for different report
        other_letter = GeneratedLetter(
            report_id=uuid4(),
            case_name=case_name,
            jurisdiction="state",
            content="Other report letter",
            agent_execution_id="exec-other"
        )
        await repository.create_letter(other_letter)
        
        # List all letters for report
        all_letters = await repository.list_letters_by_report(report_id, case_name)
        assert len(all_letters) == 3
        
        # List only draft letters
        draft_letters = await repository.list_letters_by_report(
            report_id, case_name, status=LetterStatus.DRAFT
        )
        assert len(draft_letters) == 2
    
    @pytest.mark.asyncio
    async def test_list_letters_by_case_pagination(self, repository):
        """Test pagination when listing by case."""
        case_name = "Test_Case_2024"
        
        # Create many letters
        for i in range(15):
            letter = GeneratedLetter(
                report_id=uuid4(),
                case_name=case_name,
                jurisdiction="federal" if i % 2 == 0 else "state",
                content=f"Letter {i}",
                agent_execution_id=f"exec-{i}"
            )
            await repository.create_letter(letter)
        
        # Test pagination
        page1 = await repository.list_letters_by_case(case_name, limit=5, offset=0)
        assert len(page1) == 5
        
        page2 = await repository.list_letters_by_case(case_name, limit=5, offset=5)
        assert len(page2) == 5
        
        page3 = await repository.list_letters_by_case(case_name, limit=5, offset=10)
        assert len(page3) == 5
        
        # Verify no overlap
        page1_ids = {l.id for l in page1}
        page2_ids = {l.id for l in page2}
        assert len(page1_ids.intersection(page2_ids)) == 0
    
    @pytest.mark.asyncio
    async def test_delete_letter(self, repository, db_session):
        """Test deleting letter and cascading edits."""
        # Create letter with edits
        letter = GeneratedLetter(
            report_id=uuid4(),
            case_name="Test_Case_2024",
            jurisdiction="federal",
            content="To delete",
            agent_execution_id="exec-delete"
        )
        created = await repository.create_letter(letter)
        
        # Add some edits
        for i in range(2):
            edit = LetterEdit(
                section_name=f"section_{i}",
                original_content="old",
                new_content="new",
                editor_id=f"editor_{i}"
            )
            await repository.add_edit(created.id, edit, "Test_Case_2024")
        
        # Delete letter
        success = await repository.delete_letter(created.id, "Test_Case_2024")
        assert success is True
        
        # Verify letter deleted
        result = await repository.get_letter(created.id, "Test_Case_2024")
        assert result is None
        
        # Verify edits also deleted (cascade)
        stmt = select(LetterEditDB).where(LetterEditDB.letter_id == str(created.id))
        result = await db_session.execute(stmt)
        edits = result.scalars().all()
        assert len(edits) == 0
    
    @pytest.mark.asyncio
    async def test_delete_letter_wrong_case(self, repository):
        """Test delete fails with wrong case name."""
        # Create letter
        letter = GeneratedLetter(
            report_id=uuid4(),
            case_name="Test_Case_2024",
            jurisdiction="federal",
            content="Protected",
            agent_execution_id="exec-protected"
        )
        created = await repository.create_letter(letter)
        
        # Try to delete with wrong case name
        success = await repository.delete_letter(created.id, "Wrong_Case")
        assert success is False
        
        # Verify letter still exists
        result = await repository.get_letter(created.id, "Test_Case_2024")
        assert result is not None
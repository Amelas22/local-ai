"""
Tests for Good Faith Letter Agent Service with database integration.
"""
import pytest
from uuid import uuid4, UUID
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.good_faith_letter_agent_service import GoodFaithLetterAgentService
from src.models.deficiency_models import GeneratedLetter, LetterStatus
from src.ai_agents.bmad_framework.security import AgentSecurityContext
from src.ai_agents.bmad_framework import AgentExecutor


class TestGoodFaithLetterAgentService:
    """Test suite for Good Faith Letter Agent Service."""
    
    @pytest.fixture
    def mock_security_context(self):
        """Mock security context for tests."""
        context = Mock(spec=AgentSecurityContext)
        context.case_id = "test-case-123"
        context.case_name = "Test_Case_2024"
        context.user_id = "test-user"
        return context
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        session = MagicMock(spec=AsyncSession)
        # Make it work as async context manager
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=None)
        return session
    
    @pytest.fixture
    def service(self, mock_db_session):
        """Create service instance with mocked database."""
        return GoodFaithLetterAgentService(db_session=mock_db_session)
    
    @pytest.mark.asyncio
    async def test_generate_letter_success(self, service, mock_security_context, mock_db_session):
        """Test successful letter generation with database persistence."""
        parameters = {
            "report_id": str(uuid4()),
            "jurisdiction": "federal",
            "include_evidence": True,
            "attorney_info": {
                "name": "Jane Smith, Esq.",
                "firm": "Smith & Associates",
                "email": "jane@smithlaw.com"
            }
        }
        
        # Mock agent execution
        with patch.object(service.agent_loader, 'load_agent') as mock_load:
            with patch.object(service.agent_executor, 'execute_command') as mock_exec:
                # Mock execution result
                mock_result = Mock()
                mock_result.output = {
                    "content": "Dear Counsel:\n\nThis is a test letter...",
                    "metadata": {"template_id": "federal-template"}
                }
                mock_result.execution_id = "exec-123"
                
                mock_load.return_value = AsyncMock()
                mock_exec.return_value = mock_result
                
                # Mock repository
                with patch('src.services.good_faith_letter_agent_service.LetterRepository') as mock_repo_class:
                    mock_repo = mock_repo_class.return_value
                    mock_repo.create_letter = AsyncMock(side_effect=lambda x: x)
                    
                    result = await service.generate_letter(parameters, mock_security_context)
                    
                    # Verify letter created
                    assert isinstance(result, GeneratedLetter)
                    assert str(result.report_id) == parameters["report_id"]
                    assert result.case_name == mock_security_context.case_name
                    assert result.jurisdiction == "federal"
                    assert result.status == LetterStatus.DRAFT
                    assert result.agent_execution_id == "exec-123"
                    
                    # Verify database call
                    mock_repo.create_letter.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_letter_failure(self, service, mock_security_context):
        """Test letter generation handles agent execution failure."""
        parameters = {
            "report_id": str(uuid4()),
            "jurisdiction": "federal"
        }
        
        with patch.object(service.agent_executor, 'execute_command') as mock_exec:
            mock_exec.side_effect = Exception("Agent execution failed")
            
            with pytest.raises(Exception) as exc_info:
                await service.generate_letter(parameters, mock_security_context)
            
            assert "Agent execution failed" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_get_letter_found(self, service, mock_security_context, mock_db_session):
        """Test retrieving letter from database."""
        letter_id = uuid4()
        
        # Mock letter
        expected_letter = GeneratedLetter(
            id=letter_id,
            report_id=uuid4(),
            case_name=mock_security_context.case_name,
            jurisdiction="state",
            content="Test content",
            agent_execution_id="exec-456"
        )
        
        with patch('src.services.good_faith_letter_agent_service.LetterRepository') as mock_repo_class:
            mock_repo = mock_repo_class.return_value
            mock_repo.get_letter = AsyncMock(return_value=expected_letter)
            
            result = await service.get_letter(letter_id, mock_security_context)
            
            assert result == expected_letter
            mock_repo.get_letter.assert_called_once_with(letter_id, mock_security_context.case_name)
    
    @pytest.mark.asyncio
    async def test_get_letter_not_found(self, service, mock_security_context, mock_db_session):
        """Test retrieving non-existent letter."""
        with patch('src.services.good_faith_letter_agent_service.LetterRepository') as mock_repo_class:
            mock_repo = mock_repo_class.return_value
            mock_repo.get_letter = AsyncMock(return_value=None)
            
            result = await service.get_letter(uuid4(), mock_security_context)
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_finalize_letter_success(self, service, mock_security_context, mock_db_session):
        """Test letter finalization with database update."""
        letter_id = uuid4()
        
        # Mock existing letter
        existing_letter = GeneratedLetter(
            id=letter_id,
            report_id=uuid4(),
            case_name=mock_security_context.case_name,
            jurisdiction="federal",
            content="Final content",
            status=LetterStatus.APPROVED,
            agent_execution_id="exec-789"
        )
        
        # Updated letter after finalization
        letter_dict = existing_letter.model_dump()
        letter_dict.update({
            "status": LetterStatus.FINALIZED,
            "approved_by": "senior.attorney@firm.com",
            "approved_at": datetime.utcnow()
        })
        finalized_letter = GeneratedLetter(**letter_dict)
        
        with patch('src.services.good_faith_letter_agent_service.LetterRepository') as mock_repo_class:
            mock_repo = mock_repo_class.return_value
            mock_repo.get_letter = AsyncMock(return_value=existing_letter)
            mock_repo.update_letter = AsyncMock(return_value=finalized_letter)
            
            with patch('src.services.good_faith_letter_agent_service.emit_agent_event') as mock_emit:
                result = await service.finalize_letter(
                    letter_id, 
                    "senior.attorney@firm.com",
                    mock_security_context
                )
                
                assert result.status == LetterStatus.FINALIZED
                assert result.approved_by == "senior.attorney@firm.com"
                assert result.approved_at is not None
                
                # Verify database update
                mock_repo.update_letter.assert_called_once()
                
                # Verify event emission
                mock_emit.assert_called_once()
                event_metadata = mock_emit.call_args[1]['metadata']
                assert event_metadata['old_status'] == LetterStatus.APPROVED
                assert event_metadata['new_status'] == LetterStatus.FINALIZED
    
    @pytest.mark.asyncio
    async def test_finalize_letter_not_found(self, service, mock_security_context, mock_db_session):
        """Test finalization of non-existent letter."""
        with patch('src.services.good_faith_letter_agent_service.LetterRepository') as mock_repo_class:
            mock_repo = mock_repo_class.return_value
            mock_repo.get_letter = AsyncMock(return_value=None)
            
            with pytest.raises(ValueError) as exc_info:
                await service.finalize_letter(uuid4(), "approver", mock_security_context)
            
            assert "not found" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_finalize_letter_already_finalized(self, service, mock_security_context, mock_db_session):
        """Test finalization of already finalized letter."""
        letter_id = uuid4()
        
        # Mock already finalized letter
        finalized_letter = GeneratedLetter(
            id=letter_id,
            report_id=uuid4(),
            case_name=mock_security_context.case_name,
            jurisdiction="federal",
            content="Final content",
            status=LetterStatus.FINALIZED,
            agent_execution_id="exec-final"
        )
        
        with patch('src.services.good_faith_letter_agent_service.LetterRepository') as mock_repo_class:
            mock_repo = mock_repo_class.return_value
            mock_repo.get_letter = AsyncMock(return_value=finalized_letter)
            
            with pytest.raises(ValueError) as exc_info:
                await service.finalize_letter(letter_id, "approver", mock_security_context)
            
            assert "already finalized" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_list_letters_by_report(self, service, mock_security_context, mock_db_session):
        """Test listing letters by report ID."""
        report_id = uuid4()
        
        # Mock letters
        mock_letters = [
            GeneratedLetter(
                report_id=report_id,
                case_name=mock_security_context.case_name,
                jurisdiction="federal",
                content=f"Letter {i}",
                agent_execution_id=f"exec-{i}"
            )
            for i in range(3)
        ]
        
        with patch('src.services.good_faith_letter_agent_service.LetterRepository') as mock_repo_class:
            mock_repo = mock_repo_class.return_value
            mock_repo.list_letters_by_report = AsyncMock(return_value=mock_letters)
            
            result = await service.list_letters_by_report(
                report_id, 
                mock_security_context,
                status=LetterStatus.DRAFT
            )
            
            assert len(result) == 3
            mock_repo.list_letters_by_report.assert_called_once_with(
                report_id, 
                mock_security_context.case_name,
                LetterStatus.DRAFT
            )
    
    @pytest.mark.asyncio
    async def test_list_letters_by_case(self, service, mock_security_context, mock_db_session):
        """Test listing letters by case with pagination."""
        # Mock letters
        mock_letters = [
            GeneratedLetter(
                report_id=uuid4(),
                case_name=mock_security_context.case_name,
                jurisdiction="state",
                content=f"Letter {i}",
                agent_execution_id=f"exec-{i}"
            )
            for i in range(5)
        ]
        
        with patch('src.services.good_faith_letter_agent_service.LetterRepository') as mock_repo_class:
            mock_repo = mock_repo_class.return_value
            mock_repo.list_letters_by_case = AsyncMock(return_value=mock_letters)
            
            result = await service.list_letters_by_case(
                mock_security_context,
                limit=10,
                offset=0
            )
            
            assert len(result) == 5
            mock_repo.list_letters_by_case.assert_called_once_with(
                mock_security_context.case_name,
                None,  # status
                10,    # limit
                0      # offset
            )
    
    @pytest.mark.asyncio
    async def test_export_letter_mock(self, service, mock_security_context, mock_db_session):
        """Test export letter returns mock data (until real export implemented)."""
        letter_id = uuid4()
        
        # Mock letter
        mock_letter = GeneratedLetter(
            id=letter_id,
            report_id=uuid4(),
            case_name=mock_security_context.case_name,
            jurisdiction="federal",
            content="Export this content",
            status=LetterStatus.FINALIZED,
            agent_execution_id="exec-export"
        )
        
        with patch('src.services.good_faith_letter_agent_service.LetterRepository') as mock_repo_class:
            mock_repo = mock_repo_class.return_value
            mock_repo.get_letter = AsyncMock(return_value=mock_letter)
            
            with patch.object(service.agent_loader, 'load_agent') as mock_load:
                mock_load.return_value = AsyncMock()
                
                # Mock the export service methods
                with patch.object(service.export_service, 'export_to_pdf', return_value=b"Export this content"):
                    result = await service.export_letter(
                        letter_id,
                        "pdf",
                        mock_security_context
                    )
                    
                    assert result["format"] == "pdf"
                    assert result["content"] == b"Export this content"
                    assert str(letter_id) in result["filename"]
                    assert result["filename"].endswith(".pdf")
    
    @pytest.mark.asyncio
    async def test_list_templates(self, service):
        """Test listing available templates."""
        # Mock template metadata
        with patch.object(service.template_service, 'get_template_requirements') as mock_get_reqs:
            mock_get_reqs.side_effect = [
                {"required_variables": ["CASE_NAME", "ATTORNEY_NAME"]},  # federal
                {"required_variables": ["CASE_NAME", "ATTORNEY_NAME", "STATE"]}  # state
            ]
            
            result = await service.list_templates()
            
            assert len(result) == 2
            assert result[0]["jurisdiction"] == "federal"
            assert result[0]["id"] == "good-faith-letter-federal"
            assert result[1]["jurisdiction"] == "state"
            assert result[1]["id"] == "good-faith-letter-state"
            
            # Verify both templates were queried
            assert mock_get_reqs.call_count == 2
    
    @pytest.mark.asyncio
    async def test_get_db_session_provided(self, mock_db_session):
        """Test _get_db_session when session is provided."""
        service = GoodFaithLetterAgentService(db_session=mock_db_session)
        
        # _get_db_session is an async context manager
        async with service._get_db_session() as session:
            assert session == mock_db_session
    
    @pytest.mark.asyncio
    async def test_get_db_session_from_dependency(self):
        """Test _get_db_session gets new session from dependency."""
        service = GoodFaithLetterAgentService()
        
        mock_session = MagicMock(spec=AsyncSession)
        
        # Mock the AsyncSessionLocal
        with patch('src.database.connection.AsyncSessionLocal') as mock_session_local:
            # Create a mock async context manager
            @asynccontextmanager
            async def mock_session_context():
                yield mock_session
                
            mock_session_local.return_value = mock_session_context()
            
            # _get_db_session is an async context manager
            async with service._get_db_session() as session:
                assert session == mock_session
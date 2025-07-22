"""
Tests for Good Faith Letter agent API endpoints.
"""
import pytest
from uuid import uuid4
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from fastapi import HTTPException
from fastapi.testclient import TestClient

from src.api.agents.good_faith_letter_endpoints import (
    AgentCommandRequest,
    GenerateLetterRequest,
    CustomizeLetterRequest,
    FinalizeLetterRequest
)
from src.models.deficiency_models import GeneratedLetter, LetterStatus
from src.ai_agents.bmad_framework.security import AgentSecurityContext


class TestGoodFaithLetterEndpoints:
    """Test suite for Good Faith Letter API endpoints."""
    
    @pytest.fixture
    def mock_security_context(self):
        """Mock security context for tests."""
        context = Mock(spec=AgentSecurityContext)
        context.case_id = "test-case-123"
        context.case_name = "Test_Case_2024"
        context.user_id = "test-user"
        return context
    
    @pytest.fixture
    def mock_letter_service(self):
        """Mock letter service."""
        with patch('src.api.agents.good_faith_letter_endpoints.GoodFaithLetterAgentService') as mock:
            yield mock
    
    @pytest.mark.asyncio
    async def test_execute_agent_command_valid(self, mock_security_context):
        """Test executing valid agent command."""
        from src.api.agents.good_faith_letter_endpoints import execute_agent_command
        
        request = AgentCommandRequest(
            command="select-template",
            parameters={"jurisdiction": "federal"}
        )
        
        with patch('src.api.agents.good_faith_letter_endpoints.AgentLoader') as mock_loader:
            with patch('src.api.agents.good_faith_letter_endpoints.AgentExecutor') as mock_executor:
                # Mock execution result
                mock_result = Mock()
                mock_result.status = "success"
                mock_result.output = {"template_id": "federal-template"}
                mock_result.execution_id = "exec-123"
                
                mock_executor.return_value.execute_command = AsyncMock(return_value=mock_result)
                mock_loader.return_value.load_agent = AsyncMock()
                
                response = await execute_agent_command(request, mock_security_context)
                
                assert response.command == "select-template"
                assert response.status == "success"
                assert response.execution_id == "exec-123"
    
    @pytest.mark.asyncio
    async def test_execute_agent_command_invalid(self, mock_security_context):
        """Test executing invalid agent command."""
        from src.api.agents.good_faith_letter_endpoints import execute_agent_command
        
        request = AgentCommandRequest(
            command="invalid-command",
            parameters={}
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await execute_agent_command(request, mock_security_context)
        
        assert exc_info.value.status_code == 400
        assert "Invalid command" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_generate_letter_success(self, mock_security_context, mock_letter_service):
        """Test successful letter generation."""
        from src.api.agents.good_faith_letter_endpoints import generate_letter_via_agent
        from fastapi import BackgroundTasks
        
        request = GenerateLetterRequest(
            report_id=uuid4(),
            jurisdiction="federal",
            include_evidence=True,
            evidence_format="inline",
            attorney_info={
                "name": "John Doe",
                "firm": "Doe Law",
                "bar_number": "12345",
                "email": "john.doe@doelaw.com"
            }
        )
        
        # Mock generated letter
        mock_letter = GeneratedLetter(
            report_id=request.report_id,
            case_name=mock_security_context.case_name,
            jurisdiction="federal",
            content="Dear Counsel...",
            agent_execution_id="exec-456"
        )
        
        mock_service = mock_letter_service.return_value
        mock_service.generate_letter = AsyncMock(return_value=mock_letter)
        
        background_tasks = BackgroundTasks()
        
        response = await generate_letter_via_agent(
            request, background_tasks, mock_security_context
        )
        
        assert response.letter_id == mock_letter.id
        assert response.status == LetterStatus.DRAFT
        assert response.agent_execution_id == "exec-456"
        assert "/preview/" in response.preview_url
    
    @pytest.mark.asyncio
    async def test_preview_letter(self, mock_security_context, mock_letter_service):
        """Test letter preview endpoint."""
        from src.api.agents.good_faith_letter_endpoints import preview_letter
        
        letter_id = uuid4()
        
        # Mock letter
        mock_letter = GeneratedLetter(
            id=letter_id,
            report_id=uuid4(),
            case_name=mock_security_context.case_name,
            jurisdiction="federal",
            content="Test letter content",
            agent_execution_id="exec-789"
        )
        
        mock_service = mock_letter_service.return_value
        mock_service.get_letter = AsyncMock(return_value=mock_letter)
        
        result = await preview_letter(letter_id, mock_security_context)
        
        assert result["letter_id"] == str(letter_id)
        assert result["status"] == LetterStatus.DRAFT
        assert result["content"] == "Test letter content"
        assert result["metadata"]["editable"] is True
    
    @pytest.mark.asyncio
    async def test_preview_letter_not_found(self, mock_security_context, mock_letter_service):
        """Test preview non-existent letter."""
        from src.api.agents.good_faith_letter_endpoints import preview_letter
        
        mock_service = mock_letter_service.return_value
        mock_service.get_letter = AsyncMock(return_value=None)
        
        with pytest.raises(HTTPException) as exc_info:
            await preview_letter(uuid4(), mock_security_context)
        
        assert exc_info.value.status_code == 404
    
    @pytest.mark.asyncio
    async def test_customize_letter(self, mock_security_context):
        """Test letter customization endpoint."""
        from src.api.agents.good_faith_letter_endpoints import customize_letter
        
        letter_id = uuid4()
        request = CustomizeLetterRequest(
            section_edits=[
                {"section": "opening", "content": "Updated opening"},
                {"section": "closing", "content": "Updated closing"}
            ],
            editor_notes="Made tone more formal"
        )
        
        with patch('src.api.agents.good_faith_letter_endpoints.LetterCustomizationService') as mock_custom:
            # Mock updated letter
            mock_updated = Mock()
            mock_updated.id = letter_id
            mock_updated.version = 2
            mock_updated.status = LetterStatus.DRAFT
            mock_updated.edit_history = [Mock(), Mock()]
            
            mock_custom.return_value.apply_edits = AsyncMock(return_value=mock_updated)
            
            result = await customize_letter(letter_id, request, mock_security_context)
            
            assert result["letter_id"] == str(letter_id)
            assert result["version"] == 2
            assert result["edit_history_count"] == 2
    
    @pytest.mark.asyncio
    async def test_finalize_letter(self, mock_security_context, mock_letter_service):
        """Test letter finalization endpoint."""
        from src.api.agents.good_faith_letter_endpoints import finalize_letter
        
        letter_id = uuid4()
        request = FinalizeLetterRequest(
            approved_by="senior.attorney@firm.com",
            export_formats=["pdf", "docx"]
        )
        
        # Mock finalized letter
        mock_finalized = GeneratedLetter(
            id=letter_id,
            report_id=uuid4(),
            case_name=mock_security_context.case_name,
            jurisdiction="federal",
            content="Final content",
            status=LetterStatus.FINALIZED,
            approved_by=request.approved_by,
            approved_at=datetime.utcnow(),
            agent_execution_id="exec-final"
        )
        
        mock_service = mock_letter_service.return_value
        mock_service.finalize_letter = AsyncMock(return_value=mock_finalized)
        
        result = await finalize_letter(letter_id, request, mock_security_context)
        
        assert result["letter_id"] == str(letter_id)
        assert result["status"] == LetterStatus.FINALIZED
        assert result["approved_by"] == request.approved_by
        assert "pdf" in result["export_urls"]
        assert "docx" in result["export_urls"]
    
    @pytest.mark.asyncio
    async def test_list_templates(self, mock_security_context, mock_letter_service):
        """Test template listing endpoint."""
        from src.api.agents.good_faith_letter_endpoints import list_available_templates
        
        # Mock templates
        mock_templates = [
            {
                "id": "good-faith-letter-federal",
                "jurisdiction": "federal",
                "title": "Federal Good Faith Letter",
                "description": "FRCP Rule 37 compliant",
                "required_variables": ["CASE_NAME", "ATTORNEY_NAME"]
            },
            {
                "id": "good-faith-letter-state",
                "jurisdiction": "state",
                "title": "State Good Faith Letter",
                "description": "State-specific template",
                "required_variables": ["CASE_NAME", "ATTORNEY_NAME", "STATE"]
            }
        ]
        
        mock_service = mock_letter_service.return_value
        mock_service.list_templates = AsyncMock(return_value=mock_templates)
        
        result = await list_available_templates(mock_security_context)
        
        assert len(result) == 2
        assert result[0]["template_id"] == "good-faith-letter-federal"
        assert result[1]["jurisdiction"] == "state"
    
    @pytest.mark.asyncio
    async def test_export_letter_success(self, mock_security_context, mock_letter_service):
        """Test successful letter export."""
        from src.api.agents.good_faith_letter_endpoints import export_letter
        
        letter_id = uuid4()
        format = "pdf"
        
        # Mock finalized letter
        mock_letter = GeneratedLetter(
            id=letter_id,
            report_id=uuid4(),
            case_name=mock_security_context.case_name,
            jurisdiction="federal",
            content="Final content",
            status=LetterStatus.FINALIZED,
            agent_execution_id="exec-export"
        )
        
        # Mock export data as a dictionary
        mock_export_data = {
            "content": b"PDF content here",
            "filename": f"good-faith-letter-{letter_id}.pdf"
        }
        
        mock_service = mock_letter_service.return_value
        mock_service.get_letter = AsyncMock(return_value=mock_letter)
        mock_service.export_letter = AsyncMock(return_value=mock_export_data)
        
        response = await export_letter(letter_id, format, mock_security_context)
        
        # Check response is StreamingResponse
        assert response.status_code == 200
        assert response.media_type == "application/pdf"
        assert f"filename=good-faith-letter-{letter_id}.pdf" in response.headers["content-disposition"]
    
    @pytest.mark.asyncio
    async def test_export_letter_invalid_format(self, mock_security_context):
        """Test export with invalid format."""
        from src.api.agents.good_faith_letter_endpoints import export_letter
        
        with pytest.raises(HTTPException) as exc_info:
            await export_letter(uuid4(), "invalid", mock_security_context)
        
        assert exc_info.value.status_code == 400
        assert "Invalid format" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_export_letter_not_finalized(self, mock_security_context, mock_letter_service):
        """Test export of non-finalized letter."""
        from src.api.agents.good_faith_letter_endpoints import export_letter
        
        letter_id = uuid4()
        
        # Mock draft letter
        mock_letter = GeneratedLetter(
            id=letter_id,
            report_id=uuid4(),
            case_name=mock_security_context.case_name,
            jurisdiction="federal",
            content="Draft content",
            status=LetterStatus.DRAFT,
            agent_execution_id="exec-draft"
        )
        
        mock_service = mock_letter_service.return_value
        mock_service.get_letter = AsyncMock(return_value=mock_letter)
        
        with pytest.raises(HTTPException) as exc_info:
            await export_letter(letter_id, "pdf", mock_security_context)
        
        assert exc_info.value.status_code == 400
        assert "must be finalized" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_generate_letter_missing_attorney_info(self):
        """Test validation of attorney_info fields."""
        from src.api.agents.good_faith_letter_endpoints import GenerateLetterRequest
        
        # Test missing required fields
        with pytest.raises(ValueError) as exc_info:
            GenerateLetterRequest(
                report_id=uuid4(),
                jurisdiction="federal",
                attorney_info={"name": "John Doe"}  # Missing firm and email
            )
        
        assert "required fields" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_customize_letter_empty_edits(self, mock_security_context):
        """Test customization with empty edits."""
        from src.api.agents.good_faith_letter_endpoints import customize_letter, CustomizeLetterRequest
        
        letter_id = uuid4()
        
        # The validation should fail when creating the request object
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError) as exc_info:
            request = CustomizeLetterRequest(
                section_edits=[],
                editor_notes="No changes"
            )
        
        # Check that the error mentions the empty edits
        assert "At least one edit must be provided" in str(exc_info.value)
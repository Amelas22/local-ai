"""
Tests for Good Faith Letter export task.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from uuid import uuid4
from datetime import datetime

from ai_agents.bmad_framework.security import AgentSecurityContext
from src.models.deficiency_models import GeneratedLetter, LetterStatus


class TestExportLetterTask:
    """Test suite for export-letter task."""
    
    @pytest.mark.asyncio
    async def test_export_pdf_success(self):
        """Test successful PDF export."""
        from ai_agents.bmad_framework.task_handlers import execute_task
        
        # Mock security context
        security_context = Mock(spec=AgentSecurityContext)
        security_context.case_id = "test-case-123"
        
        letter_id = str(uuid4())
        
        # Mock letter
        mock_letter = GeneratedLetter(
            id=uuid4(),
            report_id=uuid4(),
            case_name="Test_Case_2024",
            jurisdiction="federal",
            content="Dear Counsel:\n\nThis is the letter content.\n\nSincerely,\nAttorney",
            status=LetterStatus.FINALIZED,
            approved_by="approver@firm.com",
            agent_execution_id="exec-123"
        )
        
        with patch('src.services.good_faith_letter_agent_service.GoodFaithLetterAgentService') as mock_service:
            with patch('src.utils.document_exporter.DocumentExporter') as mock_exporter:
                # Mock get_letter
                mock_service.return_value.get_letter = AsyncMock(return_value=mock_letter)
                
                # Mock PDF export
                mock_exporter.return_value.to_pdf = AsyncMock(
                    return_value=b"PDF content bytes"
                )
                
                result = await execute_task(
                    "export-letter",
                    letter_id=letter_id,
                    format="pdf",
                    include_metadata=True,
                    security_context=security_context
                )
        
        assert result["format"] == "pdf"
        assert result["content"] == b"PDF content bytes"
        assert ".pdf" in result["filename"]
        assert result["content_type"] == "application/pdf"
    
    @pytest.mark.asyncio
    async def test_export_docx_success(self):
        """Test successful DOCX export."""
        from ai_agents.bmad_framework.task_handlers import execute_task
        
        security_context = Mock(spec=AgentSecurityContext)
        security_context.case_id = "test-case-123"
        
        letter_id = str(uuid4())
        
        # Mock letter
        mock_letter = GeneratedLetter(
            id=uuid4(),
            report_id=uuid4(),
            case_name="Test_Case",
            jurisdiction="state",
            content="Letter content",
            status=LetterStatus.FINALIZED,
            agent_execution_id="exec-456"
        )
        
        with patch('src.services.good_faith_letter_agent_service.GoodFaithLetterAgentService') as mock_service:
            with patch('src.utils.document_exporter.DocumentExporter') as mock_exporter:
                mock_service.return_value.get_letter = AsyncMock(return_value=mock_letter)
                mock_exporter.return_value.to_docx = AsyncMock(
                    return_value=b"DOCX content bytes"
                )
                
                result = await execute_task(
                    "export-letter",
                    letter_id=letter_id,
                    format="docx",
                    security_context=security_context
                )
        
        assert result["format"] == "docx"
        assert ".docx" in result["filename"]
        assert "wordprocessingml" in result["content_type"]
    
    @pytest.mark.asyncio
    async def test_export_not_finalized_fails(self):
        """Test export fails if letter not finalized."""
        from ai_agents.bmad_framework.task_handlers import execute_task
        
        security_context = Mock(spec=AgentSecurityContext)
        letter_id = str(uuid4())
        
        # Mock draft letter
        mock_letter = GeneratedLetter(
            id=uuid4(),
            report_id=uuid4(),
            case_name="Test_Case",
            jurisdiction="federal",
            content="Draft content",
            status=LetterStatus.DRAFT,  # Not finalized
            agent_execution_id="exec-789"
        )
        
        with patch('src.services.good_faith_letter_agent_service.GoodFaithLetterAgentService') as mock_service:
            mock_service.return_value.get_letter = AsyncMock(return_value=mock_letter)
            
            with pytest.raises(ValueError) as exc_info:
                await execute_task(
                    "export-letter",
                    letter_id=letter_id,
                    format="pdf",
                    security_context=security_context
                )
            
            assert "finalized" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_export_invalid_format(self):
        """Test export with invalid format."""
        from ai_agents.bmad_framework.task_handlers import execute_task
        
        security_context = Mock(spec=AgentSecurityContext)
        letter_id = str(uuid4())
        
        # Mock letter
        mock_letter = GeneratedLetter(
            id=uuid4(),
            report_id=uuid4(),
            case_name="Test_Case",
            jurisdiction="federal",
            content="Content",
            status=LetterStatus.FINALIZED,
            agent_execution_id="exec-123"
        )
        
        with patch('src.services.good_faith_letter_agent_service.GoodFaithLetterAgentService') as mock_service:
            mock_service.return_value.get_letter = AsyncMock(return_value=mock_letter)
            
            with pytest.raises(ValueError) as exc_info:
                await execute_task(
                    "export-letter",
                    letter_id=letter_id,
                    format="invalid",
                    security_context=security_context
                )
            
            assert "Unsupported format" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_export_with_metadata(self):
        """Test export includes metadata when requested."""
        from ai_agents.bmad_framework.task_handlers import execute_task
        
        security_context = Mock(spec=AgentSecurityContext)
        letter_id = str(uuid4())
        
        # Mock letter with metadata
        mock_letter = GeneratedLetter(
            id=uuid4(),
            report_id=uuid4(),
            case_name="Smith_v_Jones",
            jurisdiction="federal",
            content="Letter body",
            status=LetterStatus.FINALIZED,
            approved_by="senior.partner@firm.com",
            created_at=datetime(2024, 1, 15),
            version=3,
            agent_execution_id="exec-meta"
        )
        
        with patch('src.services.good_faith_letter_agent_service.GoodFaithLetterAgentService') as mock_service:
            with patch('src.utils.document_exporter.DocumentExporter') as mock_exporter:
                mock_service.return_value.get_letter = AsyncMock(return_value=mock_letter)
                
                # Capture the content passed to exporter
                export_content = None
                async def capture_content(content, options):
                    nonlocal export_content
                    export_content = content
                    return b"HTML content"
                
                mock_exporter.return_value.to_html = capture_content
                
                result = await execute_task(
                    "export-letter",
                    letter_id=letter_id,
                    format="html",
                    include_metadata=True,
                    security_context=security_context
                )
                
                # Verify metadata included
                assert "[METADATA]" in export_content
                assert "Smith_v_Jones" in export_content
                assert "Federal" in export_content
                assert "Version: 3" in export_content
    
    def test_content_type_mapping(self):
        """Test content type mapping for formats."""
        from ai_agents.bmad_framework.tasks.export_letter import _get_content_type
        
        assert _get_content_type("pdf") == "application/pdf"
        assert _get_content_type("docx") == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        assert _get_content_type("html") == "text/html"
        assert _get_content_type("unknown") == "application/octet-stream"
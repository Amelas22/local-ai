"""
Tests for Good Faith Letter generation BMad tasks.
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path
import json

from src.ai_agents.bmad_framework.security import AgentSecurityContext


class TestSelectLetterTemplateTask:
    """Test suite for select-letter-template task."""
    
    @pytest.mark.asyncio
    async def test_select_federal_template(self):
        """Test selecting federal jurisdiction template."""
        from src.ai_agents.bmad_framework.task_handlers import execute_task
        
        # Mock security context
        security_context = Mock(spec=AgentSecurityContext)
        security_context.case_id = "test-case-123"
        
        # Execute task
        with patch('src.ai_agents.bmad_framework.template_loader.TemplateLoader') as mock_loader:
            mock_template = Mock()
            mock_template.metadata = {"id": "good-faith-letter-federal"}
            mock_template.get_required_variables.return_value = ["CASE_NAME", "DEFICIENCY_COUNT"]
            mock_template.get_optional_variables.return_value = ["CC_RECIPIENTS"]
            mock_template.sections = [Mock(name="header"), Mock(name="body")]
            
            mock_loader.return_value.load_template = AsyncMock(return_value=mock_template)
            
            result = await execute_task(
                "select-letter-template",
                jurisdiction="federal",
                security_context=security_context
            )
        
        # Verify result
        assert result["jurisdiction"] == "federal"
        assert result["template_id"] == "good-faith-letter-federal"
        assert "CASE_NAME" in result["required_variables"]
        assert "header" in result["sections"]
    
    @pytest.mark.asyncio
    async def test_select_state_template_requires_state_code(self):
        """Test state jurisdiction requires state code."""
        from src.ai_agents.bmad_framework.task_handlers import execute_task
        
        security_context = Mock(spec=AgentSecurityContext)
        
        # Should raise error without state code
        with pytest.raises(ValueError, match="State code required"):
            await execute_task(
                "select-letter-template",
                jurisdiction="state",
                security_context=security_context
            )
    
    @pytest.mark.asyncio
    async def test_invalid_jurisdiction_raises_error(self):
        """Test invalid jurisdiction raises error."""
        from src.ai_agents.bmad_framework.task_handlers import execute_task
        
        security_context = Mock(spec=AgentSecurityContext)
        
        with pytest.raises(ValueError, match="Invalid jurisdiction"):
            await execute_task(
                "select-letter-template",
                jurisdiction="invalid",
                security_context=security_context
            )


class TestPopulateDeficiencyFindingsTask:
    """Test suite for populate-deficiency-findings task."""
    
    @pytest.mark.asyncio
    async def test_populate_findings_basic(self):
        """Test basic population of deficiency findings."""
        from src.ai_agents.bmad_framework.task_handlers import execute_task
        from datetime import datetime
        
        security_context = Mock(spec=AgentSecurityContext)
        security_context.case_id = "test-case-123"
        
        # Mock deficiency data
        mock_report = Mock()
        mock_report.case_name = "Smith v. Jones"
        mock_report.created_at = datetime(2024, 1, 15)
        mock_report.total_requests = 25
        mock_report.summary_statistics = {
            "fully_produced": 10,
            "partially_produced": 5,
            "not_produced": 8,
            "no_responsive_docs": 2
        }
        
        mock_item = Mock()
        mock_item.request_number = "RFP No. 1"
        mock_item.request_text = "All emails"
        mock_item.oc_response_text = "No responsive documents"
        mock_item.classification = "not_produced"
        mock_item.evidence_chunks = []
        
        with patch('src.services.deficiency_service.DeficiencyService') as mock_service:
            mock_service.return_value.get_deficiency_report = AsyncMock(return_value=mock_report)
            mock_service.return_value.get_deficiency_items = AsyncMock(return_value=[mock_item])
            
            result = await execute_task(
                "populate-deficiency-findings",
                report_id="test-report-123",
                include_evidence=False,
                security_context=security_context
            )
        
        # Verify result
        assert result["CASE_NAME"] == "Smith v. Jones"
        assert result["DEFICIENCY_COUNT"] == 15  # 25 - 10 fully produced
        assert len(result["DEFICIENCY_ITEMS"]) == 1
        assert result["DEFICIENCY_ITEMS"][0]["REQUEST_NUMBER"] == "RFP No. 1"
    
    @pytest.mark.asyncio
    async def test_populate_findings_with_evidence(self):
        """Test population with evidence chunks."""
        from src.ai_agents.bmad_framework.task_handlers import execute_task
        from datetime import datetime
        
        security_context = Mock(spec=AgentSecurityContext)
        
        # Mock deficiency data with evidence
        mock_report = Mock()
        mock_report.case_name = "Test Case"
        mock_report.created_at = datetime.now()
        mock_report.total_requests = 10
        mock_report.summary_statistics = {"fully_produced": 5}
        
        mock_item = Mock()
        mock_item.request_number = "RFP No. 1"
        mock_item.request_text = "Documents"
        mock_item.oc_response_text = "None"
        mock_item.classification = "not_produced"
        mock_item.evidence_chunks = [
            {
                "document_id": "doc123",
                "chunk_text": "Evidence text",
                "relevance_score": 0.95,
                "page_number": 10
            }
        ]
        
        with patch('src.services.deficiency_service.DeficiencyService') as mock_service:
            mock_service.return_value.get_deficiency_report = AsyncMock(return_value=mock_report)
            mock_service.return_value.get_deficiency_items = AsyncMock(return_value=[mock_item])
            
            result = await execute_task(
                "populate-deficiency-findings",
                report_id="test-report-123",
                include_evidence=True,
                evidence_format="inline",
                security_context=security_context
            )
        
        # Verify evidence included
        assert result["INCLUDE_EVIDENCE"] is True
        assert len(result["DEFICIENCY_ITEMS"][0]["EVIDENCE"]) == 1
        assert result["DEFICIENCY_ITEMS"][0]["EVIDENCE"][0]["RELEVANCE_SCORE"] == "0.95"


class TestGenerateSignatureBlockTask:
    """Test suite for generate-signature-block task."""
    
    @pytest.mark.asyncio
    async def test_generate_basic_signature(self):
        """Test basic signature block generation."""
        from src.ai_agents.bmad_framework.task_handlers import execute_task
        
        security_context = Mock(spec=AgentSecurityContext)
        
        result = await execute_task(
            "generate-signature-block",
            attorney_name="Jane Smith, Esq.",
            attorney_title="Partner",
            firm_name="Smith Law Firm",
            bar_number="12345",
            address_lines=["123 Main St", "Suite 100", "Miami, FL 33131"],
            phone="(305) 555-1234",
            email="jsmith@smithlaw.com",
            security_context=security_context
        )
        
        # Verify result
        assert result["PRIMARY_SIGNATURE"]["ATTORNEY_NAME"] == "Jane Smith, Esq."
        assert result["PRIMARY_SIGNATURE"]["FIRM_NAME"] == "Smith Law Firm"
        assert result["CLOSING"] == "Respectfully submitted,"
        assert "FORMATTED_BLOCK" in result
    
    @pytest.mark.asyncio
    async def test_generate_signature_with_certification(self):
        """Test signature with certification text."""
        from src.ai_agents.bmad_framework.task_handlers import execute_task
        
        security_context = Mock(spec=AgentSecurityContext)
        
        result = await execute_task(
            "generate-signature-block",
            attorney_name="John Doe",
            attorney_title="Attorney",
            firm_name="Doe & Associates",
            bar_number="67890",
            address_lines=["456 Court St"],
            phone="(305) 555-5678",
            email="jdoe@doelaw.com",
            include_certification=True,
            jurisdiction="federal",
            security_context=security_context
        )
        
        # Verify certification included
        assert "certify" in result["CERTIFICATION_TEXT"].lower()
        assert "good faith" in result["CERTIFICATION_TEXT"].lower()
    
    @pytest.mark.asyncio
    async def test_generate_signature_with_additional_signatories(self):
        """Test signature with multiple signatories."""
        from src.ai_agents.bmad_framework.task_handlers import execute_task
        
        security_context = Mock(spec=AgentSecurityContext)
        
        additional = [
            {
                "name": "Bob Johnson, Esq.",
                "title": "Associate",
                "bar_number": "11111"
            }
        ]
        
        result = await execute_task(
            "generate-signature-block",
            attorney_name="Jane Smith",
            attorney_title="Partner",
            firm_name="Smith Law",
            bar_number="12345",
            address_lines=["123 Main St"],
            phone="(305) 555-1234",
            email="jsmith@law.com",
            additional_signatories=additional,
            security_context=security_context
        )
        
        # Verify additional signatures
        assert len(result["ADDITIONAL_SIGNATURES"]) == 1
        assert result["ADDITIONAL_SIGNATURES"][0]["ATTORNEY_NAME"] == "Bob Johnson, Esq."
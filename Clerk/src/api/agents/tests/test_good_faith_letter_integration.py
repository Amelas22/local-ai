"""
End-to-end integration tests for Good Faith Letter workflow.

Tests the complete workflow from deficiency report to finalized letter export.
"""
import pytest
import asyncio
from uuid import uuid4
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch
from io import BytesIO

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from src.models.deficiency_models import (
    DeficiencyReport, 
    DeficiencyItem,
    GeneratedLetter,
    LetterStatus
)
from src.database.connection import Base
from src.database.letter_models import GeneratedLetterDB
from src.ai_agents.bmad_framework.security import AgentSecurityContext


class TestGoodFaithLetterIntegration:
    """End-to-end integration tests for letter workflow."""
    
    @pytest.fixture
    async def test_database(self):
        """Create test database with tables."""
        # Use in-memory SQLite for tests
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        
        # Create tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        # Create session factory
        async_session = async_sessionmaker(engine, class_=AsyncSession)
        
        yield async_session
        
        await engine.dispose()
    
    @pytest.fixture
    def test_client(self):
        """Create test client."""
        from main import app
        return TestClient(app)
    
    @pytest.fixture
    def mock_security_context(self):
        """Mock security context for tests."""
        context = Mock(spec=AgentSecurityContext)
        context.case_id = "test-case-123"
        context.case_name = "Test_Case_2024"
        context.user_id = "test-user@lawfirm.com"
        return context
    
    @pytest.fixture
    async def test_deficiency_report(self, test_database):
        """Create test deficiency report."""
        report = DeficiencyReport(
            case_name="Test_Case_2024",
            case_number="2024-CV-12345",
            production_id=uuid4(),
            rtp_document_id=uuid4(),
            oc_response_document_id=uuid4(),
            analysis_status="completed",
            total_requests=10,
            summary_statistics={
                "fully_produced": 5,
                "not_produced": 3,
                "partially_produced": 2,
                "no_responsive_docs": 0
            }
        )
        
        # Create deficiency items
        items = [
            DeficiencyItem(
                report_id=report.id,
                request_number="RFP No. 1",
                request_text="All emails regarding the contract",
                oc_response_text="No responsive documents exist",
                classification="not_produced",
                confidence_score=0.92,
                evidence_chunks=[{
                    "document_id": "doc123",
                    "chunk_text": "Email dated 3/15: Contract negotiations ongoing",
                    "relevance_score": 0.95
                }]
            ),
            DeficiencyItem(
                report_id=report.id,
                request_number="RFP No. 5",
                request_text="Financial statements for 2023",
                oc_response_text="Documents will be produced",
                classification="partially_produced",
                confidence_score=0.78,
                evidence_chunks=[]
            ),
            DeficiencyItem(
                report_id=report.id,
                request_number="RFP No. 8",
                request_text="Board meeting minutes",
                oc_response_text="See attached production",
                classification="fully_produced",
                confidence_score=0.95,
                evidence_chunks=[]
            )
        ]
        
        return report, items
    
    @pytest.mark.asyncio
    async def test_complete_letter_workflow(
        self, 
        test_client, 
        test_database,
        test_deficiency_report,
        mock_security_context
    ):
        """Test full workflow from report to finalized letter."""
        report, items = test_deficiency_report
        
        # Step 1: Generate letter from deficiency report
        with patch('src.api.agents.good_faith_letter_endpoints.get_agent_security_context') as mock_get_context:
            mock_get_context.return_value = mock_security_context
            
            # Mock the agent service to use test database
            with patch('src.services.good_faith_letter_agent_service.GoodFaithLetterAgentService') as mock_service_class:
                # Create mock service instance
                mock_service = mock_service_class.return_value
                
                # Mock letter generation
                generated_letter = GeneratedLetter(
                    report_id=report.id,
                    case_name="Test_Case_2024",
                    jurisdiction="federal",
                    content="""Dear Counsel:

RE: Test Case 2024 - Discovery Deficiencies

I am writing regarding deficiencies in your discovery production dated January 15, 2024.

DEFICIENCIES:

1. RFP No. 1 - All emails regarding the contract
   Response: "No responsive documents exist"
   Issue: Our analysis indicates responsive documents likely exist.

2. RFP No. 5 - Financial statements for 2023
   Response: "Documents will be produced"
   Issue: Documents have not been produced as promised.

Please remedy these deficiencies within 10 days.

Sincerely,
Test Attorney""",
                    status=LetterStatus.DRAFT,
                    agent_execution_id="exec-test-123"
                )
                
                mock_service.generate_letter = AsyncMock(return_value=generated_letter)
                
                # Make API request
                response = test_client.post(
                    "/api/agents/good-faith-letter/generate-letter",
                    json={
                        "report_id": str(report.id),
                        "jurisdiction": "federal",
                        "attorney_info": {
                            "name": "Test Attorney, Esq.",
                            "firm": "Test Law Firm",
                            "email": "attorney@testfirm.com",
                            "bar_number": "12345"
                        }
                    },
                    headers={"X-Case-ID": "test-case-123"}
                )
                
                assert response.status_code == 200
                letter_data = response.json()
                letter_id = letter_data["letter_id"]
                assert letter_data["status"] == "draft"
        
        # Step 2: Preview the generated letter
        with patch('src.api.agents.good_faith_letter_endpoints.get_agent_security_context') as mock_get_context:
            mock_get_context.return_value = mock_security_context
            
            mock_service.get_letter = AsyncMock(return_value=generated_letter)
            
            response = test_client.get(
                f"/api/agents/good-faith-letter/preview/{letter_id}",
                headers={"X-Case-ID": "test-case-123"}
            )
            
            assert response.status_code == 200
            preview_data = response.json()
            assert "Dear Counsel" in preview_data["content"]
            assert preview_data["metadata"]["editable"] is True
        
        # Step 3: Customize the letter
        with patch('src.api.agents.good_faith_letter_endpoints.get_agent_security_context') as mock_get_context:
            mock_get_context.return_value = mock_security_context
            
            # Mock customization service
            with patch('src.api.agents.good_faith_letter_endpoints.LetterCustomizationService') as mock_custom_class:
                mock_custom = mock_custom_class.return_value
                
                # Updated letter after customization
                customized_letter = GeneratedLetter(
                    **generated_letter.model_dump(),
                    content=generated_letter.content.replace("10 days", "7 business days"),
                    version=2,
                    status=LetterStatus.REVIEW
                )
                
                mock_custom.apply_edits = AsyncMock(return_value=customized_letter)
                
                response = test_client.put(
                    f"/api/agents/good-faith-letter/customize/{letter_id}",
                    json={
                        "section_edits": [{
                            "section": "deadline",
                            "content": "Please remedy these deficiencies within 7 business days."
                        }],
                        "editor_notes": "Shortened deadline per partner guidance"
                    },
                    headers={"X-Case-ID": "test-case-123"}
                )
                
                assert response.status_code == 200
                custom_data = response.json()
                assert custom_data["version"] == 2
                assert custom_data["status"] == "review"
        
        # Step 4: Finalize the letter
        with patch('src.api.agents.good_faith_letter_endpoints.get_agent_security_context') as mock_get_context:
            mock_get_context.return_value = mock_security_context
            
            # Mock finalized letter
            finalized_letter = GeneratedLetter(
                **customized_letter.model_dump(),
                status=LetterStatus.FINALIZED,
                approved_by="senior.partner@firm.com",
                approved_at=datetime.utcnow()
            )
            
            mock_service.finalize_letter = AsyncMock(return_value=finalized_letter)
            
            response = test_client.post(
                f"/api/agents/good-faith-letter/finalize/{letter_id}",
                json={
                    "approved_by": "senior.partner@firm.com",
                    "export_formats": ["pdf", "docx"]
                },
                headers={"X-Case-ID": "test-case-123"}
            )
            
            assert response.status_code == 200
            finalize_data = response.json()
            assert finalize_data["status"] == "finalized"
            assert finalize_data["approved_by"] == "senior.partner@firm.com"
            assert "pdf" in finalize_data["export_urls"]
            assert "docx" in finalize_data["export_urls"]
        
        # Step 5: Export the letter as PDF
        with patch('src.api.agents.good_faith_letter_endpoints.get_agent_security_context') as mock_get_context:
            mock_get_context.return_value = mock_security_context
            
            # Mock export
            mock_service.get_letter = AsyncMock(return_value=finalized_letter)
            mock_service.export_letter = AsyncMock(return_value={
                "content": b"PDF binary content here",
                "format": "pdf",
                "filename": f"good-faith-letter-Test_Case_2024-{letter_id}.pdf"
            })
            
            response = test_client.get(
                f"/api/agents/good-faith-letter/export/{letter_id}/pdf",
                headers={"X-Case-ID": "test-case-123"}
            )
            
            assert response.status_code == 200
            assert response.headers["content-type"] == "application/pdf"
            assert "attachment" in response.headers["content-disposition"]
    
    @pytest.mark.asyncio
    async def test_letter_workflow_with_database_persistence(
        self,
        test_database,
        test_deficiency_report
    ):
        """Test letter workflow with actual database operations."""
        report, items = test_deficiency_report
        
        # Create database session
        async with test_database() as session:
            # Import repository
            from src.database.letter_repository import LetterRepository
            repo = LetterRepository(session)
            
            # Create letter
            letter = GeneratedLetter(
                report_id=report.id,
                case_name="Test_Case_2024",
                jurisdiction="federal",
                content="Test letter content",
                agent_execution_id="exec-db-test"
            )
            
            # Save to database
            saved_letter = await repo.create_letter(letter)
            assert saved_letter.id == letter.id
            
            # Retrieve letter
            retrieved = await repo.get_letter(letter.id, "Test_Case_2024")
            assert retrieved is not None
            assert retrieved.content == "Test letter content"
            
            # Update letter
            retrieved.content = "Updated content"
            retrieved.version = 2
            updated = await repo.update_letter(retrieved)
            assert updated.version == 2
            
            # List letters by report
            letters = await repo.list_letters_by_report(report.id, "Test_Case_2024")
            assert len(letters) == 1
            assert letters[0].version == 2
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, test_client):
        """Test rate limiting prevents abuse."""
        with patch('src.api.agents.good_faith_letter_endpoints.get_agent_security_context') as mock_get_context:
            mock_context = Mock()
            mock_context.case_id = "test-case"
            mock_context.case_name = "Test_Case"
            mock_context.user_id = "rate-limit-test"
            mock_get_context.return_value = mock_context
            
            # Reset rate limiter
            from src.middleware.rate_limiter import letter_generation_limiter
            letter_generation_limiter.requests.clear()
            
            # Make requests up to the limit (30 per minute)
            request_data = {
                "report_id": str(uuid4()),
                "jurisdiction": "federal",
                "attorney_info": {
                    "name": "Test",
                    "firm": "Test Firm",
                    "email": "test@test.com"
                }
            }
            
            # Simulate rapid requests
            responses = []
            for i in range(35):  # Try to exceed limit
                response = test_client.post(
                    "/api/agents/good-faith-letter/generate-letter",
                    json=request_data,
                    headers={"X-Case-ID": "test-case"}
                )
                responses.append(response.status_code)
                
                # After 30 requests, should get 429
                if i >= 30:
                    assert response.status_code == 429
                    assert "Rate limit exceeded" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_access_control(self, test_client):
        """Test case isolation prevents cross-case access."""
        letter_id = uuid4()
        
        # User A from Case A tries to access letter
        with patch('src.api.agents.good_faith_letter_endpoints.get_agent_security_context') as mock_get_context:
            mock_context_a = Mock()
            mock_context_a.case_id = "case-a"
            mock_context_a.case_name = "Case_A"
            mock_context_a.user_id = "user-a"
            mock_get_context.return_value = mock_context_a
            
            # Mock service returns None (not found due to case isolation)
            with patch('src.services.good_faith_letter_agent_service.GoodFaithLetterAgentService') as mock_service_class:
                mock_service = mock_service_class.return_value
                mock_service.get_letter = AsyncMock(return_value=None)
                
                response = test_client.get(
                    f"/api/agents/good-faith-letter/preview/{letter_id}",
                    headers={"X-Case-ID": "case-a"}
                )
                
                assert response.status_code == 404
                assert "Letter not found" in response.json()["detail"]
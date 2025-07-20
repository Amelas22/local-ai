"""
Unit tests for ReportStorage service.

Tests database operations for report storage, versioning,
and retrieval with mocked database sessions.
"""

from datetime import datetime, timedelta
from uuid import uuid4
import pytest
from unittest.mock import AsyncMock, MagicMock

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.deficiency_models import (
    DeficiencyItem,
    DeficiencyReport,
    GeneratedReport,
)
from src.services.report_storage import ReportStorage


class TestReportStorage:
    """Test suite for ReportStorage service."""

    @pytest.fixture
    def mock_db_session(self):
        """Create mock database session."""
        session = AsyncMock(spec=AsyncSession)
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        session.refresh = AsyncMock()
        session.add = MagicMock()
        session.get = AsyncMock()
        session.execute = AsyncMock()
        return session

    @pytest.fixture
    def storage(self, mock_db_session):
        """Create ReportStorage instance with mocked session."""
        return ReportStorage(mock_db_session)

    @pytest.fixture
    def sample_report(self):
        """Create sample report for testing."""
        return DeficiencyReport(
            id=uuid4(),
            case_name="Test_Case_2024",
            production_id=uuid4(),
            rtp_document_id=uuid4(),
            oc_response_document_id=uuid4(),
            analysis_status="completed",
            total_requests=2,
            summary_statistics={"fully_produced": 1, "not_produced": 1},
        )

    @pytest.fixture
    def sample_items(self):
        """Create sample deficiency items."""
        report_id = uuid4()
        return [
            DeficiencyItem(
                id=uuid4(),
                report_id=report_id,
                request_number="RFP No. 1",
                request_text="All documents",
                oc_response_text="Produced",
                classification="fully_produced",
                confidence_score=0.95,
            ),
            DeficiencyItem(
                id=uuid4(),
                report_id=report_id,
                request_number="RFP No. 2",
                request_text="All emails",
                oc_response_text="None exist",
                classification="not_produced",
                confidence_score=0.90,
            ),
        ]

    @pytest.mark.asyncio
    async def test_save_new_report(self, storage, sample_report, sample_items):
        """Test saving a new report."""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar.return_value = None  # Report doesn't exist
        storage.db.execute.return_value = mock_result

        # Act
        result = await storage.save_report(sample_report, sample_items, "test_user")

        # Assert
        storage.db.execute.assert_called()
        storage.db.commit.assert_called_once()
        assert result == sample_report

    @pytest.mark.asyncio
    async def test_save_existing_report_creates_version(
        self, storage, sample_report, sample_items
    ):
        """Test updating existing report creates version."""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar.return_value = 1  # Existing version
        storage.db.execute.return_value = mock_result

        # Act
        result = await storage.save_report(sample_report, sample_items, "test_user")

        # Assert
        assert sample_report.version == 2
        assert sample_report.updated_at is not None
        storage.db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_report_rollback_on_error(
        self, storage, sample_report, sample_items
    ):
        """Test rollback on save error."""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar.return_value = None
        storage.db.execute.return_value = mock_result
        storage.db.commit.side_effect = Exception("DB Error")

        # Act & Assert
        with pytest.raises(Exception, match="DB Error"):
            await storage.save_report(sample_report, sample_items)

        storage.db.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_report_with_case_isolation(self, storage):
        """Test getting report with case isolation."""
        # Arrange
        report_id = uuid4()
        case_name = "Test_Case"
        prod_id = uuid4()
        rtp_id = uuid4()
        oc_id = uuid4()
        
        mock_row = MagicMock()
        mock_row.id = str(report_id)
        mock_row.case_name = case_name
        mock_row.production_id = str(prod_id)
        mock_row.rtp_document_id = str(rtp_id)
        mock_row.oc_response_document_id = str(oc_id)
        mock_row.analysis_status = "completed"
        mock_row.created_at = datetime.utcnow()
        mock_row.completed_at = datetime.utcnow()
        mock_row.total_requests = 10
        mock_row.summary_statistics = '{"fully_produced": 5}'
        mock_row.analyzed_by = "test_user"
        mock_row.updated_at = datetime.utcnow()
        mock_row.version = 1
        
        mock_result = MagicMock()
        mock_result.first.return_value = mock_row
        storage.db.execute.return_value = mock_result

        # Act
        result = await storage.get_report(report_id, case_name)

        # Assert
        assert result is not None
        assert result.id == report_id
        assert result.case_name == case_name

    @pytest.mark.asyncio
    async def test_get_report_items(self, storage, sample_items):
        """Test getting report items."""
        # Arrange
        report_id = uuid4()
        
        # Create mock rows for items
        mock_rows = []
        for item in sample_items:
            mock_row = MagicMock()
            mock_row.id = str(item.id)
            mock_row.report_id = str(report_id)
            mock_row.request_number = item.request_number
            mock_row.request_text = item.request_text
            mock_row.oc_response_text = item.oc_response_text
            mock_row.classification = item.classification
            mock_row.confidence_score = item.confidence_score
            mock_row.evidence_chunks = '[]'
            mock_row.reviewer_notes = None
            mock_row.modified_by = None
            mock_row.created_at = datetime.utcnow()
            mock_row.updated_at = datetime.utcnow()
            mock_rows.append(mock_row)
        
        mock_result = MagicMock()
        mock_result.__iter__ = lambda self: iter(mock_rows)
        storage.db.execute.return_value = mock_result

        # Act
        result = await storage.get_report_items(report_id)

        # Assert
        assert len(result) == 2
        assert result[0].request_number == "RFP No. 1"

    @pytest.mark.asyncio
    async def test_list_reports(self, storage):
        """Test listing reports for a case."""
        # Arrange
        case_name = "Test_Case"
        
        # Create mock rows for reports
        mock_rows = []
        for _ in range(3):
            mock_row = MagicMock()
            mock_row.id = str(uuid4())
            mock_row.case_name = case_name
            mock_row.production_id = str(uuid4())
            mock_row.rtp_document_id = str(uuid4())
            mock_row.oc_response_document_id = str(uuid4())
            mock_row.analysis_status = "completed"
            mock_row.created_at = datetime.utcnow()
            mock_row.completed_at = datetime.utcnow()
            mock_row.total_requests = 10
            mock_row.summary_statistics = '{}'
            mock_row.analyzed_by = "test_user"
            mock_row.updated_at = datetime.utcnow()
            mock_row.version = 1
            mock_rows.append(mock_row)
        
        mock_result = MagicMock()
        mock_result.__iter__ = lambda self: iter(mock_rows)
        storage.db.execute.return_value = mock_result

        # Act
        result = await storage.list_reports(case_name, status="completed")

        # Assert
        assert len(result) == 3
        assert all(r.case_name == case_name for r in result)

    @pytest.mark.asyncio
    async def test_save_generated_report(self, storage):
        """Test saving a generated report."""
        # Arrange
        report_id = uuid4()

        # Act
        result = await storage.save_generated_report(
            report_id=report_id,
            format="pdf",
            content="<html>...</html>",
            options={"include_evidence": True},
        )

        # Assert
        storage.db.execute.assert_called()
        storage.db.commit.assert_called_once()
        assert result.format == "pdf"
        assert result.expires_at > datetime.utcnow()

    @pytest.mark.asyncio
    async def test_get_generated_report_not_expired(self, storage):
        """Test getting non-expired generated report."""
        # Arrange
        report_id = uuid4()
        gen_id = uuid4()
        
        mock_row = MagicMock()
        mock_row.id = str(gen_id)
        mock_row.report_id = str(report_id)
        mock_row.format = "pdf"
        mock_row.content = "PDF content"
        mock_row.file_path = None
        mock_row.generation_options = '{}'
        mock_row.created_at = datetime.utcnow()
        mock_row.expires_at = datetime.utcnow() + timedelta(days=1)
        
        mock_result = MagicMock()
        mock_result.first.return_value = mock_row
        storage.db.execute.return_value = mock_result

        # Act
        result = await storage.get_generated_report(report_id, "pdf")

        # Assert
        assert result is not None
        assert result.format == "pdf"

    @pytest.mark.asyncio
    async def test_cleanup_expired_reports(self, storage):
        """Test cleanup of expired reports."""
        # Arrange
        mock_result = MagicMock()
        mock_result.rowcount = 5
        storage.db.execute.return_value = mock_result

        # Act
        deleted_count = await storage.cleanup_expired_reports()

        # Assert
        assert deleted_count == 5
        storage.db.commit.assert_called_once()

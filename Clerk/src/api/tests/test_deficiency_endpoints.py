"""
Unit tests for deficiency API endpoints.

Tests report generation and retrieval endpoints with
mocked dependencies and case context.
"""

from datetime import datetime
from uuid import uuid4
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deficiency_endpoints import (
    ReportGenerationRequest,
    generate_report,
    get_report,
)
from src.models.deficiency_models import DeficiencyItem, DeficiencyReport


class TestDeficiencyEndpoints:
    """Test suite for deficiency API endpoints."""

    @pytest.fixture
    def mock_case_context(self):
        """Create mock case context."""
        context = MagicMock()
        context.case_id = str(uuid4())
        context.case_name = "Test_Case_2024"
        context.user_id = "test_user"
        context.permissions = ["read", "write"]
        return context

    @pytest.fixture
    def mock_db_session(self):
        """Create mock database session."""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def sample_report(self):
        """Create sample report."""
        return DeficiencyReport(
            id=uuid4(),
            case_name="Test_Case_2024",
            production_id=uuid4(),
            rtp_document_id=uuid4(),
            oc_response_document_id=uuid4(),
            analysis_status="completed",
            total_requests=5,
            summary_statistics={"fully_produced": 3, "not_produced": 2},
        )

    @pytest.fixture
    def sample_items(self):
        """Create sample deficiency items."""
        return [
            DeficiencyItem(
                id=uuid4(),
                report_id=uuid4(),
                request_number="RFP No. 1",
                request_text="All documents",
                oc_response_text="Produced",
                classification="fully_produced",
                confidence_score=0.95,
            )
        ]

    @pytest.mark.asyncio
    @patch("src.api.deficiency_endpoints.sio")
    @patch("src.api.deficiency_endpoints.ReportStorage")
    @patch("src.api.deficiency_endpoints.ReportGenerator")
    async def test_generate_report_success(
        self,
        mock_generator_class,
        mock_storage_class,
        mock_sio,
        mock_case_context,
        mock_db_session,
        sample_report,
        sample_items,
    ):
        """Test successful report generation."""
        # Arrange
        request = ReportGenerationRequest(analysis_id=sample_report.id, format="pdf")

        mock_storage = mock_storage_class.return_value
        mock_storage.get_report = AsyncMock(return_value=sample_report)
        mock_storage.get_report_items = AsyncMock(return_value=sample_items)

        mock_generator = mock_generator_class.return_value
        mock_generator.generate_and_store_report = AsyncMock(
            return_value={
                "report_id": str(sample_report.id),
                "version": 1,
                "format": "pdf",
                "generated_id": str(uuid4()),
                "expires_at": datetime.utcnow().isoformat(),
            }
        )

        mock_sio.emit = AsyncMock()

        # Act
        response = await generate_report(
            request=request, case_context=mock_case_context, db=mock_db_session
        )

        # Assert
        assert response.report_id == sample_report.id
        assert response.format == "pdf"
        assert response.status == "processing"
        assert mock_sio.emit.call_count == 2  # Start and complete events

    @pytest.mark.asyncio
    @patch("src.api.deficiency_endpoints.ReportStorage")
    async def test_generate_report_not_found(
        self, mock_storage_class, mock_case_context, mock_db_session
    ):
        """Test report generation with non-existent analysis."""
        # Arrange
        request = ReportGenerationRequest(analysis_id=uuid4(), format="json")

        mock_storage = mock_storage_class.return_value
        mock_storage.get_report = AsyncMock(return_value=None)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await generate_report(
                request=request, case_context=mock_case_context, db=mock_db_session
            )

        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail

    @pytest.mark.asyncio
    @patch("src.api.deficiency_endpoints.ReportStorage")
    async def test_generate_report_incomplete_analysis(
        self, mock_storage_class, mock_case_context, mock_db_session, sample_report
    ):
        """Test report generation with incomplete analysis."""
        # Arrange
        sample_report.analysis_status = "processing"
        request = ReportGenerationRequest(analysis_id=sample_report.id, format="json")

        mock_storage = mock_storage_class.return_value
        mock_storage.get_report = AsyncMock(return_value=sample_report)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await generate_report(
                request=request, case_context=mock_case_context, db=mock_db_session
            )

        assert exc_info.value.status_code == 400
        assert "completed analysis" in exc_info.value.detail

    @pytest.mark.asyncio
    @patch("src.api.deficiency_endpoints.ReportStorage")
    @patch("src.api.deficiency_endpoints.ReportGenerator")
    async def test_get_report_cached(
        self,
        mock_generator_class,
        mock_storage_class,
        mock_case_context,
        mock_db_session,
        sample_report,
    ):
        """Test getting cached report."""
        # Arrange
        report_id = sample_report.id

        mock_storage = mock_storage_class.return_value
        mock_storage.get_report = AsyncMock(return_value=sample_report)

        mock_generated = MagicMock()
        mock_generated.content = '{"report": "data"}'
        mock_storage.get_generated_report = AsyncMock(return_value=mock_generated)

        # Act
        response = await get_report(
            report_id=report_id,
            format="json",
            version=None,
            case_context=mock_case_context,
            db=mock_db_session,
        )

        # Assert
        assert response.body == b'{"report": "data"}'
        assert response.media_type == "application/json"
        mock_generator_class.assert_not_called()

    @pytest.mark.asyncio
    @patch("src.api.deficiency_endpoints.ReportStorage")
    @patch("src.api.deficiency_endpoints.ReportGenerator")
    async def test_get_report_generate_fresh(
        self,
        mock_generator_class,
        mock_storage_class,
        mock_case_context,
        mock_db_session,
        sample_report,
        sample_items,
    ):
        """Test generating fresh report when not cached."""
        # Arrange
        report_id = sample_report.id

        mock_storage = mock_storage_class.return_value
        mock_storage.get_report = AsyncMock(return_value=sample_report)
        mock_storage.get_generated_report = AsyncMock(return_value=None)
        mock_storage.get_report_items = AsyncMock(return_value=sample_items)
        mock_storage.save_generated_report = AsyncMock()

        mock_generator = mock_generator_class.return_value
        mock_generator.generate_report = AsyncMock(
            return_value="# Deficiency Report\n\nContent..."
        )

        # Act
        response = await get_report(
            report_id=report_id,
            format="markdown",
            version=None,
            case_context=mock_case_context,
            db=mock_db_session,
        )

        # Assert
        assert response.body == b"# Deficiency Report\n\nContent..."
        assert response.media_type == "text/markdown"
        mock_generator.generate_report.assert_called_once()
        mock_storage.save_generated_report.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.api.deficiency_endpoints.ReportStorage")
    async def test_get_report_not_found(
        self, mock_storage_class, mock_case_context, mock_db_session
    ):
        """Test getting non-existent report."""
        # Arrange
        report_id = uuid4()

        mock_storage = mock_storage_class.return_value
        mock_storage.get_report = AsyncMock(return_value=None)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await get_report(
                report_id=report_id,
                format="json",
                version=None,
                case_context=mock_case_context,
                db=mock_db_session,
            )

        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail

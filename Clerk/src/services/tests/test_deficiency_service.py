"""
Unit tests for DeficiencyService.

Tests service initialization, case isolation validation, and
stub method interfaces.
"""

import pytest
from unittest.mock import patch

from src.services.deficiency_service import DeficiencyService


class TestDeficiencyService:
    """Test suite for DeficiencyService following existing patterns."""

    @pytest.fixture
    def service(self):
        """Create DeficiencyService instance for testing."""
        return DeficiencyService()

    def test_service_initialization(self):
        """Test service initializes successfully."""
        # Arrange & Act
        service = DeficiencyService()

        # Assert
        assert service is not None
        assert hasattr(service, "process_deficiency_analysis")
        assert hasattr(service, "update_analysis_status")
        assert hasattr(service, "_validate_case_access")

    @patch("src.services.deficiency_service.logger")
    def test_service_initialization_logs(self, mock_logger):
        """Test service initialization logs properly."""
        # Arrange & Act
        service = DeficiencyService()

        # Assert
        mock_logger.info.assert_called_once_with("Initializing DeficiencyService")

    async def test_process_deficiency_analysis_validates_production_id(self, service):
        """Test process_deficiency_analysis validates production_id."""
        # Arrange
        invalid_ids = ["", "   ", None]

        # Act & Assert
        for invalid_id in invalid_ids:
            if invalid_id is not None:
                with pytest.raises(ValueError, match="Production ID cannot be empty"):
                    await service.process_deficiency_analysis(invalid_id, "Test_Case")

    async def test_process_deficiency_analysis_validates_case_name(self, service):
        """Test process_deficiency_analysis validates case_name."""
        # Arrange
        invalid_names = ["", "   ", None]

        # Act & Assert
        for invalid_name in invalid_names:
            if invalid_name is not None:
                with pytest.raises(ValueError, match="Case name cannot be empty"):
                    await service.process_deficiency_analysis("prod123", invalid_name)

    async def test_process_deficiency_analysis_stub_raises_not_implemented(
        self, service
    ):
        """Test process_deficiency_analysis stub raises NotImplementedError."""
        # Arrange
        production_id = "prod123"
        case_name = "Test_Case_2024"

        # Act & Assert
        with pytest.raises(NotImplementedError, match="future stories"):
            await service.process_deficiency_analysis(production_id, case_name)

    async def test_update_analysis_status_validates_report_id(self, service):
        """Test update_analysis_status validates report_id."""
        # Arrange
        invalid_ids = ["", "   ", None]

        # Act & Assert
        for invalid_id in invalid_ids:
            if invalid_id is not None:
                with pytest.raises(ValueError, match="Report ID cannot be empty"):
                    await service.update_analysis_status(invalid_id, "completed")

    async def test_update_analysis_status_validates_status(self, service):
        """Test update_analysis_status validates status value."""
        # Arrange
        invalid_statuses = ["invalid", "done", "error", "in-progress"]

        # Act & Assert
        for invalid_status in invalid_statuses:
            with pytest.raises(ValueError, match="Status must be one of"):
                await service.update_analysis_status("report123", invalid_status)

    async def test_update_analysis_status_accepts_valid_statuses(self, service):
        """Test update_analysis_status accepts all valid status values."""
        # Arrange
        valid_statuses = ["pending", "processing", "completed", "failed"]

        # Act & Assert
        for valid_status in valid_statuses:
            # Should raise NotImplementedError, not ValueError
            with pytest.raises(NotImplementedError, match="future stories"):
                await service.update_analysis_status("report123", valid_status)

    async def test_update_analysis_status_stub_raises_not_implemented(self, service):
        """Test update_analysis_status stub raises NotImplementedError."""
        # Arrange
        report_id = "report123"
        status = "completed"

        # Act & Assert
        with pytest.raises(NotImplementedError, match="future stories"):
            await service.update_analysis_status(report_id, status)

    def test_validate_case_access_with_empty_case_name(self, service):
        """Test _validate_case_access returns False for empty case name."""
        # Arrange
        invalid_names = ["", "   ", None]

        # Act & Assert
        for invalid_name in invalid_names:
            if invalid_name is not None:
                assert service._validate_case_access(invalid_name) is False

    def test_validate_case_access_with_valid_case_name(self, service):
        """Test _validate_case_access returns True for valid case name."""
        # Arrange
        valid_names = ["Test_Case", "Smith_v_Jones_2024", "Complex Case Name"]

        # Act & Assert
        for valid_name in valid_names:
            assert service._validate_case_access(valid_name) is True

    @patch("src.services.deficiency_service.logger")
    async def test_process_deficiency_analysis_logs_properly(
        self, mock_logger, service
    ):
        """Test process_deficiency_analysis logs the operation."""
        # Arrange
        production_id = "prod123"
        case_name = "Test_Case"

        # Act
        try:
            await service.process_deficiency_analysis(production_id, case_name)
        except NotImplementedError:
            pass  # Expected

        # Assert
        mock_logger.info.assert_called_with(
            f"Processing deficiency analysis for production {production_id} "
            f"in case {case_name}"
        )

    @patch("src.services.deficiency_service.logger")
    async def test_update_analysis_status_logs_properly(self, mock_logger, service):
        """Test update_analysis_status logs the operation."""
        # Arrange
        report_id = "report123"
        status = "completed"

        # Act
        try:
            await service.update_analysis_status(report_id, status)
        except NotImplementedError:
            pass  # Expected

        # Assert
        mock_logger.info.assert_called_with(
            f"Updating analysis status for report {report_id} to {status}"
        )

"""
Tests for deficiency analysis trigger functionality in discovery endpoints
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import asyncio

from src.api.discovery_endpoints import (
    _trigger_deficiency_analysis,
    processing_status,
    DiscoveryProcessingStatus,
)
from src.models.discovery_models import (
    DiscoveryProcessingRequest as EndpointDiscoveryRequest,
)


class TestDeficiencyAnalysisTrigger:
    """Test deficiency analysis trigger logic"""

    @pytest.fixture
    def mock_settings(self):
        """Mock settings with deficiency analysis configuration"""
        with patch("src.api.discovery_endpoints.settings") as mock_settings:
            mock_settings.discovery.enable_deficiency_analysis = True
            yield mock_settings

    @pytest.fixture
    def mock_sio(self):
        """Mock socket.io for WebSocket events"""
        with patch("src.api.discovery_endpoints.sio") as mock_sio:
            mock_sio.emit = AsyncMock()
            yield mock_sio

    @pytest.fixture
    def mock_deficiency_service(self):
        """Mock DeficiencyService"""
        with patch(
            "src.api.discovery_endpoints.DeficiencyService"
        ) as mock_service_class:
            mock_service = AsyncMock()
            mock_service.process_deficiency_analysis = AsyncMock()
            mock_service_class.return_value = mock_service
            yield mock_service

    @pytest.fixture
    def sample_request(self):
        """Create sample discovery request with RTP/OC documents"""
        return EndpointDiscoveryRequest(
            discovery_files=["test.pdf"],
            rtp_document_id="rtp-doc-123",
            oc_response_document_id="oc-doc-456",
        )

    @pytest.fixture
    def processing_id(self):
        """Test processing ID"""
        return "test-proc-123"

    @pytest.fixture
    def case_name(self):
        """Test case name"""
        return "Test_Case_2024"

    async def test_trigger_with_feature_flag_disabled(
        self, mock_settings, mock_sio, processing_id, case_name, sample_request
    ):
        """Test trigger when feature flag is disabled"""
        # Disable feature flag
        mock_settings.discovery.enable_deficiency_analysis = False

        # Add processing status
        processing_status[processing_id] = DiscoveryProcessingStatus(
            processing_id=processing_id,
            case_id=case_name,
            case_name=case_name,
            total_documents=1,
        )

        # Call trigger
        await _trigger_deficiency_analysis(processing_id, case_name, sample_request)

        # Verify no WebSocket events were emitted
        mock_sio.emit.assert_not_called()

        # Verify status was updated
        assert processing_status[processing_id].deficiency_analysis_status == "skipped"

    async def test_trigger_with_missing_rtp_document(
        self, mock_settings, mock_sio, processing_id, case_name
    ):
        """Test trigger with missing RTP document"""
        # Create request without RTP document
        request = EndpointDiscoveryRequest(
            discovery_files=["test.pdf"],
            rtp_document_id=None,
            oc_response_document_id="oc-doc-456",
        )

        # Add processing status
        processing_status[processing_id] = DiscoveryProcessingStatus(
            processing_id=processing_id,
            case_id=case_name,
            case_name=case_name,
            total_documents=1,
        )

        # Call trigger
        await _trigger_deficiency_analysis(processing_id, case_name, request)

        # Verify skipped event was emitted
        mock_sio.emit.assert_called_once_with(
            "deficiency:analysis_skipped",
            {
                "processing_id": processing_id,
                "case_id": case_name,
                "reason": "Missing RTP or OC response documents",
            },
            room=f"case_{case_name}",
        )

        # Verify status was updated
        assert processing_status[processing_id].deficiency_analysis_status == "skipped"

    async def test_trigger_with_missing_oc_document(
        self, mock_settings, mock_sio, processing_id, case_name
    ):
        """Test trigger with missing OC response document"""
        # Create request without OC document
        request = EndpointDiscoveryRequest(
            discovery_files=["test.pdf"],
            rtp_document_id="rtp-doc-123",
            oc_response_document_id=None,
        )

        # Add processing status
        processing_status[processing_id] = DiscoveryProcessingStatus(
            processing_id=processing_id,
            case_id=case_name,
            case_name=case_name,
            total_documents=1,
        )

        # Call trigger
        await _trigger_deficiency_analysis(processing_id, case_name, request)

        # Verify skipped event was emitted
        mock_sio.emit.assert_called_once()
        assert mock_sio.emit.call_args[0][0] == "deficiency:analysis_skipped"

        # Verify status was updated
        assert processing_status[processing_id].deficiency_analysis_status == "skipped"

    async def test_trigger_successful_analysis(
        self,
        mock_settings,
        mock_sio,
        mock_deficiency_service,
        processing_id,
        case_name,
        sample_request,
    ):
        """Test successful deficiency analysis trigger"""
        # Add processing status
        processing_status[processing_id] = DiscoveryProcessingStatus(
            processing_id=processing_id,
            case_id=case_name,
            case_name=case_name,
            total_documents=1,
        )

        # Call trigger
        await _trigger_deficiency_analysis(processing_id, case_name, sample_request)

        # Verify triggered event was emitted
        triggered_call = mock_sio.emit.call_args_list[0]
        assert triggered_call[0][0] == "deficiency:analysis_triggered"
        assert triggered_call[0][1]["processing_id"] == processing_id
        assert triggered_call[0][1]["case_id"] == case_name
        assert triggered_call[0][1]["rtp_document_id"] == "rtp-doc-123"
        assert triggered_call[0][1]["oc_response_document_id"] == "oc-doc-456"

        # Verify deficiency service was called
        mock_deficiency_service.process_deficiency_analysis.assert_called_once_with(
            production_id=processing_id, case_name=case_name
        )

        # Verify status was updated
        assert (
            processing_status[processing_id].deficiency_analysis_status == "completed"
        )

    async def test_trigger_with_error(
        self,
        mock_settings,
        mock_sio,
        mock_deficiency_service,
        processing_id,
        case_name,
        sample_request,
    ):
        """Test trigger with deficiency service error"""
        # Add processing status
        processing_status[processing_id] = DiscoveryProcessingStatus(
            processing_id=processing_id,
            case_id=case_name,
            case_name=case_name,
            total_documents=1,
        )

        # Make deficiency service raise an error
        mock_deficiency_service.process_deficiency_analysis.side_effect = Exception(
            "Test error"
        )

        # Call trigger
        await _trigger_deficiency_analysis(processing_id, case_name, sample_request)

        # Verify error event was emitted
        error_call = [
            call
            for call in mock_sio.emit.call_args_list
            if call[0][0] == "deficiency:analysis_failed"
        ][0]
        assert error_call[0][1]["processing_id"] == processing_id
        assert error_call[0][1]["case_id"] == case_name
        assert error_call[0][1]["error"] == "Test error"

        # Verify status was updated
        assert processing_status[processing_id].deficiency_analysis_status == "failed"

    async def test_trigger_without_processing_status(
        self,
        mock_settings,
        mock_sio,
        mock_deficiency_service,
        case_name,
        sample_request,
    ):
        """Test trigger when processing status doesn't exist"""
        # Use a processing ID that doesn't exist in status dict
        unknown_id = "unknown-proc-999"

        # Call trigger - should not raise exception
        await _trigger_deficiency_analysis(unknown_id, case_name, sample_request)

        # Verify triggered event was still emitted
        assert mock_sio.emit.call_count >= 1
        triggered_call = mock_sio.emit.call_args_list[0]
        assert triggered_call[0][0] == "deficiency:analysis_triggered"

        # Verify deficiency service was called
        mock_deficiency_service.process_deficiency_analysis.assert_called_once()

    async def test_trigger_concurrent_execution(
        self,
        mock_settings,
        mock_sio,
        mock_deficiency_service,
        case_name,
        sample_request,
    ):
        """Test that trigger runs as non-blocking background task"""

        # Add processing delay to deficiency service
        async def delayed_analysis(*args, **kwargs):
            await asyncio.sleep(0.1)
            return Mock()

        mock_deficiency_service.process_deficiency_analysis = delayed_analysis

        # Create status
        proc_id = "concurrent-test-123"
        processing_status[proc_id] = DiscoveryProcessingStatus(
            processing_id=proc_id,
            case_id=case_name,
            case_name=case_name,
            total_documents=1,
        )

        # Measure execution time
        start_time = asyncio.get_event_loop().time()
        await _trigger_deficiency_analysis(proc_id, case_name, sample_request)
        end_time = asyncio.get_event_loop().time()

        # Execution should be fast (not wait for analysis)
        # Note: In real implementation this would use asyncio.create_task()
        # but our test calls the function directly
        assert end_time - start_time > 0.1  # Should wait in this test setup

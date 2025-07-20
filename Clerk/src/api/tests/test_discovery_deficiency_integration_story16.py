"""
Integration tests for discovery processing with deficiency analysis trigger
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import asyncio
import base64
import uuid

from src.api.discovery_endpoints import processing_status, DiscoveryProcessingStatus
from src.models.unified_document_models import DiscoveryProductionResult, DiscoverySegment
from src.models.discovery_models import (
    DiscoveryProcessingRequest as EndpointDiscoveryRequest,
)


class TestDiscoveryDeficiencyIntegration:
    """Integration tests for discovery with deficiency analysis"""

    @pytest.fixture
    def mock_dependencies(self):
        """Mock all external dependencies for integration testing"""
        with (
            patch("src.api.discovery_endpoints.settings") as mock_settings,
            patch("src.api.discovery_endpoints.sio") as mock_sio,
            patch(
                "src.api.discovery_endpoints.DeficiencyService"
            ) as mock_deficiency_service,
            patch(
                "src.api.discovery_endpoints.UnifiedDocumentManager"
            ) as mock_doc_manager,
            patch("src.api.discovery_endpoints.EnhancedChunker"),
            patch("src.api.discovery_endpoints.EmbeddingGenerator"),
            patch("src.api.discovery_endpoints.FactExtractor") as mock_fact_extractor,
            patch("src.api.discovery_endpoints.QdrantVectorStore") as mock_vector_store,
            patch(
                "src.document_processing.discovery_splitter.DiscoveryProductionProcessor"
            ) as mock_discovery_processor,
            patch(
                "src.api.discovery_endpoints.emit_discovery_started"
            ) as mock_emit_started,
            patch(
                "src.api.discovery_endpoints.emit_processing_completed"
            ) as mock_emit_completed,
            patch("src.api.discovery_endpoints.emit_document_found"),
            patch("src.api.discovery_endpoints.emit_document_stored"),
            patch(
                "src.api.discovery_endpoints.store_processing_result"
            ) as mock_store_result,
        ):
            # Configure settings
            mock_settings.discovery.enable_deficiency_analysis = True

            # Configure WebSocket
            mock_sio.emit = AsyncMock()

            # Configure deficiency service
            deficiency_service = AsyncMock()
            deficiency_service.process_deficiency_analysis = AsyncMock()
            mock_deficiency_service.return_value = deficiency_service

            # Configure document processing
            mock_doc_manager.return_value.process_and_store_document = AsyncMock(
                return_value=Mock(
                    doc_id="doc-123", chunks=["chunk1", "chunk2"], page_count=10
                )
            )

            # Configure fact extraction
            fact_extractor = AsyncMock()
            fact_extractor.extract_facts_from_chunks = AsyncMock(
                return_value=[
                    Mock(id="fact-1", content="Test fact 1"),
                    Mock(id="fact-2", content="Test fact 2"),
                ]
            )
            mock_fact_extractor.return_value = fact_extractor

            # Configure discovery processor
            discovery_processor = Mock()
            discovery_processor.process_discovery_production = AsyncMock(
                return_value=DiscoveryProductionResult(
                    production_id="prod-123",
                    case_name="Integration_Test_Case",
                    production_batch="BATCH001",
                    source_pdf_path="/tmp/test.pdf",
                    total_pages=10,
                    segments_found=[
                        DiscoverySegment(
                            segment_id="seg-1",
                            case_name="Integration_Test_Case",
                            document_type="email_correspondence",
                            start_page=1,
                            end_page=5,
                            confidence_score=0.95,
                            production_batch="BATCH001"
                        ),
                        DiscoverySegment(
                            segment_id="seg-2",
                            case_name="Integration_Test_Case",
                            document_type="contract",
                            start_page=6,
                            end_page=10,
                            confidence_score=0.92,
                            production_batch="BATCH001"
                        )
                    ],
                    processing_windows=2,
                    average_confidence_score=0.95
                )
            )
            mock_discovery_processor.return_value = discovery_processor

            # Configure vector store
            mock_vector_store.return_value.hybrid_search = AsyncMock(return_value=[])

            yield {
                "settings": mock_settings,
                "sio": mock_sio,
                "deficiency_service": deficiency_service,
                "doc_manager": mock_doc_manager,
                "fact_extractor": fact_extractor,
                "emit_started": mock_emit_started,
                "emit_completed": mock_emit_completed,
                "store_result": mock_store_result,
            }

    async def test_complete_discovery_with_deficiency_trigger(self, mock_dependencies):
        """Test complete discovery flow with deficiency analysis trigger"""
        from src.api.discovery_endpoints import (
            _process_discovery_core,
            _trigger_deficiency_analysis,
        )

        # Setup test data
        processing_id = str(uuid.uuid4())
        case_name = "Integration_Test_Case"

        # Create discovery files
        discovery_files = [
            {"content": base64.b64decode("JVBERi0xLjQKMSAwIG9iago8PC9UeXBlL0NhdGFsb2cvUGFnZXMgMiAwIFI+PgplbmRvYmoKMiAwIG9iago8PC9UeXBlL1BhZ2VzL0tpZHNbMyAwIFJdL0NvdW50IDE+PgplbmRvYmoKMyAwIG9iago8PC9UeXBlL1BhZ2UvTWVkaWFCb3hbMCAwIDYxMiA3OTJdL1BhcmVudCAyIDAgUi9SZXNvdXJjZXM8PD4+Pj4KZW5kb2JqCnhyZWYKMCA0CjAwMDAwMDAwMDAgNjU1MzUgZiAKMDAwMDAwMDAwOSAwMDAwMCBuIAowMDAwMDAwMDU4IDAwMDAwIG4gCjAwMDAwMDAxMTcgMDAwMDAgbiAKdHJhaWxlcgo8PC9TaXplIDQvUm9vdCAxIDAgUj4+CnN0YXJ0eHJlZgoyMDMKJSVFT0Y="), "filename": "test_discovery.pdf"}
        ]

        # Create request with RTP/OC documents
        request = EndpointDiscoveryRequest(
            discovery_files=["test_discovery.pdf"],
            rtp_document_id="rtp-doc-456",
            oc_response_document_id="oc-doc-789",
        )

        # Initialize processing status
        processing_status[processing_id] = DiscoveryProcessingStatus(
            processing_id=processing_id,
            case_id=case_name,
            case_name=case_name,
            total_documents=1,
        )

        # Run discovery processing
        result = await _process_discovery_core(
            processing_id=processing_id,
            case_name=case_name,
            discovery_files=discovery_files,
            production_metadata={
                "production_batch": "BATCH001",
                "producing_party": "Test Party",
            },
            enable_fact_extraction=True,
        )

        # Trigger deficiency analysis
        await _trigger_deficiency_analysis(processing_id, case_name, request)

        # Verify discovery completed
        assert result["status"] == "completed"
        assert result["facts_extracted"] == 2

        # Verify deficiency was triggered
        assert mock_dependencies[
            "deficiency_service"
        ].process_deficiency_analysis.called
        assert mock_dependencies[
            "deficiency_service"
        ].process_deficiency_analysis.call_args[1] == {
            "production_id": processing_id,
            "case_name": case_name,
        }

        # Verify WebSocket events
        deficiency_events = [
            call
            for call in mock_dependencies["sio"].emit.call_args_list
            if call[0][0].startswith("deficiency:")
        ]
        assert len(deficiency_events) == 1
        assert deficiency_events[0][0][0] == "deficiency:analysis_triggered"

        # Verify status tracking
        assert (
            processing_status[processing_id].deficiency_analysis_status == "completed"
        )

    async def test_discovery_without_deficiency_documents(self, mock_dependencies):
        """Test discovery when RTP/OC documents are not provided"""
        from src.api.discovery_endpoints import _trigger_deficiency_analysis

        # Setup test data
        processing_id = str(uuid.uuid4())
        case_name = "Test_Case_No_Deficiency"

        # Create request without RTP/OC documents
        request = EndpointDiscoveryRequest(
            discovery_files=["test_discovery.pdf"],
            rtp_document_id=None,  # No RTP document
            oc_response_document_id=None,  # No OC document
        )

        # Initialize processing status
        processing_status[processing_id] = DiscoveryProcessingStatus(
            processing_id=processing_id,
            case_id=case_name,
            case_name=case_name,
            total_documents=1,
        )

        # Trigger deficiency analysis
        await _trigger_deficiency_analysis(processing_id, case_name, request)

        # Verify deficiency was NOT triggered
        assert not mock_dependencies[
            "deficiency_service"
        ].process_deficiency_analysis.called

        # Verify skipped event was emitted
        skipped_events = [
            call
            for call in mock_dependencies["sio"].emit.call_args_list
            if call[0][0] == "deficiency:analysis_skipped"
        ]
        assert len(skipped_events) == 1
        assert (
            "Missing RTP or OC response documents" in skipped_events[0][0][1]["reason"]
        )

        # Verify status tracking
        assert processing_status[processing_id].deficiency_analysis_status == "skipped"

    async def test_discovery_with_deficiency_service_failure(self, mock_dependencies):
        """Test discovery when deficiency service fails"""
        from src.api.discovery_endpoints import _trigger_deficiency_analysis

        # Setup test data
        processing_id = str(uuid.uuid4())
        case_name = "Test_Case_Failure"

        # Make deficiency service fail
        mock_dependencies[
            "deficiency_service"
        ].process_deficiency_analysis.side_effect = Exception(
            "Deficiency service error"
        )

        # Create request with RTP/OC documents
        request = EndpointDiscoveryRequest(
            discovery_files=["test_discovery.pdf"],
            rtp_document_id="rtp-doc-123",
            oc_response_document_id="oc-doc-456",
        )

        # Initialize processing status
        processing_status[processing_id] = DiscoveryProcessingStatus(
            processing_id=processing_id,
            case_id=case_name,
            case_name=case_name,
            total_documents=1,
        )

        # Trigger deficiency analysis
        await _trigger_deficiency_analysis(processing_id, case_name, request)

        # Verify failed event was emitted
        failed_events = [
            call
            for call in mock_dependencies["sio"].emit.call_args_list
            if call[0][0] == "deficiency:analysis_failed"
        ]
        assert len(failed_events) == 1
        assert failed_events[0][0][1]["error"] == "Deficiency service error"

        # Verify status tracking
        assert processing_status[processing_id].deficiency_analysis_status == "failed"

    async def test_discovery_with_feature_flag_disabled(self, mock_dependencies):
        """Test discovery with deficiency analysis feature flag disabled"""
        from src.api.discovery_endpoints import _trigger_deficiency_analysis

        # Disable feature flag
        mock_dependencies["settings"].discovery.enable_deficiency_analysis = False

        # Setup test data
        processing_id = str(uuid.uuid4())
        case_name = "Test_Case_Disabled"

        # Create request with RTP/OC documents
        request = EndpointDiscoveryRequest(
            discovery_files=["test_discovery.pdf"],
            rtp_document_id="rtp-doc-123",
            oc_response_document_id="oc-doc-456",
        )

        # Initialize processing status
        processing_status[processing_id] = DiscoveryProcessingStatus(
            processing_id=processing_id,
            case_id=case_name,
            case_name=case_name,
            total_documents=1,
        )

        # Trigger deficiency analysis
        await _trigger_deficiency_analysis(processing_id, case_name, request)

        # Verify deficiency was NOT triggered
        assert not mock_dependencies[
            "deficiency_service"
        ].process_deficiency_analysis.called

        # Verify no WebSocket events were emitted
        deficiency_events = [
            call
            for call in mock_dependencies["sio"].emit.call_args_list
            if call[0][0].startswith("deficiency:")
        ]
        assert len(deficiency_events) == 0

        # Verify status tracking
        assert processing_status[processing_id].deficiency_analysis_status == "skipped"

    async def test_concurrent_discovery_processing(self, mock_dependencies):
        """Test multiple concurrent discovery processes with deficiency analysis"""
        from src.api.discovery_endpoints import _trigger_deficiency_analysis

        # Create multiple processing jobs
        jobs = []
        for i in range(3):
            processing_id = f"concurrent-{i}"
            case_name = f"Concurrent_Case_{i}"

            request = EndpointDiscoveryRequest(
                discovery_files=[f"test_{i}.pdf"],
                rtp_document_id=f"rtp-{i}" if i > 0 else None,  # First one without RTP
                oc_response_document_id=f"oc-{i}",
            )

            processing_status[processing_id] = DiscoveryProcessingStatus(
                processing_id=processing_id,
                case_id=case_name,
                case_name=case_name,
                total_documents=1,
            )

            jobs.append(_trigger_deficiency_analysis(processing_id, case_name, request))

        # Run all concurrently
        await asyncio.gather(*jobs)

        # Verify results
        assert (
            processing_status["concurrent-0"].deficiency_analysis_status == "skipped"
        )  # No RTP
        assert (
            processing_status["concurrent-1"].deficiency_analysis_status == "completed"
        )
        assert (
            processing_status["concurrent-2"].deficiency_analysis_status == "completed"
        )

        # Verify correct number of service calls
        assert (
            mock_dependencies[
                "deficiency_service"
            ].process_deficiency_analysis.call_count
            == 2
        )

    async def test_case_isolation_in_deficiency_trigger(self, mock_dependencies):
        """Test that deficiency analysis maintains case isolation"""
        from src.api.discovery_endpoints import _trigger_deficiency_analysis

        # Setup two different cases
        case1_id = "case-iso-1"
        case1_name = "Case_One"
        case2_id = "case-iso-2"
        case2_name = "Case_Two"

        # Create requests for both cases
        request1 = EndpointDiscoveryRequest(
            discovery_files=["case1.pdf"],
            rtp_document_id="rtp-case1",
            oc_response_document_id="oc-case1",
        )

        request2 = EndpointDiscoveryRequest(
            discovery_files=["case2.pdf"],
            rtp_document_id="rtp-case2",
            oc_response_document_id="oc-case2",
        )

        # Initialize status for both
        processing_status[case1_id] = DiscoveryProcessingStatus(
            processing_id=case1_id,
            case_id=case1_name,
            case_name=case1_name,
            total_documents=1,
        )

        processing_status[case2_id] = DiscoveryProcessingStatus(
            processing_id=case2_id,
            case_id=case2_name,
            case_name=case2_name,
            total_documents=1,
        )

        # Trigger for both cases
        await _trigger_deficiency_analysis(case1_id, case1_name, request1)
        await _trigger_deficiency_analysis(case2_id, case2_name, request2)

        # Verify service was called with correct case isolation
        calls = mock_dependencies[
            "deficiency_service"
        ].process_deficiency_analysis.call_args_list
        assert len(calls) == 2
        assert calls[0][1]["case_name"] == case1_name
        assert calls[1][1]["case_name"] == case2_name

        # Verify WebSocket events are case-scoped
        ws_calls = mock_dependencies["sio"].emit.call_args_list
        case1_events = [c for c in ws_calls if f"case_{case1_name}" in str(c)]
        case2_events = [c for c in ws_calls if f"case_{case2_name}" in str(c)]
        assert len(case1_events) > 0
        assert len(case2_events) > 0

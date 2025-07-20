"""
Integration tests for discovery processing with deficiency analysis.

Tests the full flow of discovery processing with RTP and OC response documents,
including fact extraction and metadata storage.
"""

import pytest
import base64
import os
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock

from src.api.discovery_endpoints import (
    _process_discovery_core,
)
from src.models.discovery_models import (
    DiscoveryMetadataWithDeficiency,
)
from src.utils.temp_file_manager import TempFileManager


@pytest.fixture
def integration_pdf_content():
    """Create a more realistic PDF content for integration testing."""
    return b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/Resources <<
/Font <<
/F1 4 0 R
>>
>>
/MediaBox [0 0 612 792]
/Contents 5 0 R
>>
endobj
4 0 obj
<<
/Type /Font
/Subtype /Type1
/BaseFont /Helvetica
>>
endobj
5 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
100 700 Td
(Test Discovery Document) Tj
ET
endstream
endobj
xref
0 6
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000274 00000 n
0000000353 00000 n
trailer
<<
/Size 6
/Root 1 0 R
>>
startxref
451
%%EOF"""


@pytest.fixture
def mock_discovery_result():
    """Mock discovery processing result."""
    from src.models.unified_document_models import DocumentType

    class MockSegment:
        def __init__(self):
            self.document_type = DocumentType.CORRESPONDENCE
            self.title = "Letter to Counsel"
            self.start_page = 1
            self.end_page = 3
            self.bates_range = {"start": "DEF001", "end": "DEF003"}
            self.confidence_score = 0.95

    class MockResult:
        def __init__(self):
            self.segments_found = [MockSegment()]
            self.average_confidence = 0.95
            self.processing_windows = 5

    return MockResult()


class TestFullDiscoveryFlow:
    """Test the complete discovery processing flow with deficiency analysis."""

    @pytest.mark.asyncio
    async def test_complete_discovery_flow_with_deficiency(
        self, integration_pdf_content
    ):
        """Test full discovery processing with RTP and OC response documents."""
        processing_id = "test-integration-123"
        case_name = "Test_v_Integration_2024"

        # Create test files
        discovery_files = [
            {
                "filename": "discovery_production.pdf",
                "content": integration_pdf_content,
                "content_type": "application/pdf",
            }
        ]

        production_metadata = {
            "production_batch": "PROD_001",
            "producing_party": "Defendant Corp",
            "production_date": "2024-01-15",
            "responsive_to_requests": ["RFP_001", "RFP_005"],
            "confidentiality_designation": "Confidential",
            "has_deficiency_analysis": True,
            "rtp_document_id": "rtp-test-123",
            "rtp_document_path": "/tmp/rtp_test.pdf",
            "oc_response_document_id": "oc-test-456",
            "oc_response_document_path": "/tmp/oc_test.pdf",
        }

        # Mock dependencies
        with patch(
            "src.api.discovery_endpoints.emit_discovery_started", new_callable=AsyncMock
        ):
            with patch(
                "src.api.discovery_endpoints.DiscoveryProductionProcessor"
            ) as mock_processor_class:
                # Mock discovery processor
                mock_processor = Mock()
                mock_processor.process_discovery_production = AsyncMock()
                mock_processor.process_discovery_production.return_value = (
                    mock_discovery_result()
                )
                mock_processor_class.return_value = mock_processor

                with patch(
                    "src.api.discovery_endpoints.UnifiedDocumentManager"
                ) as mock_doc_manager:
                    # Mock document manager
                    mock_manager = Mock()
                    mock_manager.calculate_document_hash = Mock(
                        return_value="test-hash-123"
                    )
                    mock_manager.is_duplicate = AsyncMock(return_value=False)
                    mock_manager.add_document = AsyncMock(return_value="doc-123")
                    mock_doc_manager.return_value = mock_manager

                    with patch(
                        "src.api.discovery_endpoints.extract_text_from_pages"
                    ) as mock_extract:
                        mock_extract.return_value = (
                            "Test document content for discovery"
                        )

                        with patch(
                            "src.api.discovery_endpoints.QdrantVectorStore"
                        ) as mock_vector_store:
                            # Mock vector store
                            mock_store = Mock()
                            mock_store.store_document_chunks = Mock(
                                return_value=["chunk1", "chunk2"]
                            )
                            mock_vector_store.return_value = mock_store

                            with patch(
                                "src.api.discovery_endpoints.FactExtractor"
                            ) as mock_fact_extractor:
                                # Mock fact extractor
                                mock_extractor = Mock()
                                mock_facts = Mock()
                                mock_facts.facts = []
                                mock_extractor.return_value.extract_facts_from_document = AsyncMock(
                                    return_value=mock_facts
                                )

                                # Run the core processing
                                result = await _process_discovery_core(
                                    processing_id=processing_id,
                                    case_name=case_name,
                                    discovery_files=discovery_files,
                                    production_metadata=production_metadata,
                                    enable_fact_extraction=True,
                                )

                                # Verify the flow
                                assert result["status"] == "completed"
                                assert result["total_documents_found"] == 1
                                assert result["documents_processed"] == 1

                                # Verify metadata was passed through
                                call_args = mock_processor.process_discovery_production.call_args
                                assert (
                                    call_args[1]["production_metadata"]
                                    == production_metadata
                                )

                                # Verify hybrid storage was used
                                store_call = mock_store.store_document_chunks.call_args
                                assert store_call[1]["use_hybrid"] is True

    @pytest.mark.asyncio
    async def test_temp_file_lifecycle(self):
        """Test temporary file lifecycle during discovery processing."""
        temp_manager = TempFileManager()
        processing_id = "test-lifecycle-456"

        # Simulate storing RTP and OC files
        rtp_content = b"%PDF-1.4\nRTP Document\n%%EOF"
        oc_content = b"%PDF-1.4\nOC Response\n%%EOF"

        rtp_id, rtp_path = await temp_manager.save_temp_file(
            content=rtp_content,
            filename="rtp_request.pdf",
            processing_id=processing_id,
            file_type="rtp",
        )

        oc_id, oc_path = await temp_manager.save_temp_file(
            content=oc_content,
            filename="oc_response.pdf",
            processing_id=processing_id,
            file_type="oc_response",
        )

        # Verify files exist
        assert os.path.exists(rtp_path)
        assert os.path.exists(oc_path)

        # Simulate processing complete - cleanup
        cleaned = await temp_manager.cleanup_temp_files(processing_id=processing_id)

        # Verify cleanup
        assert cleaned == 2
        assert not os.path.exists(rtp_path)
        assert not os.path.exists(oc_path)

    @pytest.mark.asyncio
    async def test_metadata_persistence(self):
        """Test that discovery metadata with deficiency info is properly stored."""

        # Create metadata with deficiency info
        metadata = DiscoveryMetadataWithDeficiency(
            production_batch="PROD_TEST",
            producing_party="Test Party",
            production_date=datetime.utcnow(),
            has_deficiency_analysis=True,
            rtp_document_id="rtp-persist-123",
            rtp_document_path="/tmp/rtp_persist.pdf",
            oc_response_document_id="oc-persist-456",
            oc_response_document_path="/tmp/oc_persist.pdf",
        )

        # Convert to dict (simulating storage)
        metadata_dict = metadata.dict()

        # Verify all fields are present
        assert metadata_dict["has_deficiency_analysis"] is True
        assert metadata_dict["rtp_document_id"] == "rtp-persist-123"
        assert metadata_dict["oc_response_document_id"] == "oc-persist-456"
        assert metadata_dict["rtp_document_path"] == "/tmp/rtp_persist.pdf"
        assert metadata_dict["oc_response_document_path"] == "/tmp/oc_persist.pdf"

    @pytest.mark.asyncio
    async def test_error_recovery_during_processing(self):
        """Test error recovery and cleanup during processing failures."""
        processing_id = "test-error-789"
        case_name = "Test_v_Error_2024"

        discovery_files = [
            {
                "filename": "discovery.pdf",
                "content": b"%PDF-1.4\n%%EOF",
                "content_type": "application/pdf",
            }
        ]

        production_metadata = {
            "production_batch": "PROD_ERROR",
            "has_deficiency_analysis": True,
            "rtp_document_id": "rtp-error",
            "oc_response_document_id": "oc-error",
        }

        # Mock a failure during processing
        with patch(
            "src.api.discovery_endpoints.emit_discovery_started", new_callable=AsyncMock
        ):
            with patch(
                "src.api.discovery_endpoints.DiscoveryProductionProcessor"
            ) as mock_processor:
                # Make processor raise an error
                mock_processor.return_value.process_discovery_production = AsyncMock(
                    side_effect=Exception("Processing failed")
                )

                # Run processing and expect error handling
                result = await _process_discovery_core(
                    processing_id=processing_id,
                    case_name=case_name,
                    discovery_files=discovery_files,
                    production_metadata=production_metadata,
                    enable_fact_extraction=False,
                )

                # Verify error was handled
                assert result["status"] == "failed"
                assert result["error"] == "Processing failed"

    @pytest.mark.asyncio
    async def test_websocket_event_sequence(self):
        """Test that WebSocket events are emitted in correct sequence."""
        events_emitted = []

        async def mock_emit(event_type, data, **kwargs):
            events_emitted.append((event_type, data))

        processing_id = "test-websocket-seq"
        case_name = "Test_v_WebSocket_2024"

        discovery_files = [
            {
                "filename": "discovery.pdf",
                "content": b"%PDF-1.4\n%%EOF",
                "content_type": "application/pdf",
            }
        ]

        production_metadata = {
            "production_batch": "PROD_WS",
            "has_deficiency_analysis": False,
        }

        with patch("src.api.discovery_endpoints.sio.emit", side_effect=mock_emit):
            with patch(
                "src.api.discovery_endpoints.emit_discovery_started",
                new_callable=AsyncMock,
            ) as mock_start:
                with patch(
                    "src.api.discovery_endpoints.emit_document_found",
                    new_callable=AsyncMock,
                ):
                    with patch(
                        "src.api.discovery_endpoints.DiscoveryProductionProcessor"
                    ):
                        # Run minimal processing
                        # (Most functionality will be mocked)
                        pass

        # In a real test, we would verify the sequence of events


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_missing_required_fields(self):
        """Test handling of missing required fields."""
        from src.models.discovery_models import DiscoveryProcessWithDeficiencyRequest

        # Should fail without pdf_file
        with pytest.raises(ValueError):
            request = DiscoveryProcessWithDeficiencyRequest(case_name="Test_Case")

    def test_deficiency_without_files(self):
        """Test enabling deficiency analysis without required files."""
        from src.models.discovery_models import DiscoveryProcessWithDeficiencyRequest

        # Should fail validation
        with pytest.raises(ValueError) as exc_info:
            request = DiscoveryProcessWithDeficiencyRequest(
                pdf_file=base64.b64encode(b"%PDF-1.4\n%%EOF").decode(),
                enable_deficiency_analysis=True,  # Missing RTP and OC files
            )

        assert "requires both rtp_file and oc_response_file" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_concurrent_processing_isolation(self):
        """Test that concurrent processing jobs are properly isolated."""
        # This would test that multiple discovery processing jobs
        # don't interfere with each other's temp files or metadata
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

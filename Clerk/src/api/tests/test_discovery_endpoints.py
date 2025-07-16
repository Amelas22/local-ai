"""
Tests for discovery processing endpoints with document splitting functionality
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from fastapi import UploadFile
from fastapi.testclient import TestClient
import base64
import json
from datetime import datetime
from io import BytesIO

from src.api.discovery_endpoints import router
from src.models.unified_document_models import UnifiedDocument, DocumentType
from src.document_processing.discovery_splitter import DiscoverySegment, DiscoveryProductionResult
from src.models.fact_models import CaseFact


class TestDiscoveryEndpoints:
    """Tests for discovery processing endpoints"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        from main import app
        return TestClient(app)

    @pytest.fixture
    def mock_dependencies(self):
        """Mock all external dependencies"""
        with patch('src.api.discovery_endpoints.vector_store') as mock_vector_store, \
             patch('src.api.discovery_endpoints.sio') as mock_sio, \
             patch('src.api.discovery_endpoints.FactExtractor') as mock_fact_extractor, \
             patch('src.api.discovery_endpoints.NormalizedDiscoveryProductionProcessor') as mock_discovery_processor, \
             patch('src.api.discovery_endpoints.UnifiedDocumentManager') as mock_doc_manager, \
             patch('src.api.discovery_endpoints.EnhancedChunker') as mock_chunker, \
             patch('src.api.discovery_endpoints.EmbeddingGenerator') as mock_embedder, \
             patch('src.api.discovery_endpoints.PDFExtractor') as mock_pdf_extractor:
            
            # Configure mocks
            mock_sio.emit = AsyncMock()
            mock_vector_store.upsert_chunk = AsyncMock()
            
            yield {
                'vector_store': mock_vector_store,
                'sio': mock_sio,
                'fact_extractor': mock_fact_extractor,
                'discovery_processor': mock_discovery_processor,
                'doc_manager': mock_doc_manager,
                'chunker': mock_chunker,
                'embedder': mock_embedder,
                'pdf_extractor': mock_pdf_extractor
            }

    @pytest.fixture
    def sample_pdf_content(self):
        """Sample PDF content for testing"""
        # This would be actual PDF bytes in real scenario
        return b"Mock PDF content"

    @pytest.fixture
    def sample_discovery_segments(self):
        """Sample discovery segments simulating document splitting"""
        return [
            DiscoverySegment(
                start_page=1,
                end_page=5,
                document_type=DocumentType.MOTION,
                confidence_score=0.95,
                title="Motion for Summary Judgment",
                bates_range="PROD0001-PROD0005",
                indicators=["MOTION FOR SUMMARY JUDGMENT", "Plaintiff moves"]
            ),
            DiscoverySegment(
                start_page=6,
                end_page=15,
                document_type=DocumentType.DEPOSITION,
                confidence_score=0.88,
                title="Deposition of John Smith",
                bates_range="PROD0006-PROD0015",
                indicators=["DEPOSITION OF", "Q:", "A:"]
            ),
            DiscoverySegment(
                start_page=16,
                end_page=20,
                document_type=DocumentType.CORRESPONDENCE,
                confidence_score=0.92,
                title="Letter to Opposing Counsel",
                bates_range="PROD0016-PROD0020",
                indicators=["Dear Counsel", "Sincerely"]
            )
        ]

    @pytest.fixture
    def sample_facts(self):
        """Sample extracted facts"""
        return [
            CaseFact(
                case_name="test_case",
                fact_text="The incident occurred on January 15, 2024",
                category="timeline",
                confidence=0.9,
                entities=["January 15, 2024"],
                dates=["2024-01-15"],
                source_metadata={
                    "document_id": "doc1",
                    "page": 3,
                    "bates_range": "PROD0003"
                }
            ),
            CaseFact(
                case_name="test_case",
                fact_text="John Smith was driving a 2022 Honda Accord",
                category="person",
                confidence=0.85,
                entities=["John Smith", "Honda Accord"],
                source_metadata={
                    "document_id": "doc2",
                    "page": 8,
                    "bates_range": "PROD0008"
                }
            )
        ]

    @pytest.mark.asyncio
    async def test_start_discovery_processing_with_file_upload(self, client, mock_dependencies, sample_pdf_content):
        """Test discovery processing with direct file upload"""
        # Arrange
        mock_discovery_processor = mock_dependencies['discovery_processor']
        mock_sio = mock_dependencies['sio']
        
        # Mock discovery processor to return segments
        mock_processor_instance = AsyncMock()
        mock_discovery_processor.return_value = mock_processor_instance
        mock_processor_instance.process_production_normalized = AsyncMock(return_value=DiscoveryProductionResult(
            segments_found=self.sample_discovery_segments(),
            total_pages=20,
            processing_windows=4,
            average_confidence=0.92,
            low_confidence_boundaries=[]
        ))

        # Mock document processing
        mock_doc_manager = mock_dependencies['doc_manager']
        mock_doc_manager_instance = AsyncMock()
        mock_doc_manager.return_value = mock_doc_manager_instance
        mock_doc_manager_instance.generate_document_hash = Mock(return_value="hash123")
        mock_doc_manager_instance.is_duplicate = AsyncMock(return_value=False)
        mock_doc_manager_instance.add_document = AsyncMock(return_value="doc_id_123")

        # Mock PDF text extraction
        mock_pdf_extractor = mock_dependencies['pdf_extractor']
        mock_pdf_extractor_instance = Mock()
        mock_pdf_extractor.return_value = mock_pdf_extractor_instance
        mock_pdf_extractor_instance.extract_text_from_pages = Mock(return_value="Sample document text")

        # Mock chunking
        mock_chunker = mock_dependencies['chunker']
        mock_chunker_instance = Mock()
        mock_chunker.return_value = mock_chunker_instance
        mock_chunker_instance.create_chunks_with_context = Mock(return_value=[
            Mock(chunk_id="chunk1", text="chunk text 1", metadata={}),
            Mock(chunk_id="chunk2", text="chunk text 2", metadata={})
        ])

        # Mock embedding generation
        mock_embedder = mock_dependencies['embedder']
        mock_embedder_instance = AsyncMock()
        mock_embedder.return_value = mock_embedder_instance
        mock_embedder_instance.generate_embedding = AsyncMock(return_value=[0.1] * 1536)

        # Mock fact extraction
        mock_fact_extractor = mock_dependencies['fact_extractor']
        mock_fact_extractor_instance = AsyncMock()
        mock_fact_extractor.return_value = mock_fact_extractor_instance
        mock_fact_extractor_instance.extract_facts_from_document = AsyncMock(return_value=self.sample_facts())

        # Prepare multipart form data
        files = [
            ("files", ("discovery_batch1.pdf", sample_pdf_content, "application/pdf"))
        ]
        
        # Act
        response = client.post(
            "/api/discovery/process",
            files=files,
            data={
                "case_name": "test_case",
                "producing_party": "Defendant ABC Corp",
                "production_batch": "BATCH001"
            },
            headers={"X-Case-ID": "test_case"}
        )

        # Assert
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "processing"
        assert "processing_id" in result

        # Verify WebSocket events were emitted
        mock_sio.emit.assert_any_call("discovery:started", {
            "processing_id": result["processing_id"],
            "case_name": "test_case",
            "total_files": 1
        })

    @pytest.mark.asyncio
    async def test_discovery_processing_with_document_splitting(self, mock_dependencies):
        """Test that discovery processing properly splits documents"""
        # This test verifies the core document splitting logic
        from src.api.discovery_endpoints import _process_discovery_async
        
        # Arrange
        mock_discovery_processor = mock_dependencies['discovery_processor']
        mock_sio = mock_dependencies['sio']
        
        # Setup processor to return multiple segments
        mock_processor_instance = AsyncMock()
        mock_discovery_processor.return_value = mock_processor_instance
        mock_processor_instance.process_production_normalized = AsyncMock(return_value=DiscoveryProductionResult(
            segments_found=self.sample_discovery_segments(),
            total_pages=20,
            processing_windows=4,
            average_confidence=0.92,
            low_confidence_boundaries=[]
        ))

        # Setup other mocks
        self._setup_processing_mocks(mock_dependencies)

        discovery_files = [{
            "filename": "test.pdf",
            "content": b"PDF content"
        }]

        # Act
        await _process_discovery_async(
            case_name="test_case",
            processing_id="test_proc_123",
            discovery_files=discovery_files,
            producing_party="Test Party",
            production_batch="BATCH001",
            enable_fact_extraction=True
        )

        # Assert - Verify document_found events for each segment
        assert mock_sio.emit.call_count >= 3  # At least 3 document_found events
        
        # Check that each segment was emitted as a separate document
        document_found_calls = [
            call for call in mock_sio.emit.call_args_list 
            if call[0][0] == "discovery:document_found"
        ]
        assert len(document_found_calls) == 3
        
        # Verify each document has correct metadata
        for i, call in enumerate(document_found_calls):
            event_data = call[0][1]
            assert "document_id" in event_data
            assert "title" in event_data
            assert "type" in event_data
            assert "bates_range" in event_data

    @pytest.mark.asyncio
    async def test_discovery_processing_websocket_events(self, mock_dependencies):
        """Test that all expected WebSocket events are emitted in correct order"""
        from src.api.discovery_endpoints import _process_discovery_async
        
        # Arrange
        self._setup_processing_mocks(mock_dependencies)
        mock_sio = mock_dependencies['sio']
        
        # Act
        await _process_discovery_async(
            case_name="test_case",
            processing_id="test_proc_123",
            discovery_files=[{"filename": "test.pdf", "content": b"PDF"}],
            enable_fact_extraction=True
        )

        # Assert - Check event sequence
        event_types = [call[0][0] for call in mock_sio.emit.call_args_list]
        
        # Verify critical events are present
        assert "discovery:started" in event_types
        assert "discovery:document_found" in event_types
        assert "discovery:chunking" in event_types
        assert "discovery:embedding" in event_types
        assert "discovery:fact_extracted" in event_types
        assert "discovery:completed" in event_types

    @pytest.mark.asyncio
    async def test_discovery_processing_error_handling(self, mock_dependencies):
        """Test error handling during discovery processing"""
        from src.api.discovery_endpoints import _process_discovery_async
        
        # Arrange
        mock_discovery_processor = mock_dependencies['discovery_processor']
        mock_sio = mock_dependencies['sio']
        
        # Make processor raise an error
        mock_processor_instance = AsyncMock()
        mock_discovery_processor.return_value = mock_processor_instance
        mock_processor_instance.process_production_normalized = AsyncMock(
            side_effect=Exception("PDF processing failed")
        )

        # Act
        await _process_discovery_async(
            case_name="test_case",
            processing_id="test_proc_123",
            discovery_files=[{"filename": "test.pdf", "content": b"PDF"}]
        )

        # Assert - Check error event was emitted
        error_calls = [
            call for call in mock_sio.emit.call_args_list 
            if call[0][0] == "discovery:error"
        ]
        assert len(error_calls) > 0
        assert "PDF processing failed" in str(error_calls[0])

    @pytest.mark.asyncio
    async def test_fact_extraction_per_document(self, mock_dependencies):
        """Test that facts are extracted for each discovered document"""
        from src.api.discovery_endpoints import _process_discovery_async
        
        # Arrange
        self._setup_processing_mocks(mock_dependencies)
        mock_sio = mock_dependencies['sio']
        mock_fact_extractor = mock_dependencies['fact_extractor']
        
        # Setup fact extractor to return different facts for each doc
        mock_extractor_instance = AsyncMock()
        mock_fact_extractor.return_value = mock_extractor_instance
        mock_extractor_instance.extract_facts_from_document = AsyncMock(
            side_effect=[
                [self.sample_facts()[0]],  # First document
                [self.sample_facts()[1]],  # Second document
                []  # Third document (no facts)
            ]
        )

        # Act
        await _process_discovery_async(
            case_name="test_case",
            processing_id="test_proc_123",
            discovery_files=[{"filename": "test.pdf", "content": b"PDF"}],
            enable_fact_extraction=True
        )

        # Assert - Verify fact extraction was called for each document
        assert mock_extractor_instance.extract_facts_from_document.call_count == 3
        
        # Verify fact_extracted events
        fact_events = [
            call for call in mock_sio.emit.call_args_list 
            if call[0][0] == "discovery:fact_extracted"
        ]
        assert len(fact_events) == 2  # Two facts total

    def _setup_processing_mocks(self, mock_dependencies):
        """Helper to setup common mocks for processing tests"""
        # Setup discovery processor
        mock_processor = AsyncMock()
        mock_dependencies['discovery_processor'].return_value = mock_processor
        mock_processor.process_production_normalized = AsyncMock(return_value=DiscoveryProductionResult(
            segments_found=self.sample_discovery_segments(),
            total_pages=20,
            processing_windows=4,
            average_confidence=0.92,
            low_confidence_boundaries=[]
        ))

        # Setup document manager
        mock_doc_manager = AsyncMock()
        mock_dependencies['doc_manager'].return_value = mock_doc_manager
        mock_doc_manager.generate_document_hash = Mock(return_value="hash123")
        mock_doc_manager.is_duplicate = AsyncMock(return_value=False)
        mock_doc_manager.add_document = AsyncMock(return_value="doc_id")

        # Setup PDF extractor
        mock_pdf = Mock()
        mock_dependencies['pdf_extractor'].return_value = mock_pdf
        mock_pdf.extract_text_from_pages = Mock(return_value="Document text")

        # Setup chunker
        mock_chunker = Mock()
        mock_dependencies['chunker'].return_value = mock_chunker
        mock_chunker.create_chunks_with_context = Mock(return_value=[
            Mock(chunk_id="chunk1", text="text", metadata={})
        ])

        # Setup embedder
        mock_embedder = AsyncMock()
        mock_dependencies['embedder'].return_value = mock_embedder
        mock_embedder.generate_embedding = AsyncMock(return_value=[0.1] * 1536)

        # Setup fact extractor
        mock_extractor = AsyncMock()
        mock_dependencies['fact_extractor'].return_value = mock_extractor
        mock_extractor.extract_facts_from_document = AsyncMock(return_value=[])


class TestDiscoveryStatusEndpoint:
    """Tests for discovery status endpoint"""
    
    @pytest.mark.asyncio
    async def test_get_discovery_status(self, client):
        """Test getting discovery processing status"""
        with patch('src.api.discovery_endpoints.get_processing_status') as mock_get_status:
            mock_get_status.return_value = {
                "processing_id": "test_123",
                "status": "completed",
                "documents_processed": 3,
                "facts_extracted": 10
            }
            
            response = client.get(
                "/api/discovery/status/test_123",
                headers={"X-Case-ID": "test_case"}
            )
            
            assert response.status_code == 200
            assert response.json()["status"] == "completed"
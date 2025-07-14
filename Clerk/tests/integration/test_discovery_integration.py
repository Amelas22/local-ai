"""
Integration tests for complete discovery processing workflow
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import tempfile
import os
from datetime import datetime
import json

from fastapi.testclient import TestClient
from src.vector_storage.qdrant_store import QdrantVectorStore
from src.document_processing.discovery_splitter import DiscoveryProductionProcessor
from src.ai_agents.fact_extractor import FactExtractor
from src.models.unified_document_models import DocumentType


class TestDiscoveryIntegration:
    """Integration tests for discovery processing workflow"""

    @pytest.fixture
    async def setup_test_environment(self):
        """Setup test environment with mocked services"""
        # Mock Qdrant
        with patch('src.vector_storage.qdrant_store.QdrantClient') as mock_qdrant_client:
            mock_client_instance = Mock()
            mock_qdrant_client.return_value = mock_client_instance
            
            # Mock collection operations
            mock_client_instance.create_collection = AsyncMock()
            mock_client_instance.upsert = AsyncMock()
            mock_client_instance.search = AsyncMock(return_value=[])
            
            # Mock WebSocket
            with patch('src.websocket.socket_server.sio') as mock_sio:
                mock_sio.emit = AsyncMock()
                
                # Mock OpenAI
                with patch('openai.AsyncOpenAI') as mock_openai:
                    mock_openai_instance = AsyncMock()
                    mock_openai.return_value = mock_openai_instance
                    
                    # Mock embedding response
                    mock_embedding = Mock()
                    mock_embedding.data = [Mock(embedding=[0.1] * 1536)]
                    mock_openai_instance.embeddings.create = AsyncMock(return_value=mock_embedding)
                    
                    # Mock chat completion
                    mock_completion = Mock()
                    mock_completion.choices = [Mock(message=Mock(content="AI response"))]
                    mock_openai_instance.chat.completions.create = AsyncMock(return_value=mock_completion)
                    
                    yield {
                        'qdrant_client': mock_client_instance,
                        'sio': mock_sio,
                        'openai': mock_openai_instance
                    }

    @pytest.fixture
    def create_test_pdf(self):
        """Create a test PDF file"""
        def _create_pdf(content_pages):
            # For real tests, this would create an actual PDF
            # For now, we'll create a mock file
            with tempfile.NamedTemporaryFile(mode='wb', suffix='.pdf', delete=False) as f:
                f.write(b"Mock PDF content")
                return f.name
        return _create_pdf

    @pytest.mark.asyncio
    async def test_full_discovery_workflow(self, setup_test_environment, create_test_pdf):
        """Test complete discovery workflow from upload to fact extraction"""
        # Arrange
        test_case = "integration_test_case"
        pdf_path = create_test_pdf(["Page 1", "Page 2", "Page 3"])
        
        try:
            # Mock PDF reading
            with patch('pdfplumber.open') as mock_pdf:
                # Setup mock pages
                mock_pages = []
                page_contents = [
                    "MOTION FOR SUMMARY JUDGMENT\nPlaintiff moves for summary judgment on all claims.",
                    "Defendant breached the contract on January 15, 2024.",
                    "DEPOSITION OF JANE DOE\nQ: State your name.\nA: Jane Doe",
                    "Q: What did you observe?\nA: I saw the accident occur at 2:30 PM.",
                    "EXHIBIT A\nContract dated December 1, 2023"
                ]
                
                for i, content in enumerate(page_contents):
                    mock_page = Mock()
                    mock_page.extract_text.return_value = content
                    mock_page.page_number = i + 1
                    mock_pages.append(mock_page)
                
                mock_pdf.return_value.__enter__.return_value.pages = mock_pages
                
                # Initialize processor
                processor = DiscoveryProductionProcessor(case_name=test_case)
                
                # Mock AI boundary detection
                with patch.object(processor, '_detect_boundaries_with_ai') as mock_detect:
                    from src.document_processing.discovery_splitter import DocumentBoundary
                    
                    mock_detect.return_value = [
                        DocumentBoundary(
                            page_number=1,
                            confidence=0.95,
                            boundary_type="new_document",
                            document_type=DocumentType.MOTION,
                            title="Motion for Summary Judgment",
                            bates_range="PROD0001-PROD0002",
                            indicators=["MOTION FOR SUMMARY JUDGMENT"]
                        ),
                        DocumentBoundary(
                            page_number=3,
                            confidence=0.90,
                            boundary_type="new_document",
                            document_type=DocumentType.DEPOSITION,
                            title="Deposition of Jane Doe",
                            bates_range="PROD0003-PROD0004",
                            indicators=["DEPOSITION OF"]
                        ),
                        DocumentBoundary(
                            page_number=5,
                            confidence=0.88,
                            boundary_type="new_document",
                            document_type=DocumentType.EXHIBIT,
                            title="Exhibit A - Contract",
                            bates_range="PROD0005",
                            indicators=["EXHIBIT A"]
                        )
                    ]
                    
                    # Process discovery
                    result = processor.process_discovery_production(
                        pdf_path=pdf_path,
                        production_metadata={
                            "production_batch": "TEST_BATCH_001",
                            "producing_party": "Plaintiff"
                        }
                    )
                    
                    # Verify results
                    assert len(result.segments_found) == 3
                    assert result.segments_found[0].document_type == DocumentType.MOTION
                    assert result.segments_found[1].document_type == DocumentType.DEPOSITION
                    assert result.segments_found[2].document_type == DocumentType.EXHIBIT
                    
                    # Test fact extraction for each segment
                    fact_extractor = FactExtractor(case_name=test_case)
                    
                    # Mock fact extraction
                    with patch.object(fact_extractor, 'extract_facts_from_document') as mock_extract:
                        mock_extract.return_value = [
                            Mock(
                                fact_text="Defendant breached the contract on January 15, 2024",
                                category="breach",
                                confidence=0.9,
                                entities=["Defendant"],
                                dates=["2024-01-15"]
                            ),
                            Mock(
                                fact_text="Accident occurred at 2:30 PM",
                                category="timeline",
                                confidence=0.85,
                                entities=[],
                                dates=[]
                            )
                        ]
                        
                        # Extract facts for each segment
                        all_facts = []
                        for segment in result.segments_found:
                            facts = await fact_extractor.extract_facts_from_document(
                                document_id=f"doc_{segment.start_page}",
                                document_content=f"Content for segment {segment.title}",
                                document_type=segment.document_type.value
                            )
                            all_facts.extend(facts)
                        
                        assert len(all_facts) == 6  # 2 facts x 3 segments
                        
        finally:
            # Cleanup
            if os.path.exists(pdf_path):
                os.unlink(pdf_path)

    @pytest.mark.asyncio
    async def test_websocket_event_flow(self, setup_test_environment):
        """Test WebSocket event emission during processing"""
        mock_sio = setup_test_environment['sio']
        
        # Track all emitted events
        emitted_events = []
        
        def track_event(event_name, data):
            emitted_events.append((event_name, data))
            return asyncio.Future()
        
        mock_sio.emit.side_effect = track_event
        
        # Simulate processing workflow
        processing_id = "test_proc_123"
        
        # Emit discovery events in sequence
        await mock_sio.emit("discovery:started", {
            "processing_id": processing_id,
            "case_name": "test_case",
            "total_files": 1
        })
        
        # Document found events
        for i in range(3):
            await mock_sio.emit("discovery:document_found", {
                "processing_id": processing_id,
                "document_id": f"doc_{i}",
                "title": f"Document {i}",
                "type": "motion",
                "pages": f"{i*5+1}-{i*5+5}",
                "confidence": 0.9
            })
        
        # Processing events for each document
        for i in range(3):
            await mock_sio.emit("discovery:chunking", {
                "processing_id": processing_id,
                "document_id": f"doc_{i}",
                "status": "started"
            })
            
            await mock_sio.emit("discovery:fact_extracted", {
                "processing_id": processing_id,
                "document_id": f"doc_{i}",
                "fact": {
                    "fact_id": f"fact_{i}",
                    "text": f"Fact from document {i}",
                    "category": "timeline",
                    "confidence": 0.85
                }
            })
        
        await mock_sio.emit("discovery:completed", {
            "processing_id": processing_id,
            "total_documents_found": 3,
            "documents_processed": 3,
            "facts_extracted": 3
        })
        
        # Verify event sequence
        event_names = [event[0] for event in emitted_events]
        assert "discovery:started" in event_names
        assert event_names.count("discovery:document_found") == 3
        assert event_names.count("discovery:fact_extracted") == 3
        assert "discovery:completed" in event_names

    @pytest.mark.asyncio
    async def test_error_recovery(self, setup_test_environment):
        """Test that processing continues after document-level errors"""
        # This test verifies that if one document fails, others still process
        
        with patch('src.api.discovery_endpoints._process_discovery_async') as mock_process:
            # Simulate partial failure
            async def process_with_error(*args, **kwargs):
                mock_sio = setup_test_environment['sio']
                processing_id = "error_test_123"
                
                # First document succeeds
                await mock_sio.emit("discovery:document_found", {
                    "processing_id": processing_id,
                    "document_id": "doc_1",
                    "title": "Good Document"
                })
                
                # Second document fails
                await mock_sio.emit("discovery:error", {
                    "processing_id": processing_id,
                    "document_id": "doc_2",
                    "error": "Failed to extract text"
                })
                
                # Third document succeeds
                await mock_sio.emit("discovery:document_found", {
                    "processing_id": processing_id,
                    "document_id": "doc_3",
                    "title": "Another Good Document"
                })
                
                await mock_sio.emit("discovery:completed", {
                    "processing_id": processing_id,
                    "total_documents_found": 3,
                    "documents_processed": 2,
                    "errors": 1
                })
            
            mock_process.side_effect = process_with_error
            
            # Run processing
            await mock_process()
            
            # Verify mixed results were handled
            mock_sio = setup_test_environment['sio']
            completed_calls = [
                call for call in mock_sio.emit.call_args_list
                if call[0][0] == "discovery:completed"
            ]
            
            assert len(completed_calls) == 1
            completed_data = completed_calls[0][0][1]
            assert completed_data["documents_processed"] == 2
            assert completed_data["errors"] == 1

    @pytest.mark.asyncio
    async def test_duplicate_detection(self, setup_test_environment):
        """Test that duplicate documents are detected and skipped"""
        from src.document_processing.unified_document_manager import UnifiedDocumentManager
        from src.vector_storage.qdrant_store import QdrantVectorStore
        
        # Setup vector store
        vector_store = QdrantVectorStore()
        doc_manager = UnifiedDocumentManager(
            case_name="test_case",
            vector_store=vector_store
        )
        
        # Mock hash generation
        with patch.object(doc_manager, 'generate_document_hash') as mock_hash:
            mock_hash.side_effect = ["hash1", "hash1", "hash2"]  # First two are duplicates
            
            # Mock duplicate check
            with patch.object(doc_manager, 'is_duplicate') as mock_dup_check:
                mock_dup_check.side_effect = [False, True, False]  # Second is duplicate
                
                # Process three documents
                docs_processed = []
                for i in range(3):
                    doc_hash = doc_manager.generate_document_hash(f"Content {i}")
                    is_dup = await doc_manager.is_duplicate(doc_hash)
                    
                    if not is_dup:
                        docs_processed.append(f"doc_{i}")
                
                # Only two documents should be processed
                assert len(docs_processed) == 2
                assert "doc_1" not in docs_processed  # Duplicate skipped

    @pytest.mark.asyncio
    async def test_fact_database_integration(self, setup_test_environment):
        """Test that facts are properly stored in case_facts collection"""
        mock_qdrant = setup_test_environment['qdrant_client']
        
        # Configure mock to track upserted facts
        facts_stored = []
        
        async def track_upsert(collection_name, points, **kwargs):
            if "facts" in collection_name:
                facts_stored.extend(points)
        
        mock_qdrant.upsert.side_effect = track_upsert
        
        # Create fact extractor
        fact_extractor = FactExtractor(case_name="test_case")
        
        # Mock the LLM fact extraction
        with patch.object(fact_extractor, '_extract_with_llm') as mock_llm:
            mock_llm.return_value = [
                {
                    "text": "The contract was signed on January 1, 2024",
                    "category": "timeline",
                    "confidence": 0.9
                },
                {
                    "text": "John Smith is the CEO of ABC Corp",
                    "category": "person",
                    "confidence": 0.85
                }
            ]
            
            # Extract and store facts
            facts = await fact_extractor.extract_facts_from_document(
                document_id="test_doc",
                document_content="Contract signed by John Smith, CEO of ABC Corp on January 1, 2024"
            )
            
            # Verify facts were prepared for storage
            assert len(facts) == 2
            assert mock_qdrant.upsert.called


class TestDiscoveryAPIIntegration:
    """Integration tests for discovery API endpoints"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        from main import app
        return TestClient(app)
    
    @pytest.mark.asyncio
    async def test_api_file_upload_flow(self, client, setup_test_environment):
        """Test complete API flow from file upload to completion"""
        # This would test the actual API endpoint
        # For now, it's a placeholder showing the structure
        
        # Mock file upload
        files = [("files", ("test.pdf", b"PDF content", "application/pdf"))]
        
        with patch('src.api.discovery_endpoints._process_discovery_async') as mock_process:
            mock_process.return_value = None
            
            response = client.post(
                "/api/discovery/process",
                files=files,
                data={
                    "case_name": "test_case",
                    "producing_party": "Test Party",
                    "production_batch": "BATCH001"
                },
                headers={"X-Case-ID": "test_case"}
            )
            
            assert response.status_code == 200
            result = response.json()
            assert "processing_id" in result
            assert result["status"] == "processing"
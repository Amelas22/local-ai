"""
Simple test for discovery processing to debug issues
"""
import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi.testclient import TestClient


class TestDiscoverySimple:
    """Simplified discovery processing test"""
    
    @pytest.mark.asyncio
    async def test_discovery_endpoint(self):
        """Test that discovery endpoint accepts requests and starts processing"""
        
        # Mock all external dependencies
        with patch("src.api.discovery_endpoints.FactExtractor") as mock_fact_ext, \
             patch("src.api.discovery_endpoints.sio") as mock_sio, \
             patch("src.document_processing.discovery_splitter.DiscoveryProductionProcessor") as mock_splitter, \
             patch("src.document_processing.unified_document_manager.UnifiedDocumentManager") as mock_doc_mgr, \
             patch("src.vector_storage.qdrant_store.QdrantVectorStore") as mock_qdrant:
            
            # Setup basic mocks
            mock_sio.emit = AsyncMock()
            
            # Mock discovery splitter to return simple results
            mock_processor = MagicMock()
            mock_processor.process_discovery_production = MagicMock(
                return_value={
                    "segments_found": [
                        {
                            "start_page": 0,
                            "end_page": 10,
                            "document_type": "other",
                            "title": "Test Document",
                            "confidence": 0.9
                        }
                    ],
                    "average_confidence": 0.9,
                    "processing_windows": 1
                }
            )
            mock_splitter.return_value = mock_processor
            
            # Mock document manager
            mock_doc_mgr_instance = MagicMock()
            mock_doc_mgr_instance.is_duplicate = AsyncMock(return_value=False)
            mock_doc_mgr_instance.process_and_chunk_document = AsyncMock(
                return_value={
                    "document": MagicMock(id="doc-123"),
                    "chunks": [MagicMock(id="chunk-1")],
                    "total_chunks": 1
                }
            )
            mock_doc_mgr.return_value = mock_doc_mgr_instance
            
            # Import app after mocks are set up
            from main import app
            
            # Create test client
            with TestClient(app) as client:
                # Make discovery request
                response = client.post(
                    "/api/discovery/process",
                    json={
                        "discovery_files": [{
                            "filename": "test.pdf",
                            "content": "UGxhY2Vob2xkZXI=",  # Base64 "Placeholder"
                            "content_type": "application/pdf"
                        }],
                        "case_id": "test-case",
                        "case_name": "test-case"
                    }
                )
                
                # Check response
                assert response.status_code == 200
                data = response.json()
                assert "processing_id" in data
                assert data["status"] == "started"
                
                # Give async processing a moment
                await asyncio.sleep(0.5)
                
                # Verify WebSocket event was emitted
                assert mock_sio.emit.called
                emitted_events = [call[0][0] for call in mock_sio.emit.call_args_list]
                assert "discovery:started" in emitted_events
                
                print(f"Test passed! Events emitted: {emitted_events}")
"""
Integration tests for discovery processing endpoint with JSON requests.
Tests the complete flow from API request to document splitting.
"""

import pytest
import json
import base64
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI

from src.api.discovery_endpoints import router, processing_status
from src.models.discovery_models import DiscoveryProcessingStatus


class TestDiscoveryIntegration:
    """Integration tests for discovery processing"""

    @pytest.fixture
    def app(self):
        """Create FastAPI app with discovery router"""
        app = FastAPI()
        app.include_router(router)
        return app

    @pytest.fixture
    def client(self, app):
        """Create test client"""
        return TestClient(app)

    @pytest.fixture
    def sample_pdf_base64(self):
        """Create a base64 encoded sample PDF"""
        # Minimal PDF structure
        pdf_content = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\nxref\n0 4\n0000000000 65535 f\n0000000009 00000 n\n0000000058 00000 n\n0000000115 00000 n\ntrailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n190\n%%EOF"
        return base64.b64encode(pdf_content).decode('utf-8')

    def test_process_discovery_json_request(self, client, sample_pdf_base64):
        """Test processing discovery with JSON request format"""
        # Mock dependencies
        with patch("src.api.discovery_endpoints.require_case_context") as mock_require_context, \
             patch("src.api.discovery_endpoints.BackgroundTasks") as mock_bg_tasks:
            
            # Setup mock case context
            mock_case_context = Mock(case_id="test-case-1", case_name="Test Case")
            mock_require_context.return_value = lambda: mock_case_context
            
            # Setup mock background tasks
            mock_bg_instance = Mock()
            mock_bg_tasks.return_value = mock_bg_instance
            
            # Prepare request data
            request_data = {
                "discovery_files": [
                    {
                        "filename": "test_discovery.pdf",
                        "content": sample_pdf_base64
                    }
                ],
                "production_batch": "TEST_BATCH_001",
                "producing_party": "Test Party",
                "enable_fact_extraction": True,
                "responsive_to_requests": ["RFP-1", "RFP-2"],
                "confidentiality_designation": "Confidential"
            }
            
            # Make request
            headers = {"X-Case-ID": "test-case-1"}
            response = client.post(
                "/api/discovery/process",
                json=request_data,
                headers=headers
            )
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert "processing_id" in data
            assert data["status"] == "started"
            assert data["message"] == "Discovery processing started"
            
            # Verify background task was scheduled
            mock_bg_instance.add_task.assert_called_once()
            
            # Verify processing status was created
            processing_id = data["processing_id"]
            assert processing_id in processing_status
            assert processing_status[processing_id].case_name == "Test Case"

    def test_process_discovery_empty_files(self, client):
        """Test processing with empty file list"""
        with patch("src.api.discovery_endpoints.require_case_context") as mock_require_context, \
             patch("src.api.discovery_endpoints.BackgroundTasks") as mock_bg_tasks:
            
            mock_case_context = Mock(case_id="test-case-1", case_name="Test Case")
            mock_require_context.return_value = lambda: mock_case_context
            mock_bg_instance = Mock()
            mock_bg_tasks.return_value = mock_bg_instance
            
            request_data = {
                "discovery_files": [],
                "production_batch": "EMPTY_BATCH",
                "producing_party": "Test Party"
            }
            
            headers = {"X-Case-ID": "test-case-1"}
            response = client.post(
                "/api/discovery/process",
                json=request_data,
                headers=headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "started"

    def test_process_discovery_with_box_folder(self, client):
        """Test processing with Box folder ID"""
        with patch("src.api.discovery_endpoints.require_case_context") as mock_require_context, \
             patch("src.api.discovery_endpoints.BackgroundTasks") as mock_bg_tasks:
            
            mock_case_context = Mock(case_id="test-case-1", case_name="Test Case")
            mock_require_context.return_value = lambda: mock_case_context
            mock_bg_instance = Mock()
            mock_bg_tasks.return_value = mock_bg_instance
            
            request_data = {
                "discovery_files": [],
                "box_folder_id": "123456789",
                "production_batch": "BOX_BATCH",
                "producing_party": "Test Party"
            }
            
            headers = {"X-Case-ID": "test-case-1"}
            response = client.post(
                "/api/discovery/process",
                json=request_data,
                headers=headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "started"

    def test_get_processing_status_integration(self, client):
        """Test getting processing status through the API"""
        # Create a processing status
        processing_id = "test-int-123"
        status = DiscoveryProcessingStatus(
            processing_id=processing_id,
            case_id="test-case-1",
            case_name="Test Case",
            total_documents=5,
            processed_documents=3,
            total_facts=10,
            status="processing"
        )
        processing_status[processing_id] = status
        
        with patch("src.api.discovery_endpoints.get_case_context") as mock_get_context:
            mock_get_context.return_value = Mock(case_id="test-case-1", case_name="Test Case")
            
            headers = {"X-Case-ID": "test-case-1"}
            response = client.get(
                f"/api/discovery/status/{processing_id}",
                headers=headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["processing_id"] == processing_id
            assert data["total_documents"] == 5
            assert data["processed_documents"] == 3
            assert data["total_facts"] == 10
            assert data["status"] == "processing"
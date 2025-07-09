import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from src.api.case_endpoints import router

class TestCaseEndpoints:
    """Test case creation with Qdrant collection creation"""
    
    @pytest.mark.asyncio
    @patch('src.api.case_endpoints.CaseService.create_case')
    @patch('src.api.case_endpoints.QdrantVectorStore')
    @patch('src.api.case_endpoints.create_case_collections_with_events')
    async def test_create_case_with_collections_success(
        self,
        mock_create_collections,
        mock_vector_store_class,
        mock_create_case
    ):
        """Test successful case creation with Qdrant collections"""
        # Setup
        mock_case = Mock(
            id="case-123",
            name="Test Case",
            collection_name="test_case_12345678",
            case_metadata=None
        )
        mock_create_case.return_value = mock_case
        mock_create_collections.return_value = True
        
        # Execute (would need proper FastAPI test client setup)
        # This is a simplified example
        
        # Verify
        mock_create_collections.assert_called_once()
        mock_vector_store_class.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('src.api.case_endpoints.CaseService.create_case')
    @patch('src.api.case_endpoints.QdrantVectorStore')
    @patch('src.api.case_endpoints.create_case_collections_with_events')
    async def test_create_case_collections_failure_non_blocking(
        self,
        mock_create_collections,
        mock_vector_store_class,
        mock_create_case
    ):
        """Test that Qdrant failure doesn't block case creation"""
        # Setup
        mock_case = Mock(
            id="case-456",
            name="Test Case 2",
            collection_name="test_case_2_12345678"
        )
        mock_create_case.return_value = mock_case
        mock_create_collections.side_effect = Exception("Qdrant unavailable")
        
        # Execute - should not raise exception
        # Case should still be created successfully
        
        # Verify case was created despite Qdrant error
        mock_create_case.assert_called_once()
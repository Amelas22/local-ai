import pytest
from unittest.mock import Mock, AsyncMock, patch
from src.vector_storage.qdrant_store import QdrantVectorStore
from src.config.settings import settings

class TestQdrantVectorStore:
    """Test QdrantVectorStore collection creation functionality"""
    
    @pytest.fixture
    def mock_qdrant_async_client(self):
        """Mock async Qdrant client"""
        client = AsyncMock()
        client.collection_exists = AsyncMock()
        client.create_collection = AsyncMock()
        client.create_payload_index = AsyncMock()
        return client
    
    @pytest.fixture
    def vector_store(self, mock_qdrant_async_client):
        """Create QdrantVectorStore with mocked client"""
        store = QdrantVectorStore()
        store.async_client = mock_qdrant_async_client
        return store
    
    @pytest.mark.asyncio
    async def test_create_case_collections_success(self, vector_store):
        """Test successful creation of all case collections"""
        # Setup
        collection_name = "test_case_12345678"
        vector_store.async_client.collection_exists.return_value = False
        
        # Execute
        results = await vector_store.create_case_collections(collection_name)
        
        # Verify
        assert len(results) == 4
        assert all(results.values())
        assert collection_name in results
        assert f"{collection_name}_facts" in results
        assert f"{collection_name}_timeline" in results
        assert f"{collection_name}_depositions" in results
        
        # Verify create_collection was called 4 times
        assert vector_store.async_client.create_collection.call_count == 4
    
    @pytest.mark.asyncio
    async def test_create_case_collections_already_exist(self, vector_store):
        """Test when collections already exist"""
        # Setup
        collection_name = "existing_case_12345678"
        vector_store.async_client.collection_exists.return_value = True
        
        # Execute
        results = await vector_store.create_case_collections(collection_name)
        
        # Verify
        assert all(results.values())
        # Should not create collections that already exist
        vector_store.async_client.create_collection.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_create_case_collections_partial_failure(self, vector_store):
        """Test partial failure during collection creation"""
        # Setup
        collection_name = "partial_fail_12345678"
        vector_store.async_client.collection_exists.return_value = False
        
        # Make third collection creation fail
        vector_store.async_client.create_collection.side_effect = [
            None,  # Success
            None,  # Success
            Exception("Qdrant error"),  # Failure
            None   # Success
        ]
        
        # Execute
        results = await vector_store.create_case_collections(collection_name)
        
        # Verify
        assert results[collection_name] == True
        assert results[f"{collection_name}_facts"] == True
        assert results[f"{collection_name}_timeline"] == False
        assert results[f"{collection_name}_depositions"] == True
    
    @pytest.mark.asyncio
    async def test_create_case_collections_long_name(self, vector_store):
        """Test collection name truncation for long names"""
        # Setup - name that would exceed 63 chars with suffixes
        collection_name = "very_long_case_name_that_exceeds_limit_when_suffixes_added_12345678"
        vector_store.async_client.collection_exists.return_value = False
        
        # Execute
        results = await vector_store.create_case_collections(collection_name)
        
        # Verify all collection names are within limit
        for coll_name in results.keys():
            assert len(coll_name) <= 63
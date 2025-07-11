import pytest
from unittest.mock import patch, AsyncMock


@pytest.mark.integration
class TestCaseCreationIntegration:
    """Integration tests for case creation with Qdrant"""

    @pytest.mark.asyncio
    async def test_full_case_creation_flow(self, test_client, test_db):
        """Test complete case creation flow including Qdrant collections"""
        # This would require a test Qdrant instance or extensive mocking
        # Example structure:

        with patch("src.vector_storage.qdrant_store.QdrantVectorStore") as mock_store:
            mock_store.return_value.create_case_collections = AsyncMock(
                return_value={
                    "test_case_123": True,
                    "test_case_123_facts": True,
                    "test_case_123_timeline": True,
                    "test_case_123_depositions": True,
                }
            )

            response = test_client.post(
                "/api/cases", json={"name": "Test Case", "metadata": {}}
            )

            assert response.status_code == 200
            assert mock_store.return_value.create_case_collections.called

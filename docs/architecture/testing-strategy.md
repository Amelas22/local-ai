# Testing Strategy

## Integration with Existing Tests
- **Existing Test Framework:** pytest with asyncio support
- **Test Organization:** Co-located tests in tests/ subdirectories
- **Coverage Requirements:** Maintain >80% coverage for new code

## New Testing Requirements

**Unit Tests for New Components:**
- **Framework:** pytest
- **Location:** src/*/tests/ following vertical slice pattern
- **Coverage Target:** 85% for critical paths
- **Integration with Existing:** Use existing fixtures and mocks

**Integration Tests:**
- **Scope:** End-to-end deficiency analysis workflow
- **Existing System Verification:** Ensure discovery pipeline unaffected
- **New Feature Testing:** Complete deficiency analysis with mock data

**Regression Testing:**
- **Existing Feature Verification:** Run full discovery test suite
- **Automated Regression Suite:** Add deficiency tests to CI/CD
- **Manual Testing Requirements:** Legal team UAT for report accuracy

## Test Implementation Examples

**Integration Test Pattern:**
```python
import pytest
from httpx import AsyncClient
from src.main import app

class TestDeficiencyIntegration:
    """Integration tests for deficiency analysis workflow."""
    
    @pytest.mark.asyncio
    async def test_complete_deficiency_workflow(self, async_client: AsyncClient):
        """Test full workflow from discovery to letter generation."""
        # Step 1: Process discovery with deficiency analysis
        response = await async_client.post(
            "/api/discovery/process-with-deficiency",
            json={
                "folder_id": "test_folder",
                "case_name": "test_case",
                "rtp_file": "base64_test_rtp",
                "oc_response_file": "base64_test_response",
                "enable_deficiency_analysis": True
            }
        )
        assert response.status_code == 200
        production_id = response.json()["production_id"]
        
        # Step 2: Wait for analysis completion (mocked)
        # Step 3: Retrieve deficiency report
        # Step 4: Generate Good Faith letter
        # Assert all steps succeed
```

**Mock Strategy:**
```python
@pytest.fixture
def mock_vector_store():
    """Mock Qdrant vector store for testing."""
    with patch("src.vector_storage.qdrant_store.QdrantVectorStore") as mock:
        mock.hybrid_search.return_value = [
            # Mock search results
        ]
        yield mock
```

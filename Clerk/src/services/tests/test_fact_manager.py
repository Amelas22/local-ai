"""
Tests for Fact Manager Service
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
import uuid
import numpy as np

from src.services.fact_manager import FactManager
from src.models.discovery_models import (
    ExtractedFactWithSource,
    FactSource,
    FactUpdateRequest,
    FactDeleteRequest,
    FactSearchFilter,
    FactBulkUpdateRequest,
)
from src.models.fact_models import FactCategory, EntityType
from src.models.case_models import CaseContext


@pytest.fixture
def mock_dependencies():
    """Mock external dependencies"""
    with (
        patch("src.services.fact_manager.QdrantVectorStore") as mock_qdrant,
        patch("src.services.fact_manager.EmbeddingGenerator") as mock_embedding,
        patch("src.services.fact_manager.CaseManager") as mock_case_manager,
    ):
        # Configure mocks
        mock_qdrant_instance = Mock()
        mock_qdrant_instance.client = AsyncMock()
        mock_qdrant.return_value = mock_qdrant_instance

        mock_embedding_instance = Mock()
        mock_embedding_instance.generate_embedding = AsyncMock(
            return_value=np.array([0.1] * 1536)
        )
        mock_embedding.return_value = mock_embedding_instance

        mock_case_manager_instance = Mock()
        mock_case_manager.return_value = mock_case_manager_instance

        yield {
            "qdrant": mock_qdrant_instance,
            "embedding": mock_embedding_instance,
            "case_manager": mock_case_manager_instance,
        }


@pytest.fixture
def sample_fact():
    """Create a sample fact for testing"""
    source = FactSource(
        doc_id="doc-123",
        doc_title="Medical Records",
        page=42,
        bbox=[100.0, 200.0, 400.0, 250.0],
        text_snippet="patient was treated for back pain",
        bates_number="DEF00042",
    )

    return ExtractedFactWithSource(
        id="fact-" + str(uuid.uuid4()),
        case_name="Smith_v_Jones_2024",
        content="Patient was treated for severe back pain on January 15, 2024",
        category=FactCategory.MEDICAL,
        source_document="doc-123",
        page_references=[42],
        extraction_timestamp=datetime.utcnow(),
        confidence_score=0.95,
        source=source,
        entities={EntityType.DATE: ["January 15, 2024"]},
    )


@pytest.fixture
def case_context():
    """Create a sample case context"""
    return CaseContext(
        case_id="case-123",
        case_name="Smith_v_Jones_2024",
        user_id="user-456",
        permissions=["read", "write"],
    )


class TestFactManager:
    """Test FactManager class"""

    @pytest.mark.asyncio
    async def test_create_fact_success(
        self, mock_dependencies, sample_fact, case_context
    ):
        """Test successful fact creation"""
        fact_manager = FactManager()

        # Configure mocks
        mock_dependencies["qdrant"].client.search.return_value = []  # No duplicates
        mock_dependencies["qdrant"].client.upsert.return_value = None

        # Create fact
        result = await fact_manager.create_fact(sample_fact, case_context)

        # Verify
        assert result == sample_fact
        mock_dependencies["embedding"].generate_embedding.assert_called_once_with(
            sample_fact.content
        )
        mock_dependencies["qdrant"].client.upsert.assert_called_once()

        # Check collection name
        call_args = mock_dependencies["qdrant"].client.upsert.call_args
        assert call_args[1]["collection_name"] == "Smith_v_Jones_2024_facts"

    @pytest.mark.asyncio
    async def test_create_fact_duplicate_detection(
        self, mock_dependencies, sample_fact, case_context
    ):
        """Test duplicate fact detection"""
        fact_manager = FactManager()

        # Configure mock to return similar fact
        similar_result = Mock()
        similar_result.score = 0.95
        similar_result.payload = {"content": sample_fact.content}
        mock_dependencies["qdrant"].client.search.return_value = [similar_result]

        # Create fact
        result = await fact_manager.create_fact(sample_fact, case_context)

        # Should return None for duplicate
        assert result is None
        mock_dependencies["qdrant"].client.upsert.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_fact_case_mismatch(
        self, mock_dependencies, sample_fact, case_context
    ):
        """Test fact creation with case name mismatch"""
        fact_manager = FactManager()

        # Change fact case name
        sample_fact.case_name = "Different_Case"

        # Should raise ValueError
        with pytest.raises(ValueError, match="Case name mismatch"):
            await fact_manager.create_fact(sample_fact, case_context)

    @pytest.mark.asyncio
    async def test_update_fact_success(self, mock_dependencies, case_context):
        """Test successful fact update"""
        fact_manager = FactManager()
        fact_id = "fact-123"

        # Configure mock to return existing fact
        existing_point = Mock()
        existing_point.payload = {
            "id": fact_id,
            "content": "Original content",
            "edit_history": [],
        }
        mock_dependencies["qdrant"].client.retrieve.return_value = [existing_point]
        mock_dependencies["qdrant"].client.upsert.return_value = None

        # Update request
        update_request = FactUpdateRequest(
            fact_id=fact_id, new_content="Updated content", edit_reason="Corrected date"
        )

        # Update fact
        result = await fact_manager.update_fact(fact_id, update_request, case_context)

        # Verify
        assert result is not None
        mock_dependencies["embedding"].generate_embedding.assert_called_with(
            "Updated content"
        )
        mock_dependencies["qdrant"].client.upsert.assert_called_once()

        # Check updated payload
        call_args = mock_dependencies["qdrant"].client.upsert.call_args
        points = call_args[1]["points"]
        assert points[0].payload["content"] == "Updated content"
        assert points[0].payload["is_edited"] is True
        assert len(points[0].payload["edit_history"]) == 1

    @pytest.mark.asyncio
    async def test_update_fact_not_found(self, mock_dependencies, case_context):
        """Test updating non-existent fact"""
        fact_manager = FactManager()

        # Configure mock to return no facts
        mock_dependencies["qdrant"].client.retrieve.return_value = []

        update_request = FactUpdateRequest(
            fact_id="non-existent", new_content="Updated content"
        )

        # Should raise ValueError
        with pytest.raises(ValueError, match="not found"):
            await fact_manager.update_fact("non-existent", update_request, case_context)

    @pytest.mark.asyncio
    async def test_delete_fact_success(self, mock_dependencies, case_context):
        """Test successful fact deletion (soft delete)"""
        fact_manager = FactManager()
        fact_id = "fact-123"

        # Configure mock
        existing_point = Mock()
        existing_point.payload = {"id": fact_id, "content": "Fact content"}
        mock_dependencies["qdrant"].client.retrieve.return_value = [existing_point]
        mock_dependencies["qdrant"].client.set_payload.return_value = None

        # Delete request
        delete_request = FactDeleteRequest(
            fact_id=fact_id, delete_reason="Incorrect information"
        )

        # Delete fact
        result = await fact_manager.delete_fact(fact_id, delete_request, case_context)

        # Verify
        assert result is True
        mock_dependencies["qdrant"].client.set_payload.assert_called_once()

        # Check payload update
        call_args = mock_dependencies["qdrant"].client.set_payload.call_args
        payload = call_args[1]["payload"]
        assert payload["is_deleted"] is True
        assert payload["deleted_by"] == case_context.user_id
        assert payload["delete_reason"] == "Incorrect information"

    @pytest.mark.asyncio
    async def test_get_fact_success(self, mock_dependencies, case_context):
        """Test getting a fact by ID"""
        fact_manager = FactManager()
        fact_id = "fact-123"

        # Configure mock
        point = Mock()
        point.payload = {
            "id": fact_id,
            "case_name": case_context.case_name,
            "content": "Fact content",
            "category": "medical",
            "source_document": "doc-123",
            "page_references": [42],
            "extraction_timestamp": datetime.utcnow().isoformat(),
            "confidence_score": 0.95,
            "entities": {},
            "source": {
                "doc_id": "doc-123",
                "doc_title": "Medical Records",
                "page": 42,
                "bbox": [100, 200, 400, 250],
                "text_snippet": "context",
            },
            "is_deleted": False,
        }
        mock_dependencies["qdrant"].client.retrieve.return_value = [point]

        # Get fact
        result = await fact_manager.get_fact(fact_id, case_context)

        # Verify
        assert result is not None
        assert result.id == fact_id
        assert result.content == "Fact content"

    @pytest.mark.asyncio
    async def test_get_fact_deleted(self, mock_dependencies, case_context):
        """Test getting a deleted fact returns None"""
        fact_manager = FactManager()

        # Configure mock with deleted fact
        point = Mock()
        point.payload = {"id": "fact-123", "is_deleted": True}
        mock_dependencies["qdrant"].client.retrieve.return_value = [point]

        # Get fact
        result = await fact_manager.get_fact("fact-123", case_context)

        # Should return None for deleted facts
        assert result is None

    @pytest.mark.asyncio
    async def test_search_facts_with_query(self, mock_dependencies, case_context):
        """Test searching facts with query"""
        fact_manager = FactManager()

        # Configure mock search results
        result_point = Mock()
        result_point.payload = {
            "id": "fact-123",
            "case_name": case_context.case_name,
            "content": "Matching fact",
            "category": "medical",
            "source_document": "doc-123",
            "page_references": [1],
            "extraction_timestamp": datetime.utcnow().isoformat(),
            "confidence_score": 0.9,
            "entities": {},
            "source": {
                "doc_id": "doc-123",
                "doc_title": "Document",
                "page": 1,
                "bbox": [0, 0, 100, 100],
                "text_snippet": "text",
            },
        }
        mock_dependencies["qdrant"].client.search.return_value = [result_point]

        # Search filter
        search_filter = FactSearchFilter(
            case_id=case_context.case_id,
            query="back pain",
            categories=[FactCategory.MEDICAL],
            limit=10,
        )

        # Search
        results = await fact_manager.search_facts(search_filter, case_context)

        # Verify
        assert len(results) == 1
        assert results[0].content == "Matching fact"
        mock_dependencies["embedding"].generate_embedding.assert_called_with(
            "back pain"
        )

    @pytest.mark.asyncio
    async def test_bulk_update_mark_reviewed(self, mock_dependencies, case_context):
        """Test bulk marking facts as reviewed"""
        fact_manager = FactManager()

        # Configure mock
        mock_dependencies["qdrant"].client.set_payload.return_value = None

        # Bulk request
        bulk_request = FactBulkUpdateRequest(
            fact_ids=["fact-1", "fact-2", "fact-3"], action="mark_reviewed"
        )

        # Execute bulk update
        results = await fact_manager.bulk_update_facts(bulk_request, case_context)

        # Verify
        assert all(results.values())  # All should succeed
        assert mock_dependencies["qdrant"].client.set_payload.call_count == 3

    @pytest.mark.asyncio
    async def test_text_similarity_calculation(self, mock_dependencies):
        """Test text similarity calculation"""
        fact_manager = FactManager()

        # Test exact match
        assert fact_manager._calculate_text_similarity("Hello", "Hello") == 1.0

        # Test case insensitive
        assert fact_manager._calculate_text_similarity("Hello", "hello") == 1.0

        # Test substring
        similarity = fact_manager._calculate_text_similarity(
            "The patient has back pain", "back pain"
        )
        assert 0 < similarity < 1.0

        # Test completely different
        similarity = fact_manager._calculate_text_similarity("Apple", "Orange")
        assert similarity < 0.5

"""
Test async/await functionality in enhanced chunker
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from typing import List

from ..enhanced_chunker import EnhancedChunker
from ...models.normalized_document_models import DocumentCore, ChunkMetadata
from ...vector_storage.embeddings import EmbeddingGenerator


@pytest.fixture
def mock_embedding_generator():
    """Create a mock embedding generator with async methods"""
    generator = Mock(spec=EmbeddingGenerator)
    generator.model = "text-embedding-3-small"
    
    # Mock async methods
    generator.generate_embeddings_batch_async = AsyncMock(
        return_value=([[0.1, 0.2, 0.3] * 512, [0.4, 0.5, 0.6] * 512], 100)
    )
    generator.generate_embedding_async = AsyncMock(
        return_value=([0.1, 0.2, 0.3] * 512, 50)
    )
    
    return generator


@pytest.fixture
def document_core():
    """Create a sample document core"""
    return DocumentCore(
        id="test-doc-123",
        case_id="case-123",
        case_name="Test_Case_2024",
        filename="test_document.pdf",
        file_type="pdf",
        page_count=10,
        file_size=1024000
    )


@pytest.mark.asyncio
async def test_generate_embeddings_batch_async(mock_embedding_generator, document_core):
    """Test that the enhanced chunker correctly calls async embedding methods"""
    
    # Create chunker with mock generator
    chunker = EnhancedChunker(
        embedding_generator=mock_embedding_generator,
        chunk_size=1200,
        chunk_overlap=200
    )
    
    # Create sample text
    sample_text = """
    This is a test document with multiple paragraphs.
    
    Each paragraph contains some text that will be chunked appropriately.
    The chunking process should create semantic chunks with embeddings.
    
    This is the third paragraph with more content to ensure we have enough text
    for proper chunking and testing of the async embedding generation.
    """
    
    # Create chunks
    chunks = await chunker.create_chunks(
        document_core=document_core,
        document_text=sample_text
    )
    
    # Verify async methods were called
    assert mock_embedding_generator.generate_embeddings_batch_async.called
    assert len(chunks) > 0
    
    # Verify each chunk has embeddings
    for chunk in chunks:
        assert chunk.dense_vector is not None
        assert chunk.embedding_model == "text-embedding-3-small"
        assert isinstance(chunk.dense_vector, list)


@pytest.mark.asyncio
async def test_embedding_fallback_to_individual_async(mock_embedding_generator, document_core):
    """Test fallback to individual async embedding generation when batch fails"""
    
    # Make batch method fail
    mock_embedding_generator.generate_embeddings_batch_async = AsyncMock(
        side_effect=Exception("Batch processing failed")
    )
    
    # Create chunker
    chunker = EnhancedChunker(
        embedding_generator=mock_embedding_generator,
        chunk_size=1200,
        chunk_overlap=200
    )
    
    # Create sample text
    sample_text = "This is a short test document."
    
    # Create chunks - should fall back to individual generation
    chunks = await chunker.create_chunks(
        document_core=document_core,
        document_text=sample_text
    )
    
    # Verify individual async method was called
    assert mock_embedding_generator.generate_embedding_async.called
    assert len(chunks) > 0
    
    # Verify chunks still have embeddings despite batch failure
    for chunk in chunks:
        assert chunk.dense_vector is not None
        assert chunk.embedding_model == "text-embedding-3-small"


@pytest.mark.asyncio
async def test_no_await_on_sync_methods():
    """Test that we're not trying to await synchronous methods"""
    
    # This test verifies our fix by ensuring the code doesn't try to await
    # non-async methods like generate_embeddings_batch or generate_embedding
    
    with patch('src.document_processing.enhanced_chunker.EmbeddingGenerator') as MockGen:
        # Create mock with only sync methods (no async versions)
        sync_generator = Mock()
        sync_generator.model = "test-model"
        sync_generator.generate_embeddings_batch = Mock(
            return_value=([[0.1] * 1536], 100)  # Returns tuple, not awaitable
        )
        sync_generator.generate_embedding = Mock(
            return_value=([0.1] * 1536, 50)  # Returns tuple, not awaitable
        )
        
        # Ensure async methods exist (our fix)
        sync_generator.generate_embeddings_batch_async = AsyncMock(
            return_value=([[0.1] * 1536], 100)
        )
        sync_generator.generate_embedding_async = AsyncMock(
            return_value=([0.1] * 1536, 50)
        )
        
        chunker = EnhancedChunker(
            embedding_generator=sync_generator,
            chunk_size=1200
        )
        
        doc_core = DocumentCore(
            id="test-123",
            case_id="case-123", 
            case_name="Test_Case",
            filename="test.pdf",
            file_type="pdf",
            page_count=1,
            file_size=1000
        )
        
        # This should not raise "object tuple can't be used in 'await' expression"
        chunks = await chunker.create_chunks(
            document_core=doc_core,
            document_text="Test text"
        )
        
        # Verify async methods were called, not sync ones
        assert sync_generator.generate_embeddings_batch_async.called
        assert not sync_generator.generate_embeddings_batch.called
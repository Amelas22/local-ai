"""Test to verify chunk sizes are correct for embedding generation"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from src.models.normalized_document_models import ChunkMetadata, DocumentCore
from src.document_processing.enhanced_chunker import EnhancedChunker
from src.vector_storage.embeddings import EmbeddingGenerator
import tiktoken


@pytest.mark.asyncio
async def test_chunk_size_within_token_limit():
    """Test that chunks created by EnhancedChunker are within the token limit"""
    
    # Create mock embedding generator
    embedding_generator = MagicMock()
    embedding_generator.model = "text-embedding-ada-002"
    
    # Create chunker with standard chunk size
    chunker = EnhancedChunker(
        embedding_generator=embedding_generator,
        chunk_size=1400,  # Characters, not tokens
        chunk_overlap=200
    )
    
    # Create a test document with enough text
    test_text = "This is a test document. " * 500  # ~12,500 characters
    
    # Create document core
    doc_core = DocumentCore(
        id="test-doc-1",
        document_hash="test-hash",
        metadata_hash="test-meta-hash",
        file_name="test.pdf",
        original_file_path="/test/path/test.pdf",
        file_size=len(test_text),
        mime_type="application/pdf",
        total_pages=10
    )
    
    # Create chunks
    chunks = await chunker.create_chunks(
        document_core=doc_core,
        document_text=test_text
    )
    
    # Verify chunks were created
    assert len(chunks) > 0, "No chunks were created"
    
    # Get the tokenizer for the embedding model
    encoding = tiktoken.encoding_for_model("text-embedding-ada-002")
    
    # Check each chunk's token count
    max_tokens_allowed = 8192
    for idx, chunk in enumerate(chunks):
        # Get the chunk text
        chunk_text = chunk.chunk_text
        
        # Count tokens
        tokens = encoding.encode(chunk_text)
        token_count = len(tokens)
        
        print(f"Chunk {idx}: {len(chunk_text)} chars, {token_count} tokens")
        
        # Verify token count is within limit
        assert token_count < max_tokens_allowed, \
            f"Chunk {idx} has {token_count} tokens, exceeding limit of {max_tokens_allowed}"
        
        # Verify chunk text is approximately the expected size
        assert len(chunk_text) <= 1600, \
            f"Chunk {idx} text is {len(chunk_text)} chars, expected ~1400"


@pytest.mark.asyncio
async def test_chunk_metadata_attributes():
    """Test that ChunkMetadata has the correct attributes"""
    
    chunk = ChunkMetadata(
        document_id="test-doc-1",
        chunk_text="This is the chunk text content",
        chunk_index=0,
        chunk_hash="test-hash",
        start_page=1,
        end_page=1,
        section_title="Test Section",
        semantic_type="paragraph"
    )
    
    # Verify all required attributes exist
    assert hasattr(chunk, 'chunk_text')
    assert hasattr(chunk, 'section_title')
    assert hasattr(chunk, 'semantic_type')
    assert hasattr(chunk, 'start_page')
    assert hasattr(chunk, 'end_page')
    
    # Verify correct values
    assert chunk.chunk_text == "This is the chunk text content"
    assert chunk.section_title == "Test Section"
    assert chunk.semantic_type == "paragraph"
    assert chunk.start_page == 1
    assert chunk.end_page == 1
    
    # Verify str(chunk) doesn't include the entire content
    chunk_str = str(chunk)
    # The string representation should be reasonable size
    assert len(chunk_str) < 10000, f"String representation too large: {len(chunk_str)} chars"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
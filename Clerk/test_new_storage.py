#!/usr/bin/env python3
"""
Test storing new documents with the fix.
"""
import asyncio
from src.vector_storage.qdrant_store import QdrantVectorStore
from src.vector_storage.embeddings import EmbeddingGenerator
from datetime import datetime

async def test_new_storage():
    """Test storing new documents with top-level production fields."""
    vector_store = QdrantVectorStore()
    embedding_generator = EmbeddingGenerator()
    
    # Use the existing case
    case_name = "debug5_071725_7be167d5"
    
    print(f"\n=== Testing New Storage Format ===")
    print(f"Case: {case_name}")
    
    # Generate test embedding
    test_content = "NEW DOCUMENT: Test document stored with fixed field names"
    embedding, _ = embedding_generator.generate_embedding(test_content)
    
    # Create a test chunk with metadata
    chunk = {
        "content": test_content,
        "embedding": embedding,
        "metadata": {
            "production_batch": "FixedBatch001",
            "producing_party": "Fixed Test Party",
            "production_date": datetime.utcnow().isoformat(),
            "document_type": "Test Document",
            "document_name": "Fixed Field Test"
        }
    }
    
    # Store the document
    print("\n1. Storing new document with fixed fields...")
    try:
        doc_id = f"fixed_test_{datetime.utcnow().timestamp()}"
        chunk_ids = vector_store.store_document_chunks(
            case_name=case_name,
            document_id=doc_id,
            chunks=[chunk]
        )
        print(f"✓ Stored document with ID: {doc_id}")
        print(f"  Chunk IDs: {chunk_ids}")
    except Exception as e:
        print(f"✗ Error storing document: {e}")
        return
    
    # Wait for indexing
    await asyncio.sleep(2)
    
    # Test searching for the new document
    print("\n2. Testing search with production_batch filter...")
    
    # Search with the new field name (no dots)
    results = vector_store.search_documents(
        collection_name=case_name,
        query_embedding=embedding,
        limit=5,
        threshold=0.0,
        filters={"production_batch": "FixedBatch001"}
    )
    
    print(f"\n   Filter: production_batch='FixedBatch001'")
    print(f"   Results: {len(results)} documents")
    
    if len(results) > 0:
        print("   ✓ SUCCESS: New documents can be filtered!")
        for i, result in enumerate(results):
            print(f"\n   Result {i+1}:")
            print(f"     Content: {result.content[:50]}...")
            print(f"     Score: {result.score}")
            
            # Check metadata structure
            prod_fields = {k: v for k, v in result.metadata.items() if 'production' in k}
            print(f"     Production fields: {prod_fields}")
    else:
        print("   ✗ FAILED: Cannot find new document with filter")
        
        # Debug: search without filter
        print("\n   Searching without filter...")
        unfiltered = vector_store.search_documents(
            collection_name=case_name,
            query_embedding=embedding,
            limit=5,
            threshold=0.0,
            filters=None
        )
        
        print(f"   Found {len(unfiltered)} documents without filter")
        if unfiltered:
            print("\n   First result metadata:")
            for key, value in sorted(unfiltered[0].metadata.items()):
                if 'production' in key.lower() or 'fixed' in str(value).lower():
                    print(f"     {key}: {value}")
    
    # Also test the old documents with the old field names
    print("\n3. Testing if old documents still work...")
    old_filter_results = vector_store.search_documents(
        collection_name=case_name,
        query_embedding=embedding,
        limit=5,
        threshold=0.0,
        filters={"metadata.production_batch": "Batch001"}
    )
    print(f"   Old format filter results: {len(old_filter_results)} documents")

if __name__ == "__main__":
    asyncio.run(test_new_storage())
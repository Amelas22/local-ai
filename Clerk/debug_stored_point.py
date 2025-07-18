#!/usr/bin/env python3
"""
Debug what's actually being stored.
"""
import asyncio
from datetime import datetime
from src.vector_storage.qdrant_store import QdrantVectorStore
from src.vector_storage.embeddings import EmbeddingGenerator

async def debug_stored_point():
    """Debug the stored point structure."""
    vector_store = QdrantVectorStore()
    embedding_generator = EmbeddingGenerator()
    
    # Create a simple test
    test_case = f"debug_{datetime.utcnow().strftime('%H%M%S')}"
    print(f"\nCreating test case: {test_case}")
    
    # Create collection
    vector_store.create_collection(test_case)
    
    # Create one chunk
    emb, _ = embedding_generator.generate_embedding("Test content")
    chunk = {
        "content": "Test content",
        "embedding": emb,
        "metadata": {
            "production_batch": "TestBatch",
            "producing_party": "TestParty",
            "other_field": "OtherValue"
        }
    }
    
    # Store it
    print("\nStoring chunk...")
    chunk_ids = vector_store.store_document_chunks(
        case_name=test_case,
        document_id="test_doc",
        chunks=[chunk]
    )
    print(f"Stored with ID: {chunk_ids[0]}")
    
    # Wait a moment
    await asyncio.sleep(1)
    
    # Retrieve the point directly
    print("\nRetrieving stored point...")
    point = vector_store.client.retrieve(
        collection_name=test_case,
        ids=[int(chunk_ids[0])],
        with_payload=True,
        with_vectors=False
    )[0]
    
    print("\nStored payload fields:")
    print("-" * 50)
    
    # Group fields
    prod_fields = []
    meta_fields = []
    other_fields = []
    
    for key, value in sorted(point.payload.items()):
        if key in ["production_batch", "producing_party", "production_date"]:
            prod_fields.append((key, value))
        elif key.startswith("metadata."):
            meta_fields.append((key, value))
        else:
            other_fields.append((key, value))
    
    if prod_fields:
        print("\nPRODUCTION FIELDS (TOP LEVEL):")
        for k, v in prod_fields:
            print(f"  {k}: {v}")
    
    if meta_fields:
        print("\nMETADATA FIELDS (WITH PREFIX):")
        for k, v in meta_fields:
            print(f"  {k}: {v}")
            
    # Clean up
    vector_store.client.delete_collection(test_case)
    
    # Result
    print("\n" + "="*50)
    if prod_fields:
        print("✅ SUCCESS: Production fields are stored at top level!")
        print("The fix is working in the code.")
    else:
        print("❌ FAILED: Production fields not found at top level")
        print("The fix is not being applied correctly.")

if __name__ == "__main__":
    asyncio.run(debug_stored_point())
#!/usr/bin/env python3
"""
Simple test to verify production batch filtering fix.
"""
import asyncio
import uuid
from src.vector_storage.qdrant_store import QdrantVectorStore
from src.vector_storage.embeddings import EmbeddingGenerator

async def test_simple_fix():
    """Test production batch filtering with direct API calls."""
    vector_store = QdrantVectorStore()
    embedding_generator = EmbeddingGenerator()
    
    # Create a test case
    test_case_name = f"test_fix_{uuid.uuid4().hex[:8]}"
    
    print(f"\n=== Testing Production Batch Fix ===")
    print(f"Test case: {test_case_name}")
    
    try:
        # Create collection
        print("\n1. Creating test collection...")
        vector_store.create_collection(test_case_name)
        
        # Generate test embedding
        test_content = "This is a test document for production batch filtering"
        embedding, _ = embedding_generator.generate_embedding(test_content)
        
        # Create test chunks manually
        chunks_data = [
            {
                "content": f"{test_content} - Document 1",
                "embedding": embedding
            },
            {
                "content": f"{test_content} - Document 2", 
                "embedding": embedding
            },
            {
                "content": f"{test_content} - Document 3",
                "embedding": embedding
            }
        ]
        
        # Metadata for each document
        metadata_list = [
            {
                "production_batch": "TestBatch001",
                "producing_party": "Test Party"
            },
            {
                "production_batch": "TestBatch001",
                "producing_party": "Test Party"
            },
            {
                "production_batch": "TestBatch002",
                "producing_party": "Other Party"
            }
        ]
        
        # Store chunks using the method that applies our fix
        print("\n2. Storing test documents...")
        for i, (chunk_data, metadata) in enumerate(zip(chunks_data, metadata_list)):
            doc_id = f"test_doc_{i+1}"
            await vector_store.store_document_chunks(
                case_name=test_case_name,
                chunks=[chunk_data],
                document_id=doc_id,
                chunk_metadata=metadata
            )
        
        # Wait for indexing
        await asyncio.sleep(2)
        
        # Test filtering
        print("\n3. Testing production batch filtering...")
        
        # Test with the new field name (no dots)
        results = vector_store.search_documents(
            collection_name=test_case_name,
            query_embedding=embedding,
            limit=10,
            threshold=0.0,
            filters={"production_batch": "TestBatch001"}
        )
        
        print(f"\n   Filter: production_batch='TestBatch001'")
        print(f"   Expected: 2 documents")
        print(f"   Actual: {len(results)} documents")
        
        if len(results) == 2:
            print("   ✓ SUCCESS: Filtering works with the fix!")
        else:
            print("   ✗ FAILED: Fix didn't work")
            
            # Debug: check metadata structure
            if results:
                print("\n   Sample result metadata:")
                for key, value in results[0].metadata.items():
                    if 'production' in key:
                        print(f"     {key}: {value}")
        
        # Clean up
        print("\n4. Cleaning up...")
        vector_store.client.delete_collection(test_case_name)
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        
        # Try to clean up
        try:
            vector_store.client.delete_collection(test_case_name)
        except:
            pass

if __name__ == "__main__":
    asyncio.run(test_simple_fix())
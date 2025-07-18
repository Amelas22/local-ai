#!/usr/bin/env python3
"""
Verify the production batch filtering fix works.
"""
import asyncio
import uuid
from src.vector_storage.qdrant_store import QdrantVectorStore
from src.vector_storage.embeddings import EmbeddingGenerator
from src.models.unified_document_models import ProcessedChunk
from datetime import datetime

async def test_fix_verification():
    """Test that production batch filtering works with the fix."""
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
        
        # Create test chunks with production metadata
        chunks = [
            ProcessedChunk(
                content=f"{test_content} - Document 1",
                embedding=embedding,
                chunk_index=0,
                metadata={
                    "production_batch": "TestBatch001",
                    "producing_party": "Test Party",
                    "production_date": datetime.utcnow().isoformat()
                }
            ),
            ProcessedChunk(
                content=f"{test_content} - Document 2",
                embedding=embedding,
                chunk_index=0,
                metadata={
                    "production_batch": "TestBatch001",
                    "producing_party": "Test Party",
                    "production_date": datetime.utcnow().isoformat()
                }
            ),
            ProcessedChunk(
                content=f"{test_content} - Document 3",
                embedding=embedding,
                chunk_index=0,
                metadata={
                    "production_batch": "TestBatch002",  # Different batch
                    "producing_party": "Other Party",
                    "production_date": datetime.utcnow().isoformat()
                }
            )
        ]
        
        # Store chunks
        print("\n2. Storing test documents...")
        for i, chunk in enumerate(chunks):
            doc_id = f"test_doc_{i+1}"
            await vector_store.store_document_chunks(
                case_name=test_case_name,
                chunks=[chunk],
                document_id=doc_id,
                chunk_metadata=chunk.metadata
            )
        
        # Wait for indexing
        await asyncio.sleep(2)
        
        # Test filtering
        print("\n3. Testing production batch filtering...")
        
        # Test 1: Filter for TestBatch001
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
            print("   ✓ SUCCESS: Filtering works correctly!")
            for result in results:
                print(f"     - {result.content[:50]}...")
        else:
            print("   ✗ FAILED: Filtering not working")
            print("   Checking what's in the collection...")
            
            # Debug: Check all documents
            all_results = vector_store.search_documents(
                collection_name=test_case_name,
                query_embedding=embedding,
                limit=10,
                threshold=0.0,
                filters=None
            )
            print(f"\n   Total documents in collection: {len(all_results)}")
            for result in all_results:
                print(f"     - Content: {result.content[:30]}...")
                print(f"       Metadata keys: {[k for k in result.metadata.keys() if 'production' in k]}")
                if 'production_batch' in result.metadata:
                    print(f"       production_batch: {result.metadata['production_batch']}")
                if 'metadata.production_batch' in result.metadata:
                    print(f"       metadata.production_batch: {result.metadata['metadata.production_batch']}")
        
        # Test 2: Filter for TestBatch002
        results2 = vector_store.search_documents(
            collection_name=test_case_name,
            query_embedding=embedding,
            limit=10,
            threshold=0.0,
            filters={"production_batch": "TestBatch002"}
        )
        print(f"\n   Filter: production_batch='TestBatch002'")
        print(f"   Expected: 1 document")
        print(f"   Actual: {len(results2)} documents")
        
        if len(results2) == 1:
            print("   ✓ SUCCESS: Second filter also works!")
        else:
            print("   ✗ FAILED: Second filter not working")
        
        # Clean up
        print("\n4. Cleaning up test collection...")
        vector_store.client.delete_collection(test_case_name)
        
    except Exception as e:
        print(f"\nError during test: {e}")
        import traceback
        traceback.print_exc()
        
        # Try to clean up
        try:
            vector_store.client.delete_collection(test_case_name)
        except:
            pass

if __name__ == "__main__":
    asyncio.run(test_fix_verification())
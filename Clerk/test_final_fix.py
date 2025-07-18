#!/usr/bin/env python3
"""
Final test to verify production batch filtering fix.
"""
import asyncio
from datetime import datetime
from src.vector_storage.qdrant_store import QdrantVectorStore
from src.vector_storage.embeddings import EmbeddingGenerator
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

async def test_final_fix():
    """Test the production batch filtering fix."""
    vector_store = QdrantVectorStore()
    embedding_generator = EmbeddingGenerator()
    
    print("\n=== FINAL FIX VERIFICATION ===")
    
    # Test with a fresh collection
    test_case = f"final_test_{datetime.utcnow().strftime('%H%M%S')}"
    print(f"\n1. Creating test case: {test_case}")
    
    try:
        # Create collection
        vector_store.create_collection(test_case)
        
        # Generate embeddings
        emb1, _ = embedding_generator.generate_embedding("Test document for batch A")
        emb2, _ = embedding_generator.generate_embedding("Test document for batch B")
        
        # Create test chunks
        chunks = [
            {
                "content": "Document 1 in Batch A",
                "embedding": emb1,
                "metadata": {
                    "production_batch": "BatchA",
                    "producing_party": "Party A",
                    "document_type": "Test Type 1"
                }
            },
            {
                "content": "Document 2 in Batch A", 
                "embedding": emb1,
                "metadata": {
                    "production_batch": "BatchA",
                    "producing_party": "Party A",
                    "document_type": "Test Type 2"
                }
            },
            {
                "content": "Document 3 in Batch B",
                "embedding": emb2,
                "metadata": {
                    "production_batch": "BatchB",
                    "producing_party": "Party B",
                    "document_type": "Test Type 3"
                }
            }
        ]
        
        # Store documents
        print("\n2. Storing test documents...")
        for i, chunk in enumerate(chunks):
            doc_id = f"test_doc_{i+1}"
            chunk_ids = vector_store.store_document_chunks(
                case_name=test_case,
                document_id=doc_id,
                chunks=[chunk]
            )
            print(f"   Stored {doc_id}: {chunk_ids}")
        
        # Wait for indexing
        await asyncio.sleep(3)
        
        # Test filtering
        print("\n3. Testing production batch filtering...")
        
        # Test BatchA
        results_a = vector_store.search_documents(
            collection_name=test_case,
            query_embedding=emb1,
            limit=10,
            threshold=0.0,
            filters={"production_batch": "BatchA"}
        )
        print(f"\n   Filter: production_batch='BatchA'")
        print(f"   Expected: 2 documents")
        print(f"   Actual: {len(results_a)} documents")
        
        if len(results_a) == 2:
            print("   ✅ SUCCESS! BatchA filtering works correctly")
            for r in results_a:
                print(f"      - {r.content}")
        else:
            print("   ❌ FAILED")
            
        # Test BatchB
        results_b = vector_store.search_documents(
            collection_name=test_case,
            query_embedding=emb2,
            limit=10,
            threshold=0.0,
            filters={"production_batch": "BatchB"}
        )
        print(f"\n   Filter: production_batch='BatchB'")
        print(f"   Expected: 1 document")
        print(f"   Actual: {len(results_b)} documents")
        
        if len(results_b) == 1:
            print("   ✅ SUCCESS! BatchB filtering works correctly")
            print(f"      - {results_b[0].content}")
        else:
            print("   ❌ FAILED")
            
        # Test producing_party filter
        results_party = vector_store.search_documents(
            collection_name=test_case,
            query_embedding=emb1,
            limit=10,
            threshold=0.0,
            filters={"producing_party": "Party A"}
        )
        print(f"\n   Filter: producing_party='Party A'")
        print(f"   Expected: 2 documents")
        print(f"   Actual: {len(results_party)} documents")
        
        if len(results_party) == 2:
            print("   ✅ SUCCESS! Producing party filtering also works")
        else:
            print("   ❌ FAILED")
            
        # Clean up
        print("\n4. Cleaning up test collection...")
        vector_store.client.delete_collection(test_case)
        
        # Summary
        total_tests = 3
        passed_tests = (
            (1 if len(results_a) == 2 else 0) +
            (1 if len(results_b) == 1 else 0) +
            (1 if len(results_party) == 2 else 0)
        )
        
        print(f"\n{'='*50}")
        print(f"FINAL RESULT: {passed_tests}/{total_tests} tests passed")
        if passed_tests == total_tests:
            print("✅ ALL TESTS PASSED! The fix is working correctly.")
            print("\nProduction fields are now stored at the top level and can be filtered properly.")
            print("Use filters like: {'production_batch': 'value'} (without metadata. prefix)")
        else:
            print("❌ Some tests failed. Check the implementation.")
        print(f"{'='*50}")
        
    except Exception as e:
        print(f"\nError during test: {e}")
        import traceback
        traceback.print_exc()
        
        # Try to clean up
        try:
            vector_store.client.delete_collection(test_case)
        except:
            pass

if __name__ == "__main__":
    asyncio.run(test_final_fix())
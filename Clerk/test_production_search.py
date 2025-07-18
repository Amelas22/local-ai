#!/usr/bin/env python3
"""
Test script to debug production batch filtering in vector search.
"""
import asyncio
from src.vector_storage.qdrant_store import QdrantVectorStore
from src.vector_storage.embeddings import EmbeddingGenerator
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

async def test_production_search():
    """Test searching with production batch filter."""
    # Initialize components
    vector_store = QdrantVectorStore()
    embedding_generator = EmbeddingGenerator()
    
    # Test case configuration
    case_name = "debug5_071725_7be167d5"  # From your example
    production_batch = "Batch001"
    
    print(f"\n=== Testing Production Batch Search ===")
    print(f"Case: {case_name}")
    print(f"Production Batch: {production_batch}")
    
    # Test query
    test_query = "driver qualification documents and medical records"
    print(f"\nQuery: '{test_query}'")
    
    # Generate embedding
    try:
        embedding, tokens = embedding_generator.generate_embedding(test_query)
        print(f"✓ Generated embedding with {len(embedding)} dimensions ({tokens} tokens)")
    except Exception as e:
        print(f"✗ Failed to generate embedding: {str(e)}")
        return
    
    # Test 1: Search WITH production batch filter
    print(f"\n--- Test 1: Search WITH production_batch filter ---")
    try:
        filtered_results = vector_store.search_documents(
            collection_name=case_name,
            query_embedding=embedding,
            limit=10,
            threshold=0.0,
            filters={"metadata.production_batch": production_batch}
        )
        print(f"Results: {len(filtered_results)} documents found")
        
        if filtered_results:
            for i, result in enumerate(filtered_results[:3]):
                print(f"\nResult {i+1}:")
                print(f"  Score: {result.score:.4f}")
                print(f"  Document ID: {result.document_id}")
                print(f"  Content preview: {result.content[:100]}...")
                print(f"  Metadata keys: {list(result.metadata.keys())}")
                if "metadata.production_batch" in result.metadata:
                    print(f"  Production batch: {result.metadata['metadata.production_batch']}")
    except Exception as e:
        print(f"✗ Error with filtered search: {str(e)}")
        import traceback
        traceback.print_exc()
    
    # Test 2: Search WITHOUT filter
    print(f"\n--- Test 2: Search WITHOUT filter (baseline) ---")
    try:
        unfiltered_results = vector_store.search_documents(
            collection_name=case_name,
            query_embedding=embedding,
            limit=10,
            threshold=0.0,
            filters=None
        )
        print(f"Results: {len(unfiltered_results)} documents found")
        
        if unfiltered_results:
            # Check production batches in results
            batches = set()
            for result in unfiltered_results:
                if "metadata.production_batch" in result.metadata:
                    batches.add(result.metadata["metadata.production_batch"])
            print(f"Production batches found: {batches}")
            
            # Show first result
            print(f"\nFirst result metadata:")
            for key, value in sorted(unfiltered_results[0].metadata.items()):
                if "production" in key.lower() or "batch" in key.lower():
                    print(f"  {key}: {value}")
    except Exception as e:
        print(f"✗ Error with unfiltered search: {str(e)}")
        import traceback
        traceback.print_exc()
    
    # Test 3: Try different filter keys
    print(f"\n--- Test 3: Testing different filter key formats ---")
    filter_variations = [
        {"metadata.production_batch": production_batch},
        {"production_batch": production_batch},  # Without metadata prefix
        {"metadata.production_batch": f'"{production_batch}"'},  # With quotes
    ]
    
    for i, test_filter in enumerate(filter_variations):
        print(f"\nVariation {i+1}: {test_filter}")
        try:
            results = vector_store.search_documents(
                collection_name=case_name,
                query_embedding=embedding,
                limit=5,
                threshold=0.0,
                filters=test_filter
            )
            print(f"  Results: {len(results)} documents")
        except Exception as e:
            print(f"  Error: {str(e)}")
    
    # Test 4: Direct Qdrant client query to verify data
    print(f"\n--- Test 4: Direct Qdrant verification ---")
    try:
        # Get collection info
        collection_info = vector_store.client.get_collection(case_name)
        print(f"Collection '{case_name}' exists with {collection_info.points_count} points")
        
        # Scroll through some points to check metadata
        points = vector_store.client.scroll(
            collection_name=case_name,
            limit=5,
            with_payload=True,
            with_vectors=False
        )
        
        print("\nSample point payloads:")
        for i, point in enumerate(points[0][:2]):  # First 2 points
            print(f"\nPoint {i+1} (ID: {point.id}):")
            payload_keys = list(point.payload.keys())
            print(f"  Total keys: {len(payload_keys)}")
            
            # Show production-related fields
            prod_keys = [k for k in payload_keys if "production" in k.lower() or "batch" in k.lower()]
            if prod_keys:
                print(f"  Production-related keys:")
                for key in prod_keys:
                    print(f"    {key}: {point.payload.get(key)}")
            else:
                print(f"  No production-related keys found!")
                print(f"  Sample keys: {payload_keys[:5]}...")
                
    except Exception as e:
        print(f"✗ Error accessing Qdrant directly: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_production_search())
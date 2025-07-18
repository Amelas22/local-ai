#!/usr/bin/env python3
"""
Debug script to test Qdrant filtering directly.
"""
import asyncio
from src.vector_storage.qdrant_store import QdrantVectorStore
from qdrant_client.models import Filter, FieldCondition, MatchValue, PointStruct
import uuid

async def test_qdrant_debug():
    """Test Qdrant filtering with a simple test case."""
    vector_store = QdrantVectorStore()
    
    # Use the existing collection
    collection_name = "debug5_071725_7be167d5"
    
    print(f"\n=== Qdrant Debug Test ===")
    print(f"Collection: {collection_name}")
    
    # Get the Qdrant client directly
    client = vector_store.client
    
    # 1. First, let's check the exact payload structure
    print("\n--- Checking exact payload structure ---")
    try:
        # Get one point to examine
        points = client.scroll(
            collection_name=collection_name,
            limit=1,
            with_payload=True,
            with_vectors=False
        )
        
        if points[0]:
            point = points[0][0]
            print(f"\nPoint ID: {point.id}")
            print(f"Payload type: {type(point.payload)}")
            print(f"Payload keys ({len(point.payload)} total):")
            
            # Group keys by prefix
            metadata_keys = [k for k in point.payload.keys() if k.startswith("metadata.")]
            other_keys = [k for k in point.payload.keys() if not k.startswith("metadata.")]
            
            print(f"\nMetadata keys ({len(metadata_keys)}):")
            for key in sorted(metadata_keys)[:10]:
                print(f"  {key}: {point.payload[key]}")
            
            print(f"\nOther keys ({len(other_keys)}):")
            for key in sorted(other_keys)[:10]:
                print(f"  {key}: {point.payload[key]}")
                
            # Specifically check production_batch
            prod_batch_key = "metadata.production_batch"
            if prod_batch_key in point.payload:
                print(f"\n✓ Found {prod_batch_key}: '{point.payload[prod_batch_key]}'")
                print(f"  Type: {type(point.payload[prod_batch_key])}")
                print(f"  Repr: {repr(point.payload[prod_batch_key])}")
    except Exception as e:
        print(f"Error checking payload: {e}")
    
    # 2. Test direct filter with Qdrant client
    print("\n--- Testing direct Qdrant filter ---")
    try:
        # Build filter exactly as the search_documents method does
        filter_obj = Filter(
            must=[
                FieldCondition(
                    key="metadata.production_batch",
                    match=MatchValue(value="Batch001")
                )
            ]
        )
        
        # Count points with this filter
        count = client.count(
            collection_name=collection_name,
            count_filter=filter_obj,
            exact=True
        )
        print(f"\nCount with filter: {count.count}")
        
        # Try a search with the filter
        if count.count > 0:
            # Get a dummy vector (use zeros)
            dummy_vector = [0.0] * 1536
            
            results = client.search(
                collection_name=collection_name,
                query_vector={"name": "semantic", "vector": dummy_vector},
                query_filter=filter_obj,
                limit=5
            )
            print(f"Search returned {len(results)} results")
    except Exception as e:
        print(f"Error with direct filter: {e}")
        import traceback
        traceback.print_exc()
    
    # 3. Test if it's a type mismatch issue
    print("\n--- Testing different value types ---")
    test_values = [
        "Batch001",           # String
        b"Batch001",          # Bytes
        ["Batch001"],         # List
        {"value": "Batch001"} # Dict
    ]
    
    for i, test_value in enumerate(test_values):
        print(f"\nTest {i+1}: {type(test_value)} - {repr(test_value)}")
        try:
            filter_obj = Filter(
                must=[
                    FieldCondition(
                        key="metadata.production_batch",
                        match=MatchValue(value=test_value) if isinstance(test_value, (str, bytes)) else test_value
                    )
                ]
            )
            
            count = client.count(
                collection_name=collection_name,
                count_filter=filter_obj,
                exact=True
            )
            print(f"  Count: {count.count}")
        except Exception as e:
            print(f"  Error: {e}")
    
    # 4. Create a test point and verify filtering works
    print("\n--- Creating test point to verify filtering ---")
    test_collection = f"filter_test_{uuid.uuid4().hex[:8]}"
    try:
        # Create test collection
        client.create_collection(
            collection_name=test_collection,
            vectors_config={"size": 4, "distance": "Cosine"}
        )
        
        # Insert test point
        client.upsert(
            collection_name=test_collection,
            points=[
                PointStruct(
                    id=1,
                    vector=[0.1, 0.2, 0.3, 0.4],
                    payload={
                        "metadata.production_batch": "TestBatch",
                        "content": "Test content"
                    }
                )
            ]
        )
        
        # Test filter
        filter_obj = Filter(
            must=[
                FieldCondition(
                    key="metadata.production_batch",
                    match=MatchValue(value="TestBatch")
                )
            ]
        )
        
        count = client.count(
            collection_name=test_collection,
            count_filter=filter_obj,
            exact=True
        )
        print(f"Test collection filter count: {count.count}")
        
        # Clean up
        client.delete_collection(test_collection)
        print("✓ Test collection filtering works correctly")
        
    except Exception as e:
        print(f"Error with test collection: {e}")
        try:
            client.delete_collection(test_collection)
        except:
            pass

if __name__ == "__main__":
    asyncio.run(test_qdrant_debug())
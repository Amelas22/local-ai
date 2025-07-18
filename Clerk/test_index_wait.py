#!/usr/bin/env python3
"""
Test if indexes need more time to build.
"""
import asyncio
import time
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from config.settings import settings

async def test_index_wait():
    """Test filtering after waiting for index build."""
    client = QdrantClient(
        url=settings.qdrant.url,
        api_key=settings.qdrant.api_key,
    )
    
    collection_name = "debug5_071725_7be167d5"
    
    print(f"\n=== Testing Index Build Time ===")
    
    # Create/ensure index exists
    print("Creating index for metadata.production_batch...")
    try:
        client.create_payload_index(
            collection_name=collection_name,
            field_name="metadata.production_batch",
            field_schema="keyword",
            wait=True  # Wait for index to be created
        )
        print("Index created (or already exists)")
    except Exception as e:
        print(f"Index creation result: {e}")
    
    # Test filtering over time
    print("\nTesting filter over time:")
    filter_obj = Filter(
        must=[
            FieldCondition(
                key="metadata.production_batch",
                match=MatchValue(value="Batch001")
            )
        ]
    )
    
    for i in range(5):
        await asyncio.sleep(2)  # Wait 2 seconds between attempts
        
        try:
            count = client.count(
                collection_name=collection_name,
                count_filter=filter_obj,
                exact=True
            )
            print(f"Attempt {i+1} (after {(i+1)*2} seconds): Count = {count.count}")
            
            if count.count > 0:
                print("✓ Filter is now working!")
                break
        except Exception as e:
            print(f"Attempt {i+1}: Error - {e}")
    
    # Try alternative: recreate the entire collection with proper indexes
    print("\n--- Testing with a fresh collection ---")
    test_collection = f"test_prod_batch_{int(time.time())}"
    
    try:
        # Create collection with index from the start
        from qdrant_client.models import VectorParams, Distance
        
        client.create_collection(
            collection_name=test_collection,
            vectors_config=VectorParams(size=4, distance=Distance.COSINE)
        )
        
        # Create index BEFORE adding data
        client.create_payload_index(
            collection_name=test_collection,
            field_name="metadata.production_batch",
            field_schema="keyword"
        )
        
        # Add test point
        from qdrant_client.models import PointStruct
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
        
        # Test filter immediately
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
        print(f"Fresh collection filter count: {count.count}")
        
        # Clean up
        client.delete_collection(test_collection)
        
    except Exception as e:
        print(f"Fresh collection test error: {e}")
        try:
            client.delete_collection(test_collection)
        except:
            pass

if __name__ == "__main__":
    asyncio.run(test_index_wait())
#!/usr/bin/env python3
"""
Test different field name patterns to debug filtering.
"""
import asyncio
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue, MatchAny
from config.settings import settings

async def test_field_names():
    """Test different field name patterns."""
    client = QdrantClient(
        url=settings.qdrant.url,
        api_key=settings.qdrant.api_key,
    )
    
    collection_name = "debug5_071725_7be167d5"
    
    print(f"\n=== Testing Field Name Patterns ===")
    
    # First, get a sample point to see exact field values
    print("\n--- Sample point inspection ---")
    points = client.scroll(
        collection_name=collection_name,
        limit=1,
        with_payload=True,
        with_vectors=False
    )
    
    if points[0]:
        point = points[0][0]
        # Find the exact value of production_batch
        prod_batch_value = point.payload.get("metadata.production_batch")
        print(f"Production batch value: '{prod_batch_value}'")
        print(f"Value type: {type(prod_batch_value)}")
        print(f"Value repr: {repr(prod_batch_value)}")
        print(f"Value length: {len(prod_batch_value) if isinstance(prod_batch_value, str) else 'N/A'}")
        
        # Check for any hidden characters
        if isinstance(prod_batch_value, str):
            print(f"Hex representation: {prod_batch_value.encode('utf-8').hex()}")
            print(f"ASCII codes: {[ord(c) for c in prod_batch_value]}")
    
    # Test different matching approaches
    print("\n--- Testing different matching approaches ---")
    
    # 1. Test with MatchAny instead of MatchValue
    print("\n1. Testing MatchAny:")
    try:
        filter_obj = Filter(
            must=[
                FieldCondition(
                    key="metadata.production_batch",
                    match=MatchAny(any=["Batch001", "Batch001 ", " Batch001"])
                )
            ]
        )
        count = client.count(collection_name=collection_name, count_filter=filter_obj, exact=True)
        print(f"   Count: {count.count}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # 2. Test filtering on a different field we know works
    print("\n2. Testing case_name filter (should work):")
    try:
        filter_obj = Filter(
            must=[
                FieldCondition(
                    key="case_name",
                    match=MatchValue(value=collection_name)
                )
            ]
        )
        count = client.count(collection_name=collection_name, count_filter=filter_obj, exact=True)
        print(f"   Count: {count.count}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # 3. Test if the field exists at all
    print("\n3. Testing field existence with null check:")
    try:
        # This is a hack - we're looking for points where the field is NOT null
        # by searching for points that don't match an impossible value
        filter_obj = Filter(
            must_not=[
                FieldCondition(
                    key="metadata.production_batch",
                    match=MatchValue(value="IMPOSSIBLE_VALUE_THAT_DOESNT_EXIST_123456789")
                )
            ]
        )
        count = client.count(collection_name=collection_name, count_filter=filter_obj, exact=True)
        print(f"   Count of points with field: {count.count}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # 4. Test with nested payload structure
    print("\n4. Testing nested match (if payload is nested):")
    try:
        filter_obj = Filter(
            must=[
                FieldCondition(
                    key="metadata",
                    match={"production_batch": "Batch001"}
                )
            ]
        )
        count = client.count(collection_name=collection_name, count_filter=filter_obj, exact=True)
        print(f"   Count: {count.count}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # 5. Get multiple points and check all production_batch values
    print("\n5. Checking all unique production_batch values:")
    all_points = client.scroll(
        collection_name=collection_name,
        limit=100,  # Get all points
        with_payload=True,
        with_vectors=False
    )
    
    batch_values = set()
    for point in all_points[0]:
        if "metadata.production_batch" in point.payload:
            batch_values.add(point.payload["metadata.production_batch"])
    
    print(f"   Unique production_batch values found: {batch_values}")
    
    # 6. Try exact value from the data
    if batch_values:
        exact_value = list(batch_values)[0]
        print(f"\n6. Testing with exact value from data: '{exact_value}'")
        try:
            filter_obj = Filter(
                must=[
                    FieldCondition(
                        key="metadata.production_batch",
                        match=MatchValue(value=exact_value)
                    )
                ]
            )
            count = client.count(collection_name=collection_name, count_filter=filter_obj, exact=True)
            print(f"   Count: {count.count}")
        except Exception as e:
            print(f"   Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_field_names())
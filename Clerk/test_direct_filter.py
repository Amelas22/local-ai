#!/usr/bin/env python3
"""
Direct test of Qdrant filtering to debug production batch issue.
"""
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from config.settings import settings

def test_direct_qdrant_filter():
    """Test filtering directly with Qdrant client."""
    # Initialize client
    client = QdrantClient(
        url=settings.qdrant.url,
        api_key=settings.qdrant.api_key,
    )
    
    collection_name = "debug6_071725_edee9ad5"
    
    print(f"\n=== Direct Qdrant Filter Test ===")
    print(f"Collection: {collection_name}")
    
    # Test 1: Get collection info
    try:
        info = client.get_collection(collection_name)
        print(f"\nCollection exists with {info.points_count} points")
    except Exception as e:
        print(f"Error getting collection: {e}")
        return
    
    # Test 2: Scroll through points to see metadata structure
    print("\n--- Checking point metadata structure ---")
    try:
        points, _ = client.scroll(
            collection_name=collection_name,
            limit=3,
            with_payload=True,
            with_vectors=False
        )
        
        for i, point in enumerate(points):
            print(f"\nPoint {i+1} (ID: {point.id}):")
            print(f"Payload keys: {list(point.payload.keys())[:10]}...")
            
            # Look for production batch fields
            for key in point.payload.keys():
                if "production" in key.lower() or "batch" in key.lower():
                    print(f"  {key}: {point.payload[key]}")
                    
    except Exception as e:
        print(f"Error scrolling points: {e}")
    
    # Test 3: Try different filter formats
    print("\n--- Testing different filter formats ---")
    
    filter_tests = [
        ("metadata.production_batch", "Batch001"),
        ("metadata.production_batch", "\"Batch001\""),
        ("production_batch", "Batch001"),
    ]
    
    for field_name, field_value in filter_tests:
        print(f"\nTesting filter: {field_name} = {field_value}")
        try:
            # Create filter
            filter_obj = Filter(
                must=[
                    FieldCondition(
                        key=field_name,
                        match=MatchValue(value=field_value)
                    )
                ]
            )
            
            # Try to count points with this filter
            count_result = client.count(
                collection_name=collection_name,
                count_filter=filter_obj,
                exact=True
            )
            print(f"  Count with filter: {count_result.count}")
            
            # If count > 0, try a search
            if count_result.count > 0:
                # Get a random embedding from existing points
                sample_point = points[0] if points else None
                if sample_point and "semantic" in info.config.params.vectors:
                    # For hybrid collections
                    search_results = client.search(
                        collection_name=collection_name,
                        query_vector={"semantic": [0.1] * 1536},  # Dummy vector
                        query_filter=filter_obj,
                        limit=1
                    )
                else:
                    # For standard collections  
                    search_results = client.search(
                        collection_name=collection_name,
                        query_vector=[0.1] * 1536,  # Dummy vector
                        query_filter=filter_obj,
                        limit=1
                    )
                print(f"  Search returned {len(search_results)} results")
            
        except Exception as e:
            print(f"  Error: {e}")
    
    # Test 4: Check if it's a nested field issue
    print("\n--- Checking for nested field structure ---")
    try:
        # Try filter with nested structure
        filter_nested = Filter(
            must=[
                FieldCondition(
                    key="metadata",
                    match={
                        "production_batch": "Batch001"
                    }
                )
            ]
        )
        
        count_result = client.count(
            collection_name=collection_name,
            count_filter=filter_nested,
            exact=True
        )
        print(f"Count with nested filter: {count_result.count}")
        
    except Exception as e:
        print(f"Nested filter error: {e}")

if __name__ == "__main__":
    test_direct_qdrant_filter()
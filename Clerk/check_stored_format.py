#!/usr/bin/env python3
"""
Check how fields are actually stored.
"""
from qdrant_client import QdrantClient
from config.settings import settings

def check_stored_format():
    """Check the actual stored format of recent documents."""
    client = QdrantClient(
        url=settings.qdrant.url,
        api_key=settings.qdrant.api_key,
    )
    
    print("\n=== Checking Stored Field Format ===")
    
    # Get the most recent test collection
    collections = client.get_collections().collections
    test_collections = [c for c in collections if c.name.startswith("test_debug_")]
    
    if test_collections:
        # Sort by name (which includes timestamp) and get the latest
        latest = sorted(test_collections, key=lambda x: x.name)[-1]
        collection_name = latest.name
        print(f"\nChecking collection: {collection_name}")
        
        # Get points from this collection
        points = client.scroll(
            collection_name=collection_name,
            limit=10,
            with_payload=True,
            with_vectors=False
        )
        
        if points[0]:
            print(f"\nFound {len(points[0])} points")
            for i, point in enumerate(points[0]):
                print(f"\nPoint {i+1} (ID: {point.id}):")
                print("Payload fields:")
                
                # Group by production fields
                prod_fields = {}
                metadata_fields = {}
                other_fields = {}
                
                for key, value in point.payload.items():
                    if key in ["production_batch", "producing_party", "production_date"]:
                        prod_fields[key] = value
                    elif key.startswith("metadata."):
                        metadata_fields[key] = value
                    else:
                        other_fields[key] = value
                
                if prod_fields:
                    print("\n  Production fields (TOP LEVEL):")
                    for k, v in prod_fields.items():
                        print(f"    {k}: {v}")
                
                if metadata_fields:
                    print("\n  Metadata fields (WITH PREFIX):")
                    for k, v in sorted(metadata_fields.items())[:5]:
                        print(f"    {k}: {v}")
                    if len(metadata_fields) > 5:
                        print(f"    ... and {len(metadata_fields) - 5} more")
                
                if other_fields:
                    print("\n  Other fields:")
                    for k, v in sorted(other_fields.items())[:5]:
                        print(f"    {k}: {v}")
                        
                # Test filtering
                print("\n  Testing filters on this collection:")
                
                # Test top-level filter
                if "production_batch" in prod_fields:
                    from qdrant_client.models import Filter, FieldCondition, MatchValue
                    filter_obj = Filter(
                        must=[
                            FieldCondition(
                                key="production_batch",
                                match=MatchValue(value=prod_fields["production_batch"])
                            )
                        ]
                    )
                    count = client.count(collection_name=collection_name, count_filter=filter_obj, exact=True)
                    print(f"    Filter 'production_batch={prod_fields['production_batch']}': {count.count} results")
                    
                    if count.count > 0:
                        print("    ✓ SUCCESS: Top-level filtering works!")
    else:
        print("No test collections found")
    
    # Also check the main collection
    print("\n\n=== Checking Main Collection (debug5_071725_7be167d5) ===")
    main_collection = "debug5_071725_7be167d5"
    
    # Get the most recent point (highest ID)
    points = client.scroll(
        collection_name=main_collection,
        limit=100,
        with_payload=True,
        with_vectors=False,
        order_by="indexed_at"  # Get most recent
    )
    
    if points[0]:
        # Find points with "fixed" or "NEW DOCUMENT" in content
        recent_points = [p for p in points[0] if "fixed" in p.payload.get("content", "").lower() or "NEW DOCUMENT" in p.payload.get("content", "")]
        
        if recent_points:
            print(f"\nFound {len(recent_points)} recently added test points")
            point = recent_points[0]
            
            print(f"\nPoint ID: {point.id}")
            print(f"Content: {point.payload.get('content', '')[:60]}...")
            
            # Check field structure
            prod_fields = {}
            metadata_prod_fields = {}
            
            for key, value in point.payload.items():
                if key in ["production_batch", "producing_party", "production_date"]:
                    prod_fields[key] = value
                elif key.startswith("metadata.") and "production" in key:
                    metadata_prod_fields[key] = value
            
            if prod_fields:
                print("\nProduction fields at TOP LEVEL:")
                for k, v in prod_fields.items():
                    print(f"  {k}: {v}")
            
            if metadata_prod_fields:
                print("\nProduction fields with metadata. PREFIX:")
                for k, v in metadata_prod_fields.items():
                    print(f"  {k}: {v}")

if __name__ == "__main__":
    check_stored_format()
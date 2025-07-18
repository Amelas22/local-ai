#!/usr/bin/env python3
"""
Check if indexes exist on the collection.
"""
import asyncio
from src.vector_storage.qdrant_store import QdrantVectorStore

async def check_indexes():
    """Check indexes on collection."""
    vector_store = QdrantVectorStore()
    collection_name = "debug5_071725_7be167d5"
    
    print(f"\n=== Checking Indexes on {collection_name} ===")
    
    try:
        # Get collection info
        info = vector_store.client.get_collection(collection_name)
        print(f"\nCollection exists with {info.points_count} points")
        
        # Check if we can access payload indexes info
        # Note: This might not be directly accessible via the API
        print("\nCollection config:")
        print(f"  Vectors config: {info.config.params.vectors}")
        print(f"  On disk payload: {info.config.params.on_disk_payload}")
        
        # Try to create the index - if it already exists, it will error
        print("\n--- Attempting to create indexes ---")
        indexes_to_create = [
            ("metadata.production_batch", "keyword"),
            ("case_name", "keyword"),
            ("document_id", "keyword"),
        ]
        
        for field_name, field_type in indexes_to_create:
            try:
                vector_store.client.create_payload_index(
                    collection_name=collection_name,
                    field_name=field_name,
                    field_schema=field_type,
                )
                print(f"✓ Created index for {field_name}")
            except Exception as e:
                if "already exists" in str(e).lower():
                    print(f"✓ Index already exists for {field_name}")
                else:
                    print(f"✗ Error creating index for {field_name}: {e}")
        
        # Wait a moment for indexes to be built
        print("\nWaiting for indexes to be built...")
        await asyncio.sleep(2)
        
        # Test filtering again
        print("\n--- Testing filter after ensuring indexes ---")
        from qdrant_client.models import Filter, FieldCondition, MatchValue
        
        filter_obj = Filter(
            must=[
                FieldCondition(
                    key="metadata.production_batch",
                    match=MatchValue(value="Batch001")
                )
            ]
        )
        
        count = vector_store.client.count(
            collection_name=collection_name,
            count_filter=filter_obj,
            exact=True
        )
        print(f"\nCount with filter: {count.count}")
        
        # Also test with a simple scroll with filter
        points = vector_store.client.scroll(
            collection_name=collection_name,
            scroll_filter=filter_obj,
            limit=5,
            with_payload=True,
            with_vectors=False
        )
        
        print(f"Scroll with filter returned {len(points[0])} points")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(check_indexes())
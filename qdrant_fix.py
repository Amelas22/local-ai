#!/usr/bin/env python3
"""
Add missing upsert_points method to QdrantVectorStore as a wrapper
"""

# Add this method to the QdrantVectorStore class
def upsert_points(self, collection_name: str, points: list, **kwargs):
    """
    Wrapper method for Qdrant client's upsert method
    
    Args:
        collection_name: Name of the collection
        points: List of points to upsert
        **kwargs: Additional arguments for the upsert method
    """
    try:
        # Ensure collection exists
        self.ensure_collection_exists(collection_name)
        
        # Call the client's upsert method
        return self.client.upsert(
            collection_name=collection_name,
            points=points,
            **kwargs
        )
    except Exception as e:
        logger.error(f"Error upserting points to {collection_name}: {e}")
        raise

# Add to QdrantVectorStore class
print("""
Add this method to the QdrantVectorStore class in /app/src/vector_storage/qdrant_store.py:

    def upsert_points(self, collection_name: str, points: list, **kwargs):
        \"\"\"
        Wrapper method for Qdrant client's upsert method
        
        Args:
            collection_name: Name of the collection
            points: List of points to upsert
            **kwargs: Additional arguments for the upsert method
        \"\"\"
        try:
            # Ensure collection exists
            self.ensure_collection_exists(collection_name)
            
            # Call the client's upsert method
            return self.client.upsert(
                collection_name=collection_name,
                points=points,
                **kwargs
            )
        except Exception as e:
            logger.error(f"Error upserting points to {collection_name}: {e}")
            raise
""")
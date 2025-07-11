"""
Test database connectivity from within Docker container.

These tests ensure that services can connect to each other using
Docker's internal networking.
"""

import pytest
import os
import time
from qdrant_client import QdrantClient
from src.config.settings import settings


@pytest.mark.container
class TestContainerConnectivity:
    """Test database connectivity from within Docker container"""

    def test_qdrant_connection(self):
        """Test that Qdrant is accessible from container"""
        # Use internal Docker network hostname
        qdrant_host = os.getenv("QDRANT_HOST", "qdrant")
        qdrant_port = int(os.getenv("QDRANT_PORT", "6333"))

        client = QdrantClient(
            host=qdrant_host,
            port=qdrant_port,
            api_key=settings.qdrant.api_key if settings.qdrant.api_key else None,
        )

        # Test connection
        try:
            collections = client.get_collections()
            assert collections is not None
            print(f"Successfully connected to Qdrant at {qdrant_host}:{qdrant_port}")
            print(f"Found {len(collections.collections)} existing collections")
        except Exception as e:
            pytest.fail(f"Failed to connect to Qdrant: {e}")

    @pytest.mark.asyncio
    async def test_collection_creation_in_container(self):
        """Test collection creation from within container"""
        from src.vector_storage.qdrant_store import QdrantVectorStore

        store = QdrantVectorStore()
        test_collection = f"test_container_{int(time.time())}"

        # Create collections
        results = await store.create_case_collections(test_collection)

        # Verify all collections created
        assert len(results) == 4, f"Expected 4 collections, got {len(results)}"
        assert all(results.values()), f"Some collections failed: {results}"

        # Verify collection names
        expected_collections = [
            test_collection,
            f"{test_collection}_facts",
            f"{test_collection}_timeline",
            f"{test_collection}_depositions",
        ]

        for expected in expected_collections:
            assert expected in results, f"Missing collection: {expected}"

        print(f"Successfully created all collections: {list(results.keys())}")

        # Cleanup
        for collection_name in results.keys():
            try:
                store.client.delete_collection(collection_name)
                print(f"Cleaned up collection: {collection_name}")
            except Exception as e:
                print(f"Failed to cleanup {collection_name}: {e}")

    @pytest.mark.asyncio
    async def test_websocket_connectivity(self):
        """Test WebSocket server connectivity from container"""
        from src.websocket.socket_server import emit_case_event

        # This test verifies that WebSocket events can be emitted
        # In a real container environment, you'd verify the events are received
        try:
            await emit_case_event(
                "test_event",
                "test-case-123",
                {"message": "Container connectivity test", "timestamp": time.time()},
            )
            print("Successfully emitted WebSocket event from container")
        except Exception as e:
            pytest.fail(f"Failed to emit WebSocket event: {e}")

    def test_postgres_connection(self):
        """Test PostgreSQL connectivity from container"""
        from sqlalchemy import create_engine, text

        # Use container network hostname
        postgres_host = os.getenv("POSTGRES_HOST", "postgres")
        postgres_port = os.getenv("POSTGRES_PORT", "5432")
        postgres_db = os.getenv("POSTGRES_DB", "clerk_db")
        postgres_user = os.getenv("POSTGRES_USER", "clerk_user")
        postgres_pass = os.getenv("POSTGRES_PASSWORD", "clerk_password")

        connection_string = (
            f"postgresql://{postgres_user}:{postgres_pass}@"
            f"{postgres_host}:{postgres_port}/{postgres_db}"
        )

        try:
            engine = create_engine(connection_string)
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                assert result.scalar() == 1
                print(
                    f"Successfully connected to PostgreSQL at {postgres_host}:{postgres_port}"
                )
        except Exception as e:
            pytest.fail(f"Failed to connect to PostgreSQL: {e}")

    @pytest.mark.asyncio
    async def test_full_case_creation_flow(self):
        """Test complete case creation flow including Qdrant collections"""

        # This would require proper database setup and session management
        # Placeholder for full integration test
        print("Full case creation flow test - requires database session setup")

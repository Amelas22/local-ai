#!/usr/bin/env python3
"""
Wait for required services to be available before starting the application.
"""

import time
import sys
import logging
from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse
import psycopg2
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def wait_for_qdrant(host="qdrant", port=6333, timeout=60):
    """Wait for Qdrant to be available."""
    logger.info(f"Waiting for Qdrant at {host}:{port}...")
    
    client = QdrantClient(host=host, port=port)
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            # Try to get collections
            collections = client.get_collections()
            logger.info(f"Qdrant is ready! Found {len(collections.collections)} collections")
            return True
        except Exception as e:
            logger.debug(f"Qdrant not ready yet: {e}")
            time.sleep(2)
    
    logger.error(f"Qdrant not available after {timeout} seconds")
    return False

def wait_for_postgres(timeout=60):
    """Wait for PostgreSQL to be available."""
    logger.info("Waiting for PostgreSQL...")
    
    # Get connection details from environment
    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:password@postgres:5432/postgres")
    
    # Parse connection string
    if "postgresql://" in db_url:
        parts = db_url.replace("postgresql://", "").split("@")
        if len(parts) == 2:
            user_pass = parts[0].split(":")
            host_port_db = parts[1].split("/")
            host_port = host_port_db[0].split(":")
            
            user = user_pass[0]
            password = user_pass[1] if len(user_pass) > 1 else ""
            host = host_port[0]
            port = int(host_port[1]) if len(host_port) > 1 else 5432
            database = host_port_db[1] if len(host_port_db) > 1 else "postgres"
        else:
            # Fallback to defaults
            user = "postgres"
            password = os.getenv("POSTGRES_PASSWORD", "password")
            host = "postgres"
            port = 5432
            database = "postgres"
    
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            conn = psycopg2.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                database=database,
                connect_timeout=5
            )
            conn.close()
            logger.info("PostgreSQL is ready!")
            return True
        except Exception as e:
            logger.debug(f"PostgreSQL not ready yet: {e}")
            time.sleep(2)
    
    logger.error(f"PostgreSQL not available after {timeout} seconds")
    return False

def main():
    """Wait for all required services."""
    logger.info("Starting service availability checks...")
    
    # Check Qdrant
    if not wait_for_qdrant():
        logger.error("Failed to connect to Qdrant")
        sys.exit(1)
    
    # Check PostgreSQL
    if not wait_for_postgres():
        logger.error("Failed to connect to PostgreSQL")
        sys.exit(1)
    
    logger.info("All services are ready!")
    
    # Add a small delay to ensure services are fully initialized
    time.sleep(3)

if __name__ == "__main__":
    main()
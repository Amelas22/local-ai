#!/usr/bin/env python3
"""
Test if the Socket.IO server is working properly
"""
import asyncio
from fastapi import FastAPI
from src.websocket import socket_app, sio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_emit():
    """Test emitting events"""
    logger.info("Testing Socket.IO server...")
    
    # Check if there are any connected clients
    from src.websocket import get_active_connections
    connections = get_active_connections()
    logger.info(f"Active connections: {connections}")
    
    # Try to emit a test event
    try:
        await sio.emit('test_event', {'message': 'Hello from server!'})
        logger.info("Successfully emitted test event")
    except Exception as e:
        logger.error(f"Error emitting event: {e}")
    
    # List all registered event handlers
    logger.info(f"Registered handlers: {list(sio.handlers.keys())}")
    logger.info(f"Namespace handlers: {list(sio.namespace_handlers.keys())}")

if __name__ == "__main__":
    # Run the test
    asyncio.run(test_emit())
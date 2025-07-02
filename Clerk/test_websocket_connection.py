#!/usr/bin/env python3
"""
Test WebSocket connection to the Clerk backend
"""
import asyncio
import socketio
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def test_connection():
    """Test WebSocket connection"""
    # Create a Socket.IO client
    sio = socketio.AsyncClient(
        logger=True,
        engineio_logger=True
    )
    
    # Define event handlers
    @sio.event
    async def connect():
        logger.info("Connected to WebSocket server!")
        
    @sio.event
    async def connected(data):
        logger.info(f"Received 'connected' event: {data}")
        
    @sio.event
    async def disconnect():
        logger.info("Disconnected from WebSocket server")
        
    @sio.event
    async def connect_error(data):
        logger.error(f"Connection error: {data}")
    
    try:
        # Try to connect
        logger.info("Attempting to connect to ws://localhost:8000/ws with path /socket.io/")
        await sio.connect(
            'ws://localhost:8000', 
            socketio_path='/ws/socket.io/',
            transports=['websocket']
        )
        
        # Wait a bit to see if we receive any events
        await asyncio.sleep(2)
        
        # Send a ping
        await sio.emit('ping')
        await asyncio.sleep(1)
        
        # Disconnect
        await sio.disconnect()
        
    except Exception as e:
        logger.error(f"Failed to connect: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_connection())
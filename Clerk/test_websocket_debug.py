#!/usr/bin/env python3
"""
WebSocket Connection Debugger for Clerk
Tests WebSocket connectivity through different paths
"""

import asyncio
import socketio
import aiohttp
import sys
import json
from datetime import datetime

async def test_connection(url, path='/ws/socket.io/'):
    """Test a WebSocket connection"""
    print(f"\n{'='*60}")
    print(f"Testing connection to: {url}")
    print(f"Socket.IO path: {path}")
    print(f"Time: {datetime.now().isoformat()}")
    print(f"{'='*60}")
    
    sio = socketio.AsyncClient(
        logger=True,
        engineio_logger=True
    )
    
    # Event handlers
    @sio.event
    async def connect():
        print("✅ Connected successfully!")
        print(f"Session ID: {sio.sid}")
        
    @sio.event
    async def connect_error(data):
        print(f"❌ Connection error: {data}")
        
    @sio.event
    async def disconnect():
        print("🔌 Disconnected")
        
    @sio.event
    async def connected(data):
        print(f"📨 Received 'connected' event: {json.dumps(data, indent=2)}")
    
    # Try to connect
    try:
        print("🔄 Attempting to connect...")
        await sio.connect(
            url,
            auth={'token': 'test-token'},
            socketio_path=path,
            transports=['websocket', 'polling'],
            wait_timeout=10
        )
        
        # Wait a bit to receive events
        await asyncio.sleep(2)
        
        # Test emitting an event
        print("📤 Testing emit...")
        await sio.emit('ping')
        await asyncio.sleep(1)
        
        # Disconnect
        await sio.disconnect()
        
    except Exception as e:
        print(f"❌ Exception: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """Test various connection scenarios"""
    
    # Test configurations
    test_configs = [
        # Direct backend connection
        ("http://localhost:8000", "/ws/socket.io/"),
        
        # Through Caddy proxy
        ("http://localhost:8010", "/ws/socket.io/"),
        
        # WebSocket protocol through Caddy
        ("ws://localhost:8010", "/ws/socket.io/"),
    ]
    
    print("🧪 Clerk WebSocket Connection Debugger")
    print("=====================================\n")
    
    # First, test if services are running
    print("📡 Checking if services are reachable...")
    
    async with aiohttp.ClientSession() as session:
        # Test backend health
        try:
            async with session.get('http://localhost:8000/health') as resp:
                if resp.status == 200:
                    print("✅ Backend API is reachable at port 8000")
                else:
                    print(f"⚠️  Backend API returned status {resp.status}")
        except Exception as e:
            print(f"❌ Cannot reach backend API at port 8000: {e}")
            
        # Test Caddy proxy
        try:
            async with session.get('http://localhost:8010/api/health') as resp:
                if resp.status == 200:
                    print("✅ Caddy proxy is reachable at port 8010")
                else:
                    print(f"⚠️  Caddy proxy returned status {resp.status}")
        except Exception as e:
            print(f"❌ Cannot reach Caddy proxy at port 8010: {e}")
    
    # Test each configuration
    for url, path in test_configs:
        await test_connection(url, path)
        await asyncio.sleep(1)
    
    print("\n📊 Summary")
    print("==========")
    print("If direct backend connection works but Caddy proxy doesn't:")
    print("- Check Caddy configuration for WebSocket headers")
    print("- Verify CORS settings include the frontend origin")
    print("- Ensure the /ws/* route is properly configured in Caddyfile")
    print("\nIf neither works:")
    print("- Check if the Clerk backend service is running")
    print("- Verify the WebSocket mount in main.py")
    print("- Check for any firewall or network issues")

if __name__ == "__main__":
    asyncio.run(main())
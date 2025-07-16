#!/usr/bin/env python3
"""Test WebSocket discovery events with room-based subscriptions"""

import asyncio
import socketio
import json
import sys

# Create Socket.IO client
sio = socketio.AsyncClient(logger=True, engineio_logger=False)

# Global variables
case_id = "test_case_websocket"
received_events = []

@sio.event
async def connect():
    print("✅ Connected to WebSocket server")
    print(f"🔗 Session ID: {sio.sid}")

@sio.event
async def connected(data):
    print(f"✅ Received 'connected' event: {data}")
    # Subscribe to case
    print(f"📤 Subscribing to case: {case_id}")
    await sio.emit('subscribe_case', {'case_id': case_id})

@sio.event
async def subscribed(data):
    print(f"✅ Received 'subscribed' event: {data}")
    print(f"✅ Successfully subscribed to case: {data.get('case_id')}")

@sio.event
async def disconnect():
    print("❌ Disconnected from WebSocket server")

# Discovery event handlers
@sio.on('discovery:started')
async def on_discovery_started(data):
    print(f"🚀 Received discovery:started: {json.dumps(data, indent=2)}")
    received_events.append('discovery:started')

@sio.on('discovery:document_found')
async def on_document_found(data):
    print(f"📄 Received discovery:document_found: {json.dumps(data, indent=2)}")
    received_events.append('discovery:document_found')

@sio.on('discovery:chunking')
async def on_chunking(data):
    print(f"🔪 Received discovery:chunking: {json.dumps(data, indent=2)}")
    received_events.append('discovery:chunking')

@sio.on('discovery:embedding')
async def on_embedding(data):
    print(f"🧮 Received discovery:embedding: {json.dumps(data, indent=2)}")
    received_events.append('discovery:embedding')

@sio.on('discovery:stored')
async def on_stored(data):
    print(f"💾 Received discovery:stored: {json.dumps(data, indent=2)}")
    received_events.append('discovery:stored')

@sio.on('discovery:fact_extracted')
async def on_fact_extracted(data):
    print(f"💡 Received discovery:fact_extracted: {json.dumps(data, indent=2)}")
    received_events.append('discovery:fact_extracted')

@sio.on('discovery:document_completed')
async def on_document_completed(data):
    print(f"✅ Received discovery:document_completed: {json.dumps(data, indent=2)}")
    received_events.append('discovery:document_completed')

@sio.on('discovery:completed')
async def on_discovery_completed(data):
    print(f"🎉 Received discovery:completed: {json.dumps(data, indent=2)}")
    received_events.append('discovery:completed')

@sio.on('discovery:error')
async def on_discovery_error(data):
    print(f"❌ Received discovery:error: {json.dumps(data, indent=2)}")
    received_events.append('discovery:error')

async def test_websocket_events():
    """Test WebSocket event reception with room subscriptions"""
    try:
        # Connect to WebSocket server
        print("🔌 Connecting to WebSocket server...")
        await sio.connect(
            'http://localhost:8000',
            socketio_path='/ws/socket.io/',
            transports=['websocket', 'polling']
        )
        
        # Wait for connection and subscription
        await asyncio.sleep(2)
        
        # Emit a test discovery event from another client
        print("\n📡 Triggering test discovery events...")
        import httpx
        async with httpx.AsyncClient() as client:
            # Trigger test events via API
            response = await client.post(
                'http://localhost:8000/api/discovery/test-events',
                headers={'X-Case-ID': case_id}
            )
            if response.status_code == 200:
                print("✅ Test events triggered successfully")
            else:
                print(f"❌ Failed to trigger test events: {response.status_code}")
                print(response.text)
        
        # Wait for events to be received
        print("\n⏳ Waiting for events...")
        await asyncio.sleep(5)
        
        # Summary
        print("\n📊 Summary:")
        print(f"Total events received: {len(received_events)}")
        print(f"Event types: {set(received_events)}")
        
        expected_events = [
            'discovery:started',
            'discovery:document_found',
            'discovery:chunking',
            'discovery:fact_extracted',
            'discovery:document_completed',
            'discovery:completed'
        ]
        
        missing_events = set(expected_events) - set(received_events)
        if missing_events:
            print(f"❌ Missing events: {missing_events}")
        else:
            print("✅ All expected events received!")
        
        # Disconnect
        await sio.disconnect()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(test_websocket_events())
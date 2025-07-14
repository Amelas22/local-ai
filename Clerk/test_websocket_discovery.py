#!/usr/bin/env python
"""
Monitor WebSocket events during discovery processing
"""

import asyncio
import socketio
import requests
import base64
import json
from datetime import datetime

# Track events
events_received = []
documents_found = []
documents_processed = []

# Configure Socket.IO client
sio = socketio.AsyncClient()

@sio.event
async def connect():
    print(f"✅ Connected to WebSocket at {datetime.now()}")

@sio.on('discovery:started')
async def on_started(data):
    print(f"🚀 Discovery Started: {data}")
    events_received.append(('discovery:started', data))

@sio.on('discovery:document_found')
async def on_document_found(data):
    print(f"📄 Document Found: {data.get('title')} (ID: {data.get('document_id')})")
    documents_found.append(data)
    events_received.append(('discovery:document_found', data))

@sio.on('discovery:chunking')
async def on_chunking(data):
    print(f"✂️  Chunking: Document {data.get('document_id')}")
    events_received.append(('discovery:chunking', data))

@sio.on('discovery:embedding')
async def on_embedding(data):
    print(f"🔤 Embedding: Document {data.get('document_id')} - {data.get('total_chunks')} chunks")
    events_received.append(('discovery:embedding', data))

@sio.on('discovery:fact_extracted')
async def on_fact_extracted(data):
    print(f"💡 Fact Extracted: {data.get('fact', {}).get('category')}")
    events_received.append(('discovery:fact_extracted', data))

@sio.on('discovery:error')
async def on_error(data):
    print(f"❌ Error: {data.get('error')}")
    events_received.append(('discovery:error', data))

@sio.on('discovery:completed')
async def on_completed(data):
    print(f"✅ Completed: {data.get('total_documents_found')} documents, {data.get('documents_processed')} processed")
    documents_processed.append(data)
    events_received.append(('discovery:completed', data))

async def submit_discovery_request():
    """Submit a discovery processing request"""
    await asyncio.sleep(2)  # Wait for WebSocket to connect
    
    # Read test PDF
    with open('/app/tesdoc_Redacted_ocr.pdf', 'rb') as f:
        pdf_content = f.read()
    
    pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')
    
    request_data = {
        "discovery_files": [{
            "filename": "tesdoc_Redacted_ocr.pdf",
            "content": pdf_base64,
            "content_type": "application/pdf"
        }],
        "production_batch": "WEBSOCKET_TEST",
        "producing_party": "WebSocket Test",
        "enable_fact_extraction": False  # Disable for faster testing
    }
    
    headers = {
        'Content-Type': 'application/json',
        'X-Case-ID': 'test_websocket',
        'X-Case-Name': 'Test WebSocket'
    }
    
    print("\n📤 Submitting discovery request...")
    response = requests.post(
        "http://localhost:8000/api/discovery/process",
        json=request_data,
        headers=headers
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Processing started: {result.get('processing_id')}")
        return result.get('processing_id')
    else:
        print(f"❌ Request failed: {response.status_code}")
        return None

async def main():
    """Main function"""
    # Connect to WebSocket
    await sio.connect('http://localhost:8000', socketio_path='/ws/socket.io')
    
    # Submit discovery request
    processing_id = await submit_discovery_request()
    
    if processing_id:
        # Wait for completion
        print("\n⏳ Waiting for processing to complete...")
        await asyncio.sleep(90)  # Wait up to 90 seconds
    
    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total Events: {len(events_received)}")
    print(f"Documents Found: {len(documents_found)}")
    
    # Count event types
    event_counts = {}
    for event_type, _ in events_received:
        event_counts[event_type] = event_counts.get(event_type, 0) + 1
    
    print("\nEvent Types:")
    for event_type, count in sorted(event_counts.items()):
        print(f"  {event_type}: {count}")
    
    # Show documents
    if documents_found:
        print(f"\nDocuments Found ({len(documents_found)}):")
        for i, doc in enumerate(documents_found[:10]):  # Show first 10
            print(f"  {i+1}. {doc.get('title')} (pages {doc.get('pages')})")
    
    # Disconnect
    await sio.disconnect()

if __name__ == '__main__':
    asyncio.run(main())
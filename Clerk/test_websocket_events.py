#!/usr/bin/env python
"""
WebSocket Event Monitor for Discovery Processing

This script connects to the Clerk WebSocket server and monitors all discovery-related events.
Use this to debug whether WebSocket events are being emitted correctly during PDF processing.
"""

import asyncio
import socketio
import sys
from datetime import datetime
import json

# Configure Socket.IO client
sio = socketio.AsyncClient(
    logger=True,
    engineio_logger=True,
    reconnection=True,
    reconnection_attempts=5,
    reconnection_delay=1,
    reconnection_delay_max=5
)

# Track document discoveries
documents_found = []
events_received = []

@sio.event
async def connect():
    print(f"\n✅ Connected to WebSocket server at {datetime.now()}")
    print("Monitoring for discovery events...\n")

@sio.event
async def disconnect():
    print(f"\n❌ Disconnected from WebSocket server at {datetime.now()}")

@sio.on('discovery:started')
async def on_started(data):
    print(f"🚀 Discovery Started at {datetime.now()}")
    print(f"   Processing ID: {data.get('processing_id')}")
    print(f"   Case Name: {data.get('case_name')}")
    print(f"   Total Files: {data.get('total_files')}")
    print("   " + "-" * 50)
    events_received.append(('discovery:started', data))

@sio.on('discovery:document_found')
async def on_document_found(data):
    doc_id = data.get('document_id')
    title = data.get('title', 'Untitled')
    doc_type = data.get('type', 'Unknown')
    pages = data.get('pages', 'N/A')
    confidence = data.get('confidence', 0.0)
    
    print(f"📄 Document Found at {datetime.now()}")
    print(f"   Document ID: {doc_id}")
    print(f"   Title: {title}")
    print(f"   Type: {doc_type}")
    print(f"   Pages: {pages}")
    print(f"   Confidence: {confidence:.2f}")
    print(f"   Bates Range: {data.get('bates_range', 'N/A')}")
    print("   " + "-" * 50)
    
    documents_found.append(data)
    events_received.append(('discovery:document_found', data))

@sio.on('discovery:chunking')
async def on_chunking(data):
    print(f"✂️  Chunking at {datetime.now()}")
    print(f"   Document ID: {data.get('document_id')}")
    print(f"   Status: {data.get('status')}")
    events_received.append(('discovery:chunking', data))

@sio.on('discovery:embedding')
async def on_embedding(data):
    print(f"🔤 Embedding at {datetime.now()}")
    print(f"   Document ID: {data.get('document_id')}")
    print(f"   Total Chunks: {data.get('total_chunks')}")
    events_received.append(('discovery:embedding', data))

@sio.on('discovery:fact_extracted')
async def on_fact_extracted(data):
    fact = data.get('fact', {})
    print(f"💡 Fact Extracted at {datetime.now()}")
    print(f"   Document ID: {data.get('document_id')}")
    print(f"   Fact ID: {fact.get('fact_id')}")
    print(f"   Category: {fact.get('category')}")
    print(f"   Confidence: {fact.get('confidence', 0.0):.2f}")
    print(f"   Text: {fact.get('text', '')[:100]}...")
    events_received.append(('discovery:fact_extracted', data))

@sio.on('discovery:error')
async def on_error(data):
    print(f"❌ Error at {datetime.now()}")
    print(f"   Processing ID: {data.get('processing_id')}")
    print(f"   Document ID: {data.get('document_id')}")
    print(f"   Error: {data.get('error')}")
    print("   " + "-" * 50)
    events_received.append(('discovery:error', data))

@sio.on('discovery:completed')
async def on_completed(data):
    print(f"\n✅ Discovery Completed at {datetime.now()}")
    print(f"   Processing ID: {data.get('processing_id')}")
    print(f"   Total Documents Found: {data.get('total_documents_found', 0)}")
    print(f"   Documents Processed: {data.get('documents_processed', 0)}")
    print(f"   Facts Extracted: {data.get('facts_extracted', 0)}")
    print(f"   Status: {data.get('status')}")
    if data.get('errors'):
        print(f"   Errors: {len(data.get('errors', []))}")
    print("\n" + "=" * 60)
    print(f"SUMMARY: Found {len(documents_found)} documents")
    for idx, doc in enumerate(documents_found):
        print(f"  {idx + 1}. {doc.get('title', 'Untitled')} (pages {doc.get('pages', 'N/A')})")
    print("=" * 60 + "\n")
    events_received.append(('discovery:completed', data))

# Catch-all event handler for debugging
@sio.on('*')
async def catch_all(event, *args):
    if not event.startswith('discovery:'):
        return
    print(f"🔍 Unknown Event '{event}' at {datetime.now()}")
    print(f"   Args: {args}")

async def main():
    """Main function to connect and monitor WebSocket events"""
    server_url = 'http://localhost:8000'
    
    if len(sys.argv) > 1:
        server_url = sys.argv[1]
    
    print(f"Connecting to WebSocket server at {server_url}...")
    
    try:
        await sio.connect(server_url, 
                          namespaces=['/'],
                          socketio_path='/ws/socket.io')
        
        print("Press Ctrl+C to stop monitoring...")
        
        # Keep the connection alive
        await sio.wait()
        
    except KeyboardInterrupt:
        print("\n\nStopping monitor...")
        await sio.disconnect()
        
        # Print summary
        print(f"\n📊 Event Summary:")
        print(f"   Total Events: {len(events_received)}")
        print(f"   Documents Found: {len(documents_found)}")
        
        # Count event types
        event_counts = {}
        for event_type, _ in events_received:
            event_counts[event_type] = event_counts.get(event_type, 0) + 1
        
        print("\n   Event Types:")
        for event_type, count in sorted(event_counts.items()):
            print(f"     {event_type}: {count}")
        
        # Save events to file for analysis
        with open('discovery_events_log.json', 'w') as f:
            json.dump({
                'events': events_received,
                'documents_found': documents_found,
                'summary': {
                    'total_events': len(events_received),
                    'total_documents': len(documents_found),
                    'event_counts': event_counts
                }
            }, f, indent=2, default=str)
        print(f"\n💾 Events saved to discovery_events_log.json")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        await sio.disconnect()

if __name__ == '__main__':
    asyncio.run(main())
#!/usr/bin/env python3
"""
Test script for discovery processing with multi-document PDF.
Tests document splitting, fact extraction, and WebSocket events.
"""

import asyncio
import base64
import json
import aiohttp
import socketio
from datetime import datetime
import sys

# Configuration
API_BASE_URL = "http://localhost:8000"
WEBSOCKET_URL = "http://localhost:8000"
PDF_PATH = "/tmp/tesdoc_Redacted.pdf"

# WebSocket event tracking
events_received = []

# Create Socket.IO client
sio = socketio.AsyncClient()

@sio.event
async def connect():
    print("✅ WebSocket connected")

@sio.event
async def disconnect():
    print("❌ WebSocket disconnected")

# Discovery event handlers
@sio.on('discovery:started')
async def on_discovery_started(data):
    print(f"📋 Discovery started: {json.dumps(data, indent=2)}")
    events_received.append(('discovery:started', data))

@sio.on('discovery:document_found')
async def on_document_found(data):
    print(f"📄 Document found: {data.get('title', 'Unknown')} (Pages: {data.get('pages', 'Unknown')})")
    events_received.append(('discovery:document_found', data))

@sio.on('discovery:chunking')
async def on_chunking(data):
    print(f"🔄 Chunking document: {data.get('document_id', 'Unknown')}")
    events_received.append(('discovery:chunking', data))

@sio.on('discovery:embedding')
async def on_embedding(data):
    print(f"🧮 Generating embeddings: {data.get('total_chunks', 0)} chunks")
    events_received.append(('discovery:embedding', data))

@sio.on('discovery:fact_extracted')
async def on_fact_extracted(data):
    fact = data.get('fact', {})
    print(f"💡 Fact extracted: {fact.get('text', 'Unknown')[:100]}...")
    events_received.append(('discovery:fact_extracted', data))

@sio.on('discovery:completed')
async def on_completed(data):
    print(f"✅ Discovery completed!")
    print(f"   - Total documents found: {data.get('total_documents_found', 0)}")
    print(f"   - Documents processed: {data.get('documents_processed', 0)}")
    print(f"   - Facts extracted: {data.get('facts_extracted', 0)}")
    events_received.append(('discovery:completed', data))

@sio.on('discovery:error')
async def on_error(data):
    print(f"❌ Error: {data.get('error', 'Unknown error')}")
    events_received.append(('discovery:error', data))

async def test_discovery_processing():
    """Test the discovery processing endpoint with a multi-document PDF."""
    
    print("=" * 80)
    print("DISCOVERY PROCESSING TEST")
    print("=" * 80)
    print(f"PDF File: {PDF_PATH}")
    print(f"API URL: {API_BASE_URL}")
    print("=" * 80)
    
    # Connect to WebSocket
    print("\n1. Connecting to WebSocket...")
    try:
        await sio.connect(WEBSOCKET_URL)
        await asyncio.sleep(1)  # Give connection time to establish
    except Exception as e:
        print(f"❌ WebSocket connection failed: {e}")
        return
    
    # Read the PDF file
    print("\n2. Reading PDF file...")
    try:
        with open(PDF_PATH, 'rb') as f:
            pdf_content = f.read()
        print(f"   ✅ PDF loaded: {len(pdf_content):,} bytes")
    except Exception as e:
        print(f"❌ Failed to read PDF: {e}")
        return
    
    # Prepare the request
    print("\n3. Preparing request...")
    
    # First, let's try with JSON format (base64 encoded)
    request_data = {
        "discovery_files": [{
            "filename": "tesdoc_Redacted.pdf",
            "content": base64.b64encode(pdf_content).decode('utf-8')
        }],
        "production_batch": "TestBatch001",
        "producing_party": "Opposing Counsel - Test",
        "production_date": datetime.now().isoformat(),
        "responsive_to_requests": ["RFP No. 1-10"],
        "confidentiality_designation": "Confidential",
        "enable_fact_extraction": True
    }
    
    # Add mock case context headers for MVP mode
    headers = {
        "Content-Type": "application/json",
        "X-Case-ID": "test-case-001",
        "X-Case-Name": "Test_Discovery_Case",
        "X-User-ID": "test-user-001"
    }
    
    print("   ✅ Request prepared")
    print(f"   - File size: {len(pdf_content):,} bytes")
    print(f"   - Base64 size: {len(request_data['discovery_files'][0]['content']):,} chars")
    
    # Send the request
    print("\n4. Sending discovery processing request...")
    start_time = asyncio.get_event_loop().time()
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(
                f"{API_BASE_URL}/api/discovery/process",
                json=request_data,
                headers=headers
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"   ✅ Request successful!")
                    print(f"   - Processing ID: {result.get('processing_id', 'Unknown')}")
                    print(f"   - Status: {result.get('status', 'Unknown')}")
                    processing_id = result.get('processing_id')
                else:
                    error_text = await response.text()
                    print(f"   ❌ Request failed: {response.status}")
                    print(f"   Error: {error_text}")
                    return
        except Exception as e:
            print(f"   ❌ Request error: {e}")
            return
    
    # Wait for processing to complete
    print("\n5. Monitoring processing (waiting up to 2 minutes)...")
    
    # Wait for completion or timeout
    timeout = 120  # 2 minutes
    check_interval = 2
    elapsed = 0
    completed = False
    
    while elapsed < timeout:
        # Check if we received completion event
        completion_events = [e for e in events_received if e[0] == 'discovery:completed']
        if completion_events:
            completed = True
            break
            
        # Also check for errors
        error_events = [e for e in events_received if e[0] == 'discovery:error']
        if error_events:
            print("   ❌ Processing failed with errors")
            break
            
        await asyncio.sleep(check_interval)
        elapsed += check_interval
        
        # Show progress
        if elapsed % 10 == 0:
            doc_events = [e for e in events_received if e[0] == 'discovery:document_found']
            fact_events = [e for e in events_received if e[0] == 'discovery:fact_extracted']
            print(f"   ... {elapsed}s elapsed - Documents: {len(doc_events)}, Facts: {len(fact_events)}")
    
    processing_time = asyncio.get_event_loop().time() - start_time
    
    # Summary
    print("\n" + "=" * 80)
    print("PROCESSING SUMMARY")
    print("=" * 80)
    print(f"Processing time: {processing_time:.2f} seconds")
    print(f"Completed: {'Yes' if completed else 'No (timeout)'}")
    
    # Event summary
    event_types = {}
    for event_type, data in events_received:
        event_types[event_type] = event_types.get(event_type, 0) + 1
    
    print("\nEvents received:")
    for event_type, count in event_types.items():
        print(f"  - {event_type}: {count}")
    
    # Document analysis
    doc_events = [e[1] for e in events_received if e[0] == 'discovery:document_found']
    if doc_events:
        print(f"\nDocuments found: {len(doc_events)}")
        for i, doc in enumerate(doc_events, 1):
            print(f"  {i}. {doc.get('title', 'Unknown')} ({doc.get('type', 'Unknown')})")
            print(f"     Pages: {doc.get('pages', 'Unknown')}")
            print(f"     Bates: {doc.get('bates_range', 'Unknown')}")
            print(f"     Confidence: {doc.get('confidence', 0):.2f}")
    
    # Fact analysis
    fact_events = [e[1] for e in events_received if e[0] == 'discovery:fact_extracted']
    if fact_events:
        print(f"\nFacts extracted: {len(fact_events)}")
        
        # Group by category
        categories = {}
        for event in fact_events:
            fact = event.get('fact', {})
            category = fact.get('category', 'Unknown')
            categories[category] = categories.get(category, 0) + 1
        
        print("By category:")
        for category, count in categories.items():
            print(f"  - {category}: {count}")
    
    # Check processing status via API
    if processing_id:
        print(f"\n6. Checking final status via API...")
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    f"{API_BASE_URL}/api/discovery/status/{processing_id}",
                    headers=headers
                ) as response:
                    if response.status == 200:
                        status = await response.json()
                        print(f"   ✅ Final status retrieved:")
                        print(f"   - Status: {status.get('status', 'Unknown')}")
                        print(f"   - Total documents: {status.get('total_documents', 0)}")
                        print(f"   - Processed documents: {status.get('processed_documents', 0)}")
                        print(f"   - Total facts: {status.get('total_facts', 0)}")
                    else:
                        print(f"   ❌ Status check failed: {response.status}")
            except Exception as e:
                print(f"   ❌ Status check error: {e}")
    
    # Disconnect WebSocket
    await sio.disconnect()
    
    print("\n" + "=" * 80)
    print("TEST COMPLETED")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_discovery_processing())
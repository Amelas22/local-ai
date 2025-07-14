#!/usr/bin/env python3
"""
Simple test script for discovery processing without WebSocket monitoring.
"""

import asyncio
import base64
import json
import aiohttp
from datetime import datetime
import time

# Configuration
API_BASE_URL = "http://localhost:8000"
PDF_PATH = "/tmp/tesdoc_Redacted.pdf"

async def test_discovery_processing():
    """Test the discovery processing endpoint."""
    
    print("=" * 80)
    print("DISCOVERY PROCESSING TEST (Simple)")
    print("=" * 80)
    print(f"PDF File: {PDF_PATH}")
    print(f"API URL: {API_BASE_URL}")
    print("=" * 80)
    
    # Read the PDF file
    print("\n1. Reading PDF file...")
    try:
        with open(PDF_PATH, 'rb') as f:
            pdf_content = f.read()
        print(f"   ✅ PDF loaded: {len(pdf_content):,} bytes")
    except Exception as e:
        print(f"❌ Failed to read PDF: {e}")
        return
    
    # Prepare the request
    print("\n2. Preparing request...")
    
    # JSON format with base64 encoded PDF
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
    print("\n3. Sending discovery processing request...")
    start_time = time.time()
    
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
                    print(f"   - Message: {result.get('message', 'Unknown')}")
                    processing_id = result.get('processing_id')
                else:
                    error_text = await response.text()
                    print(f"   ❌ Request failed: {response.status}")
                    print(f"   Error: {error_text}")
                    return None
        except Exception as e:
            print(f"   ❌ Request error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    # Poll for status
    print("\n4. Polling for processing status...")
    
    if processing_id:
        completed = False
        for i in range(60):  # Poll for up to 2 minutes
            await asyncio.sleep(2)
            
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(
                        f"{API_BASE_URL}/api/discovery/status/{processing_id}",
                        headers=headers
                    ) as response:
                        if response.status == 200:
                            status = await response.json()
                            current_status = status.get('status', 'Unknown')
                            total_docs = status.get('total_documents', 0)
                            processed_docs = status.get('processed_documents', 0)
                            total_facts = status.get('total_facts', 0)
                            
                            print(f"   [{i*2}s] Status: {current_status} | Docs: {processed_docs}/{total_docs} | Facts: {total_facts}")
                            
                            if current_status in ['completed', 'error']:
                                completed = True
                                if current_status == 'error':
                                    print(f"   ❌ Error: {status.get('error_message', 'Unknown error')}")
                                break
                except Exception as e:
                    print(f"   Status check error: {e}")
        
        processing_time = time.time() - start_time
        
        # Final status
        print("\n" + "=" * 80)
        print("FINAL RESULTS")
        print("=" * 80)
        print(f"Processing time: {processing_time:.2f} seconds")
        print(f"Completed: {'Yes' if completed else 'No (timeout)'}")
        
        if completed and current_status == 'completed':
            print(f"\n✅ Successfully processed:")
            print(f"   - Total documents found: {total_docs}")
            print(f"   - Documents processed: {processed_docs}")
            print(f"   - Facts extracted: {total_facts}")
    
    print("\n" + "=" * 80)
    print("TEST COMPLETED")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_discovery_processing())
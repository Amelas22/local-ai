#!/usr/bin/env python3
"""
Debug test script for discovery processing with enhanced logging
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
    """Test the discovery processing endpoint with debug info."""
    
    print("=" * 80)
    print("DISCOVERY PROCESSING DEBUG TEST")
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
    
    # Use a test case name
    case_name = "Test_Discovery_Case"
    
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
        "X-Case-Name": case_name,
        "X-User-ID": "test-user-001"
    }
    
    print("   ✅ Request prepared")
    print(f"   - Case name: {case_name}")
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
    
    # Wait a bit for processing to start
    print("\n4. Waiting for processing to start...")
    await asyncio.sleep(5)
    
    # Check logs for the processing
    print("\n5. Checking processing status...")
    
    if processing_id:
        # Poll for detailed status
        for i in range(30):  # Poll for up to 1 minute
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
                            error_msg = status.get('error_message', '')
                            
                            print(f"   [{i*2}s] Status: {current_status} | Docs: {processed_docs}/{total_docs} | Facts: {total_facts}")
                            
                            if error_msg:
                                print(f"        Error: {error_msg}")
                            
                            if current_status in ['completed', 'error']:
                                break
                except Exception as e:
                    print(f"   Status check error: {e}")
        
        processing_time = time.time() - start_time
        
        # Final status
        print("\n" + "=" * 80)
        print("DEBUG INFORMATION")
        print("=" * 80)
        print(f"Processing time: {processing_time:.2f} seconds")
        print(f"Final status: {current_status}")
        
        if current_status == 'error':
            print(f"\n❌ Processing failed with error:")
            print(f"   {error_msg}")
            print("\nCheck docker logs for more details:")
            print(f"   docker logs clerk --tail 100 | grep {processing_id}")
        elif total_docs == 0:
            print(f"\n⚠️  No documents were found in the PDF")
            print("Possible issues:")
            print("   1. Document boundary detection failed")
            print("   2. PDF format not recognized")
            print("   3. Boundary detection confidence too low")
            print("\nCheck docker logs for boundary detection details:")
            print(f"   docker logs clerk --tail 200 | grep -E '(boundary|segment|document)'")
        else:
            print(f"\n✅ Successfully processed:")
            print(f"   - Total documents found: {total_docs}")
            print(f"   - Documents processed: {processed_docs}")
            print(f"   - Facts extracted: {total_facts}")
    
    print("\n" + "=" * 80)
    print("TEST COMPLETED")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_discovery_processing())
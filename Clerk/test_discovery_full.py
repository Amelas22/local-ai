#!/usr/bin/env python
"""
Full test of discovery processing with detailed logging
"""

import asyncio
import requests
import base64
import json
import time
from datetime import datetime

def test_discovery_full():
    """Test discovery processing end-to-end"""
    
    print("🔍 Discovery Processing Full Test")
    print("=" * 60)
    
    # Read test PDF
    pdf_path = "/app/tesdoc_Redacted_ocr.pdf"
    with open(pdf_path, 'rb') as f:
        pdf_content = f.read()
    
    print(f"📄 PDF loaded: {len(pdf_content):,} bytes")
    
    # Encode to base64
    pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')
    
    # Prepare request
    request_data = {
        "discovery_files": [{
            "filename": "tesdoc_Redacted_ocr.pdf",
            "content": pdf_base64,
            "content_type": "application/pdf"
        }],
        "production_batch": "FULL_TEST_001",
        "producing_party": "Full Test Party",
        "enable_fact_extraction": False  # Disable for simpler testing
    }
    
    headers = {
        'Content-Type': 'application/json',
        'X-Case-ID': 'test_full',
        'X-Case-Name': 'Test Full'
    }
    
    print(f"\n📤 Submitting discovery request...")
    print(f"   Endpoint: http://localhost:8000/api/discovery/process")
    
    # Submit request
    start_time = time.time()
    response = requests.post(
        "http://localhost:8000/api/discovery/process",
        json=request_data,
        headers=headers
    )
    
    if response.status_code != 200:
        print(f"❌ Request failed: {response.status_code}")
        print(response.text)
        return
    
    result = response.json()
    processing_id = result.get('processing_id')
    print(f"✅ Processing started: {processing_id}")
    
    # Poll for status
    print("\n⏳ Monitoring progress...")
    last_status = None
    
    for i in range(120):  # Poll for up to 4 minutes
        time.sleep(2)
        
        status_response = requests.get(
            f"http://localhost:8000/api/discovery/status/{processing_id}",
            headers=headers
        )
        
        if status_response.status_code == 200:
            status = status_response.json()
            current_status = status.get('status')
            
            # Print updates
            if status != last_status:
                elapsed = time.time() - start_time
                print(f"\n[{elapsed:.1f}s] Status Update:")
                print(f"  Status: {current_status}")
                print(f"  Total Documents: {status.get('total_documents', 0)}")
                print(f"  Processed: {status.get('processed_documents', 0)}")
                print(f"  Facts: {status.get('total_facts', 0)}")
                
                if status.get('error_message'):
                    print(f"  Error: {status.get('error_message')}")
                
                last_status = status
            
            if current_status == 'completed' or current_status == 'error':
                break
    
    # Final summary
    elapsed = time.time() - start_time
    print(f"\n{'=' * 60}")
    print(f"FINAL RESULTS (after {elapsed:.1f}s)")
    print(f"{'=' * 60}")
    
    if status:
        print(f"Status: {status.get('status')}")
        print(f"Total Documents Found: {status.get('total_documents', 0)}")
        print(f"Documents Processed: {status.get('processed_documents', 0)}")
        print(f"Facts Extracted: {status.get('total_facts', 0)}")
        
        if status.get('processed_documents', 0) == 0:
            print("\n⚠️  WARNING: No documents were processed!")
            print("This indicates an error in the processing pipeline.")
        elif status.get('processed_documents') == status.get('total_documents'):
            print("\n✅ SUCCESS: All documents processed!")
        else:
            print(f"\n⚠️  WARNING: Only {status.get('processed_documents')} of {status.get('total_documents')} documents processed")
    
    # Check logs for errors
    print(f"\n📋 Checking container logs for errors...")
    print("Run this command to see detailed logs:")
    print(f"docker logs clerk 2>&1 | grep '{processing_id}' | grep -i error")

if __name__ == "__main__":
    test_discovery_full()
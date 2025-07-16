#!/usr/bin/env python
"""
Direct test of discovery API endpoint
"""

import requests
import base64
import json
import time

def test_discovery_api():
    """Test the discovery API directly"""
    base_url = "http://localhost:8000"
    
    # Read test PDF
    pdf_path = "/app/tesdoc_Redacted_ocr.pdf"
    with open(pdf_path, 'rb') as f:
        pdf_content = f.read()
    
    print(f"PDF size: {len(pdf_content):,} bytes")
    
    # Encode to base64
    pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')
    print(f"Base64 size: {len(pdf_base64):,} chars")
    
    # Prepare JSON request
    request_data = {
        "discovery_files": [{
            "filename": "tesdoc_Redacted_ocr.pdf",
            "content": pdf_base64,
            "content_type": "application/pdf"
        }],
        "production_batch": "API_TEST_001",
        "producing_party": "API Test",
        "enable_fact_extraction": True
    }
    
    headers = {
        'Content-Type': 'application/json',
        'X-Case-ID': 'test_case_api',
        'X-Case-Name': 'Test Case API'
    }
    
    print("\n📤 Sending discovery request...")
    print(f"   Endpoint: {base_url}/api/discovery/process")
    print(f"   Headers: {headers}")
    
    # Send request
    response = requests.post(
        f"{base_url}/api/discovery/process",
        json=request_data,
        headers=headers
    )
    
    print(f"\n📥 Response: {response.status_code}")
    print(f"   Content: {response.text}")
    
    if response.status_code == 200:
        result = response.json()
        processing_id = result.get('processing_id')
        print(f"\n✅ Processing started: {processing_id}")
        
        # Poll for status
        print("\n⏳ Polling for status...")
        for i in range(30):
            time.sleep(2)
            status_response = requests.get(
                f"{base_url}/api/discovery/status/{processing_id}",
                headers=headers
            )
            
            if status_response.status_code == 200:
                status = status_response.json()
                print(f"   Status: {status.get('status')} - Docs: {status.get('total_documents')} - Facts: {status.get('total_facts')}")
                
                if status.get('status') == 'completed':
                    print("\n✅ Processing completed!")
                    print(json.dumps(status, indent=2))
                    break
                elif status.get('status') == 'error':
                    print(f"\n❌ Processing failed: {status.get('error_message')}")
                    break
    else:
        print(f"\n❌ Request failed: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    test_discovery_api()
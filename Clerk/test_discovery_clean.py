#!/usr/bin/env python
"""
Test discovery processing with a clean case
"""

import requests
import base64
import json
import time
from datetime import datetime

def test_discovery_clean():
    """Test with a unique case name to avoid duplicates"""
    
    # Use timestamp to ensure unique case
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    case_id = f"test_clean_{timestamp}"
    case_name = f"Test Clean {timestamp}"
    
    print(f"🧹 Testing with fresh case: {case_name}")
    
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
        "production_batch": "CLEAN_TEST_001",
        "producing_party": "Clean Test Party",
        "enable_fact_extraction": False
    }
    
    headers = {
        'Content-Type': 'application/json',
        'X-Case-ID': case_id,
        'X-Case-Name': case_name
    }
    
    print("\n📤 Submitting discovery request...")
    response = requests.post(
        "http://localhost:8000/api/discovery/process",
        json=request_data,
        headers=headers
    )
    
    if response.status_code != 200:
        print(f"❌ Request failed: {response.status_code}")
        return
    
    result = response.json()
    processing_id = result.get('processing_id')
    print(f"✅ Processing started: {processing_id}")
    
    # Poll for status
    print("\n⏳ Monitoring progress...")
    for i in range(60):  # 2 minutes max
        time.sleep(2)
        
        status_response = requests.get(
            f"http://localhost:8000/api/discovery/status/{processing_id}",
            headers=headers
        )
        
        if status_response.status_code == 200:
            status = status_response.json()
            
            if i % 5 == 0:  # Print every 10 seconds
                print(f"   Status: {status.get('status')} - Docs: {status.get('total_documents')} - Processed: {status.get('processed_documents')}")
            
            if status.get('status') in ['completed', 'error']:
                print(f"\n📊 Final Status:")
                print(json.dumps(status, indent=2))
                
                if status.get('processed_documents', 0) > 0:
                    print(f"\n✅ SUCCESS! Processed {status.get('processed_documents')} documents")
                else:
                    print(f"\n❌ FAILED! No documents were processed")
                break

if __name__ == "__main__":
    test_discovery_clean()
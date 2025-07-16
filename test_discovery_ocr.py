#!/usr/bin/env python3
"""
Test discovery processing with OCR'd PDF
"""

import json
import requests
import base64
import time

# Read the OCR'd PDF
pdf_path = "/tmp/tesdoc_Redacted_ocr.pdf"
with open(pdf_path, "rb") as f:
    pdf_content = f.read()

# Prepare the request
url = "http://localhost:8000/api/discovery/process"
headers = {
    "Content-Type": "application/json",
    "X-Case-ID": "test-case-001",
    "X-Case-Name": "Test_Discovery_Case"
}

data = {
    "discovery_files": [{
        "filename": "tesdoc_Redacted_ocr.pdf",
        "content": base64.b64encode(pdf_content).decode('utf-8'),
        "content_type": "application/pdf"
    }],
    "production_batch": "Test_Batch_001",
    "producing_party": "Opposing Counsel",
    "enable_fact_extraction": True
}

print("Sending discovery processing request for OCR'd PDF...")
print("=" * 80)

try:
    response = requests.post(url, json=data, headers=headers, timeout=300)
    response.raise_for_status()
    
    result = response.json()
    processing_id = result.get("processing_id")
    print(f"Processing started with ID: {processing_id}")
    
    # Check status periodically
    status_url = f"http://localhost:8000/api/discovery/status/{processing_id}"
    
    for i in range(30):  # Check for up to 5 minutes
        time.sleep(10)
        
        status_response = requests.get(status_url, headers=headers)
        if status_response.ok:
            status = status_response.json()
            print(f"\n[{i*10}s] Status: {status['status']} | Docs: {status['processed_documents']}/{status['total_documents']} | Facts: {status['total_facts']}")
            
            if status['status'] in ['completed', 'error']:
                print(f"\nFinal status: {status['status']}")
                if status['status'] == 'error':
                    print(f"Error: {status.get('error_message', 'Unknown error')}")
                else:
                    print(f"Total documents found: {status['total_documents']}")
                    print(f"Documents processed: {status['processed_documents']}")
                    print(f"Facts extracted: {status['total_facts']}")
                break
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
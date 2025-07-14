#!/usr/bin/env python3
"""
Quick verification script to test the discovery endpoint fix.
This checks that the endpoint accepts the correct request format.
"""

import requests
import json

# Test endpoint
url = "http://localhost:8000/api/discovery/process"

# Test data matching what the frontend sends
test_data = {
    "discovery_files": [],
    "box_folder_id": None,
    "rfp_file": None,
    "production_batch": "Batch001",
    "producing_party": "Opposing Counsel",
    "production_date": None,
    "responsive_to_requests": [],
    "confidentiality_designation": None,
    "enable_fact_extraction": True
}

# Headers for case context
headers = {
    "X-Case-ID": "test-case-1",
    "Content-Type": "application/json"
}

print("Testing discovery endpoint...")
print(f"URL: {url}")
print(f"Headers: {headers}")
print(f"Data: {json.dumps(test_data, indent=2)}")

try:
    response = requests.post(url, json=test_data, headers=headers)
    print(f"\nResponse status: {response.status_code}")
    
    if response.status_code == 200:
        print("✓ Success! Discovery endpoint is working correctly.")
        print(f"Response: {response.json()}")
    else:
        print("✗ Error response:")
        print(response.text)
        
except Exception as e:
    print(f"✗ Request failed: {str(e)}")

print("\nNote: Make sure the Clerk service is running with the updated code.")
"""
Test script to verify Authorization headers are being sent correctly.
Run this inside the clerk docker container:
docker exec clerk python tests/test_auth_headers.py
"""

import asyncio
import sys
import os

# Add the src directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config.settings import get_settings


async def test_auth_headers():
    """Test that API calls include proper Authorization headers."""
    settings = get_settings()

    print("=== Testing Auth Headers ===")
    print(f"Auth Enabled: {settings.auth.auth_enabled}")
    print(f"Development Mode: {settings.is_development}")
    print(f"Dev Mock Token: {settings.auth.dev_mock_token}")

    # Test direct curl command
    import subprocess

    print("\n1. Testing with curl...")
    curl_cmd = [
        "curl",
        "-s",
        "-v",
        "-H",
        f"Authorization: Bearer {settings.auth.dev_mock_token}",
        "http://localhost:8000/api/cases",
    ]

    result = subprocess.run(curl_cmd, capture_output=True, text=True)
    print(f"Response code: {'200' if 'HTTP/1.1 200' in result.stderr else 'NOT 200'}")

    if "401" in result.stderr:
        print("ERROR: Got 401 Unauthorized")
        print("Response:", result.stdout)
    else:
        print("SUCCESS: Authorization accepted")
        if result.stdout:
            import json

            try:
                data = json.loads(result.stdout)
                print(f"Found {len(data.get('cases', []))} cases")
            except:
                print("Response:", result.stdout)

    print("\n2. Testing Python requests...")
    import requests

    headers = {"Authorization": f"Bearer {settings.auth.dev_mock_token}"}

    try:
        response = requests.get("http://localhost:8000/api/cases", headers=headers)
        print(f"Response code: {response.status_code}")

        if response.status_code == 200:
            print("SUCCESS: Authorization accepted")
            data = response.json()
            print(f"Found {len(data.get('cases', []))} cases")
        else:
            print("ERROR: Got non-200 response")
            print("Response:", response.text)
    except Exception as e:
        print(f"ERROR: {e}")

    print("\n3. Testing health endpoint (no auth required)...")
    try:
        response = requests.get("http://localhost:8000/health")
        print(f"Response code: {response.status_code}")
        if response.status_code == 200:
            print("SUCCESS: Health check passed")
            print("Response:", response.json())
    except Exception as e:
        print(f"ERROR: {e}")

    print("\n=== Test Complete ===")


if __name__ == "__main__":
    asyncio.run(test_auth_headers())

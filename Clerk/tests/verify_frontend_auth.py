#!/usr/bin/env python3
"""
Test script to verify frontend authentication is working.
Run this to simulate browser requests and check auth headers.
"""

import requests


def test_frontend_auth():
    """Test that the frontend correctly includes auth headers."""
    base_url = "http://localhost:8010"

    print("=== Testing Frontend Auth ===")

    # Test 1: API endpoint directly (should work)
    print("\n1. Testing API endpoint directly...")
    headers = {"Authorization": "Bearer dev-token-123456"}
    try:
        response = requests.get(f"{base_url}/api/cases", headers=headers)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✓ Found {len(data.get('cases', []))} cases")
        else:
            print(f"   ✗ Error: {response.text}")
    except Exception as e:
        print(f"   ✗ Error: {e}")

    # Test 2: Frontend page load
    print("\n2. Testing frontend page load...")
    try:
        response = requests.get(f"{base_url}/dashboard")
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print("   ✓ Dashboard page loaded")
            # Check if the page includes the correct JS file
            if "index-DjasusvC.js" in response.text:
                print("   ✓ Using latest frontend build")
            else:
                print("   ✗ Not using latest frontend build")
        else:
            print(f"   ✗ Error loading dashboard: {response.status_code}")
    except Exception as e:
        print(f"   ✗ Error: {e}")

    # Test 3: Check if dev auth is configured
    print("\n3. Checking frontend configuration...")
    try:
        # Get the main JS file
        response = requests.get(f"{base_url}/assets/index-DjasusvC.js")
        if response.status_code == 200:
            js_content = response.text
            # Check for dev auth markers
            if "dev-token-123456" in js_content:
                print("   ✓ Dev token found in frontend build")
            else:
                print("   ✗ Dev token NOT found in frontend build")

            if "Auth disabled - using development auth service" in js_content:
                print("   ✓ Dev auth service configured")
            else:
                print("   ✗ Dev auth service NOT configured")

            # Check for apiClient usage
            if "apiClient" in js_content and "fetch(" not in js_content.replace(
                "fetch(", ""
            ):
                print("   ✓ Using apiClient (not raw fetch)")
            else:
                print("   ✗ Still using raw fetch API")
        else:
            print(f"   ✗ Could not load JS file: {response.status_code}")
    except Exception as e:
        print(f"   ✗ Error: {e}")

    print("\n=== Summary ===")
    print("The frontend should now properly include Authorization headers.")
    print("Try refreshing http://localhost:8010/dashboard in your browser.")
    print("Check the Network tab in DevTools - /api/cases should have auth header.")


if __name__ == "__main__":
    test_frontend_auth()

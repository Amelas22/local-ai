#!/bin/bash
# Test script to verify frontend auth configuration
# Run this to check if the frontend was built with correct environment variables

echo "=== Testing Frontend Auth Configuration ==="

# Check if frontend files exist
echo "1. Checking frontend build..."
if [ -d "/srv/clerk-frontend" ]; then
    echo "✓ Frontend directory exists"
    ls -la /srv/clerk-frontend/ | head -5
else
    echo "✗ Frontend directory not found at /srv/clerk-frontend"
fi

# Check environment variables
echo -e "\n2. Checking environment variables..."
echo "AUTH_ENABLED: ${AUTH_ENABLED:-not set}"
echo "DEV_MOCK_TOKEN: ${DEV_MOCK_TOKEN:-not set}"
echo "VITE_AUTH_ENABLED: ${VITE_AUTH_ENABLED:-not set}"

# Check if the frontend JS includes the dev token
echo -e "\n3. Searching for auth configuration in built files..."
if [ -d "/srv/clerk-frontend" ]; then
    # Look for the mock token in the built files
    if grep -r "dev-token-123456" /srv/clerk-frontend/assets/ 2>/dev/null | head -3; then
        echo "✓ Found dev token in frontend build"
    else
        echo "✗ Dev token not found in frontend build"
    fi
    
    # Look for auth service references
    if grep -r "Auth disabled - using development auth service" /srv/clerk-frontend/assets/ 2>/dev/null | head -3; then
        echo "✓ Found dev auth service reference"
    else
        echo "✗ Dev auth service reference not found"
    fi
fi

# Test API endpoint from inside container
echo -e "\n4. Testing API endpoint..."
curl -s -w "\nHTTP Status: %{http_code}\n" \
     -H "Authorization: Bearer dev-token-123456" \
     http://localhost:8000/api/cases | head -10

echo -e "\n=== Test Complete ==="
#!/bin/bash
# Test WebSocket connection through Caddy

echo "Testing WebSocket connection through Caddy..."
echo "==========================================="

# Test 1: Check if Caddy is running
echo -e "\n1. Checking if Caddy is accessible:"
curl -s -o /dev/null -w "%{http_code}" http://localhost:8010 && echo "✓ Caddy is responding" || echo "✗ Caddy not accessible"

# Test 2: Check API through Caddy
echo -e "\n2. Checking API through Caddy:"
curl -s http://localhost:8010/api/health | jq . 2>/dev/null || echo "✗ API not accessible through Caddy"

# Test 3: Check direct backend
echo -e "\n3. Checking direct backend:"
curl -s http://localhost:8000/health | jq . 2>/dev/null || echo "✗ Backend not accessible directly"

# Test 4: Check WebSocket endpoint
echo -e "\n4. Testing WebSocket upgrade:"
curl -v -H "Upgrade: websocket" \
     -H "Connection: Upgrade" \
     -H "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==" \
     -H "Sec-WebSocket-Version: 13" \
     http://localhost:8010/ws/socket.io/ 2>&1 | grep -E "(< HTTP|< Upgrade:|< Connection:)" || echo "✗ WebSocket upgrade failed"

echo -e "\n5. Docker container status:"
docker ps | grep -E "(caddy|clerk)" || echo "✗ Containers not running"

echo -e "\n6. Caddy logs (last 10 lines):"
docker logs caddy 2>&1 | tail -10

echo -e "\n7. Clerk logs (last 10 lines):"
docker logs clerk 2>&1 | tail -10
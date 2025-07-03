#!/usr/bin/env python3
"""
Comprehensive WebSocket diagnostics for Clerk system
Tests multiple connection scenarios to identify the issue
"""
import asyncio
import aiohttp
import socketio
import logging
import json
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class WebSocketDiagnostic:
    def __init__(self):
        self.results = []
        
    async def test_http_endpoints(self):
        """Test basic HTTP endpoints first"""
        logger.info("=== Testing HTTP Endpoints ===")
        
        endpoints = [
            ("http://localhost:8000/", "Backend direct"),
            ("http://localhost:8000/health", "Backend health"),
            ("http://localhost:8000/websocket/status", "WebSocket status"),
            ("http://localhost:8010/api/", "Frontend proxy to backend"),
            ("http://localhost:8010/api/health", "Frontend proxy health"),
            ("http://localhost:8010/api/websocket/status", "Frontend proxy WebSocket status"),
        ]
        
        async with aiohttp.ClientSession() as session:
            for url, description in endpoints:
                try:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                        status = response.status
                        text = await response.text()
                        self.results.append({
                            "test": f"HTTP GET {description}",
                            "url": url,
                            "status": "✅ Success",
                            "details": f"Status: {status}, Response length: {len(text)} chars"
                        })
                        
                        # Try to parse JSON response
                        try:
                            data = json.loads(text)
                            logger.info(f"  Response: {json.dumps(data, indent=2)}")
                        except:
                            logger.info(f"  Response (first 200 chars): {text[:200]}")
                            
                except Exception as e:
                    self.results.append({
                        "test": f"HTTP GET {description}",
                        "url": url,
                        "status": "❌ Failed",
                        "details": str(e)
                    })
    
    async def test_websocket_raw(self):
        """Test raw WebSocket connections"""
        logger.info("\n=== Testing Raw WebSocket Connections ===")
        
        ws_urls = [
            ("ws://localhost:8000/ws/socket.io/", "Backend direct WebSocket"),
            ("ws://localhost:8010/ws/socket.io/", "Frontend proxy WebSocket"),
        ]
        
        for url, description in ws_urls:
            try:
                session = aiohttp.ClientSession()
                ws = await session.ws_connect(
                    url,
                    headers={
                        'Upgrade': 'websocket',
                        'Connection': 'Upgrade',
                        'Sec-WebSocket-Version': '13',
                        'Sec-WebSocket-Key': 'dGhlIHNhbXBsZSBub25jZQ=='
                    },
                    timeout=aiohttp.ClientTimeout(total=5)
                )
                
                self.results.append({
                    "test": f"Raw WebSocket {description}",
                    "url": url,
                    "status": "✅ Connected",
                    "details": "WebSocket connection established"
                })
                
                await ws.close()
                await session.close()
                
            except Exception as e:
                self.results.append({
                    "test": f"Raw WebSocket {description}",
                    "url": url,
                    "status": "❌ Failed",
                    "details": str(e)
                })
    
    async def test_socketio_connection(self):
        """Test Socket.IO connections with different configurations"""
        logger.info("\n=== Testing Socket.IO Connections ===")
        
        configs = [
            {
                "url": "http://localhost:8000",
                "path": "/ws/socket.io/",
                "description": "Backend direct Socket.IO"
            },
            {
                "url": "http://localhost:8010",
                "path": "/ws/socket.io/",
                "description": "Frontend proxy Socket.IO"
            },
            {
                "url": "ws://localhost:8000",
                "path": "/ws/socket.io/",
                "description": "Backend WebSocket protocol"
            },
            {
                "url": "ws://localhost:8010",
                "path": "/ws/socket.io/",
                "description": "Frontend proxy WebSocket protocol"
            }
        ]
        
        for config in configs:
            sio = socketio.AsyncClient(logger=False, engineio_logger=False)
            connected = False
            error_msg = None
            
            @sio.event
            async def connect():
                nonlocal connected
                connected = True
                logger.info(f"  ✅ Connected to {config['description']}")
            
            @sio.event
            async def connect_error(data):
                nonlocal error_msg
                error_msg = str(data)
                logger.error(f"  ❌ Connection error: {data}")
            
            @sio.event
            async def connected(data):
                logger.info(f"  📨 Received 'connected' event: {data}")
            
            try:
                logger.info(f"Attempting {config['description']}...")
                await sio.connect(
                    config['url'],
                    socketio_path=config['path'],
                    transports=['websocket', 'polling'],
                    wait_timeout=5
                )
                
                # Wait for connection
                await asyncio.sleep(2)
                
                if connected:
                    # Try to emit a ping
                    await sio.emit('ping')
                    await asyncio.sleep(1)
                    
                    self.results.append({
                        "test": f"Socket.IO {config['description']}",
                        "url": f"{config['url']}{config['path']}",
                        "status": "✅ Success",
                        "details": "Connected and communicated successfully"
                    })
                else:
                    self.results.append({
                        "test": f"Socket.IO {config['description']}",
                        "url": f"{config['url']}{config['path']}",
                        "status": "⚠️ Partial",
                        "details": "Connection attempt made but no confirmation received"
                    })
                
                await sio.disconnect()
                
            except Exception as e:
                self.results.append({
                    "test": f"Socket.IO {config['description']}",
                    "url": f"{config['url']}{config['path']}",
                    "status": "❌ Failed",
                    "details": f"{str(e)} {error_msg or ''}"
                })
    
    async def test_cors_headers(self):
        """Test CORS headers on the endpoints"""
        logger.info("\n=== Testing CORS Headers ===")
        
        urls = [
            "http://localhost:8000/",
            "http://localhost:8010/api/"
        ]
        
        headers = {
            'Origin': 'http://localhost:8010',
            'Access-Control-Request-Method': 'GET',
            'Access-Control-Request-Headers': 'content-type'
        }
        
        async with aiohttp.ClientSession() as session:
            for url in urls:
                try:
                    # OPTIONS request for CORS preflight
                    async with session.options(url, headers=headers) as response:
                        cors_headers = {
                            'Access-Control-Allow-Origin': response.headers.get('Access-Control-Allow-Origin', 'Not set'),
                            'Access-Control-Allow-Methods': response.headers.get('Access-Control-Allow-Methods', 'Not set'),
                            'Access-Control-Allow-Headers': response.headers.get('Access-Control-Allow-Headers', 'Not set'),
                            'Access-Control-Allow-Credentials': response.headers.get('Access-Control-Allow-Credentials', 'Not set')
                        }
                        
                        self.results.append({
                            "test": f"CORS Headers {url}",
                            "url": url,
                            "status": "ℹ️ Info",
                            "details": json.dumps(cors_headers, indent=2)
                        })
                        
                except Exception as e:
                    self.results.append({
                        "test": f"CORS Headers {url}",
                        "url": url,
                        "status": "❌ Failed",
                        "details": str(e)
                    })
    
    def print_results(self):
        """Print diagnostic results"""
        logger.info("\n" + "="*60)
        logger.info("DIAGNOSTIC RESULTS SUMMARY")
        logger.info("="*60)
        
        for result in self.results:
            logger.info(f"\n{result['status']} {result['test']}")
            logger.info(f"   URL: {result['url']}")
            logger.info(f"   Details: {result['details']}")
        
        # Provide recommendations
        logger.info("\n" + "="*60)
        logger.info("RECOMMENDATIONS")
        logger.info("="*60)
        
        failed_tests = [r for r in self.results if "❌" in r['status']]
        
        if not failed_tests:
            logger.info("✅ All tests passed! WebSocket connections should be working.")
        else:
            logger.info("Issues detected:")
            
            # Check specific failure patterns
            if any("8000" in r['url'] and "❌" in r['status'] for r in self.results):
                logger.info("• Backend service (port 8000) appears to be down or not accessible")
                logger.info("  → Check if the Clerk Docker container is running: docker ps | grep clerk")
                logger.info("  → Check Docker logs: docker logs clerk")
                
            if any("8010" in r['url'] and "❌" in r['status'] for r in self.results):
                logger.info("• Frontend proxy (port 8010) appears to be down or misconfigured")
                logger.info("  → Check if Caddy is running: docker ps | grep caddy")
                logger.info("  → Check Caddy logs: docker logs caddy")
                
            if any("WebSocket" in r['test'] and "❌" in r['status'] for r in self.results):
                logger.info("• WebSocket specific issues detected")
                logger.info("  → Verify Socket.IO server is properly mounted in main.py")
                logger.info("  → Check if firewall is blocking WebSocket connections")
                logger.info("  → Ensure Caddy WebSocket proxy configuration is correct")

async def main():
    diagnostic = WebSocketDiagnostic()
    
    # Run all tests
    await diagnostic.test_http_endpoints()
    await diagnostic.test_websocket_raw()
    await diagnostic.test_socketio_connection()
    await diagnostic.test_cors_headers()
    
    # Print results
    diagnostic.print_results()

if __name__ == "__main__":
    asyncio.run(main())
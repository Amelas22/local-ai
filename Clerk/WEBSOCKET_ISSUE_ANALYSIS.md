# WebSocket Discovery Issue Analysis

## Root Cause Analysis

After analyzing the logs and code, the actual issues are:

### 1. **Frontend minification removed debug logging**
The production build minified the code, so the `onAny` debug logging we added isn't present.

### 2. **Connection instability**
The frontend shows repeated "ping timeout" errors and reconnections, suggesting:
- The frontend is connecting through a proxy (port 8010) in development
- There may be a proxy/nginx configuration issue in Docker
- The WebSocket upgrade headers might not be properly forwarded

### 3. **Room management not working**
The backend logs show `emitting event "discovery:started" to case_debug2_071625_bd534072 [/]` - the `[/]` indicates it's emitting to the root namespace, not to a specific room.

### 4. **The real fix needed**

The python-socketio room management requires a different approach. Here's what's actually needed:

```python
# In socket_server.py, the room join should be:
@sio.event
async def subscribe_case(sid, data):
    case_id = data.get("case_id")
    if case_id:
        room_name = f"case_{case_id}"
        # This is the correct way to join a room in python-socketio
        sio.enter_room(sid, room_name, namespace='/')
        await sio.emit("subscribed", {"case_id": case_id}, room=sid)

# And emission should be:
await sio.emit("discovery:started", event_data, room=room, namespace='/')
```

### 5. **Frontend connection URL issue**
The frontend connects to `http://localhost:8010` but in Docker it should connect to the backend directly. This needs an environment variable fix:

```javascript
// In WebSocketContext.tsx
const baseUrl = wsUrl || import.meta.env.VITE_WS_URL || '';
const url = baseUrl || window.location.origin;
```

## Solution Steps

1. **Fix the backend room management**:
   - Use proper namespace parameter in room operations
   - Ensure rooms are created in the default namespace

2. **Fix the frontend connection**:
   - Set proper VITE_WS_URL in Docker build
   - Or use relative URLs that work in both dev and prod

3. **Fix the proxy configuration**:
   - Ensure WebSocket upgrade headers are forwarded
   - Check nginx/proxy timeout settings

4. **Add proper error handling**:
   - Implement reconnection backoff
   - Add connection state management

## Testing

Use the test HTML file to verify:
1. WebSocket connects properly
2. Room subscription works
3. Events are received by subscribed clients only
4. No reconnection loops occur
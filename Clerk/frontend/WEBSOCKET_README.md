# WebSocket Implementation Guide

This document describes the React 19 WebSocket implementation for the Clerk Legal AI System.

## Overview

The WebSocket implementation provides real-time updates for:
- Discovery document processing
- Motion drafting progress
- Case-based isolation
- Connection status monitoring

## Architecture

### 1. WebSocket Context (`src/context/WebSocketContext.tsx`)
- Manages Socket.IO connection lifecycle
- Handles reconnection with exponential backoff
- Provides connection state to all components
- Automatically connects on mount

### 2. Case Context (`src/context/CaseContext.tsx`)
- Manages active case selection
- Fetches available cases from API
- Integrates with WebSocket for case subscriptions
- Persists active case in localStorage

### 3. useWebSocket Hook (`src/hooks/useWebSocket.ts`)
- Provides typed event handling
- Automatic cleanup on unmount
- Case-based subscriptions
- Type-safe emit and on methods

## Configuration

### Environment Variables

```bash
# WebSocket URL (use http/https, Socket.IO handles upgrade)
VITE_WS_URL=http://localhost:8000

# API URL for REST endpoints
VITE_API_URL=http://localhost:8000
```

### Backend Configuration

The backend WebSocket path must match the frontend configuration:
```python
# src/websocket/socket_server.py
socket_app = socketio.ASGIApp(
    sio,
    socketio_path='/ws/socket.io'  # Must match frontend path
)
```

## Usage

### Basic WebSocket Connection

```typescript
import { useWebSocket } from '@/hooks/useWebSocket';

function MyComponent() {
  const { connected, error, on, emit } = useWebSocket();
  
  useEffect(() => {
    // Listen for discovery events
    const unsubscribe = on('discovery:started', (data) => {
      console.log('Discovery started:', data);
    });
    
    // Cleanup on unmount
    return unsubscribe;
  }, [on]);
  
  return <div>Connected: {connected}</div>;
}
```

### Case-Based Connection

```typescript
import { useCaseSelection } from '@/hooks/useCaseSelection';

function CaseAwareComponent() {
  const { activeCase, switchCase, cases } = useCaseSelection();
  const { on, subscribedCase } = useWebSocket(activeCase);
  
  // WebSocket automatically subscribes to active case
  
  return (
    <Select value={activeCase} onChange={(e) => switchCase(e.target.value)}>
      {cases.map(c => (
        <MenuItem key={c.case_name} value={c.case_name}>
          {c.display_name}
        </MenuItem>
      ))}
    </Select>
  );
}
```

### Real-time Components

#### Connection Status
```typescript
import { ConnectionStatus } from '@/components/realtime/ConnectionStatus';

// Shows connection state with visual indicators
<ConnectionStatus />
```

#### Discovery Progress
```typescript
import { DiscoveryProgress } from '@/components/realtime/DiscoveryProgress';

// Shows real-time discovery processing updates
<DiscoveryProgress caseId={activeCase} />
```

#### Motion Progress
```typescript
import { MotionProgress } from '@/components/realtime/MotionProgress';

// Shows motion drafting progress
<MotionProgress caseId={activeCase} motionId={motionId} />
```

## WebSocket Events

### Connection Events
- `connect` - WebSocket connected
- `disconnect` - WebSocket disconnected
- `connect_error` - Connection error occurred
- `connected` - Server acknowledgment

### Case Events
- `subscribe_case` - Subscribe to case updates
- `unsubscribe_case` - Unsubscribe from case
- `subscribed` - Subscription confirmed

### Discovery Events
- `discovery:started` - Processing started
- `discovery:document_found` - Document discovered
- `discovery:chunking` - Document chunking progress
- `discovery:embedding` - Embedding generation progress
- `discovery:stored` - Vectors stored
- `discovery:completed` - Processing completed
- `discovery:error` - Processing error

### Motion Events
- `motion:started` - Motion drafting started
- `motion:outline_started` - Outline generation started
- `motion:outline_completed` - Outline completed
- `motion:section_completed` - Section completed
- `motion:completed` - Motion completed
- `motion:error` - Motion error

## Testing

### Unit Tests
```bash
# Run all tests
npm test

# Run WebSocket tests
npm test useWebSocket
npm test ConnectionStatus
```

### Manual Testing
1. Start backend: `cd Clerk && python main.py`
2. Start frontend: `cd Clerk/frontend && npm run dev`
3. Open browser DevTools > Network > WS tab
4. Verify WebSocket connection to `/ws/socket.io/`
5. Test case switching and real-time updates

## Troubleshooting

### Connection Issues
1. Check backend is running with Uvicorn (not Gunicorn)
2. Verify WebSocket path matches: `/ws/socket.io/`
3. Check browser console for connection errors
4. Ensure CORS is configured correctly

### Event Issues
1. Verify case subscription before expecting events
2. Check event names match backend exactly
3. Use browser DevTools to monitor WebSocket frames
4. Check Redux DevTools for state updates

### Development Tips
- Use `VITE_DEBUG_WEBSOCKET=true` for verbose logging
- Monitor WebSocket frames in browser DevTools
- Test reconnection by stopping/starting backend
- Use mock events for frontend development

## Migration from Old Implementation

The new implementation replaces:
- `socketClient.ts` - Now handled by WebSocketContext
- Manual reconnection - Now automatic with exponential backoff
- Complex URL logic - Simplified environment-based configuration
- Redux-only state - Now uses React Context for connection state
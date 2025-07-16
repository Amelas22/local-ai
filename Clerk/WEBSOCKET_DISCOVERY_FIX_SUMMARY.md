# WebSocket Discovery Processing Fix Summary

## Issues Identified

1. **Backend was emitting to all clients instead of case-specific rooms**
   - Events were broadcast globally without room filtering
   - No room management for case subscriptions

2. **Frontend had a render loop causing rapid subscribe/unsubscribe cycles**
   - Dependency array issues in useDiscoverySocket
   - Stale closure in WebSocketContext's attemptReconnect
   - Multiple components subscribing to the same case

3. **Missing event handler registration**
   - Discovery event handlers weren't properly attached before subscription

## Changes Made

### Backend (Python)

1. **socket_server.py**
   - Added room management in `subscribe_case` and `unsubscribe_case` handlers
   - Updated all emit functions to accept `case_id` parameter
   - Modified emit functions to use room-based emission: `room=f"case_{case_id}"`
   - Added proper room join/leave logic

2. **discovery_endpoints.py**
   - Updated all `sio.emit()` calls to include `room=f"case_{case_name}"`
   - Modified all emit function calls to pass `case_id` parameter
   - Fixed test endpoint to use room-based emission

### Frontend (React/TypeScript)

1. **WebSocketContext.tsx**
   - Fixed stale closure issue in subscribeToCase
   - Added debug logging with `socket.onAny()` to track all events
   - Improved subscription state management

2. **CaseContext.tsx**
   - Added `useCallback` to prevent unnecessary re-renders
   - Centralized case subscription management

3. **useDiscoverySocket.ts**
   - Removed event handler callbacks from dependency arrays
   - Used `handlersRef` to store stable handler references
   - Fixed event handler registration to use handlers from ref
   - Removed redundant case subscription (handled by CaseContext)

## How It Works Now

1. **Connection Flow**:
   - Client connects to WebSocket server
   - Client subscribes to a case using `subscribe_case` event
   - Server joins client to room `case_{case_id}`
   - All discovery events for that case are emitted to the room

2. **Event Flow**:
   - Backend processes discovery documents
   - Events are emitted to `case_{case_id}` room only
   - Only clients subscribed to that case receive the events
   - Frontend updates UI in real-time

## Testing

To test the fixes:

1. Rebuild the Docker container with the updated files
2. Start discovery processing from the frontend
3. Check browser console for WebSocket events
4. Verify that:
   - No rapid subscribe/unsubscribe loops occur
   - Discovery events are received and displayed
   - Facts are shown as they're extracted
   - UI updates in real-time

## Files Modified

### Backend:
- `/Clerk/src/websocket/socket_server.py`
- `/Clerk/src/api/discovery_endpoints.py`

### Frontend:
- `/Clerk/frontend/src/context/WebSocketContext.tsx`
- `/Clerk/frontend/src/context/CaseContext.tsx`
- `/Clerk/frontend/src/hooks/useDiscoverySocket.ts`

## Next Steps

1. Rebuild the Clerk Docker container to include frontend changes
2. Test the complete discovery processing flow
3. Monitor for any remaining issues
4. Consider adding more robust error handling and reconnection logic
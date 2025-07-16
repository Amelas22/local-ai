# WebSocket Discovery Processing Fix Summary

## Problem Statement
The discovery processing feature was working correctly on the backend but the frontend was not receiving real-time WebSocket events. The UI remained stuck and timed out after 30 seconds.

## Root Causes Identified

### 1. **Event Property Name Mismatch** (PRIMARY ISSUE)
- Backend was emitting events with camelCase properties (e.g., `processingId`, `documentId`)
- Frontend expected snake_case properties (e.g., `processing_id`, `document_id`)
- This caused the frontend to ignore all incoming events

### 2. **Rapid Subscribe/Unsubscribe Loop**
- Frontend was constantly subscribing and unsubscribing from WebSocket events
- This was caused by React useEffect dependencies triggering re-renders
- Could cause events to be missed during unsubscribed periods

### 3. **Processing ID Validation Issues**
- Frontend was filtering events by processing_id
- Events might arrive before the frontend had the processing_id available

## Fixes Implemented

### 1. Fixed Event Property Naming in `socket_server.py`
Changed all event emitters from camelCase to snake_case:
```python
# Before
event_data = {
    "processingId": processing_id,
    "documentId": document_id,
    "pageCount": page_count
}

# After
event_data = {
    "processing_id": processing_id,
    "document_id": document_id,
    "page_count": page_count
}
```

### 2. Fixed Rapid Re-subscription in `useEnhancedDiscoverySocket.ts`
- Added debouncing with timeout to prevent rapid subscription attempts
- Stored last subscribed case/processing ID to prevent redundant subscriptions
- Simplified useEffect dependencies to prevent circular updates
- Used refs to store event handlers to prevent recreation

```typescript
// Added subscription state tracking
const subscriptionTimeoutRef = useRef<NodeJS.Timeout | null>(null);
const lastSubscribedCaseRef = useRef<string | null>(null);
const lastProcessingIdRef = useRef<string | null>(null);

// Debounced subscription
subscriptionTimeoutRef.current = setTimeout(() => {
    // Subscribe logic
}, 100);
```

### 3. Added Processing ID Validation
Enhanced event handlers to check if events match the current processing session:
```typescript
const handleDocumentFound = useCallback((data: any) => {
    if (processingId && data.processing_id !== processingId) {
        console.log('Ignoring event for different processing_id');
        return;
    }
    // Process the event
}, [dispatch, processingId]);
```

### 4. Enhanced Logging Throughout
Added comprehensive logging with emojis for better tracking:
- Backend: Added processing_id tracking in all log messages
- Frontend: Added event reception logging with `socket.onAny()`
- All event emissions now log the full event data

## Verification

### WebSocket Status Check
```bash
# Direct backend check
docker exec clerk curl -X GET http://localhost:8000/websocket/status

# Result shows active connection:
{
  "status": "active",
  "connections": {
    "total": 1,
    "connections": [{
      "sid": "gXK3281jD5tz9MA3AAAG",
      "connected_at": "2025-07-15T02:19:35.077454",
      "case_id": "debug_071425_a64e60a6"
    }]
  }
}
```

## Files Modified

1. **Backend**:
   - `Clerk/src/websocket/socket_server.py` - Fixed event property naming
   - `Clerk/src/api/discovery_endpoints.py` - Added enhanced logging

2. **Frontend**:
   - `Clerk/frontend/src/hooks/useEnhancedDiscoverySocket.ts` - Fixed subscription loop and added validation

3. **Documentation**:
   - `PRPs/debug-websocket-discovery.md` - Problem Resolution Plan
   - This summary document

## Expected Behavior After Fix

1. WebSocket events are emitted with correct snake_case property names
2. Frontend receives and processes all discovery events
3. No rapid subscribe/unsubscribe loops
4. Document tabs appear as documents are discovered
5. Facts stream in real-time as they are extracted
6. WebSocket connection remains stable throughout processing

## Testing Instructions

1. Upload a discovery PDF through the frontend
2. Open browser console to see WebSocket event logs
3. Monitor for:
   - `🔵 [WebSocket] Event received: discovery:document_found`
   - `📄 [Discovery] Document Found event received`
   - UI updates (tabs appearing, progress indicators)
4. Check docker logs for backend event emissions:
   ```bash
   docker-compose -p localai logs -f clerk | grep "Discovery"
   ```

## Next Steps

1. Run full end-to-end discovery test with actual PDF
2. Monitor for any remaining issues
3. Consider implementing WebSocket rooms for more targeted event delivery
4. Add automated tests for WebSocket event flow
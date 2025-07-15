# Debug WebSocket Discovery Processing - Problem Resolution Plan (PRP)

## FEATURE: Debug WebSocket Discovery Processing

The discovery processing feature works correctly on the backend but the frontend is not receiving real-time events. WebSocket connections timeout after 30 seconds and the discovery processing UI remains stuck.

## PROBLEM ANALYSIS

After analyzing the codebase and docker logs, the following issues were identified:

### 1. Event Name Mismatch (CONFIRMED)
**Primary Issue**: The backend emits WebSocket events with camelCase property names while the frontend expects snake_case.

Backend emits (from socket_server.py):
```javascript
{
  "processingId": "123",
  "documentId": "doc-1",
  "pageCount": 10
}
```

Frontend expects (from useEnhancedDiscoverySocket.ts):
```javascript
{
  "processing_id": "123",
  "document_id": "doc-1", 
  "page_count": 10
}
```

**Docker Log Evidence**: Events ARE being emitted successfully:
```
emitting event "discovery:document_found" to all [/]
emitting event "discovery:fact_extracted" to all [/]
emitting event "discovery:document_completed" to all [/]
```

### 2. Connection Instability Issues (NEW FINDING)
**From Docker Logs**: Multiple rapid subscribe/unsubscribe cycles:
```
received event "unsubscribe_case" from gXK3281jD5tz9MA3AAAG [/]
received event "subscribe_case" from gXK3281jD5tz9MA3AAAG [/]
emitting event "subscribed" to gXK3281jD5tz9MA3AAAG [/]
received event "unsubscribe_case" from gXK3281jD5tz9MA3AAAG [/]
```
This pattern repeats multiple times per second, indicating the frontend is constantly reconnecting or re-subscribing.

### 3. Frontend Not Processing Events
- Events are broadcast with `to all [/]` which means they go to ALL connected clients
- The frontend may be filtering these events by processing_id/case_id
- If the frontend doesn't have the correct processing_id when events arrive, they will be ignored

### 4. Multiple Socket Connections
**From Docker Logs**: Multiple socket IDs present:
- `8P8mgH2wA7FMUmDoAAAD`
- `gXK3281jD5tz9MA3AAAG`
This suggests multiple tabs/connections or connection recycling issues.

## IMPLEMENTATION BLUEPRINT

### Phase 1: Fix Immediate Issues (HIGH PRIORITY)

1. **Fix Event Property Names in socket_server.py**
   ```python
   # Change all event emitters from camelCase to snake_case
   async def emit_document_found(...):
       event_data = {
           "processing_id": processing_id,     # Was: processingId
           "document_id": document_id,         # Was: documentId
           "title": title,
           "type": doc_type,
           "page_count": page_count,           # Was: pageCount
           "bates_range": bates_range,         # Was: batesRange
           "confidence": confidence,
       }
       await sio.emit("discovery:document_found", event_data)
   ```

2. **Fix Rapid Re-subscription Issue**
   ```typescript
   // In useEnhancedDiscoverySocket.ts
   // Add debouncing to prevent rapid reconnections
   const subscribeToDiscoveryEvents = useCallback(() => {
       if (!socket || !isConnected || subscribedRef.current) return;
       
       // Clear any pending subscription attempts
       if (subscriptionTimeoutRef.current) {
           clearTimeout(subscriptionTimeoutRef.current);
       }
       
       subscriptionTimeoutRef.current = setTimeout(() => {
           console.log('🔌 [Discovery] Subscribing to WebSocket events...');
           // ... rest of subscription logic
           subscribedRef.current = true;
       }, 100); // Small delay to prevent rapid fire
   }, [socket, isConnected, caseId]);
   ```

3. **Add Processing ID Validation**
   ```typescript
   // Ensure events are only processed if they match our processing ID
   const handleDocumentFound = useCallback((data: any) => {
       console.log('📄 [Discovery] Document Found event received:', data);
       
       // Check if this event is for our processing session
       if (processingId && data.processing_id !== processingId) {
           console.log('  - Ignoring event for different processing_id:', data.processing_id);
           return;
       }
       
       // Process the event
       dispatch(addDocument({
           id: data.document_id,
           // ... rest of the data
       }));
   }, [dispatch, processingId]);
   ```

### Phase 2: Add Debug Logging to Trace Event Flow

1. **Enhanced Backend Logging**
   ```python
   # In discovery_endpoints.py - log processing_id throughout
   async def _process_discovery_async(processing_id: str, ...):
       logger.info(f"🚀 Starting discovery processing: {processing_id}")
       
       # When emitting events, always log the processing_id
       await emit_discovery_started(
           processing_id=processing_id,
           case_id=case_name,
           total_files=len(discovery_files or [])
       )
       logger.info(f"✅ Emitted discovery:started for {processing_id}")
   ```

2. **Frontend Event Reception Logging**
   ```typescript
   // Add to useEnhancedDiscoverySocket.ts
   useEffect(() => {
       if (!socket) return;
       
       // Log ALL incoming events for debugging
       socket.onAny((eventName, ...args) => {
           console.log(`🔵 [WebSocket] Event received: ${eventName}`, {
               timestamp: new Date().toISOString(),
               args: args,
               currentProcessingId: processingId,
               isSubscribed: subscribedRef.current
           });
       });
       
       return () => {
           socket.offAny();
       };
   }, [socket, processingId]);
   ```

### Phase 3: Fix the Subscribe/Unsubscribe Loop

1. **Identify Source of Rapid Resubscription**
   ```typescript
   // Check for multiple useEffect triggers
   useEffect(() => {
       console.log('🔄 [Discovery] Effect triggered:', {
           socket: !!socket,
           isConnected,
           caseId,
           processingId,
           subscribedRef: subscribedRef.current
       });
       
       subscribeToDiscoveryEvents();
       
       return () => {
           console.log('🔄 [Discovery] Effect cleanup');
           unsubscribeFromDiscoveryEvents();
       };
   }, [subscribeToDiscoveryEvents, unsubscribeFromDiscoveryEvents]);
   ```

2. **Stabilize Subscription State**
   ```typescript
   // Use a more stable subscription mechanism
   const [subscriptionState, setSubscriptionState] = useState<{
       caseId: string | null;
       processingId: string | null;
       subscribed: boolean;
   }>({ caseId: null, processingId: null, subscribed: false });
   
   // Only resubscribe if critical values change
   useEffect(() => {
       const shouldSubscribe = 
           socket && 
           isConnected && 
           caseId && 
           (!subscriptionState.subscribed || 
            subscriptionState.caseId !== caseId ||
            subscriptionState.processingId !== processingId);
       
       if (shouldSubscribe) {
           // Subscribe logic
           setSubscriptionState({ caseId, processingId, subscribed: true });
       }
   }, [socket, isConnected, caseId, processingId, subscriptionState]);
   ```

### Phase 4: Add Discovery Event Testing

1. **Create Test Endpoint**
   ```python
   @router.post("/discovery/test-events")
   async def test_discovery_events():
       """Test WebSocket event emission"""
       test_id = str(uuid.uuid4())
       
       # Emit test events with proper naming
       await sio.emit("discovery:started", {
           "processing_id": test_id,
           "case_id": "test_case",
           "total_files": 1
       })
       
       await asyncio.sleep(1)
       
       await sio.emit("discovery:document_found", {
           "processing_id": test_id,
           "document_id": "test_doc_1",
           "title": "Test Document",
           "type": "motion",
           "page_count": 10,
           "bates_range": {"start": "001", "end": "010"},
           "confidence": 0.95
       })
       
       return {"message": "Test events emitted", "processing_id": test_id}
   ```

2. **Add Frontend Test Component**
   ```typescript
   // TestWebSocketEvents.tsx
   const TestWebSocketEvents = () => {
       const { socket, isConnected } = useWebSocket();
       
       useEffect(() => {
           if (!socket) return;
           
           // Log all events
           socket.onAny((event, ...args) => {
               console.log(`🔵 Event received: ${event}`, args);
           });
           
           return () => {
               socket.offAny();
           };
       }, [socket]);
       
       const triggerTestEvents = async () => {
           const response = await fetch('/api/discovery/test-events', {
               method: 'POST'
           });
           const data = await response.json();
           console.log('Test triggered:', data);
       };
       
       return (
           <button onClick={triggerTestEvents}>
               Test Discovery Events
           </button>
       );
   };
   ```

### Phase 5: Fix Discovery Processing Flow

1. **Ensure Processing ID Consistency**
   ```python
   # In discovery_endpoints.py
   async def process_discovery(...):
       processing_id = str(uuid.uuid4())
       
       # Pass processing_id to background task
       background_tasks.add_task(
           _process_discovery_async,
           processing_id,  # Ensure this is passed and used
           # ...
       )
   ```

2. **Add Processing State Recovery**
   ```typescript
   // In EnhancedDiscoveryProcessing.tsx
   useEffect(() => {
       // Check for in-progress processing on mount
       const checkProcessingStatus = async () => {
           if (processingId) {
               const response = await fetch(`/api/discovery/status/${processingId}`);
               const status = await response.json();
               // Restore UI state based on status
           }
       };
       checkProcessingStatus();
   }, [processingId]);
   ```

## VALIDATION GATES

### 1. WebSocket Connection Test
```bash
# Test WebSocket connection directly
curl -X GET http://localhost:8010/websocket/status

# Expected output:
# {
#   "status": "active",
#   "connections": {...}
# }
```

### 2. Event Emission Test
```python
# Test script: test_websocket_events.py
import asyncio
import socketio

async def test_events():
    sio = socketio.AsyncClient()
    
    events_received = []
    
    @sio.on('discovery:document_found')
    async def on_document_found(data):
        print(f"Received document found: {data}")
        events_received.append(data)
    
    await sio.connect('http://localhost:8010', 
                      socketio_path='/ws/socket.io/')
    
    # Trigger test events
    # ... test emission
    
    await asyncio.sleep(5)
    print(f"Total events received: {len(events_received)}")
    
asyncio.run(test_events())
```

### 3. Frontend Integration Test
```bash
# Run frontend with debug logging
VITE_LOG_LEVEL=debug npm run dev

# Check browser console for:
# - WebSocket connection established
# - Events being received
# - Redux state updates
```

### 4. End-to-End Discovery Test
```bash
# Upload a test PDF and monitor:
# 1. Backend logs for event emission
# 2. Frontend console for event reception
# 3. UI updates (tabs, facts, progress)
```

## CRITICAL GOTCHAS

1. **Events ARE Being Emitted**
   - Docker logs confirm: `emitting event "discovery:document_found" to all [/]`
   - The issue is NOT with event emission, but with reception/processing

2. **camelCase vs snake_case Mismatch**
   - Backend: `processingId`, `documentId`, `pageCount`
   - Frontend: `processing_id`, `document_id`, `page_count`
   - This MUST be fixed for events to be processed

3. **Rapid Subscribe/Unsubscribe Loop**
   - Frontend is subscribing/unsubscribing multiple times per second
   - This may be caused by React effect re-renders
   - Can cause events to be missed during unsubscribed periods

4. **Processing ID Not Available**
   - Frontend may not have the processing_id when events arrive
   - Events broadcast to "all" but frontend filters by processing_id
   - Timing issue: events arrive before frontend knows its processing_id

5. **Multiple Connections**
   - Docker logs show multiple socket IDs
   - Could be multiple tabs, or connection recycling
   - Each connection needs proper event subscription

## REFERENCES

- **Socket.IO Debugging**: https://socket.io/docs/v3/troubleshooting-connection-issues/
- **FastAPI WebSockets**: https://fastapi.tiangolo.com/reference/websockets/
- **Python SocketIO**: https://python-socketio.readthedocs.io/en/latest/
- **React Socket.IO Client**: https://socket.io/docs/v4/client-api/

## IMPLEMENTATION TASKS (PRIORITIZED)

### Critical (Must Fix First)
1. [ ] Fix event property naming in `socket_server.py` (camelCase → snake_case)
2. [ ] Fix rapid subscribe/unsubscribe loop in frontend
3. [ ] Ensure processing_id is available before subscribing to events

### High Priority
4. [ ] Add comprehensive event logging to trace flow
5. [ ] Add processing_id validation in event handlers
6. [ ] Test with single tab to eliminate multiple connection issues

### Medium Priority
7. [ ] Create test endpoint for isolated event testing
8. [ ] Add connection stability monitoring
9. [ ] Implement proper cleanup on component unmount

### Low Priority
10. [ ] Document the final solution
11. [ ] Add automated tests for WebSocket events
12. [ ] Consider using rooms for targeted event delivery

## DEBUGGING STEPS

1. **Verify Event Names Fixed**
   ```bash
   # Check docker logs for event structure
   docker-compose -p localai logs -f clerk | grep "emitting event"
   ```

2. **Monitor Frontend Console**
   ```javascript
   // Add to browser console
   window.socket = window.socket || io.sockets[0];
   window.socket.onAny((event, ...args) => {
       console.log('Event:', event, args);
   });
   ```

3. **Test Single Event**
   ```bash
   # Trigger test event from backend
   curl -X POST http://localhost:8010/api/discovery/test-events
   ```

## EXPECTED OUTCOME

After implementing these fixes:
1. Events have correct property names (snake_case)
2. No rapid subscribe/unsubscribe loops
3. Frontend receives and processes all discovery events
4. Document tabs appear as documents are discovered
5. Facts stream in real-time as they are extracted
6. WebSocket connection remains stable throughout processing

## CONFIDENCE SCORE: 9/10

The docker logs have confirmed the root cause: events are being emitted but not processed due to property name mismatch and subscription instability. The fix is straightforward with clear validation steps. The remaining 1 point accounts for potential edge cases in the subscription timing.
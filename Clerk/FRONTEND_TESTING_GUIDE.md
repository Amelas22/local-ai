# Clerk Frontend Testing Guide

## Current Implementation Status

### ✅ Implemented Components

1. **WebSocket Connection**
   - Socket.io client properly configured
   - Auto-connection on app load
   - Reconnection logic with exponential backoff
   - Connection state tracked in Redux

2. **Discovery Form**
   - Complete form with all required fields
   - Form validation
   - API submission to backend
   - Mock endpoint available for testing

3. **WebSocket Event Handlers**
   - All discovery events properly mapped
   - Redux state updates on each event
   - Document stream updates in real-time

4. **UI Components**
   - DocumentStream displays discovered documents
   - ProcessingVisualization shows progress
   - ProcessingStats tracks metrics
   - Tab-based interface for different views

### ⚠️ Known Issues

1. **Backend Dependencies**: The real discovery processor requires Box API and other dependencies
2. **Mock Endpoint**: Using `/discovery/process/mock` for testing without dependencies
3. **WebSocket Path**: Ensure backend mounts WebSocket at `/ws/socket.io`

## Testing Instructions

### 1. Start the Backend

```bash
cd /mnt/c/Users/jlemr/Test2/local-ai-package/Clerk
python3 main.py
```

If you get dependency errors, you can run a minimal backend:
```bash
# Create a minimal test server
python3 -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Start the Frontend

```bash
cd /mnt/c/Users/jlemr/Test2/local-ai-package/Clerk/frontend
npm install  # First time only
npm run dev
```

### 3. Access the Application

Navigate to: http://localhost:5173/discovery

### 4. Test Discovery Processing

Fill out the form with these test values:
- **Box Folder ID**: `test_folder_123`
- **Case Name**: `Smith_v_Jones_2024`
- **Production Batch**: `Defendant's First Production`
- **Producing Party**: `ABC Transport Corp`
- **Production Date**: Today's date
- **Responsive Requests**: Select or add `RFP 1-25`, `RFA 1-15`
- **Confidentiality**: `Confidential`
- **Force Fact Extraction**: Toggle ON

### 5. Submit and Monitor

1. Click "Start Processing"
2. The form should show "Processing..." on the button
3. You should automatically switch to the "Processing Status" tab
4. Watch for:
   - Progress bar updating through stages
   - Documents appearing in the stream as they're discovered
   - Each document showing:
     - Title
     - Document type (colored chip)
     - Bates range
     - Confidence score
     - Processing progress
   - Statistics updating (documents found, processed, chunks, vectors)

### 6. Expected Flow

The mock processor will:
1. Emit `discovery:started` - Progress bar begins
2. For each of 5 documents:
   - Emit `discovery:document_found` - Document appears in stream
   - Emit multiple `discovery:chunking` - Progress updates
   - Emit multiple `discovery:embedding` - More progress
   - Emit `discovery:stored` - Document marked complete
3. Emit `discovery:completed` - Final summary shown

Total processing time: ~15-20 seconds

## Troubleshooting

### WebSocket Not Connecting

1. Check browser console for WebSocket errors
2. Verify backend is running on port 8000
3. Check CORS settings in main.py
4. Try accessing http://localhost:8000/docs to verify backend

### No Real-time Updates

1. Open browser DevTools Network tab
2. Filter by "WS" to see WebSocket connections
3. Should see connection to `ws://localhost:8000/ws/socket.io/`
4. Check "Messages" tab for event flow

### Form Submission Errors

1. Check browser console for API errors
2. Verify mock endpoint exists: `POST /discovery/process/mock`
3. Check Redux DevTools for state updates

## Development Tips

### Enable Debug Logging

```typescript
// In frontend/.env.development
VITE_LOG_LEVEL=debug
```

### Monitor Redux State

Install Redux DevTools browser extension to see:
- `discovery` slice for processing state
- `websocket` slice for connection status
- `ui` slice for toasts/notifications

### Test Individual Events

You can test WebSocket events from browser console:
```javascript
// Get socket instance (when using debug mode)
const socket = window.__socket__;

// Simulate events
socket.emit('discovery:document_found', {
  processingId: 'test-123',
  documentId: 'doc_99',
  title: 'Test Document.pdf',
  type: 'motion',
  pageCount: 50,
  confidence: 0.95
});
```

## Next Steps

Once basic testing works:

1. **Enhance Visualizations**
   - Add chunking animations
   - Show embedding generation progress
   - Add document preview on click

2. **Error Handling**
   - Test error scenarios
   - Add retry mechanisms
   - Improve error messages

3. **Performance**
   - Handle large document sets (100+ documents)
   - Optimize re-renders
   - Add virtual scrolling for document list

4. **Integration**
   - Connect to real Box API
   - Implement actual document processing
   - Add download/export features
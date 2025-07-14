# Discovery Processing Debug Summary

## Overview

I've completed the implementation of comprehensive debugging tools and logging for the discovery processing feature. The integration code was already present in `discovery_endpoints.py` (lines 263-264 using DiscoveryProductionProcessor), but needed debugging to identify why document splitting wasn't creating multiple tabs in the frontend.

## What Was Added

### 1. Enhanced Logging

**Backend Logging:**
- Added comprehensive logging to `discovery_endpoints.py` (lines 311, 319, 327-330, 339)
- Added initialization logging to `discovery_splitter.py` (lines 47-51)
- Logs now show:
  - When discovery processing starts
  - How many segments are found
  - Details of each segment (type, title, pages, confidence)
  - When WebSocket events are emitted

**Frontend Logging:**
- Added console logging to `useEnhancedDiscoverySocket.ts`
- Logs show when WebSocket events are received
- Tracks document discovery events in browser console

### 2. Debugging Tools

**`test_websocket_events.py`**
- Monitors WebSocket events in real-time
- Shows all discovery-related events as they occur
- Saves event log to `discovery_events_log.json`
- Usage: `python test_websocket_events.py`

**`test_discovery_simple.py`**
- Tests the discovery splitter directly with a PDF
- Shows how many documents are found
- Displays confidence scores and document types
- Usage: `python test_discovery_simple.py`

**`verify_discovery_env.py`**
- Checks all required environment variables
- Verifies OpenAI connection
- Shows what's missing or misconfigured
- Usage: `python verify_discovery_env.py`

**`run_discovery_validation.py`**
- Comprehensive validation suite
- Tests all components end-to-end
- Generates detailed validation report
- Usage: `python run_discovery_validation.py`

**`run_discovery_tests_docker.sh`**
- All-in-one bash script for Docker
- Runs all tests in sequence
- Shows combined results
- Usage: `bash run_discovery_tests_docker.sh`

## How to Debug

### Step 1: Check Environment
```bash
docker-compose -p localai exec clerk python verify_discovery_env.py
```

Key variables that must be set:
- `DISCOVERY_BOUNDARY_MODEL=gpt-4.1-mini`
- `DISCOVERY_WINDOW_SIZE=5`
- `DISCOVERY_WINDOW_OVERLAP=1`
- `DISCOVERY_CONFIDENCE_THRESHOLD=0.7`
- `OPENAI_API_KEY=<your-key>`

### Step 2: Test Discovery Splitter
```bash
docker-compose -p localai exec clerk python test_discovery_simple.py
```

This should show 18+ documents found from `tesdoc_Redacted_ocr.pdf`.

### Step 3: Monitor WebSocket Events
In one terminal:
```bash
docker-compose -p localai exec clerk python test_websocket_events.py
```

In another terminal, upload a PDF through the frontend or API.

### Step 4: Check Docker Logs
```bash
docker-compose -p localai logs -f clerk | grep -i discovery
```

Look for:
- "Processing PDF with discovery splitter"
- "Discovery result: X segments found"
- "Emitting discovery:document_found for segment"

### Step 5: Check Browser Console
Open browser DevTools (F12) and look for:
- "🔌 [Discovery] Subscribing to WebSocket events..."
- "📄 [Discovery] Document Found event received:"
- "✅ [Discovery] Completed event received:"

## Common Issues

### Issue: Only One Tab Shows
**Cause:** Document splitting not working
**Check:**
1. Verify `DISCOVERY_BOUNDARY_MODEL=gpt-4.1-mini` is set
2. Run `test_discovery_simple.py` to verify splitter works
3. Check Docker logs for "segments found" message

### Issue: No WebSocket Events
**Cause:** WebSocket connection issues
**Check:**
1. Verify WebSocket is running: `curl http://localhost:8000/websocket/status`
2. Check browser console for connection errors
3. Ensure case context headers are present

### Issue: AI Model Errors
**Cause:** OpenAI API issues
**Check:**
1. Verify `OPENAI_API_KEY` is valid
2. Check for rate limiting in logs
3. Ensure model name is `gpt-4.1-mini` (not `gpt-4o-mini`)

## Quick Test

Run this single command to test everything:
```bash
docker-compose -p localai exec clerk bash run_discovery_tests_docker.sh
```

This will:
1. Check environment variables
2. Test the discovery splitter
3. Monitor WebSocket events
4. Run full validation
5. Show all results

## Success Criteria

When working correctly, you should see:
- ✅ 18+ segments discovered from test PDF
- ✅ Multiple `discovery:document_found` WebSocket events
- ✅ Frontend shows 18+ tabs
- ✅ Each tab has its own processing progress
- ✅ Facts appear in the correct document tabs

## Files Modified

1. `/app/src/api/discovery_endpoints.py` - Added logging
2. `/app/src/document_processing/discovery_splitter.py` - Added logging
3. `/app/frontend/src/hooks/useEnhancedDiscoverySocket.ts` - Added console logging

## Files Created

1. `test_websocket_events.py` - WebSocket event monitor
2. `test_discovery_simple.py` - Direct splitter test
3. `verify_discovery_env.py` - Environment checker
4. `run_discovery_validation.py` - Full validation suite
5. `run_discovery_tests_docker.sh` - All-in-one test script

## Next Steps

1. Run the validation script to identify the specific issue
2. Check the logs to see where the process is failing
3. Fix any environment variable issues
4. Verify the PDF has extractable text (use OCR'd version)
5. Monitor WebSocket events to ensure they're being emitted

The integration code is already in place - this is a debugging exercise to find why it's not working as expected.
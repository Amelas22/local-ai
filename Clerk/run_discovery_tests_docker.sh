#!/bin/bash
# Discovery Processing Validation Script for Docker

echo "🔧 Discovery Processing Debug & Validation"
echo "========================================"
echo "Running inside Docker container: clerk"
echo "Date: $(date)"
echo "========================================"

# Change to app directory
cd /app

echo -e "\n1️⃣  Checking Environment Variables..."
echo "--------------------------------------"
python verify_discovery_env.py

echo -e "\n2️⃣  Testing Discovery Splitter Directly..."
echo "--------------------------------------"
python test_discovery_simple.py

echo -e "\n3️⃣  Starting WebSocket Monitor (background)..."
echo "--------------------------------------"
python test_websocket_events.py > websocket_monitor.log 2>&1 &
MONITOR_PID=$!
echo "Monitor started with PID: $MONITOR_PID"

echo -e "\n4️⃣  Running Full Validation..."
echo "--------------------------------------"
python run_discovery_validation.py

echo -e "\n5️⃣  Checking Docker Logs..."
echo "--------------------------------------"
echo "Recent discovery-related logs:"
tail -n 50 /app/logs/app.log 2>/dev/null | grep -i discovery || echo "No discovery logs found"

echo -e "\n6️⃣  Checking WebSocket Monitor Output..."
echo "--------------------------------------"
if [ -f websocket_monitor.log ]; then
    echo "WebSocket monitor log:"
    tail -n 20 websocket_monitor.log
fi

# Kill monitor process
kill $MONITOR_PID 2>/dev/null

echo -e "\n7️⃣  Final Results..."
echo "--------------------------------------"
if [ -f discovery_events_log.json ]; then
    echo "WebSocket events summary:"
    python -c "
import json
with open('discovery_events_log.json', 'r') as f:
    data = json.load(f)
    print(f'Total Events: {data[\"summary\"][\"total_events\"]}')
    print(f'Documents Found: {data[\"summary\"][\"total_documents\"]}')
    print('Event Types:')
    for event, count in data['summary']['event_counts'].items():
        print(f'  {event}: {count}')
"
fi

echo -e "\n✅ Validation Complete!"
echo "Check the following files for details:"
echo "  - discovery_test_results.txt"
echo "  - discovery_events_log.json"
echo "  - discovery_validation_report_*.json"
echo "  - websocket_monitor.log"
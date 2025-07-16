#!/bin/bash

# Create a simple test PDF using Docker
docker exec clerk python -c "
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

c = canvas.Canvas('/tmp/test_discovery.pdf', pagesize=letter)
# Page 1 - Document 1
c.drawString(100, 750, 'DRIVER QUALIFICATION FILE')
c.drawString(100, 700, 'Employee Name: John Doe')
c.drawString(100, 650, 'CDL Number: 123456789')
c.showPage()

# Page 2 - Document 1 continued
c.drawString(100, 750, 'Driver History - Page 2')
c.drawString(100, 700, 'Experience: 10 years')
c.showPage()

# Page 3 - Document 2
c.drawString(100, 750, 'EMPLOYMENT APPLICATION')
c.drawString(100, 700, 'Application Date: 01/15/2024')
c.showPage()

# Page 4 - Document 2 continued
c.drawString(100, 750, 'Employment History')
c.drawString(100, 700, 'Previous Employer: ABC Trucking')
c.showPage()

c.save()
print('Test PDF created successfully')
"

echo "Testing discovery processing endpoint..."
echo "===================================="

# Send the discovery processing request
response=$(docker exec clerk curl -s -X POST \
  -F "case_id=test_case_async_$(date +%s)" \
  -F "case_name=test_case_async_$(date +%s)" \
  -F "production_batch=TestBatch001" \
  -F "producing_party=Test Party" \
  -F "enable_fact_extraction=false" \
  -F "discovery_files=@/tmp/test_discovery.pdf" \
  http://localhost:8000/api/discovery/process)

echo "Response: $response"

# Extract processing_id using grep and sed
processing_id=$(echo "$response" | grep -o '"processing_id":"[^"]*"' | sed 's/"processing_id":"\([^"]*\)"/\1/')

if [ -n "$processing_id" ]; then
    echo "Processing ID: $processing_id"
    echo "Checking status..."
    
    # Poll status for up to 30 seconds
    for i in {1..30}; do
        sleep 1
        status=$(docker exec clerk curl -s http://localhost:8000/api/discovery/status/$processing_id)
        echo -ne "\rAttempt $i/30: $status"
        
        # Check if completed or error
        if echo "$status" | grep -q '"status":"completed"'; then
            echo -e "\n\nProcessing completed successfully!"
            echo "Final status: $status"
            break
        elif echo "$status" | grep -q '"status":"error"'; then
            echo -e "\n\nProcessing failed with error!"
            echo "Final status: $status"
            break
        fi
    done
else
    echo "Failed to get processing ID from response"
fi

echo -e "\n\nChecking Docker logs for any errors..."
docker logs clerk --tail 20 | grep -E "(ERROR|Exception|Traceback)" || echo "No errors found in recent logs"
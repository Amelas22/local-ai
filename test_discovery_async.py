#!/usr/bin/env python3
"""
Test script for discovery processing with async fixes
"""
import asyncio
import aiohttp
import time
import sys

async def test_discovery_processing():
    """Test the discovery processing endpoint"""
    
    # Use a small test PDF that we know exists
    test_pdf_path = "/mnt/d/jrl/GitHub Repos/local-ai/Clerk/tests/test_data/test_pdf.pdf"
    
    # Check if file exists
    import os
    if not os.path.exists(test_pdf_path):
        print(f"Test PDF not found at {test_pdf_path}")
        # Create a minimal test PDF
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        
        c = canvas.Canvas(test_pdf_path, pagesize=letter)
        c.drawString(100, 750, "Test Document 1")
        c.drawString(100, 700, "This is a test document for discovery processing.")
        c.showPage()
        c.drawString(100, 750, "Test Document 2") 
        c.drawString(100, 700, "This is another test document.")
        c.showPage()
        c.save()
        print(f"Created test PDF at {test_pdf_path}")
    
    # Read the PDF file
    with open(test_pdf_path, 'rb') as f:
        pdf_content = f.read()
    
    # Prepare the multipart form data
    form_data = aiohttp.FormData()
    form_data.add_field('case_id', 'test_case_async')
    form_data.add_field('case_name', 'test_case_async')
    form_data.add_field('production_batch', 'TestBatch001')
    form_data.add_field('producing_party', 'Test Party')
    form_data.add_field('enable_fact_extraction', 'false')  # Disable to make test faster
    form_data.add_field('discovery_files', 
                       pdf_content,
                       filename='test_discovery.pdf',
                       content_type='application/pdf')
    
    # Send the request
    async with aiohttp.ClientSession() as session:
        url = "http://localhost:8010/api/discovery/process"
        
        print(f"Sending discovery processing request to {url}")
        start_time = time.time()
        
        try:
            async with session.post(url, data=form_data) as response:
                result = await response.json()
                print(f"Response status: {response.status}")
                print(f"Response: {result}")
                
                if response.status == 200:
                    processing_id = result.get('processing_id')
                    print(f"\nProcessing started with ID: {processing_id}")
                    print("Check the server logs for processing progress")
                    
                    # Poll the status endpoint
                    status_url = f"http://localhost:8010/api/discovery/status/{processing_id}"
                    for i in range(30):  # Poll for up to 30 seconds
                        await asyncio.sleep(1)
                        async with session.get(status_url) as status_response:
                            if status_response.status == 200:
                                status_data = await status_response.json()
                                print(f"\rStatus: {status_data['status']} - Documents: {status_data.get('processed_documents', 0)}/{status_data.get('total_documents', 0)}", end='')
                                
                                if status_data['status'] in ['completed', 'error']:
                                    print(f"\n\nProcessing {status_data['status']}!")
                                    print(f"Total time: {time.time() - start_time:.2f} seconds")
                                    if status_data['status'] == 'error':
                                        print(f"Error: {status_data.get('error_message', 'Unknown error')}")
                                    else:
                                        print(f"Documents found: {status_data.get('total_documents', 0)}")
                                        print(f"Facts extracted: {status_data.get('total_facts', 0)}")
                                    break
                else:
                    print(f"Error: {result}")
                    
        except Exception as e:
            print(f"Error: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    print("Testing Discovery Processing with Async Fixes")
    print("=" * 50)
    asyncio.run(test_discovery_processing())
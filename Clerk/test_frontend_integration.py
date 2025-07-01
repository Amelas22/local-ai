#!/usr/bin/env python3
"""
Test script to verify frontend integration with WebSocket discovery processing
"""
import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any

# Import the WebSocket document processor
from src.document_processing.websocket_document_processor import WebSocketDocumentProcessor
from src.models.unified_document_models import DiscoveryProcessingRequest

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_websocket_processing():
    """Test the WebSocket document processor with mock data"""
    
    # Create processor instance
    processor = WebSocketDocumentProcessor(None)  # Mock processor doesn't need injector
    
    # Create test request
    test_request = DiscoveryProcessingRequest(
        folder_id="test_folder_123",
        case_name="Smith_v_Jones_2024",
        production_batch="Defendant's First Production",
        producing_party="ABC Transport Corp",
        production_date=datetime.now(),
        responsive_to_requests=["RFP 1-25", "RFA 1-15"],
        confidentiality_designation="Confidential",
        override_fact_extraction=True
    )
    
    logger.info("Starting test discovery processing...")
    logger.info(f"Request: {test_request.dict()}")
    
    try:
        # Process with WebSocket updates
        result = await processor.process_discovery_with_updates(test_request)
        
        logger.info(f"Processing completed successfully!")
        logger.info(f"Result: {json.dumps(result, indent=2)}")
        
        # Check job status
        job_status = processor.get_job_status(result['processing_id'])
        logger.info(f"Job status: {json.dumps(job_status, indent=2, default=str)}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error during processing: {str(e)}", exc_info=True)
        raise

def main():
    """Run the test"""
    # Check if we're in the right directory
    import os
    if not os.path.exists('main.py'):
        logger.error("Please run this script from the Clerk directory")
        return
    
    logger.info("Starting WebSocket integration test...")
    
    # Run the async test
    try:
        result = asyncio.run(test_websocket_processing())
        logger.info("\nTest completed successfully!")
        logger.info("\nTo test with the frontend:")
        logger.info("1. Start the backend: python main.py")
        logger.info("2. Start the frontend: cd frontend && npm run dev")
        logger.info("3. Navigate to http://localhost:5173/discovery")
        logger.info("4. Fill out the form with these test values:")
        logger.info("   - Box Folder ID: test_folder_123")
        logger.info("   - Case Name: Smith_v_Jones_2024")
        logger.info("   - Production Batch: Defendant's First Production")
        logger.info("   - Producing Party: ABC Transport Corp")
        logger.info("5. Submit the form and watch the real-time updates!")
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
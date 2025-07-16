#!/usr/bin/env python
"""
Direct test of DiscoveryProductionProcessor with the OCR'd PDF.
This tests the document splitting functionality independently of the API.
"""

import os
import sys
import logging
from datetime import datetime

# Add src to path
sys.path.insert(0, '/app')

from src.document_processing.discovery_splitter import DiscoveryProductionProcessor
from src.models.unified_document_models import DocumentType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_discovery_splitter():
    """Test the discovery splitter directly with the OCR'd PDF"""
    
    # Path to test PDF
    pdf_path = "/app/tesdoc_Redacted_ocr.pdf"
    
    if not os.path.exists(pdf_path):
        logger.error(f"Test PDF not found at {pdf_path}")
        return
    
    logger.info(f"Testing discovery splitter with: {pdf_path}")
    logger.info(f"File size: {os.path.getsize(pdf_path):,} bytes")
    
    # Initialize processor
    case_name = "test_case_discovery"
    processor = DiscoveryProductionProcessor(case_name=case_name)
    
    # Production metadata
    production_metadata = {
        "production_batch": "TEST_BATCH_001",
        "producing_party": "Test Opposing Counsel",
        "production_date": datetime.now().isoformat(),
        "responsive_to_requests": ["RFP_001", "RFP_005"],
        "confidentiality_designation": "Confidential"
    }
    
    logger.info("Processing discovery production...")
    logger.info(f"Production metadata: {production_metadata}")
    
    try:
        # Process the PDF
        result = processor.process_discovery_production(
            pdf_path=pdf_path,
            production_metadata=production_metadata
        )
        
        # Log results
        logger.info("=" * 80)
        logger.info("DISCOVERY PROCESSING RESULTS")
        logger.info("=" * 80)
        logger.info(f"Case Name: {result.case_name}")
        logger.info(f"Production Batch: {result.production_batch}")
        logger.info(f"Total Pages: {result.total_pages}")
        logger.info(f"Documents Found: {len(result.segments_found)}")
        logger.info(f"Average Confidence: {result.average_confidence:.2f}")
        logger.info(f"Processing Windows: {result.processing_windows}")
        logger.info(f"Processing Time: {(result.processing_completed - result.processing_started).total_seconds():.2f} seconds")
        
        if result.errors:
            logger.warning(f"Errors encountered: {len(result.errors)}")
            for error in result.errors[:5]:  # Show first 5 errors
                logger.warning(f"  - {error}")
        
        logger.info("\n" + "-" * 80)
        logger.info("DOCUMENT SEGMENTS FOUND:")
        logger.info("-" * 80)
        
        # Display each segment
        for idx, segment in enumerate(result.segments_found):
            logger.info(f"\nSegment {idx + 1}:")
            logger.info(f"  Type: {segment.document_type.value}")
            logger.info(f"  Title: {segment.title or 'Untitled'}")
            logger.info(f"  Pages: {segment.start_page + 1} - {segment.end_page + 1} ({segment.page_count} pages)")
            logger.info(f"  Confidence: {segment.confidence_score:.2f}")
            logger.info(f"  Bates Range: {segment.bates_range or 'None detected'}")
            if segment.boundary_indicators:
                logger.info(f"  Boundary Indicators:")
                for indicator in segment.boundary_indicators[:3]:  # Show first 3
                    logger.info(f"    - {indicator}")
            logger.info(f"  Extraction Success: {segment.extraction_successful}")
            logger.info(f"  Processing Strategy: {segment.processing_strategy.value if segment.processing_strategy else 'STANDARD'}")
        
        # Summary statistics
        logger.info("\n" + "=" * 80)
        logger.info("SUMMARY STATISTICS:")
        logger.info("=" * 80)
        
        # Count document types
        type_counts = {}
        for segment in result.segments_found:
            doc_type = segment.document_type.value
            type_counts[doc_type] = type_counts.get(doc_type, 0) + 1
        
        logger.info("Document Types Found:")
        for doc_type, count in sorted(type_counts.items()):
            logger.info(f"  {doc_type}: {count}")
        
        # Page distribution
        total_pages_in_segments = sum(seg.page_count for seg in result.segments_found)
        logger.info(f"\nPage Distribution:")
        logger.info(f"  Total PDF Pages: {result.total_pages}")
        logger.info(f"  Pages in Segments: {total_pages_in_segments}")
        logger.info(f"  Average Pages per Document: {total_pages_in_segments / len(result.segments_found):.1f}")
        
        # Confidence analysis
        confidence_scores = [seg.confidence_score for seg in result.segments_found]
        logger.info(f"\nConfidence Analysis:")
        logger.info(f"  Average Confidence: {result.average_confidence:.2f}")
        logger.info(f"  Min Confidence: {min(confidence_scores):.2f}")
        logger.info(f"  Max Confidence: {max(confidence_scores):.2f}")
        
        # Low confidence segments
        low_confidence = [seg for seg in result.segments_found if seg.confidence_score < 0.7]
        if low_confidence:
            logger.warning(f"\nLow Confidence Segments ({len(low_confidence)}):")
            for seg in low_confidence:
                logger.warning(f"  - Pages {seg.start_page + 1}-{seg.end_page + 1}: {seg.confidence_score:.2f}")
        
        # Success check
        if len(result.segments_found) >= 10:
            logger.info("\n✅ SUCCESS: Found multiple documents in the PDF!")
        else:
            logger.warning(f"\n⚠️  WARNING: Only found {len(result.segments_found)} documents. Expected more.")
        
        # Save detailed results
        output_file = "discovery_test_results.txt"
        with open(output_file, 'w') as f:
            f.write(f"Discovery Processing Test Results\n")
            f.write(f"Generated at: {datetime.now()}\n")
            f.write(f"PDF: {pdf_path}\n")
            f.write(f"Documents Found: {len(result.segments_found)}\n\n")
            
            for idx, segment in enumerate(result.segments_found):
                f.write(f"Document {idx + 1}:\n")
                f.write(f"  Type: {segment.document_type.value}\n")
                f.write(f"  Title: {segment.title or 'Untitled'}\n")
                f.write(f"  Pages: {segment.start_page + 1}-{segment.end_page + 1}\n")
                f.write(f"  Confidence: {segment.confidence_score:.2f}\n")
                f.write(f"  Bates: {segment.bates_range or 'None'}\n\n")
        
        logger.info(f"\n💾 Detailed results saved to {output_file}")
        
    except Exception as e:
        logger.error(f"Error during processing: {str(e)}", exc_info=True)
        raise

def check_environment():
    """Check if required environment variables are set"""
    logger.info("\nChecking environment variables...")
    
    env_vars = {
        'DISCOVERY_BOUNDARY_MODEL': 'gpt-4.1-mini',
        'DISCOVERY_WINDOW_SIZE': '5',
        'DISCOVERY_WINDOW_OVERLAP': '1',
        'DISCOVERY_CONFIDENCE_THRESHOLD': '0.7',
        'OPENAI_API_KEY': '<should be set>'
    }
    
    all_good = True
    for var, expected in env_vars.items():
        value = os.getenv(var, 'NOT SET')
        if var == 'OPENAI_API_KEY':
            if value == 'NOT SET':
                logger.error(f"❌ {var} is not set!")
                all_good = False
            else:
                logger.info(f"✅ {var} is set")
        else:
            if value == expected:
                logger.info(f"✅ {var} = {value}")
            else:
                logger.warning(f"⚠️  {var} = {value} (expected: {expected})")
    
    return all_good

if __name__ == "__main__":
    logger.info("Starting Discovery Splitter Test")
    logger.info("=" * 80)
    
    # Check environment first
    if not check_environment():
        logger.error("Environment check failed! Please set required variables.")
        sys.exit(1)
    
    # Run the test
    test_discovery_splitter()
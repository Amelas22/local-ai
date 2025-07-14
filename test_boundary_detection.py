#!/usr/bin/env python3
"""
Test document boundary detection directly
"""

import sys
sys.path.append('/app')

from src.document_processing.discovery_splitter import DiscoveryProductionProcessor
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Test the boundary detection
processor = DiscoveryProductionProcessor(case_name="test_case")

# Process the test PDF
pdf_path = "/tmp/tesdoc_Redacted.pdf"
production_metadata = {
    "production_batch": "test_batch",
    "producing_party": "Test Party"
}

print("Testing boundary detection on:", pdf_path)
print("=" * 80)

try:
    result = processor.process_discovery_production(
        pdf_path=pdf_path,
        production_metadata=production_metadata
    )
    
    print(f"\nTotal pages in PDF: {result.total_pages}")
    print(f"Processing windows used: {result.processing_windows}")
    print(f"Documents found: {len(result.segments_found)}")
    print(f"Average confidence: {result.average_confidence:.2f}")
    print(f"Low confidence boundaries: {len(result.low_confidence_boundaries)}")
    
    print("\nSegments found:")
    for i, segment in enumerate(result.segments_found):
        print(f"\n{i+1}. Document Type: {segment.document_type}")
        print(f"   Pages: {segment.start_page}-{segment.end_page} ({segment.page_count} pages)")
        print(f"   Title: {segment.title or 'No title'}")
        print(f"   Confidence: {segment.confidence_score:.2f}")
        print(f"   Bates Range: {segment.bates_range}")
        print(f"   Indicators: {segment.boundary_indicators}")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
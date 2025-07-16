#!/usr/bin/env python3
"""
Test advanced boundary detection directly
"""

import sys
sys.path.append('/app')

from src.document_processing.document_boundary_detector import DocumentBoundaryDetector
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Test the advanced boundary detector
detector = DocumentBoundaryDetector()

# Process the test PDF
pdf_path = "/tmp/tesdoc_Redacted.pdf"

print("Testing advanced boundary detection on:", pdf_path)
print("=" * 80)

try:
    boundaries = detector.detect_boundaries(pdf_path, confidence_threshold=0.5)
    
    print(f"\nBoundaries found: {len(boundaries)}")
    
    for i, boundary in enumerate(boundaries):
        print(f"\n{i+1}. Document Type Hint: {boundary.document_type_hint}")
        print(f"   Pages: {boundary.start_page}-{boundary.end_page}")
        print(f"   Title: {boundary.title or 'No title'}")
        print(f"   Confidence: {boundary.confidence:.2f}")
        print(f"   Bates Range: {boundary.bates_range}")
        print(f"   Indicators: {boundary.indicators}")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
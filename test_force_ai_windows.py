#!/usr/bin/env python3
"""
Force AI boundary detection with small windows
"""

import sys
sys.path.append('/app')

from src.document_processing.discovery_splitter import BoundaryDetector
import logging

# Enable info logging only
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test the AI boundary detector
detector = BoundaryDetector()

# Temporarily lower the confidence threshold
detector.confidence_threshold = 0.3

# Disable the advanced detector to force AI approach
detector.boundary_detector = None

# Process the test PDF with smaller windows
pdf_path = "/tmp/tesdoc_Redacted_ocr.pdf"

print("Testing AI boundary detection with small windows...")
print("=" * 80)

try:
    # Use smaller window (5 pages) with minimal overlap (1 page)
    boundaries = detector.detect_all_boundaries(pdf_path, window_size=5, window_overlap=1)
    
    print(f"\nBoundaries found: {len(boundaries)}")
    
    for i, boundary in enumerate(boundaries):
        print(f"\n{i+1}. Document Type Hint: {boundary.document_type_hint}")
        print(f"   Pages: {boundary.start_page+1}-{boundary.end_page+1}")  # Convert to 1-based
        print(f"   Title: {boundary.title or 'No title'}")
        print(f"   Confidence: {boundary.confidence:.2f}")
        print(f"   Bates Range: {boundary.bates_range}")
        print(f"   Indicators: {boundary.indicators}")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
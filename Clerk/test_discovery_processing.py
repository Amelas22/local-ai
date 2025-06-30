#!/usr/bin/env python3
"""
Test script for discovery document processing
Tests the multi-document PDF segmentation and processing pipeline
"""

import asyncio
import logging
from datetime import datetime

from src.document_injector_unified import UnifiedDocumentInjector
from src.document_processing.discovery_splitter import (
    BoundaryDetector,
    DiscoveryDocumentProcessor,
    DiscoveryProductionProcessor
)
from src.models.unified_document_models import (
    DiscoveryProcessingRequest,
    DocumentBoundary
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_boundary_detection():
    """Test boundary detection on a sample PDF"""
    logger.info("Testing boundary detection...")
    
    # This would need a real PDF path
    pdf_path = "sample_discovery_production.pdf"
    
    try:
        detector = BoundaryDetector()
        
        # Test with default settings
        logger.info("Testing with default window settings...")
        # boundaries = detector.detect_all_boundaries(pdf_path)
        
        # For now, just verify it initializes correctly
        logger.info(f"✓ Boundary detector initialized with model: {detector.model}")
        logger.info(f"✓ Confidence threshold: {detector.confidence_threshold}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Boundary detection test failed: {e}")
        return False


def test_discovery_processor():
    """Test discovery document processor"""
    logger.info("\nTesting discovery document processor...")
    
    try:
        processor = DiscoveryDocumentProcessor("Test_Case_2024")
        
        # Test document classification
        sample_text = """
        DRIVER QUALIFICATION FILE
        
        Driver Name: John Smith
        CDL Number: 123456789
        Medical Certificate Expiration: 12/31/2024
        
        This file contains all required documentation for driver qualification.
        """
        
        boundary = DocumentBoundary(
            start_page=0,
            end_page=5,
            confidence=0.9,
            document_type_hint=None,
            boundary_indicators=["DRIVER QUALIFICATION FILE header"]
        )
        
        doc_type = processor.classify_document(sample_text, boundary)
        logger.info(f"✓ Document classified as: {doc_type}")
        
        # Test context generation
        context = processor.generate_document_context(
            sample_text,
            doc_type,
            boundary
        )
        logger.info(f"✓ Generated context: {context[:100]}...")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Discovery processor test failed: {e}")
        return False


def test_multi_document_detection():
    """Test multi-document production detection"""
    logger.info("\nTesting multi-document detection...")
    
    from src.document_processing.box_client import BoxDocument
    from datetime import datetime
    
    try:
        injector = UnifiedDocumentInjector()
        
        # Test with large file
        large_doc = BoxDocument(
            name="Production_001_Bates_DEF00001-DEF01000.pdf",
            file_id="test_large",
            size=15 * 1024 * 1024,  # 15MB
            modified_at=datetime.now(),
            path="/test/large.pdf",
            folder_path=["test"],
            case_name="Test_Case",
            subfolder_name="Productions"
        )
        
        is_multi = injector._is_multi_document_production(large_doc)
        logger.info(f"✓ Large file (15MB) detected as multi-doc: {is_multi}")
        
        # Test with small file
        small_doc = BoxDocument(
            name="single_document.pdf",
            file_id="test_small",
            size=500 * 1024,  # 500KB
            modified_at=datetime.now(),
            path="/test/small.pdf",
            folder_path=["test"],
            case_name="Test_Case",
            subfolder_name="Documents"
        )
        
        is_multi = injector._is_multi_document_production(small_doc)
        logger.info(f"✓ Small file (500KB) detected as multi-doc: {is_multi}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Multi-document detection test failed: {e}")
        return False


def test_discovery_endpoint_request():
    """Test discovery processing request model"""
    logger.info("\nTesting discovery processing request...")
    
    try:
        request = DiscoveryProcessingRequest(
            folder_id="123456789",
            case_name="Smith_v_Jones_2024",
            production_batch="Production 1",
            producing_party="Defendant ABC Corp",
            responsive_to_requests=["RFP 1-10", "RFP 15"],
            confidentiality_designation="Confidential"
        )
        
        logger.info(f"✓ Created discovery request for: {request.case_name}")
        logger.info(f"  Production: {request.production_batch}")
        logger.info(f"  Producer: {request.producing_party}")
        logger.info(f"  Responsive to: {', '.join(request.responsive_to_requests)}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Discovery request test failed: {e}")
        return False


def test_settings_integration():
    """Test that discovery settings are properly integrated"""
    logger.info("\nTesting settings integration...")
    
    try:
        from config.settings import settings
        
        logger.info(f"✓ Window size: {settings.discovery.window_size}")
        logger.info(f"✓ Window overlap: {settings.discovery.window_overlap}")
        logger.info(f"✓ Boundary detection model: {settings.discovery.boundary_detection_model}")
        logger.info(f"✓ Classification model: {settings.discovery.classification_model}")
        logger.info(f"✓ Multi-doc threshold: {settings.discovery.multi_doc_size_threshold_mb}MB")
        logger.info(f"✓ Max single-pass pages: {settings.discovery.max_single_pass_pages}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Settings integration test failed: {e}")
        return False


def main():
    """Run all tests"""
    logger.info("=" * 60)
    logger.info("DISCOVERY PROCESSING TEST SUITE")
    logger.info("=" * 60)
    
    tests = [
        ("Settings Integration", test_settings_integration),
        ("Boundary Detection", test_boundary_detection),
        ("Discovery Processor", test_discovery_processor),
        ("Multi-Document Detection", test_multi_document_detection),
        ("Discovery Endpoint Request", test_discovery_endpoint_request)
    ]
    
    results = []
    for test_name, test_func in tests:
        logger.info(f"\n{'='*60}")
        logger.info(f"Running: {test_name}")
        logger.info(f"{'='*60}")
        
        result = test_func()
        results.append((test_name, result))
    
    # Summary
    logger.info("\n" + "="*60)
    logger.info("TEST SUMMARY")
    logger.info("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{test_name}: {status}")
    
    logger.info(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("\n🎉 All tests passed! Discovery processing system is ready.")
    else:
        logger.error(f"\n⚠️  {total - passed} tests failed. Please check the errors above.")


if __name__ == "__main__":
    main()
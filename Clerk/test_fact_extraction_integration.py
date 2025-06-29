#!/usr/bin/env python3
"""
Test script for fact extraction integration
Tests that documents are properly processed with fact extraction
"""

import asyncio
import logging
from datetime import datetime

from src.document_injector import DocumentInjector
from src.ai_agents.fact_extractor import FactExtractor
from src.document_processing.deposition_parser import DepositionParser
from src.document_processing.exhibit_indexer import ExhibitIndexer
from src.utils.timeline_generator import TimelineGenerator
from src.vector_storage.qdrant_store import QdrantVectorStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_basic_fact_extraction():
    """Test basic fact extraction functionality"""
    logger.info("Testing basic fact extraction...")
    
    # Sample document content
    sample_content = """
    DEPOSITION OF JOHN SMITH
    
    On January 15, 2024, at approximately 3:45 PM, the defendant's vehicle 
    collided with the plaintiff's car at the intersection of Main Street and 
    5th Avenue. 
    
    Q: What were you doing at the time of the accident?
    A: I was checking my phone. (Smith Dep. 45:12-15)
    
    The police report (Exhibit A) shows photos of the damage to both vehicles.
    Medical records (Exhibit B) indicate the plaintiff sustained injuries.
    
    According to Florida Statute 316.193, driving under the influence is prohibited.
    The defendant violated 49 CFR § 395.8 regarding hours of service.
    """
    
    # Create case-specific extractors
    case_name = "Test_v_Case_2024"
    
    try:
        # Test fact extraction
        fact_extractor = FactExtractor(case_name)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        fact_collection = loop.run_until_complete(
            fact_extractor.extract_facts_from_document(
                "test_doc_1",
                sample_content,
                {"document_name": "test_deposition.pdf"}
            )
        )
        
        logger.info(f"✓ Extracted {len(fact_collection.facts)} facts")
        for fact in fact_collection.facts[:3]:
            logger.info(f"  - {fact.content[:80]}...")
        
        # Test deposition parsing
        depo_parser = DepositionParser(case_name)
        depositions = loop.run_until_complete(
            depo_parser.parse_deposition(
                "test_deposition.pdf",
                sample_content
            )
        )
        
        logger.info(f"✓ Parsed {len(depositions)} deposition citations")
        for depo in depositions:
            logger.info(f"  - {depo.citation_format}: {depo.testimony_excerpt[:50]}...")
        
        # Test exhibit indexing
        exhibit_indexer = ExhibitIndexer(case_name)
        exhibits = loop.run_until_complete(
            exhibit_indexer.index_document_exhibits(
                "test_deposition.pdf",
                sample_content
            )
        )
        
        logger.info(f"✓ Indexed {len(exhibits)} exhibits")
        for exhibit in exhibits:
            logger.info(f"  - {exhibit.exhibit_number}: {exhibit.description}")
        
        loop.close()
        
        logger.info("\n✅ Basic fact extraction test passed!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Basic fact extraction test failed: {e}")
        return False


def test_document_injector_integration():
    """Test that DocumentInjector properly integrates fact extraction"""
    logger.info("\nTesting DocumentInjector integration...")
    
    try:
        # Initialize injector with fact extraction enabled
        injector = DocumentInjector(
            enable_cost_tracking=False,
            no_context=True,  # Skip context for faster testing
            enable_fact_extraction=True
        )
        
        logger.info("✓ DocumentInjector initialized with fact extraction")
        
        # Check that fact extraction methods exist
        assert hasattr(injector, '_extract_facts_sync'), "Missing _extract_facts_sync method"
        assert hasattr(injector, '_parse_depositions_sync'), "Missing _parse_depositions_sync method"
        assert hasattr(injector, '_index_exhibits_sync'), "Missing _index_exhibits_sync method"
        
        logger.info("✓ All fact extraction methods present")
        
        # Check statistics tracking
        assert 'facts_extracted' in injector.stats
        assert 'depositions_parsed' in injector.stats
        assert 'exhibits_indexed' in injector.stats
        
        logger.info("✓ Fact extraction statistics tracking enabled")
        
        logger.info("\n✅ DocumentInjector integration test passed!")
        return True
        
    except Exception as e:
        logger.error(f"❌ DocumentInjector integration test failed: {e}")
        return False


def test_timeline_generation():
    """Test timeline generation from extracted facts"""
    logger.info("\nTesting timeline generation...")
    
    case_name = "Timeline_Test_2024"
    
    try:
        # First extract some facts with dates
        sample_content = """
        January 15, 2024: Initial incident occurred.
        February 1, 2024: Complaint filed with the court.
        March 10, 2024: Discovery phase began.
        April 5, 2024: Depositions were taken.
        May 20, 2024: Expert reports submitted.
        """
        
        fact_extractor = FactExtractor(case_name)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Extract facts
        fact_collection = loop.run_until_complete(
            fact_extractor.extract_facts_from_document(
                "timeline_doc",
                sample_content,
                {"document_name": "case_timeline.pdf"}
            )
        )
        
        logger.info(f"✓ Extracted {len(fact_collection.facts)} facts for timeline")
        
        # Generate timeline
        timeline_gen = TimelineGenerator(case_name)
        timeline = loop.run_until_complete(timeline_gen.generate_timeline())
        
        # Create narrative
        narrative = timeline_gen.generate_narrative_timeline(timeline, format="markdown")
        
        logger.info("✓ Generated timeline narrative")
        logger.info(f"  Timeline has {len(timeline.timeline_events)} events")
        logger.info(f"  Key dates identified: {len(timeline.key_dates)}")
        
        loop.close()
        
        logger.info("\n✅ Timeline generation test passed!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Timeline generation test failed: {e}")
        return False


def test_case_isolation():
    """Test that case isolation is maintained"""
    logger.info("\nTesting case isolation...")
    
    case_a = "Case_A_2024"
    case_b = "Case_B_2024"
    
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Extract facts for Case A
        fact_extractor_a = FactExtractor(case_a)
        loop.run_until_complete(
            fact_extractor_a.extract_facts_from_document(
                "doc_a",
                "Case A facts: The incident occurred on January 1, 2024.",
                {"document_name": "case_a.pdf"}
            )
        )
        
        # Try to search Case A facts from Case B extractor
        fact_extractor_b = FactExtractor(case_b)
        results = loop.run_until_complete(
            fact_extractor_b.search_facts("January 1, 2024")
        )
        
        assert len(results) == 0, "Case B found Case A facts - isolation breach!"
        
        logger.info("✓ Case isolation maintained - Case B cannot see Case A facts")
        
        loop.close()
        
        logger.info("\n✅ Case isolation test passed!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Case isolation test failed: {e}")
        return False


def main():
    """Run all integration tests"""
    logger.info("=" * 60)
    logger.info("FACT EXTRACTION INTEGRATION TEST SUITE")
    logger.info("=" * 60)
    
    tests = [
        ("Basic Fact Extraction", test_basic_fact_extraction),
        ("DocumentInjector Integration", test_document_injector_integration),
        ("Timeline Generation", test_timeline_generation),
        ("Case Isolation", test_case_isolation)
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
        logger.info("\n🎉 All tests passed! Fact extraction is properly integrated.")
    else:
        logger.error(f"\n⚠️  {total - passed} tests failed. Please check the errors above.")


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Quick test script to verify deficiency analyzer fixes.
"""
import asyncio
from src.ai_agents.deficiency_analyzer import DeficiencyAnalyzer
from src.vector_storage.qdrant_store import QdrantVectorStore, SearchResult

async def test_search_production_documents():
    """Test that search_production_documents handles embeddings correctly."""
    print("Testing search_production_documents...")
    
    try:
        # Create analyzer
        analyzer = DeficiencyAnalyzer("test_case")
        
        # This should handle the embedding generation properly now
        results = await analyzer._search_production_documents(
            query="test safety documents",
            production_batch="PROD_001"
        )
        
        print(f"✓ Search completed without error. Found {len(results)} results")
        print(f"✓ Results are of type: {type(results)}")
        if results:
            print(f"✓ First result type: {type(results[0])}")
            
    except Exception as e:
        print(f"✗ Error during search: {str(e)}")
        import traceback
        traceback.print_exc()

async def test_deduplicate_results():
    """Test that deduplicate works with SearchResult objects."""
    print("\nTesting deduplicate_results...")
    
    try:
        analyzer = DeficiencyAnalyzer("test_case")
        
        # Create test SearchResult objects
        results = [
            SearchResult(
                id="1",
                content="Test content 1",
                case_name="test_case",
                document_id="doc1",
                score=0.9,
                metadata={}
            ),
            SearchResult(
                id="2",
                content="Test content 2",
                case_name="test_case", 
                document_id="doc2",
                score=0.8,
                metadata={}
            ),
            SearchResult(
                id="3",
                content="Test content 1 duplicate",
                case_name="test_case",
                document_id="doc1",  # Duplicate document ID
                score=0.85,
                metadata={}
            )
        ]
        
        unique = analyzer._deduplicate_results(results)
        print(f"✓ Deduplication completed. {len(results)} -> {len(unique)} results")
        print(f"✓ Unique document IDs: {[r.document_id for r in unique]}")
        
    except Exception as e:
        print(f"✗ Error during deduplication: {str(e)}")
        import traceback
        traceback.print_exc()

async def test_format_documents():
    """Test document formatting with SearchResult objects."""
    print("\nTesting format_documents_for_analysis...")
    
    try:
        analyzer = DeficiencyAnalyzer("test_case")
        
        # Create test SearchResult objects
        results = [
            SearchResult(
                id="1",
                content="This is safety training content...",
                case_name="test_case",
                document_id="doc1",
                score=0.95,
                metadata={
                    "title": "Safety Training Manual",
                    "bates_range": "DEF00001-DEF00050",
                    "document_type": "manual"
                }
            ),
            SearchResult(
                id="2",
                content="Company policy content...",
                case_name="test_case",
                document_id="doc2",
                score=0.88,
                metadata={
                    "title": "Company Policy",
                    "bates_range": "DEF00051-DEF00075",
                    "document_type": "policy"
                }
            )
        ]
        
        formatted = analyzer._format_documents_for_analysis(results)
        print(f"✓ Formatting completed")
        print(f"✓ Formatted output length: {len(formatted)} chars")
        print(f"✓ Contains 'Safety Training Manual': {'Safety Training Manual' in formatted}")
        print(f"✓ Contains 'Score: 0.950': {'Score: 0.950' in formatted}")
        
    except Exception as e:
        print(f"✗ Error during formatting: {str(e)}")
        import traceback
        traceback.print_exc()

async def main():
    """Run all tests."""
    print("=== Deficiency Analyzer Fix Verification ===\n")
    
    await test_search_production_documents()
    await test_deduplicate_results()
    await test_format_documents()
    
    print("\n=== Test Complete ===")

if __name__ == "__main__":
    asyncio.run(main())
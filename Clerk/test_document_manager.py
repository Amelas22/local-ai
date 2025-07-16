#!/usr/bin/env python
"""
Test UnifiedDocumentManager methods
"""

import asyncio
from src.document_processing.unified_document_manager import UnifiedDocumentManager

async def test_document_manager():
    """Test if UnifiedDocumentManager has required methods"""
    
    print("Testing UnifiedDocumentManager...")
    
    # Create instance
    manager = UnifiedDocumentManager(case_name="test_case")
    
    # Check attributes
    print(f"Manager type: {type(manager)}")
    print(f"Has is_duplicate: {hasattr(manager, 'is_duplicate')}")
    print(f"Has add_document: {hasattr(manager, 'add_document')}")
    print(f"Has calculate_document_hash: {hasattr(manager, 'calculate_document_hash')}")
    
    # List all methods
    print("\nAll methods:")
    for attr in dir(manager):
        if not attr.startswith('_') and callable(getattr(manager, attr)):
            print(f"  - {attr}")
    
    # Test calculate_document_hash
    test_content = b"test content"
    hash_result = manager.calculate_document_hash(test_content)
    print(f"\nHash test: {hash_result}")
    
    # Test is_duplicate
    try:
        is_dup = await manager.is_duplicate(hash_result)
        print(f"is_duplicate test: {is_dup}")
    except Exception as e:
        print(f"is_duplicate error: {e}")

if __name__ == "__main__":
    asyncio.run(test_document_manager())
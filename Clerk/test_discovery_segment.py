#!/usr/bin/env python
"""
Test processing a single discovery segment
"""

import asyncio
import sys
sys.path.insert(0, '/app')

from src.document_processing.unified_document_manager import UnifiedDocumentManager
from src.models.unified_document_models import UnifiedDocument, DocumentType
from datetime import datetime

async def test_segment_processing():
    """Test processing a single segment like discovery_endpoints does"""
    
    print("Testing segment processing...")
    
    # Create document manager
    case_name = "test_case"
    document_manager = UnifiedDocumentManager(case_name)
    
    print(f"Document manager created: {type(document_manager)}")
    print(f"Has is_duplicate: {hasattr(document_manager, 'is_duplicate')}")
    
    # Test content
    segment_text = "This is a test document content for testing purposes."
    
    # Calculate hash
    doc_hash = document_manager.calculate_document_hash(segment_text.encode('utf-8'))
    print(f"Document hash: {doc_hash}")
    
    # Check for duplicates (should work)
    try:
        is_dup = await document_manager.is_duplicate(doc_hash)
        print(f"✅ is_duplicate check passed: {is_dup}")
    except AttributeError as e:
        print(f"❌ AttributeError: {e}")
    except Exception as e:
        print(f"❌ Other error: {e}")
    
    # Create unified document
    unified_doc = UnifiedDocument(
        case_name=case_name,
        document_hash=doc_hash,
        file_name="test_document.pdf",
        file_path="discovery/test/test_document.pdf",
        file_size=len(segment_text.encode('utf-8')),
        document_type=DocumentType.OTHER,
        title="Test Document",
        description="Test discovery document",
        last_modified=datetime.utcnow(),
        total_pages=1,
        summary="Test summary",
        search_text=segment_text,
        metadata={"test": True}
    )
    
    # Add document (should work)
    try:
        doc_id = await document_manager.add_document(unified_doc)
        print(f"✅ add_document passed: {doc_id}")
    except AttributeError as e:
        print(f"❌ AttributeError: {e}")
    except Exception as e:
        print(f"❌ Other error: {e}")

if __name__ == "__main__":
    asyncio.run(test_segment_processing())
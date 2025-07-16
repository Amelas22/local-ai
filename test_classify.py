import asyncio
import os
import sys
sys.path.insert(0, '/app')

from src.document_processing.discovery_splitter import DiscoveryDocumentProcessor, DocumentBoundary
from src.models.unified_document_models import DocumentType

async def test_classify():
    processor = DiscoveryDocumentProcessor("test_case")
    
    test_text = """
    DEPOSITION OF JOHN DOE
    
    This is the deposition testimony of John Doe, taken on January 15, 2024.
    
    Q: Please state your name for the record.
    A: John Doe.
    """
    
    boundary = DocumentBoundary(
        start_page=1,
        end_page=1,
        confidence=0.5,
        document_type_hint=None
    )
    
    try:
        result = await processor.classify_document(test_text, boundary)
        print(f"Classification result: {result}")
    except Exception as e:
        print(f"Error during classification: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_classify())
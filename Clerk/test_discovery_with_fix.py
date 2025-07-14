#!/usr/bin/env python
"""
Test discovery processing with DocumentCore fix
"""

import asyncio
import sys
import os

# Fix the import path before running
sys.path.insert(0, '/app')

async def test_with_fix():
    """Test discovery processing after fixing DocumentCore import"""
    
    # Import everything we need
    from src.api.discovery_endpoints import _process_discovery_async
    from src.websocket.socket_server import sio
    from datetime import datetime
    import tempfile
    
    print("🧪 Testing discovery processing with DocumentCore fix")
    print("=" * 60)
    
    # Test parameters
    processing_id = "test_fix_001"
    case_name = f"test_fix_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Create a simple request object
    class TestRequest:
        discovery_files = ["test.pdf"]
        box_folder_id = None
        rfp_file = None
    
    # Read test PDF
    with open('/app/tesdoc_Redacted_ocr.pdf', 'rb') as f:
        pdf_content = f.read()
    
    # Create file data
    file_contents = [{
        "filename": "tesdoc_Redacted_ocr.pdf",
        "content": pdf_content,
        "content_type": "application/pdf"
    }]
    
    print(f"📄 Processing PDF: {len(pdf_content):,} bytes")
    print(f"📁 Case name: {case_name}")
    print(f"🔑 Processing ID: {processing_id}")
    
    # Mock the DocumentCore import in discovery_endpoints
    import src.api.discovery_endpoints
    from src.models.normalized_document_models import DocumentCore
    
    # Patch the module to have DocumentCore available
    src.models.document_core = type(sys)('document_core')
    src.models.document_core.DocumentCore = DocumentCore
    sys.modules['src.models.document_core'] = src.models.document_core
    
    print("\n✅ Applied DocumentCore import fix")
    
    try:
        # Run the processing
        print("\n⚙️  Starting discovery processing...")
        await _process_discovery_async(
            processing_id=processing_id,
            case_name=case_name,
            request=TestRequest(),
            discovery_files=file_contents,
            rfp_file=None,
            production_batch="FIX_TEST_001",
            producing_party="Fix Test Party",
            production_date=None,
            responsive_to_requests=[],
            confidentiality_designation=None,
            enable_fact_extraction=False
        )
        
        print("\n✅ Processing completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error during processing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_with_fix())
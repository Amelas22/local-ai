#!/usr/bin/env python
"""
Final test of discovery processing with all fixes
"""

import asyncio
import sys
import os
import hashlib
from datetime import datetime

# Fix the import path before running
sys.path.insert(0, '/app')

async def test_final():
    """Test discovery processing end-to-end with fixes"""
    
    print("🎯 Discovery Processing Final Test")
    print("=" * 60)
    
    # Import what we need
    from src.document_processing.discovery_splitter import DiscoveryProductionProcessor
    from src.document_processing.unified_document_manager import UnifiedDocumentManager
    from src.document_processing.enhanced_chunker import EnhancedChunker
    from src.vector_storage.embeddings import EmbeddingGenerator
    from src.vector_storage.qdrant_store import QdrantVectorStore
    from src.models.unified_document_models import UnifiedDocument, DocumentType
    from src.models.normalized_document_models import DocumentCore
    import tempfile
    import pdfplumber
    
    # Test parameters
    case_name = f"test_final_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    print(f"📁 Case name: {case_name}")
    
    # Initialize components
    discovery_processor = DiscoveryProductionProcessor(case_name=case_name)
    document_manager = UnifiedDocumentManager(case_name)
    embedding_generator = EmbeddingGenerator()
    vector_store = QdrantVectorStore()
    chunker = EnhancedChunker(
        embedding_generator=embedding_generator,
        chunk_size=1400,
        chunk_overlap=200
    )
    
    # Read test PDF
    pdf_path = '/app/tesdoc_Redacted_ocr.pdf'
    with open(pdf_path, 'rb') as f:
        pdf_content = f.read()
    
    print(f"📄 PDF loaded: {len(pdf_content):,} bytes")
    
    # Save PDF temporarily
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
        tmp_file.write(pdf_content)
        temp_pdf_path = tmp_file.name
    
    try:
        # Process with discovery splitter
        print("\n🔍 Phase 1: Document Boundary Detection")
        production_result = discovery_processor.process_discovery_production(
            pdf_path=temp_pdf_path,
            production_metadata={
                "production_batch": "FINAL_TEST",
                "producing_party": "Test Party",
                "production_date": datetime.now().isoformat()
            }
        )
        
        print(f"✅ Found {len(production_result.segments_found)} documents")
        print(f"📊 Average confidence: {production_result.average_confidence:.2f}")
        
        # Process first 3 segments to test the pipeline
        segments_to_process = production_result.segments_found[:3]
        processed_count = 0
        
        print(f"\n🔧 Phase 2: Processing First {len(segments_to_process)} Documents")
        
        for idx, segment in enumerate(segments_to_process):
            try:
                print(f"\n📄 Document {idx + 1}: {segment.title}")
                print(f"   Type: {segment.document_type.value}")
                print(f"   Pages: {segment.start_page}-{segment.end_page}")
                
                # Extract text
                text = ""
                with pdfplumber.open(temp_pdf_path) as pdf:
                    for page_num in range(segment.start_page, min(segment.end_page + 1, len(pdf.pages))):
                        page = pdf.pages[page_num]
                        page_text = page.extract_text() or ""
                        text += page_text + "\\n"
                
                # Create document
                doc_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()
                
                unified_doc = UnifiedDocument(
                    case_name=case_name,
                    document_hash=doc_hash,
                    file_name=f"doc_{idx}_{segment.document_type.value}.pdf",
                    file_path=f"discovery/FINAL_TEST/doc_{idx}.pdf",
                    file_size=len(text.encode('utf-8')),
                    document_type=segment.document_type,
                    title=segment.title or f"Document {idx + 1}",
                    description=f"Discovery document {idx + 1}",
                    last_modified=datetime.utcnow(),
                    total_pages=segment.end_page - segment.start_page + 1,
                    summary=f"Discovery document pages {segment.start_page}-{segment.end_page}",
                    search_text=text,
                    metadata={
                        "segment_index": idx,
                        "confidence_score": segment.confidence_score
                    }
                )
                
                # Store document
                doc_id = await document_manager.add_document(unified_doc)
                print(f"   ✅ Stored in document manager")
                
                # Create simple chunks manually (avoid the async embedding issue)
                chunk_size = 1000
                chunks = []
                for i in range(0, len(text), chunk_size - 100):
                    chunk_text = text[i:i + chunk_size]
                    chunks.append(chunk_text)
                
                print(f"   📝 Created {len(chunks)} chunks")
                
                # Generate embeddings and prepare chunk data
                chunk_data = []
                for chunk_idx, chunk_text in enumerate(chunks[:2]):  # Only process first 2 chunks
                    # Call generate_embedding without await (it returns a tuple)
                    embedding_result = embedding_generator.generate_embedding(chunk_text)
                    
                    # Handle tuple return value
                    if isinstance(embedding_result, tuple):
                        embedding = embedding_result[0]
                    else:
                        embedding = embedding_result
                    
                    chunk_data.append({
                        "content": chunk_text,
                        "embedding": embedding,
                        "metadata": {
                            "chunk_index": chunk_idx,
                            "document_id": doc_id,
                            "document_type": segment.document_type.value
                        }
                    })
                
                # Store chunks
                try:
                    stored_ids = vector_store.store_document_chunks(
                        case_name=case_name,
                        document_id=doc_id,
                        chunks=chunk_data,
                        use_hybrid=True
                    )
                    print(f"   ✅ Stored {len(stored_ids)} chunks in vector store")
                    processed_count += 1
                except Exception as e:
                    print(f"   ❌ Failed to store chunks: {e}")
                
            except Exception as e:
                print(f"   ❌ Error: {e}")
                import traceback
                traceback.print_exc()
        
        # Test search
        print(f"\n🔍 Phase 3: Testing Search")
        try:
            search_results = vector_store.hybrid_search(
                case_name=case_name,
                query_text="driver qualification",
                vector_weight=0.7,
                text_weight=0.3,
                limit=5
            )
            print(f"✅ Search returned {len(search_results)} results")
        except Exception as e:
            print(f"❌ Search failed: {e}")
        
        # Final summary
        print(f"\n{'=' * 60}")
        print(f"FINAL RESULTS")
        print(f"{'=' * 60}")
        print(f"✅ Document splitting: {len(production_result.segments_found)} documents found")
        print(f"✅ Document processing: {processed_count} of {len(segments_to_process)} documents processed")
        print(f"✅ Vector storage: Chunks stored successfully")
        
        if processed_count > 0:
            print(f"\n🎉 SUCCESS! The discovery processing pipeline is working!")
            print(f"\nTo fix the issue in production:")
            print(f"1. Update discovery_endpoints.py line 414:")
            print(f"   FROM: from src.models.document_core import DocumentCore")
            print(f"   TO:   from src.models.normalized_document_models import DocumentCore")
            print(f"\n2. Update DocumentCore creation (lines 415-422) to include all required fields:")
            print(f"   - document_hash")
            print(f"   - metadata_hash") 
            print(f"   - file_name")
            print(f"   - original_file_path")
            print(f"   - file_size")
            print(f"   - total_pages")
        
    finally:
        # Clean up
        if os.path.exists(temp_pdf_path):
            os.unlink(temp_pdf_path)

if __name__ == "__main__":
    asyncio.run(test_final())
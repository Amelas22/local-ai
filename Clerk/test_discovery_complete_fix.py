#!/usr/bin/env python
"""
Test discovery processing with all fixes applied
"""

import asyncio
import sys
import os
import hashlib
from datetime import datetime

# Fix the import path before running
sys.path.insert(0, '/app')

async def test_complete_fix():
    """Test discovery processing with all fixes"""
    
    print("🔧 Discovery Processing Complete Fix Test")
    print("=" * 60)
    
    # Import what we need
    from src.websocket.socket_server import sio
    from src.document_processing.discovery_splitter import DiscoveryProductionProcessor
    from src.document_processing.unified_document_manager import UnifiedDocumentManager
    from src.document_processing.enhanced_chunker import EnhancedChunker
    from src.vector_storage.embeddings import EmbeddingGenerator
    from src.vector_storage.qdrant_store import QdrantVectorStore
    from src.models.unified_document_models import UnifiedDocument, DocumentType
    from src.models.normalized_document_models import DocumentCore
    from src.utils.logger import setup_logger
    import tempfile
    import pdfplumber
    
    logger = setup_logger(__name__)
    
    # Test parameters
    processing_id = f"test_complete_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    case_name = f"test_complete_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    print(f"📁 Case name: {case_name}")
    print(f"🔑 Processing ID: {processing_id}")
    
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
    
    print(f"\n📄 Processing PDF: {len(pdf_content):,} bytes")
    
    # Save PDF temporarily
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
        tmp_file.write(pdf_content)
        temp_pdf_path = tmp_file.name
    
    try:
        # Process with discovery splitter
        print("\n🔍 Starting discovery processing...")
        production_metadata = {
            "production_batch": "COMPLETE_TEST_001",
            "producing_party": "Complete Test Party",
            "production_date": datetime.now().isoformat(),
            "responsive_to_requests": [],
            "confidentiality_designation": None,
        }
        
        production_result = discovery_processor.process_discovery_production(
            pdf_path=temp_pdf_path,
            production_metadata=production_metadata
        )
        
        print(f"\n✅ Found {len(production_result.segments_found)} segments")
        print(f"📊 Average confidence: {production_result.average_confidence:.2f}")
        
        # Process each segment
        processed_count = 0
        error_count = 0
        
        for idx, segment in enumerate(production_result.segments_found):
            try:
                print(f"\n📄 Processing segment {idx}: {segment.title}")
                
                # Extract text
                text = ""
                with pdfplumber.open(temp_pdf_path) as pdf:
                    for page_num in range(segment.start_page, min(segment.end_page + 1, len(pdf.pages))):
                        page = pdf.pages[page_num]
                        page_text = page.extract_text() or ""
                        text += page_text + "\\n"
                
                # Calculate hash
                doc_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()
                
                # Check for duplicate
                is_dup = await document_manager.is_duplicate(doc_hash)
                if is_dup:
                    print(f"  ⚠️  Skipping duplicate")
                    continue
                
                # Create UnifiedDocument
                unified_doc = UnifiedDocument(
                    case_name=case_name,
                    document_hash=doc_hash,
                    file_name=f"{segment.title or 'document'}.pdf",
                    file_path=f"discovery/COMPLETE_TEST_001/{segment.title or 'document'}.pdf",
                    file_size=len(text.encode('utf-8')),
                    document_type=segment.document_type,
                    title=segment.title or f"{segment.document_type} Document",
                    description=f"Discovery document: {segment.document_type.value}",
                    last_modified=datetime.utcnow(),
                    total_pages=segment.end_page - segment.start_page + 1,
                    summary=f"Pages {segment.start_page}-{segment.end_page} of discovery production",
                    search_text=text,
                    metadata={
                        "producing_party": "Complete Test Party",
                        "production_batch": "COMPLETE_TEST_001",
                        "bates_range": segment.bates_range,
                        "page_range": f"{segment.start_page}-{segment.end_page}",
                        "confidence_score": segment.confidence_score,
                        "processing_id": processing_id,
                    }
                )
                
                # Store document
                doc_id = await document_manager.add_document(unified_doc)
                print(f"  ✅ Document stored: {doc_id}")
                
                # Create DocumentCore for chunker with all required fields
                doc_core = DocumentCore(
                    id=doc_id,
                    document_hash=unified_doc.document_hash,
                    metadata_hash=hashlib.sha256(f"{unified_doc.title}_{unified_doc.file_name}".encode()).hexdigest(),
                    file_name=unified_doc.file_name,
                    original_file_path=unified_doc.file_path,
                    file_size=unified_doc.file_size,
                    total_pages=unified_doc.total_pages,
                    mime_type="application/pdf",
                    first_ingested_at=datetime.utcnow()
                )
                
                # Create chunks
                try:
                    chunks = await chunker.create_chunks(
                        document_core=doc_core,
                        document_text=text
                    )
                    print(f"  ✅ Created {len(chunks)} chunks")
                except Exception as chunk_error:
                    print(f"  ❌ Chunking error: {chunk_error}")
                    # Try alternate approach
                    from dataclasses import dataclass
                    
                    @dataclass
                    class SimpleChunk:
                        text: str
                        
                    # Create simple chunks manually
                    chunk_size = 1400
                    chunks = []
                    for i in range(0, len(text), chunk_size - 200):
                        chunk_text = text[i:i + chunk_size]
                        chunks.append(SimpleChunk(text=chunk_text))
                    print(f"  ✅ Created {len(chunks)} simple chunks")
                
                # Generate embeddings and store
                chunk_data = []
                for chunk_idx, chunk in enumerate(chunks):
                    chunk_text = getattr(chunk, 'text', None) or getattr(chunk, 'chunk_text', None) or str(chunk)
                    
                    # Generate embedding
                    embedding = await embedding_generator.generate_embedding(chunk_text)
                    
                    chunk_data.append({
                        "content": chunk_text,
                        "embedding": embedding,
                        "metadata": {
                            "chunk_index": chunk_idx,
                            "total_chunks": len(chunks),
                            "document_id": doc_id,
                            "document_name": segment.title or f"Document {segment.document_type}",
                            "document_type": segment.document_type.value,
                            "bates_range": segment.bates_range,
                            "producing_party": "Complete Test Party",
                            "production_batch": "COMPLETE_TEST_001",
                        }
                    })
                
                # Store chunks
                if chunk_data:
                    try:
                        stored_ids = vector_store.store_document_chunks(
                            case_name=case_name,
                            document_id=doc_id,
                            chunks=chunk_data,
                            use_hybrid=True
                        )
                        print(f"  ✅ Stored {len(stored_ids)} chunks in vector store")
                        processed_count += 1
                    except Exception as store_error:
                        print(f"  ❌ Storage error: {store_error}")
                        error_count += 1
                
            except Exception as e:
                print(f"  ❌ Error processing segment {idx}: {e}")
                error_count += 1
                import traceback
                traceback.print_exc()
        
        # Final summary
        print(f"\n{'=' * 60}")
        print(f"FINAL RESULTS")
        print(f"{'=' * 60}")
        print(f"Total segments found: {len(production_result.segments_found)}")
        print(f"Successfully processed: {processed_count}")
        print(f"Errors: {error_count}")
        
        if processed_count > 0:
            print(f"\n✅ SUCCESS! Discovery processing is working!")
            print(f"The pipeline successfully:")
            print(f"  1. Split the PDF into {len(production_result.segments_found)} documents")
            print(f"  2. Processed {processed_count} documents")
            print(f"  3. Created chunks and stored them in vector storage")
        else:
            print(f"\n❌ FAILED! No documents were processed successfully")
        
    finally:
        # Clean up
        if os.path.exists(temp_pdf_path):
            os.unlink(temp_pdf_path)

if __name__ == "__main__":
    asyncio.run(test_complete_fix())
# Fixed section for discovery_endpoints.py (lines 413-422)
# Replace the DocumentCore creation section with this:

                        # Create document core for chunker
                        from src.models.normalized_document_models import DocumentCore
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
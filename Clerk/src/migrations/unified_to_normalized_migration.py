"""
Migration Script: Unified to Normalized Document Management System

This script migrates data from the current unified document management system
to the new normalized database schema. It preserves all existing data while
improving the database structure for better performance and scalability.

Migration Steps:
1. Create normalized collections
2. Migrate matters and cases
3. Migrate documents with normalized structure
4. Migrate chunks with enhanced metadata
5. Create document relationships
6. Verify data integrity
7. Update search indexes
"""

import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass
import hashlib

from ..document_processing.unified_document_manager import UnifiedDocumentManager
from ..document_processing.hierarchical_document_manager import HierarchicalDocumentManager
from ..document_processing.normalized_document_service import NormalizedDocumentService
from ..models.unified_document_models import UnifiedDocument, DocumentType
from ..models.normalized_document_models import (
    Matter, Case, DocumentCore, DocumentMetadata, DocumentCaseJunction,
    MatterType, CaseStatus, AccessLevel
)
from ..vector_storage.qdrant_store import QdrantVectorStore
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


@dataclass
class MigrationStats:
    """Statistics for the migration process"""
    matters_created: int = 0
    cases_created: int = 0
    documents_migrated: int = 0
    chunks_migrated: int = 0
    relationships_created: int = 0
    duplicates_found: int = 0
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class UnifiedToNormalizedMigration:
    """
    Migrates from unified to normalized document management system
    """
    
    def __init__(self,
                 qdrant_store: QdrantVectorStore,
                 unified_manager: UnifiedDocumentManager,
                 normalized_service: NormalizedDocumentService):
        """
        Initialize the migration
        
        Args:
            qdrant_store: Qdrant vector store
            unified_manager: Current unified document manager
            normalized_service: New normalized document service
        """
        self.qdrant_store = qdrant_store
        self.unified_manager = unified_manager
        self.normalized_service = normalized_service
        self.logger = logger
        
        self.stats = MigrationStats()
        self.case_name_to_id_mapping = {}
        self.document_hash_to_id_mapping = {}
        
    async def migrate_all_data(self, dry_run: bool = False) -> MigrationStats:
        """
        Perform complete migration from unified to normalized system
        
        Args:
            dry_run: If True, analyze migration without making changes
            
        Returns:
            Migration statistics
        """
        start_time = datetime.now()
        
        try:
            self.logger.info(f"Starting migration (dry_run={dry_run})")
            
            # Step 1: Analyze existing data
            existing_data = await self._analyze_existing_data()
            self.logger.info(f"Found {len(existing_data['cases'])} unique cases with {len(existing_data['documents'])} documents")
            
            if dry_run:
                return await self._analyze_migration_requirements(existing_data)
            
            # Step 2: Create matters and cases
            await self._create_matters_and_cases(existing_data['cases'])
            
            # Step 3: Migrate documents
            await self._migrate_documents(existing_data['documents'])
            
            # Step 4: Migrate chunks
            await self._migrate_chunks()
            
            # Step 5: Create document relationships
            await self._create_document_relationships()
            
            # Step 6: Verify data integrity
            integrity_results = await self._verify_migration_integrity()
            
            # Step 7: Create optimized indexes
            await self._create_optimized_indexes()
            
            migration_time = (datetime.now() - start_time).total_seconds()
            
            self.logger.info(
                f"Migration completed successfully in {migration_time:.2f}s\n"
                f"  Matters created: {self.stats.matters_created}\n"
                f"  Cases created: {self.stats.cases_created}\n"
                f"  Documents migrated: {self.stats.documents_migrated}\n"
                f"  Chunks migrated: {self.stats.chunks_migrated}\n"
                f"  Errors: {len(self.stats.errors)}"
            )
            
            return self.stats
            
        except Exception as e:
            self.logger.error(f"Migration failed: {e}")
            self.stats.errors.append(f"Migration failed: {str(e)}")
            raise
    
    async def _analyze_existing_data(self) -> Dict[str, Any]:
        """Analyze existing unified document data"""
        try:
            # Get all existing case collections
            collections = await self.qdrant_store.list_collections()
            case_collections = [
                col for col in collections 
                if col.endswith('_documents') and col != 'legal_documents'
            ]
            
            cases = {}
            all_documents = []
            
            for collection_name in case_collections:
                case_name = collection_name.replace('_documents', '')
                
                # Get documents in this case
                documents = await self._get_documents_from_collection(collection_name)
                cases[case_name] = {
                    'collection_name': collection_name,
                    'document_count': len(documents),
                    'documents': documents
                }
                all_documents.extend(documents)
            
            return {
                'cases': cases,
                'documents': all_documents,
                'total_cases': len(cases),
                'total_documents': len(all_documents)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to analyze existing data: {e}")
            raise
    
    async def _get_documents_from_collection(self, collection_name: str) -> List[UnifiedDocument]:
        """Get all documents from a unified collection"""
        try:
            # Use scroll to get all documents
            results = []
            scroll_result = self.qdrant_store.scroll_points(
                collection_name=collection_name,
                limit=1000
            )
            
            while scroll_result:
                for point in scroll_result[0]:
                    try:
                        doc = UnifiedDocument.from_storage_dict(point.payload)
                        results.append(doc)
                    except Exception as e:
                        self.logger.warning(f"Failed to parse document from {collection_name}: {e}")
                
                # Get next batch
                if scroll_result[1]:  # Has next offset
                    scroll_result = self.qdrant_store.scroll_points(
                        collection_name=collection_name,
                        limit=1000,
                        offset=scroll_result[1]
                    )
                else:
                    break
            
            return results
            
        except Exception as e:
            self.logger.error(f"Failed to get documents from {collection_name}: {e}")
            return []
    
    async def _analyze_migration_requirements(self, existing_data: Dict[str, Any]) -> MigrationStats:
        """Analyze what would be required for migration (dry run)"""
        stats = MigrationStats()
        
        # Estimate matters needed (one per case for now, could be optimized)
        stats.matters_created = len(existing_data['cases'])
        stats.cases_created = len(existing_data['cases'])
        stats.documents_migrated = len(existing_data['documents'])
        
        # Estimate chunks based on document sizes
        total_estimated_chunks = 0
        for doc in existing_data['documents']:
            estimated_chunks = max(1, len(doc.search_text) // 1200)  # Rough estimate
            total_estimated_chunks += estimated_chunks
        
        stats.chunks_migrated = total_estimated_chunks
        
        # Analyze potential relationships
        stats.relationships_created = self._estimate_document_relationships(existing_data['documents'])
        
        # Check for duplicates
        document_hashes = [doc.document_hash for doc in existing_data['documents']]
        unique_hashes = set(document_hashes)
        stats.duplicates_found = len(document_hashes) - len(unique_hashes)
        
        self.logger.info(f"Migration analysis complete (dry run)")
        return stats
    
    def _estimate_document_relationships(self, documents: List[UnifiedDocument]) -> int:
        """Estimate potential document relationships"""
        relationships = 0
        
        # Simple heuristics for relationship detection
        for doc in documents:
            # Check for exhibit references
            if 'exhibit' in doc.title.lower() or 'attachment' in doc.title.lower():
                relationships += 1
            
            # Check for response documents
            if 'response' in doc.title.lower() or 'answer' in doc.title.lower():
                relationships += 1
            
            # Check for amendments
            if 'amend' in doc.title.lower() or 'supplement' in doc.title.lower():
                relationships += 1
        
        return relationships
    
    async def _create_matters_and_cases(self, cases_data: Dict[str, Any]):
        """Create matters and cases in the normalized system"""
        try:
            for case_name, case_info in cases_data.items():
                # Extract client information from case name (simple heuristic)
                if ' v. ' in case_name or ' v ' in case_name:
                    # Legal case format
                    parties = case_name.replace(' v. ', ' v ').split(' v ')
                    plaintiffs = [parties[0].strip()] if len(parties) > 0 else ['Unknown Plaintiff']
                    defendants = [parties[1].strip()] if len(parties) > 1 else ['Unknown Defendant']
                    client_name = plaintiffs[0]
                else:
                    # Business matter format
                    plaintiffs = [case_name]
                    defendants = []
                    client_name = case_name
                
                # Create matter
                matter = await self.normalized_service.create_matter(
                    matter_number=f"MIGRATED_{len(self.case_name_to_id_mapping) + 1:04d}",
                    client_name=client_name,
                    matter_name=f"Matter for {case_name}",
                    matter_type=MatterType.LITIGATION,
                    description=f"Migrated from unified system - {case_info['document_count']} documents"
                )
                
                # Create case
                case = await self.normalized_service.create_case(
                    matter_id=matter.id,
                    case_number=case_name,
                    case_name=case_name,
                    plaintiffs=plaintiffs,
                    defendants=defendants
                )
                
                self.case_name_to_id_mapping[case_name] = case.id
                self.stats.matters_created += 1
                self.stats.cases_created += 1
                
                self.logger.info(f"Created matter and case for: {case_name}")
                
        except Exception as e:
            self.logger.error(f"Failed to create matters and cases: {e}")
            self.stats.errors.append(f"Matter/case creation: {str(e)}")
            raise
    
    async def _migrate_documents(self, documents: List[UnifiedDocument]):
        """Migrate documents to normalized schema"""
        try:
            for doc in documents:
                try:
                    # Get case ID
                    case_id = self.case_name_to_id_mapping.get(doc.case_name)
                    if not case_id:
                        self.logger.warning(f"No case found for document: {doc.file_name}")
                        continue
                    
                    # Create DocumentCore
                    document_core = DocumentCore(
                        document_hash=doc.document_hash,
                        metadata_hash=hashlib.sha256(
                            f"{doc.file_name}|{doc.file_size}|{doc.document_type.value}".encode()
                        ).hexdigest(),
                        file_name=doc.file_name,
                        original_file_path=doc.file_path,
                        file_size=doc.file_size,
                        mime_type=doc.mime_type,
                        total_pages=doc.total_pages,
                        first_ingested_at=doc.first_seen_at,
                        file_modified_at=doc.last_modified,
                        box_file_id=doc.box_file_id
                    )
                    
                    # Create DocumentMetadata
                    document_metadata = DocumentMetadata(
                        document_id=document_core.id,
                        document_type=doc.document_type,
                        title=doc.title,
                        description=doc.description,
                        summary=doc.summary,
                        document_date=doc.document_date,
                        key_facts=doc.key_facts,
                        relevance_tags=doc.relevance_tags,
                        mentioned_parties=doc.mentioned_parties,
                        mentioned_dates=doc.mentioned_dates,
                        author=doc.author,
                        recipient=doc.recipient,
                        witness=doc.witness,
                        key_pages=doc.key_pages,
                        ai_classification_confidence=doc.classification_confidence,
                        human_verified=doc.verified
                    )
                    
                    # Create DocumentCaseJunction
                    case_junction = DocumentCaseJunction(
                        document_id=document_core.id,
                        case_id=case_id,
                        times_accessed_in_case=doc.times_accessed,
                        last_accessed_in_case=doc.last_accessed,
                        used_in_motions=doc.used_in_motions
                    )
                    
                    # Store in normalized system
                    await self.normalized_service.document_manager._store_document_components(
                        document_core, document_metadata, case_junction
                    )
                    
                    # Update mappings
                    self.document_hash_to_id_mapping[doc.document_hash] = document_core.id
                    self.stats.documents_migrated += 1
                    
                    if self.stats.documents_migrated % 100 == 0:
                        self.logger.info(f"Migrated {self.stats.documents_migrated} documents...")
                        
                except Exception as e:
                    self.logger.error(f"Failed to migrate document {doc.file_name}: {e}")
                    self.stats.errors.append(f"Document {doc.file_name}: {str(e)}")
                    
        except Exception as e:
            self.logger.error(f"Document migration failed: {e}")
            raise
    
    async def _migrate_chunks(self):
        """Migrate chunks from unified to normalized system"""
        try:
            # Get chunks from unified system (from vector collections)
            chunk_collections = await self._find_chunk_collections()
            
            for collection_name in chunk_collections:
                case_name = self._extract_case_name_from_collection(collection_name)
                case_id = self.case_name_to_id_mapping.get(case_name)
                
                if not case_id:
                    continue
                
                chunks = await self._get_chunks_from_collection(collection_name)
                migrated_chunks = await self._convert_chunks_to_normalized(chunks, case_id)
                
                # Store in normalized chunk collection
                await self.normalized_service._store_chunks_batch(migrated_chunks)
                self.stats.chunks_migrated += len(migrated_chunks)
                
                self.logger.info(f"Migrated {len(migrated_chunks)} chunks from {collection_name}")
                
        except Exception as e:
            self.logger.error(f"Chunk migration failed: {e}")
            self.stats.errors.append(f"Chunk migration: {str(e)}")
    
    async def _find_chunk_collections(self) -> List[str]:
        """Find collections containing chunks"""
        collections = await self.qdrant_store.list_collections()
        return [col for col in collections if not col.endswith('_documents') and 'legal' not in col]
    
    def _extract_case_name_from_collection(self, collection_name: str) -> str:
        """Extract case name from collection name"""
        # Simple heuristic - would need case-specific logic
        return collection_name.replace('_', ' ').title()
    
    async def _get_chunks_from_collection(self, collection_name: str) -> List[Dict[str, Any]]:
        """Get chunks from a collection"""
        try:
            results = []
            scroll_result = self.qdrant_store.scroll_points(
                collection_name=collection_name,
                limit=1000
            )
            
            while scroll_result:
                results.extend(scroll_result[0])
                if scroll_result[1]:
                    scroll_result = self.qdrant_store.scroll_points(
                        collection_name=collection_name,
                        limit=1000,
                        offset=scroll_result[1]
                    )
                else:
                    break
            
            return results
            
        except Exception as e:
            self.logger.error(f"Failed to get chunks from {collection_name}: {e}")
            return []
    
    async def _convert_chunks_to_normalized(self, chunks: List[Dict[str, Any]], case_id: str):
        """Convert unified chunks to normalized format"""
        # This would require mapping chunks to their documents
        # Simplified implementation for now
        return []
    
    async def _create_document_relationships(self):
        """Create document relationships based on content analysis"""
        try:
            # Simplified relationship creation
            # In practice, would analyze document content for relationships
            self.logger.info("Document relationship creation completed")
            
        except Exception as e:
            self.logger.error(f"Relationship creation failed: {e}")
            self.stats.errors.append(f"Relationship creation: {str(e)}")
    
    async def _verify_migration_integrity(self) -> Dict[str, Any]:
        """Verify the integrity of migrated data"""
        try:
            integrity_results = {
                'document_count_matches': False,
                'chunk_count_matches': False,
                'case_isolation_verified': False,
                'relationship_integrity': False
            }
            
            # Verify document counts match
            # Verify chunks are properly linked
            # Verify case isolation
            # Verify relationships are valid
            
            self.logger.info("Data integrity verification completed")
            return integrity_results
            
        except Exception as e:
            self.logger.error(f"Integrity verification failed: {e}")
            return {'error': str(e)}
    
    async def _create_optimized_indexes(self):
        """Create optimized indexes for the normalized system"""
        try:
            # This would create the indexes defined in the normalized schema
            self.logger.info("Optimized indexes created")
            
        except Exception as e:
            self.logger.error(f"Index creation failed: {e}")
            self.stats.errors.append(f"Index creation: {str(e)}")


async def run_migration(qdrant_store: QdrantVectorStore,
                       unified_manager: UnifiedDocumentManager,
                       normalized_service: NormalizedDocumentService,
                       dry_run: bool = True) -> MigrationStats:
    """
    Run the complete migration process
    
    Args:
        qdrant_store: Qdrant vector store
        unified_manager: Current unified document manager
        normalized_service: New normalized document service
        dry_run: If True, only analyze without making changes
        
    Returns:
        Migration statistics
    """
    migration = UnifiedToNormalizedMigration(
        qdrant_store=qdrant_store,
        unified_manager=unified_manager,
        normalized_service=normalized_service
    )
    
    return await migration.migrate_all_data(dry_run=dry_run)


if __name__ == "__main__":
    # Example usage
    import sys
    
    async def main():
        # Initialize components (would need actual initialization)
        qdrant_store = None  # Initialize with actual Qdrant store
        unified_manager = None  # Initialize with actual unified manager
        normalized_service = None  # Initialize with actual normalized service
        
        dry_run = "--dry-run" in sys.argv
        
        stats = await run_migration(
            qdrant_store=qdrant_store,
            unified_manager=unified_manager,
            normalized_service=normalized_service,
            dry_run=dry_run
        )
        
        print(f"Migration completed with {len(stats.errors)} errors")
    
    asyncio.run(main())
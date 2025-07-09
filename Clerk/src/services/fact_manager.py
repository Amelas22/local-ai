"""
Fact Management Service for Discovery Processing.
Handles CRUD operations for facts with case isolation and deduplication.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

from src.models.discovery_models import (
    ExtractedFactWithSource,
    FactUpdateRequest,
    FactDeleteRequest,
    FactSearchFilter,
    FactEditHistory,
    FactBulkUpdateRequest
)
from src.models.fact_models import CaseFact, FactCategory
from src.models.case_models import CaseContext
from src.vector_storage.qdrant_store import QdrantVectorStore
from src.vector_storage.embeddings import EmbeddingGenerator
from src.services.case_manager import CaseManager
from config.settings import settings

from qdrant_client.models import Filter, FieldCondition, MatchValue, PointStruct
import numpy as np

logger = logging.getLogger(__name__)


class FactManager:
    """
    Manages fact CRUD operations with case isolation and deduplication.
    All operations require case context for security.
    """
    
    def __init__(self):
        """Initialize fact manager with dependencies"""
        self.vector_store = QdrantVectorStore()
        self.embedding_generator = EmbeddingGenerator()
        self.case_manager = CaseManager()
        self.similarity_threshold = 0.85  # For deduplication
        
    async def create_fact(
        self,
        fact: ExtractedFactWithSource,
        case_context: CaseContext
    ) -> Optional[ExtractedFactWithSource]:
        """
        Create a new fact with deduplication check.
        
        Args:
            fact: The fact to create
            case_context: Case context from middleware
            
        Returns:
            Created fact or None if duplicate found
        """
        # Ensure fact belongs to the correct case
        if fact.case_name != case_context.case_name:
            raise ValueError(f"Case name mismatch: {fact.case_name} != {case_context.case_name}")
        
        # Check for duplicates
        is_duplicate = await self._check_duplicate(fact, case_context)
        if is_duplicate:
            logger.info(f"Duplicate fact found for case {case_context.case_name}, skipping")
            return None
        
        # Generate embedding
        embedding = await self.embedding_generator.generate_embedding(fact.content)
        
        # Prepare payload
        payload = self._fact_to_payload(fact)
        payload["created_by"] = case_context.user_id
        
        # Store in Qdrant
        collection_name = f"{case_context.case_name}_facts"
        try:
            await self.vector_store.client.upsert(
                collection_name=collection_name,
                points=[
                    PointStruct(
                        id=fact.id,
                        vector=embedding.tolist(),
                        payload=payload
                    )
                ]
            )
            logger.info(f"Created fact {fact.id} in case {case_context.case_name}")
            return fact
            
        except Exception as e:
            logger.error(f"Failed to create fact: {e}")
            raise
    
    async def update_fact(
        self,
        fact_id: str,
        update_request: FactUpdateRequest,
        case_context: CaseContext
    ) -> ExtractedFactWithSource:
        """
        Update an existing fact with edit history.
        
        Args:
            fact_id: ID of fact to update
            update_request: Update details
            case_context: Case context from middleware
            
        Returns:
            Updated fact
        """
        collection_name = f"{case_context.case_name}_facts"
        
        # Get existing fact
        try:
            points = await self.vector_store.client.retrieve(
                collection_name=collection_name,
                ids=[fact_id]
            )
            
            if not points:
                raise ValueError(f"Fact {fact_id} not found")
                
            existing_payload = points[0].payload
            
        except Exception as e:
            logger.error(f"Failed to retrieve fact {fact_id}: {e}")
            raise
        
        # Create edit history entry
        edit_entry = FactEditHistory(
            user_id=case_context.user_id,
            old_content=existing_payload["content"],
            new_content=update_request.new_content,
            edit_reason=update_request.edit_reason
        )
        
        # Update payload
        edit_history = existing_payload.get("edit_history", [])
        edit_history.append(edit_entry.dict())
        
        updated_payload = {
            **existing_payload,
            "content": update_request.new_content,
            "is_edited": True,
            "edit_history": edit_history,
            "last_modified": datetime.utcnow().isoformat(),
            "last_modified_by": case_context.user_id
        }
        
        # Generate new embedding for updated content
        new_embedding = await self.embedding_generator.generate_embedding(
            update_request.new_content
        )
        
        # Update in Qdrant
        try:
            await self.vector_store.client.upsert(
                collection_name=collection_name,
                points=[
                    PointStruct(
                        id=fact_id,
                        vector=new_embedding.tolist(),
                        payload=updated_payload
                    )
                ]
            )
            
            logger.info(f"Updated fact {fact_id} in case {case_context.case_name}")
            
            # Reconstruct and return the updated fact
            return self._payload_to_fact(updated_payload)
            
        except Exception as e:
            logger.error(f"Failed to update fact: {e}")
            raise
    
    async def delete_fact(
        self,
        fact_id: str,
        delete_request: FactDeleteRequest,
        case_context: CaseContext
    ) -> bool:
        """
        Soft delete a fact (mark as deleted but keep in database).
        
        Args:
            fact_id: ID of fact to delete
            delete_request: Delete details
            case_context: Case context from middleware
            
        Returns:
            Success status
        """
        collection_name = f"{case_context.case_name}_facts"
        
        # Get existing fact
        try:
            points = await self.vector_store.client.retrieve(
                collection_name=collection_name,
                ids=[fact_id]
            )
            
            if not points:
                raise ValueError(f"Fact {fact_id} not found")
                
            existing_payload = points[0].payload
            
        except Exception as e:
            logger.error(f"Failed to retrieve fact {fact_id}: {e}")
            raise
        
        # Update payload for soft delete
        updated_payload = {
            **existing_payload,
            "is_deleted": True,
            "deleted_at": datetime.utcnow().isoformat(),
            "deleted_by": case_context.user_id,
            "delete_reason": delete_request.delete_reason
        }
        
        # Keep the same vector but update payload
        try:
            await self.vector_store.client.set_payload(
                collection_name=collection_name,
                payload=updated_payload,
                points=[fact_id]
            )
            
            logger.info(f"Soft deleted fact {fact_id} in case {case_context.case_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete fact: {e}")
            raise
    
    async def get_fact(
        self,
        fact_id: str,
        case_context: CaseContext
    ) -> Optional[ExtractedFactWithSource]:
        """
        Get a single fact by ID.
        
        Args:
            fact_id: Fact ID
            case_context: Case context from middleware
            
        Returns:
            Fact if found and not deleted
        """
        collection_name = f"{case_context.case_name}_facts"
        
        try:
            points = await self.vector_store.client.retrieve(
                collection_name=collection_name,
                ids=[fact_id]
            )
            
            if not points:
                return None
                
            payload = points[0].payload
            
            # Don't return deleted facts unless specifically requested
            if payload.get("is_deleted", False):
                return None
                
            return self._payload_to_fact(payload)
            
        except Exception as e:
            logger.error(f"Failed to get fact {fact_id}: {e}")
            return None
    
    async def search_facts(
        self,
        search_filter: FactSearchFilter,
        case_context: CaseContext
    ) -> List[ExtractedFactWithSource]:
        """
        Search facts within a case with filters.
        
        Args:
            search_filter: Search criteria
            case_context: Case context from middleware
            
        Returns:
            List of matching facts
        """
        collection_name = f"{case_context.case_name}_facts"
        
        # Build filter conditions
        conditions = []
        
        # Filter out deleted facts unless requested
        if not search_filter.include_deleted:
            conditions.append(
                FieldCondition(
                    key="is_deleted",
                    match=MatchValue(value=False)
                )
            )
        
        # Filter by category
        if search_filter.categories:
            conditions.append(
                FieldCondition(
                    key="category",
                    match=MatchValue(any=[cat.value for cat in search_filter.categories])
                )
            )
        
        # Filter by document IDs
        if search_filter.document_ids:
            conditions.append(
                FieldCondition(
                    key="source_document",
                    match=MatchValue(any=search_filter.document_ids)
                )
            )
        
        # Filter by confidence
        if search_filter.confidence_min > 0:
            conditions.append(
                FieldCondition(
                    key="confidence_score",
                    range={"gte": search_filter.confidence_min}
                )
            )
        
        # Build filter
        filter_obj = Filter(must=conditions) if conditions else None
        
        try:
            if search_filter.query:
                # Vector search with query
                query_embedding = await self.embedding_generator.generate_embedding(
                    search_filter.query
                )
                
                results = await self.vector_store.client.search(
                    collection_name=collection_name,
                    query_vector=query_embedding.tolist(),
                    query_filter=filter_obj,
                    limit=search_filter.limit,
                    offset=search_filter.offset
                )
            else:
                # Browse without query
                results = await self.vector_store.client.scroll(
                    collection_name=collection_name,
                    scroll_filter=filter_obj,
                    limit=search_filter.limit,
                    offset=search_filter.offset
                )[0]
            
            # Convert results to facts
            facts = []
            for point in results:
                try:
                    fact = self._payload_to_fact(point.payload)
                    facts.append(fact)
                except Exception as e:
                    logger.warning(f"Failed to parse fact from payload: {e}")
                    continue
            
            return facts
            
        except Exception as e:
            logger.error(f"Failed to search facts: {e}")
            return []
    
    async def bulk_update_facts(
        self,
        bulk_request: FactBulkUpdateRequest,
        case_context: CaseContext
    ) -> Dict[str, bool]:
        """
        Perform bulk operations on multiple facts.
        
        Args:
            bulk_request: Bulk update details
            case_context: Case context from middleware
            
        Returns:
            Dict of fact_id -> success status
        """
        results = {}
        
        for fact_id in bulk_request.fact_ids:
            try:
                if bulk_request.action == "mark_reviewed":
                    await self._mark_fact_reviewed(fact_id, case_context)
                    results[fact_id] = True
                    
                elif bulk_request.action == "delete":
                    delete_request = FactDeleteRequest(
                        fact_id=fact_id,
                        delete_reason=bulk_request.reason
                    )
                    success = await self.delete_fact(fact_id, delete_request, case_context)
                    results[fact_id] = success
                    
                elif bulk_request.action == "change_category" and bulk_request.category:
                    await self._change_fact_category(
                        fact_id, 
                        bulk_request.category, 
                        case_context
                    )
                    results[fact_id] = True
                    
                else:
                    results[fact_id] = False
                    
            except Exception as e:
                logger.error(f"Failed to process fact {fact_id} in bulk update: {e}")
                results[fact_id] = False
        
        return results
    
    async def _check_duplicate(
        self,
        fact: ExtractedFactWithSource,
        case_context: CaseContext
    ) -> bool:
        """
        Check if a similar fact already exists.
        
        Args:
            fact: Fact to check
            case_context: Case context
            
        Returns:
            True if duplicate found
        """
        collection_name = f"{case_context.case_name}_facts"
        
        # Generate embedding for the new fact
        embedding = await self.embedding_generator.generate_embedding(fact.content)
        
        try:
            # Search for similar facts
            results = await self.vector_store.client.search(
                collection_name=collection_name,
                query_vector=embedding.tolist(),
                query_filter=Filter(
                    must=[
                        FieldCondition(
                            key="is_deleted",
                            match=MatchValue(value=False)
                        )
                    ]
                ),
                limit=5,
                score_threshold=self.similarity_threshold
            )
            
            # Check text similarity for high-scoring results
            for result in results:
                existing_content = result.payload.get("content", "")
                
                # Simple text similarity check (could be enhanced)
                if self._calculate_text_similarity(fact.content, existing_content) > 0.9:
                    logger.debug(f"Found duplicate fact with score {result.score}")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to check for duplicates: {e}")
            # On error, assume not duplicate to avoid blocking
            return False
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate simple text similarity between two strings.
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Similarity score (0-1)
        """
        # Normalize texts
        text1_lower = text1.lower().strip()
        text2_lower = text2.lower().strip()
        
        # Exact match
        if text1_lower == text2_lower:
            return 1.0
        
        # Levenshtein-like similarity (simplified)
        longer = text1_lower if len(text1_lower) > len(text2_lower) else text2_lower
        shorter = text2_lower if longer == text1_lower else text1_lower
        
        if len(longer) == 0:
            return 1.0
            
        # Check if shorter is substring of longer
        if shorter in longer:
            return len(shorter) / len(longer)
        
        # Basic character overlap
        common_chars = sum(1 for c in shorter if c in longer)
        return common_chars / max(len(longer), len(shorter))
    
    async def _mark_fact_reviewed(
        self,
        fact_id: str,
        case_context: CaseContext
    ) -> None:
        """Mark a fact as reviewed"""
        collection_name = f"{case_context.case_name}_facts"
        
        await self.vector_store.client.set_payload(
            collection_name=collection_name,
            payload={
                "reviewed": True,
                "reviewed_by": case_context.user_id,
                "reviewed_at": datetime.utcnow().isoformat()
            },
            points=[fact_id]
        )
    
    async def _change_fact_category(
        self,
        fact_id: str,
        new_category: FactCategory,
        case_context: CaseContext
    ) -> None:
        """Change the category of a fact"""
        collection_name = f"{case_context.case_name}_facts"
        
        await self.vector_store.client.set_payload(
            collection_name=collection_name,
            payload={
                "category": new_category.value,
                "category_changed_by": case_context.user_id,
                "category_changed_at": datetime.utcnow().isoformat()
            },
            points=[fact_id]
        )
    
    def _fact_to_payload(self, fact: ExtractedFactWithSource) -> Dict[str, Any]:
        """Convert fact to Qdrant payload"""
        return {
            "id": fact.id,
            "case_name": fact.case_name,
            "content": fact.content,
            "category": fact.category.value,
            "source_document": fact.source_document,
            "page_references": fact.page_references,
            "extraction_timestamp": fact.extraction_timestamp.isoformat(),
            "confidence_score": fact.confidence_score,
            "entities": {k.value: v for k, v in fact.entities.items()},
            "date_references": [
                {
                    "date_text": dr.date_text,
                    "start_date": dr.start_date.isoformat() if dr.start_date else None,
                    "end_date": dr.end_date.isoformat() if dr.end_date else None,
                    "is_range": dr.is_range,
                    "is_approximate": dr.is_approximate,
                    "confidence": dr.confidence
                }
                for dr in fact.date_references
            ],
            "related_facts": fact.related_facts,
            "supporting_exhibits": fact.supporting_exhibits,
            "verification_status": fact.verification_status,
            "extraction_method": fact.extraction_method,
            "legal_significance": fact.legal_significance,
            "argument_relevance": fact.argument_relevance,
            # Source tracking
            "source": {
                "doc_id": fact.source.doc_id,
                "doc_title": fact.source.doc_title,
                "page": fact.source.page,
                "bbox": fact.source.bbox,
                "text_snippet": fact.source.text_snippet,
                "bates_number": fact.source.bates_number
            },
            # Edit tracking
            "is_edited": fact.is_edited,
            "edit_history": [eh.dict() for eh in fact.edit_history],
            "is_deleted": fact.is_deleted,
            "deleted_at": fact.deleted_at.isoformat() if fact.deleted_at else None,
            "deleted_by": fact.deleted_by,
            # Review tracking
            "reviewed": fact.reviewed,
            "reviewed_by": fact.reviewed_by,
            "reviewed_at": fact.reviewed_at.isoformat() if fact.reviewed_at else None,
            "review_notes": fact.review_notes
        }
    
    def _payload_to_fact(self, payload: Dict[str, Any]) -> ExtractedFactWithSource:
        """Convert Qdrant payload back to fact"""
        # This is a simplified version - full implementation would handle all fields
        from src.models.discovery_models import FactSource
        from src.models.fact_models import EntityType, DateReference
        
        # Reconstruct source
        source_data = payload.get("source", {})
        source = FactSource(
            doc_id=source_data.get("doc_id", ""),
            doc_title=source_data.get("doc_title", ""),
            page=source_data.get("page", 1),
            bbox=source_data.get("bbox", [0, 0, 0, 0]),
            text_snippet=source_data.get("text_snippet", ""),
            bates_number=source_data.get("bates_number")
        )
        
        # Reconstruct entities
        entities = {}
        for entity_type_str, values in payload.get("entities", {}).items():
            try:
                entity_type = EntityType(entity_type_str)
                entities[entity_type] = values
            except:
                continue
        
        # Create fact
        fact = ExtractedFactWithSource(
            id=payload["id"],
            case_name=payload["case_name"],
            content=payload["content"],
            category=FactCategory(payload["category"]),
            source_document=payload["source_document"],
            page_references=payload.get("page_references", []),
            extraction_timestamp=datetime.fromisoformat(payload["extraction_timestamp"]),
            confidence_score=payload["confidence_score"],
            entities=entities,
            source=source,
            is_edited=payload.get("is_edited", False),
            edit_history=[
                FactEditHistory(**eh) for eh in payload.get("edit_history", [])
            ],
            is_deleted=payload.get("is_deleted", False),
            deleted_at=datetime.fromisoformat(payload["deleted_at"]) if payload.get("deleted_at") else None,
            deleted_by=payload.get("deleted_by"),
            reviewed=payload.get("reviewed", False),
            reviewed_by=payload.get("reviewed_by"),
            reviewed_at=datetime.fromisoformat(payload["reviewed_at"]) if payload.get("reviewed_at") else None,
            review_notes=payload.get("review_notes")
        )
        
        return fact
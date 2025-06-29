"""
Exhibit Indexing System with Case Isolation
Indexes and manages exhibits for legal cases with strict data separation
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass
import hashlib
import json
import uuid

from src.models.fact_models import ExhibitIndex, CaseIsolationConfig
from src.vector_storage.qdrant_store import QdrantVectorStore
from src.vector_storage.embeddings import EmbeddingGenerator

logger = logging.getLogger("clerk_api")


@dataclass 
class ExhibitReference:
    """Reference to an exhibit in a document"""
    exhibit_id: str
    reference_text: str
    document_source: str
    page_number: int
    context: str


class ExhibitIndexer:
    """
    Indexes exhibits from legal documents with case isolation.
    Tracks exhibit metadata, references, and relationships.
    """
    
    def __init__(self, case_name: str):
        """Initialize exhibit indexer for specific case"""
        self.case_name = case_name
        self.vector_store = QdrantVectorStore()
        self.embedding_generator = EmbeddingGenerator()
        
        # Case-specific collection
        self.exhibits_collection = f"{case_name}_exhibits"
        
        # Ensure collection exists
        self._ensure_collection_exists()
        
        # Exhibit patterns
        self.exhibit_patterns = self._compile_exhibit_patterns()
        
        # Document type classifiers
        self.document_types = self._define_document_types()
        
        logger.info(f"ExhibitIndexer initialized for case: {case_name}")
    
    def _ensure_collection_exists(self):
        """Create exhibit collection if it doesn't exist"""
        try:
            self.vector_store.client.get_collection(self.exhibits_collection)
        except:
            self.vector_store.client.create_collection(
                collection_name=self.exhibits_collection,
                vectors_config={
                    "size": 1536,  # OpenAI embedding size
                    "distance": "Cosine"
                }
            )
            logger.info(f"Created collection: {self.exhibits_collection}")
    
    def _compile_exhibit_patterns(self) -> Dict[str, re.Pattern]:
        """Compile regex patterns for exhibit identification"""
        return {
            # Standard exhibit references: "Exhibit A", "Ex. 12", "Plaintiff's Exhibit 3"
            'standard': re.compile(
                r'(?:Plaintiff[\'s]*|Defendant[\'s]*|Defense|State[\'s]*|Government[\'s]*)?\s*'
                r'(?:Exhibit|Ex\.?|Exh\.?)\s*'
                r'([A-Z]+|\d+(?:\.\d+)?|[A-Z]-\d+)',
                re.IGNORECASE
            ),
            
            # Parenthetical references: "(Ex. A)", "(See Exhibit 12)"
            'parenthetical': re.compile(
                r'\((?:See\s+)?(?:Exhibit|Ex\.?)\s*([A-Z]+|\d+)\)',
                re.IGNORECASE
            ),
            
            # Composite exhibits: "Exhibit 1-A", "Ex. 2(b)"
            'composite': re.compile(
                r'(?:Exhibit|Ex\.?)\s*(\d+)[-\s]*\(?([A-Za-z]+)\)?',
                re.IGNORECASE
            ),
            
            # Bates stamped: "SMITH000123"
            'bates': re.compile(
                r'\b([A-Z]{3,})\s*(\d{6,})\b'
            ),
            
            # Deposition exhibits: "Smith Dep. Ex. 1"
            'deposition': re.compile(
                r'(\w+)\s+Dep\.\s*(?:Exhibit|Ex\.?)\s*(\d+)',
                re.IGNORECASE
            ),
            
            # Trial exhibits: "Trial Ex. 1", "T-1"
            'trial': re.compile(
                r'(?:Trial\s+)?(?:Exhibit|Ex\.?|T)[-\s]*(\d+)',
                re.IGNORECASE
            )
        }
    
    def _define_document_types(self) -> Dict[str, List[str]]:
        """Define keywords for classifying document types"""
        return {
            'photo': ['photo', 'photograph', 'picture', 'image'],
            'email': ['email', 'e-mail', 'message', 'correspondence'],
            'contract': ['contract', 'agreement', 'lease', 'terms'],
            'medical_record': ['medical', 'diagnosis', 'treatment', 'hospital', 'doctor'],
            'police_report': ['police', 'incident', 'report', 'officer'],
            'invoice': ['invoice', 'bill', 'receipt', 'payment'],
            'letter': ['letter', 'correspondence', 'memo'],
            'video': ['video', 'recording', 'footage', 'surveillance'],
            'audio': ['audio', 'recording', 'transcript'],
            'diagram': ['diagram', 'chart', 'graph', 'illustration'],
            'report': ['report', 'analysis', 'evaluation', 'assessment'],
            'policy': ['policy', 'procedure', 'manual', 'guideline']
        }
    
    async def index_document_exhibits(
        self,
        document_path: str,
        document_content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[ExhibitIndex]:
        """Index all exhibits referenced in a document"""
        logger.info(f"Indexing exhibits from {document_path}")
        
        exhibits = []
        exhibit_refs = []
        
        # Extract exhibit references
        for pattern_name, pattern in self.exhibit_patterns.items():
            for match in pattern.finditer(document_content):
                ref = self._process_exhibit_match(
                    match, pattern_name, document_content, document_path
                )
                if ref:
                    exhibit_refs.append(ref)
        
        # Group references by exhibit ID
        exhibit_groups = self._group_exhibit_references(exhibit_refs)
        
        # Create exhibit index entries
        for exhibit_id, refs in exhibit_groups.items():
            exhibit = await self._create_exhibit_index(
                exhibit_id, refs, document_path, metadata
            )
            exhibits.append(exhibit)
        
        # Store exhibits in vector database
        await self._store_exhibits(exhibits)
        
        return exhibits
    
    def _process_exhibit_match(
        self,
        match: re.Match,
        pattern_type: str,
        content: str,
        document_path: str
    ) -> Optional[ExhibitReference]:
        """Process a regex match to create exhibit reference"""
        try:
            # Extract exhibit identifier based on pattern type
            if pattern_type == 'standard' or pattern_type == 'parenthetical':
                exhibit_id = f"Exhibit_{match.group(1)}"
            elif pattern_type == 'composite':
                exhibit_id = f"Exhibit_{match.group(1)}-{match.group(2)}"
            elif pattern_type == 'bates':
                exhibit_id = f"{match.group(1)}{match.group(2)}"
            elif pattern_type == 'deposition':
                exhibit_id = f"{match.group(1)}_Dep_Ex_{match.group(2)}"
            elif pattern_type == 'trial':
                exhibit_id = f"Trial_Ex_{match.group(1)}"
            else:
                return None
            
            # Extract context
            start_pos = max(0, match.start() - 200)
            end_pos = min(len(content), match.end() + 200)
            context = content[start_pos:end_pos].strip()
            
            # Estimate page number (rough approximation)
            chars_before = len(content[:match.start()])
            page_number = (chars_before // 3000) + 1  # ~3000 chars per page
            
            return ExhibitReference(
                exhibit_id=exhibit_id,
                reference_text=match.group(0),
                document_source=document_path,
                page_number=page_number,
                context=context
            )
        except Exception as e:
            logger.warning(f"Failed to process exhibit match: {e}")
            return None
    
    def _group_exhibit_references(
        self,
        references: List[ExhibitReference]
    ) -> Dict[str, List[ExhibitReference]]:
        """Group references by exhibit ID"""
        groups = {}
        
        for ref in references:
            # Normalize exhibit ID
            normalized_id = self._normalize_exhibit_id(ref.exhibit_id)
            
            if normalized_id not in groups:
                groups[normalized_id] = []
            groups[normalized_id].append(ref)
        
        return groups
    
    def _normalize_exhibit_id(self, exhibit_id: str) -> str:
        """Normalize exhibit ID for consistency"""
        # Remove extra spaces and convert to uppercase
        normalized = re.sub(r'\s+', '_', exhibit_id.strip()).upper()
        
        # Standardize common variations
        normalized = normalized.replace('EXHIBIT_', 'EX_')
        normalized = normalized.replace('EXH_', 'EX_')
        
        return normalized
    
    async def _create_exhibit_index(
        self,
        exhibit_id: str,
        references: List[ExhibitReference],
        document_path: str,
        metadata: Optional[Dict[str, Any]]
    ) -> ExhibitIndex:
        """Create exhibit index entry from references"""
        # Generate unique ID using UUID
        index_id = str(uuid.uuid4())
        
        # Combine all contexts for description
        all_contexts = " ".join([ref.context for ref in references])
        
        # Determine document type
        document_type = self._classify_document_type(all_contexts)
        
        # Extract description from context
        description = self._extract_description(all_contexts, exhibit_id)
        
        # Get all page references
        page_refs = sorted(list(set([ref.page_number for ref in references])))
        
        return ExhibitIndex(
            id=index_id,
            case_name=self.case_name,
            exhibit_number=exhibit_id,
            description=description,
            document_type=document_type,
            source_document=document_path,
            page_references=page_refs,
            authenticity_status="pending"
        )
    
    def _classify_document_type(self, context: str) -> str:
        """Classify document type based on context"""
        context_lower = context.lower()
        
        # Check each document type
        best_match = "document"  # default
        best_score = 0
        
        for doc_type, keywords in self.document_types.items():
            score = sum(1 for keyword in keywords if keyword in context_lower)
            if score > best_score:
                best_score = score
                best_match = doc_type
        
        return best_match
    
    def _extract_description(self, context: str, exhibit_id: str) -> str:
        """Extract meaningful description from context"""
        # Look for descriptive phrases near exhibit reference
        patterns = [
            rf'{exhibit_id}[,\s]+(?:which\s+is\s+)?(?:a|an|the)\s+([^,\.]+)',
            rf'{exhibit_id}[,\s]+(?:showing|depicting|containing)\s+([^,\.]+)',
            rf'([^,\.]+)[,\s]+marked\s+as\s+{exhibit_id}',
            rf'([^,\.]+)[,\s]+{exhibit_id}'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, context, re.IGNORECASE)
            if match:
                description = match.group(1).strip()
                # Clean up description
                description = re.sub(r'\s+', ' ', description)
                if len(description) > 10 and len(description) < 200:
                    return description
        
        # Fallback: use document type
        doc_type = self._classify_document_type(context)
        return f"{doc_type.replace('_', ' ').title()} - {exhibit_id}"
    
    async def _store_exhibits(self, exhibits: List[ExhibitIndex]):
        """Store exhibits in case-specific vector database"""
        if not exhibits:
            return
            
        points = []
        
        for exhibit in exhibits:
            # Generate embedding for exhibit description and context
            text_for_embedding = f"{exhibit.exhibit_number}: {exhibit.description}"
            embedding, _ = await self.embedding_generator.generate_embedding_async(text_for_embedding)
            
            # Prepare metadata
            metadata = {
                "case_name": self.case_name,
                "exhibit_id": exhibit.id,
                "exhibit_number": exhibit.exhibit_number,
                "description": exhibit.description,
                "document_type": exhibit.document_type,
                "source_document": exhibit.source_document,
                "page_references": json.dumps(exhibit.page_references),
                "authenticity_status": exhibit.authenticity_status,
                "relevance_score": exhibit.relevance_score
            }
            
            if exhibit.date_created:
                metadata["date_created"] = exhibit.date_created.isoformat()
            if exhibit.date_admitted:
                metadata["date_admitted"] = exhibit.date_admitted.isoformat()
            
            points.append({
                "id": exhibit.id,
                "vector": embedding,
                "payload": metadata
            })
        
        # Store in case-specific collection
        self.vector_store.client.upsert(
            collection_name=self.exhibits_collection,
            points=points
        )
        
        logger.info(f"Stored {len(points)} exhibits in {self.exhibits_collection}")
    
    async def search_exhibits(
        self,
        query: str,
        document_type_filter: Optional[str] = None,
        authenticity_filter: Optional[str] = None,
        limit: int = 20
    ) -> List[ExhibitIndex]:
        """Search exhibits within this case"""
        # Generate query embedding
        query_embedding = await self.embedding_generator.generate_embedding(query)
        
        # Build filter
        must_conditions = [{"key": "case_name", "match": {"value": self.case_name}}]
        
        if document_type_filter:
            must_conditions.append({
                "key": "document_type",
                "match": {"value": document_type_filter}
            })
        
        if authenticity_filter:
            must_conditions.append({
                "key": "authenticity_status",
                "match": {"value": authenticity_filter}
            })
        
        # Search
        results = self.vector_store.client.search(
            collection_name=self.exhibits_collection,
            query_vector=query_embedding,
            query_filter={"must": must_conditions},
            limit=limit
        )
        
        # Convert results to exhibit objects
        exhibits = []
        for result in results:
            payload = result.payload
            exhibit = ExhibitIndex(
                id=payload["exhibit_id"],
                case_name=self.case_name,
                exhibit_number=payload["exhibit_number"],
                description=payload["description"],
                document_type=payload["document_type"],
                source_document=payload["source_document"],
                page_references=json.loads(payload["page_references"]),
                authenticity_status=payload["authenticity_status"],
                relevance_score=payload["relevance_score"]
            )
            exhibits.append(exhibit)
        
        return exhibits
    
    async def link_exhibit_to_fact(
        self,
        exhibit_id: str,
        fact_id: str
    ):
        """Link an exhibit to a fact"""
        # This would update both the exhibit and fact records
        # to maintain bidirectional relationships
        logger.info(f"Linking exhibit {exhibit_id} to fact {fact_id}")
        
        # Update exhibit with related fact
        exhibit_point = self.vector_store.client.retrieve(
            collection_name=self.exhibits_collection,
            ids=[exhibit_id]
        )[0]
        
        if exhibit_point:
            related_facts = json.loads(exhibit_point.payload.get("related_facts", "[]"))
            if fact_id not in related_facts:
                related_facts.append(fact_id)
            
            # Update payload
            exhibit_point.payload["related_facts"] = json.dumps(related_facts)
            
            # Update in database
            self.vector_store.client.upsert(
                collection_name=self.exhibits_collection,
                points=[exhibit_point]
            )
    
    async def get_exhibit_summary(self) -> Dict[str, Any]:
        """Get summary statistics for exhibits in this case"""
        # Get all exhibits
        all_exhibits = self.vector_store.client.scroll(
            collection_name=self.exhibits_collection,
            scroll_filter={"must": [{"key": "case_name", "match": {"value": self.case_name}}]},
            limit=1000,
            with_payload=True,
            with_vectors=False
        )[0]
        
        # Calculate statistics
        total_exhibits = len(all_exhibits)
        
        # Count by type
        type_counts = {}
        authenticity_counts = {
            "pending": 0,
            "admitted": 0,
            "objected": 0,
            "excluded": 0
        }
        
        for exhibit in all_exhibits:
            doc_type = exhibit.payload.get("document_type", "unknown")
            type_counts[doc_type] = type_counts.get(doc_type, 0) + 1
            
            auth_status = exhibit.payload.get("authenticity_status", "pending")
            authenticity_counts[auth_status] = authenticity_counts.get(auth_status, 0) + 1
        
        return {
            "case_name": self.case_name,
            "total_exhibits": total_exhibits,
            "exhibits_by_type": type_counts,
            "authenticity_status": authenticity_counts,
            "collection_name": self.exhibits_collection
        }
    
    def format_exhibit_citation(
        self,
        exhibit: ExhibitIndex,
        style: str = "standard"
    ) -> str:
        """Format exhibit citation for legal documents"""
        if style == "standard":
            return exhibit.exhibit_number.replace("_", " ")
        elif style == "formal":
            return f"{exhibit.exhibit_number.replace('_', ' ')}, {exhibit.description}"
        elif style == "with_pages":
            pages = exhibit.page_references
            if pages:
                page_str = f"p. {pages[0]}" if len(pages) == 1 else f"pp. {pages[0]}-{pages[-1]}"
                return f"{exhibit.exhibit_number.replace('_', ' ')} ({page_str})"
            return exhibit.exhibit_number.replace("_", " ")
        else:
            return exhibit.exhibit_number
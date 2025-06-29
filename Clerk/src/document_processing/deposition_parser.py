"""
Deposition Citation Parser with Case Isolation
Extracts testimony citations and content from deposition transcripts
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple, Set
from datetime import datetime
from dataclasses import dataclass
import hashlib
import uuid

from src.models.fact_models import DepositionCitation, CaseIsolationConfig
from src.vector_storage.qdrant_store import QdrantVectorStore
from src.vector_storage.embeddings import EmbeddingGenerator

logger = logging.getLogger("clerk_api")


@dataclass
class DepositionMetadata:
    """Metadata for a deposition document"""
    deponent_name: str
    deposition_date: Optional[datetime]
    case_name: str
    document_path: str
    total_pages: int
    examiner_names: List[str] = None


class DepositionParser:
    """
    Parses deposition transcripts to extract citations and testimony.
    Maintains strict case isolation.
    """
    
    def __init__(self, case_name: str):
        """Initialize parser for specific case"""
        self.case_name = case_name
        self.vector_store = QdrantVectorStore()
        self.embedding_generator = EmbeddingGenerator()
        
        # Case-specific collection
        self.depositions_collection = f"{case_name}_depositions"
        
        # Ensure collection exists
        self._ensure_collection_exists()
        
        # Citation patterns
        self.citation_patterns = self._compile_citation_patterns()
        
        # Page/line patterns
        self.page_line_patterns = self._compile_page_line_patterns()
        
        logger.info(f"DepositionParser initialized for case: {case_name}")
    
    def _ensure_collection_exists(self):
        """Create deposition collection if it doesn't exist"""
        try:
            self.vector_store.client.get_collection(self.depositions_collection)
        except:
            self.vector_store.client.create_collection(
                collection_name=self.depositions_collection,
                vectors_config={
                    "size": 1536,  # OpenAI embedding size
                    "distance": "Cosine"
                }
            )
            logger.info(f"Created collection: {self.depositions_collection}")
    
    def _compile_citation_patterns(self) -> Dict[str, re.Pattern]:
        """Compile regex patterns for citation formats"""
        return {
            # Short form: "Smith Dep. 45:12-23"
            'short_form': re.compile(
                r'(\w+)\s+Dep\.\s*(?:at\s*)?(\d+):(\d+)(?:-(?:(\d+):)?(\d+))?',
                re.IGNORECASE
            ),
            
            # Long form: "Deposition of John Smith, taken on January 15, 2023, p. 45"
            'long_form': re.compile(
                r'Deposition\s+of\s+([^,]+),\s*(?:taken\s+on\s+)?([^,]+),\s*(?:at\s*)?(?:pp?\.\s*)?(\d+)(?:-(\d+))?',
                re.IGNORECASE
            ),
            
            # Page reference: "Page 45, Line 12"
            'page_line': re.compile(
                r'(?:Page|Pg\.?|P\.?)\s*(\d+),?\s*(?:Line|Ln\.?|L\.?)\s*(\d+)(?:\s*-\s*(?:Line|Ln\.?|L\.?)?\s*(\d+))?',
                re.IGNORECASE
            ),
            
            # Transcript format: "45:12 Q:"
            'transcript': re.compile(
                r'^(\d+):(\d+)\s*([QA]):',
                re.MULTILINE
            )
        }
    
    def _compile_page_line_patterns(self) -> Dict[str, re.Pattern]:
        """Compile patterns for page/line extraction"""
        return {
            # Standard format: "1  Q. What is your name?"
            'standard': re.compile(r'^(\d+)\s+([QA])\.\s*(.+)$', re.MULTILINE),
            
            # Line number format: "12:5  Q. What happened next?"
            'line_number': re.compile(r'^(\d+):(\d+)\s+([QA])[.:]?\s*(.+)$', re.MULTILINE),
            
            # Page header: "Page 45"
            'page_header': re.compile(r'^\s*(?:Page|PAGE)\s+(\d+)\s*$', re.MULTILINE | re.IGNORECASE),
            
            # Witness name: "JOHN SMITH, sworn"
            'witness': re.compile(r'^([A-Z\s]+),\s*(?:sworn|affirmed)', re.MULTILINE)
        }
    
    async def parse_deposition(
        self,
        document_path: str,
        document_content: str,
        metadata: Optional[DepositionMetadata] = None
    ) -> List[DepositionCitation]:
        """Parse a deposition transcript and extract citations"""
        logger.info(f"Parsing deposition: {document_path}")
        
        # Extract metadata if not provided
        if not metadata:
            metadata = self._extract_metadata(document_content)
            metadata.case_name = self.case_name
            metadata.document_path = document_path
        
        # Extract all citations
        citations = []
        
        # Parse different citation formats
        citations.extend(self._extract_short_form_citations(document_content, metadata))
        citations.extend(self._extract_page_line_citations(document_content, metadata))
        citations.extend(self._extract_transcript_testimony(document_content, metadata))
        
        # Store citations in vector database
        await self._store_citations(citations)
        
        return citations
    
    def _extract_metadata(self, content: str) -> DepositionMetadata:
        """Extract metadata from deposition content"""
        # Look for deponent name
        deponent_name = "Unknown"
        witness_match = self.page_line_patterns['witness'].search(content)
        if witness_match:
            deponent_name = witness_match.group(1).strip().title()
        
        # Look for date
        deposition_date = None
        date_patterns = [
            r'taken\s+on\s+([A-Za-z]+ \d+, \d{4})',
            r'Date:\s*([A-Za-z]+ \d+, \d{4})',
            r'(\d{1,2}/\d{1,2}/\d{4})'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, content[:1000], re.IGNORECASE)  # Check first 1000 chars
            if match:
                try:
                    from dateparser import parse
                    deposition_date = parse(match.group(1))
                    break
                except:
                    pass
        
        # Count pages
        page_matches = self.page_line_patterns['page_header'].findall(content)
        total_pages = max([int(p) for p in page_matches]) if page_matches else 0
        
        return DepositionMetadata(
            deponent_name=deponent_name,
            deposition_date=deposition_date,
            case_name=self.case_name,
            document_path="",
            total_pages=total_pages
        )
    
    def _extract_short_form_citations(
        self,
        content: str,
        metadata: DepositionMetadata
    ) -> List[DepositionCitation]:
        """Extract short form citations like 'Smith Dep. 45:12-23'"""
        citations = []
        
        for match in self.citation_patterns['short_form'].finditer(content):
            deponent = match.group(1)
            page_start = int(match.group(2))
            line_start = int(match.group(3))
            page_end = int(match.group(4)) if match.group(4) else page_start
            line_end = int(match.group(5)) if match.group(5) else None
            
            # Extract surrounding context
            start_pos = max(0, match.start() - 200)
            end_pos = min(len(content), match.end() + 200)
            context = content[start_pos:end_pos].strip()
            
            # Generate unique ID using UUID
            citation_id = str(uuid.uuid4())
            
            citation = DepositionCitation(
                id=citation_id,
                case_name=self.case_name,
                deponent_name=deponent,
                deposition_date=metadata.deposition_date,
                page_start=page_start,
                page_end=page_end,
                line_start=line_start,
                line_end=line_end,
                testimony_excerpt=context,
                citation_format=match.group(0),
                source_document=metadata.document_path
            )
            
            citations.append(citation)
        
        return citations
    
    def _extract_page_line_citations(
        self,
        content: str,
        metadata: DepositionMetadata
    ) -> List[DepositionCitation]:
        """Extract page/line references"""
        citations = []
        
        for match in self.citation_patterns['page_line'].finditer(content):
            page = int(match.group(1))
            line_start = int(match.group(2))
            line_end = int(match.group(3)) if match.group(3) else line_start
            
            # Extract surrounding context
            start_pos = max(0, match.start() - 300)
            end_pos = min(len(content), match.end() + 300)
            context = content[start_pos:end_pos].strip()
            
            # Generate unique ID using UUID
            citation_id = str(uuid.uuid4())
            
            citation = DepositionCitation(
                id=citation_id,
                case_name=self.case_name,
                deponent_name=metadata.deponent_name,
                deposition_date=metadata.deposition_date,
                page_start=page,
                line_start=line_start,
                line_end=line_end,
                testimony_excerpt=context,
                citation_format=f"Page {page}, Line {line_start}",
                source_document=metadata.document_path
            )
            
            citations.append(citation)
        
        return citations
    
    def _extract_transcript_testimony(
        self,
        content: str,
        metadata: DepositionMetadata
    ) -> List[DepositionCitation]:
        """Extract Q&A testimony from transcript format"""
        citations = []
        
        # Split content into pages
        pages = re.split(r'^\s*(?:Page|PAGE)\s+\d+\s*$', content, flags=re.MULTILINE | re.IGNORECASE)
        
        current_page = 1
        for page_content in pages[1:]:  # Skip content before first page marker
            # Extract Q&A pairs
            qa_matches = list(self.page_line_patterns['line_number'].finditer(page_content))
            
            for i, match in enumerate(qa_matches):
                line_num = int(match.group(2))
                qa_type = match.group(3)
                text = match.group(4).strip()
                
                # Get the full Q&A exchange
                if i + 1 < len(qa_matches):
                    next_match = qa_matches[i + 1]
                    full_text = page_content[match.start():next_match.start()].strip()
                else:
                    full_text = page_content[match.start():match.start() + 500].strip()
                
                # Only create citations for questions that seem significant
                if qa_type == 'Q' and len(text) > 20:
                    # Generate unique ID using UUID
                    citation_id = str(uuid.uuid4())
                    
                    citation = DepositionCitation(
                        id=citation_id,
                        case_name=self.case_name,
                        deponent_name=metadata.deponent_name,
                        deposition_date=metadata.deposition_date,
                        page_start=current_page,
                        line_start=line_num,
                        testimony_excerpt=full_text,
                        citation_format=f"{metadata.deponent_name} Dep. {current_page}:{line_num}",
                        source_document=metadata.document_path,
                        topics=self._extract_topics(text)
                    )
                    
                    citations.append(citation)
            
            current_page += 1
        
        return citations
    
    def _extract_topics(self, text: str) -> List[str]:
        """Extract potential topics from testimony text"""
        topics = []
        
        # Keywords that indicate important topics
        topic_keywords = {
            'accident': ['accident', 'crash', 'collision', 'incident'],
            'injury': ['injury', 'hurt', 'pain', 'damage', 'harm'],
            'speed': ['speed', 'mph', 'fast', 'slow', 'velocity'],
            'visibility': ['see', 'saw', 'visible', 'visibility', 'dark', 'light'],
            'weather': ['weather', 'rain', 'wet', 'dry', 'fog', 'clear'],
            'safety': ['safety', 'safe', 'dangerous', 'hazard', 'risk'],
            'training': ['training', 'trained', 'procedure', 'protocol'],
            'maintenance': ['maintenance', 'repair', 'inspection', 'condition'],
            'liability': ['fault', 'responsible', 'liability', 'negligence'],
            'damages': ['damage', 'cost', 'expense', 'loss', 'compensation']
        }
        
        text_lower = text.lower()
        for topic, keywords in topic_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                topics.append(topic)
        
        return topics
    
    async def _store_citations(self, citations: List[DepositionCitation]):
        """Store citations in case-specific vector database"""
        if not citations:
            return
            
        points = []
        
        for citation in citations:
            # Generate embedding for testimony
            embedding, _ = await self.embedding_generator.generate_embedding_async(
                citation.testimony_excerpt
            )
            
            # Prepare metadata
            metadata = {
                "case_name": self.case_name,
                "citation_id": citation.id,
                "deponent_name": citation.deponent_name,
                "page_start": citation.page_start,
                "line_start": citation.line_start if citation.line_start else 0,
                "citation_format": citation.citation_format,
                "source_document": citation.source_document,
                "topics": ",".join(citation.topics) if citation.topics else "",
                "testimony_excerpt": citation.testimony_excerpt[:500]  # Truncate for storage
            }
            
            if citation.deposition_date:
                metadata["deposition_date"] = citation.deposition_date.isoformat()
            
            points.append({
                "id": citation.id,
                "vector": embedding,
                "payload": metadata
            })
        
        # Store in case-specific collection
        self.vector_store.client.upsert(
            collection_name=self.depositions_collection,
            points=points
        )
        
        logger.info(f"Stored {len(points)} deposition citations in {self.depositions_collection}")
    
    async def search_testimony(
        self,
        query: str,
        deponent_filter: Optional[str] = None,
        topic_filter: Optional[List[str]] = None,
        limit: int = 20
    ) -> List[DepositionCitation]:
        """Search deposition testimony within this case"""
        # Generate query embedding
        query_embedding, _ = await self.embedding_generator.generate_embedding_async(query)
        
        # Build filter
        must_conditions = [{"key": "case_name", "match": {"value": self.case_name}}]
        
        if deponent_filter:
            must_conditions.append({
                "key": "deponent_name",
                "match": {"value": deponent_filter}
            })
        
        if topic_filter:
            # Topics are stored as comma-separated string
            should_conditions = []
            for topic in topic_filter:
                should_conditions.append({
                    "key": "topics",
                    "match": {"text": topic}
                })
            must_conditions.append({"should": should_conditions})
        
        # Search
        results = self.vector_store.client.search(
            collection_name=self.depositions_collection,
            query_vector=query_embedding,
            query_filter={"must": must_conditions},
            limit=limit
        )
        
        # Convert results to citations
        citations = []
        for result in results:
            payload = result.payload
            citation = DepositionCitation(
                id=payload["citation_id"],
                case_name=self.case_name,
                deponent_name=payload["deponent_name"],
                deposition_date=datetime.fromisoformat(payload["deposition_date"]) 
                    if "deposition_date" in payload else None,
                page_start=payload["page_start"],
                line_start=payload.get("line_start", 0),
                testimony_excerpt=payload["testimony_excerpt"],
                citation_format=payload["citation_format"],
                source_document=payload["source_document"],
                topics=payload["topics"].split(",") if payload["topics"] else []
            )
            citations.append(citation)
        
        return citations
    
    def format_citation(
        self,
        citation: DepositionCitation,
        style: str = "bluebook"
    ) -> str:
        """Format citation according to legal citation standards"""
        if style == "bluebook":
            # Bluebook format: "Smith Dep. 45:12-23"
            base = f"{citation.deponent_name.split()[-1]} Dep. {citation.page_start}"
            if citation.line_start:
                base += f":{citation.line_start}"
                if citation.line_end and citation.line_end != citation.line_start:
                    base += f"-{citation.line_end}"
            return base
        elif style == "full":
            # Full format with date
            base = f"Deposition of {citation.deponent_name}"
            if citation.deposition_date:
                base += f", {citation.deposition_date.strftime('%B %d, %Y')}"
            base += f", p. {citation.page_start}"
            if citation.line_start:
                base += f", l. {citation.line_start}"
            return base
        else:
            return citation.citation_format
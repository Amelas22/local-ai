"""
Source Document Indexer with Case Isolation
Indexes and classifies source documents for evidence discovery
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import json
import uuid

from src.models.source_document_models import (
    SourceDocument, DocumentType, DocumentRelevance,
    DocumentClassificationRequest, DocumentClassificationResult
)
from src.vector_storage.qdrant_store import QdrantVectorStore
from src.vector_storage.embeddings import EmbeddingGenerator
from config.settings import settings
import openai

logger = logging.getLogger("clerk_api")


class SourceDocumentIndexer:
    """
    Indexes source documents for evidence discovery.
    Replaces exhibit tracking with source document discovery.
    """
    
    def __init__(self, case_name: str):
        """Initialize source document indexer for a specific case"""
        self.case_name = case_name
        self.vector_store = QdrantVectorStore()
        self.embedding_generator = EmbeddingGenerator()
        self.openai_client = openai.OpenAI(api_key=settings.openai.api_key)
        
        # Case-specific collection for source documents
        self.source_docs_collection = f"{case_name}_source_documents"
        
        # Ensure collection exists
        self._ensure_collection_exists()
        
        # Compile patterns for document analysis
        self.patterns = self._compile_patterns()
        
        logger.info(f"SourceDocumentIndexer initialized for case: {case_name}")
    
    def _ensure_collection_exists(self):
        """Create source documents collection if it doesn't exist"""
        try:
            self.vector_store.client.get_collection(self.source_docs_collection)
        except:
            self.vector_store.client.create_collection(
                collection_name=self.source_docs_collection,
                vectors_config={
                    "size": 1536,  # OpenAI embedding size
                    "distance": "Cosine"
                },
                # Add payload indexes for efficient filtering
                payload_schema={
                    "document_type": "keyword",
                    "relevance_tags": "keyword[]",
                    "author": "keyword",
                    "document_date": "datetime",
                    "verified": "bool"
                }
            )
            logger.info(f"Created collection: {self.source_docs_collection}")
    
    def _compile_patterns(self) -> Dict[str, re.Pattern]:
        """Compile regex patterns for document analysis"""
        return {
            # Date patterns
            'date': re.compile(
                r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b|'
                r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})\b',
                re.IGNORECASE
            ),
            
            # Deposition patterns
            'deposition': re.compile(
                r'deposition\s+of\s+([^,\n]+)|'
                r'([^,\n]+)\s+deposition|'
                r'deponent:\s*([^\n]+)',
                re.IGNORECASE
            ),
            
            # Medical record patterns
            'medical': re.compile(
                r'patient\s+name:\s*([^\n]+)|'
                r'diagnosis:|treatment:|medication:|'
                r'chief\s+complaint:|physical\s+exam:',
                re.IGNORECASE
            ),
            
            # Police report patterns
            'police': re.compile(
                r'incident\s+report|case\s+number:\s*([^\n]+)|'
                r'officer\s+([^,\n]+)|badge\s*#?\s*(\d+)',
                re.IGNORECASE
            ),
            
            # Expert report patterns
            'expert': re.compile(
                r'expert\s+opinion|expert\s+report|'
                r'qualifications:|methodology:|conclusions:',
                re.IGNORECASE
            ),
            
            # Financial patterns
            'financial': re.compile(
                r'invoice\s*#?\s*(\d+)|'
                r'amount\s+due:|total:|balance:|'
                r'\$[\d,]+\.?\d*',
                re.IGNORECASE
            )
        }
    
    async def classify_document(
        self,
        document_content: str,
        document_path: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> DocumentClassificationResult:
        """Classify a document using patterns and AI"""
        
        # First, try pattern-based classification
        doc_type = self._pattern_based_classification(document_content)
        
        # Get first 2000 chars for AI classification
        sample_content = document_content[:2000]
        
        # Use AI for more accurate classification
        prompt = f"""Analyze this legal document and classify it. 

Document sample:
{sample_content}

Provide:
1. Document type (one of: deposition, medical_record, police_report, expert_report, photograph, video, invoice, contract, correspondence, interrogatory, request_for_admission, request_for_production, financial_record, employment_record, insurance_policy, incident_report, witness_statement, affidavit, other)
2. Key parties mentioned (names only)
3. Key dates mentioned
4. Main topics (3-5 topics)
5. Relevance categories (one or more of: liability, damages, causation, credibility, procedure, background, impeachment, authentication)
6. Brief summary (2-3 sentences)

Format as JSON."""

        try:
            response = self.openai_client.chat.completions.create(
                model=settings.ai.default_model,
                messages=[
                    {"role": "system", "content": "You are a legal document classifier."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500,
                response_format={"type": "json_object"}
            )
            
            classification = json.loads(response.choices[0].message.content)
            
            # Override with pattern-based type if high confidence
            if doc_type and doc_type != DocumentType.OTHER:
                classification["document_type"] = doc_type.value
            
            return DocumentClassificationResult(
                document_type=DocumentType(classification.get("document_type", "other")),
                confidence=0.9 if doc_type else 0.7,
                detected_parties=classification.get("parties", []),
                detected_dates=classification.get("dates", []),
                key_topics=classification.get("topics", []),
                suggested_relevance=[DocumentRelevance(r) for r in classification.get("relevance", [])],
                summary=classification.get("summary", "")
            )
            
        except Exception as e:
            logger.error(f"Error classifying document: {e}")
            # Fallback to pattern-based only
            return DocumentClassificationResult(
                document_type=doc_type or DocumentType.OTHER,
                confidence=0.5,
                detected_parties=self._extract_parties(document_content),
                detected_dates=self._extract_dates(document_content),
                key_topics=[],
                suggested_relevance=[],
                summary=""
            )
    
    def _pattern_based_classification(self, content: str) -> Optional[DocumentType]:
        """Classify document based on patterns"""
        content_lower = content.lower()
        
        # Check for specific document markers
        if 'deposition of' in content_lower or 'deponent:' in content_lower:
            return DocumentType.DEPOSITION
        elif 'patient name:' in content_lower or 'diagnosis:' in content_lower:
            return DocumentType.MEDICAL_RECORD
        elif 'incident report' in content_lower or 'case number:' in content_lower:
            return DocumentType.POLICE_REPORT
        elif 'expert opinion' in content_lower or 'qualifications:' in content_lower:
            return DocumentType.EXPERT_REPORT
        elif 'invoice' in content_lower or 'amount due:' in content_lower:
            return DocumentType.INVOICE
        elif 'interrogatory' in content_lower:
            return DocumentType.INTERROGATORY
        elif 'request for admission' in content_lower:
            return DocumentType.REQUEST_FOR_ADMISSION
        elif 'request for production' in content_lower:
            return DocumentType.REQUEST_FOR_PRODUCTION
        elif 'affidavit' in content_lower or 'sworn statement' in content_lower:
            return DocumentType.AFFIDAVIT
        
        return None
    
    def _extract_parties(self, content: str) -> List[str]:
        """Extract party names from document"""
        parties = []
        
        # Look for common party indicators
        party_patterns = [
            r'(?:plaintiff|defendant|petitioner|respondent|claimant|appellant|appellee):\s*([^\n,]+)',
            r'between\s+([^,\n]+)\s+and\s+([^,\n]+)',
            r'deposition\s+of\s+([^,\n]+)',
            r'patient\s+name:\s*([^\n]+)',
            r'witness:\s*([^\n]+)'
        ]
        
        for pattern in party_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                for group in match.groups():
                    if group and len(group) > 2:
                        cleaned_name = group.strip().title()
                        if cleaned_name not in parties:
                            parties.append(cleaned_name)
        
        return parties[:10]  # Limit to 10 parties
    
    def _extract_dates(self, content: str) -> List[str]:
        """Extract dates from document"""
        dates = []
        
        for match in self.patterns['date'].finditer(content):
            date_str = match.group(0)
            if date_str not in dates:
                dates.append(date_str)
        
        return dates[:20]  # Limit to 20 dates
    
    async def index_source_document(
        self,
        document_path: str,
        document_content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> SourceDocument:
        """Index a source document for evidence discovery"""
        logger.info(f"Indexing source document: {document_path}")
        
        # Classify the document
        classification = await self.classify_document(
            document_content, document_path, metadata
        )
        
        # Extract key pages (pages with high keyword density)
        key_pages = self._identify_key_pages(document_content)
        
        # Create source document
        doc_id = str(uuid.uuid4())
        source_doc = SourceDocument(
            id=doc_id,
            case_name=self.case_name,
            document_type=classification.document_type,
            title=self._generate_title(document_path, classification),
            description=classification.summary,
            source_path=document_path,
            upload_date=datetime.now(),
            document_date=self._extract_document_date(classification.detected_dates),
            author=self._extract_author(classification.detected_parties, classification.document_type),
            key_facts=classification.key_topics,
            relevance_tags=classification.suggested_relevance,
            mentioned_parties=classification.detected_parties,
            mentioned_dates=classification.detected_dates,
            key_pages=key_pages,
            summary=classification.summary,
            search_text=document_content,
            total_pages=self._estimate_pages(document_content)
        )
        
        # Store in vector database
        await self._store_source_document(source_doc)
        
        return source_doc
    
    def _generate_title(
        self,
        path: str,
        classification: DocumentClassificationResult
    ) -> str:
        """Generate descriptive title for document"""
        filename = path.split('/')[-1].replace('.pdf', '')
        
        if classification.document_type == DocumentType.DEPOSITION and classification.detected_parties:
            return f"Deposition of {classification.detected_parties[0]}"
        elif classification.document_type == DocumentType.MEDICAL_RECORD and classification.detected_parties:
            return f"Medical Records - {classification.detected_parties[0]}"
        elif classification.document_type == DocumentType.POLICE_REPORT:
            return f"Police Report - {classification.detected_dates[0] if classification.detected_dates else 'Unknown Date'}"
        else:
            return filename.replace('_', ' ').title()
    
    def _extract_document_date(self, dates: List[str]) -> Optional[datetime]:
        """Extract the primary date of the document"""
        if not dates:
            return None
        
        # Try to parse the first date
        try:
            from dateparser import parse
            return parse(dates[0])
        except:
            return None
    
    def _extract_author(
        self,
        parties: List[str],
        doc_type: DocumentType
    ) -> Optional[str]:
        """Extract author based on document type"""
        if not parties:
            return None
        
        if doc_type == DocumentType.DEPOSITION:
            # First party is usually the deponent
            return parties[0]
        elif doc_type in [DocumentType.EXPERT_REPORT, DocumentType.AFFIDAVIT]:
            # Look for doctor/expert names
            for party in parties:
                if 'Dr.' in party or 'MD' in party or 'Ph.D' in party:
                    return party
        
        return None
    
    def _identify_key_pages(self, content: str) -> List[int]:
        """Identify most relevant pages based on keyword density"""
        # Split into approximate pages
        pages = [content[i:i+3000] for i in range(0, len(content), 3000)]
        
        # Score each page
        page_scores = []
        keywords = ['injury', 'accident', 'negligence', 'damages', 'liability', 
                   'cause', 'fault', 'breach', 'duty', 'harm']
        
        for i, page in enumerate(pages):
            score = sum(1 for keyword in keywords if keyword in page.lower())
            page_scores.append((i + 1, score))
        
        # Return top 5 pages
        page_scores.sort(key=lambda x: x[1], reverse=True)
        return [page_num for page_num, score in page_scores[:5] if score > 0]
    
    def _estimate_pages(self, content: str) -> int:
        """Estimate number of pages"""
        return max(1, len(content) // 3000)
    
    async def _store_source_document(self, doc: SourceDocument):
        """Store source document in vector database"""
        # Generate embedding for the document
        embedding_text = f"{doc.title}\n{doc.description}\n{' '.join(doc.key_facts)}"
        embedding, _ = await self.embedding_generator.generate_embedding_async(embedding_text)
        
        # Prepare metadata
        metadata = {
            "case_name": self.case_name,
            "document_id": doc.id,
            "document_type": doc.document_type.value,
            "title": doc.title,
            "description": doc.description,
            "source_path": doc.source_path,
            "upload_date": doc.upload_date.isoformat(),
            "relevance_tags": json.dumps([tag.value for tag in doc.relevance_tags]),
            "mentioned_parties": json.dumps(doc.mentioned_parties),
            "key_pages": json.dumps(doc.key_pages),
            "verified": doc.verified
        }
        
        if doc.document_date:
            metadata["document_date"] = doc.document_date.isoformat()
        if doc.author:
            metadata["author"] = doc.author
        
        # Store in vector database
        point = {
            "id": doc.id,
            "vector": embedding,
            "payload": metadata
        }
        
        self.vector_store.client.upsert(
            collection_name=self.source_docs_collection,
            points=[point]
        )
        
        logger.info(f"Stored source document: {doc.title}")
    
    async def search_evidence(
        self,
        query: str,
        document_types: Optional[List[DocumentType]] = None,
        relevance_tags: Optional[List[DocumentRelevance]] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Search for source documents that could be used as evidence"""
        # Generate query embedding
        query_embedding, _ = await self.embedding_generator.generate_embedding_async(query)
        
        # Build filter
        filter_conditions = {"must": [{"key": "case_name", "match": {"value": self.case_name}}]}
        
        if document_types:
            filter_conditions["must"].append({
                "key": "document_type",
                "match": {"any": [dt.value for dt in document_types]}
            })
        
        if relevance_tags:
            # Note: This would need custom filtering logic for array fields
            pass
        
        # Search
        results = self.vector_store.client.search(
            collection_name=self.source_docs_collection,
            query_vector=query_embedding,
            query_filter=filter_conditions,
            limit=limit,
            with_payload=True
        )
        
        # Format results
        search_results = []
        for result in results:
            payload = result.payload
            search_results.append({
                "document_id": payload["document_id"],
                "title": payload["title"],
                "document_type": payload["document_type"],
                "description": payload["description"],
                "relevance_score": result.score,
                "source_path": payload["source_path"],
                "key_pages": json.loads(payload.get("key_pages", "[]")),
                "author": payload.get("author"),
                "document_date": payload.get("document_date")
            })
        
        return search_results
"""
Unified Document Manager for Legal AI System
Combines document deduplication and source document indexing into a single system
"""

import hashlib
import logging
import re
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import json
import uuid

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    PayloadSchemaType,
)
import openai

from src.models.unified_document_models import (
    UnifiedDocument,
    DocumentType,
    DocumentRelevance,
    DocumentStatus,
    DuplicateLocation,
    DocumentProcessingResult,
    DocumentSearchRequest,
    DocumentSearchResult,
)
from src.vector_storage.embeddings import EmbeddingGenerator
from config.settings import settings

logger = logging.getLogger(__name__)


class UnifiedDocumentManager:
    """
    Unified manager for document deduplication and discovery
    Replaces both QdrantDocumentDeduplicator and SourceDocumentIndexer
    """

    def __init__(self, case_name: str):
        """Initialize unified document manager for a specific case

        Args:
            case_name: Name of the case for case-specific collections
        """
        self.case_name = case_name
        self.collection_name = f"{case_name}_documents"

        # Initialize clients
        self.client = QdrantClient(
            url=settings.qdrant.url,
            api_key=settings.qdrant.api_key,
            prefer_grpc=settings.qdrant.prefer_grpc,
            timeout=settings.qdrant.timeout,
        )

        self.embedding_generator = EmbeddingGenerator()
        self.openai_client = openai.OpenAI(api_key=settings.openai.api_key)
        self.async_openai_client = openai.AsyncOpenAI(api_key=settings.openai.api_key)

        # Compile patterns for document analysis
        self.patterns = self._compile_patterns()

        # Ensure collection exists
        self._ensure_collection_exists()

        logger.info(f"UnifiedDocumentManager initialized for case: {case_name}")

    def _ensure_collection_exists(self):
        """Create unified documents collection if it doesn't exist"""
        try:
            self.client.get_collection(self.collection_name)
            logger.debug(f"Collection {self.collection_name} already exists")
        except Exception:
            logger.info(f"Creating unified collection: {self.collection_name}")
            try:
                # Create collection with proper vector configuration
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=1536,  # OpenAI embedding size
                        distance=Distance.COSINE,
                    ),
                )

                # Create indexes for efficient filtering
                indexes = [
                    ("document_hash", PayloadSchemaType.KEYWORD),
                    ("document_type", PayloadSchemaType.KEYWORD),
                    ("case_name", PayloadSchemaType.KEYWORD),
                    ("status", PayloadSchemaType.KEYWORD),
                    ("author", PayloadSchemaType.KEYWORD),
                    ("first_seen_at", PayloadSchemaType.DATETIME),
                    ("document_date", PayloadSchemaType.DATETIME),
                    ("is_duplicate", PayloadSchemaType.BOOL),
                    ("verified", PayloadSchemaType.BOOL),
                ]

                for field_name, field_type in indexes:
                    try:
                        self.client.create_payload_index(
                            collection_name=self.collection_name,
                            field_name=field_name,
                            field_schema=field_type,
                        )
                        logger.debug(f"Created index for {field_name}")
                    except Exception as e:
                        logger.debug(
                            f"Index {field_name} might already exist: {str(e)}"
                        )

                logger.info(f"Created unified collection: {self.collection_name}")
            except Exception as e:
                logger.error(f"Failed to create collection: {e}")
                raise

    def calculate_document_hash(self, content: bytes) -> str:
        """Calculate SHA-256 hash of document content"""
        return hashlib.sha256(content).hexdigest()

    def check_document_exists(
        self, doc_hash: str
    ) -> Tuple[bool, Optional[UnifiedDocument]]:
        """Check if document with given hash already exists

        Returns:
            Tuple of (exists, existing_document)
        """
        try:
            # Search for document with this hash
            results = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="document_hash", match=MatchValue(value=doc_hash)
                        ),
                        FieldCondition(
                            key="case_name", match=MatchValue(value=self.case_name)
                        ),
                    ]
                ),
                limit=1,
            )[0]

            if results:
                # Document exists
                doc_data = results[0].payload
                existing_doc = UnifiedDocument.from_storage_dict(doc_data)
                return True, existing_doc

            return False, None

        except Exception as e:
            logger.error(f"Error checking document existence: {str(e)}")
            return False, None

    async def is_duplicate(self, document_hash: str) -> bool:
        """Check if a document with this hash already exists
        
        Args:
            document_hash: SHA-256 hash of the document content
            
        Returns:
            True if document exists, False otherwise
        """
        exists, _ = self.check_document_exists(document_hash)
        return exists

    async def process_document(
        self, file_path: str, file_content: bytes, file_metadata: Dict[str, Any]
    ) -> DocumentProcessingResult:
        """Process a document: deduplicate, classify, and index

        Args:
            file_path: Path to the document in Box
            file_content: Raw document content
            file_metadata: Metadata from Box (name, size, modified_at, etc.)

        Returns:
            DocumentProcessingResult with processing details
        """
        start_time = datetime.now()
        warnings = []

        # Calculate hash
        doc_hash = self.calculate_document_hash(file_content)

        # Check for duplicates
        exists, existing_doc = self.check_document_exists(doc_hash)

        if exists:
            # Handle duplicate
            logger.info(f"Duplicate found: {file_metadata['name']}")

            # Add this location to the duplicate tracking
            duplicate_location = DuplicateLocation(
                case_name=self.case_name,
                file_path=file_path,
                folder_path="/".join(file_metadata.get("folder_path", [])),
                found_at=datetime.now(),
            )

            # Update the existing document
            existing_doc.duplicate_locations.append(duplicate_location)
            existing_doc.duplicate_count += 1

            # Update in storage
            self._update_document(existing_doc)

            return DocumentProcessingResult(
                document_id=existing_doc.id,
                is_duplicate=True,
                original_document_id=existing_doc.id,
                document_type=existing_doc.document_type,
                title=existing_doc.title,
                summary=existing_doc.summary,
                chunks_created=0,
                processing_time=(datetime.now() - start_time).total_seconds(),
                warnings=["Document is a duplicate of an existing file"],
            )

        # Extract text content (assuming text extraction is done elsewhere)
        text_content = file_metadata.get("extracted_text", "")

        # Classify the document
        classification = await self._classify_document(text_content, file_path)

        # Extract metadata
        parties = self._extract_parties(text_content)
        dates = self._extract_dates(text_content)
        key_pages = self._identify_key_pages(text_content)

        # Generate embedding for the document
        embedding_text = f"{classification['title']}\n{classification['summary']}\n{' '.join(classification['key_facts'])}"
        embedding, _ = self.embedding_generator.generate_embedding(embedding_text)

        # Create unified document
        doc = UnifiedDocument(
            case_name=self.case_name,
            document_hash=doc_hash,
            file_name=file_metadata["name"],
            file_path=file_path,
            file_size=file_metadata.get("size", 0),
            document_type=classification["document_type"],
            title=classification["title"],
            description=classification["summary"],
            last_modified=datetime.fromisoformat(
                file_metadata.get("modified_at", datetime.now().isoformat())
            ),
            document_date=self._extract_document_date(dates),
            key_facts=classification["key_facts"],
            relevance_tags=classification["relevance_tags"],
            mentioned_parties=parties,
            mentioned_dates=dates,
            author=self._extract_author(parties, classification["document_type"]),
            total_pages=self._estimate_pages(text_content),
            key_pages=key_pages,
            summary=classification["summary"],
            search_text=text_content,
            embedding_id=str(uuid.uuid4()),
            embedding_model=self.embedding_generator.model,
            box_file_id=file_metadata.get("box_file_id"),
            box_shared_link=file_metadata.get("box_shared_link"),
            folder_path=file_metadata.get("folder_path", []),
            subfolder=file_metadata.get("subfolder", "root"),
            extraction_confidence=classification["confidence"],
            classification_confidence=classification["confidence"],
        )

        # Store in Qdrant
        self._store_document(doc, embedding)

        return DocumentProcessingResult(
            document_id=doc.id,
            is_duplicate=False,
            document_type=doc.document_type,
            title=doc.title,
            summary=doc.summary,
            chunks_created=file_metadata.get("chunks_created", 0),
            processing_time=(datetime.now() - start_time).total_seconds(),
            confidence_scores={
                "extraction": doc.extraction_confidence,
                "classification": doc.classification_confidence,
            },
            warnings=warnings,
        )

    def _store_document(self, doc: UnifiedDocument, embedding: List[float]):
        """Store document in Qdrant"""
        point = PointStruct(id=doc.id, vector=embedding, payload=doc.to_storage_dict())

        self.client.upsert(
            collection_name=self.collection_name, points=[point], wait=True
        )

        logger.info(f"Stored unified document: {doc.title} (ID: {doc.id})")

    async def add_document(self, doc: UnifiedDocument) -> str:
        """Add a document to the storage
        
        Args:
            doc: UnifiedDocument instance to store
            
        Returns:
            Document ID
        """
        # Generate embedding for the document
        embedding_text = f"{doc.title}\n{doc.description}\n{doc.summary or ''}"
        embedding, _ = self.embedding_generator.generate_embedding(embedding_text)
        
        # Store the document
        self._store_document(doc, embedding)
        
        return doc.id

    def _update_document(self, doc: UnifiedDocument):
        """Update an existing document in storage"""
        # Get the current embedding (we're not changing it)
        existing_points = self.client.retrieve(
            collection_name=self.collection_name, ids=[doc.id], with_vectors=True
        )

        if existing_points:
            vector = existing_points[0].vector
            self._store_document(doc, vector)

    async def _classify_document(self, content: str, file_path: str) -> Dict[str, Any]:
        """Classify document using AI and patterns"""
        # Pattern-based classification first
        doc_type = self._pattern_based_classification(content)

        # Get sample for AI classification
        sample_content = content[:2000]

        prompt = f"""Analyze this legal document and provide structured information.

Document sample:
{sample_content}

Provide a JSON response with:
1. document_type: (one of: motion, complaint, answer, memorandum, brief, order, deposition, medical_record, police_report, expert_report, photograph, video, invoice, contract, correspondence, interrogatory, request_for_admission, request_for_production, financial_record, employment_record, insurance_policy, incident_report, witness_statement, affidavit, other)
2. title: A descriptive title for the document
3. summary: 2-3 sentence summary
4. key_facts: List of 3-5 key facts from the document
5. relevance_tags: List of relevance categories (liability, damages, causation, credibility, procedure, background, impeachment, authentication)
6. confidence: Confidence score 0-1

Format as valid JSON."""

        try:
            response = await self.async_openai_client.chat.completions.create(
                model=settings.ai.default_model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a legal document classifier.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=500,
                response_format={"type": "json_object"},
            )

            classification = json.loads(response.choices[0].message.content)

            # Override with pattern-based type if high confidence
            if doc_type and doc_type != DocumentType.OTHER:
                classification["document_type"] = doc_type

            # Convert to proper types
            classification["document_type"] = DocumentType(
                classification.get("document_type", "other")
            )
            classification["relevance_tags"] = [
                DocumentRelevance(tag)
                for tag in classification.get("relevance_tags", [])
            ]
            classification["confidence"] = float(classification.get("confidence", 0.7))

            # Generate title if not provided
            if not classification.get("title"):
                classification["title"] = self._generate_title(
                    file_path,
                    classification["document_type"],
                    self._extract_parties(content)[:1],
                )

            return classification

        except Exception as e:
            logger.error(f"Error classifying document: {e}")
            # Fallback classification
            return {
                "document_type": doc_type or DocumentType.OTHER,
                "title": file_path.split("/")[-1]
                .replace(".pdf", "")
                .replace("_", " ")
                .title(),
                "summary": "Unable to generate summary due to processing error",
                "key_facts": [],
                "relevance_tags": [],
                "confidence": 0.5,
            }

    def _compile_patterns(self) -> Dict[str, re.Pattern]:
        """Compile regex patterns for document analysis"""
        return {
            "date": re.compile(
                r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b|"
                r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})\b",
                re.IGNORECASE,
            ),
            "party": re.compile(
                r"(?:plaintiff|defendant|petitioner|respondent|claimant|appellant|appellee):\s*([^\n,]+)|"
                r"between\s+([^,\n]+)\s+and\s+([^,\n]+)|"
                r"deposition\s+of\s+([^,\n]+)|"
                r"patient\s+name:\s*([^\n]+)|"
                r"witness:\s*([^\n]+)",
                re.IGNORECASE,
            ),
        }

    def _pattern_based_classification(self, content: str) -> Optional[DocumentType]:
        """Classify document based on patterns"""
        content_lower = content.lower()

        # Check for legal filings first
        if any(
            phrase in content_lower
            for phrase in [
                "motion for",
                "motion to",
                "plaintiff's motion",
                "defendant's motion",
            ]
        ):
            return DocumentType.MOTION
        elif "complaint" in content_lower and (
            "plaintiff" in content_lower or "cause of action" in content_lower
        ):
            return DocumentType.COMPLAINT
        elif "deposition of" in content_lower or "deponent:" in content_lower:
            return DocumentType.DEPOSITION
        elif "patient name:" in content_lower or "diagnosis:" in content_lower:
            return DocumentType.MEDICAL_RECORD
        elif "incident report" in content_lower or "case number:" in content_lower:
            return DocumentType.POLICE_REPORT
        elif "expert opinion" in content_lower or "qualifications:" in content_lower:
            return DocumentType.EXPERT_REPORT

        return None

    def _extract_parties(self, content: str) -> List[str]:
        """Extract party names from document"""
        parties = []

        for match in self.patterns["party"].finditer(content):
            for group in match.groups():
                if group and len(group) > 2:
                    cleaned_name = group.strip().title()
                    if cleaned_name not in parties:
                        parties.append(cleaned_name)

        return parties[:10]  # Limit to 10 parties

    def _extract_dates(self, content: str) -> List[str]:
        """Extract dates from document"""
        dates = []

        for match in self.patterns["date"].finditer(content):
            date_str = match.group(0)
            if date_str not in dates:
                dates.append(date_str)

        return dates[:20]  # Limit to 20 dates

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
        self, parties: List[str], doc_type: DocumentType
    ) -> Optional[str]:
        """Extract author based on document type and parties"""
        if not parties:
            return None

        if doc_type == DocumentType.DEPOSITION:
            return parties[0]  # First party is usually the deponent
        elif doc_type in [DocumentType.EXPERT_REPORT, DocumentType.AFFIDAVIT]:
            # Look for doctor/expert names
            for party in parties:
                if any(title in party for title in ["Dr.", "MD", "Ph.D", "P.E."]):
                    return party

        return None

    def _identify_key_pages(self, content: str) -> List[int]:
        """Identify most relevant pages based on keyword density"""
        # Split into approximate pages
        pages = [content[i : i + 3000] for i in range(0, len(content), 3000)]

        # Score each page
        page_scores = []
        keywords = [
            "injury",
            "accident",
            "negligence",
            "damages",
            "liability",
            "cause",
            "fault",
            "breach",
            "duty",
            "harm",
        ]

        for i, page in enumerate(pages):
            score = sum(1 for keyword in keywords if keyword in page.lower())
            page_scores.append((i + 1, score))

        # Return top 5 pages
        page_scores.sort(key=lambda x: x[1], reverse=True)
        return [page_num for page_num, score in page_scores[:5] if score > 0]

    def _estimate_pages(self, content: str) -> int:
        """Estimate number of pages"""
        return max(1, len(content) // 3000)

    def _generate_title(
        self, file_path: str, doc_type: DocumentType, parties: List[str]
    ) -> str:
        """Generate descriptive title for document"""
        filename = file_path.split("/")[-1].replace(".pdf", "")

        if doc_type == DocumentType.MOTION:
            if "dismiss" in filename.lower() or "mtd" in filename.lower():
                return "Motion to Dismiss"
            elif "summary" in filename.lower() or "msj" in filename.lower():
                return "Motion for Summary Judgment"
            else:
                return filename.replace("_", " ").title()
        elif doc_type == DocumentType.DEPOSITION and parties:
            return f"Deposition of {parties[0]}"
        elif doc_type == DocumentType.MEDICAL_RECORD and parties:
            return f"Medical Records - {parties[0]}"
        elif doc_type == DocumentType.EXPERT_REPORT and parties:
            return f"Expert Report - {parties[0]}"
        else:
            return filename.replace("_", " ").title()

    async def search_documents(
        self, request: DocumentSearchRequest
    ) -> List[DocumentSearchResult]:
        """Search for documents using vector similarity and filters"""
        # Generate embedding for query
        query_embedding, _ = self.embedding_generator.generate_embedding(request.query)

        # Build filter conditions
        must_conditions = [
            FieldCondition(key="case_name", match=MatchValue(value=request.case_name)),
            FieldCondition(
                key="status", match=MatchValue(value=DocumentStatus.ACTIVE.value)
            ),
        ]

        # Add optional filters
        if request.document_types:
            must_conditions.append(
                FieldCondition(
                    key="document_type",
                    match=MatchValue(
                        value=[dt.value for dt in request.document_types], any=True
                    ),
                )
            )

        if not request.include_duplicates:
            must_conditions.append(
                FieldCondition(key="is_duplicate", match=MatchValue(value=False))
            )

        # Search
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            query_filter=Filter(must=must_conditions),
            limit=request.limit,
            with_payload=True,
        )

        # Convert to search results
        search_results = []
        for result in results:
            doc = UnifiedDocument.from_storage_dict(result.payload)
            search_results.append(
                DocumentSearchResult(
                    document=doc,
                    score=result.score,
                    relevance_explanation=f"Similarity score: {result.score:.3f}",
                )
            )

        return search_results

    def get_document_by_id(self, document_id: str) -> Optional[UnifiedDocument]:
        """Retrieve a document by its ID"""
        try:
            results = self.client.retrieve(
                collection_name=self.collection_name,
                ids=[document_id],
                with_payload=True,
            )

            if results:
                return UnifiedDocument.from_storage_dict(results[0].payload)

            return None

        except Exception as e:
            logger.error(f"Error retrieving document: {e}")
            return None

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about documents in this case"""
        try:
            # Get collection info
            collection_info = self.client.get_collection(self.collection_name)

            # Count documents by type
            doc_type_counts = {}
            for doc_type in DocumentType:
                count_result = self.client.count(
                    collection_name=self.collection_name,
                    count_filter=Filter(
                        must=[
                            FieldCondition(
                                key="document_type",
                                match=MatchValue(value=doc_type.value),
                            ),
                            FieldCondition(
                                key="is_duplicate", match=MatchValue(value=False)
                            ),
                        ]
                    ),
                )
                if count_result.count > 0:
                    doc_type_counts[doc_type.value] = count_result.count

            # Count duplicates
            duplicate_count = self.client.count(
                collection_name=self.collection_name,
                count_filter=Filter(
                    must=[
                        FieldCondition(key="is_duplicate", match=MatchValue(value=True))
                    ]
                ),
            ).count

            return {
                "case_name": self.case_name,
                "total_documents": collection_info.points_count,
                "unique_documents": collection_info.points_count - duplicate_count,
                "duplicate_count": duplicate_count,
                "document_types": doc_type_counts,
                "collection_size": collection_info.payload_schema_info,
            }

        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {"case_name": self.case_name, "error": str(e)}

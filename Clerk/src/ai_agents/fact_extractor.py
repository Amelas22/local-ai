"""
Fact Extraction Agent with Case Isolation
Extracts facts, dates, entities, and relationships from legal documents
while maintaining strict case separation.
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import json
import uuid

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
import openai
import spacy
from dateparser import parse as parse_date

from src.models.fact_models import (
    CaseFact,
    FactCategory,
    EntityType,
    DateReference,
    CaseFactCollection,
)
from src.vector_storage.qdrant_store import QdrantVectorStore
from src.vector_storage.embeddings import EmbeddingGenerator
from config.settings import settings

logger = logging.getLogger("clerk_api")


class FactExtractor:
    """
    Extracts facts from legal documents with case isolation.
    Uses NLP and pattern matching for entity and date extraction.
    """

    def __init__(self, case_name: str):
        """Initialize fact extractor for a specific case"""
        self.case_name = self._validate_case_name(case_name)
        self.vector_store = QdrantVectorStore()
        self.embedding_generator = EmbeddingGenerator()

        # Initialize NLP model for entity recognition
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except (OSError, ImportError) as e:
            logger.warning(
                f"spaCy model not found: {str(e)}. Running without NER support."
            )
            self.nlp = None

        # Initialize OpenAI client
        self.openai_client = openai.OpenAI(api_key=settings.openai.api_key)

        # Initialize LLM for fact categorization (pydantic_ai)
        self.llm_model = OpenAIModel(settings.ai.default_model)
        self.fact_categorizer = self._create_fact_categorizer()

        # Compile regex patterns
        self.patterns = self._compile_patterns()

        # Case-specific collections
        self.facts_collection = f"{self.case_name}_facts"
        self.timeline_collection = f"{self.case_name}_timeline"

        # Ensure collections exist
        self._ensure_collections_exist()

        logger.info(f"FactExtractor initialized for case: {self.case_name}")

    def _validate_case_name(self, case_name: str) -> str:
        """Validate and sanitize case name"""
        if not case_name or not case_name.strip():
            raise ValueError("Case name cannot be empty")

        # Remove/replace problematic characters
        sanitized = re.sub(r"[*?\[\]{}]", "", case_name.strip())
        sanitized = re.sub(r"\s+", "_", sanitized)  # Replace spaces with underscores

        return sanitized

    def _ensure_collections_exist(self):
        """Verify case-specific collections exist"""
        collections_to_verify = [self.facts_collection, self.timeline_collection]

        for collection_name in collections_to_verify:
            try:
                self.vector_store.client.get_collection(collection_name)
                logger.debug(f"Collection {collection_name} verified to exist")
            except Exception as e:
                logger.warning(f"Collection {collection_name} does not exist: {e}")
                # Don't create it - let the main collection creation handle this

    def _compile_patterns(self) -> Dict[str, re.Pattern]:
        """Compile regex patterns for fact extraction"""
        return {
            # Date patterns
            "date_mdy": re.compile(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b"),
            "date_written": re.compile(
                r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})\b",
                re.I,
            ),
            "date_iso": re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b"),
            # Deposition citation patterns
            "deposition": re.compile(
                r"(\w+)\s+Dep\.\s*(?:at\s*)?(\d+):(\d+)(?:-(\d+))?(?::(\d+))?"
            ),
            "deposition_long": re.compile(
                r"Deposition\s+of\s+([^,]+),\s*(?:taken\s+on\s+)?([^,]+),\s*(?:at\s*)?(?:pp?\.\s*)?(\d+)(?:-(\d+))?"
            ),
            # Legal citation patterns
            "case_citation": re.compile(
                r"(\d+)\s+(\w+\.?\s*\d*[dst]?)\s+(\d+)(?:\s*\(([^)]+)\))?"
            ),
            "statute": re.compile(r"(?:Fla\.\s*Stat\.|F\.S\.)\s*§?\s*([\d.]+)"),
            "cfr": re.compile(r"(\d+)\s+C\.F\.R\.\s*§?\s*([\d.]+)"),
            # Money patterns
            "money": re.compile(r"\$[\d,]+(?:\.\d{2})?|\b\d+\s*dollars?\b", re.I),
            # Vehicle patterns
            "vehicle": re.compile(
                r"\b\d{4}\s+\w+\s+\w+\b|\b(?:car|truck|vehicle|trailer|semi)\b", re.I
            ),
            # Medical patterns
            "medical": re.compile(
                r"\b(?:diagnosis|injury|treatment|surgery|fracture|trauma|condition)\b",
                re.I,
            ),
        }

    def _create_fact_categorizer(self) -> Agent:
        """Create AI agent for fact categorization"""
        return Agent(
            self.llm_model,
            system_prompt="""You are a legal fact categorizer. Categorize facts into one of these categories:
            - PROCEDURAL: Court filings, motions, orders, procedural history
            - SUBSTANTIVE: Core facts of the case, what happened
            - EVIDENTIARY: Evidence, exhibits, witness testimony
            - MEDICAL: Medical records, diagnoses, treatment
            - DAMAGES: Financial losses, injuries, harm suffered
            - TIMELINE: Specific dated events
            - PARTY: Information about parties involved
            - EXPERT: Expert opinions and reports
            - REGULATORY: Regulatory violations or compliance issues
            
            Respond with just the category name.""",
        )

    async def extract_facts_from_document(
        self,
        document_id: str,
        document_content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> CaseFactCollection:
        """Extract all facts from a document"""
        logger.info(
            f"Extracting facts from document {document_id} for case {self.case_name}"
        )

        collection = CaseFactCollection(case_name=self.case_name)
        collection.extraction_start_time = datetime.now()

        # Split document into chunks for processing
        chunks = self._split_into_chunks(document_content)

        for i, chunk in enumerate(chunks):
            # Extract different types of information
            facts = await self._extract_facts_from_chunk(chunk, document_id, i)
            dates = self._extract_dates(chunk)
            entities = self._extract_entities(chunk) if self.nlp else {}
            citations = self._extract_citations(chunk)

            # Create fact objects
            for fact_text in facts:
                # Extract entities specific to this fact
                fact_entities = self._extract_entities(fact_text) if self.nlp else {}
                # Extract dates specific to this fact
                fact_dates = self._extract_dates(fact_text)
                # Extract citations specific to this fact
                fact_citations = self._extract_citations(fact_text)

                fact = await self._create_fact(
                    fact_text, document_id, i, fact_dates, fact_entities, fact_citations
                )
                collection.add_fact(fact)

        collection.extraction_end_time = datetime.now()
        collection.total_documents_processed = 1

        # Store facts in vector database
        await self._store_facts(collection)

        return collection

    def _split_into_chunks(self, text: str, chunk_size: int = 1000) -> List[str]:
        """Split document into processable chunks"""
        # Split by paragraphs first
        paragraphs = text.split("\n\n")

        chunks = []
        current_chunk = ""

        for para in paragraphs:
            if len(current_chunk) + len(para) < chunk_size:
                current_chunk += para + "\n\n"
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = para + "\n\n"

        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    async def _extract_facts_from_chunk(
        self, chunk: str, document_id: str, chunk_index: int
    ) -> List[str]:
        """Extract fact statements from text chunk using LLM"""
        prompt = f"""Extract key factual statements from this legal text. 
        Return each fact as a separate line. Focus on:
        - What happened (events)
        - Who was involved (parties)
        - When it happened (dates)
        - Where it happened (locations)
        - Important details (injuries, damages, violations)
        
        Text:
        {chunk}
        
        Facts (one per line):"""

        try:
            # Use OpenAI client directly
            response = self.openai_client.chat.completions.create(
                model=settings.ai.default_model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a legal fact extractor. Extract key factual statements from legal text.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=500,
            )

            facts_text = response.choices[0].message.content
            facts = [f.strip() for f in facts_text.split("\n") if f.strip()]
            return facts[:10]  # Limit to top 10 facts per chunk
        except Exception as e:
            logger.error(f"Error extracting facts: {e}")
            return []

    def _extract_dates(self, text: str) -> List[DateReference]:
        """Extract dates from text"""
        dates = []

        # Try each date pattern
        for pattern_name, pattern in self.patterns.items():
            if pattern_name.startswith("date_"):
                for match in pattern.finditer(text):
                    date_text = match.group(0)
                    parsed_date = parse_date(date_text)

                    if parsed_date:
                        dates.append(
                            DateReference(
                                date_text=date_text,
                                start_date=parsed_date,
                                is_approximate=False,
                                confidence=0.9,
                            )
                        )

        # Also try dateparser for more complex dates
        sentences = text.split(".")
        for sentence in sentences:
            if any(
                month in sentence.lower()
                for month in [
                    "january",
                    "february",
                    "march",
                    "april",
                    "may",
                    "june",
                    "july",
                    "august",
                    "september",
                    "october",
                    "november",
                    "december",
                ]
            ):
                parsed = parse_date(sentence, settings={"PREFER_DATES_FROM": "past"})
                if parsed:
                    dates.append(
                        DateReference(
                            date_text=sentence.strip(),
                            start_date=parsed,
                            is_approximate=True,
                            confidence=0.7,
                        )
                    )

        return dates

    def _extract_entities(self, text: str) -> Dict[EntityType, List[str]]:
        """Extract named entities using spaCy"""
        if not self.nlp:
            return {}

        doc = self.nlp(text)
        entities = {entity_type: [] for entity_type in EntityType}

        # Map spaCy labels to our entity types
        label_mapping = {
            "PERSON": EntityType.PERSON,
            "ORG": EntityType.ORGANIZATION,
            "LOC": EntityType.LOCATION,
            "GPE": EntityType.LOCATION,
            "DATE": EntityType.DATE,
            "TIME": EntityType.TIME,
            "MONEY": EntityType.MONETARY_AMOUNT,
        }

        # Pattern to identify party designations
        party_pattern = re.compile(
            r"^(Plaintiff|Defendant|Petitioner|Respondent|Appellant|Appellee|Claimant)\s+(.+)$",
            re.IGNORECASE,
        )

        for ent in doc.ents:
            if ent.label_ in label_mapping:
                entity_type = label_mapping[ent.label_]
                entity_text = ent.text

                # Check if this is a party designation
                party_match = party_pattern.match(entity_text)
                if party_match:
                    # Extract the actual name without the party designation
                    party_role = party_match.group(1)
                    party_name = party_match.group(2)

                    # Add the person's name (not the full phrase with role)
                    if party_name not in entities[EntityType.PERSON]:
                        entities[EntityType.PERSON].append(party_name)
                else:
                    # Regular entity extraction
                    if entity_text not in entities[entity_type]:
                        entities[entity_type].append(entity_text)

        # Extract vehicles using pattern
        for match in self.patterns["vehicle"].finditer(text):
            vehicle = match.group(0)
            if vehicle not in entities[EntityType.VEHICLE]:
                entities[EntityType.VEHICLE].append(vehicle)

        # Extract medical conditions
        for match in self.patterns["medical"].finditer(text):
            condition = match.group(0)
            if condition not in entities[EntityType.MEDICAL_CONDITION]:
                entities[EntityType.MEDICAL_CONDITION].append(condition)

        # Manual extraction for party names that spaCy might miss
        party_patterns = [
            r"\b(Plaintiff|Defendant|Petitioner|Respondent|Appellant|Appellee|Claimant)\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)\b",
            r"\b([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*),?\s+(?:the\s+)?(Plaintiff|Defendant|Petitioner|Respondent|Appellant|Appellee|Claimant)\b",
        ]

        for pattern in party_patterns:
            for match in re.finditer(pattern, text):
                if match.lastindex == 2:
                    # Pattern 1: Role Name
                    name = (
                        match.group(2)
                        if match.group(1)
                        in [
                            "Plaintiff",
                            "Defendant",
                            "Petitioner",
                            "Respondent",
                            "Appellant",
                            "Appellee",
                            "Claimant",
                        ]
                        else match.group(1)
                    )
                else:
                    # Pattern 2: Name Role
                    name = match.group(1)

                # Only add if it looks like a proper name (not all caps like "PLAINTIFF")
                if (
                    name
                    and not name.isupper()
                    and name not in entities[EntityType.PERSON]
                ):
                    entities[EntityType.PERSON].append(name)

        # Clean up empty lists
        return {k: v for k, v in entities.items() if v}

    def _extract_citations(self, text: str) -> List[str]:
        """Extract legal citations from text"""
        citations = []

        # Deposition citations
        for match in self.patterns["deposition"].finditer(text):
            citation = match.group(0)
            citations.append(citation)

        # Case citations
        for match in self.patterns["case_citation"].finditer(text):
            citation = match.group(0)
            citations.append(citation)

        # Statute citations
        for match in self.patterns["statute"].finditer(text):
            citation = match.group(0)
            citations.append(citation)

        # CFR citations
        for match in self.patterns["cfr"].finditer(text):
            citation = match.group(0)
            citations.append(citation)

        return citations

    async def _create_fact(
        self,
        fact_text: str,
        document_id: str,
        page_number: int,
        dates: List[DateReference],
        entities: Dict[EntityType, List[str]],
        citations: List[str],
    ) -> CaseFact:
        """Create a fact object with all extracted information"""
        # Generate unique ID using UUID
        fact_id = str(uuid.uuid4())

        # Categorize the fact
        try:
            category_response = await self.fact_categorizer.run(fact_text)
            category = FactCategory(category_response.data.lower())
        except Exception as e:
            logger.warning(f"Failed to categorize fact, using default: {str(e)}")
            category = FactCategory.SUBSTANTIVE  # Default

        # Find relevant dates for this fact
        relevant_dates = []
        for date_ref in dates:
            if date_ref.date_text.lower() in fact_text.lower():
                relevant_dates.append(date_ref)

        # Calculate confidence based on extraction quality
        confidence = 0.8  # Base confidence
        if relevant_dates:
            confidence += 0.1
        if entities:
            confidence += 0.05
        if citations:
            confidence += 0.05

        return CaseFact(
            id=fact_id,
            case_name=self.case_name,
            content=fact_text,
            category=category,
            source_document=document_id,
            page_references=[page_number],
            extraction_timestamp=datetime.now(),
            confidence_score=min(confidence, 1.0),
            entities=entities,
            date_references=relevant_dates,
            related_facts=[],
            supporting_exhibits=[],
            verification_status="unverified",
            extraction_method="automated",
        )

    async def _store_facts(self, collection: CaseFactCollection):
        """Store facts in case-specific vector database"""
        points = []

        for fact in collection.facts:
            # Generate embedding for fact content
            embedding, _ = await self.embedding_generator.generate_embedding_async(
                fact.content
            )

            # Prepare metadata
            metadata = {
                "case_name": self.case_name,
                "fact_id": fact.id,
                "content": fact.content,  # Add the actual fact text
                "category": fact.category.value,
                "source_document": fact.source_document,
                "confidence_score": fact.confidence_score,
                "extraction_timestamp": fact.extraction_timestamp.isoformat(),
                "entities": json.dumps({k.value: v for k, v in fact.entities.items()}),
                "has_dates": len(fact.date_references) > 0,
                "verification_status": fact.verification_status,
            }

            # Add date information if available
            if fact.date_references:
                first_date = fact.date_references[0]
                if first_date.start_date:
                    metadata["primary_date"] = first_date.start_date.isoformat()

            # Check if hybrid search is enabled
            if settings.legal.enable_hybrid_search:
                # For hybrid collections, use named vectors
                points.append(
                    {
                        "id": fact.id,
                        "vector": {
                            "semantic": embedding,
                            "legal_concepts": embedding,  # Using same embedding for both for now
                        },
                        "payload": metadata,
                    }
                )
            else:
                # For standard collections, use single vector
                points.append({"id": fact.id, "vector": embedding, "payload": metadata})

        # Store in case-specific collection
        if points:
            self.vector_store.client.upsert(
                collection_name=self.facts_collection, points=points
            )
            logger.info(f"Stored {len(points)} facts in {self.facts_collection}")

    async def search_facts(
        self,
        query: str,
        category_filter: Optional[List[FactCategory]] = None,
        date_range: Optional[Tuple[datetime, datetime]] = None,
        limit: int = 20,
    ) -> List[CaseFact]:
        """Search facts within this case only"""
        # Generate query embedding
        query_embedding, _ = await self.embedding_generator.generate_embedding_async(
            query
        )

        # Build filter
        must_conditions = [{"key": "case_name", "match": {"value": self.case_name}}]

        if category_filter:
            must_conditions.append(
                {
                    "key": "category",
                    "match": {"any": [cat.value for cat in category_filter]},
                }
            )

        if date_range:
            must_conditions.append(
                {
                    "key": "primary_date",
                    "range": {
                        "gte": date_range[0].isoformat(),
                        "lte": date_range[1].isoformat(),
                    },
                }
            )

        # Search case-specific collection
        if settings.legal.enable_hybrid_search:
            # For hybrid collections, specify the vector name
            results = self.vector_store.client.search(
                collection_name=self.facts_collection,
                query_vector=("semantic", query_embedding),  # Named vector search
                query_filter={"must": must_conditions},
                limit=limit,
            )
        else:
            # For standard collections, use unnamed vector
            results = self.vector_store.client.search(
                collection_name=self.facts_collection,
                query_vector=query_embedding,
                query_filter={"must": must_conditions},
                limit=limit,
            )

        # Convert results back to CaseFact objects
        facts = []
        for result in results:
            # Reconstruct fact from stored data
            # In production, you might want to store the full fact object
            fact = CaseFact(
                id=result.payload["fact_id"],
                case_name=self.case_name,
                content=result.payload.get("content", ""),  # Would need to store this
                category=FactCategory(result.payload["category"]),
                source_document=result.payload["source_document"],
                page_references=[],  # Would need to store this
                extraction_timestamp=datetime.fromisoformat(
                    result.payload["extraction_timestamp"]
                ),
                confidence_score=result.payload["confidence_score"],
                entities=json.loads(result.payload.get("entities", "{}")),
                date_references=[],  # Would need to store this
                verification_status=result.payload["verification_status"],
            )
            facts.append(fact)

        return facts

    def validate_case_access(self, requested_case: str) -> bool:
        """Validate that access is only to the initialized case"""
        return requested_case == self.case_name

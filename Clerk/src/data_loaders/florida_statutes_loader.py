"""
Florida Statutes Loader for Shared Legal Knowledge Base
Loads and indexes Florida statutory law for cross-case access
"""

import re
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import json
import uuid

from src.models.fact_models import SharedKnowledgeEntry
from src.vector_storage.qdrant_store import QdrantVectorStore
from src.vector_storage.embeddings import EmbeddingGenerator
from qdrant_client.models import VectorParams, Distance

logger = logging.getLogger("clerk_api")


class FloridaStatutesLoader:
    """
    Loads Florida statutes into a shared collection accessible by all cases.
    Maintains statute structure and enables efficient legal research.
    """

    def __init__(self):
        """Initialize Florida statutes loader"""
        self.vector_store = QdrantVectorStore()
        self.embedding_generator = EmbeddingGenerator()

        # Shared collection name
        self.collection_name = "florida_statutes"

        # Ensure collection exists
        self._ensure_collection_exists()

        # Statute patterns
        self.statute_patterns = self._compile_statute_patterns()

        # Topic mappings for common legal areas
        self.topic_mappings = self._define_topic_mappings()

        logger.info("FloridaStatutesLoader initialized")

    def _ensure_collection_exists(self):
        """Create Florida statutes collection if it doesn't exist"""
        import time

        max_retries = 5
        retry_delay = 2

        for attempt in range(max_retries):
            try:
                self.vector_store.client.get_collection(self.collection_name)
                logger.debug(f"Collection {self.collection_name} already exists")
                return
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(
                        f"Failed to connect to Qdrant (attempt {attempt + 1}/{max_retries}): {e}"
                    )
                    time.sleep(retry_delay)
                    continue

                # Last attempt - try to create the collection
                try:
                    self.vector_store.client.create_collection(
                        collection_name=self.collection_name,
                        vectors_config=VectorParams(
                            size=1536,  # OpenAI embedding size
                            distance=Distance.COSINE,
                        ),
                    )
                    logger.info(f"Created shared collection: {self.collection_name}")
                    return
                except Exception as create_error:
                    logger.error(
                        f"Failed to create collection after {max_retries} attempts: {create_error}"
                    )
                    raise

    def _compile_statute_patterns(self) -> Dict[str, re.Pattern]:
        """Compile regex patterns for statute parsing"""
        return {
            # Section number: "768.81" or "316.193(3)(c)2.b."
            "section": re.compile(
                r"§?\s*(\d+)\.(\d+)(?:\((\d+)\))?(?:\(([a-z])\))?(?:(\d+))?(?:\.([a-z]))?"
            ),
            # Title format: "CHAPTER 768 NEGLIGENCE"
            "chapter": re.compile(
                r"^CHAPTER\s+(\d+)\s+(.+)$", re.MULTILINE | re.IGNORECASE
            ),
            # Section title: "768.81 Comparative fault.—"
            "section_title": re.compile(r"^(\d+\.\d+)\s+([^.—]+)[.—]", re.MULTILINE),
            # Subsection: "(1)" or "(a)"
            "subsection": re.compile(r"^\s*\((\d+|[a-z])\)\s*(.+)", re.MULTILINE),
            # Effective date: "Effective Date: July 1, 2023"
            "effective_date": re.compile(
                r"Effective\s+Date:\s*([A-Za-z]+ \d+, \d{4})", re.IGNORECASE
            ),
        }

    def _define_topic_mappings(self) -> Dict[str, List[str]]:
        """Define topic keywords for categorizing statutes"""
        return {
            "negligence": [
                "negligence",
                "fault",
                "liability",
                "duty of care",
                "breach",
            ],
            "motor_vehicle": [
                "vehicle",
                "driver",
                "traffic",
                "motor carrier",
                "commercial",
            ],
            "personal_injury": [
                "injury",
                "damages",
                "compensation",
                "harm",
                "recovery",
            ],
            "civil_procedure": [
                "procedure",
                "pleading",
                "motion",
                "discovery",
                "trial",
            ],
            "evidence": ["evidence", "admissible", "testimony", "witness", "exhibit"],
            "insurance": ["insurance", "coverage", "policy", "insurer", "claim"],
            "premises_liability": [
                "premises",
                "property",
                "owner",
                "invitee",
                "trespasser",
            ],
            "product_liability": [
                "product",
                "defect",
                "manufacturer",
                "design",
                "warning",
            ],
            "medical_malpractice": [
                "medical",
                "malpractice",
                "physician",
                "hospital",
                "standard of care",
            ],
            "wrongful_death": ["wrongful death", "survivor", "estate", "beneficiary"],
        }

    async def load_statute(
        self,
        statute_number: str,
        title: str,
        content: str,
        chapter: Optional[str] = None,
        effective_date: Optional[datetime] = None,
        source_url: Optional[str] = None,
    ) -> SharedKnowledgeEntry:
        """Load a single Florida statute"""
        logger.info(f"Loading Florida Statute § {statute_number}: {title}")

        # Generate unique ID using UUID
        statute_id = str(uuid.uuid4())

        # Extract topics
        topics = self._extract_topics(title + " " + content)

        # Extract citations within the statute
        citations = self._extract_cross_references(content)

        # Create knowledge entry
        entry = SharedKnowledgeEntry(
            id=statute_id,
            knowledge_type="florida_statute",
            identifier=f"Fla. Stat. § {statute_number}",
            title=title,
            content=content,
            effective_date=effective_date,
            topics=topics,
            citations=citations,
        )

        # Store in vector database
        await self._store_statute(entry, chapter, source_url)

        return entry

    async def load_chapter(
        self,
        chapter_number: str,
        chapter_title: str,
        chapter_content: str,
        source_url: Optional[str] = None,
    ) -> List[SharedKnowledgeEntry]:
        """Load an entire chapter of Florida statutes"""
        logger.info(
            f"Loading Florida Statutes Chapter {chapter_number}: {chapter_title}"
        )

        entries = []

        # Parse individual sections
        sections = self._parse_chapter_sections(chapter_content)

        for section_num, section_title, section_content in sections:
            # Extract effective date if present
            effective_date = None
            date_match = self.statute_patterns["effective_date"].search(section_content)
            if date_match:
                try:
                    from dateparser import parse

                    effective_date = parse(date_match.group(1))
                except:
                    pass

            # Load section
            entry = await self.load_statute(
                statute_number=f"{chapter_number}.{section_num}",
                title=section_title,
                content=section_content,
                chapter=f"Chapter {chapter_number} - {chapter_title}",
                effective_date=effective_date,
                source_url=source_url,
            )
            entries.append(entry)

        logger.info(f"Loaded {len(entries)} sections from Chapter {chapter_number}")
        return entries

    def _parse_chapter_sections(
        self, chapter_content: str
    ) -> List[Tuple[str, str, str]]:
        """Parse chapter content into individual sections"""
        sections = []

        # Split by section numbers
        section_splits = self.statute_patterns["section_title"].split(chapter_content)

        # Process each section
        for i in range(1, len(section_splits), 3):
            if i + 2 < len(section_splits):
                section_num = section_splits[i]
                section_title = section_splits[i + 1]
                section_content = section_splits[i + 2]

                sections.append(
                    (section_num, section_title.strip(), section_content.strip())
                )

        return sections

    def _extract_topics(self, text: str) -> List[str]:
        """Extract relevant legal topics from statute text"""
        topics = []
        text_lower = text.lower()

        for topic, keywords in self.topic_mappings.items():
            if any(keyword in text_lower for keyword in keywords):
                topics.append(topic)

        # Also extract specific legal concepts
        legal_concepts = [
            "comparative_fault",
            "statute_of_limitations",
            "sovereign_immunity",
            "res_judicata",
            "collateral_estoppel",
            "proximate_cause",
            "respondeat_superior",
            "vicarious_liability",
            "punitive_damages",
        ]

        for concept in legal_concepts:
            if concept.replace("_", " ") in text_lower:
                topics.append(concept)

        return list(set(topics))  # Remove duplicates

    def _extract_cross_references(self, content: str) -> List[str]:
        """Extract references to other statutes"""
        citations = []

        # Florida statute references
        fla_pattern = re.compile(r"(?:section|s\.|§)\s*(\d+\.\d+)", re.IGNORECASE)
        for match in fla_pattern.finditer(content):
            citations.append(f"Fla. Stat. § {match.group(1)}")

        # Chapter references
        chapter_pattern = re.compile(r"chapter\s+(\d+)", re.IGNORECASE)
        for match in chapter_pattern.finditer(content):
            citations.append(f"Fla. Stat. Ch. {match.group(1)}")

        # Federal law references
        usc_pattern = re.compile(r"(\d+)\s+U\.S\.C\.\s*§?\s*(\d+)")
        for match in usc_pattern.finditer(content):
            citations.append(f"{match.group(1)} U.S.C. § {match.group(2)}")

        cfr_pattern = re.compile(r"(\d+)\s+C\.F\.R\.\s*§?\s*([\d.]+)")
        for match in cfr_pattern.finditer(content):
            citations.append(f"{match.group(1)} C.F.R. § {match.group(2)}")

        return list(set(citations))  # Remove duplicates

    async def _store_statute(
        self,
        entry: SharedKnowledgeEntry,
        chapter: Optional[str],
        source_url: Optional[str],
    ):
        """Store statute in shared vector database"""
        # Generate embedding for statute content
        text_for_embedding = f"{entry.identifier} {entry.title}\n{entry.content[:500]}"
        embedding, _ = await self.embedding_generator.generate_embedding_async(
            text_for_embedding
        )

        # Prepare metadata
        metadata = {
            "knowledge_type": entry.knowledge_type,
            "identifier": entry.identifier,
            "title": entry.title,
            "topics": json.dumps(entry.topics),
            "citations": json.dumps(entry.citations),
            "last_updated": entry.last_updated.isoformat(),
            "content_preview": entry.content[:500],  # Store preview for quick access
        }

        if chapter:
            metadata["chapter"] = chapter
        if entry.effective_date:
            metadata["effective_date"] = entry.effective_date.isoformat()
        if source_url:
            metadata["source_url"] = source_url

        # Store in shared collection
        point = {"id": entry.id, "vector": embedding, "payload": metadata}

        self.vector_store.client.upsert(
            collection_name=self.collection_name, points=[point]
        )

        logger.debug(f"Stored statute {entry.identifier} in shared collection")

    async def search_statutes(
        self, query: str, topic_filter: Optional[List[str]] = None, limit: int = 10
    ) -> List[SharedKnowledgeEntry]:
        """Search Florida statutes"""
        # Generate query embedding
        query_embedding, _ = await self.embedding_generator.generate_embedding_async(
            query
        )

        # Build filter
        filter_conditions = None
        if topic_filter:
            # Topics are stored as JSON array
            should_conditions = []
            for topic in topic_filter:
                should_conditions.append({"key": "topics", "match": {"text": topic}})
            filter_conditions = {"should": should_conditions}

        # Search
        results = self.vector_store.client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            query_filter=filter_conditions,
            limit=limit,
        )

        # Convert to knowledge entries
        entries = []
        for result in results:
            payload = result.payload
            entry = SharedKnowledgeEntry(
                id=result.id,
                knowledge_type=payload["knowledge_type"],
                identifier=payload["identifier"],
                title=payload["title"],
                content=payload.get("content_preview", ""),  # Would need full content
                topics=json.loads(payload["topics"]),
                citations=json.loads(payload["citations"]),
                last_updated=datetime.fromisoformat(payload["last_updated"]),
            )
            entries.append(entry)

        return entries

    async def get_statute_by_number(
        self, statute_number: str
    ) -> Optional[SharedKnowledgeEntry]:
        """Retrieve specific statute by number"""
        # Search by identifier
        filter_condition = {
            "must": [
                {
                    "key": "identifier",
                    "match": {"value": f"Fla. Stat. § {statute_number}"},
                }
            ]
        }

        results = self.vector_store.client.scroll(
            collection_name=self.collection_name,
            scroll_filter=filter_condition,
            limit=1,
            with_payload=True,
            with_vectors=False,
        )[0]

        if results:
            payload = results[0].payload
            return SharedKnowledgeEntry(
                id=results[0].id,
                knowledge_type=payload["knowledge_type"],
                identifier=payload["identifier"],
                title=payload["title"],
                content=payload.get("content_preview", ""),
                topics=json.loads(payload["topics"]),
                citations=json.loads(payload["citations"]),
                last_updated=datetime.fromisoformat(payload["last_updated"]),
            )

        return None

    async def load_common_statutes(self):
        """Load commonly referenced Florida statutes for personal injury cases"""
        common_statutes = [
            {
                "number": "768.81",
                "title": "Comparative fault",
                "content": """(1) DEFINITIONS.—As used in this section:
                (a) "Economic damages" means damages for past lost income and future lost income...
                (2) EFFECT OF CONTRIBUTORY FAULT.—In a negligence action, contributory fault chargeable 
                to the claimant diminishes proportionately the amount awarded as economic and 
                noneconomic damages for an injury attributable to the claimant's contributory fault...""",
            },
            {
                "number": "316.193",
                "title": "Driving under the influence",
                "content": """(1) A person is guilty of the offense of driving under the influence and is 
                subject to punishment as provided in subsection (2) if the person is driving or in 
                actual physical control of a vehicle within this state and:
                (a) The person is under the influence of alcoholic beverages...""",
            },
            {
                "number": "768.125",
                "title": "Admissibility of evidence relating to seat belts",
                "content": """In any action for damages for personal injuries or wrongful death arising 
                out of the ownership, maintenance, operation, or control of a motor vehicle, evidence 
                of the failure of the plaintiff to wear an available and operational seat belt...""",
            },
        ]

        for statute in common_statutes:
            await self.load_statute(
                statute_number=statute["number"],
                title=statute["title"],
                content=statute["content"],
                chapter="Chapter 768 - Negligence"
                if statute["number"].startswith("768")
                else "Chapter 316 - Traffic",
                effective_date=datetime(2023, 7, 1),  # Example date
            )

        logger.info("Loaded common Florida statutes")

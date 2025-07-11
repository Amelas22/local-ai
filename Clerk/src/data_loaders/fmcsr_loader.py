"""
Federal Motor Carrier Safety Regulations (FMCSR) Loader
Loads and indexes FMCSR for cross-case access in trucking/commercial vehicle cases
"""

import re
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import uuid

from src.models.fact_models import SharedKnowledgeEntry
from src.vector_storage.qdrant_store import QdrantVectorStore
from src.vector_storage.embeddings import EmbeddingGenerator
from qdrant_client.models import VectorParams, Distance

logger = logging.getLogger("clerk_api")


class FMCSRLoader:
    """
    Loads Federal Motor Carrier Safety Regulations into a shared collection.
    Provides efficient access to regulations for commercial vehicle cases.
    """

    def __init__(self):
        """Initialize FMCSR loader"""
        self.vector_store = QdrantVectorStore()
        self.embedding_generator = EmbeddingGenerator()

        # Shared collection name
        self.collection_name = "fmcsr_regulations"

        # Ensure collection exists
        self._ensure_collection_exists()

        # Regulation patterns
        self.regulation_patterns = self._compile_regulation_patterns()

        # Part descriptions for context
        self.part_descriptions = self._define_part_descriptions()

        logger.info("FMCSRLoader initialized")

    def _ensure_collection_exists(self):
        """Create FMCSR collection if it doesn't exist"""
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
                    logger.warning(f"Failed to connect to Qdrant (attempt {attempt + 1}/{max_retries}): {e}")
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
                    logger.error(f"Failed to create collection after {max_retries} attempts: {create_error}")
                    raise

    def _compile_regulation_patterns(self) -> Dict[str, re.Pattern]:
        """Compile regex patterns for FMCSR parsing"""
        return {
            # Section format: "§ 395.8" or "Section 395.8"
            "section": re.compile(r"(?:§|Section)\s*(\d{3})\.(\d+)(?:\.(\d+))?"),
            # Part header: "PART 395—HOURS OF SERVICE OF DRIVERS"
            "part_header": re.compile(
                r"^PART\s+(\d{3})—(.+)$", re.MULTILINE | re.IGNORECASE
            ),
            # Subpart: "Subpart A—General"
            "subpart": re.compile(
                r"^Subpart\s+([A-Z])—(.+)$", re.MULTILINE | re.IGNORECASE
            ),
            # Paragraph: "(a)" or "(1)" or "(i)"
            "paragraph": re.compile(r"^\s*\(([a-z]|\d+|[ivx]+)\)\s*(.+)", re.MULTILINE),
            # Cross-reference: "See § 395.2"
            "cross_ref": re.compile(r"(?:See|see)\s+§\s*(\d{3}\.\d+)"),
            # Effective date: "Effective: January 1, 2020"
            "effective": re.compile(
                r"Effective:\s*([A-Za-z]+ \d+, \d{4})", re.IGNORECASE
            ),
        }

    def _define_part_descriptions(self) -> Dict[str, Dict[str, str]]:
        """Define FMCSR parts and their descriptions"""
        return {
            "325": {
                "title": "Compliance with Interstate Motor Carrier Noise Emission Standards",
                "topics": ["noise", "emissions", "environmental"],
            },
            "350": {
                "title": "Commercial Motor Carrier Safety Assistance Program",
                "topics": ["safety", "assistance", "program"],
            },
            "382": {
                "title": "Controlled Substances and Alcohol Use and Testing",
                "topics": ["drug_testing", "alcohol", "substance_abuse", "testing"],
            },
            "383": {
                "title": "Commercial Driver's License Standards",
                "topics": ["cdl", "license", "qualification", "driver"],
            },
            "390": {
                "title": "Federal Motor Carrier Safety Regulations; General",
                "topics": ["general", "definitions", "applicability"],
            },
            "391": {
                "title": "Qualifications of Drivers",
                "topics": ["driver_qualification", "medical", "fitness", "hiring"],
            },
            "392": {
                "title": "Driving of Commercial Motor Vehicles",
                "topics": [
                    "driving",
                    "operation",
                    "safety_rules",
                    "prohibited_practices",
                ],
            },
            "393": {
                "title": "Parts and Accessories Necessary for Safe Operation",
                "topics": ["equipment", "maintenance", "inspection", "parts"],
            },
            "395": {
                "title": "Hours of Service of Drivers",
                "topics": ["hours_of_service", "logbook", "rest", "fatigue", "eld"],
            },
            "396": {
                "title": "Inspection, Repair, and Maintenance",
                "topics": ["inspection", "maintenance", "repair", "records"],
            },
            "397": {
                "title": "Transportation of Hazardous Materials",
                "topics": ["hazmat", "dangerous_goods", "routing", "safety"],
            },
            "398": {
                "title": "Transportation of Migrant Workers",
                "topics": ["migrant", "passenger", "worker_transport"],
            },
            "399": {
                "title": "Step, Handhold, and Deck Requirements",
                "topics": ["equipment", "safety_features", "specifications"],
            },
        }

    async def load_regulation(
        self,
        part: str,
        section: str,
        title: str,
        content: str,
        subpart: Optional[str] = None,
        effective_date: Optional[datetime] = None,
        source_url: Optional[str] = None,
    ) -> SharedKnowledgeEntry:
        """Load a single FMCSR regulation"""
        logger.info(f"Loading 49 CFR § {part}.{section}: {title}")

        # Generate unique ID using UUID
        reg_id = str(uuid.uuid4())

        # Get part information
        part_info = self.part_descriptions.get(part, {})
        topics = part_info.get("topics", [])

        # Extract additional topics from content
        topics.extend(self._extract_regulation_topics(title + " " + content))
        topics = list(set(topics))  # Remove duplicates

        # Extract cross-references
        citations = self._extract_cross_references(content, part)

        # Create knowledge entry
        entry = SharedKnowledgeEntry(
            id=reg_id,
            knowledge_type="fmcsr_regulation",
            identifier=f"49 CFR § {part}.{section}",
            title=title,
            content=content,
            effective_date=effective_date,
            topics=topics,
            citations=citations,
        )

        # Store in vector database
        await self._store_regulation(entry, part, subpart, source_url)

        return entry

    async def load_part(
        self, part_number: str, part_content: str, source_url: Optional[str] = None
    ) -> List[SharedKnowledgeEntry]:
        """Load an entire FMCSR part"""
        part_info = self.part_descriptions.get(part_number, {})
        part_title = part_info.get("title", f"Part {part_number}")

        logger.info(f"Loading 49 CFR Part {part_number}: {part_title}")

        entries = []

        # Parse sections within the part
        sections = self._parse_part_sections(part_content, part_number)

        current_subpart = None

        for section_data in sections:
            # Check if this is a subpart header
            if section_data.get("is_subpart"):
                current_subpart = section_data["subpart"]
                continue

            # Extract effective date if present
            effective_date = None
            if section_data.get("effective_date"):
                try:
                    from dateparser import parse

                    effective_date = parse(section_data["effective_date"])
                except:
                    pass

            # Load section
            entry = await self.load_regulation(
                part=part_number,
                section=section_data["section"],
                title=section_data["title"],
                content=section_data["content"],
                subpart=current_subpart,
                effective_date=effective_date,
                source_url=source_url,
            )
            entries.append(entry)

        logger.info(f"Loaded {len(entries)} sections from Part {part_number}")
        return entries

    def _parse_part_sections(
        self, part_content: str, part_number: str
    ) -> List[Dict[str, Any]]:
        """Parse part content into individual sections"""
        sections = []

        # Split content into lines for processing
        lines = part_content.split("\n")

        current_section = None
        current_content = []

        for line in lines:
            # Check for subpart
            subpart_match = self.regulation_patterns["subpart"].match(line)
            if subpart_match:
                # Save current section if exists
                if current_section:
                    sections.append(
                        {
                            "section": current_section["number"],
                            "title": current_section["title"],
                            "content": "\n".join(current_content).strip(),
                            "is_subpart": False,
                        }
                    )
                    current_content = []
                    current_section = None

                # Add subpart marker
                sections.append(
                    {
                        "is_subpart": True,
                        "subpart": f"Subpart {subpart_match.group(1)} - {subpart_match.group(2)}",
                    }
                )
                continue

            # Check for section header
            section_match = re.match(
                rf"^§\s*{part_number}\.(\d+)\s+(.+)$", line.strip()
            )

            if section_match:
                # Save previous section
                if current_section:
                    sections.append(
                        {
                            "section": current_section["number"],
                            "title": current_section["title"],
                            "content": "\n".join(current_content).strip(),
                            "is_subpart": False,
                        }
                    )

                # Start new section
                current_section = {
                    "number": section_match.group(1),
                    "title": section_match.group(2).rstrip("."),
                }
                current_content = []
            else:
                # Add to current section content
                current_content.append(line)

        # Save last section
        if current_section:
            sections.append(
                {
                    "section": current_section["number"],
                    "title": current_section["title"],
                    "content": "\n".join(current_content).strip(),
                    "is_subpart": False,
                }
            )

        return sections

    def _extract_regulation_topics(self, text: str) -> List[str]:
        """Extract relevant topics from regulation text"""
        topics = []
        text_lower = text.lower()

        # Topic keywords specific to FMCSR
        topic_keywords = {
            "hours_of_service": [
                "hours of service",
                "11-hour",
                "14-hour",
                "70-hour",
                "60-hour",
                "rest period",
            ],
            "driver_qualification": [
                "qualified",
                "disqualified",
                "medical certificate",
                "physical examination",
            ],
            "vehicle_inspection": [
                "inspection",
                "pre-trip",
                "post-trip",
                "annual inspection",
            ],
            "drug_testing": [
                "drug test",
                "alcohol test",
                "controlled substance",
                "random testing",
            ],
            "cdl": ["commercial driver", "cdl", "endorsement", "restriction"],
            "eld": ["electronic logging", "eld", "aobrd", "logbook"],
            "maintenance": ["maintenance", "repair", "systematic inspection"],
            "hazmat": ["hazardous", "hazmat", "dangerous", "placard"],
            "safety": ["safety", "safe operation", "unsafe", "violation"],
            "training": ["training", "instruction", "entry-level driver"],
            "fatigue": ["fatigue", "rest", "sleeper berth", "off-duty"],
            "speed": ["speed", "speed limiter", "speeding"],
            "brakes": ["brake", "braking system", "air brake"],
            "tires": ["tire", "tread depth", "tire pressure"],
            "lighting": ["light", "lamp", "reflector", "conspicuity"],
        }

        for topic, keywords in topic_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                topics.append(topic)

        return topics

    def _extract_cross_references(self, content: str, current_part: str) -> List[str]:
        """Extract references to other regulations"""
        citations = []

        # Internal FMCSR references
        for match in self.regulation_patterns["cross_ref"].finditer(content):
            citations.append(f"49 CFR § {match.group(1)}")

        # References to other CFR titles
        other_cfr = re.compile(r"(\d+)\s+CFR\s+(?:Part\s+)?(\d+)(?:\.(\d+))?")
        for match in other_cfr.finditer(content):
            title = match.group(1)
            part = match.group(2)
            section = match.group(3)
            if section:
                citations.append(f"{title} CFR § {part}.{section}")
            else:
                citations.append(f"{title} CFR Part {part}")

        # References to USC
        usc_pattern = re.compile(r"(\d+)\s+U\.S\.C\.\s*(?:§\s*)?(\d+)")
        for match in usc_pattern.finditer(content):
            citations.append(f"{match.group(1)} U.S.C. § {match.group(2)}")

        return list(set(citations))  # Remove duplicates

    async def _store_regulation(
        self,
        entry: SharedKnowledgeEntry,
        part: str,
        subpart: Optional[str],
        source_url: Optional[str],
    ):
        """Store regulation in shared vector database"""
        # Generate embedding
        text_for_embedding = f"{entry.identifier} {entry.title}\n{entry.content[:500]}"
        embedding, _ = await self.embedding_generator.generate_embedding_async(
            text_for_embedding
        )

        # Prepare metadata
        metadata = {
            "knowledge_type": entry.knowledge_type,
            "identifier": entry.identifier,
            "title": entry.title,
            "part": part,
            "part_title": self.part_descriptions.get(part, {}).get("title", ""),
            "topics": json.dumps(entry.topics),
            "citations": json.dumps(entry.citations),
            "last_updated": entry.last_updated.isoformat(),
            "content_preview": entry.content[:500],
        }

        if subpart:
            metadata["subpart"] = subpart
        if entry.effective_date:
            metadata["effective_date"] = entry.effective_date.isoformat()
        if source_url:
            metadata["source_url"] = source_url

        # Store in shared collection
        point = {"id": entry.id, "vector": embedding, "payload": metadata}

        self.vector_store.client.upsert(
            collection_name=self.collection_name, points=[point]
        )

        logger.debug(f"Stored regulation {entry.identifier} in shared collection")

    async def search_regulations(
        self,
        query: str,
        part_filter: Optional[List[str]] = None,
        topic_filter: Optional[List[str]] = None,
        limit: int = 10,
    ) -> List[SharedKnowledgeEntry]:
        """Search FMCSR regulations"""
        # Generate query embedding
        query_embedding, _ = await self.embedding_generator.generate_embedding_async(
            query
        )

        # Build filter
        must_conditions = []

        if part_filter:
            should_conditions = []
            for part in part_filter:
                should_conditions.append({"key": "part", "match": {"value": part}})
            must_conditions.append({"should": should_conditions})

        if topic_filter:
            should_conditions = []
            for topic in topic_filter:
                should_conditions.append({"key": "topics", "match": {"text": topic}})
            must_conditions.append({"should": should_conditions})

        filter_conditions = {"must": must_conditions} if must_conditions else None

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
                content=payload.get("content_preview", ""),
                topics=json.loads(payload["topics"]),
                citations=json.loads(payload["citations"]),
                last_updated=datetime.fromisoformat(payload["last_updated"]),
            )
            entries.append(entry)

        return entries

    async def get_regulation_by_section(
        self, part: str, section: str
    ) -> Optional[SharedKnowledgeEntry]:
        """Retrieve specific regulation by part and section"""
        identifier = f"49 CFR § {part}.{section}"

        filter_condition = {
            "must": [{"key": "identifier", "match": {"value": identifier}}]
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

    async def load_common_regulations(self):
        """Load commonly referenced FMCSR for trucking cases"""
        common_regulations = [
            {
                "part": "395",
                "section": "8",
                "title": "Driver's record of duty status",
                "content": """(a) Except for a private motor carrier of passengers (nonbusiness), 
                every motor carrier shall require every driver to record his/her duty status...
                (1) No driver shall operate a commercial motor vehicle, and a motor carrier shall not
                require or permit a driver to operate a commercial motor vehicle, unless the driver's
                record of duty status is current...""",
            },
            {
                "part": "392",
                "section": "3",
                "title": "Ill or fatigued operator",
                "content": """No driver shall operate a commercial motor vehicle, and a motor carrier 
                shall not require or permit a driver to operate a commercial motor vehicle, while the 
                driver's ability or alertness is so impaired, or so likely to become impaired, through 
                fatigue, illness, or any other cause...""",
            },
            {
                "part": "396",
                "section": "3",
                "title": "Inspection, repair, and maintenance",
                "content": """(a) General. Every motor carrier and intermodal equipment provider must 
                systematically inspect, repair, and maintain, or cause to be systematically inspected, 
                repaired, and maintained, all motor vehicles and intermodal equipment subject to its 
                control...""",
            },
            {
                "part": "391",
                "section": "11",
                "title": "General qualifications of drivers",
                "content": """(a) A person shall not drive a commercial motor vehicle unless he/she is 
                qualified to drive a commercial motor vehicle. Except as provided in § 391.63, a motor 
                carrier shall not require or permit a person to drive a commercial motor vehicle unless 
                that person is qualified to drive a commercial motor vehicle...""",
            },
            {
                "part": "382",
                "section": "301",
                "title": "Pre-employment testing",
                "content": """(a) Prior to the first time a driver performs safety-sensitive functions 
                for an employer, the driver shall undergo testing for controlled substances as a 
                condition prior to being used, unless the employer uses the exception in paragraph (b) 
                of this section...""",
            },
        ]

        for reg in common_regulations:
            await self.load_regulation(
                part=reg["part"],
                section=reg["section"],
                title=reg["title"],
                content=reg["content"],
                effective_date=datetime(2023, 1, 1),  # Example date
            )

        logger.info("Loaded common FMCSR regulations")

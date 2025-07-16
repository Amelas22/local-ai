"""
Evidence Discovery Agent for Motion Drafting
Helps find and organize source documents to use as exhibits
"""

import logging
from typing import List, Dict, Any, Optional
import json

import openai
from pydantic import BaseModel

from src.models.source_document_models import DocumentType
from src.document_processing.source_document_indexer import SourceDocumentIndexer
from src.vector_storage.qdrant_store import QdrantVectorStore
from src.vector_storage.embeddings import EmbeddingGenerator
from config.settings import settings

logger = logging.getLogger("clerk_api")


class ExhibitSuggestion(BaseModel):
    """Suggestion for using a source document as an exhibit"""

    source_document_id: str
    suggested_exhibit_label: str  # e.g., "Exhibit A"
    purpose: str  # Why this document supports the argument
    key_pages: List[int]  # Specific pages to cite
    key_excerpts: List[str]  # Important quotes
    relevance_score: float


class ArgumentEvidence(BaseModel):
    """Evidence package for a specific legal argument"""

    argument: str
    supporting_documents: List[ExhibitSuggestion]
    evidence_strategy: str  # How to use these documents together


class EvidenceDiscoveryAgent:
    """
    AI agent that helps discover and organize evidence for legal motions.
    Focuses on finding source documents that support specific arguments.
    """

    def __init__(self, case_name: str):
        """Initialize evidence discovery agent"""
        self.case_name = case_name
        self.source_indexer = SourceDocumentIndexer(case_name)
        self.vector_store = QdrantVectorStore()
        self.embedding_generator = EmbeddingGenerator()
        self.openai_client = openai.OpenAI(api_key=settings.openai.api_key)

        logger.info(f"EvidenceDiscoveryAgent initialized for case: {case_name}")

    async def find_evidence_for_argument(
        self, argument: str, motion_type: str, context: Optional[str] = None
    ) -> ArgumentEvidence:
        """Find source documents that support a specific legal argument"""
        logger.info(f"Finding evidence for argument: {argument[:100]}...")

        # Analyze the argument to understand what evidence is needed
        evidence_needs = await self._analyze_evidence_needs(argument, motion_type)

        # Search for relevant documents
        all_results = []
        for need in evidence_needs:
            results = await self.source_indexer.search_evidence(
                query=need["query"],
                document_types=need.get("document_types"),
                relevance_tags=need.get("relevance_tags"),
                limit=10,
            )
            all_results.extend(results)

        # Rank and organize the results
        exhibit_suggestions = await self._create_exhibit_suggestions(
            argument, all_results, motion_type
        )

        # Create evidence strategy
        strategy = await self._create_evidence_strategy(
            argument, exhibit_suggestions, motion_type
        )

        return ArgumentEvidence(
            argument=argument,
            supporting_documents=exhibit_suggestions,
            evidence_strategy=strategy,
        )

    async def _analyze_evidence_needs(
        self, argument: str, motion_type: str
    ) -> List[Dict[str, Any]]:
        """Analyze what types of evidence would support this argument"""

        prompt = f"""Analyze this legal argument and determine what evidence is needed.

Motion Type: {motion_type}
Argument: {argument}

For this argument, identify:
1. Types of documents needed (e.g., medical records, depositions, police reports)
2. Key search queries to find relevant evidence
3. Relevance categories (liability, damages, causation, etc.)

Format as JSON array with objects containing:
- query: search query string
- document_types: array of document types
- relevance_tags: array of relevance categories
"""

        try:
            response = self.openai_client.chat.completions.create(
                model=settings.ai.default_model,
                messages=[
                    {"role": "system", "content": "You are a legal evidence analyst."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                response_format={"type": "json_object"},
            )

            result = json.loads(response.choices[0].message.content)
            return result.get("evidence_needs", [])

        except Exception as e:
            logger.error(f"Error analyzing evidence needs: {e}")
            # Fallback to basic search
            return [{"query": argument, "document_types": None, "relevance_tags": None}]

    async def _create_exhibit_suggestions(
        self, argument: str, search_results: List[Dict[str, Any]], motion_type: str
    ) -> List[ExhibitSuggestion]:
        """Create exhibit suggestions from search results"""

        suggestions = []
        exhibit_labels = self._generate_exhibit_labels(len(search_results))

        for i, result in enumerate(search_results[:10]):  # Limit to top 10
            # Analyze how this document supports the argument
            purpose = await self._analyze_document_relevance(
                argument, result, motion_type
            )

            if purpose and result["relevance_score"] > 0.7:
                suggestion = ExhibitSuggestion(
                    source_document_id=result["document_id"],
                    suggested_exhibit_label=exhibit_labels[i],
                    purpose=purpose,
                    key_pages=result.get("key_pages", []),
                    key_excerpts=[],  # Would need to extract from full document
                    relevance_score=result["relevance_score"],
                )
                suggestions.append(suggestion)

        # Sort by relevance
        suggestions.sort(key=lambda x: x.relevance_score, reverse=True)

        return suggestions[:5]  # Return top 5

    async def _analyze_document_relevance(
        self, argument: str, document: Dict[str, Any], motion_type: str
    ) -> Optional[str]:
        """Analyze how a specific document supports the argument"""

        prompt = f"""Analyze how this document supports the legal argument.

Motion Type: {motion_type}
Argument: {argument}

Document:
- Title: {document["title"]}
- Type: {document["document_type"]}
- Description: {document["description"]}

If this document supports the argument, explain how in 1-2 sentences.
If it doesn't support the argument, respond with "NOT RELEVANT".
"""

        try:
            response = self.openai_client.chat.completions.create(
                model=settings.ai.default_model,
                messages=[
                    {"role": "system", "content": "You are a legal analyst."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=200,
            )

            purpose = response.choices[0].message.content.strip()

            if "NOT RELEVANT" in purpose:
                return None

            return purpose

        except Exception as e:
            logger.error(f"Error analyzing document relevance: {e}")
            return None

    async def _create_evidence_strategy(
        self, argument: str, suggestions: List[ExhibitSuggestion], motion_type: str
    ) -> str:
        """Create a strategy for using the evidence together"""

        if not suggestions:
            return (
                "No supporting evidence found. Consider gathering additional discovery."
            )

        doc_summary = "\n".join(
            [f"- {s.suggested_exhibit_label}: {s.purpose}" for s in suggestions]
        )

        prompt = f"""Create a brief evidence strategy for this argument.

Motion Type: {motion_type}
Argument: {argument}

Available Evidence:
{doc_summary}

Write a 2-3 sentence strategy for how to use these documents together to support the argument.
Focus on the logical flow and how they build upon each other.
"""

        try:
            response = self.openai_client.chat.completions.create(
                model=settings.ai.default_model,
                messages=[
                    {"role": "system", "content": "You are a legal strategist."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=200,
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.error(f"Error creating evidence strategy: {e}")
            return "Present evidence in chronological order to establish timeline and causation."

    def _generate_exhibit_labels(self, count: int) -> List[str]:
        """Generate exhibit labels (A, B, C... AA, BB, CC...)"""
        labels = []
        for i in range(count):
            if i < 26:
                labels.append(f"Exhibit {chr(65 + i)}")
            else:
                # Double letters for 26+
                idx = i - 26
                labels.append(f"Exhibit {chr(65 + idx % 26)}{chr(65 + idx % 26)}")
        return labels

    async def suggest_exhibits_for_motion(
        self, motion_sections: List[Dict[str, str]], motion_type: str
    ) -> List[ArgumentEvidence]:
        """Suggest exhibits for an entire motion outline"""
        logger.info(f"Suggesting exhibits for {len(motion_sections)} sections")

        evidence_packages = []

        for section in motion_sections:
            if section.get("type") in ["argument", "sub_argument"]:
                evidence = await self.find_evidence_for_argument(
                    section.get("content", ""),
                    motion_type,
                    context=section.get("context"),
                )
                evidence_packages.append(evidence)

        return evidence_packages

    async def search_by_topic(
        self, topic: str, document_types: Optional[List[DocumentType]] = None
    ) -> List[Dict[str, Any]]:
        """Simple topic-based search for source documents"""
        return await self.source_indexer.search_evidence(
            query=topic, document_types=document_types, limit=20
        )

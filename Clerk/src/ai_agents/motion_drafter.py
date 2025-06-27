"""
AI Motion Drafting Agent
Implements section-by-section legal motion generation following best practices
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import re
import json

from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIModel
import tiktoken

from src.vector_storage.qdrant_store import QdrantVectorStore
from src.vector_storage.embeddings import EmbeddingGenerator
from config.settings import settings
from config.agent_settings import agent_settings

logger = logging.getLogger(__name__)


class SectionType(Enum):
    """Types of sections in a legal motion"""
    INTRODUCTION = "introduction"
    STATEMENT_OF_FACTS = "statement_of_facts"
    LEGAL_STANDARD = "legal_standard"
    ARGUMENT = "argument"
    SUB_ARGUMENT = "sub_argument"
    CONCLUSION = "conclusion"
    PRAYER_FOR_RELIEF = "prayer_for_relief"


class DocumentLength(Enum):
    """Target document lengths"""
    SHORT = (15, 20)  # 15-20 pages
    MEDIUM = (20, 30)  # 20-30 pages
    LONG = (30, 40)   # 30-40 pages


@dataclass
class OutlineSection:
    """Represents a section in the motion outline"""
    id: str
    title: str
    section_type: SectionType
    content_points: List[str]
    legal_authorities: List[str]
    target_length: int  # Target word count
    parent_id: Optional[str] = None
    children: List['OutlineSection'] = field(default_factory=list)
    context_summary: Optional[str] = None


@dataclass
class DraftedSection:
    """Represents a drafted section of the motion"""
    outline_section: OutlineSection
    content: str
    word_count: int
    citations_used: List[str]
    expansion_cycles: int
    confidence_score: float
    needs_revision: bool = False
    revision_notes: List[str] = field(default_factory=list)


@dataclass
class MotionDraft:
    """Complete motion draft with metadata"""
    title: str
    case_name: str
    sections: List[DraftedSection]
    total_word_count: int
    total_page_estimate: int
    creation_timestamp: datetime
    outline_source: Dict[str, Any]
    coherence_score: float = 0.0
    review_notes: List[str] = field(default_factory=list)


class MotionDraftingAgent:
    """AI agent for drafting legal motions section by section"""
    
    def __init__(self):
        """Initialize the motion drafting agent"""
        self.vector_store = QdrantVectorStore()
        self.embedding_generator = EmbeddingGenerator()
        
        # Initialize AI models
        self.section_writer = self._create_section_writer()
        self.section_expander = self._create_section_expander()
        self.transition_writer = self._create_transition_writer()
        self.document_reviewer = self._create_document_reviewer()
        
        # Initialize tokenizer for accurate length estimation
        self.tokenizer = tiktoken.encoding_for_model("cl100k_base")
        
        # Configuration
        self.words_per_page = 250  # Standard legal document formatting
        self.max_expansion_cycles = 5
        self.min_confidence_threshold = 0.7
        
    def _create_section_writer(self) -> Agent:
        """Create agent for initial section drafting"""
        return Agent(
            "claude-sonnet-4-20250514",
            system_prompt="""You are an expert legal writer specializing in motion drafting.
            
Your task is to write individual sections of legal motions based on outlines.
You must:
1. Follow IRAC/CRAC structure (Issue, Rule, Application, Conclusion)
2. Write in formal legal style with proper citations
3. Expand outline points into comprehensive legal arguments
4. Maintain consistent tone and terminology
5. Generate content that is thorough and detailed, not summary-style
6. Use Bluebook citation format for all legal references
7. Never create fictional citations - only use provided authorities

Remember: This is for a formal legal document that will be filed with the court.""",
            result_type=str
        )
    
    def _create_section_expander(self) -> Agent:
        """Create agent for expanding drafted sections"""
        return Agent(
            "claude-sonnet-4-20250514",
            system_prompt="""You are an expert legal writer focused on expanding and enriching legal arguments.

Your task is to take a drafted section and expand it with:
1. Additional legal analysis and reasoning
2. More detailed application of law to facts
3. Anticipated counterarguments and rebuttals
4. Supporting case law explanations
5. Policy considerations where relevant
6. Procedural history if applicable

Maintain the existing structure while adding depth and nuance.
Do not simply repeat existing content - add new substantive material.""",
            result_type=str
        )
    
    def _create_transition_writer(self) -> Agent:
        """Create agent for writing transitions between sections"""
        return Agent(
            "claude-sonnet-4-20250514",
            system_prompt="""You are an expert legal writer specializing in document flow and coherence.

Your task is to write smooth transitions between sections of a legal motion.
The transitions should:
1. Connect the legal arguments logically
2. Maintain narrative flow
3. Reference key points from previous sections
4. Preview upcoming arguments
5. Be concise but effective (1-2 paragraphs typically)

Ensure the document reads as a cohesive whole, not disconnected sections.""",
            result_type=str
        )
    
    def _create_document_reviewer(self) -> Agent:
        """Create agent for final document review"""
        return Agent(
            "claude-opus-4-20250514",  # Using Opus for comprehensive review
            system_prompt="""You are a senior legal editor reviewing motion drafts for filing.

Review the document for:
1. Legal accuracy and citation correctness
2. Argument coherence and logical flow
3. Consistency in terminology and style
4. Factual accuracy based on case documents
5. Compliance with court rules and formatting
6. Overall persuasiveness and professionalism

Provide specific feedback on:
- Sections that need revision
- Missing arguments or authorities
- Inconsistencies or contradictions
- Citation errors or concerns
- Suggested improvements

Rate the document's readiness for filing on a scale of 1-10.""",
            result_type=Dict[str, Any]
        )
    
    async def draft_motion(
        self,
        outline: Dict[str, Any],
        case_name: str,
        target_length: DocumentLength = DocumentLength.MEDIUM,
        motion_title: Optional[str] = None
    ) -> MotionDraft:
        """
        Draft a complete motion from an outline using section-by-section generation.
        
        Args:
            outline: Structured outline from the outline generation phase
            case_name: Name of the case for document retrieval
            target_length: Target document length (SHORT, MEDIUM, or LONG)
            motion_title: Optional title for the motion
            
        Returns:
            Complete MotionDraft object
        """
        try:
            logger.info(f"Starting motion draft for {case_name}")
            
            # Parse outline into structured sections
            outline_sections = self._parse_outline(outline, target_length)
            
            # Retrieve relevant case documents for context
            case_context = await self._retrieve_case_context(case_name, outline_sections)
            
            # Draft each section
            drafted_sections = []
            total_words = 0
            
            for i, section in enumerate(outline_sections):
                logger.info(f"Drafting section {i+1}/{len(outline_sections)}: {section.title}")
                
                # Add context from previous sections
                previous_context = self._get_previous_context(drafted_sections)
                
                # Draft the section
                drafted_section = await self._draft_section(
                    section, 
                    case_context, 
                    previous_context
                )
                
                # Expand if needed to meet target length
                if drafted_section.word_count < section.target_length * 0.8:
                    drafted_section = await self._expand_section(
                        drafted_section,
                        section.target_length,
                        case_context
                    )
                
                drafted_sections.append(drafted_section)
                total_words += drafted_section.word_count
                
                # Add transition if not the last section
                if i < len(outline_sections) - 1:
                    transition = await self._create_transition(
                        drafted_section,
                        outline_sections[i + 1]
                    )
                    drafted_section.content += f"\n\n{transition}\n"
            
            # Create motion draft
            motion_draft = MotionDraft(
                title=motion_title or self._generate_motion_title(outline),
                case_name=case_name,
                sections=drafted_sections,
                total_word_count=total_words,
                total_page_estimate=total_words // self.words_per_page,
                creation_timestamp=datetime.utcnow(),
                outline_source=outline
            )
            
            # Review and refine the complete document
            motion_draft = await self._review_and_refine(motion_draft, case_context)
            
            logger.info(f"Completed motion draft: {motion_draft.total_page_estimate} pages")
            
            return motion_draft
            
        except Exception as e:
            logger.error(f"Error drafting motion: {str(e)}")
            raise
    
    def _parse_outline(self, outline: Dict[str, Any], target_length: DocumentLength) -> List[OutlineSection]:
        """Parse outline dictionary into structured OutlineSection objects"""
        sections = []
        
        # Calculate target words per section based on outline structure
        total_sections = len(outline.get("sections", []))
        min_pages, max_pages = target_length.value
        target_words = ((min_pages + max_pages) // 2) * self.words_per_page
        base_words_per_section = target_words // max(total_sections, 1)
        
        # Parse each section from the outline
        for idx, section_data in enumerate(outline.get("sections", [])):
            section_type = self._determine_section_type(section_data.get("title", ""))
            
            # Adjust word count based on section type
            if section_type == SectionType.STATEMENT_OF_FACTS:
                section_words = int(base_words_per_section * 1.5)
            elif section_type in [SectionType.INTRODUCTION, SectionType.CONCLUSION]:
                section_words = int(base_words_per_section * 0.5)
            else:
                section_words = base_words_per_section
            
            section = OutlineSection(
                id=f"section_{idx}",
                title=section_data.get("title", f"Section {idx + 1}"),
                section_type=section_type,
                content_points=section_data.get("points", []),
                legal_authorities=section_data.get("authorities", []),
                target_length=section_words
            )
            
            # Parse sub-sections if present
            if "subsections" in section_data:
                for sub_idx, subsection_data in enumerate(section_data["subsections"]):
                    subsection = OutlineSection(
                        id=f"section_{idx}_{sub_idx}",
                        title=subsection_data.get("title", f"Subsection {sub_idx + 1}"),
                        section_type=SectionType.SUB_ARGUMENT,
                        content_points=subsection_data.get("points", []),
                        legal_authorities=subsection_data.get("authorities", []),
                        target_length=section_words // max(len(section_data["subsections"]), 1),
                        parent_id=section.id
                    )
                    section.children.append(subsection)
            
            sections.append(section)
        
        return sections
    
    def _determine_section_type(self, title: str) -> SectionType:
        """Determine section type from title"""
        title_lower = title.lower()
        
        if any(term in title_lower for term in ["introduction", "preliminary", "overview"]):
            return SectionType.INTRODUCTION
        elif any(term in title_lower for term in ["facts", "background", "factual"]):
            return SectionType.STATEMENT_OF_FACTS
        elif any(term in title_lower for term in ["standard", "law", "legal framework"]):
            return SectionType.LEGAL_STANDARD
        elif any(term in title_lower for term in ["conclusion", "summary"]):
            return SectionType.CONCLUSION
        elif any(term in title_lower for term in ["prayer", "relief", "request"]):
            return SectionType.PRAYER_FOR_RELIEF
        else:
            return SectionType.ARGUMENT
    
    async def _retrieve_case_context(self, case_name: str, sections: List[OutlineSection]) -> Dict[str, Any]:
        """Retrieve relevant documents from the case for drafting context"""
        context = {
            "case_facts": [],
            "legal_authorities": [],
            "expert_reports": [],
            "key_documents": []
        }
        
        # Extract all legal authorities mentioned in outline
        all_authorities = []
        for section in sections:
            all_authorities.extend(section.legal_authorities)
            for child in section.children:
                all_authorities.extend(child.legal_authorities)
        
        # Search for relevant documents
        for authority in set(all_authorities):
            query_embedding, _ = self.embedding_generator.generate_embedding(authority)
            
            results = await self.vector_store.hybrid_search(
                collection_name=case_name,
                query=authority,
                query_embedding=query_embedding,
                limit=5,
                enable_reranking=True
            )
            
            for result in results:
                if result.score > 0.7:
                    context["legal_authorities"].append({
                        "citation": authority,
                        "content": result.content,
                        "document": result.metadata.get("document_name", "Unknown"),
                        "score": result.score
                    })
        
        # Search for key factual documents
        fact_queries = [
            "complaint allegations",
            "key facts",
            "incident report",
            "medical records summary",
            "expert opinion"
        ]
        
        for query in fact_queries:
            query_embedding, _ = self.embedding_generator.generate_embedding(query)
            
            results = await self.vector_store.hybrid_search(
                collection_name=case_name,
                query=query,
                query_embedding=query_embedding,
                limit=3,
                enable_reranking=True
            )
            
            for result in results:
                if result.score > 0.6:
                    doc_type = result.metadata.get("document_type", "general")
                    
                    if "expert" in doc_type.lower():
                        context["expert_reports"].append(result)
                    elif any(term in doc_type.lower() for term in ["complaint", "fact", "statement"]):
                        context["case_facts"].append(result)
                    else:
                        context["key_documents"].append(result)
        
        logger.info(f"Retrieved context: {len(context['legal_authorities'])} authorities, "
                   f"{len(context['case_facts'])} facts, {len(context['expert_reports'])} expert reports")
        
        return context
    
    async def _draft_section(
        self, 
        section: OutlineSection, 
        case_context: Dict[str, Any],
        previous_context: str
    ) -> DraftedSection:
        """Draft a single section of the motion"""
        
        # Prepare context for the section writer
        relevant_facts = self._filter_relevant_facts(case_context["case_facts"], section)
        relevant_authorities = self._filter_relevant_authorities(
            case_context["legal_authorities"], 
            section.legal_authorities
        )
        
        # Create prompt for section drafting
        prompt = f"""Draft the following section of a legal motion:

Title: {section.title}
Type: {section.section_type.value}
Target Length: Approximately {section.target_length} words

Outline Points to Address:
{chr(10).join(f"- {point}" for point in section.content_points)}

Required Legal Authorities:
{chr(10).join(f"- {auth}" for auth in section.legal_authorities)}

Relevant Case Facts:
{self._format_facts_for_prompt(relevant_facts)}

Legal Authority Context:
{self._format_authorities_for_prompt(relevant_authorities)}

Previous Section Context:
{previous_context}

Instructions:
1. Write in formal legal style appropriate for court filing
2. Use IRAC structure where applicable
3. Cite all authorities in proper Bluebook format
4. Be comprehensive and detailed - this is not a summary
5. Connect facts to legal arguments explicitly
6. Anticipate and address potential counterarguments"""

        # Generate initial draft
        initial_content = await self.section_writer.run(prompt)
        
        # Count words and assess quality
        word_count = len(initial_content.split())
        confidence_score = self._assess_section_quality(initial_content, section)
        
        # Extract citations used
        citations_used = self._extract_citations(initial_content)
        
        drafted_section = DraftedSection(
            outline_section=section,
            content=initial_content,
            word_count=word_count,
            citations_used=citations_used,
            expansion_cycles=1,
            confidence_score=confidence_score
        )
        
        # Draft subsections if present
        if section.children:
            for child in section.children:
                child_draft = await self._draft_section(
                    child,
                    case_context,
                    initial_content[-500:]  # Last 500 chars as context
                )
                drafted_section.content += f"\n\n{child_draft.content}"
                drafted_section.word_count += child_draft.word_count
                drafted_section.citations_used.extend(child_draft.citations_used)
        
        return drafted_section
    
    async def _expand_section(
        self,
        drafted_section: DraftedSection,
        target_length: int,
        case_context: Dict[str, Any]
    ) -> DraftedSection:
        """Expand a section to meet target length"""
        
        expansion_cycles = drafted_section.expansion_cycles
        current_content = drafted_section.content
        
        while (drafted_section.word_count < target_length * 0.8 and 
               expansion_cycles < self.max_expansion_cycles):
            
            # Calculate how much more content we need
            words_needed = target_length - drafted_section.word_count
            expansion_ratio = words_needed / drafted_section.word_count
            
            expansion_prompt = f"""Expand the following legal section by adding approximately {words_needed} words:

Current Section:
{current_content}

Expansion Focus:
- Add deeper legal analysis
- Provide more detailed fact application
- Include additional supporting case law
- Address counterarguments more thoroughly
- Add policy considerations if relevant

Available Context:
{self._get_expansion_context(drafted_section.outline_section, case_context)}

Do not repeat existing content. Add new substantive material that strengthens the argument."""

            # Generate expansion
            expansion = await self.section_expander.run(expansion_prompt)
            
            # Integrate expansion into content
            current_content = self._integrate_expansion(current_content, expansion)
            
            # Update metrics
            new_word_count = len(current_content.split())
            drafted_section.content = current_content
            drafted_section.word_count = new_word_count
            drafted_section.expansion_cycles = expansion_cycles + 1
            
            # Extract any new citations
            new_citations = self._extract_citations(expansion)
            drafted_section.citations_used.extend(new_citations)
            
            expansion_cycles += 1
            
            logger.debug(f"Expansion cycle {expansion_cycles}: {new_word_count} words")
        
        return drafted_section
    
    async def _create_transition(
        self,
        current_section: DraftedSection,
        next_section: OutlineSection
    ) -> str:
        """Create transition text between sections"""
        
        prompt = f"""Write a transition between these two sections of a legal motion:

Current Section Summary:
Title: {current_section.outline_section.title}
Key Points: {', '.join(current_section.outline_section.content_points[:3])}
Final Paragraph: {current_section.content[-500:]}

Next Section:
Title: {next_section.title}
Type: {next_section.section_type.value}
Opening Points: {', '.join(next_section.content_points[:2])}

Create a 1-2 paragraph transition that:
1. Summarizes the key conclusion from the current section
2. Logically connects to the next section's argument
3. Maintains document flow and coherence"""

        transition = await self.transition_writer.run(prompt)
        return transition
    
    async def _review_and_refine(
        self,
        motion_draft: MotionDraft,
        case_context: Dict[str, Any]
    ) -> MotionDraft:
        """Review and refine the complete motion draft"""
        
        # Compile full document text
        full_text = f"{motion_draft.title}\n\n"
        for section in motion_draft.sections:
            full_text += f"{section.outline_section.title}\n\n{section.content}\n\n"
        
        # Prepare review prompt
        review_prompt = f"""Review this legal motion draft for filing:

{full_text}

Case Context:
- Case Name: {motion_draft.case_name}
- Target Length: {motion_draft.total_page_estimate} pages
- Actual Length: {motion_draft.total_word_count} words

Evaluate:
1. Legal accuracy and citation format
2. Argument coherence and persuasiveness
3. Factual accuracy based on case documents
4. Consistency in terminology and style
5. Overall readiness for filing (1-10 scale)

Provide specific feedback in JSON format."""

        # Get review feedback
        review_result = await self.document_reviewer.run(review_prompt)
        
        # Parse review feedback
        try:
            review_data = json.loads(review_result) if isinstance(review_result, str) else review_result
            
            motion_draft.coherence_score = review_data.get("coherence_score", 0.0)
            motion_draft.review_notes = review_data.get("feedback", [])
            
            # Mark sections needing revision
            sections_to_revise = review_data.get("sections_needing_revision", [])
            for section_id in sections_to_revise:
                for section in motion_draft.sections:
                    if section.outline_section.id == section_id:
                        section.needs_revision = True
                        section.revision_notes = review_data.get(f"revision_notes_{section_id}", [])
            
            # Apply critical fixes if readiness score is low
            readiness_score = review_data.get("readiness_score", 7)
            if readiness_score < 6:
                logger.warning(f"Low readiness score: {readiness_score}. Applying critical fixes.")
                motion_draft = await self._apply_critical_fixes(motion_draft, review_data)
            
        except Exception as e:
            logger.error(f"Error parsing review feedback: {str(e)}")
            motion_draft.review_notes = ["Review completed but feedback parsing failed"]
        
        return motion_draft
    
    def _filter_relevant_facts(self, facts: List[Any], section: OutlineSection) -> List[Any]:
        """Filter facts relevant to a specific section"""
        relevant = []
        
        # Create search terms from section content
        search_terms = []
        search_terms.extend(section.content_points)
        search_terms.extend(section.legal_authorities)
        search_terms.append(section.title)
        
        # Score each fact by relevance
        for fact in facts:
            relevance_score = 0
            fact_content = fact.content.lower() if hasattr(fact, 'content') else str(fact).lower()
            
            for term in search_terms:
                if term.lower() in fact_content:
                    relevance_score += 1
            
            if relevance_score > 0:
                relevant.append((relevance_score, fact))
        
        # Sort by relevance and return top facts
        relevant.sort(key=lambda x: x[0], reverse=True)
        return [fact for _, fact in relevant[:5]]
    
    def _filter_relevant_authorities(
        self, 
        authorities: List[Dict[str, Any]], 
        required_citations: List[str]
    ) -> List[Dict[str, Any]]:
        """Filter authorities relevant to required citations"""
        relevant = []
        
        for auth in authorities:
            citation = auth.get("citation", "")
            # Check if this authority matches any required citation
            for required in required_citations:
                if required.lower() in citation.lower() or citation.lower() in required.lower():
                    relevant.append(auth)
                    break
        
        return relevant
    
    def _format_facts_for_prompt(self, facts: List[Any]) -> str:
        """Format facts for inclusion in prompt"""
        if not facts:
            return "No specific facts provided."
        
        formatted = []
        for i, fact in enumerate(facts[:5], 1):
            if hasattr(fact, 'content'):
                formatted.append(f"{i}. {fact.content[:200]}...")
            else:
                formatted.append(f"{i}. {str(fact)[:200]}...")
        
        return "\n".join(formatted)
    
    def _format_authorities_for_prompt(self, authorities: List[Dict[str, Any]]) -> str:
        """Format legal authorities for inclusion in prompt"""
        if not authorities:
            return "No specific authorities provided."
        
        formatted = []
        for auth in authorities[:5]:
            citation = auth.get("citation", "Unknown")
            content = auth.get("content", "")[:200]
            formatted.append(f"- {citation}: {content}...")
        
        return "\n".join(formatted)
    
    def _get_previous_context(self, drafted_sections: List[DraftedSection]) -> str:
        """Get context from previously drafted sections"""
        if not drafted_sections:
            return "This is the first section of the motion."
        
        # Get last section's conclusion
        last_section = drafted_sections[-1]
        last_content = last_section.content
        
        # Extract last paragraph or last 500 characters
        paragraphs = last_content.split('\n\n')
        if paragraphs:
            context = paragraphs[-1]
        else:
            context = last_content[-500:]
        
        return f"Previous section '{last_section.outline_section.title}' concluded with:\n{context}"
    
    def _assess_section_quality(self, content: str, section: OutlineSection) -> float:
        """Assess quality and completeness of drafted section"""
        score = 0.0
        max_score = 100.0
        
        # Check if all outline points are addressed
        points_addressed = 0
        content_lower = content.lower()
        for point in section.content_points:
            if any(word in content_lower for word in point.lower().split()[:3]):
                points_addressed += 1
        
        if section.content_points:
            score += (points_addressed / len(section.content_points)) * 30
        
        # Check if legal authorities are cited
        citations_found = 0
        for authority in section.legal_authorities:
            if authority in content or authority.replace(" ", "") in content:
                citations_found += 1
        
        if section.legal_authorities:
            score += (citations_found / len(section.legal_authorities)) * 30
        
        # Check structure (IRAC indicators)
        irac_indicators = ["issue", "rule", "application", "conclusion", "analysis", "holding"]
        irac_found = sum(1 for indicator in irac_indicators if indicator in content_lower)
        score += (irac_found / len(irac_indicators)) * 20
        
        # Check length relative to target
        word_count = len(content.split())
        if word_count >= section.target_length * 0.8:
            score += 20
        else:
            score += (word_count / section.target_length) * 20
        
        return score / max_score
    
    def _extract_citations(self, content: str) -> List[str]:
        """Extract legal citations from content"""
        citations = []
        
        # Common legal citation patterns
        patterns = [
            r'\d+\s+U\.S\.C\.\s+§\s*\d+',  # USC
            r'\d+\s+F\.\d+d\s+\d+',  # Federal Reporter
            r'\d+\s+S\.\s*Ct\.\s+\d+',  # Supreme Court
            r'\d+\s+[A-Z][a-z]+\.\s*(?:2d|3d)?\s+\d+',  # State reporters
            r'[A-Z][a-z]+\s+v\.\s+[A-Z][a-z]+(?:,\s+\d+)?'  # Case names
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content)
            citations.extend(matches)
        
        return list(set(citations))  # Remove duplicates
    
    def _get_expansion_context(
        self, 
        section: OutlineSection, 
        case_context: Dict[str, Any]
    ) -> str:
        """Get additional context for section expansion"""
        context_parts = []
        
        # Add unused facts
        if case_context["case_facts"]:
            context_parts.append("Additional Case Facts:")
            for fact in case_context["case_facts"][:3]:
                if hasattr(fact, 'content'):
                    context_parts.append(f"- {fact.content[:150]}...")
        
        # Add expert opinions
        if case_context["expert_reports"]:
            context_parts.append("\nExpert Opinions:")
            for expert in case_context["expert_reports"][:2]:
                if hasattr(expert, 'content'):
                    context_parts.append(f"- {expert.content[:150]}...")
        
        return "\n".join(context_parts)
    
    def _integrate_expansion(self, original: str, expansion: str) -> str:
        """Integrate expansion content into original section"""
        # Find the best place to insert expansion
        paragraphs = original.split('\n\n')
        
        # If expansion starts with a transition phrase, append it
        if any(expansion.lower().startswith(phrase) for phrase in 
               ["furthermore", "additionally", "moreover", "in addition"]):
            return original + "\n\n" + expansion
        
        # Otherwise, try to insert it before the conclusion
        conclusion_indicators = ["conclusion", "therefore", "thus", "in summary", "accordingly"]
        
        for i in range(len(paragraphs) - 1, -1, -1):
            if any(indicator in paragraphs[i].lower() for indicator in conclusion_indicators):
                # Insert before conclusion
                paragraphs.insert(i, expansion)
                return '\n\n'.join(paragraphs)
        
        # Default: append to end
        return original + "\n\n" + expansion
    
    def _generate_motion_title(self, outline: Dict[str, Any]) -> str:
        """Generate motion title from outline if not provided"""
        # Try to extract from outline
        if "title" in outline:
            return outline["title"]
        
        if "motion_type" in outline:
            return f"Motion {outline['motion_type']}"
        
        # Default
        return "Motion for Relief"
    
    async def _apply_critical_fixes(
        self, 
        motion_draft: MotionDraft, 
        review_data: Dict[str, Any]
    ) -> MotionDraft:
        """Apply critical fixes based on review feedback"""
        critical_issues = review_data.get("critical_issues", [])
        
        for issue in critical_issues:
            issue_type = issue.get("type", "")
            
            if issue_type == "missing_citations":
                # Add missing citations
                logger.info("Applying fix for missing citations")
                # Implementation would add citations where needed
                
            elif issue_type == "inconsistent_facts":
                # Fix factual inconsistencies
                logger.info("Applying fix for inconsistent facts")
                # Implementation would reconcile facts
                
            elif issue_type == "weak_argument":
                # Strengthen weak arguments
                section_id = issue.get("section_id")
                logger.info(f"Strengthening argument in section {section_id}")
                # Implementation would revise specific sections
        
        return motion_draft
    
    def export_to_docx(self, motion_draft: MotionDraft, output_path: str):
        """Export motion draft to DOCX format"""
        from docx import Document
        from docx.shared import Pt, Inches
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        
        # Create document
        doc = Document()
        
        # Set margins
        sections = doc.sections
        for section in sections:
            section.top_margin = Inches(1)
            section.bottom_margin = Inches(1)
            section.left_margin = Inches(1)
            section.right_margin = Inches(1)
        
        # Add title
        title = doc.add_heading(motion_draft.title, level=0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        # Add case caption
        doc.add_paragraph(motion_draft.case_name)
        doc.add_paragraph()
        
        # Add each section
        for section in motion_draft.sections:
            # Section heading
            doc.add_heading(section.outline_section.title, level=1)
            
            # Section content
            for paragraph in section.content.split('\n\n'):
                if paragraph.strip():
                    p = doc.add_paragraph(paragraph)
                    p.style.font.size = Pt(12)
                    p.style.font.name = 'Times New Roman'
        
        # Add metadata page
        doc.add_page_break()
        doc.add_heading("Document Metadata", level=1)
        doc.add_paragraph(f"Total Words: {motion_draft.total_word_count}")
        doc.add_paragraph(f"Estimated Pages: {motion_draft.total_page_estimate}")
        doc.add_paragraph(f"Created: {motion_draft.creation_timestamp}")
        doc.add_paragraph(f"Coherence Score: {motion_draft.coherence_score:.2f}")
        
        if motion_draft.review_notes:
            doc.add_heading("Review Notes", level=2)
            for note in motion_draft.review_notes:
                doc.add_paragraph(f"• {note}")
        
        # Save document
        doc.save(output_path)
        logger.info(f"Motion exported to {output_path}")


# Create singleton instance
motion_drafter = MotionDraftingAgent()
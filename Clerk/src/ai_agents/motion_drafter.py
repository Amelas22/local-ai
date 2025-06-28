"""
AI Motion Drafting Agent - Enhanced Version with Direct Database Access
Implements section-by-section legal motion generation following best practices
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple, Set
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import re

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from openai import AsyncOpenAI
import tiktoken

from src.vector_storage.qdrant_store import QdrantVectorStore
from src.vector_storage.embeddings import EmbeddingGenerator
from src.ai_agents.outline_cache_manager import outline_cache
from src.utils.timeout_monitor import TimeoutMonitor, ProgressTracker
from config.settings import settings

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
    """Target document lengths with expanded ranges"""
    SHORT = (15, 20)   # 15-20 pages
    MEDIUM = (20, 30)  # 20-30 pages  
    LONG = (30, 40)    # 30-40 pages
    COMPREHENSIVE = (35, 50)  # 35-50 pages for complex motions


@dataclass
class OutlineSection:
    """Enhanced outline section with better structure"""
    id: str
    title: str
    section_type: SectionType
    content_points: List[str]
    legal_authorities: List[str]
    target_length: int  # Target word count
    parent_id: Optional[str] = None
    children: List['OutlineSection'] = field(default_factory=list)
    context_summary: Optional[str] = None
    hook_options: List[str] = field(default_factory=list)
    themes: List[str] = field(default_factory=list)
    key_facts: List[Dict[str, Any]] = field(default_factory=list)
    counter_arguments: List[Dict[str, str]] = field(default_factory=list)


@dataclass
class DraftedSection:
    """Enhanced drafted section with quality metrics"""
    outline_section: OutlineSection
    content: str
    word_count: int
    citations_used: List[str]
    citations_verified: Dict[str, bool]  # Citation -> verification status
    expansion_cycles: int
    confidence_score: float
    needs_revision: bool = False
    revision_notes: List[str] = field(default_factory=list)
    consistency_score: float = 0.0
    factual_accuracy_score: float = 0.0
    argument_strength_score: float = 0.0
    transitions: Dict[str, str] = field(default_factory=dict)  # To next/from previous


@dataclass
class MotionDraft:
    """Enhanced motion draft with comprehensive metadata"""
    title: str
    case_name: str  # Can be derived from database_name or set as a display value
    sections: List[DraftedSection]
    total_word_count: int
    total_page_estimate: int
    creation_timestamp: datetime
    outline_source: Dict[str, Any]
    coherence_score: float = 0.0
    review_notes: List[str] = field(default_factory=list)
    quality_metrics: Dict[str, float] = field(default_factory=dict)
    citation_index: Dict[str, List[str]] = field(default_factory=dict)  # Citation -> sections using it
    consistency_issues: List[Dict[str, Any]] = field(default_factory=list)
    

class EnhancedMotionDraftingAgent:
    """Enhanced AI agent for drafting legal motions with direct database access"""
    
    def __init__(self):
        """Initialize the enhanced motion drafting agent"""
        self.vector_store = QdrantVectorStore()
        self.embedding_generator = EmbeddingGenerator()
        self.openai_client = AsyncOpenAI(api_key=settings.openai.api_key)
        
        # Initialize OpenAI models with proper configuration
        self.gpt4_model = OpenAIModel('gpt-4.1-mini-2025-04-14')
        
        # For now, use GPT-4 for all agents to ensure compatibility
        self.primary_model = self.gpt4_model
        
        # Initialize AI agents with enhanced prompts
        self.section_writer = self._create_enhanced_section_writer()
        
        # Initialize tokenizer
        self.tokenizer = tiktoken.encoding_for_model("gpt-4")
        
        # Enhanced configuration
        self.words_per_page = 250
        self.max_expansion_cycles = 5
        self.min_confidence_threshold = 0.75
        self.citation_patterns = self._compile_citation_patterns()
        
        # Track document-wide context
        self.document_context = {
            "themes": [],
            "key_arguments": [],
            "terminology": {},
            "citations_used": set(),
            "fact_chronology": []
        }
        
        logger.info("EnhancedMotionDraftingAgent initialized successfully")

    def _create_enhanced_section_writer(self) -> Agent:
        """Create enhanced section writer with ABCDE framework and CoT prompting"""
        try:
            # Use primary model for section writing
            agent = Agent(
                self.primary_model,
                system_prompt="""You are an expert legal writer specializing in comprehensive motion drafting.

## AUDIENCE
You are writing for a trial court judge who needs detailed legal analysis, not summaries.
The document will be reviewed by opposing counsel looking for weaknesses.
Your writing must be authoritative, precise, and persuasive.

## BACKGROUND
You are drafting sections of formal legal motions (15-40 pages) that will be filed in court.
Each section must contribute substantive content to reach the target length.
This is NOT a brief or summary - it requires comprehensive analysis.

## CONSTRAINTS
1. Use formal legal writing style appropriate for court filings
2. Follow IRAC/CRAC structure (Issue, Rule, Application, Conclusion)
3. All citations must be in proper Bluebook format
4. Never create fictional citations - only use provided authorities
5. Maintain consistent terminology throughout
6. Each section must meet its target word count

## DETAILED PARAMETERS
- Write comprehensively, not concisely
- Develop each point with multiple paragraphs of analysis
- Include detailed factual application to legal standards
- Address counterarguments preemptively
- Use topic sentences and smooth transitions
- Incorporate policy considerations where relevant
- Analyze case law holdings in detail
- Apply multi-factor tests thoroughly

## EVALUATION CRITERIA
Your output will be evaluated on:
1. Completeness - Did you address all outline points?
2. Depth - Is the analysis thorough and detailed?
3. Length - Does it meet the target word count?
4. Legal accuracy - Are citations and law correctly stated?
5. Persuasiveness - Is the argument compelling?
6. Coherence - Does it flow logically?

## CHAIN-OF-THOUGHT PROCESS
Before writing, think through:
1. What is the core legal issue this section addresses?
2. What are the relevant legal standards and elements?
3. How do the facts of our case apply to each element?
4. What would opposing counsel argue?
5. How can we preemptively counter those arguments?
6. What policy reasons support our position?""",
                result_type=str
            )
            logger.info("Section writer agent created successfully")
            return agent
        except Exception as e:
            logger.error(f"Failed to create section writer agent: {str(e)}")
            raise

    def _compile_citation_patterns(self) -> List[re.Pattern]:
        """Compile regex patterns for citation extraction"""
        patterns = [
            # Federal cases
            re.compile(r'\d+\s+U\.S\.\s+\d+(?:\s+\(\d{4}\))?'),
            re.compile(r'\d+\s+F\.\d+d\s+\d+(?:\s+\([^)]+\d{4}\))?'),
            re.compile(r'\d+\s+F\.\s*Supp\.\s*\d+d?\s+\d+(?:\s+\([^)]+\d{4}\))?'),
            re.compile(r'\d+\s+S\.\s*Ct\.\s+\d+(?:\s+\(\d{4}\))?'),
            
            # State cases  
            re.compile(r'\d+\s+[A-Z][a-z]+\.(?:\s+\d+d)?\s+\d+(?:\s+\([^)]+\d{4}\))?'),
            
            # Case names
            re.compile(r'[A-Z][a-zA-Z]+\s+v\.\s+[A-Z][a-zA-Z]+(?:,\s+\d+)?'),
            
            # Statutes
            re.compile(r'\d+\s+U\.S\.C\.\s+§+\s*\d+[\w\-\.]*'),
            re.compile(r'[A-Z][a-z]+\.\s+Stat\.\s+(?:Ann\.\s+)?§+\s*\d+[\w\-\.]*'),
            
            # Regulations
            re.compile(r'\d+\s+C\.F\.R\.\s+§*\s*\d+\.\d+'),
            
            # Rules
            re.compile(r'Fed\.\s*R\.\s*(?:Civ|Crim|Evid|App)\.\s*P\.\s*\d+[a-z]*'),
        ]
        return patterns

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

    def _clean_outline_content(self, content: str, max_length: int = 500) -> str:
        """Clean and truncate outline content to prevent token overflow"""
        if not content:
            return ""
        
        # Handle multi-option format (e.g., "Option 1: ... || Option 2: ...")
        if "||" in content:
            options = content.split("||")
            # Take only the first option and clean it
            content = options[0].strip()
            # Remove "Option 1:" prefix if present
            if content.startswith("Option"):
                content = content.split(":", 1)[1].strip() if ":" in content else content
        
        # Truncate if too long
        if len(content) > max_length:
            content = content[:max_length] + "..."
        
        return content

    def _build_comprehensive_search_queries(self, outline_sections: List[OutlineSection]) -> Dict[str, List[str]]:
        """Build comprehensive search queries based on outline"""
        queries = {
            "legal_authorities": [],
            "factual_searches": [],
            "expert_searches": [],
            "procedural_history": []
        }
        
        # Extract all legal authorities
        for section in outline_sections:
            queries["legal_authorities"].extend(section.legal_authorities)
            for child in section.children:
                queries["legal_authorities"].extend(child.legal_authorities)
        
        # Build factual search queries from ALL content
        fact_patterns = set()
        for section in outline_sections:
            # Extract from ALL key facts
            for fact in section.key_facts:
                if isinstance(fact, dict):
                    fact_patterns.add(fact.get("description", str(fact)))
                else:
                    fact_patterns.add(str(fact))
            
            # Extract from ALL content points (not just first 3)
            for point in section.content_points:
                if isinstance(point, str) and len(point) > 20:  # Skip very short strings
                    # Extract key phrases from longer content
                    sentences = point.split('.')
                    for sentence in sentences[:2]:  # First 2 sentences
                        if len(sentence) > 20:
                            fact_patterns.add(sentence.strip())
        
        # Remove duplicates and empty strings
        queries["factual_searches"] = [q for q in list(fact_patterns) if q and len(q) > 10]
        
        # Expert-specific searches
        queries["expert_searches"] = [
            "expert report",
            "expert opinion", 
            "expert analysis",
            "expert testimony",
            "expert conclusions"
        ]
        
        # Procedural history searches
        queries["procedural_history"] = [
            "complaint filed",
            "motion to dismiss",
            "discovery order",
            "scheduling order",
            "previous motions"
        ]
        
        logger.info(f"Built search queries: {len(queries['legal_authorities'])} authorities, "
                f"{len(queries['factual_searches'])} factual searches")
        
        return queries

    async def _retrieve_enhanced_case_context(
        self, 
        database_name: str,
        outline_sections: List[OutlineSection]
    ) -> Dict[str, Any]:
        """Retrieve comprehensive case context directly from database"""
        
        context = {
            "case_facts": [],
            "legal_authorities": [],
            "expert_reports": [],
            "key_documents": [],
            "medical_records": [],
            "motion_practice": [],
            "fact_chronology": [],
            "themes": [],
            "opposing_motion": self.document_context.get("opposing_motion_text", "")
        }
        
        # Build comprehensive search queries
        search_queries = self._build_comprehensive_search_queries(outline_sections)
        
        # LIMIT the number of queries to prevent overload
        max_queries_per_type = 5
        
        for query_type, queries in search_queries.items():
            # Limit queries
            limited_queries = queries[:max_queries_per_type]
            logger.info(f"Processing {len(limited_queries)} queries for {query_type}")
            
            for query in limited_queries:
                try:
                    # Clean and validate query
                    query = query.strip()
                    if not query or len(query) < 3:
                        continue
                    
                    # Truncate overly long queries
                    if len(query) > 200:
                        query = query[:200]
                    
                    logger.debug(f"Searching for: {query[:100]}...")
                    
                    # Generate embedding for the query
                    query_embedding, _ = self.embedding_generator.generate_embedding(query)
                    
                    # Perform hybrid search with timeout
                    results = await asyncio.wait_for(
                        self.vector_store.hybrid_search(
                            collection_name=database_name,
                            query=query,
                            query_embedding=query_embedding,
                            limit=5,  # Reduced from 10
                            enable_reranking=False
                        ),
                        timeout=10  # 10 second timeout per search
                    )
                    
                    # Categorize results
                    for result in results:
                        if result.score > 0.6:
                            doc_type = result.metadata.get("document_type", "").lower()
                            
                            if "medical" in doc_type:
                                context["medical_records"].append(result)
                            elif "expert" in doc_type:
                                context["expert_reports"].append(result)
                            elif "motion" in doc_type:
                                context["motion_practice"].append(result)
                            elif query_type == "legal_authorities":
                                context["legal_authorities"].append({
                                    "citation": query,
                                    "content": result.content,
                                    "document": result.metadata.get("document_name", "Unknown"),
                                    "score": result.score,
                                    "context": result.metadata.get("context_summary", "")
                                })
                            else:
                                context["case_facts"].append(result)
                                
                except Exception as e:
                    logger.error(f"Error searching for '{query}': {str(e)}")
                    continue
        
        # Build fact chronology
        context["fact_chronology"] = self._build_fact_chronology(context["case_facts"])
        
        # Extract themes
        context["themes"] = self._extract_case_themes(context)
        
        logger.info(f"Retrieved comprehensive context from {database_name}: {len(context['legal_authorities'])} authorities, "
                   f"{len(context['case_facts'])} facts, {len(context['expert_reports'])} expert reports, "
                   f"{len(context['medical_records'])} medical records")
        
        return context

    def _build_fact_chronology(self, facts: List[Any]) -> List[Dict[str, Any]]:
        """Build chronological ordering of facts"""
        
        chronology = []
        
        for fact in facts:
            content = fact.content if hasattr(fact, 'content') else str(fact)
            
            # Extract dates
            date_patterns = [
                r'(\d{1,2}/\d{1,2}/\d{2,4})',
                r'(\w+\s+\d{1,2},\s+\d{4})',
                r'(\d{4}-\d{2}-\d{2})'
            ]
            
            for pattern in date_patterns:
                dates = re.findall(pattern, content)
                for date in dates:
                    chronology.append({
                        "date": date,
                        "description": content[:100],
                        "source": fact.metadata.get("document_name", "Unknown") if hasattr(fact, 'metadata') else 'Unknown'
                    })
        
        # Sort by date (simple approach - would need proper date parsing in production)
        return chronology[:20]  # Top 20 events

    def _extract_case_themes(self, context: Dict[str, Any]) -> List[str]:
        """Extract overarching themes from case context"""
        
        themes = []
        
        # Analyze content for common themes
        all_content = []
        for category in ["case_facts", "expert_reports", "legal_authorities"]:
            for item in context.get(category, [])[:10]:
                if hasattr(item, 'content'):
                    all_content.append(item.content)
                elif isinstance(item, dict):
                    all_content.append(item.get('content', ''))
        
        combined_text = ' '.join(all_content).lower()
        
        # Theme detection patterns
        theme_patterns = {
            "safety": ["safety", "dangerous", "hazard", "risk", "harm"],
            "corporate_responsibility": ["corporate", "company", "business", "employer"],
            "negligence": ["negligent", "breach", "duty", "reasonable care"],
            "causation": ["caused", "resulted", "led to", "because of"],
            "damages": ["damages", "injury", "harm", "loss", "suffering"]
        }
        
        for theme, keywords in theme_patterns.items():
            if sum(1 for kw in keywords if kw in combined_text) >= 2:
                themes.append(theme)
        
        return themes[:5]  # Top 5 themes

    def _extract_themes_from_value(self, value: str) -> List[str]:
        """Extract themes from a field value string"""
        if not value:
            return []
        
        themes = []
        
        # Handle multi-option format
        if "||" in value:
            options = value.split("||")
            for option in options:
                option = option.strip()
                if option.startswith("Option"):
                    option = option.split(":", 1)[1].strip() if ":" in option else option
                themes.append(option.strip('"').strip())
        else:
            themes.append(value.strip('"').strip())
        
        # Clean and filter themes
        cleaned_themes = []
        for theme in themes:
            if theme and len(theme) > 3:  # Skip very short themes
                cleaned_themes.append(theme[:100])  # Limit length
        
        return cleaned_themes[:3]  # Max 3 themes

    def _build_citation_index(self, motion_draft: MotionDraft) -> Dict[str, List[str]]:
        """Build index of citations to sections using them"""
        citation_index = {}
        
        for section in motion_draft.sections:
            for citation in section.citations_used:
                if citation not in citation_index:
                    citation_index[citation] = []
                citation_index[citation].append(section.outline_section.id)
        
        return citation_index

    def _extract_citations_from_text(self, text: str) -> List[str]:
        """Extract all citations from text using compiled patterns"""
        citations = []
        
        for pattern in self.citation_patterns:
            matches = pattern.findall(text)
            citations.extend(matches)
        
        # Clean and deduplicate
        citations = list(set(citation.strip() for citation in citations))
        
        return citations

    def _calculate_section_confidence(
        self,
        content: str,
        section: OutlineSection,
        word_count: int
    ) -> float:
        """Calculate confidence score for section"""
        score = 0.0
        max_score = 100.0
        
        # Length score (30 points)
        if word_count >= section.target_length:
            score += 30
        else:
            score += (word_count / section.target_length) * 30
        
        # Content points addressed (25 points)
        points_addressed = sum(
            1 for point in section.content_points
            if any(keyword in content.lower() for keyword in point.lower().split()[:5])
        )
        if section.content_points:
            score += (points_addressed / len(section.content_points)) * 25
        else:
            score += 25
        
        # Citations included (25 points)
        citations_found = sum(
            1 for auth in section.legal_authorities
            if auth in content or auth.replace(" ", "") in content
        )
        if section.legal_authorities:
            score += (citations_found / len(section.legal_authorities)) * 25
        else:
            score += 25
        
        # Structure quality (20 points)
        structure_indicators = [
            "first", "second", "third",
            "moreover", "furthermore", "additionally",
            "however", "nevertheless", 
            "therefore", "accordingly",
            "issue", "rule", "application", "conclusion"
        ]
        structure_score = sum(2 for indicator in structure_indicators if indicator in content.lower())
        score += min(structure_score, 20)
        
        return score / max_score

    def _update_document_context(self, section: DraftedSection):
        """Update document-wide context with section information"""
        
        # Update citations used
        self.document_context["citations_used"].update(section.citations_used)
        
        # Update terminology
        terms = self._extract_key_terms(section.content)
        for term in terms:
            if term not in self.document_context["terminology"]:
                self.document_context["terminology"][term] = section.outline_section.id

    def _extract_key_terms(self, content: str) -> List[str]:
        """Extract key legal terms from content"""
        # Simple implementation - could be enhanced
        terms = []
        legal_terms = [
            "negligence", "liability", "duty", "breach", "damages", "causation",
            "standard of care", "reasonable person", "proximate cause", "foreseeability"
        ]
        
        content_lower = content.lower()
        for term in legal_terms:
            if term in content_lower:
                terms.append(term)
        
        return terms[:5]

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
        
        # Add each section with transitions
        for i, section in enumerate(motion_draft.sections):
            # Section heading
            doc.add_heading(section.outline_section.title, level=1)
            
            # Add transition from previous if available
            if "from_previous" in section.transitions and i > 0:
                transition_para = doc.add_paragraph(section.transitions["from_previous"])
                transition_para.style.font.italic = True
                doc.add_paragraph()
            
            # Section content
            for paragraph in section.content.split('\n\n'):
                if paragraph.strip():
                    p = doc.add_paragraph(paragraph)
                    p.style.font.size = Pt(12)
                    p.style.font.name = 'Times New Roman'
            
            # Add transition to next if available
            if "to_next" in section.transitions and i < len(motion_draft.sections) - 1:
                doc.add_paragraph()
                transition_para = doc.add_paragraph(section.transitions["to_next"])
                transition_para.style.font.italic = True
        
        # Add metadata page
        doc.add_page_break()
        doc.add_heading("Document Metadata", level=1)
        
        # Basic metadata
        doc.add_paragraph(f"Total Words: {motion_draft.total_word_count:,}")
        doc.add_paragraph(f"Estimated Pages: {motion_draft.total_page_estimate}")
        doc.add_paragraph(f"Created: {motion_draft.creation_timestamp.strftime('%B %d, %Y at %I:%M %p')}")
        doc.add_paragraph(f"Document Quality Score: {motion_draft.coherence_score:.2%}")
        
        # Quality metrics
        if motion_draft.quality_metrics:
            doc.add_heading("Quality Metrics", level=2)
            for metric, score in motion_draft.quality_metrics.items():
                doc.add_paragraph(f"• {metric.replace('_', ' ').title()}: {score:.2%}")
        
        # Citation index
        if motion_draft.citation_index:
            doc.add_heading("Citation Index", level=2)
            doc.add_paragraph(f"Total Unique Citations: {len(motion_draft.citation_index)}")
            
            # List top citations
            sorted_citations = sorted(
                motion_draft.citation_index.items(),
                key=lambda x: len(x[1]),
                reverse=True
            )[:10]
            
            for citation, sections in sorted_citations:
                doc.add_paragraph(f"• {citation} (used in {len(sections)} sections)")
        
        # Review notes
        if motion_draft.review_notes:
            doc.add_heading("Review Notes", level=2)
            for note in motion_draft.review_notes:
                doc.add_paragraph(f"• {note}")
        
        # Save document
        doc.save(output_path)
        logger.info(f"Motion exported to {output_path}")

    async def draft_motion_with_cache(
        self,
        outline: Dict[str, Any],
        database_name: str,
        target_length: DocumentLength = DocumentLength.MEDIUM,
        motion_title: Optional[str] = None,
        opposing_motion_text: Optional[str] = None,
        outline_id: Optional[str] = None  # If already cached
    ) -> MotionDraft:
        """
        Enhanced motion drafting that caches outline and processes sections individually
        """
        start_time = datetime.utcnow()
        logger.info(f"[MOTION_DRAFTER] Starting cached motion draft for database: {database_name}")
        
        # Cache the outline if not already cached
        if not outline_id:
            outline_id = await outline_cache.cache_outline(outline, database_name)
            logger.info(f"[MOTION_DRAFTER] Cached outline with ID: {outline_id}")
        else:
            # Verify outline exists in cache
            cached_outline = await outline_cache.get_outline(outline_id)
            if not cached_outline:
                # Re-cache if missing
                outline_id = await outline_cache.cache_outline(outline, database_name)
                logger.info(f"[MOTION_DRAFTER] Re-cached missing outline with ID: {outline_id}")
        
        # Get outline structure for processing
        outline_structure = await outline_cache.get_outline_structure(outline_id)
        if not outline_structure:
            raise ValueError(f"Failed to get outline structure for ID: {outline_id}")
        
        logger.info(f"[MOTION_DRAFTER] Processing {len(outline_structure)} sections")
        
        # Initialize timeout monitor
        timeout_monitor = TimeoutMonitor(
            operation_name=f"Motion Drafting ({database_name})",
            warning_threshold=60,
            critical_threshold=180  # Increased to 3 minutes
        )
        timeout_monitor.log_progress("Cached motion drafting started")
        
        # Initialize document context with minimal data
        self.document_context = {
            "themes": outline.get("themes", outline.get("style_notes", [])),
            "key_arguments": [],
            "terminology": {},
            "citations_used": set(),
            "fact_chronology": [],
            "database_name": database_name,
            "opposing_motion_text": opposing_motion_text,
            "outline_id": outline_id  # Store for reference
        }
        
        # Calculate word distribution based on structure
        min_pages, max_pages = target_length.value
        target_words = ((min_pages + max_pages) // 2) * self.words_per_page
        word_distribution = self._calculate_word_distribution_from_structure(
            outline_structure, target_words
        )
        
        # Retrieve case context once - convert structure back to sections for compatibility
        logger.info(f"[MOTION_DRAFTER] Retrieving case context")
        full_outline_sections = await self._convert_structure_to_sections(outline_id, outline_structure)
        case_context = await self._retrieve_enhanced_case_context(
            database_name, 
            full_outline_sections
        )
        
        # Process sections individually
        drafted_sections = []
        total_words = 0
        
        for i, section_info in enumerate(outline_structure):
            section_start_time = datetime.utcnow()
            logger.info(f"[MOTION_DRAFTER] Processing section {i+1}/{len(outline_structure)}: {section_info['heading']}")
            
            # Update timeout monitor
            timeout_monitor.log_progress(f"Drafting section {i+1}: {section_info['heading']}")
            
            # Retrieve only this section from cache
            section_data = await outline_cache.get_section(outline_id, section_info['index'])
            if not section_data:
                logger.error(f"Failed to retrieve section {i} from cache")
                continue
            
            # Create minimal OutlineSection for this section only
            outline_section = self._create_minimal_outline_section(
                section_data, 
                section_info,
                word_distribution.get(f"section_{i}", 500)
            )
            
            # Build cumulative context (lightweight)
            cumulative_context = self._build_lightweight_cumulative_context(
                drafted_sections,
                case_context
            )
            
            # Draft the section
            try:
                drafted_section = await self._draft_section_efficiently(
                    outline_section,
                    section_data,  # Pass full section data separately
                    case_context,
                    cumulative_context
                )
                
                # Expand if needed
                if drafted_section.word_count < outline_section.target_length * 0.9:
                    drafted_section = await self._expand_section_efficiently(
                        drafted_section,
                        section_data,
                        outline_section.target_length,
                        case_context
                    )
                
                drafted_sections.append(drafted_section)
                total_words += drafted_section.word_count
                
                # Update document context incrementally
                self._update_document_context(drafted_section)
                
                section_duration = datetime.utcnow() - section_start_time
                logger.info(f"[MOTION_DRAFTER] Section {i+1} completed in {section_duration}")
                
            except Exception as e:
                logger.error(f"[MOTION_DRAFTER] Error drafting section {i+1}: {str(e)}")
                # Create placeholder section
                drafted_section = DraftedSection(
                    outline_section=outline_section,
                    content=f"[ERROR: Section could not be drafted - {str(e)}]",
                    word_count=0,
                    citations_used=[],
                    citations_verified={},
                    expansion_cycles=0,
                    confidence_score=0.0
                )
                drafted_sections.append(drafted_section)
        
        # Create motion draft
        motion_draft = MotionDraft(
            title=motion_title or self._extract_title_from_cache(outline),
            case_name=database_name.replace("_", " ").title(),
            sections=drafted_sections,
            total_word_count=total_words,
            total_page_estimate=total_words // self.words_per_page,
            creation_timestamp=datetime.utcnow(),
            outline_source={"outline_id": outline_id}  # Store reference instead of full outline
        )
        
        # Simplified review process
        logger.info(f"[MOTION_DRAFTER] Starting review process")
        motion_draft = await self._lightweight_review_process(motion_draft)
        
        # Build citation index
        motion_draft.citation_index = self._build_citation_index(motion_draft)
        
        timeout_monitor.finish(success=True)
        
        total_duration = datetime.utcnow() - start_time
        logger.info(f"[MOTION_DRAFTER] Completed in {total_duration}")
        
        return motion_draft

    async def _convert_structure_to_sections(
        self, 
        outline_id: str, 
        outline_structure: List[Dict[str, Any]]
    ) -> List[OutlineSection]:
        """Convert outline structure back to OutlineSection objects for compatibility"""
        sections = []
        
        for section_info in outline_structure:
            try:
                # Get the full section data from cache
                section_data = await outline_cache.get_section(outline_id, section_info['index'])
                if not section_data:
                    logger.warning(f"Could not retrieve section {section_info['index']} from cache")
                    continue
                
                # Extract ALL content for search purposes (not just first 3)
                content_points = []
                legal_authorities = []
                key_facts = []
                themes = []
                
                # Process ALL content items for database search
                for item in section_data.get('content', []):
                    item_type = item.get('type', '')
                    
                    if item_type == 'field':
                        label = item.get('label', '')
                        value = item.get('value', '')
                        
                        # Clean multi-option values but keep full content
                        if "||" in value:
                            options = value.split("||")
                            # Add first option as primary, but keep others for search
                            for i, option in enumerate(options[:3]):
                                clean_option = option.strip()
                                if clean_option.startswith("Option"):
                                    clean_option = clean_option.split(":", 1)[1].strip() if ":" in clean_option else clean_option
                                content_points.append(clean_option.strip('"').strip())
                        else:
                            content_points.append(value.strip('"').strip())
                        
                        # Special handling for themes
                        if 'theme' in label.lower():
                            themes.extend(self._extract_themes_from_value(value))
                        
                    elif item_type == 'list':
                        label = item.get('label', '').lower()
                        items = item.get('items', [])
                        
                        if 'authorit' in label:
                            legal_authorities.extend(items)
                        elif 'fact' in label:
                            key_facts.extend(items)
                        else:
                            # Add list items as content points
                            content_points.extend([str(item) for item in items])
                    
                    elif item_type == 'paragraph':
                        text = item.get('text', '')
                        if text:
                            content_points.append(text)
                
                # Create OutlineSection with FULL content for search
                section = OutlineSection(
                    id=f"section_{section_info['index']}",
                    title=section_info.get('heading', f"Section {section_info['index'] + 1}"),
                    section_type=self._determine_section_type(section_info.get('heading', '')),
                    content_points=content_points,  # Keep ALL content points
                    legal_authorities=legal_authorities,  # Keep ALL authorities
                    target_length=500,  # Will be updated later
                    context_summary=section_data.get('summary', ''),
                    hook_options=section_data.get('hook_options', []),
                    themes=themes,
                    key_facts=key_facts,
                    counter_arguments=section_data.get('counter_arguments', [])
                )
                sections.append(section)
                
            except Exception as e:
                logger.warning(f"Error converting section {section_info['index']}: {str(e)}")
                continue
        
        return sections

    def _create_minimal_outline_section(
        self,
        section_data: Dict[str, Any],
        section_info: Dict[str, Any],
        target_length: int
    ) -> OutlineSection:
        """Create a minimal OutlineSection object for processing"""
        
        # Extract only essential content points (limit to prevent overflow)
        content_points = []
        content_items = section_data.get("content", [])[:3]  # Only first 3 items
        
        for item in content_items:
            if item.get("type") == "field":
                label = item.get("label", "")
                value = item.get("value", "")[:200]  # Truncate to 200 chars
                content_points.append(f"{label}: {value}")
            elif item.get("type") == "paragraph":
                content_points.append(item.get("text", "")[:200])
        
        # Extract limited authorities
        legal_authorities = []
        for item in content_items:
            if item.get("type") == "list" and "authorities" in item.get("label", "").lower():
                legal_authorities.extend(item.get("items", [])[:5])  # Max 5 authorities
        
        return OutlineSection(
            id=f"section_{section_info['index']}",
            title=section_info['heading'],
            section_type=self._determine_section_type(section_info['heading']),
            content_points=content_points[:5],  # Max 5 points
            legal_authorities=legal_authorities[:5],  # Max 5 authorities
            target_length=target_length,
            context_summary=f"Section {section_info['index'] + 1} of {section_info.get('type', 'standard')} type"
        )

    async def _draft_section_efficiently(
        self,
        outline_section: OutlineSection,
        full_section_data: Dict[str, Any],
        case_context: Dict[str, Any],
        cumulative_context: Dict[str, Any]
    ) -> DraftedSection:
        """Draft a section efficiently without token overflow"""
        
        try:
            # Extract the most important content from full section data
            essential_content = self._extract_essential_content(full_section_data)
            
            # Create focused prompt
            drafting_prompt = f"""Draft this section of the legal motion:

Section: {outline_section.title}
Type: {outline_section.section_type.value}
Target Length: {outline_section.target_length} words (MINIMUM)

Key Points to Address:
{chr(10).join(f"- {point}" for point in essential_content['key_points'][:5])}

Required Authorities:
{chr(10).join(f"- {auth}" for auth in essential_content['authorities'][:5])}

Context from Previous Sections:
{cumulative_context.get('summary', 'This is the first section.')}

REQUIREMENTS:
1. Write {outline_section.target_length} words MINIMUM
2. Use formal legal writing style
3. Include all required authorities with parentheticals
4. Develop each point with detailed analysis
5. Include transitions and topic sentences
6. Apply IRAC/CRAC structure where appropriate"""

            # Generate content
            result = await asyncio.wait_for(
                self.section_writer.run(drafting_prompt),
                timeout=45  # 45 second timeout per section
            )
            
            content = str(result.data) if hasattr(result, 'data') else str(result)
            
            # Create drafted section
            word_count = len(content.split())
            return DraftedSection(
                outline_section=outline_section,
                content=content,
                word_count=word_count,
                citations_used=self._extract_citations_from_text(content),
                citations_verified={},
                expansion_cycles=1,
                confidence_score=self._calculate_section_confidence(
                    content, outline_section, word_count
                )
            )
            
        except asyncio.TimeoutError:
            logger.error(f"Timeout drafting section: {outline_section.title}")
            raise
        except Exception as e:
            logger.error(f"Error drafting section efficiently: {str(e)}")
            raise

    def _extract_essential_content(self, section_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract essential content from section data without overwhelming tokens"""
        
        essential = {
            "key_points": [],
            "authorities": [],
            "facts": [],
            "themes": []
        }
        
        # Process content items
        for item in section_data.get("content", []):
            item_type = item.get("type", "")
            
            if item_type == "field":
                label = item.get("label", "")
                value = item.get("value", "")
                
                # Handle multi-option values
                if "||" in value:
                    # Take first option only
                    value = value.split("||")[0].strip()
                    if value.startswith("Option"):
                        value = value.split(":", 1)[1].strip() if ":" in value else value
                
                # Truncate and clean
                value = value.strip('"').strip()[:300]  # 300 char limit
                
                if label == "Theme":
                    essential["themes"].append(value)
                elif label == "Summary":
                    essential["key_points"].insert(0, value)  # Put summary first
                else:
                    essential["key_points"].append(f"{label}: {value}")
                    
            elif item_type == "list":
                label = item.get("label", "").lower()
                items = item.get("items", [])[:5]  # Max 5 items per list
                
                if "authorit" in label:
                    essential["authorities"].extend(items)
                elif "fact" in label:
                    essential["facts"].extend(items)
                else:
                    # Convert list items to key points
                    for list_item in items[:3]:  # Max 3 items
                        if isinstance(list_item, str):
                            essential["key_points"].append(list_item[:200])
        
        # Limit totals
        essential["key_points"] = essential["key_points"][:7]
        essential["authorities"] = essential["authorities"][:7]
        essential["facts"] = essential["facts"][:5]
        essential["themes"] = essential["themes"][:3]
        
        return essential

    def _build_lightweight_cumulative_context(
        self,
        drafted_sections: List[DraftedSection],
        case_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build minimal cumulative context to prevent token overflow"""
        
        context = {
            "summary": "",
            "citations_used": set(),
            "key_holdings": []
        }
        
        if not drafted_sections:
            context["summary"] = "This is the first section of the motion."
            return context
        
        # Build brief summary from last 2 sections only
        recent_sections = drafted_sections[-2:]
        summaries = []
        
        for section in recent_sections:
            # Extract brief conclusion (first 100 chars of last paragraph)
            paragraphs = section.content.split('\n\n')
            if paragraphs:
                last_para = paragraphs[-1][:100]
                summaries.append(f"{section.outline_section.title}: {last_para}...")
            
            # Collect citations (limit to 10)
            for citation in section.citations_used[:10]:
                context["citations_used"].add(citation)
        
        context["summary"] = " | ".join(summaries)
        context["citations_used"] = list(context["citations_used"])[:15]
        
        return context

    def _calculate_word_distribution_from_structure(
        self,
        outline_structure: List[Dict[str, Any]],
        target_words: int
    ) -> Dict[str, int]:
        """Calculate word distribution based on section structure"""
        
        distribution = {}
        weights = {}
        total_weight = 0
        
        for i, section in enumerate(outline_structure):
            section_type = section.get("type", "standard")
            heading = section.get("heading", "").lower()
            
            # Assign weights based on type and heading
            if section_type == "introduction" or "introduction" in heading:
                weight = 0.5
            elif section_type == "facts" or "facts" in heading:
                weight = 1.5
            elif section_type == "conclusion" or "conclusion" in heading:
                weight = 0.5
            elif section_type == "argument":
                weight = 1.2
                # Add weight for content complexity
                weight += 0.1 * min(section.get("content_items", 0), 5)
            else:
                weight = 1.0
            
            weights[f"section_{i}"] = weight
            total_weight += weight
        
        # Distribute words based on weights
        for section_id, weight in weights.items():
            distribution[section_id] = int((weight / total_weight) * target_words)
        
        return distribution

    async def _expand_section_efficiently(
        self,
        drafted_section: DraftedSection,
        full_section_data: Dict[str, Any],
        target_length: int,
        case_context: Dict[str, Any]
    ) -> DraftedSection:
        """Expand section efficiently without overwhelming context"""
        
        try:
            current_length = drafted_section.word_count
            expansion_needed = target_length - current_length
            
            if expansion_needed <= 0:
                return drafted_section
            
            # Extract unused content from full section data
            unused_content = self._extract_unused_content(
                drafted_section.content,
                full_section_data
            )
            
            expansion_prompt = f"""Expand this legal section by adding {expansion_needed} words.

Current Section ({current_length} words):
{drafted_section.content[:2000]}... [truncated]

Unused Content Points:
{chr(10).join(f"- {point}" for point in unused_content[:5])}

REQUIREMENTS:
1. Add {expansion_needed} words of substantive content
2. DO NOT remove any existing content
3. Add deeper analysis and more detailed application
4. Maintain formal legal style
5. Include smooth transitions

Provide the COMPLETE expanded section."""

            result = await asyncio.wait_for(
                self.section_writer.run(expansion_prompt),
                timeout=30
            )
            
            expanded_content = str(result.data) if hasattr(result, 'data') else str(result)
            
            # Update section
            drafted_section.content = expanded_content
            drafted_section.word_count = len(expanded_content.split())
            drafted_section.expansion_cycles += 1
            
            return drafted_section
            
        except Exception as e:
            logger.error(f"Error in efficient expansion: {str(e)}")
            return drafted_section

    def _extract_unused_content(
        self,
        current_content: str,
        full_section_data: Dict[str, Any]
    ) -> List[str]:
        """Extract content points not yet used in the section"""
        
        unused = []
        content_lower = current_content.lower()
        
        # Check all content items
        for item in full_section_data.get("content", []):
            if item.get("type") == "field":
                value = item.get("value", "")
                # Check if this content is not yet used
                if value and value[:50].lower() not in content_lower:
                    unused.append(value[:200])
                    
            elif item.get("type") == "list":
                for list_item in item.get("items", [])[:3]:
                    if isinstance(list_item, str) and list_item[:30].lower() not in content_lower:
                        unused.append(list_item[:150])
        
        return unused[:7]  # Return max 7 unused points

    async def _lightweight_review_process(
        self,
        motion_draft: MotionDraft
    ) -> MotionDraft:
        """Simplified review process that doesn't overwhelm the system"""
        
        try:
            # Basic quality score calculation
            total_score = 0
            
            for section in motion_draft.sections:
                # Check basic quality metrics
                if section.word_count >= section.outline_section.target_length * 0.9:
                    total_score += 0.2
                if len(section.citations_used) >= 2:
                    total_score += 0.2
                if section.confidence_score > 0.7:
                    total_score += 0.1
            
            motion_draft.coherence_score = min(total_score / len(motion_draft.sections), 0.9)
            
            # Add basic review notes
            if motion_draft.coherence_score < 0.7:
                motion_draft.review_notes.append("Some sections may need expansion or additional citations")
            
            motion_draft.quality_metrics = {
                "sections_complete": len([s for s in motion_draft.sections if s.word_count > 0]),
                "average_confidence": sum(s.confidence_score for s in motion_draft.sections) / len(motion_draft.sections),
                "total_citations": len(motion_draft.citation_index)
            }
            
            return motion_draft
            
        except Exception as e:
            logger.error(f"Error in lightweight review: {str(e)}")
            motion_draft.coherence_score = 0.7
            return motion_draft

    def _extract_title_from_cache(self, outline: Dict[str, Any]) -> str:
        """Extract title from outline with minimal processing"""
        return (outline.get("title") or 
                outline.get("motion_title") or 
                "Legal Motion")


# Create global instance
motion_drafter = EnhancedMotionDraftingAgent()
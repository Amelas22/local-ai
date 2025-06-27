import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import re
import json
import uuid
import traceback

from openai import AsyncOpenAI
from pydantic import ValidationError

from app.models.schemas import (
    ComprehensiveMotionAnalysis,
    ExtractedArgument,
    ArgumentResearchPriority,
    LegalCitation,
    ArgumentCategory,
    StrengthLevel,
    AnalysisOptions
)
from app.core.config import settings

logger = logging.getLogger(__name__)

class EnhancedMotionAnalyzer:
    def __init__(self):
        self.client = None
        self._initialized = False
        
    async def initialize(self):
        """Initialize the OpenAI client"""
        if self._initialized:
            return
            
        try:
            self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            self._initialized = True
            logger.info("Enhanced motion analyzer initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize motion analyzer: {e}")
            raise

    def _get_system_prompt(self) -> str:
        return """You are an expert legal analyst specializing in extracting arguments from motions with detailed research guidance. Your goal is to extract EVERY argument and provide comprehensive information to guide case research.

CRITICAL INSTRUCTIONS:
1. Extract ALL arguments with detailed information for research
2. Include direct excerpts from the motion for each argument
3. Provide specific research priorities and evidence needs per argument
4. Write detailed summaries that explain context and implications

Use ONLY these category values or "custom" if none fit:
- negligence_duty, negligence_breach, negligence_causation, negligence_damages
- liability_vicarious, liability_derivative, liability_direct, liability_joint, liability_comparative, liability_immunity
- causation_proximate, causation_factual, causation_intervening, causation_superseding
- damages_economic, damages_noneconomic, damages_punitive, damages_mitigation, damages_calculation
- procedural_jurisdiction, procedural_venue, procedural_service, procedural_statute_limitations, procedural_standing, procedural_pleading_deficiency, procedural_discovery
- evidence_admissibility, evidence_relevance, evidence_prejudice, evidence_hearsay, evidence_authentication, evidence_privilege
- expert_qualification, expert_methodology, expert_reliability, expert_relevance, expert_daubert
- contract_breach, contract_formation, contract_interpretation
- insurance_coverage, insurance_bad_faith, insurance_exclusion
- constitutional_due_process, constitutional_equal_protection
- other, custom

You MUST respond with a valid JSON object:

{
    "motion_type": "string - type of motion",
    "case_number": "string or null - case number if found",
    "parties": ["array of party names"],
    "filing_date": "ISO datetime string or null",
    "all_arguments": [
        {
            "argument_id": "arg_001",
            "argument_text": "Brief statement of the argument (under 150 chars)",
            "detailed_summary": "COMPREHENSIVE summary explaining the argument's context, legal theory, factual assertions, and strategic implications (300-500 chars)",
            "excerpts_from_motion": [
                "Direct quote #1 from the motion that supports this argument",
                "Direct quote #2 that shows how they frame this argument",
                "Key language they use (include section references)"
            ],
            "category": "use ONLY predefined category values listed above",
            "subcategories": ["additional relevant categories"],
            "location_in_motion": "Section I.A, Paragraphs 3-5",
            "legal_basis": "Detailed legal foundation and theory",
            "factual_basis": "Specific factual claims made or null",
            "strength_indicators": ["2-3 key factors making this strong"],
            "weaknesses": ["1-2 potential vulnerabilities"],
            "cited_cases": [
                {
                    "full_citation": "Case v. Name, 123 F.3d 456 (Ct 2023)",
                    "case_name": "Case v. Name",
                    "legal_principle": "Principle established",
                    "application": "How they apply it here",
                    "jurisdiction": "Court",
                    "year": 2023,
                    "is_binding": true,
                    "citation_strength": "strong"
                }
            ],
            "cited_statutes": ["28 U.S.C. § 1331"],
            "counterarguments": ["How we can attack this"],
            "strength_assessment": "very_weak|weak|moderate|strong|very_strong",
            "confidence_score": 0.9,
            "requires_expert_response": false,
            "priority_level": 1,
            "research_priorities": [
                {
                    "research_question": "Does our client's conduct actually fall within the scope of Grobman v. Posey?",
                    "suggested_search_terms": ["Grobman", "derivative liability", "scope of employment exceptions"],
                    "case_law_focus": "Cases distinguishing Grobman on factual grounds",
                    "factual_investigation": "Look for evidence of independent negligence beyond vicarious liability"
                },
                {
                    "research_question": "Are there exceptions to the Clooney rule?",
                    "suggested_search_terms": ["Clooney v. Geeting exceptions", "negligent entrustment Florida"],
                    "case_law_focus": "Post-Clooney cases allowing negligent hiring claims",
                    "factual_investigation": "Driver's history, hiring practices, supervision records"
                }
            ],
            "required_evidence": [
                "Destin's complete driving record and employment history",
                "PFG's hiring and supervision policies",
                "Any prior incidents or complaints about Destin",
                "Evidence of PFG's independent breach of duty"
            ],
            "suggested_case_facts_to_find": [
                "Was Destin properly licensed for commercial driving?",
                "Any evidence of fatigue, distraction, or impairment?",
                "PFG's knowledge of any prior issues with Destin",
                "Specific supervision or training failures by PFG"
            ]
        }
    ],
    "total_arguments_found": 8,
    "categories_used": ["list of used categories"],
    "custom_categories_created": ["any custom categories"]
}

CRITICAL EXTRACTION RULES:
1. For excerpts_from_motion: Include 2-4 direct quotes that best capture how they present this argument
2. For detailed_summary: Explain not just WHAT they argue but WHY it matters and HOW they support it
3. For research_priorities: Be specific about what to look for, not generic
4. For required_evidence: List specific documents, testimony, or facts needed from the case file
5. For suggested_case_facts_to_find: Think like a litigator - what facts would undermine their argument?"""

    def _get_extraction_prompt(self) -> str:
        return """Extract arguments using these enhanced guidelines:

1. CAPTURE EXACT LANGUAGE:
   - Quote their strongest phrases verbatim
   - Note how they characterize facts
   - Identify loaded or prejudicial language
   - Record specific section/paragraph numbers

2. IDENTIFY RESEARCH NEEDS:
   For each argument, think:
   - What case facts would contradict this?
   - What discovery do we need?
   - Which depositions matter?
   - What documents to request?

3. STRATEGIC ASSESSMENT:
   - Why did they make this argument?
   - What are they trying to hide?
   - What facts are they assuming?
   - Where are they vulnerable?

4. EVIDENCE MAPPING:
   For each argument, specify:
   - Medical records needed
   - Witness testimony required  
   - Expert opinions to obtain
   - Documentary evidence to find

Remember: The research agent needs specific, actionable guidance for each argument."""

    async def analyze_motion(
        self, 
        motion_text: str, 
        case_context: Optional[str] = None,
        analysis_options: Optional[AnalysisOptions] = None
    ) -> ComprehensiveMotionAnalysis:
        """
        Analyze legal motion with enhanced research guidance
        """
        if not self._initialized:
            await self.initialize()
            
        try:
            # Extract citations separately for validation
            extracted_citations = await self._extract_legal_citations(motion_text)
            
            # Prepare the enhanced user prompt
            user_prompt = f"""Please analyze this legal motion and extract EVERY argument with detailed research guidance.

MOTION TEXT:
{motion_text}

{"CASE CONTEXT: " + case_context if case_context else ""}

EXTRACTED CITATIONS (use only these):
{json.dumps(extracted_citations, indent=2)}

{self._get_extraction_prompt()}

For each argument you extract:
1. Include 2-4 direct excerpts showing how they present it
2. Write a detailed summary explaining context and implications
3. Provide specific research priorities with actionable questions
4. List exact evidence needed from our case file
5. Suggest specific facts to investigate in depositions/discovery

Focus on creating a research roadmap for each argument."""

            # Make the API call with JSON mode
            response = await self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"}
            )
            
            # Parse the response
            result_data = json.loads(response.choices[0].message.content)
            
            # Ensure proper structure
            result_data = self._ensure_enhanced_structure(result_data)
            
            # Validate and create the result object
            try:
                motion_result = ComprehensiveMotionAnalysis(**result_data)
            except ValidationError as e:
                logger.error(f"Validation errors: {e.errors()}")
                raise Exception(f"Response validation failed: {str(e)}")
            
            # Post-process to validate citations
            processed_result = await self._post_process_analysis(
                motion_result, motion_text, extracted_citations
            )
            
            # Log completion
            if response.usage:
                logger.info(
                    f"Enhanced motion analysis completed - Arguments: {processed_result.total_arguments_found} - "
                    f"Tokens: {response.usage.total_tokens}"
                )
            
            return processed_result
            
        except Exception as e:
            logger.error(f"Motion analysis failed: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise

    def _ensure_enhanced_structure(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure the response has all required fields for enhanced analysis"""
        
        # Handle datetime
        if 'filing_date' in data and data['filing_date']:
            if isinstance(data['filing_date'], str):
                if not re.match(r'^\d{4}-\d{2}-\d{2}', data['filing_date']):
                    data['filing_date'] = None
            else:
                data['filing_date'] = None
        
        # Ensure required top-level fields
        required_fields = {
            'motion_type': 'Unknown Motion Type',
            'case_number': None,
            'parties': [],
            'filing_date': None,
            'all_arguments': [],
            'total_arguments_found': 0,
            'categories_used': [],
            'custom_categories_created': []
        }
        
        for field, default in required_fields.items():
            if field not in data:
                data[field] = default
        
        # Ensure enhanced argument structure
        if 'all_arguments' in data and isinstance(data['all_arguments'], list):
            for i, arg in enumerate(data['all_arguments']):
                if not isinstance(arg, dict):
                    continue
                
                # Basic fields
                arg.setdefault('argument_id', f"arg_{i+1:03d}")
                arg.setdefault('argument_text', '')
                arg.setdefault('detailed_summary', arg.get('argument_summary', 'No detailed summary provided'))
                arg.setdefault('excerpts_from_motion', [])
                arg.setdefault('category', 'other')
                arg.setdefault('subcategories', [])
                arg.setdefault('location_in_motion', 'Not specified')
                arg.setdefault('legal_basis', 'Not specified')
                arg.setdefault('factual_basis', None)
                arg.setdefault('strength_indicators', [])
                arg.setdefault('weaknesses', [])
                arg.setdefault('cited_cases', [])
                arg.setdefault('cited_statutes', [])
                arg.setdefault('counterarguments', [])
                arg.setdefault('strength_assessment', 'moderate')
                arg.setdefault('confidence_score', 0.8)
                arg.setdefault('requires_expert_response', False)
                arg.setdefault('priority_level', 3)
                
                # Enhanced research fields
                if 'research_priorities' not in arg or not arg['research_priorities']:
                    arg['research_priorities'] = [{
                        'research_question': f"How to counter the {arg.get('category', 'legal')} argument",
                        'suggested_search_terms': [arg.get('category', 'general'), 'counter-argument'],
                        'case_law_focus': 'Cases with similar fact patterns',
                        'factual_investigation': 'Review all discovery for contradicting evidence'
                    }]
                
                arg.setdefault('required_evidence', ['Relevant case documents', 'Witness testimony'])
                arg.setdefault('suggested_case_facts_to_find', ['Facts that contradict this argument'])
                
                # Ensure research priorities have correct structure
                for rp in arg.get('research_priorities', []):
                    if isinstance(rp, dict):
                        rp.setdefault('research_question', 'General research needed')
                        rp.setdefault('suggested_search_terms', [])
                        rp.setdefault('case_law_focus', None)
                        rp.setdefault('factual_investigation', None)
                
                # Validate category
                valid_categories = {cat.value for cat in ArgumentCategory}
                if arg.get('category') not in valid_categories:
                    arg['category'] = 'custom'
                
                # Validate enums
                if arg.get('strength_assessment') not in ['very_weak', 'weak', 'moderate', 'strong', 'very_strong']:
                    arg['strength_assessment'] = 'moderate'
                
                # Ensure numeric fields
                try:
                    arg['priority_level'] = max(1, min(5, int(arg.get('priority_level', 3))))
                except:
                    arg['priority_level'] = 3
                
                try:
                    arg['confidence_score'] = max(0, min(1, float(arg.get('confidence_score', 0.8))))
                except:
                    arg['confidence_score'] = 0.8
        
        # Update metadata
        data['total_arguments_found'] = len(data.get('all_arguments', []))
        
        if not data.get('categories_used'):
            data['categories_used'] = list(set(
                arg.get('category', 'other') 
                for arg in data.get('all_arguments', [])
                if isinstance(arg, dict)
            ))
        
        return data

    async def _extract_legal_citations(self, motion_text: str) -> List[Dict[str, Any]]:
        """Extract legal citations from motion text"""
        citations = []
        
        citation_patterns = [
            r'(\w+(?:\s+\w+)*)\s*v\.\s*(\w+(?:\s+\w+)*),?\s*(\d+)\s+(F\.\d?d|F\.\s?Supp\.?\s?\d?d?|U\.S\.)\s+(\d+)(?:\s*\(([^)]+)\s*(\d{4})\))?',
            r'(\w+(?:\s+\w+)*)\s*v\.\s*(\w+(?:\s+\w+)*),?\s*(\d+)\s+([A-Z][^,\d]*?)\s+(\d+)(?:\s*\(([^)]+)\s*(\d{4})\))?',
            r'(\d+)\s+(U\.S\.C\.|C\.F\.R\.|[A-Z][a-z]+\.\s*(?:Civ\.|Crim\.|Evid\.|R\.)\s*(?:Proc\.|Code)?)\s*§+\s*(\d+(?:\.\d+)*(?:\([a-zA-Z0-9]+\))*)',
        ]
        
        for pattern in citation_patterns:
            for match in re.finditer(pattern, motion_text, re.IGNORECASE):
                try:
                    if "U.S.C." in match.group(0) or "C.F.R." in match.group(0):
                        citations.append({
                            "full_citation": match.group(0).strip(),
                            "type": "statute"
                        })
                    else:
                        citations.append({
                            "full_citation": match.group(0).strip(),
                            "case_name": f"{match.group(1).strip()} v. {match.group(2).strip()}",
                            "type": "case"
                        })
                except:
                    continue
                    
        return citations[:50]

    async def _post_process_analysis(
        self, 
        result: ComprehensiveMotionAnalysis, 
        motion_text: str,
        extracted_citations: List[Dict[str, Any]]
    ) -> ComprehensiveMotionAnalysis:
        """Post-process to validate citations and ensure quality"""
        
        # Validate citations
        valid_case_names = {
            cite['case_name'].lower() 
            for cite in extracted_citations 
            if cite.get('type') == 'case'
        }
        
        for arg in result.all_arguments:
            # Clean citations
            clean_citations = []
            for citation in arg.cited_cases:
                if citation.case_name.lower() in motion_text.lower():
                    clean_citations.append(citation)
            arg.cited_cases = clean_citations
            
            # Ensure excerpts are actual quotes
            if not arg.excerpts_from_motion:
                # Try to find relevant excerpts
                excerpts = self._find_excerpts_for_argument(
                    motion_text, 
                    arg.argument_text,
                    arg.location_in_motion
                )
                arg.excerpts_from_motion = excerpts[:3]
        
        # Update counts
        result.total_arguments_found = len(result.all_arguments)
        result.categories_used = list(set(
            arg.category for arg in result.all_arguments
        ))
        
        # Identify custom categories
        standard_categories = {cat.value for cat in ArgumentCategory}
        result.custom_categories_created = [
            cat for cat in result.categories_used 
            if cat not in standard_categories
        ]
        
        return result

    def _find_excerpts_for_argument(
        self, 
        motion_text: str, 
        argument_text: str,
        location: str
    ) -> List[str]:
        """Try to find relevant excerpts from the motion"""
        excerpts = []
        
        # Split motion into sentences
        sentences = re.split(r'(?<=[.!?])\s+', motion_text)
        
        # Find sentences that might relate to this argument
        keywords = set(argument_text.lower().split())
        for sentence in sentences:
            if len(sentence) > 20 and len(sentence) < 300:
                sentence_words = set(sentence.lower().split())
                if len(keywords & sentence_words) >= 2:
                    excerpts.append(sentence.strip())
                    if len(excerpts) >= 3:
                        break
        
        return excerpts

    async def health_check(self) -> bool:
        """Perform health check"""
        if not self._initialized:
            return False
            
        try:
            response = await self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[{"role": "user", "content": "test"}]
            )
            return True
        except:
            return False

    async def cleanup(self):
        """Cleanup resources"""
        self._initialized = False
        self.client = None

# Add alias for compatibility
MotionAnalyzer = EnhancedMotionAnalyzer
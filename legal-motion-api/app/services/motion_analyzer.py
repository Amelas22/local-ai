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
    ArgumentGroup,
    LegalCitation, 
    ResearchPriority,
    ArgumentCategory,
    StrengthLevel,
    AnalysisOptions
)
from app.core.config import settings

logger = logging.getLogger(__name__)

class MotionAnalyzer:
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
            logger.info("Motion analyzer initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize motion analyzer: {e}")
            raise

    def _get_system_prompt(self) -> str:
        return """You are an expert legal analyst specializing in comprehensive motion analysis. Your primary goal is to extract EVERY SINGLE ARGUMENT from the opposing counsel's motion, no matter how minor, then categorize and analyze each one.

CRITICAL INSTRUCTIONS:
1. Extract ALL arguments first, then assign categories
2. Keep your response CONCISE to avoid truncation
3. Use ONLY these category values or "custom" if none fit:
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

You MUST respond with a valid JSON object that includes ALL of these required fields:

{
    "motion_type": "string - type of motion",
    "case_number": "string or null - case number if found",
    "parties": ["array of party names"],
    "filing_date": "ISO datetime string or null",
    "all_arguments": [
        {
            "argument_id": "arg_001",
            "argument_text": "BRIEF quote (under 100 chars)",
            "argument_summary": "CONCISE summary (under 150 chars)",
            "category": "use ONLY predefined category values listed above",
            "subcategories": ["additional categories if relevant"],
            "location_in_motion": "Section I.A",
            "legal_basis": "BRIEF legal foundation",
            "factual_basis": "BRIEF facts or null",
            "strength_indicators": ["2-3 key factors"],
            "weaknesses": ["1-2 weaknesses if any"],
            "cited_cases": [
                {
                    "full_citation": "Case v. Name, 123 F.3d 456 (Ct 2023)",
                    "case_name": "Case v. Name",
                    "legal_principle": "BRIEF principle",
                    "application": "BRIEF application",
                    "jurisdiction": "Court",
                    "year": 2023,
                    "is_binding": true,
                    "citation_strength": "strong"
                }
            ],
            "cited_statutes": ["28 U.S.C. § 1331"],
            "counterarguments": ["1-2 key counters"],
            "strength_assessment": "very_weak|weak|moderate|strong|very_strong",
            "confidence_score": 0.9,
            "requires_expert_response": false,
            "priority_level": 1
        }
    ],
    "argument_groups": [
        {
            "group_name": "Brief name",
            "theme": "BRIEF theme",
            "arguments": ["arg_001", "arg_002"],  /* List of argument IDs only */
            "combined_strength": "strong",
            "strategic_importance": "BRIEF importance"
        }
    ],
    "arguments_by_category": {
        "NOTE": "This will be built automatically from all_arguments - do not populate"
    },
    "primary_themes": ["2-3 main themes"],
    "strongest_arguments": ["arg_001", "arg_002"],
    "weakest_arguments": ["arg_005"],
    "implied_arguments": ["1-2 implied arguments"],
    "notable_omissions": ["1-2 missing arguments"],
    "research_priorities": [
        {
            "research_area": "BRIEF area",
            "priority_level": 1,
            "suggested_sources": ["1-2 sources"],
            "key_questions": ["1-2 questions"],
            "related_arguments": ["arg_001"]
        }
    ],
    "recommended_response_structure": ["3-5 steps"],
    "required_evidence": ["2-3 key evidence items"],
    "expert_witness_needs": ["1-2 areas if any"],
    "overall_strength": "very_weak|weak|moderate|strong|very_strong",
    "risk_assessment": 7,
    "confidence_in_analysis": 0.92,
    "recommended_actions": ["3-5 actions"],
    "total_arguments_found": 8,
    "categories_used": ["list of used categories"],
    "custom_categories_created": ["any custom categories"]
}

CRITICAL BREVITY RULES:
- Keep ALL text fields BRIEF and CONCISE
- argument_text: Under 100 characters
- argument_summary: Under 150 characters  
- strength_indicators: Maximum 3 items
- For argument_groups and arguments_by_category: Include ONLY first 2 arguments to save space
- Focus on extracting ALL arguments but describing them CONCISELY"""

    def _get_extraction_prompt(self) -> str:
        return """Focus on extracting arguments using these patterns:

1. Look for argument indicators:
   - "Plaintiff/Defendant argues..."
   - "The undisputed facts show..."
   - "As a matter of law..."
   - "Courts have held..."
   - "The evidence demonstrates..."
   - "Plaintiff fails to..."
   - "There is no genuine issue..."

2. Extract from motion structure:
   - Introduction/Background arguments
   - Each numbered or lettered section
   - Legal standard arguments
   - Application of law to facts
   - Policy arguments
   - Conclusion requests

3. Don't miss:
   - Arguments in footnotes
   - Arguments embedded in fact sections
   - Implicit arguments from case citations
   - Arguments about burden of proof
   - Procedural arguments mixed with substantive ones

Remember: When in doubt, extract it as a separate argument. Better to have too many than miss one."""

    async def _extract_legal_citations(self, motion_text: str) -> List[Dict[str, Any]]:
        """Extract legal citations from motion text without fabrication"""
        citations = []
        
        # Comprehensive pattern for legal citations
        citation_patterns = [
            # Federal cases: 123 F.3d 456 (9th Cir. 2020)
            r'(\w+(?:\s+\w+)*)\s*v\.\s*(\w+(?:\s+\w+)*),?\s*(\d+)\s+(F\.\d?d|F\.\s?Supp\.?\s?\d?d?|U\.S\.)\s+(\d+)(?:\s*\(([^)]+)\s*(\d{4})\))?',
            # State cases with various reporters
            r'(\w+(?:\s+\w+)*)\s*v\.\s*(\w+(?:\s+\w+)*),?\s*(\d+)\s+([A-Z][^,\d]*?)\s+(\d+)(?:\s*\(([^)]+)\s*(\d{4})\))?',
            # Statutory citations
            r'(\d+)\s+(U\.S\.C\.|C\.F\.R\.|[A-Z][a-z]+\.\s*(?:Civ\.|Crim\.|Evid\.|R\.)\s*(?:Proc\.|Code)?)\s*§+\s*(\d+(?:\.\d+)*(?:\([a-zA-Z0-9]+\))*)',
        ]
        
        for pattern in citation_patterns:
            for match in re.finditer(pattern, motion_text, re.IGNORECASE):
                try:
                    if "U.S.C." in match.group(0) or "C.F.R." in match.group(0) or "Code" in match.group(0):
                        # Statutory citation
                        citations.append({
                            "full_citation": match.group(0).strip(),
                            "type": "statute",
                            "title": match.group(1),
                            "code": match.group(2),
                            "section": match.group(3)
                        })
                    else:
                        # Case citation
                        case_name = f"{match.group(1).strip()} v. {match.group(2).strip()}"
                        volume = match.group(3)
                        reporter = match.group(4).strip()
                        page = match.group(5)
                        court = match.group(6) if match.group(6) else "Unknown"
                        year = int(match.group(7)) if match.group(7) else 0
                        
                        citations.append({
                            "full_citation": match.group(0).strip(),
                            "case_name": case_name,
                            "volume": volume,
                            "reporter": reporter,
                            "page": page,
                            "court": court,
                            "year": year,
                            "type": "case"
                        })
                except (ValueError, AttributeError):
                    continue
                    
        return citations[:50]  # Limit to prevent overwhelming responses

    async def analyze_motion(
        self, 
        motion_text: str, 
        case_context: Optional[str] = None,
        analysis_options: Optional[AnalysisOptions] = None
    ) -> ComprehensiveMotionAnalysis:
        """
        Analyze legal motion and extract ALL arguments with comprehensive structure
        """
        if not self._initialized:
            await self.initialize()
            
        try:
            # Extract citations separately for validation
            extracted_citations = await self._extract_legal_citations(motion_text)
            
            # Prepare the user prompt
            user_prompt = f"""Please analyze this legal motion and extract EVERY SINGLE ARGUMENT, no matter how minor.

MOTION TEXT:
{motion_text}

{"CASE CONTEXT: " + case_context if case_context else ""}

EXTRACTED CITATIONS (use only these):
{json.dumps(extracted_citations, indent=2)}

{self._get_extraction_prompt()}

Remember:
1. Extract ALL arguments first (aim for comprehensive coverage)
2. Assign appropriate categories (create custom ones if needed)
3. Each argument gets a unique ID (arg_001, arg_002, etc.)
4. Group related arguments
5. Identify strategic themes
6. Note what's missing or implied
7. Prioritize arguments for response

The goal is to ensure we don't miss ANY argument that needs to be addressed in our response."""

            # Make the API call with JSON mode
            response = await self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                response_format={"type": "json_object"},
                max_tokens=8000  # Increased from 4000 to handle comprehensive responses
            )
            
            # Parse the response
            result_data = json.loads(response.choices[0].message.content)
            
            # DEBUG: Log the raw response
            logger.info("=== RAW OPENAI RESPONSE ===")
            logger.info(json.dumps(result_data, indent=2)[:1000] + "...")  # First 1000 chars
            
            # Ensure proper structure for the new schema
            result_data = self._ensure_comprehensive_structure(result_data)
            
            # DEBUG: Log after ensuring structure
            logger.info("=== AFTER STRUCTURE ENSURING ===")
            logger.info(f"Keys present: {list(result_data.keys())}")
            logger.info(f"Total arguments: {len(result_data.get('all_arguments', []))}")
            
            # Validate and create the result object
            try:
                motion_result = ComprehensiveMotionAnalysis(**result_data)
            except ValidationError as e:
                logger.error("=== VALIDATION ERROR DETAILS ===")
                logger.error(f"Validation errors: {e.errors()}")
                logger.error(f"Failed data sample: {json.dumps(result_data, indent=2)[:500]}")
                
                # Try to identify specific issues
                for error in e.errors():
                    field = " -> ".join(str(x) for x in error['loc'])
                    logger.error(f"Field '{field}': {error['msg']}")
                
                raise Exception(f"Response validation failed: {str(e)}")
            
            # Post-process to validate citations and organize
            processed_result = await self._post_process_comprehensive_analysis(
                motion_result, motion_text, extracted_citations
            )
            
            # Log usage
            if response.usage:
                logger.info(
                    f"Motion analysis completed - Arguments found: {processed_result.total_arguments_found} - "
                    f"Tokens used: {response.usage.total_tokens}"
                )
            
            return processed_result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse OpenAI response as JSON: {e}")
            logger.error(f"Raw response: {response.choices[0].message.content[:500]}...")
            raise Exception("Analysis failed: Invalid response format from AI model")
            
        except ValidationError as e:
            logger.error(f"Response validation failed: {e}")
            raise Exception("Analysis failed: Response did not match expected format")
            
        except Exception as e:
            logger.error(f"Motion analysis failed: {e}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            raise Exception(f"Analysis failed: {str(e)}")

    def _ensure_comprehensive_structure(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure the response data has all required fields for ComprehensiveMotionAnalysis"""
        
        # DEBUG log
        logger.info(f"Ensuring structure for data with keys: {list(data.keys())}")
        
        # Handle datetime fields
        if 'filing_date' in data and data['filing_date']:
            # Ensure it's a string and looks like ISO format
            if isinstance(data['filing_date'], str):
                # Basic check for ISO format (YYYY-MM-DD or with time)
                if not re.match(r'^\d{4}-\d{2}-\d{2}', data['filing_date']):
                    logger.warning(f"Invalid filing_date format '{data['filing_date']}', setting to None")
                    data['filing_date'] = None
            else:
                data['filing_date'] = None
        
        # Ensure all required top-level fields exist
        required_fields = {
            'motion_type': 'Unknown Motion Type',
            'case_number': None,
            'parties': [],
            'filing_date': None,
            'all_arguments': [],
            'argument_groups': [],
            'arguments_by_category': {},
            'primary_themes': [],
            'strongest_arguments': [],
            'weakest_arguments': [],
            'implied_arguments': [],
            'notable_omissions': [],
            'research_priorities': [],
            'recommended_response_structure': [],
            'required_evidence': [],
            'expert_witness_needs': [],
            'overall_strength': 'moderate',
            'risk_assessment': 5,
            'confidence_in_analysis': 0.85,
            'recommended_actions': [],
            'total_arguments_found': 0,
            'categories_used': [],
            'custom_categories_created': []
        }
        
        # Add missing fields with defaults
        for field, default in required_fields.items():
            if field not in data:
                logger.warning(f"Missing field '{field}', adding default: {default}")
                data[field] = default
        
        # Ensure all_arguments have proper structure
        if 'all_arguments' in data and isinstance(data['all_arguments'], list):
            for i, arg in enumerate(data['all_arguments']):
                if not isinstance(arg, dict):
                    logger.error(f"Argument {i} is not a dict: {type(arg)}")
                    continue
                    
                # Validate and fix category
                valid_categories = {cat.value for cat in ArgumentCategory}
                if arg.get('category') not in valid_categories:
                    # Try to map common mistakes to valid categories
                    category_map = {
                        'statute of limitations': 'procedural_statute_limitations',
                        'jurisdiction': 'procedural_jurisdiction',
                        'venue': 'procedural_venue',
                        'standing': 'procedural_standing',
                        'vicarious liability': 'liability_vicarious',
                        'derivative liability': 'liability_derivative',
                        'negligence': 'negligence_breach',
                        'causation': 'negligence_causation',
                        'damages': 'damages_economic',
                        'expert': 'expert_qualification',
                        'evidence': 'evidence_admissibility'
                    }
                    
                    # Try to find a match in our mapping
                    original_cat = arg.get('category', '').lower()
                    mapped = False
                    for key, value in category_map.items():
                        if key in original_cat:
                            logger.warning(f"Mapping category '{arg.get('category')}' to '{value}'")
                            arg['category'] = value
                            mapped = True
                            break
                    
                    if not mapped:
                        logger.warning(f"Unknown category '{arg.get('category')}', using 'custom'")
                        arg['category'] = 'custom'
                arg_defaults = {
                    'argument_id': f"arg_{i+1:03d}",
                    'argument_text': arg.get('argument_summary', ''),
                    'argument_summary': 'No summary provided',
                    'category': 'other',
                    'subcategories': [],
                    'location_in_motion': 'Not specified',
                    'legal_basis': 'Not specified',
                    'factual_basis': None,
                    'strength_indicators': [],
                    'weaknesses': [],
                    'cited_cases': [],
                    'cited_statutes': [],
                    'counterarguments': [],
                    'strength_assessment': 'moderate',
                    'confidence_score': 0.8,
                    'requires_expert_response': False,
                    'priority_level': 3
                }
                
                for field, default in arg_defaults.items():
                    if field not in arg:
                        arg[field] = default
                
                # Validate and fix category
                valid_categories = {cat.value for cat in ArgumentCategory}
                if arg.get('category') not in valid_categories:
                    # Try to map common mistakes to valid categories
                    category_map = {
                        'statute of limitations': 'procedural_statute_limitations',
                        'jurisdiction': 'procedural_jurisdiction',
                        'venue': 'procedural_venue',
                        'standing': 'procedural_standing',
                        'vicarious liability': 'liability_vicarious',
                        'derivative liability': 'liability_derivative',
                        'negligence': 'negligence_breach',
                        'causation': 'negligence_causation',
                        'damages': 'damages_economic',
                        'expert': 'expert_qualification',
                        'evidence': 'evidence_admissibility'
                    }
                    
                    # Try to find a match in our mapping
                    original_cat = arg.get('category', '').lower()
                    mapped = False
                    for key, value in category_map.items():
                        if key in original_cat:
                            logger.warning(f"Mapping category '{arg.get('category')}' to '{value}'")
                            arg['category'] = value
                            mapped = True
                            break
                    
                    if not mapped:
                        logger.warning(f"Unknown category '{arg.get('category')}', using 'custom'")
                        arg['category'] = 'custom'
                
                # Validate strength_assessment enum
                valid_strengths = ['very_weak', 'weak', 'moderate', 'strong', 'very_strong']
                if arg.get('strength_assessment') not in valid_strengths:
                    logger.warning(f"Invalid strength '{arg.get('strength_assessment')}', setting to 'moderate'")
                    arg['strength_assessment'] = 'moderate'
                
                # Ensure priority_level is int between 1-5
                try:
                    arg['priority_level'] = max(1, min(5, int(arg.get('priority_level', 3))))
                except:
                    arg['priority_level'] = 3
                
                # Ensure confidence_score is float between 0-1
                try:
                    arg['confidence_score'] = max(0, min(1, float(arg.get('confidence_score', 0.8))))
                except:
                    arg['confidence_score'] = 0.8
        
        # Build arguments_by_category if not present or empty
        if not data.get('arguments_by_category') and data.get('all_arguments'):
            data['arguments_by_category'] = {}
            for arg in data['all_arguments']:
                category = arg.get('category', 'other')
                if category not in data['arguments_by_category']:
                    data['arguments_by_category'][category] = []
                data['arguments_by_category'][category].append(arg)
        
        # ALWAYS rebuild arguments_by_category to ensure full objects
        if data.get('all_arguments'):
            logger.info("Rebuilding arguments_by_category from all_arguments to ensure completeness")
            data['arguments_by_category'] = {}
            for arg in data['all_arguments']:
                if isinstance(arg, dict) and 'category' in arg:
                    category = arg['category']
                    if category not in data['arguments_by_category']:
                        data['arguments_by_category'][category] = []
                    # Ensure we're adding the full argument object
                    data['arguments_by_category'][category].append(arg)
        
        # Ensure research_priorities have required fields
        if 'research_priorities' in data:
            for rp in data['research_priorities']:
                if not isinstance(rp, dict):
                    continue
                rp.setdefault('research_area', 'General research')
                rp.setdefault('priority_level', 3)
                rp.setdefault('suggested_sources', [])
                rp.setdefault('key_questions', [])
                rp.setdefault('related_arguments', [])
        
        # Ensure argument_groups have proper structure
        if 'argument_groups' in data:
            for group in data['argument_groups']:
                if not isinstance(group, dict):
                    continue
                group.setdefault('group_name', 'Unnamed Group')
                group.setdefault('theme', 'No theme specified')
                group.setdefault('combined_strength', 'moderate')
                group.setdefault('strategic_importance', 'Not specified')
                
                # Convert arguments to list of IDs if they're objects
                if 'arguments' in group and isinstance(group['arguments'], list):
                    arg_ids = []
                    for arg in group['arguments']:
                        if isinstance(arg, dict) and 'argument_id' in arg:
                            arg_ids.append(arg['argument_id'])
                        elif isinstance(arg, str):
                            arg_ids.append(arg)
                    group['arguments'] = arg_ids
                else:
                    group['arguments'] = []
        
        # Update counts
        data['total_arguments_found'] = len(data.get('all_arguments', []))
        
        if 'categories_used' not in data or not data['categories_used']:
            data['categories_used'] = list(data.get('arguments_by_category', {}).keys())
        
        # Validate overall_strength enum
        valid_overall_strengths = ['very_weak', 'weak', 'moderate', 'strong', 'very_strong']
        if data.get('overall_strength') not in valid_overall_strengths:
            data['overall_strength'] = 'moderate'
        
        # Ensure risk_assessment is int 1-10
        try:
            data['risk_assessment'] = max(1, min(10, int(data.get('risk_assessment', 5))))
        except:
            data['risk_assessment'] = 5
            
        return data

    async def _post_process_comprehensive_analysis(
        self, 
        result: ComprehensiveMotionAnalysis, 
        motion_text: str,
        extracted_citations: List[Dict[str, Any]]
    ) -> ComprehensiveMotionAnalysis:
        """Post-process comprehensive analysis for quality and completeness"""
        
        # Create a set of valid citation names for quick lookup
        valid_case_citations = {
            cite['case_name'].lower() 
            for cite in extracted_citations 
            if cite.get('type') == 'case'
        }
        valid_statute_citations = {
            cite['full_citation'].lower() 
            for cite in extracted_citations 
            if cite.get('type') == 'statute'
        }
        
        # Validate and clean citations in each argument
        for arg in result.all_arguments:
            # Clean case citations
            clean_citations = []
            for citation in arg.cited_cases:
                if (citation.case_name.lower() in motion_text.lower() or 
                    citation.case_name.lower() in valid_case_citations):
                    clean_citations.append(citation)
                else:
                    logger.warning(f"Removed potentially fabricated citation: {citation.case_name}")
            arg.cited_cases = clean_citations
            
            # Validate statute citations
            clean_statutes = []
            for statute in arg.cited_statutes:
                if (statute.lower() in motion_text.lower() or 
                    any(statute.lower() in cite for cite in valid_statute_citations)):
                    clean_statutes.append(statute)
            arg.cited_statutes = clean_statutes
        
        # Identify any arguments that might have been missed
        potential_missed = self._check_for_missed_arguments(motion_text, result)
        if potential_missed:
            result.notable_omissions.extend(potential_missed)
        
        # Ensure research priorities reference actual arguments
        for priority in result.research_priorities:
            if not priority.related_arguments:
                # Link to relevant arguments based on research area
                related = [
                    arg.argument_id for arg in result.all_arguments
                    if priority.research_area.lower() in arg.argument_summary.lower()
                ]
                priority.related_arguments = related[:3]  # Top 3 related
        
        # Update metadata
        result.total_arguments_found = len(result.all_arguments)
        result.categories_used = list(result.arguments_by_category.keys())
        
        # Identify custom categories (those not in ArgumentCategory enum)
        standard_categories = {cat.value for cat in ArgumentCategory}
        result.custom_categories_created = [
            cat for cat in result.categories_used 
            if cat not in standard_categories
        ]
        
        return result

    def _check_for_missed_arguments(
        self, 
        motion_text: str, 
        result: ComprehensiveMotionAnalysis
    ) -> List[str]:
        """Check for potentially missed arguments based on common patterns"""
        missed = []
        
        # Check for common argument patterns not covered
        patterns_to_check = [
            (r"statute of limitations", "Statute of limitations argument"),
            (r"failure to state a claim", "Failure to state a claim argument"),
            (r"lack of standing", "Standing challenge"),
            (r"improper venue", "Venue challenge"),
            (r"personal jurisdiction", "Personal jurisdiction challenge"),
            (r"failure to join.*party", "Failure to join necessary party"),
            (r"res judicata|collateral estoppel", "Preclusion argument"),
            (r"arbitration clause|agreement", "Arbitration argument"),
            (r"qualified immunity", "Qualified immunity defense"),
            (r"governmental immunity", "Governmental immunity defense"),
        ]
        
        existing_summaries = " ".join([
            arg.argument_summary.lower() for arg in result.all_arguments
        ])
        
        for pattern, description in patterns_to_check:
            if re.search(pattern, motion_text, re.IGNORECASE):
                if not re.search(pattern, existing_summaries, re.IGNORECASE):
                    missed.append(f"Potential {description} not fully extracted")
        
        return missed[:5]  # Limit to top 5 to avoid noise

    async def health_check(self) -> bool:
        """Perform health check on the motion analyzer"""
        if not self._initialized:
            return False
            
        try:
            # Simple test to verify OpenAI connection
            response = await self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=10
            )
            return True
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

    async def cleanup(self):
        """Cleanup resources"""
        self._initialized = False
        self.client = None
        logger.info("Motion analyzer cleaned up")
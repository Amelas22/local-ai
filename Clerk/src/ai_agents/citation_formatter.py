"""
Citation Formatter and Evidence Extractor
Extracts and formats legal citations with proper page/line references and exhibit numbers
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger("clerk_api")


class CitationType(Enum):
    """Types of legal citations"""
    DEPOSITION = "deposition"
    EXHIBIT = "exhibit"
    CASE_LAW = "case_law"
    STATUTE = "statute"
    REGULATION = "regulation"
    DOCUMENT = "document"
    EXPERT_REPORT = "expert_report"
    MEDICAL_RECORD = "medical_record"
    INTERNAL_COMMUNICATION = "internal_communication"


@dataclass
class Citation:
    """Structured citation with all relevant information"""
    citation_type: CitationType
    full_text: str
    formatted_citation: str
    source_name: Optional[str] = None
    page_reference: Optional[str] = None
    line_reference: Optional[str] = None
    exhibit_number: Optional[str] = None
    date: Optional[str] = None
    parenthetical: Optional[str] = None
    confidence_score: float = 1.0


class CitationFormatter:
    """Formats and extracts citations from legal text and search results"""
    
    def __init__(self):
        """Initialize citation formatter with regex patterns"""
        self.patterns = self._compile_patterns()
        
    def _compile_patterns(self) -> Dict[str, re.Pattern]:
        """Compile regex patterns for different citation types"""
        return {
            # Deposition patterns
            'deposition_full': re.compile(
                r'(?:Deposition\s+of|Dep\.\s+of|Depo\.\s+of)\s+([^,]+?)\s+'
                r'(?:at|p\.|pp\.)\s*(\d+(?:[-]\d+)?)'
                r'(?:\s*:\s*(\d+(?:[-]\d+)?))?',
                re.IGNORECASE
            ),
            'deposition_page_line': re.compile(
                r'(\d+:\d+(?:[-]\d+)?)', re.IGNORECASE
            ),
            
            # Exhibit patterns
            'exhibit': re.compile(
                r'(?:Exhibit|Ex\.|Exh\.)\s*([A-Z0-9]+(?:[-][A-Z0-9]+)?)',
                re.IGNORECASE
            ),
            'exhibit_with_desc': re.compile(
                r'(?:Exhibit|Ex\.|Exh\.)\s*([A-Z0-9]+)(?:\s*[-]\s*([^,\.\)]+))?',
                re.IGNORECASE
            ),
            
            # Document patterns
            'document_log': re.compile(
                r'(?:Maintenance\s+Log|Driver\s+Log|Safety\s+Report|Inspection\s+Report)'
                r'\s*(?:No\.|Nos\.|#)?\s*(\d+(?:[-]\d+)?)',
                re.IGNORECASE
            ),
            
            # Expert report patterns
            'expert_report': re.compile(
                r'(?:Expert\s+Report\s+of|Report\s+of)\s+(?:Dr\.|Mr\.|Ms\.)\s*([^,]+?)'
                r'(?:\s+at\s+(\d+(?:[-]\d+)?))?',
                re.IGNORECASE
            ),
            
            # Internal communication patterns
            'email': re.compile(
                r'(?:Email|E-mail)\s+(?:from|by)\s+([^,]+?)\s+'
                r'(?:dated|on)\s+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
                re.IGNORECASE
            ),
            
            # Date patterns
            'date': re.compile(
                r'(?:January|February|March|April|May|June|July|August|September|October|November|December)'
                r'\s+\d{1,2},?\s+\d{4}|'
                r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',
                re.IGNORECASE
            ),
            
            # Case law patterns
            'case_law': re.compile(
                r'([A-Z][a-zA-Z]+(?:\s+[a-zA-Z]+)*)\s+v\.\s+'
                r'([A-Z][a-zA-Z]+(?:\s+[a-zA-Z]+)*),?\s*'
                r'(\d+\s+(?:So\.|F\.|U\.S\.|S\.\s*Ct\.)\s*(?:\d+d)?\s+\d+)'
                r'(?:\s*\(([^)]+)\))?'
            ),
            
            # Statute patterns
            'statute': re.compile(
                r'(\d+)\s+(U\.S\.C\.|Fla\.\s*Stat\.)\s*(?:§|section)*\s*(\d+[\w\-\.]*)',
                re.IGNORECASE
            ),
            
            # Regulation patterns
            'regulation': re.compile(
                r'(\d+)\s+C\.F\.R\.\s*(?:§|section)*\s*(\d+\.\d+)',
                re.IGNORECASE
            ),
            
            # FMCSR patterns
            'fmcsr': re.compile(
                r'FMCSR\s+(\d+\.\d+(?:\([a-z]\)(?:\(\d+\))?)?)',
                re.IGNORECASE
            )
        }
    
    def extract_citations_from_text(self, text: str) -> List[Citation]:
        """Extract all citations from a text block"""
        citations = []
        
        # Extract depositions
        for match in self.patterns['deposition_full'].finditer(text):
            deponent = match.group(1).strip()
            pages = match.group(2)
            lines = match.group(3) if match.group(3) else None
            
            if lines:
                formatted = f"{deponent} Dep. {pages}:{lines}"
            else:
                formatted = f"{deponent} Dep. {pages}"
            
            citations.append(Citation(
                citation_type=CitationType.DEPOSITION,
                full_text=match.group(0),
                formatted_citation=formatted,
                source_name=deponent,
                page_reference=pages,
                line_reference=lines
            ))
        
        # Extract exhibits
        for match in self.patterns['exhibit_with_desc'].finditer(text):
            exhibit_num = match.group(1)
            description = match.group(2).strip() if match.group(2) else None
            
            if description:
                formatted = f"Ex. {exhibit_num} ({description})"
            else:
                formatted = f"Ex. {exhibit_num}"
            
            citations.append(Citation(
                citation_type=CitationType.EXHIBIT,
                full_text=match.group(0),
                formatted_citation=formatted,
                exhibit_number=exhibit_num,
                source_name=description
            ))
        
        # Extract case law
        for match in self.patterns['case_law'].finditer(text):
            plaintiff = match.group(1)
            defendant = match.group(2)
            reporter = match.group(3)
            court_year = match.group(4) if match.group(4) else None
            
            case_name = f"{plaintiff} v. {defendant}"
            if court_year:
                formatted = f"{case_name}, {reporter} ({court_year})"
            else:
                formatted = f"{case_name}, {reporter}"
            
            citations.append(Citation(
                citation_type=CitationType.CASE_LAW,
                full_text=match.group(0),
                formatted_citation=formatted,
                source_name=case_name,
                parenthetical=court_year
            ))
        
        # Extract FMCSR violations
        for match in self.patterns['fmcsr'].finditer(text):
            section = match.group(1)
            formatted = f"49 C.F.R. � {section}"
            
            citations.append(Citation(
                citation_type=CitationType.REGULATION,
                full_text=match.group(0),
                formatted_citation=formatted,
                source_name=f"FMCSR {section}"
            ))
        
        return citations
    
    def format_search_result_as_citation(
        self, 
        search_result: Dict[str, Any],
        citation_hint: Optional[str] = None
    ) -> Optional[Citation]:
        """Format a search result into a proper citation"""
        
        content = search_result.get('content', '')
        metadata = search_result.get('metadata', {})
        
        # Try to determine citation type from metadata
        doc_type = metadata.get('document_type', '').lower()
        doc_name = metadata.get('document_name', '')
        
        # Handle deposition
        if 'deposition' in doc_type or 'depo' in doc_name.lower():
            return self._format_deposition_citation(content, metadata)
        
        # Handle expert report
        elif 'expert' in doc_type and 'report' in doc_type:
            return self._format_expert_citation(content, metadata)
        
        # Handle exhibit
        elif 'exhibit' in doc_type or re.search(r'ex(?:hibit)?\s*\d+', doc_name, re.I):
            return self._format_exhibit_citation(content, metadata)
        
        # Handle internal documents
        elif any(term in doc_type for term in ['email', 'memo', 'policy', 'manual']):
            return self._format_internal_doc_citation(content, metadata)
        
        # Default document citation
        else:
            return self._format_document_citation(content, metadata)
    
    def _format_deposition_citation(
        self, 
        content: str, 
        metadata: Dict[str, Any]
    ) -> Optional[Citation]:
        """Format a deposition citation with page and line numbers"""
        
        # Extract deponent name
        doc_name = metadata.get('document_name', '')
        deponent_match = re.search(r'deposition\s+of\s+([^,\-]+)', doc_name, re.I)
        if deponent_match:
            deponent = deponent_match.group(1).strip()
        else:
            deponent = doc_name.split('_')[0].strip()
        
        # Look for page/line references in content
        page_line_match = self.patterns['deposition_page_line'].search(content)
        if page_line_match:
            page_line = page_line_match.group(0)
            formatted = f"{deponent} Dep. {page_line}"
        else:
            # Try to get page from metadata
            page = metadata.get('page_number', metadata.get('page', ''))
            if page:
                formatted = f"{deponent} Dep. {page}"
            else:
                formatted = f"{deponent} Dep."
        
        return Citation(
            citation_type=CitationType.DEPOSITION,
            full_text=content[:100] + "...",
            formatted_citation=formatted,
            source_name=deponent,
            page_reference=str(page) if 'page' in locals() else None
        )
    
    def _format_expert_citation(
        self, 
        content: str, 
        metadata: Dict[str, Any]
    ) -> Optional[Citation]:
        """Format an expert report citation"""
        
        doc_name = metadata.get('document_name', '')
        
        # Extract expert name
        expert_match = re.search(r'(?:dr\.|mr\.|ms\.)\s*([^,\-_]+)', doc_name, re.I)
        if expert_match:
            expert = expert_match.group(0).strip()
        else:
            expert = doc_name.split('_')[0].strip()
        
        # Get page reference
        page = metadata.get('page_number', metadata.get('page', ''))
        if page:
            formatted = f"Expert Report of {expert} at {page}"
        else:
            formatted = f"Expert Report of {expert}"
        
        # Try to extract exhibit number
        exhibit_match = self.patterns['exhibit'].search(doc_name)
        if exhibit_match:
            exhibit_num = exhibit_match.group(1)
            formatted += f", Ex. {exhibit_num}"
            
        return Citation(
            citation_type=CitationType.EXPERT_REPORT,
            full_text=content[:100] + "...",
            formatted_citation=formatted,
            source_name=expert,
            page_reference=str(page) if page else None,
            exhibit_number=exhibit_num if 'exhibit_num' in locals() else None
        )
    
    def _format_exhibit_citation(
        self, 
        content: str, 
        metadata: Dict[str, Any]
    ) -> Optional[Citation]:
        """Format an exhibit citation"""
        
        doc_name = metadata.get('document_name', '')
        
        # Extract exhibit number
        exhibit_match = self.patterns['exhibit'].search(doc_name)
        if exhibit_match:
            exhibit_num = exhibit_match.group(1)
        else:
            # Try numeric extraction
            num_match = re.search(r'\d+', doc_name)
            exhibit_num = num_match.group(0) if num_match else "?"
        
        # Get description
        doc_type = metadata.get('document_type', '')
        if doc_type and doc_type != 'exhibit':
            description = doc_type.replace('_', ' ').title()
            formatted = f"Ex. {exhibit_num} ({description})"
        else:
            formatted = f"Ex. {exhibit_num}"
        
        return Citation(
            citation_type=CitationType.EXHIBIT,
            full_text=content[:100] + "...",
            formatted_citation=formatted,
            exhibit_number=exhibit_num,
            source_name=doc_name
        )
    
    def _format_internal_doc_citation(
        self, 
        content: str, 
        metadata: Dict[str, Any]
    ) -> Optional[Citation]:
        """Format internal document citations (emails, memos, policies)"""
        
        doc_type = metadata.get('document_type', '').lower()
        doc_name = metadata.get('document_name', '')
        
        # Extract date if available
        date_match = self.patterns['date'].search(doc_name + ' ' + content[:200])
        date = date_match.group(0) if date_match else metadata.get('date', '')
        
        if 'email' in doc_type:
            # Try to extract sender
            sender_match = re.search(r'from[:\s]+([^,\n]+)', content[:200], re.I)
            sender = sender_match.group(1).strip() if sender_match else "Company Official"
            
            if date:
                formatted = f"Email from {sender} dated {date}"
            else:
                formatted = f"Email from {sender}"
                
        elif 'policy' in doc_type or 'manual' in doc_type:
            formatted = f"Company {doc_type.title()}"
            if date:
                formatted += f" ({date})"
                
        else:
            formatted = doc_name.replace('_', ' ').title()
            if date:
                formatted += f" dated {date}"
        
        return Citation(
            citation_type=CitationType.INTERNAL_COMMUNICATION,
            full_text=content[:100] + "...",
            formatted_citation=formatted,
            source_name=doc_name,
            date=date if date else None
        )
    
    def _format_document_citation(
        self, 
        content: str, 
        metadata: Dict[str, Any]
    ) -> Optional[Citation]:
        """Format generic document citation"""
        
        doc_name = metadata.get('document_name', '')
        doc_type = metadata.get('document_type', '')
        
        # Clean up document name
        clean_name = doc_name.replace('_', ' ').title()
        
        # Add page reference if available
        page = metadata.get('page_number', metadata.get('page', ''))
        if page:
            formatted = f"{clean_name} at {page}"
        else:
            formatted = clean_name
        
        # Add date if available
        date_match = self.patterns['date'].search(doc_name + ' ' + content[:200])
        if date_match:
            formatted += f" ({date_match.group(0)})"
        
        return Citation(
            citation_type=CitationType.DOCUMENT,
            full_text=content[:100] + "...",
            formatted_citation=formatted,
            source_name=doc_name,
            page_reference=str(page) if page else None
        )
    
    def enhance_text_with_citations(
        self, 
        text: str, 
        search_results: List[Dict[str, Any]]
    ) -> str:
        """Enhance text by adding proper citations from search results"""
        
        # Format all search results as citations
        citations = []
        for result in search_results:
            citation = self.format_search_result_as_citation(result)
            if citation:
                citations.append(citation)
        
        # Group citations by type for better organization
        citations_by_type = {}
        for citation in citations:
            if citation.citation_type not in citations_by_type:
                citations_by_type[citation.citation_type] = []
            citations_by_type[citation.citation_type].append(citation)
        
        # Add citations to text in a structured way
        enhanced_text = text
        
        # Add footnote-style citations
        if citations:
            enhanced_text += "\n\n[Supporting Evidence: "
            citation_strings = []
            
            for cit_type, cits in citations_by_type.items():
                for cit in cits[:3]:  # Limit to 3 per type
                    citation_strings.append(cit.formatted_citation)
            
            enhanced_text += "; ".join(citation_strings) + "]"
        
        return enhanced_text
    
    def create_citation_index(
        self, 
        drafted_sections: List[Any]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Create an index of all citations used in the motion"""
        
        citation_index = {}
        
        for section in drafted_sections:
            # Extract citations from section content
            citations = self.extract_citations_from_text(section.content)
            
            for citation in citations:
                key = citation.formatted_citation
                if key not in citation_index:
                    citation_index[key] = []
                
                citation_index[key].append({
                    'section': section.outline_section.title,
                    'type': citation.citation_type.value,
                    'full_text': citation.full_text[:100] + "..."
                })
        
        return citation_index


# Create global instance
citation_formatter = CitationFormatter()
"""
Discovery Document Splitter Module
Handles segmentation of large multi-document PDFs from discovery productions
"""

import logging
import re
import io
import json
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass

import PyPDF2
import pdfplumber
import openai
from openai import OpenAI

from src.models.unified_document_models import (
    DocumentBoundary,
    DiscoverySegment,
    DiscoveryProductionResult,
    DocumentType,
    LargeDocumentProcessingStrategy
)
from src.document_processing.pdf_extractor import PDFExtractor
from src.document_processing.chunker import DocumentChunker
from src.document_processing.context_generator import ContextGenerator
from config.settings import settings

logger = logging.getLogger(__name__)


class BoundaryDetector:
    """Detects document boundaries within large multi-document PDFs"""
    
    def __init__(self, model: str = None):
        """Initialize boundary detector with specified model"""
        self.model = model or settings.discovery.boundary_detection_model
        self.client = OpenAI(api_key=settings.openai.api_key)
        self.confidence_threshold = settings.discovery.boundary_confidence_threshold
        
    def detect_all_boundaries(self, pdf_path: str, 
                            window_size: int = None,
                            window_overlap: int = None) -> List[DocumentBoundary]:
        """
        Detect all document boundaries in a PDF using sliding window approach
        
        Args:
            pdf_path: Path to PDF file
            window_size: Number of pages per window (default from settings)
            window_overlap: Overlap between windows (default from settings)
            
        Returns:
            List of detected document boundaries
        """
        # Use settings defaults if not provided
        window_size = window_size or settings.discovery.window_size
        window_overlap = window_overlap or settings.discovery.window_overlap
        
        logger.info(f"Starting boundary detection for: {pdf_path}")
        logger.info(f"Window size: {window_size}, Overlap: {window_overlap}")
        
        # Get total page count
        total_pages = self._get_pdf_page_count(pdf_path)
        logger.info(f"Total pages in PDF: {total_pages}")
        
        # Process windows
        all_boundaries = []
        stride = window_size - window_overlap
        
        for window_start in range(0, total_pages, stride):
            window_end = min(window_start + window_size, total_pages)
            
            logger.info(f"Processing window: pages {window_start} to {window_end}")
            
            # Extract window text
            window_text = self._extract_pages(pdf_path, window_start, window_end)
            
            # Detect boundaries in this window
            window_boundaries = self._detect_boundaries_in_window(
                window_text, 
                window_start,
                window_end
            )
            
            # Add window info to boundaries
            for boundary in window_boundaries:
                boundary.detection_window = (window_start, window_end)
            
            all_boundaries.extend(window_boundaries)
        
        # Reconcile overlapping detections
        reconciled_boundaries = self._reconcile_boundaries(all_boundaries)
        
        logger.info(f"Found {len(reconciled_boundaries)} unique document boundaries")
        return reconciled_boundaries
    
    def _get_pdf_page_count(self, pdf_path: str) -> int:
        """Get total page count from PDF"""
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            return len(pdf_reader.pages)
    
    def _extract_pages(self, pdf_path: str, start_page: int, end_page: int) -> str:
        """Extract text from specified page range"""
        text_parts = []
        
        with pdfplumber.open(pdf_path) as pdf:
            for page_num in range(start_page, min(end_page, len(pdf.pages))):
                page = pdf.pages[page_num]
                page_text = page.extract_text() or ""
                
                # Add page marker for reference
                text_parts.append(f"\n[Page {page_num + 1}]\n{page_text}")
        
        return "\n".join(text_parts)
    
    def _detect_boundaries_in_window(self, window_text: str, 
                                   start_page: int,
                                   end_page: int) -> List[DocumentBoundary]:
        """Use LLM to detect document boundaries in window"""
        
        prompt = f"""You are analyzing pages {start_page + 1} to {end_page} of a large discovery production PDF that contains multiple documents concatenated together.

Your task is to identify where one document ends and another begins. Look for:

1. Document headers/titles (e.g., "DRIVER QUALIFICATION FILE", "BILL OF LADING", "EMPLOYMENT APPLICATION")
2. Form numbers (e.g., "Form MCSA-5876", "DOT Form")
3. Letterheads or company names at the top of pages
4. Date/time stamps indicating new documents
5. Signature blocks that typically end documents
6. Page numbering that resets (e.g., "Page 1 of 3" after previous document)
7. Significant format changes
8. Bates number sequences

For each boundary you find, provide:
- The page number where the NEW document starts
- Your confidence level (0.0 to 1.0)
- The type of document if identifiable
- The indicators that suggest this is a new document

Return your response as a JSON array of boundaries.

Example format:
[
  {{
    "start_page": 15,
    "confidence": 0.9,
    "document_type_hint": "DRIVER_QUALIFICATION_FILE",
    "indicators": ["Header 'DRIVER QUALIFICATION FILE' at top of page", "New letterhead", "Previous document ended with signature"]
  }},
  {{
    "start_page": 28,
    "confidence": 0.85,
    "document_type_hint": "BILL_OF_LADING",
    "indicators": ["Form number 'Bill of Lading' visible", "Date format change", "New formatting style"]
  }}
]

Text to analyze:
{window_text[:50000]}  # Limit to prevent token overflow
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a legal document analysis expert specializing in discovery document processing."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,  # Low temperature for consistency
                response_format={"type": "json_object"}
            )
            
            boundaries_data = json.loads(response.choices[0].message.content)
            
            # Convert to DocumentBoundary objects
            boundaries = []
            
            # Handle both array and object responses
            if isinstance(boundaries_data, dict) and "boundaries" in boundaries_data:
                boundaries_data = boundaries_data["boundaries"]
            elif not isinstance(boundaries_data, list):
                logger.warning(f"Unexpected response format: {type(boundaries_data)}")
                return []
            
            prev_start = start_page
            for i, boundary_info in enumerate(boundaries_data):
                # Adjust page numbers to 0-indexed
                boundary_start = boundary_info["start_page"] - 1
                
                # Create boundary for previous document ending
                if boundary_start > prev_start:
                    boundaries.append(DocumentBoundary(
                        start_page=prev_start,
                        end_page=boundary_start - 1,
                        confidence=boundary_info.get("confidence", 0.8),
                        document_type_hint=self._map_document_type(
                            boundary_info.get("document_type_hint", "OTHER")
                        ),
                        boundary_indicators=boundary_info.get("indicators", [])
                    ))
                
                prev_start = boundary_start
            
            # Add final boundary if needed
            if prev_start < end_page - 1:
                boundaries.append(DocumentBoundary(
                    start_page=prev_start,
                    end_page=end_page - 1,
                    confidence=0.8,
                    document_type_hint=DocumentType.OTHER,
                    boundary_indicators=["End of window"]
                ))
            
            return boundaries
            
        except Exception as e:
            logger.error(f"Error detecting boundaries: {str(e)}")
            return []
    
    def _map_document_type(self, type_hint: str) -> Optional[DocumentType]:
        """Map string hint to DocumentType enum"""
        # Normalize the hint
        normalized = type_hint.upper().replace(" ", "_").replace("-", "_")
        
        try:
            return DocumentType(normalized.lower())
        except ValueError:
            # Try to find closest match
            for doc_type in DocumentType:
                if normalized in doc_type.value.upper():
                    return doc_type
            return DocumentType.OTHER
    
    def _reconcile_boundaries(self, boundaries: List[DocumentBoundary]) -> List[DocumentBoundary]:
        """Reconcile overlapping boundary detections from different windows"""
        if not boundaries:
            return []
        
        # Sort by start page
        sorted_boundaries = sorted(boundaries, key=lambda b: b.start_page)
        
        reconciled = []
        current = sorted_boundaries[0]
        
        for next_boundary in sorted_boundaries[1:]:
            # Check for overlap or adjacency
            if next_boundary.start_page <= current.end_page + 1:
                # Merge if they represent the same document
                if self._is_same_document(current, next_boundary):
                    # Merge boundaries, keeping higher confidence
                    current = self._merge_boundaries(current, next_boundary)
                else:
                    # Different documents - adjust end page of current
                    current.end_page = next_boundary.start_page - 1
                    reconciled.append(current)
                    current = next_boundary
            else:
                # Gap between boundaries - add current and move to next
                reconciled.append(current)
                current = next_boundary
        
        # Add final boundary
        reconciled.append(current)
        
        return reconciled
    
    def _is_same_document(self, b1: DocumentBoundary, b2: DocumentBoundary) -> bool:
        """Check if two boundaries represent the same document"""
        # Same type hint is a strong indicator
        if b1.document_type_hint == b2.document_type_hint and b1.document_type_hint != DocumentType.OTHER:
            return True
        
        # Check for significant overlap
        overlap_start = max(b1.start_page, b2.start_page)
        overlap_end = min(b1.end_page, b2.end_page)
        overlap_pages = max(0, overlap_end - overlap_start + 1)
        
        # If more than 50% overlap, likely same document
        b1_pages = b1.end_page - b1.start_page + 1
        b2_pages = b2.end_page - b2.start_page + 1
        
        if overlap_pages > 0.5 * min(b1_pages, b2_pages):
            return True
        
        return False
    
    def _merge_boundaries(self, b1: DocumentBoundary, b2: DocumentBoundary) -> DocumentBoundary:
        """Merge two boundaries representing the same document"""
        return DocumentBoundary(
            start_page=min(b1.start_page, b2.start_page),
            end_page=max(b1.end_page, b2.end_page),
            confidence=max(b1.confidence, b2.confidence),
            document_type_hint=b1.document_type_hint if b1.confidence >= b2.confidence else b2.document_type_hint,
            boundary_indicators=list(set(b1.boundary_indicators + b2.boundary_indicators))
        )


class DiscoveryDocumentProcessor:
    """Processes segmented documents from discovery productions"""
    
    def __init__(self, case_name: str):
        """Initialize processor for specific case"""
        self.case_name = case_name
        self.pdf_extractor = PDFExtractor()
        self.chunker = DocumentChunker()
        self.context_generator = ContextGenerator()
        self.client = OpenAI(api_key=settings.openai.api_key)
        self.classification_model = settings.discovery.classification_model
    
    def process_segmented_document(self, 
                                 document_text: str,
                                 document_metadata: Dict[str, Any],
                                 boundary_info: DocumentBoundary) -> List[Any]:
        """
        Process a single document from the discovery production
        
        Args:
            document_text: Extracted text of the document
            document_metadata: Metadata about the document
            boundary_info: Boundary information for this document
            
        Returns:
            List of enhanced chunks with document-specific context
        """
        logger.info(f"Processing document: {document_metadata.get('document_type', 'Unknown')}")
        
        # Generate document-specific context
        doc_context = self.generate_document_context(
            document_text,
            document_metadata.get('document_type', 'OTHER'),
            boundary_info
        )
        
        # Add production info to metadata
        enhanced_metadata = {
            **document_metadata,
            'source_production_pages': f"{boundary_info.start_page + 1}-{boundary_info.end_page + 1}",
            'document_context': doc_context,
            'page_count': boundary_info.end_page - boundary_info.start_page + 1
        }
        
        # Chunk the document
        chunks = self.chunker.chunk_document(document_text, enhanced_metadata)
        
        # Enhance each chunk with document-specific context
        enhanced_chunks = []
        for chunk in chunks:
            enhanced_chunk = self.enhance_chunk_with_context(
                chunk,
                doc_context,
                enhanced_metadata
            )
            enhanced_chunks.append(enhanced_chunk)
        
        logger.info(f"Created {len(enhanced_chunks)} chunks for document")
        return enhanced_chunks
    
    def generate_document_context(self, document_text: str,
                                doc_type: str,
                                boundary_info: DocumentBoundary) -> str:
        """Generate context for this specific document, not entire production"""
        
        # Limit text for context generation
        preview_text = document_text[:3000] if len(document_text) > 3000 else document_text
        
        prompt = f"""Analyze this {doc_type} document and create a brief context summary.

Document Type: {doc_type}
Pages: {boundary_info.start_page + 1} to {boundary_info.end_page + 1}
Confidence: {boundary_info.confidence}

Create a 2-3 sentence context that will help understand individual chunks from this document.

Focus on:
1. What type of document this is and its purpose
2. Key parties, dates, or identifiers (case numbers, invoice numbers, etc.)
3. Main subject matter or transaction

Document preview:
{preview_text}

Provide ONLY the context summary, no additional explanation."""

        try:
            response = self.client.chat.completions.create(
                model=self.classification_model,
                messages=[
                    {"role": "system", "content": "You are a legal document analyst creating concise context summaries."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=150
            )
            
            context = response.choices[0].message.content.strip()
            logger.debug(f"Generated context: {context}")
            return context
            
        except Exception as e:
            logger.error(f"Error generating context: {str(e)}")
            return f"This is a {doc_type} document from pages {boundary_info.start_page + 1} to {boundary_info.end_page + 1}."
    
    def enhance_chunk_with_context(self, chunk: Any,
                                 doc_context: str,
                                 doc_metadata: Dict[str, Any]) -> Any:
        """Prepend document-specific context to chunk"""
        
        # Create enhanced content with document context
        enhanced_content = f"[Document Context: {doc_context}]\n\n{chunk.content}"
        
        # Update chunk metadata
        chunk.metadata.update({
            'has_document_context': True,
            'document_type': doc_metadata.get('document_type', 'OTHER'),
            'source_document_pages': doc_metadata.get('source_production_pages', ''),
            'document_bates_range': doc_metadata.get('bates_range', ''),
            'production_batch': doc_metadata.get('production_batch', ''),
            'producing_party': doc_metadata.get('producing_party', '')
        })
        
        # Store both original and enhanced content
        chunk.metadata['original_content_length'] = len(chunk.content)
        chunk.content = enhanced_content
        
        return chunk
    
    def classify_document(self, document_text: str, boundary: DocumentBoundary) -> str:
        """Classify the document type using LLM"""
        
        # Use hint if confidence is high
        if boundary.document_type_hint and boundary.confidence > 0.8:
            return boundary.document_type_hint.value
        
        # Otherwise classify with LLM
        preview = document_text[:2000]
        
        prompt = f"""Classify this legal document into one of the following categories:

Categories:
- DRIVER_QUALIFICATION_FILE
- EMPLOYMENT_APPLICATION
- BILL_OF_LADING
- MAINTENANCE_RECORD
- HOS_LOG (Hours of Service Log)
- TRIP_REPORT
- EMAIL_CORRESPONDENCE
- ACCIDENT_INVESTIGATION_REPORT
- DEPOSITION
- MEDICAL_RECORD
- POLICE_REPORT
- INVOICE
- CONTRACT
- OTHER

Document preview:
{preview}

Return ONLY the category name, nothing else."""

        try:
            response = self.client.chat.completions.create(
                model=self.classification_model,
                messages=[
                    {"role": "system", "content": "You are a legal document classifier."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=50
            )
            
            classification = response.choices[0].message.content.strip().upper()
            
            # Validate classification
            try:
                return DocumentType(classification.lower()).value
            except ValueError:
                return DocumentType.OTHER.value
                
        except Exception as e:
            logger.error(f"Error classifying document: {str(e)}")
            return DocumentType.OTHER.value
    
    def process_large_segmented_document(self, pdf_path: str,
                                       doc_metadata: Dict[str, Any],
                                       boundary: DocumentBoundary) -> List[Any]:
        """Process large documents in sections, each with its own context"""
        
        logger.info(f"Processing large document ({boundary.page_count} pages) in sections")
        
        all_chunks = []
        section_size = settings.discovery.window_size  # Use same size as boundary detection
        
        for section_start in range(boundary.start_page, boundary.end_page + 1, section_size):
            section_end = min(section_start + section_size - 1, boundary.end_page)
            
            # Extract section
            section_text = self._extract_pdf_pages(pdf_path, section_start, section_end)
            
            # Generate context for this section
            section_boundary = DocumentBoundary(
                start_page=section_start,
                end_page=section_end,
                confidence=boundary.confidence,
                document_type_hint=boundary.document_type_hint,
                boundary_indicators=boundary.boundary_indicators
            )
            
            section_context = self.generate_document_context(
                section_text,
                doc_metadata['document_type'],
                section_boundary
            )
            
            # Create section metadata
            section_metadata = {
                **doc_metadata,
                'section_number': (section_start - boundary.start_page) // section_size + 1,
                'total_sections': ((boundary.end_page - boundary.start_page) // section_size) + 1,
                'section_context': section_context
            }
            
            # Process section
            section_chunks = self.process_segmented_document(
                section_text,
                section_metadata,
                section_boundary
            )
            
            all_chunks.extend(section_chunks)
        
        return all_chunks
    
    def _extract_pdf_pages(self, pdf_path: str, start_page: int, end_page: int) -> str:
        """Extract text from specific page range"""
        with open(pdf_path, 'rb') as file:
            pdf_content = file.read()
            
        # Create a temporary PDF with just the pages we need
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_content))
        pdf_writer = PyPDF2.PdfWriter()
        
        for page_num in range(start_page, min(end_page + 1, len(pdf_reader.pages))):
            pdf_writer.add_page(pdf_reader.pages[page_num])
        
        # Extract text from temporary PDF
        temp_pdf = io.BytesIO()
        pdf_writer.write(temp_pdf)
        temp_pdf.seek(0)
        
        extracted = self.pdf_extractor.extract_text(temp_pdf.read(), f"pages_{start_page}-{end_page}.pdf")
        return extracted.text


class DiscoveryProductionProcessor:
    """Main processor for entire discovery productions"""
    
    def __init__(self, case_name: str):
        """Initialize production processor"""
        self.case_name = case_name
        self.boundary_detector = BoundaryDetector()
        self.document_processor = DiscoveryDocumentProcessor(case_name)
        self.pdf_extractor = PDFExtractor()
    
    def process_discovery_production(self, 
                                   pdf_path: str,
                                   production_metadata: Dict[str, Any]) -> DiscoveryProductionResult:
        """
        Process an entire discovery production PDF
        
        Args:
            pdf_path: Path to the production PDF
            production_metadata: Metadata about the production
            
        Returns:
            DiscoveryProductionResult with all processing information
        """
        result = DiscoveryProductionResult(
            case_name=self.case_name,
            production_batch=production_metadata.get('production_batch', 'Unknown'),
            source_pdf_path=pdf_path,
            total_pages=self._get_total_pages(pdf_path)
        )
        
        try:
            # Phase 1: Detect all boundaries
            logger.info("Phase 1: Detecting document boundaries")
            boundaries = self.boundary_detector.detect_all_boundaries(pdf_path)
            result.processing_windows = len(boundaries)
            
            # Identify low confidence boundaries
            result.low_confidence_boundaries = [
                b for b in boundaries if b.confidence < 0.7
            ]
            
            # Phase 2: Process each document
            logger.info(f"Phase 2: Processing {len(boundaries)} documents")
            
            for i, boundary in enumerate(boundaries):
                logger.info(f"Processing document {i+1}/{len(boundaries)}")
                
                try:
                    # Create segment
                    segment = DiscoverySegment(
                        start_page=boundary.start_page,
                        end_page=boundary.end_page,
                        document_type=DocumentType.OTHER,  # Will be classified
                        confidence_score=boundary.confidence,
                        boundary_indicators=boundary.boundary_indicators
                    )
                    
                    # Extract document text
                    if segment.needs_large_document_handling:
                        segment.processing_strategy = LargeDocumentProcessingStrategy.CHUNKED
                        # Process large document in sections
                        self._process_large_document(pdf_path, segment, production_metadata)
                    else:
                        # Process normal document
                        self._process_standard_document(pdf_path, segment, production_metadata)
                    
                    segment.extraction_successful = True
                    result.segments_found.append(segment)
                    
                except Exception as e:
                    logger.error(f"Error processing document at pages {boundary.start_page}-{boundary.end_page}: {str(e)}")
                    result.errors.append(f"Document {i+1}: {str(e)}")
                    segment.extraction_successful = False
                    result.segments_found.append(segment)
            
            # Calculate final metrics
            result.processing_completed = datetime.now()
            result.calculate_metrics()
            
            logger.info(f"Processing complete: {len(result.segments_found)} documents found")
            
        except Exception as e:
            logger.error(f"Fatal error processing production: {str(e)}")
            result.errors.append(f"Fatal: {str(e)}")
        
        return result
    
    def _get_total_pages(self, pdf_path: str) -> int:
        """Get total page count from PDF"""
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            return len(pdf_reader.pages)
    
    def _process_standard_document(self, pdf_path: str, 
                                 segment: DiscoverySegment,
                                 production_metadata: Dict[str, Any]) -> None:
        """Process a standard-sized document"""
        
        # Extract document text
        doc_text = self.document_processor._extract_pdf_pages(
            pdf_path, 
            segment.start_page, 
            segment.end_page
        )
        
        # Classify document
        segment.document_type = DocumentType(
            self.document_processor.classify_document(
                doc_text,
                DocumentBoundary(
                    start_page=segment.start_page,
                    end_page=segment.end_page,
                    confidence=segment.confidence_score,
                    document_type_hint=None,
                    boundary_indicators=segment.boundary_indicators
                )
            )
        )
        
        # Extract title if possible
        segment.title = self._extract_document_title(doc_text, segment.document_type)
        
        # Extract Bates range
        segment.bates_range = self._extract_bates_range(doc_text)
    
    def _process_large_document(self, pdf_path: str,
                              segment: DiscoverySegment,
                              production_metadata: Dict[str, Any]) -> None:
        """Process a large document that needs special handling"""
        
        # For now, just extract first section for classification
        preview_text = self.document_processor._extract_pdf_pages(
            pdf_path,
            segment.start_page,
            min(segment.start_page + 10, segment.end_page)
        )
        
        # Classify based on preview
        segment.document_type = DocumentType(
            self.document_processor.classify_document(
                preview_text,
                DocumentBoundary(
                    start_page=segment.start_page,
                    end_page=segment.end_page,
                    confidence=segment.confidence_score,
                    document_type_hint=None,
                    boundary_indicators=segment.boundary_indicators
                )
            )
        )
        
        # Extract title
        segment.title = self._extract_document_title(preview_text, segment.document_type)
        
        # Note that this is a multi-part document
        segment.is_complete = False
        segment.total_parts = (segment.page_count // 25) + (1 if segment.page_count % 25 else 0)
    
    def _extract_document_title(self, text: str, doc_type: DocumentType) -> Optional[str]:
        """Extract a title from document text"""
        # Look for common title patterns in first 500 characters
        preview = text[:500]
        
        # Common patterns
        patterns = [
            r'^([A-Z\s]{10,50})\n',  # All caps header
            r'^\s*(.{10,50})\n\s*\n',  # First line followed by blank
            r'RE:\s*(.+)\n',  # RE: Subject
            r'SUBJECT:\s*(.+)\n',  # SUBJECT: line
        ]
        
        for pattern in patterns:
            match = re.search(pattern, preview, re.MULTILINE)
            if match:
                title = match.group(1).strip()
                if len(title) > 10:  # Reasonable title length
                    return title
        
        # Default to document type
        return doc_type.value.replace('_', ' ').title()
    
    def _extract_bates_range(self, text: str) -> Optional[Dict[str, str]]:
        """Extract Bates number range from document"""
        # Look in first and last 500 characters
        search_text = text[:500] + "\n" + text[-500:] if len(text) > 1000 else text
        
        # Common Bates patterns
        patterns = [
            r'([A-Z]+[-_]?\d{4,})',  # DEF00001
            r'(\d{4,}[-_]?[A-Z]+)',  # 00001-DEF
        ]
        
        bates_numbers = []
        for pattern in patterns:
            matches = re.findall(pattern, search_text, re.IGNORECASE)
            bates_numbers.extend(matches)
        
        if bates_numbers:
            return {
                "start": bates_numbers[0],
                "end": bates_numbers[-1] if len(bates_numbers) > 1 else bates_numbers[0]
            }
        
        return None
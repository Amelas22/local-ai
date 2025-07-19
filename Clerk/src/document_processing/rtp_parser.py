"""
RTP (Request to Produce) Document Parser
Extracts individual requests from RTP documents with pattern-based identification
"""

import logging
import os
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any, Tuple, Generator

from .pdf_extractor import PDFExtractor

logger = logging.getLogger("clerk_api")


class RequestCategory(Enum):
    """Categories for different types of requests"""

    DOCUMENTS = "documents"
    COMMUNICATIONS = "communications"
    ELECTRONICALLY_STORED = "electronically_stored"
    TANGIBLE_THINGS = "tangible_things"
    OTHER = "other"


@dataclass
class RTPRequest:
    """Represents a single request from an RTP document."""

    request_number: str  # e.g., "1", "1a", "I", "RFP No. 12"
    request_text: str  # Full text of the request
    category: RequestCategory
    page_range: Tuple[int, int]  # (start_page, end_page)
    confidence_score: float = 1.0  # Confidence in extraction
    parent_request: Optional[str] = None  # For sub-requests like 1a, 1b
    cross_references: List[str] = field(default_factory=list)


class RTPParsingError(Exception):
    """Base exception for RTP parsing errors."""

    pass


class InvalidRTPFormatError(RTPParsingError):
    """Raised when document doesn't match RTP format."""

    pass


class PDFExtractionError(RTPParsingError):
    """Raised when PDF text extraction fails."""

    pass


class RequestExtractionError(RTPParsingError):
    """Raised when request extraction logic fails."""

    pass


class RTPParser:
    """Parses RTP documents and extracts individual requests"""

    # Performance settings
    MAX_MEMORY_MB = 1024  # 1GB memory limit
    STREAMING_THRESHOLD_MB = 50  # Switch to streaming for files > 50MB

    def __init__(self, case_name: str):
        """Initialize RTP parser with case context

        Args:
            case_name: Case name for isolation and logging context
        """
        self.case_name = case_name
        self.logger = logging.getLogger(f"clerk_api.{case_name}")
        self.pdf_extractor = PDFExtractor()

        # Performance tracking
        self._processing_start_time = None
        self._pages_processed = 0

        # Compile regex patterns for efficiency
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        """Compile regex patterns for request identification"""
        # Common RTP numbering patterns - order matters for priority
        self.request_patterns = [
            # "Request for Production No. X", "RFP No. X"
            (
                re.compile(
                    r"^(?:Request\s+for\s+Production|RFP)\s+No\.\s*(\d+)",
                    re.IGNORECASE | re.MULTILINE,
                ),
                "rfp",
            ),
            # "Request No. X"
            (
                re.compile(r"^Request\s+No\.\s*(\d+)", re.IGNORECASE | re.MULTILINE),
                "request",
            ),
            # "Interrogatory No. X"
            (
                re.compile(
                    r"^Interrogatory\s+No\.\s*(\d+)", re.IGNORECASE | re.MULTILINE
                ),
                "interrogatory",
            ),
            # "RFA No. X" (Request for Admission)
            (re.compile(r"^RFA\s+No\.\s*(\d+)", re.IGNORECASE | re.MULTILINE), "rfa"),
            # "REQUEST FOR PRODUCTION NUMBER X:" style
            (
                re.compile(
                    r"^REQUEST\s+FOR\s+PRODUCTION\s+NUMBER\s+(\d+)\s*:",
                    re.IGNORECASE | re.MULTILINE,
                ),
                "rfp",
            ),
            # Sub-requests with letters "1a.", "1(a)", "1.a", "1-a"
            (re.compile(r"^(\d+[a-z])\.\s+", re.IGNORECASE | re.MULTILINE), "sub"),
            (re.compile(r"^(\d+\([a-z]\))\s+", re.IGNORECASE | re.MULTILINE), "sub"),
            (re.compile(r"^(\d+\.[a-z])\s+", re.IGNORECASE | re.MULTILINE), "sub"),
            (re.compile(r"^(\d+[-][a-z])\s+", re.IGNORECASE | re.MULTILINE), "sub"),
            # Roman numerals "I.", "II.", "III."
            (re.compile(r"^([IVXLCDM]+)\.\s+", re.MULTILINE), "roman"),
            # Simple numbered list "1.", "2." at start of line (last priority)
            (re.compile(r"^(\d+)\.\s+", re.MULTILINE), "simple"),
        ]

        # Category keyword patterns
        self.category_patterns = {
            RequestCategory.DOCUMENTS: re.compile(
                r"\b(?:documents?|records?|files?|reports?|papers?|writings?)\b",
                re.IGNORECASE,
            ),
            RequestCategory.COMMUNICATIONS: re.compile(
                r"\b(?:emails?|correspondence|letters?|messages?|communications?|memos?|memorand[ua])\b",
                re.IGNORECASE,
            ),
            RequestCategory.ELECTRONICALLY_STORED: re.compile(
                r"\b(?:electronic|digital|database|ESI|computer|software|data)\b",
                re.IGNORECASE,
            ),
            RequestCategory.TANGIBLE_THINGS: re.compile(
                r"\b(?:physical|objects?|samples?|devices?|tangible|items?|things?)\b",
                re.IGNORECASE,
            ),
        }

        # Pattern to identify RTP document
        self.rtp_identifier_pattern = re.compile(
            r"(?:request\s+for\s+production|requests?\s+to\s+produce|RFP|production\s+requests?)",
            re.IGNORECASE,
        )

        # Pattern for merged requests (e.g., "Requests 1-5")
        self.merged_request_pattern = re.compile(
            r"(?:Requests?|RFP)\s+(\d+)\s*(?:through|to|-)\s*(\d+)", re.IGNORECASE
        )

        # Pattern for definitions section
        self.definition_pattern = re.compile(
            r"^(?:DEFINITIONS?|INSTRUCTIONS?|GENERAL\s+(?:DEFINITIONS?|INSTRUCTIONS?))",
            re.IGNORECASE | re.MULTILINE,
        )

    async def parse_rtp_document(self, pdf_path: str) -> List[RTPRequest]:
        """Parse RTP document and extract requests

        Args:
            pdf_path: Path to the RTP PDF document

        Returns:
            List of extracted RTP requests

        Raises:
            FileNotFoundError: If PDF file doesn't exist
            PDFExtractionError: If PDF text extraction fails
            InvalidRTPFormatError: If document is not an RTP
            RTPParsingError: For other parsing failures
        """
        try:
            # Validate file exists
            if not os.path.exists(pdf_path):
                raise FileNotFoundError(f"RTP document not found: {pdf_path}")

            self.logger.info(f"Parsing RTP for case: {self.case_name}")

            # Extract text from PDF
            with open(pdf_path, "rb") as f:
                pdf_content = f.read()

            extracted = self.pdf_extractor.extract_text(
                pdf_content, os.path.basename(pdf_path)
            )

            # Validate extraction
            if not self.pdf_extractor.validate_extraction(extracted):
                raise PDFExtractionError("Failed to extract sufficient text from PDF")

            # Validate it's an RTP document
            if not self._is_rtp_document(extracted.text):
                raise InvalidRTPFormatError("Document does not appear to be an RTP")

            # Detect format and preprocess
            format_type = self._detect_rtp_format(extracted.text)
            self.logger.info(f"Detected RTP format: {format_type}")

            processed_text = self._preprocess_text(extracted.text, format_type)

            # Extract requests
            requests = self._extract_requests(processed_text, extracted.page_count)

            if not requests:
                raise RTPParsingError("No requests found in document")

            self.logger.info(
                f"Successfully extracted {len(requests)} requests from RTP"
            )
            return requests

        except RTPParsingError:
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            # Wrap unexpected errors
            self.logger.error(f"Unexpected error parsing RTP: {e}")
            raise RTPParsingError(f"Failed to parse RTP document: {e}")

    def _is_rtp_document(self, text: str) -> bool:
        """Check if document appears to be an RTP

        Args:
            text: Extracted document text

        Returns:
            True if document appears to be RTP format
        """
        # Look for RTP identifiers in first 2000 characters
        preview = text[:2000]
        return bool(self.rtp_identifier_pattern.search(preview))

    def _detect_rtp_format(self, text: str) -> str:
        """Detect the format/structure of the RTP document

        Args:
            text: Document text

        Returns:
            Format identifier
        """
        # Check for various format indicators
        formats = {
            "standard": r"REQUEST\s+FOR\s+PRODUCTION\s+NO\.\s*\d+",
            "definition_first": r"^(?:DEFINITIONS?|INSTRUCTIONS?)\s*\n",
            "incorporated": r"(?:hereby\s+incorporates?|subject\s+to)",
            "subparts": r"\d+\([a-z]\)",
            "federal": r"(?:FEDERAL|FRCP|Fed\.\s*R\.\s*Civ\.\s*P\.)",
            "state": r"(?:STATE|Florida|Texas|California|New York)",
        }

        detected_formats = []
        preview = text[:5000]  # Check first 5000 chars

        for format_name, pattern in formats.items():
            if re.search(pattern, preview, re.IGNORECASE):
                detected_formats.append(format_name)

        # Return primary format
        if "federal" in detected_formats:
            return "federal"
        elif "state" in detected_formats:
            return "state"
        elif "definition_first" in detected_formats:
            return "definition_first"
        elif "subparts" in detected_formats:
            return "complex"
        else:
            return "standard"

    def _preprocess_text(self, text: str, format_type: str) -> str:
        """Preprocess text based on detected format

        Args:
            text: Raw document text
            format_type: Detected format type

        Returns:
            Preprocessed text
        """
        # Normalize line endings
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # Format-specific preprocessing
        if format_type == "definition_first":
            # Already handled in _remove_definition_sections
            pass
        elif format_type == "federal":
            # Federal format often has specific headers
            text = re.sub(
                r"^\s*UNITED STATES DISTRICT COURT.*?\n", "", text, flags=re.MULTILINE
            )
        elif format_type == "incorporated":
            # Handle incorporated instructions
            text = self._extract_incorporated_sections(text)

        # Normalize request numbering for consistency
        text = self._normalize_numbering(text)

        return text

    def _extract_incorporated_sections(self, text: str) -> str:
        """Extract and process incorporated instructions/definitions

        Args:
            text: Document text

        Returns:
            Text with incorporated sections processed
        """
        # Pattern for incorporated sections
        incorp_pattern = re.compile(
            r"(?:hereby\s+incorporates?\s+by\s+reference|subject\s+to\s+the\s+following)[^.]*\.",
            re.IGNORECASE,
        )

        # Mark incorporated sections
        for match in incorp_pattern.finditer(text):
            start = match.start()
            end = match.end()
            # Add marker for reference
            marker = f"\n[INCORPORATED SECTION: {match.group(0)[:50]}...]\n"
            text = text[:start] + marker + text[end:]

        return text

    def _normalize_numbering(self, text: str) -> str:
        """Normalize various numbering formats for consistency

        Args:
            text: Document text

        Returns:
            Text with normalized numbering
        """
        # Normalize "REQUEST FOR PRODUCTION NUMBER X:" to "RFP No. X"
        text = re.sub(
            r"REQUEST\s+FOR\s+PRODUCTION\s+NUMBER\s+(\d+)\s*:",
            r"RFP No. \1:",
            text,
            flags=re.IGNORECASE,
        )

        # Normalize spacing around numbers
        text = re.sub(r"No\.\s*(\d+)", r"No. \1", text)

        return text

    def _extract_requests(self, text: str, total_pages: int) -> List[RTPRequest]:
        """Extract individual requests from document text

        Args:
            text: Full document text with page markers
            total_pages: Total number of pages in document

        Returns:
            List of extracted requests
        """
        requests = []

        # Skip definitions/instructions sections
        text = self._remove_definition_sections(text)

        # Find all request boundaries
        boundaries = self._find_request_boundaries(text)

        # Handle merged requests first
        boundaries = self._expand_merged_requests(boundaries, text)

        # Extract each request
        for i, (start_pos, request_num, page_num) in enumerate(boundaries):
            try:
                # Determine end position (start of next request or end of document)
                if i + 1 < len(boundaries):
                    end_pos = boundaries[i + 1][0]
                else:
                    end_pos = len(text)

                # Extract request text
                request_text = text[start_pos:end_pos].strip()

                # Clean up request text
                request_text = self._clean_request_text(request_text, request_num)

                # Skip if too short or not a valid request
                if len(request_text) < 20 or self._is_non_request_content(request_text):
                    continue

                # Determine page range
                end_page = self._find_page_number_at_position(
                    text, end_pos - 1, total_pages
                )
                page_range = (page_num, end_page)

                # Categorize request
                category = self._categorize_request(request_text)

                # Determine if this is a sub-request
                parent_request = self._find_parent_request(request_num)

                # Extract cross-references
                cross_refs = self._extract_cross_references(request_text)

                request = RTPRequest(
                    request_number=request_num,
                    request_text=request_text,
                    category=category,
                    page_range=page_range,
                    parent_request=parent_request,
                    cross_references=cross_refs,
                )

                requests.append(request)

            except Exception as e:
                self.logger.error(f"Failed to extract request {request_num}: {e}")
                continue

        return requests

    def _find_request_boundaries(self, text: str) -> List[Tuple[int, str, int]]:
        """Find positions where requests begin

        Args:
            text: Document text

        Returns:
            List of (position, request_number, page_number) tuples
        """
        boundaries = []
        seen_positions = set()

        for pattern, pattern_type in self.request_patterns:
            for match in pattern.finditer(text):
                pos = match.start()

                # Skip if we've already found a request at this position
                if pos in seen_positions:
                    continue

                # Extract request number from match groups
                request_num = match.group(1)

                if request_num:
                    # Find page number at this position
                    page_num = self._find_page_number_at_position(text, pos, 1)
                    boundaries.append((pos, request_num, page_num))
                    seen_positions.add(pos)

        # Sort by position
        boundaries.sort(key=lambda x: x[0])

        # Add fallback numbering for any missed requests
        boundaries = self._add_fallback_numbering(boundaries, text)

        return boundaries

    def _find_page_number_at_position(
        self, text: str, position: int, default: int
    ) -> int:
        """Find page number at given text position

        Args:
            text: Document text with page markers
            position: Character position
            default: Default page number if not found

        Returns:
            Page number (1-indexed)
        """
        # Look for page markers before this position
        page_pattern = re.compile(r"\[Page (\d+)\]")

        # Find all page markers before position
        matches = list(page_pattern.finditer(text[:position]))

        if matches:
            # Get the last page marker before position
            last_match = matches[-1]
            return int(last_match.group(1))

        return default

    def _categorize_request(self, request_text: str) -> RequestCategory:
        """Categorize request based on keywords with priority rules

        Args:
            request_text: Text of the request

        Returns:
            Request category
        """
        # Count keyword matches for each category
        category_scores = {}

        for category, pattern in self.category_patterns.items():
            matches = pattern.findall(request_text)
            if matches:
                # Weight by match count and position (earlier = higher weight)
                score = 0
                for i, match in enumerate(matches):
                    # Give more weight to matches appearing earlier in the request
                    position_weight = 1.0 / (i + 1)
                    score += position_weight
                category_scores[category] = score

        # Apply priority rules for ambiguous cases
        if category_scores:
            # If both DOCUMENTS and ELECTRONICALLY_STORED have scores
            if (
                RequestCategory.DOCUMENTS in category_scores
                and RequestCategory.ELECTRONICALLY_STORED in category_scores
            ):
                # Check for specific electronic indicators
                if re.search(
                    r"\b(?:email|database|electronic\s+format|ESI)\b",
                    request_text,
                    re.IGNORECASE,
                ):
                    return RequestCategory.ELECTRONICALLY_STORED
                else:
                    return RequestCategory.DOCUMENTS

            # If COMMUNICATIONS scores exist, prioritize it for email/message requests
            if RequestCategory.COMMUNICATIONS in category_scores:
                if re.search(
                    r"\b(?:email|text\s+message|instant\s+message)\b",
                    request_text,
                    re.IGNORECASE,
                ):
                    return RequestCategory.COMMUNICATIONS

            # Return category with highest score
            return max(category_scores, key=category_scores.get)

        # Default categorization based on common patterns
        if re.search(
            r"\b(?:all|any\s+and\s+all|each\s+and\s+every)\s+documents?\b",
            request_text,
            re.IGNORECASE,
        ):
            return RequestCategory.DOCUMENTS

        return RequestCategory.OTHER

    def categorize_request(self, request_text: str) -> RequestCategory:
        """Public method to categorize a request

        Args:
            request_text: Text of the request

        Returns:
            Request category
        """
        return self._categorize_request(request_text)

    def _find_parent_request(self, request_num: str) -> Optional[str]:
        """Determine if this is a sub-request

        Args:
            request_num: Request number

        Returns:
            Parent request number if this is a sub-request
        """
        # Check for sub-request patterns like "1a", "1(a)", etc.
        sub_patterns = [
            re.compile(r"^(\d+)[a-z]$", re.IGNORECASE),
            re.compile(r"^(\d+)\([a-z]\)$", re.IGNORECASE),
            re.compile(r"^(\d+)\.[a-z]$", re.IGNORECASE),
            re.compile(r"^(\d+)-[a-z]$", re.IGNORECASE),
        ]

        for pattern in sub_patterns:
            match = pattern.match(request_num)
            if match:
                return match.group(1)

        return None

    def _extract_cross_references(self, request_text: str) -> List[str]:
        """Extract references to other requests

        Args:
            request_text: Text of the request

        Returns:
            List of referenced request numbers
        """
        cross_refs = []

        # Patterns for cross-references
        ref_patterns = [
            re.compile(
                r"(?:see|refer\s+to|pursuant\s+to)\s+(?:Request|RFP)\s+(?:No\.\s*)?(\d+)",
                re.IGNORECASE,
            ),
            re.compile(
                r"(?:requests?|RFP)\s+(\d+)(?:\s*(?:through|to|-)\s*(\d+))?",
                re.IGNORECASE,
            ),
        ]

        for pattern in ref_patterns:
            for match in pattern.finditer(request_text):
                if match.group(1):
                    cross_refs.append(match.group(1))
                # Handle ranges like "Requests 1-5"
                if len(match.groups()) > 1 and match.group(2):
                    start = int(match.group(1))
                    end = int(match.group(2))
                    cross_refs.extend(str(i) for i in range(start, end + 1))

        # Remove duplicates and current request
        return list(set(cross_refs))

    def extract_request_number(self, text: str) -> str:
        """Extract request number from text

        Args:
            text: Text potentially containing request number

        Returns:
            Extracted request number or generated fallback
        """
        for pattern, pattern_type in self.request_patterns:
            match = pattern.search(text)
            if match:
                return match.group(1)

        # Fallback: generate sequential number
        return "Unknown"

    def _add_fallback_numbering(
        self, boundaries: List[Tuple[int, str, int]], text: str
    ) -> List[Tuple[int, str, int]]:
        """Add fallback numbering for requests without clear numbers

        Args:
            boundaries: Current list of boundaries
            text: Document text

        Returns:
            Updated boundaries with fallback numbers
        """
        # Look for potential request boundaries that weren't caught
        # This could be expanded based on specific document patterns

        # For now, return as-is since we have comprehensive patterns
        return boundaries

    def _remove_definition_sections(self, text: str) -> str:
        """Remove definition/instruction sections that aren't requests

        Args:
            text: Document text

        Returns:
            Text with definitions sections marked
        """
        # Find definition sections
        definition_matches = list(self.definition_pattern.finditer(text))

        if not definition_matches:
            return text

        # Process matches in reverse order to maintain positions
        for match in reversed(definition_matches):
            start = match.start()
            # Find end of definition section (next request or section header)
            end = self._find_end_of_section(text, start)
            # Calculate placeholder length to maintain some content
            section_length = end - start
            placeholder = "[DEFINITION SECTION REMOVED]" + "\n" * min(
                5, section_length // 50
            )
            text = text[:start] + placeholder + text[end:]

        return text

    def _find_end_of_section(self, text: str, start_pos: int) -> int:
        """Find end of a section (definition, instructions, etc.)

        Args:
            text: Document text
            start_pos: Start position of section

        Returns:
            End position of section
        """
        # Look for next section header or request
        section_end_pattern = re.compile(
            r"\n(?:REQUEST|RFP|INTERROGATORY|DEFINITIONS?|INSTRUCTIONS?)", re.IGNORECASE
        )

        match = section_end_pattern.search(text, start_pos + 1)
        if match:
            return match.start()

        # If no next section, return end of text
        return len(text)

    def _expand_merged_requests(
        self, boundaries: List[Tuple[int, str, int]], text: str
    ) -> List[Tuple[int, str, int]]:
        """Expand merged requests (e.g., "Requests 1-5") into individual requests

        Args:
            boundaries: Current boundaries
            text: Document text

        Returns:
            Expanded boundaries
        """
        # Look for merged request patterns in the text
        for match in self.merged_request_pattern.finditer(text):
            start_num = int(match.group(1))
            end_num = int(match.group(2))

            # Check if these individual requests are already found
            existing_nums = {b[1] for b in boundaries}

            # Add placeholders for missing requests in the range
            for num in range(start_num, end_num + 1):
                if str(num) not in existing_nums:
                    # Add a boundary for this merged request
                    pos = match.start()
                    page_num = self._find_page_number_at_position(text, pos, 1)
                    boundaries.append((pos, str(num), page_num))

        # Re-sort by position
        boundaries.sort(key=lambda x: x[0])
        return boundaries

    def _clean_request_text(self, text: str, request_num: str) -> str:
        """Clean up request text by removing the request number prefix

        Args:
            text: Raw request text
            request_num: Request number

        Returns:
            Cleaned request text
        """
        # Remove the request number from the beginning
        for pattern, _ in self.request_patterns:
            match = pattern.match(text)
            if match:
                # Remove the matched pattern
                text = text[match.end() :].strip()
                break

        # Remove page markers from within the text for cleaner display
        text = re.sub(r"\[Page \d+\]\s*", " ", text)

        # Normalize whitespace
        text = " ".join(text.split())

        return text

    def _is_non_request_content(self, text: str) -> bool:
        """Check if text is non-request content (definitions, instructions, etc.)

        Args:
            text: Text to check

        Returns:
            True if text is not a request
        """
        # Check for definition/instruction keywords at start
        non_request_patterns = [
            r"^(?:The\s+following|As\s+used|Unless\s+otherwise)",
            r"^(?:DEFINITIONS?|INSTRUCTIONS?|GENERAL)",
            r"^\[DEFINITION SECTION REMOVED\]",
        ]

        for pattern in non_request_patterns:
            if re.match(pattern, text, re.IGNORECASE):
                return True

        return False

    def parse_rtp_document_streaming(
        self, pdf_path: str
    ) -> Generator[RTPRequest, None, None]:
        """Parse RTP document with streaming for large files

        Args:
            pdf_path: Path to the RTP PDF document

        Yields:
            Individual RTP requests as they are extracted

        Raises:
            Same exceptions as parse_rtp_document
        """
        try:
            # Validate file exists
            if not os.path.exists(pdf_path):
                raise FileNotFoundError(f"RTP document not found: {pdf_path}")

            file_size_mb = os.path.getsize(pdf_path) / (1024 * 1024)
            self.logger.info(
                f"Parsing RTP (streaming) for case: {self.case_name}, size: {file_size_mb:.1f}MB"
            )

            self._processing_start_time = time.time()

            # Extract text from PDF
            with open(pdf_path, "rb") as f:
                pdf_content = f.read()

            extracted = self.pdf_extractor.extract_text(
                pdf_content, os.path.basename(pdf_path)
            )

            # Validate extraction
            if not self.pdf_extractor.validate_extraction(extracted):
                raise PDFExtractionError("Failed to extract sufficient text from PDF")

            # Validate it's an RTP document
            if not self._is_rtp_document(extracted.text):
                raise InvalidRTPFormatError("Document does not appear to be an RTP")

            # Detect format and preprocess
            format_type = self._detect_rtp_format(extracted.text)
            self.logger.info(f"Detected RTP format: {format_type}")

            processed_text = self._preprocess_text(extracted.text, format_type)

            # Extract requests with streaming
            yield from self._extract_requests_streaming(
                processed_text, extracted.page_count
            )

        except RTPParsingError:
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error parsing RTP: {e}")
            raise RTPParsingError(f"Failed to parse RTP document: {e}")

    def _extract_requests_streaming(
        self, text: str, total_pages: int
    ) -> Generator[RTPRequest, None, None]:
        """Extract requests with streaming/yielding for memory efficiency

        Args:
            text: Full document text with page markers
            total_pages: Total number of pages in document

        Yields:
            Individual RTP requests as they are found
        """
        # Skip definitions/instructions sections
        text = self._remove_definition_sections(text)

        # Find all request boundaries
        boundaries = self._find_request_boundaries(text)

        # Handle merged requests first
        boundaries = self._expand_merged_requests(boundaries, text)

        request_count = 0

        # Extract each request
        for i, (start_pos, request_num, page_num) in enumerate(boundaries):
            try:
                # Memory check every 10 requests
                if request_count % 10 == 0:
                    self._check_memory_usage()

                # Determine end position
                if i + 1 < len(boundaries):
                    end_pos = boundaries[i + 1][0]
                else:
                    end_pos = len(text)

                # Extract request text
                request_text = text[start_pos:end_pos].strip()

                # Clean up request text
                request_text = self._clean_request_text(request_text, request_num)

                # Skip if too short or not a valid request
                if len(request_text) < 20 or self._is_non_request_content(request_text):
                    continue

                # Determine page range
                end_page = self._find_page_number_at_position(
                    text, end_pos - 1, total_pages
                )
                page_range = (page_num, end_page)

                # Categorize request
                category = self._categorize_request(request_text)

                # Determine if this is a sub-request
                parent_request = self._find_parent_request(request_num)

                # Extract cross-references
                cross_refs = self._extract_cross_references(request_text)

                request = RTPRequest(
                    request_number=request_num,
                    request_text=request_text,
                    category=category,
                    page_range=page_range,
                    parent_request=parent_request,
                    cross_references=cross_refs,
                )

                request_count += 1
                self._pages_processed = page_range[1]

                yield request

            except Exception as e:
                self.logger.error(f"Failed to extract request {request_num}: {e}")
                continue

        # Log final stats
        elapsed = time.time() - self._processing_start_time
        self.logger.info(
            f"Extracted {request_count} requests in {elapsed:.1f}s ({request_count / elapsed:.1f} req/s)"
        )

    def _check_memory_usage(self) -> None:
        """Check memory usage and warn if approaching limit"""
        try:
            import psutil

            process = psutil.Process()
            memory_mb = process.memory_info().rss / (1024 * 1024)

            if memory_mb > self.MAX_MEMORY_MB * 0.8:  # 80% of limit
                self.logger.warning(f"High memory usage: {memory_mb:.1f}MB")

        except ImportError:
            # psutil not available, skip memory check
            pass

    def get_parsing_progress(self) -> Dict[str, Any]:
        """Get current parsing progress

        Returns:
            Progress information dictionary
        """
        if not self._processing_start_time:
            return {"status": "not_started"}

        elapsed = time.time() - self._processing_start_time

        return {
            "status": "processing",
            "pages_processed": self._pages_processed,
            "elapsed_seconds": elapsed,
            "pages_per_second": self._pages_processed / elapsed if elapsed > 0 else 0,
        }

    async def parse_with_websocket_updates(
        self, pdf_path: str, case_id: str
    ) -> List[RTPRequest]:
        """Parse RTP document with WebSocket progress updates

        Args:
            pdf_path: Path to the RTP PDF document
            case_id: Case ID for WebSocket events

        Returns:
            List of extracted RTP requests
        """
        from src.websocket.socket_server import sio

        try:
            # Emit start event
            await sio.emit(
                "discovery:rtp_parsing",
                {
                    "case_id": case_id,
                    "status": "started",
                    "pdf_path": os.path.basename(pdf_path),
                },
            )

            # Check file size for streaming decision
            file_size_mb = os.path.getsize(pdf_path) / (1024 * 1024)
            use_streaming = file_size_mb > self.STREAMING_THRESHOLD_MB

            requests = []

            if use_streaming:
                # Use streaming for large files
                for i, request in enumerate(
                    self.parse_rtp_document_streaming(pdf_path)
                ):
                    requests.append(request)

                    # Emit progress every 5 requests
                    if i % 5 == 0:
                        await sio.emit(
                            "discovery:rtp_parsing",
                            {
                                "case_id": case_id,
                                "status": "processing",
                                "progress": int(
                                    (i / 50) * 100
                                ),  # Estimate based on typical count
                                "requests_found": i + 1,
                                "current_page": self._pages_processed,
                            },
                        )
            else:
                # Use regular parsing for smaller files
                requests = await self.parse_rtp_document(pdf_path)

            # Categorize results
            category_counts = {}
            for req in requests:
                category_counts[req.category.value] = (
                    category_counts.get(req.category.value, 0) + 1
                )

            # Emit completion event
            await sio.emit(
                "discovery:rtp_parsing",
                {
                    "case_id": case_id,
                    "status": "completed",
                    "total_requests": len(requests),
                    "categories": category_counts,
                },
            )

            return requests

        except Exception as e:
            # Emit error event
            await sio.emit(
                "discovery:rtp_parsing",
                {
                    "case_id": case_id,
                    "status": "error",
                    "error": str(e),
                    "details": str(type(e).__name__),
                },
            )
            raise

    def validate_for_pipeline(self, pdf_path: str) -> Dict[str, Any]:
        """Validate PDF is suitable for RTP parsing

        Args:
            pdf_path: Path to PDF file

        Returns:
            Validation result dictionary
        """
        result = {"valid": True, "errors": [], "warnings": [], "file_size_mb": 0}

        try:
            # Check file exists
            if not os.path.exists(pdf_path):
                result["valid"] = False
                result["errors"].append(f"File not found: {pdf_path}")
                return result

            # Check file size
            file_size = os.path.getsize(pdf_path)
            result["file_size_mb"] = file_size / (1024 * 1024)

            if result["file_size_mb"] > 500:  # 500MB limit
                result["warnings"].append(
                    f"Large file ({result['file_size_mb']:.1f}MB) may take time to process"
                )

            # Quick extraction test
            with open(pdf_path, "rb") as f:
                pdf_content = f.read(1024 * 1024)  # Read first 1MB

            # Basic PDF validation
            if not pdf_content.startswith(b"%PDF"):
                result["valid"] = False
                result["errors"].append("File does not appear to be a valid PDF")

        except Exception as e:
            result["valid"] = False
            result["errors"].append(f"Validation error: {str(e)}")

        return result

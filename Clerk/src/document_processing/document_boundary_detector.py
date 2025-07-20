"""
Advanced Document Boundary Detection Module

This module implements sophisticated boundary detection for concatenated PDFs
using multiple techniques:
1. Text-based analysis (headers, footers, page patterns)
2. Visual analysis (layout changes, whitespace patterns)
3. Metadata analysis (font changes, style changes)
4. AI-powered classification using sliding window approach
"""

import logging
import re
from typing import List, Dict, Optional
from dataclasses import dataclass
import numpy as np
from collections import Counter
import hashlib

try:
    import fitz  # PyMuPDF for better PDF analysis

    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False
    # Fallback to pdfplumber
    import pdfplumber

logger = logging.getLogger(__name__)


@dataclass
class PageFeatures:
    """Features extracted from a PDF page for boundary detection"""

    page_num: int
    text: str
    fonts: List[str]
    font_sizes: List[float]
    has_header: bool
    has_footer: bool
    has_page_number: bool
    text_density: float  # Percentage of page with text
    avg_font_size: float
    dominant_font: str
    has_letterhead: bool
    has_signature_block: bool
    has_bates_number: bool
    bates_number: Optional[str]
    structural_hash: str  # Hash of page structure


@dataclass
class DocumentBoundary:
    """Represents a detected document boundary"""

    start_page: int
    end_page: int
    confidence: float
    document_type_hint: Optional[str]
    title: Optional[str]
    indicators: List[str]
    bates_range: Optional[Dict[str, str]]


class DocumentBoundaryDetector:
    """Advanced document boundary detection for concatenated PDFs"""

    def __init__(self):
        self.logger = logger

        # Common document headers/markers
        self.document_markers = [
            # Legal document types
            r"^DEPOSITION OF",
            r"^AFFIDAVIT OF",
            r"^DECLARATION OF",
            r"^EXPERT REPORT",
            r"^BILL OF LADING",
            r"^INVOICE\s*#",
            r"^CONTRACT\s+(?:NO\.|NUMBER)",
            r"^POLICE REPORT",
            r"^MEDICAL RECORD",
            r"^EMPLOYMENT APPLICATION",
            r"^DRIVER QUALIFICATION FILE",
            r"^MAINTENANCE RECORD",
            r"^TRIP REPORT",
            r"^HOURS OF SERVICE",
            r"^ACCIDENT REPORT",
            # Form indicators
            r"^FORM\s+[A-Z0-9\-]+",
            r"^DOT FORM",
            r"^FMCSA",
            # Email/correspondence
            r"^From:\s*\S+@\S+",
            r"^Subject:",
            r"^Date:.*\d{4}",
            # General headers
            r"^EXHIBIT\s+[A-Z0-9]+",
            r"^ATTACHMENT\s+[A-Z0-9]+",
            r"^APPENDIX\s+[A-Z0-9]+",
        ]

        # Page numbering patterns
        self.page_patterns = [
            r"Page\s+\d+\s+of\s+\d+",
            r"\d+\s*/\s*\d+",
            r"[-–]\s*\d+\s*[-–]",
            r"^\d+$",  # Just a number
        ]

        # Bates patterns
        self.bates_patterns = [
            r"([A-Z]{2,4}[-_]?\d{4,})",  # DEF00001, PLF_00001
            r"(\d{4,}[-_]?[A-Z]{2,4})",  # 00001-DEF
            r"([A-Z]{2,4}\s+\d{4,})",  # DEF 00001
        ]

    def detect_boundaries(
        self, pdf_path: str, confidence_threshold: float = 0.7
    ) -> List[DocumentBoundary]:
        """
        Detect document boundaries in a concatenated PDF

        Args:
            pdf_path: Path to the PDF file
            confidence_threshold: Minimum confidence for boundary detection

        Returns:
            List of detected document boundaries
        """
        try:
            # Extract features from all pages
            page_features = self._extract_all_page_features(pdf_path)

            # Detect boundaries using multiple strategies
            boundaries = []

            # Strategy 1: Hard boundaries (new documents starting)
            hard_boundaries = self._detect_hard_boundaries(page_features)
            boundaries.extend(hard_boundaries)

            # Strategy 2: Soft boundaries (layout/style changes)
            soft_boundaries = self._detect_soft_boundaries(page_features)
            boundaries.extend(soft_boundaries)

            # Strategy 3: Page numbering resets
            numbering_boundaries = self._detect_page_numbering_resets(page_features)
            boundaries.extend(numbering_boundaries)

            # Merge and reconcile boundaries
            final_boundaries = self._reconcile_boundaries(boundaries)

            # Filter by confidence
            final_boundaries = [
                b for b in final_boundaries if b.confidence >= confidence_threshold
            ]

            # Ensure complete coverage
            final_boundaries = self._ensure_complete_coverage(
                final_boundaries, len(page_features)
            )

            self.logger.info(
                f"Detected {len(final_boundaries)} document boundaries in {pdf_path}"
            )
            return final_boundaries

        except Exception as e:
            self.logger.error(f"Error detecting boundaries in {pdf_path}: {e}")
            raise

    def _extract_all_page_features(self, pdf_path: str) -> List[PageFeatures]:
        """Extract features from all pages in the PDF"""
        features = []

        try:
            if HAS_PYMUPDF:
                pdf_document = fitz.open(pdf_path)

                for page_num in range(len(pdf_document)):
                    page = pdf_document[page_num]

                    # Extract text
                    text = page.get_text()

                    # Extract text with formatting info
                    blocks = page.get_text("dict")

                    # Extract fonts and sizes
                    fonts = []
                    font_sizes = []

                    for block in blocks.get("blocks", []):
                        if block.get("type") == 0:  # Text block
                            for line in block.get("lines", []):
                                for span in line.get("spans", []):
                                    fonts.append(span.get("font", ""))
                                    font_sizes.append(span.get("size", 0))

                    # Analyze page features
                    page_feature = PageFeatures(
                        page_num=page_num,
                        text=text,
                        fonts=fonts,
                        font_sizes=font_sizes,
                        has_header=self._has_header(text),
                        has_footer=self._has_footer(text),
                        has_page_number=self._has_page_number(text),
                        text_density=self._calculate_text_density_fitz(page),
                        avg_font_size=np.mean(font_sizes) if font_sizes else 0,
                        dominant_font=Counter(fonts).most_common(1)[0][0]
                        if fonts
                        else "",
                        has_letterhead=self._has_letterhead(text, page_num),
                        has_signature_block=self._has_signature_block(text),
                        has_bates_number=bool(self._extract_bates_number(text)),
                        bates_number=self._extract_bates_number(text),
                        structural_hash=self._calculate_structural_hash(blocks),
                    )

                    features.append(page_feature)

                pdf_document.close()
            else:
                # Fallback to pdfplumber
                with pdfplumber.open(pdf_path) as pdf:
                    for page_num, page in enumerate(pdf.pages):
                        # Extract text
                        text = page.extract_text() or ""

                        # Extract font info (limited in pdfplumber)
                        fonts = []
                        font_sizes = []

                        # Get character-level data if available
                        chars = page.chars if hasattr(page, "chars") else []
                        for char in chars:
                            if "fontname" in char:
                                fonts.append(char["fontname"])
                            if "size" in char:
                                font_sizes.append(char["size"])

                        # If no font data, use defaults
                        if not fonts:
                            fonts = ["Unknown"]
                            font_sizes = [12]

                        # Analyze page features
                        page_feature = PageFeatures(
                            page_num=page_num,
                            text=text,
                            fonts=fonts,
                            font_sizes=font_sizes,
                            has_header=self._has_header(text),
                            has_footer=self._has_footer(text),
                            has_page_number=self._has_page_number(text),
                            text_density=self._calculate_text_density_pdfplumber(page),
                            avg_font_size=np.mean(font_sizes) if font_sizes else 12,
                            dominant_font=Counter(fonts).most_common(1)[0][0]
                            if fonts
                            else "Unknown",
                            has_letterhead=self._has_letterhead(text, page_num),
                            has_signature_block=self._has_signature_block(text),
                            has_bates_number=bool(self._extract_bates_number(text)),
                            bates_number=self._extract_bates_number(text),
                            structural_hash=self._calculate_structural_hash_pdfplumber(
                                page
                            ),
                        )

                        features.append(page_feature)

        except Exception as e:
            self.logger.error(f"Error extracting page features: {e}")
            raise

        return features

    def _detect_hard_boundaries(
        self, features: List[PageFeatures]
    ) -> List[DocumentBoundary]:
        """Detect hard boundaries where new documents clearly start"""
        boundaries = []

        for i, feature in enumerate(features):
            confidence = 0.0
            indicators = []
            doc_type = None

            # Check for document markers
            first_lines = feature.text[:1000]
            for marker in self.document_markers:
                if re.search(marker, first_lines, re.MULTILINE | re.IGNORECASE):
                    confidence += 0.4
                    indicators.append(f"Document marker: {marker}")
                    doc_type = self._infer_document_type(marker)
                    break

            # Check for letterhead on non-first pages
            if i > 0 and feature.has_letterhead:
                confidence += 0.3
                indicators.append("Letterhead detected")

            # Check for email headers
            if self._is_email_start(feature.text):
                confidence += 0.5
                indicators.append("Email headers detected")
                doc_type = "EMAIL_CORRESPONDENCE"

            # Check for form start
            if self._is_form_start(feature.text):
                confidence += 0.4
                indicators.append("Form start detected")

            # Check for significant font change
            if i > 0:
                prev_feature = features[i - 1]
                if feature.dominant_font != prev_feature.dominant_font:
                    confidence += 0.2
                    indicators.append("Font change detected")

            # Check for Bates number sequence break
            if i > 0 and feature.has_bates_number and features[i - 1].has_bates_number:
                if not self._is_sequential_bates(
                    features[i - 1].bates_number, feature.bates_number
                ):
                    confidence += 0.3
                    indicators.append("Bates number sequence break")

            if confidence > 0.5:
                # Find end of this document
                end_page = self._find_document_end(features, i)

                boundaries.append(
                    DocumentBoundary(
                        start_page=i,
                        end_page=end_page,
                        confidence=min(confidence, 1.0),
                        document_type_hint=doc_type,
                        title=self._extract_title(feature.text),
                        indicators=indicators,
                        bates_range=self._get_bates_range(features[i : end_page + 1]),
                    )
                )

        return boundaries

    def _detect_soft_boundaries(
        self, features: List[PageFeatures]
    ) -> List[DocumentBoundary]:
        """Detect soft boundaries based on layout and style changes"""
        boundaries = []

        for i in range(1, len(features)):
            confidence = 0.0
            indicators = []

            curr = features[i]
            prev = features[i - 1]

            # Significant text density change
            density_change = abs(curr.text_density - prev.text_density)
            if density_change > 0.3:
                confidence += 0.2
                indicators.append(f"Text density change: {density_change:.2f}")

            # Font size change
            if curr.avg_font_size > 0 and prev.avg_font_size > 0:
                size_ratio = curr.avg_font_size / prev.avg_font_size
                if size_ratio > 1.5 or size_ratio < 0.67:
                    confidence += 0.2
                    indicators.append(f"Font size change: {size_ratio:.2f}")

            # Structural change
            if curr.structural_hash != prev.structural_hash:
                confidence += 0.1
                indicators.append("Page structure changed")

            # Page numbering restart
            if prev.has_page_number and curr.has_page_number:
                if self._is_page_number_reset(prev.text, curr.text):
                    confidence += 0.4
                    indicators.append("Page numbering reset")

            if confidence > 0.3:
                boundaries.append(
                    DocumentBoundary(
                        start_page=i,
                        end_page=self._find_document_end(features, i),
                        confidence=confidence,
                        document_type_hint=None,
                        title=self._extract_title(curr.text),
                        indicators=indicators,
                        bates_range=None,
                    )
                )

        return boundaries

    def _detect_page_numbering_resets(
        self, features: List[PageFeatures]
    ) -> List[DocumentBoundary]:
        """Detect boundaries where page numbering resets"""
        boundaries = []

        for i in range(1, len(features)):
            if self._is_page_number_reset(features[i - 1].text, features[i].text):
                boundaries.append(
                    DocumentBoundary(
                        start_page=i,
                        end_page=self._find_document_end(features, i),
                        confidence=0.7,
                        document_type_hint=None,
                        title=self._extract_title(features[i].text),
                        indicators=["Page numbering reset to 1"],
                        bates_range=None,
                    )
                )

        return boundaries

    def _reconcile_boundaries(
        self, boundaries: List[DocumentBoundary]
    ) -> List[DocumentBoundary]:
        """Merge overlapping boundaries and resolve conflicts"""
        if not boundaries:
            return []

        # Sort by start page
        sorted_boundaries = sorted(boundaries, key=lambda b: b.start_page)

        reconciled = []
        current = sorted_boundaries[0]

        for next_boundary in sorted_boundaries[1:]:
            # Check for overlap
            if next_boundary.start_page <= current.end_page:
                # Merge if they represent the same document
                if self._should_merge_boundaries(current, next_boundary):
                    current = self._merge_boundaries(current, next_boundary)
                else:
                    # Keep the one with higher confidence
                    if next_boundary.confidence > current.confidence:
                        current = next_boundary
            else:
                reconciled.append(current)
                current = next_boundary

        reconciled.append(current)
        return reconciled

    def _ensure_complete_coverage(
        self, boundaries: List[DocumentBoundary], total_pages: int
    ) -> List[DocumentBoundary]:
        """Ensure all pages are covered by boundaries"""
        if not boundaries:
            # No boundaries detected - treat as single document
            return [
                DocumentBoundary(
                    start_page=0,
                    end_page=total_pages - 1,
                    confidence=0.5,
                    document_type_hint=None,
                    title="Complete Document",
                    indicators=["No clear boundaries detected"],
                    bates_range=None,
                )
            ]

        # Sort by start page
        boundaries = sorted(boundaries, key=lambda b: b.start_page)

        complete = []

        # Handle gap before first boundary
        if boundaries[0].start_page > 0:
            complete.append(
                DocumentBoundary(
                    start_page=0,
                    end_page=boundaries[0].start_page - 1,
                    confidence=0.5,
                    document_type_hint=None,
                    title="Document Fragment",
                    indicators=["Pages before first detected boundary"],
                    bates_range=None,
                )
            )

        # Add existing boundaries and fill gaps
        for i, boundary in enumerate(boundaries):
            complete.append(boundary)

            # Check for gap to next boundary
            if i < len(boundaries) - 1:
                next_boundary = boundaries[i + 1]
                if boundary.end_page + 1 < next_boundary.start_page:
                    complete.append(
                        DocumentBoundary(
                            start_page=boundary.end_page + 1,
                            end_page=next_boundary.start_page - 1,
                            confidence=0.5,
                            document_type_hint=None,
                            title="Document Fragment",
                            indicators=["Gap between detected boundaries"],
                            bates_range=None,
                        )
                    )

        # Handle gap after last boundary
        if boundaries[-1].end_page < total_pages - 1:
            complete.append(
                DocumentBoundary(
                    start_page=boundaries[-1].end_page + 1,
                    end_page=total_pages - 1,
                    confidence=0.5,
                    document_type_hint=None,
                    title="Document Fragment",
                    indicators=["Pages after last detected boundary"],
                    bates_range=None,
                )
            )

        return complete

    # Helper methods

    def _has_header(self, text: str) -> bool:
        """Check if page has a header"""
        lines = text.split("\n")
        if len(lines) < 3:
            return False

        # Check first few lines for header patterns
        header_text = "\n".join(lines[:5])
        return bool(re.search(r"^\s*\S+.*\s+Page\s+\d+", header_text, re.MULTILINE))

    def _has_footer(self, text: str) -> bool:
        """Check if page has a footer"""
        lines = text.split("\n")
        if len(lines) < 3:
            return False

        # Check last few lines for footer patterns
        footer_text = "\n".join(lines[-5:])
        return bool(
            re.search(
                r"Page\s+\d+|©|\d{4}\s+\w+|Confidential", footer_text, re.IGNORECASE
            )
        )

    def _has_page_number(self, text: str) -> bool:
        """Check if page has page numbering"""
        for pattern in self.page_patterns:
            if re.search(pattern, text, re.MULTILINE):
                return True
        return False

    def _calculate_text_density_fitz(self, page) -> float:
        """Calculate text density using PyMuPDF"""
        try:
            page_area = page.rect.width * page.rect.height
            text_area = 0

            for block in page.get_text("dict")["blocks"]:
                if block.get("type") == 0:  # Text block
                    bbox = block.get("bbox", [0, 0, 0, 0])
                    text_area += (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])

            return text_area / page_area if page_area > 0 else 0
        except:
            return 0

    def _calculate_text_density_pdfplumber(self, page) -> float:
        """Calculate text density using pdfplumber"""
        try:
            # Get page dimensions
            page_width = page.width
            page_height = page.height
            page_area = page_width * page_height

            # Get text blocks
            text_area = 0

            # Try to get text bounding boxes
            if hasattr(page, "chars") and page.chars:
                # Calculate area covered by text characters
                x_coords = [char["x0"] for char in page.chars] + [
                    char["x1"] for char in page.chars
                ]
                y_coords = [char["top"] for char in page.chars] + [
                    char["bottom"] for char in page.chars
                ]

                if x_coords and y_coords:
                    # Approximate text area as bounding box of all characters
                    text_width = max(x_coords) - min(x_coords)
                    text_height = max(y_coords) - min(y_coords)
                    text_area = text_width * text_height
            elif hasattr(page, "extract_words") and callable(page.extract_words):
                # Fallback to word extraction
                words = page.extract_words()
                if words:
                    x_coords = []
                    y_coords = []
                    for word in words:
                        x_coords.extend([word["x0"], word["x1"]])
                        y_coords.extend([word["top"], word["bottom"]])

                    if x_coords and y_coords:
                        text_width = max(x_coords) - min(x_coords)
                        text_height = max(y_coords) - min(y_coords)
                        text_area = text_width * text_height
            else:
                # Very rough approximation based on text length
                text = page.extract_text() or ""
                # Assume average character takes up ~20 square points
                text_area = len(text) * 20

            return min(text_area / page_area, 1.0) if page_area > 0 else 0
        except Exception as e:
            self.logger.debug(f"Error calculating text density with pdfplumber: {e}")
            return 0

    def _has_letterhead(self, text: str, page_num: int) -> bool:
        """Check if page has letterhead (typically on first page or new document)"""
        if page_num == 0:
            return False  # First page often has letterhead

        # Look for company names, addresses, phone numbers in first part of page
        first_part = text[:500]
        patterns = [
            r"\b(?:LLC|Inc\.|Corporation|Corp\.|Company|Co\.)\b",
            r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",  # Phone
            r"\b\d{5}(?:-\d{4})?\b",  # ZIP code
            r"\b(?:Street|St\.|Avenue|Ave\.|Road|Rd\.|Drive|Dr\.|Boulevard|Blvd\.)\b",
        ]

        matches = sum(
            1 for pattern in patterns if re.search(pattern, first_part, re.IGNORECASE)
        )
        return matches >= 2

    def _has_signature_block(self, text: str) -> bool:
        """Check if page has signature block"""
        patterns = [
            r"_+\s*\n\s*(?:Signature|Name|Date)",
            r"(?:Sincerely|Respectfully|Best regards),?\s*\n",
            r"^\s*(?:Signed|Executed|Dated):\s*",
        ]

        text_lower = text.lower()
        return any(
            re.search(pattern, text_lower, re.MULTILINE | re.IGNORECASE)
            for pattern in patterns
        )

    def _extract_bates_number(self, text: str) -> Optional[str]:
        """Extract Bates number from page"""
        for pattern in self.bates_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        return None

    def _calculate_structural_hash(self, blocks: Dict) -> str:
        """Calculate hash of page structure for comparison"""
        structure = []
        for block in blocks.get("blocks", []):
            if block.get("type") == 0:  # Text block
                # Include position and size info
                bbox = block.get("bbox", [0, 0, 0, 0])
                structure.append(
                    f"{int(bbox[0])}:{int(bbox[1])}:{int(bbox[2] - bbox[0])}:{int(bbox[3] - bbox[1])}"
                )

        structure_str = "|".join(sorted(structure))
        return hashlib.md5(structure_str.encode()).hexdigest()[:8]

    def _calculate_structural_hash_pdfplumber(self, page) -> str:
        """Calculate structural hash using pdfplumber"""
        structure = []

        try:
            # Try to get text blocks or words
            if hasattr(page, "extract_words") and callable(page.extract_words):
                words = page.extract_words()
                # Group words by approximate line position
                lines = {}
                for word in words:
                    line_y = round(word["top"] / 10) * 10  # Round to nearest 10 points
                    if line_y not in lines:
                        lines[line_y] = []
                    lines[line_y].append(word)

                # Create structure based on line positions and widths
                for y_pos in sorted(lines.keys()):
                    line_words = lines[y_pos]
                    if line_words:
                        min_x = min(w["x0"] for w in line_words)
                        max_x = max(w["x1"] for w in line_words)
                        avg_height = sum(
                            w["bottom"] - w["top"] for w in line_words
                        ) / len(line_words)
                        structure.append(
                            f"{int(min_x)}:{int(y_pos)}:{int(max_x - min_x)}:{int(avg_height)}"
                        )

            elif hasattr(page, "chars") and page.chars:
                # Fallback to character-based structure
                # Group characters by line
                lines = {}
                for char in page.chars:
                    line_y = round(char["top"] / 10) * 10
                    if line_y not in lines:
                        lines[line_y] = []
                    lines[line_y].append(char)

                for y_pos in sorted(lines.keys())[:20]:  # Limit to first 20 lines
                    line_chars = lines[y_pos]
                    if line_chars:
                        min_x = min(c["x0"] for c in line_chars)
                        max_x = max(c["x1"] for c in line_chars)
                        avg_height = sum(
                            c["bottom"] - c["top"] for c in line_chars
                        ) / len(line_chars)
                        structure.append(
                            f"{int(min_x)}:{int(y_pos)}:{int(max_x - min_x)}:{int(avg_height)}"
                        )

            else:
                # Very basic structure based on text content
                text = page.extract_text() or ""
                lines = text.split("\n")[:20]  # First 20 lines
                for i, line in enumerate(lines):
                    if line.strip():
                        # Create pseudo-structure based on line length and position
                        structure.append(f"0:{i * 20}:{len(line) * 10}:12")

            if not structure:
                # Default structure if nothing else works
                structure.append(f"0:0:{int(page.width)}:{int(page.height)}")

            structure_str = "|".join(sorted(structure))
            return hashlib.md5(structure_str.encode()).hexdigest()[:8]

        except Exception as e:
            self.logger.debug(f"Error calculating structural hash with pdfplumber: {e}")
            # Return a default hash based on page dimensions
            return hashlib.md5(f"{page.width}x{page.height}".encode()).hexdigest()[:8]

    def _is_email_start(self, text: str) -> bool:
        """Check if page starts an email"""
        email_patterns = [
            r"^From:\s*\S+@\S+",
            r"^To:\s*\S+@\S+",
            r"^Subject:\s*.+",
            r"^Date:\s*.+\d{4}",
        ]

        first_lines = text[:500]
        matches = sum(
            1
            for pattern in email_patterns
            if re.search(pattern, first_lines, re.MULTILINE)
        )
        return matches >= 2

    def _is_form_start(self, text: str) -> bool:
        """Check if page starts a form"""
        form_patterns = [
            r"^\s*FORM\s+[A-Z0-9\-]+",
            r"^\s*(?:APPLICATION|QUESTIONNAIRE|SURVEY)\s+FORM",
            r"^\s*Please\s+(?:complete|fill)",
        ]

        first_lines = text[:300]
        return any(
            re.search(pattern, first_lines, re.MULTILINE | re.IGNORECASE)
            for pattern in form_patterns
        )

    def _infer_document_type(self, marker: str) -> Optional[str]:
        """Infer document type from marker pattern"""
        type_mappings = {
            r"DEPOSITION": "DEPOSITION",
            r"AFFIDAVIT": "AFFIDAVIT",
            r"EXPERT REPORT": "EXPERT_REPORT",
            r"BILL OF LADING": "BILL_OF_LADING",
            r"INVOICE": "INVOICE",
            r"CONTRACT": "CONTRACT",
            r"POLICE REPORT": "POLICE_REPORT",
            r"MEDICAL RECORD": "MEDICAL_RECORD",
            r"EMPLOYMENT APPLICATION": "EMPLOYMENT_APPLICATION",
            r"DRIVER QUALIFICATION": "DRIVER_QUALIFICATION_FILE",
            r"MAINTENANCE": "MAINTENANCE_RECORD",
            r"TRIP REPORT": "TRIP_REPORT",
            r"HOURS OF SERVICE": "HOS_LOG",
            r"ACCIDENT": "ACCIDENT_INVESTIGATION_REPORT",
        }

        marker_upper = marker.upper()
        for pattern, doc_type in type_mappings.items():
            if pattern in marker_upper:
                return doc_type

        return None

    def _is_sequential_bates(self, bates1: str, bates2: str) -> bool:
        """Check if two Bates numbers are sequential"""
        if not bates1 or not bates2:
            return False

        # Extract prefix and numeric parts
        match1 = re.match(r"([A-Z]+)[-_]?(\d+)", bates1)
        match2 = re.match(r"([A-Z]+)[-_]?(\d+)", bates2)

        if match1 and match2:
            prefix1, num1 = match1.groups()
            prefix2, num2 = match2.groups()

            # Check if prefixes match and numbers are sequential
            if prefix1 == prefix2:
                try:
                    return int(num2) == int(num1) + 1
                except:
                    return False

        # Try alternate formats
        match1 = re.match(r"(\d+)[-_]?([A-Z]+)", bates1)
        match2 = re.match(r"(\d+)[-_]?([A-Z]+)", bates2)

        if match1 and match2:
            num1, suffix1 = match1.groups()
            num2, suffix2 = match2.groups()

            # Check if suffixes match and numbers are sequential
            if suffix1 == suffix2:
                try:
                    return int(num2) == int(num1) + 1
                except:
                    return False

        return False

    def _find_document_end(self, features: List[PageFeatures], start_idx: int) -> int:
        """Find where a document ends"""
        # Look for signature blocks, form ends, or next document start
        for i in range(start_idx + 1, len(features)):
            # Check if this is a new document start
            if self._is_document_start(features[i]):
                return i - 1

            # Check for signature block (often at document end)
            if features[i].has_signature_block:
                # Check if next page is a new document
                if i + 1 < len(features) and self._is_document_start(features[i + 1]):
                    return i

        # Default to end of PDF
        return len(features) - 1

    def _is_document_start(self, feature: PageFeatures) -> bool:
        """Quick check if a page is likely a document start"""
        # Check for document markers
        for marker in self.document_markers[:10]:  # Check most common markers
            if re.search(marker, feature.text[:500], re.MULTILINE | re.IGNORECASE):
                return True

        return feature.has_letterhead or self._is_email_start(feature.text)

    def _extract_title(self, text: str) -> Optional[str]:
        """Extract document title from text"""
        lines = text.split("\n")

        # Look for title patterns in first few lines
        for i, line in enumerate(lines[:10]):
            line = line.strip()

            # Skip empty lines
            if not line:
                continue

            # Check if line looks like a title
            if len(line) > 10 and len(line) < 100:
                # All caps title
                if line.isupper() and len(line.split()) > 1:
                    return line.title()

                # Line with document type keywords
                for marker in self.document_markers:
                    if re.search(marker, line, re.IGNORECASE):
                        return line

                # First substantial line
                if i < 5 and len(line) > 20:
                    return line

        return None

    def _get_bates_range(
        self, features: List[PageFeatures]
    ) -> Optional[Dict[str, str]]:
        """Get Bates range for a document"""
        bates_numbers = []

        for feature in features:
            if feature.bates_number:
                bates_numbers.append(feature.bates_number)

        if bates_numbers:
            return {"start": bates_numbers[0], "end": bates_numbers[-1]}

        return None

    def _is_page_number_reset(self, prev_text: str, curr_text: str) -> bool:
        """Check if page numbering resets between pages"""
        # Extract page numbers
        prev_num = self._extract_page_number(prev_text)
        curr_num = self._extract_page_number(curr_text)

        # Check if current page is "1" or "Page 1" after a higher number
        if prev_num and curr_num:
            return prev_num > 1 and curr_num == 1

        return False

    def _extract_page_number(self, text: str) -> Optional[int]:
        """Extract page number from text"""
        # Try various page number patterns
        patterns = [
            r"Page\s+(\d+)\s+of",
            r"Page\s+(\d+)",
            r"(\d+)\s*/\s*\d+",
            r"[-–]\s*(\d+)\s*[-–]",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    return int(match.group(1))
                except:
                    continue

        return None

    def _should_merge_boundaries(
        self, b1: DocumentBoundary, b2: DocumentBoundary
    ) -> bool:
        """Determine if two boundaries should be merged"""
        # Similar confidence levels
        if abs(b1.confidence - b2.confidence) < 0.2:
            # Same document type hint
            if (
                b1.document_type_hint == b2.document_type_hint
                and b1.document_type_hint is not None
            ):
                return True

            # Overlapping indicators
            common_indicators = set(b1.indicators) & set(b2.indicators)
            if len(common_indicators) >= 2:
                return True

        return False

    def _merge_boundaries(
        self, b1: DocumentBoundary, b2: DocumentBoundary
    ) -> DocumentBoundary:
        """Merge two boundaries"""
        return DocumentBoundary(
            start_page=min(b1.start_page, b2.start_page),
            end_page=max(b1.end_page, b2.end_page),
            confidence=max(b1.confidence, b2.confidence),
            document_type_hint=b1.document_type_hint or b2.document_type_hint,
            title=b1.title or b2.title,
            indicators=list(set(b1.indicators + b2.indicators)),
            bates_range=b1.bates_range or b2.bates_range,
        )

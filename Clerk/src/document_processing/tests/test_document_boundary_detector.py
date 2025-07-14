"""
Tests for the Document Boundary Detector module
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock

# Try to import fitz, but don't fail if it's not available
try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False

from src.document_processing.document_boundary_detector import (
    DocumentBoundaryDetector,
    DocumentBoundary,
    PageFeatures
)


class TestDocumentBoundaryDetector:
    """Test the document boundary detection functionality"""
    
    @pytest.fixture
    def detector(self):
        """Create a boundary detector instance"""
        return DocumentBoundaryDetector()
    
    @pytest.fixture
    def mock_pdf_with_boundaries(self):
        """Create a mock PDF with clear document boundaries"""
        # Mock fitz document
        mock_doc = MagicMock()
        
        # Page 0: Deposition cover page
        page0 = MagicMock()
        page0.get_text.return_value = """DEPOSITION OF JOHN DOE
        
        Date: January 15, 2024
        Case No: 2024-CV-001
        
        Reporter: Jane Smith, CSR
        """
        page0.get_text.return_value = page0.get_text.return_value
        page0.rect.width = 612
        page0.rect.height = 792
        
        # Page 1: Deposition content
        page1 = MagicMock()
        page1.get_text.return_value = """Page 2
        
        Q: Please state your name for the record.
        A: John Doe.
        
        Q: What is your occupation?
        A: I'm a truck driver.
        """
        
        # Page 2: Email start (new document)
        page2 = MagicMock()
        page2.get_text.return_value = """From: manager@company.com
        To: driver@company.com
        Subject: Safety Protocol Update
        Date: December 1, 2023
        
        Dear Team,
        
        Please review the attached safety protocols.
        """
        
        # Page 3: Bill of Lading (new document)
        page3 = MagicMock()
        page3.get_text.return_value = """BILL OF LADING
        
        Shipper: ABC Company
        Consignee: XYZ Corporation
        
        BOL#: 123456
        Date: November 15, 2023
        """
        
        mock_doc.__len__.return_value = 4
        mock_doc.__getitem__.side_effect = lambda i: [page0, page1, page2, page3][i]
        
        # Mock text dict for each page
        for page in [page0, page1, page2, page3]:
            page.get_text.side_effect = lambda format=None: {
                None: page.get_text.return_value,
                "dict": {
                    "blocks": [
                        {
                            "type": 0,
                            "bbox": [0, 0, 100, 20],
                            "lines": [{
                                "spans": [{
                                    "font": "Arial",
                                    "size": 12,
                                    "text": "Sample"
                                }]
                            }]
                        }
                    ]
                }
            }.get(format, page.get_text.return_value)
        
        return mock_doc
    
    def test_extract_page_features(self, detector, mock_pdf_with_boundaries):
        """Test page feature extraction"""
        # Skip test if PyMuPDF not available
        if not HAS_PYMUPDF:
            pytest.skip("PyMuPDF not available")
            
        with patch('fitz.open', return_value=mock_pdf_with_boundaries):
            features = detector._extract_all_page_features("test.pdf")
            
            assert len(features) == 4
            
            # Check first page features
            assert features[0].page_num == 0
            assert "DEPOSITION OF JOHN DOE" in features[0].text
            assert features[0].has_letterhead is False  # First page
            
            # Check email page
            assert features[2].page_num == 2
            assert "From: manager@company.com" in features[2].text
    
    def test_detect_hard_boundaries(self, detector):
        """Test detection of hard document boundaries"""
        # Create test features
        features = [
            PageFeatures(
                page_num=0,
                text="DEPOSITION OF JOHN DOE\nDate: January 15, 2024",
                fonts=["Arial"],
                font_sizes=[12],
                has_header=False,
                has_footer=False,
                has_page_number=False,
                text_density=0.3,
                avg_font_size=12,
                dominant_font="Arial",
                has_letterhead=False,
                has_signature_block=False,
                has_bates_number=True,
                bates_number="DEF00001",
                structural_hash="hash1"
            ),
            PageFeatures(
                page_num=1,
                text="Page 2\nQ: Please state your name",
                fonts=["Arial"],
                font_sizes=[12],
                has_header=True,
                has_footer=True,
                has_page_number=True,
                text_density=0.5,
                avg_font_size=12,
                dominant_font="Arial",
                has_letterhead=False,
                has_signature_block=False,
                has_bates_number=True,
                bates_number="DEF00002",
                structural_hash="hash2"
            ),
            PageFeatures(
                page_num=2,
                text="From: manager@company.com\nTo: driver@company.com\nSubject: Safety Update",
                fonts=["Calibri"],
                font_sizes=[11],
                has_header=False,
                has_footer=False,
                has_page_number=False,
                text_density=0.2,
                avg_font_size=11,
                dominant_font="Calibri",
                has_letterhead=False,
                has_signature_block=False,
                has_bates_number=True,
                bates_number="DEF00010",  # Non-sequential
                structural_hash="hash3"
            )
        ]
        
        boundaries = detector._detect_hard_boundaries(features)
        
        assert len(boundaries) >= 1  # At least the email should be detected
        # Check that the email boundary was detected
        assert any(b.document_type_hint == "EMAIL_CORRESPONDENCE" for b in boundaries)
        # The deposition might not be detected as a hard boundary on page 0
    
    def test_detect_soft_boundaries(self, detector):
        """Test detection of soft boundaries based on layout changes"""
        features = [
            PageFeatures(
                page_num=0,
                text="Dense legal text " * 100,
                fonts=["TimesNewRoman"],
                font_sizes=[10],
                has_header=True,
                has_footer=True,
                has_page_number=True,
                text_density=0.8,
                avg_font_size=10,
                dominant_font="TimesNewRoman",
                has_letterhead=False,
                has_signature_block=False,
                has_bates_number=False,
                bates_number=None,
                structural_hash="hash1"
            ),
            PageFeatures(
                page_num=1,
                text="INVOICE\n\nInvoice #: 12345",
                fonts=["Arial"],
                font_sizes=[16],
                has_header=False,
                has_footer=False,
                has_page_number=False,
                text_density=0.2,  # Much lower density
                avg_font_size=16,  # Much larger font
                dominant_font="Arial",  # Different font
                has_letterhead=True,
                has_signature_block=False,
                has_bates_number=False,
                bates_number=None,
                structural_hash="hash2"  # Different structure
            )
        ]
        
        boundaries = detector._detect_soft_boundaries(features)
        
        assert len(boundaries) >= 1
        assert boundaries[0].start_page == 1
        assert "Text density change" in str(boundaries[0].indicators)
    
    def test_reconcile_boundaries(self, detector):
        """Test boundary reconciliation"""
        boundaries = [
            DocumentBoundary(
                start_page=0,
                end_page=5,
                confidence=0.8,
                document_type_hint="DEPOSITION",
                title="Deposition of John Doe",
                indicators=["Document marker: DEPOSITION"],
                bates_range=None
            ),
            DocumentBoundary(
                start_page=3,
                end_page=7,
                confidence=0.6,
                document_type_hint="DEPOSITION",
                title="Deposition continued",
                indicators=["Page structure changed"],
                bates_range=None
            ),
            DocumentBoundary(
                start_page=8,
                end_page=10,
                confidence=0.9,
                document_type_hint="EMAIL_CORRESPONDENCE",
                title="Email Re: Safety",
                indicators=["Email headers detected"],
                bates_range=None
            )
        ]
        
        reconciled = detector._reconcile_boundaries(boundaries)
        
        # Should merge overlapping DEPOSITION boundaries
        assert len(reconciled) == 2
        assert reconciled[0].end_page >= 5  # Should extend to at least original end
        assert reconciled[1].document_type_hint == "EMAIL_CORRESPONDENCE"
    
    def test_ensure_complete_coverage(self, detector):
        """Test that all pages are covered by boundaries"""
        boundaries = [
            DocumentBoundary(
                start_page=2,
                end_page=5,
                confidence=0.8,
                document_type_hint="DEPOSITION",
                title="Deposition",
                indicators=["Document marker"],
                bates_range=None
            ),
            DocumentBoundary(
                start_page=8,
                end_page=10,
                confidence=0.9,
                document_type_hint="EMAIL_CORRESPONDENCE",
                title="Email",
                indicators=["Email headers"],
                bates_range=None
            )
        ]
        
        complete = detector._ensure_complete_coverage(boundaries, total_pages=15)
        
        # Should have boundaries covering all pages
        assert len(complete) >= 4  # Original 2 + gaps
        
        # Check coverage
        all_pages = set()
        for boundary in complete:
            for page in range(boundary.start_page, boundary.end_page + 1):
                all_pages.add(page)
        
        assert len(all_pages) == 15  # All pages covered
        assert min(all_pages) == 0
        assert max(all_pages) == 14
    
    def test_extract_bates_number(self, detector):
        """Test Bates number extraction"""
        test_cases = [
            ("Some text DEF00001 more text", "DEF00001"),
            ("Beginning PLF-12345 end", "PLF-12345"),
            ("Multiple DEF00001 DEF00002 numbers", "DEF00001"),  # First one
            ("No Bates number here", None),
            ("Complex 00001-DEF format", "00001-DEF"),
        ]
        
        for text, expected in test_cases:
            result = detector._extract_bates_number(text)
            assert result == expected
    
    def test_is_email_start(self, detector):
        """Test email detection"""
        email_text = """From: sender@example.com
To: recipient@example.com
Subject: Important Update
Date: January 15, 2024

Dear Team,"""
        
        assert detector._is_email_start(email_text) is True
        
        non_email_text = """DEPOSITION OF JOHN DOE
        
Case No: 2024-CV-001"""
        
        assert detector._is_email_start(non_email_text) is False
    
    def test_is_sequential_bates(self, detector):
        """Test Bates number sequence checking"""
        assert detector._is_sequential_bates("DEF00001", "DEF00002") is True
        assert detector._is_sequential_bates("DEF00010", "DEF00011") is True
        assert detector._is_sequential_bates("DEF00001", "DEF00003") is False
        assert detector._is_sequential_bates("DEF00001", "PLF00002") is False
        assert detector._is_sequential_bates(None, "DEF00001") is False
    
    def test_infer_document_type(self, detector):
        """Test document type inference"""
        assert detector._infer_document_type("DEPOSITION OF") == "DEPOSITION"
        assert detector._infer_document_type("BILL OF LADING") == "BILL_OF_LADING"
        assert detector._infer_document_type("EXPERT REPORT") == "EXPERT_REPORT"
        assert detector._infer_document_type("UNKNOWN DOCUMENT") is None
    
    def test_extract_page_number(self, detector):
        """Test page number extraction"""
        assert detector._extract_page_number("Page 5 of 10") == 5
        assert detector._extract_page_number("Some text\n- 3 -\nMore text") == 3
        assert detector._extract_page_number("5/10") == 5
        assert detector._extract_page_number("No page number") is None
    
    @patch('fitz.open' if HAS_PYMUPDF else 'pdfplumber.open')
    def test_detect_boundaries_integration(self, mock_open, detector, mock_pdf_with_boundaries):
        """Test full boundary detection integration"""
        if not HAS_PYMUPDF:
            pytest.skip("PyMuPDF not available")
        mock_open.return_value = mock_pdf_with_boundaries
        
        boundaries = detector.detect_boundaries("test.pdf", confidence_threshold=0.5)
        
        assert len(boundaries) > 0
        
        # Check that boundaries are sorted by start page
        for i in range(1, len(boundaries)):
            assert boundaries[i].start_page >= boundaries[i-1].start_page
        
        # Check complete coverage
        all_pages = set()
        for boundary in boundaries:
            for page in range(boundary.start_page, boundary.end_page + 1):
                all_pages.add(page)
        
        assert len(all_pages) == 4  # Total pages in mock PDF
    
    def test_empty_pdf_handling(self, detector):
        """Test handling of empty PDF"""
        if not HAS_PYMUPDF:
            pytest.skip("PyMuPDF not available")
            
        mock_doc = MagicMock()
        mock_doc.__len__.return_value = 0
        
        with patch('fitz.open', return_value=mock_doc):
            boundaries = detector.detect_boundaries("empty.pdf")
            
            # Should return empty list for empty PDF
            assert boundaries == []
    
    def test_single_page_pdf(self, detector):
        """Test handling of single-page PDF"""
        if not HAS_PYMUPDF:
            pytest.skip("PyMuPDF not available")
            
        mock_doc = MagicMock()
        mock_doc.__len__.return_value = 1
        
        page = MagicMock()
        page.get_text.return_value = "Single page content"
        page.rect.width = 612
        page.rect.height = 792
        page.get_text.side_effect = lambda format=None: {
            None: "Single page content",
            "dict": {"blocks": []}
        }.get(format, "Single page content")
        
        mock_doc.__getitem__.return_value = page
        
        with patch('fitz.open', return_value=mock_doc):
            boundaries = detector.detect_boundaries("single.pdf")
            
            assert len(boundaries) == 1
            assert boundaries[0].start_page == 0
            assert boundaries[0].end_page == 0
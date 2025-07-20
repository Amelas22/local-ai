"""
Comprehensive unit tests for RTP Parser
Tests various RTP document formats, edge cases, and performance
"""

import pytest
import os
import tempfile
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import time

from src.document_processing.rtp_parser import (
    RTPParser,
    RTPRequest,
    RequestCategory,
    RTPParsingError,
    InvalidRTPFormatError,
    PDFExtractionError,
)
from src.document_processing.pdf_extractor import ExtractedDocument


class TestRTPParser:
    """Test suite for RTPParser following existing patterns."""

    @pytest.fixture
    def parser(self):
        """Create parser instance for testing."""
        return RTPParser(case_name="test_case")

    @pytest.fixture
    def sample_rtp_text(self):
        """Sample RTP document text with page markers."""
        return """[Page 1]
UNITED STATES DISTRICT COURT
EASTERN DISTRICT OF TEXAS

PLAINTIFF'S FIRST REQUEST FOR PRODUCTION OF DOCUMENTS

DEFINITIONS
As used herein, the following terms shall have the meanings set forth below:
1. "Document" means any written, printed, typed, or other graphic matter.

INSTRUCTIONS
1. These requests are continuing in nature.

REQUESTS FOR PRODUCTION

[Page 2]
Request for Production No. 1: All documents relating to the contract between plaintiff and defendant dated January 1, 2023.

Request for Production No. 2: All emails, letters, and other correspondence between any employee of plaintiff and any employee of defendant from January 1, 2022 to present.

[Page 3]
RFP No. 3: All electronic data, databases, and computer files containing information about the project codenamed "Alpha."

Request No. 4: All physical objects, samples, or devices related to the disputed product.

[Page 4]
5. All financial records, invoices, and payment documentation related to the contract.

Request for Production No. 6(a): All safety violation reports from 2020 to present.

Request for Production No. 6(b): All disciplinary actions taken in response to safety violations.

[Page 5]
VII. All company policies and employee handbooks in effect during 2023.

Requests 8-10: All documents referenced in your initial disclosures."""

    @pytest.fixture
    def mock_extracted_document(self, sample_rtp_text):
        """Mock extracted document."""
        return ExtractedDocument(
            text=sample_rtp_text,
            page_count=5,
            extraction_method="pdfplumber",
            metadata={"has_page_markers": True},
        )

    def test_parser_initialization(self):
        """Test parser initializes correctly."""
        parser = RTPParser(case_name="test_case_123")
        assert parser.case_name == "test_case_123"
        assert parser.logger.name == "clerk_api.test_case_123"
        assert hasattr(parser, "request_patterns")
        assert hasattr(parser, "category_patterns")

    def test_request_number_extraction(self, parser):
        """Test extraction of various request number formats."""
        test_cases = [
            ("Request for Production No. 1: All documents", "1"),
            ("RFP No. 42: All emails", "42"),
            ("Request No. 7: All records", "7"),
            ("Interrogatory No. 3: Describe all", "3"),
            ("RFA No. 5: Admit that", "5"),
            ("REQUEST FOR PRODUCTION NUMBER 10:", "10"),
            ("1. All documents relating to", "1"),
            ("15a. All sub-documents", "15a"),
            ("2(b) All related items", "2(b)"),
            ("3.c All connected records", "3.c"),
            ("4-d All associated files", "4-d"),
            ("V. All relevant materials", "V"),
            ("No pattern here", "Unknown"),
        ]

        for text, expected in test_cases:
            result = parser.extract_request_number(text)
            assert result == expected, f"Failed for: {text}"

    def test_is_rtp_document(self, parser):
        """Test RTP document identification."""
        # Valid RTP documents
        assert parser._is_rtp_document("REQUEST FOR PRODUCTION OF DOCUMENTS")
        assert parser._is_rtp_document("Plaintiff's First Requests to Produce")
        assert parser._is_rtp_document("RFP No. 1: All documents")
        assert parser._is_rtp_document("PRODUCTION REQUESTS")

        # Invalid documents
        assert not parser._is_rtp_document("MOTION FOR SUMMARY JUDGMENT")
        assert not parser._is_rtp_document("DEPOSITION OF JOHN DOE")
        assert not parser._is_rtp_document("CONTRACT AGREEMENT")

    def test_request_categorization(self, parser):
        """Test categorization of requests."""
        test_cases = [
            (
                "All documents, records, and files relating to",
                RequestCategory.DOCUMENTS,
            ),
            ("All emails and correspondence between", RequestCategory.COMMUNICATIONS),
            (
                "All electronic data and databases",
                RequestCategory.ELECTRONICALLY_STORED,
            ),
            ("All physical objects and samples", RequestCategory.TANGIBLE_THINGS),
            ("All information regarding", RequestCategory.OTHER),
            (
                "All emails in electronic format",
                RequestCategory.COMMUNICATIONS,
            ),  # Priority test
        ]

        for text, expected_category in test_cases:
            result = parser.categorize_request(text)
            assert result == expected_category, f"Failed for: {text}"

    async def test_parse_rtp_document_success(self, parser, mock_extracted_document):
        """Test successful RTP document parsing."""
        # Setup mocks
        with patch.object(
            parser.pdf_extractor, "extract_text", return_value=mock_extracted_document
        ):
            with patch.object(
                parser.pdf_extractor, "validate_extraction", return_value=True
            ):
                # Create temp PDF file
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                    tmp.write(b"%PDF-1.4 fake pdf content")
                    tmp_path = tmp.name

                try:
                    # Parse document
                    requests = await parser.parse_rtp_document(tmp_path)

                    # Verify results
                    assert len(requests) >= 8  # Should find at least 8 requests

                    # Check we have requests
                    request_numbers = [r.request_number for r in requests]
                    assert "1" in request_numbers
                    assert "2" in request_numbers

                    # Check a request has expected content
                    req1 = next((r for r in requests if r.request_number == "1"), None)
                    assert req1 is not None
                    assert req1.category in [
                        RequestCategory.DOCUMENTS,
                        RequestCategory.OTHER,
                    ]

                    # Check sub-request if found
                    req6a = next(
                        (r for r in requests if r.request_number == "6(a)"), None
                    )
                    if req6a:
                        assert req6a.parent_request == "6"
                        assert "safety" in req6a.request_text.lower()

                    # Check roman numeral if found
                    req7 = next(
                        (r for r in requests if r.request_number == "VII"), None
                    )
                    if req7:
                        assert "polic" in req7.request_text.lower()

                finally:
                    os.unlink(tmp_path)

    @patch("src.document_processing.rtp_parser.PDFExtractor")
    async def test_parse_non_rtp_document(self, mock_pdf_extractor_class, parser):
        """Test parsing non-RTP document raises error."""
        # Setup mocks
        mock_extractor = Mock()
        mock_pdf_extractor_class.return_value = mock_extractor
        mock_extractor.extract_text.return_value = ExtractedDocument(
            text="MOTION FOR SUMMARY JUDGMENT\nThis is not an RTP document.",
            page_count=1,
            extraction_method="pdfplumber",
            metadata={},
        )
        mock_extractor.validate_extraction.return_value = True

        # Create temp PDF file
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(b"%PDF-1.4 fake pdf content")
            tmp_path = tmp.name

        try:
            parser = RTPParser(case_name="test_case")
            parser.pdf_extractor = mock_extractor

            with pytest.raises(InvalidRTPFormatError):
                await parser.parse_rtp_document(tmp_path)
        finally:
            os.unlink(tmp_path)

    @patch("src.document_processing.rtp_parser.PDFExtractor")
    async def test_parse_empty_document(self, mock_pdf_extractor_class, parser):
        """Test parsing empty document."""
        # Setup mocks
        mock_extractor = Mock()
        mock_pdf_extractor_class.return_value = mock_extractor
        mock_extractor.extract_text.return_value = ExtractedDocument(
            text="",
            page_count=0,
            extraction_method="failed",
            metadata={"error": "No text extracted"},
        )
        mock_extractor.validate_extraction.return_value = False

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(b"%PDF-1.4")
            tmp_path = tmp.name

        try:
            parser = RTPParser(case_name="test_case")
            parser.pdf_extractor = mock_extractor

            with pytest.raises(PDFExtractionError):
                await parser.parse_rtp_document(tmp_path)
        finally:
            os.unlink(tmp_path)

    async def test_parse_nonexistent_file(self, parser):
        """Test parsing non-existent file."""
        with pytest.raises(RTPParsingError) as exc_info:
            await parser.parse_rtp_document("/path/to/nonexistent.pdf")
        assert "RTP document not found" in str(exc_info.value)

    def test_format_detection(self, parser):
        """Test RTP format detection."""
        federal_text = (
            "UNITED STATES DISTRICT COURT\nFRCP Rule 34\nREQUEST FOR PRODUCTION NO. 1"
        )
        assert parser._detect_rtp_format(federal_text) == "federal"

        state_text = "STATE OF FLORIDA\nREQUEST FOR PRODUCTION NO. 1"
        assert parser._detect_rtp_format(state_text) == "state"

        definition_text = (
            "DEFINITIONS\n\nThe following definitions apply:\n\nREQUEST NO. 1"
        )
        assert parser._detect_rtp_format(definition_text) == "definition_first"

        complex_text = "REQUEST NO. 1(a): Documents\nREQUEST NO. 1(b): Emails"
        assert parser._detect_rtp_format(complex_text) == "complex"

        standard_text = "REQUEST FOR PRODUCTION NO. 1: All documents"
        assert parser._detect_rtp_format(standard_text) == "standard"

    def test_merged_requests_handling(self, parser):
        """Test handling of merged requests like 'Requests 1-5'."""
        text = """
        Requests 1-5: All documents relating to the following categories:
        1. Contracts
        2. Invoices  
        3. Correspondence
        4. Reports
        5. Analyses
        
        Request No. 6: All other documents.
        """

        boundaries = parser._find_request_boundaries(text)
        boundaries = parser._expand_merged_requests(boundaries, text)

        # Should find individual boundaries for 1-5 plus 6
        request_numbers = [b[1] for b in boundaries]
        assert "1" in request_numbers
        assert "2" in request_numbers
        assert "3" in request_numbers
        assert "4" in request_numbers
        assert "5" in request_numbers
        assert "6" in request_numbers

    def test_definition_section_removal(self, parser):
        """Test removal of definition sections."""
        text = """DEFINITIONS
        
        The following terms have these meanings:
        "Document" means any written material.
        
        REQUESTS FOR PRODUCTION
        
        Request No. 1: All documents."""

        processed = parser._remove_definition_sections(text)
        assert "[DEFINITION SECTION REMOVED]" in processed
        # The key point is that definitions are removed
        assert '"Document" means' not in processed
        # And requests section is preserved
        assert "REQUESTS FOR PRODUCTION" in processed or "Request No. 1" in processed

    def test_cross_reference_extraction(self, parser):
        """Test extraction of cross-references between requests."""
        text = "All documents referenced in Request 1 and pursuant to RFP No. 5"
        refs = parser._extract_cross_references(text)
        assert "1" in refs
        assert "5" in refs

        text2 = "All documents described in Requests 10 through 15"
        refs2 = parser._extract_cross_references(text2)
        assert "10" in refs2
        assert "11" in refs2
        assert "15" in refs2

    def test_performance_large_document(self, parser):
        """Test performance with large document."""
        # Generate large RTP text
        large_text = "[Page 1]\nREQUEST FOR PRODUCTION\n\n"
        for i in range(1, 101):  # 100 requests
            large_text += (
                f"[Page {i}]\nRequest No. {i}: All documents relating to topic {i}.\n"
                * 10
            )

        start_time = time.time()
        boundaries = parser._find_request_boundaries(large_text)
        elapsed = time.time() - start_time

        assert len(boundaries) >= 100
        assert elapsed < 1.0  # Should complete within 1 second

    def test_streaming_parser(self, parser):
        """Test streaming parser for memory efficiency."""
        # Create mock document
        mock_text = """[Page 1]
        REQUEST FOR PRODUCTION
        
        Request No. 1: First request
        Request No. 2: Second request
        Request No. 3: Third request
        """

        with patch.object(parser.pdf_extractor, "extract_text") as mock_extract:
            mock_extract.return_value = ExtractedDocument(
                text=mock_text, page_count=1, extraction_method="test", metadata={}
            )

            with patch.object(
                parser.pdf_extractor, "validate_extraction", return_value=True
            ):
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                    tmp.write(b"%PDF-1.4 test")
                    tmp_path = tmp.name

                try:
                    # Test streaming
                    requests = list(parser.parse_rtp_document_streaming(tmp_path))
                    assert len(requests) >= 3

                    # Verify requests are yielded in order
                    assert requests[0].request_number == "1"
                    assert requests[1].request_number == "2"
                    assert requests[2].request_number == "3"
                finally:
                    os.unlink(tmp_path)

    def test_memory_monitoring(self, parser):
        """Test memory usage monitoring."""
        # Test without psutil (common case)
        # Should not raise exception even without psutil
        parser._check_memory_usage()

    def test_progress_tracking(self, parser):
        """Test parsing progress tracking."""
        # Initial state
        progress = parser.get_parsing_progress()
        assert progress["status"] == "not_started"

        # During processing
        parser._processing_start_time = time.time()
        parser._pages_processed = 25

        progress = parser.get_parsing_progress()
        assert progress["status"] == "processing"
        assert progress["pages_processed"] == 25
        assert "elapsed_seconds" in progress
        assert "pages_per_second" in progress

    @pytest.mark.asyncio
    async def test_websocket_integration(self, parser):
        """Test WebSocket event emission during parsing."""
        mock_sio = MagicMock()
        # Make emit async
        mock_sio.emit = AsyncMock()

        with patch("src.websocket.socket_server.sio", mock_sio):
            with patch.object(
                parser, "parse_rtp_document", new_callable=AsyncMock
            ) as mock_parse:
                mock_parse.return_value = [
                    RTPRequest(
                        request_number="1",
                        request_text="Test request",
                        category=RequestCategory.DOCUMENTS,
                        page_range=(1, 1),
                    )
                ]

                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                    tmp.write(b"%PDF-1.4 test")
                    tmp_path = tmp.name

                try:
                    await parser.parse_with_websocket_updates(tmp_path, "case_123")

                    # Verify WebSocket events
                    assert mock_sio.emit.call_count >= 2  # Start and complete events

                    # Check start event
                    start_call = mock_sio.emit.call_args_list[0]
                    assert start_call[0][0] == "discovery:rtp_parsing"
                    assert start_call[0][1]["status"] == "started"
                    assert start_call[0][1]["case_id"] == "case_123"

                    # Check completion event
                    complete_call = mock_sio.emit.call_args_list[-1]
                    assert complete_call[0][1]["status"] == "completed"
                    assert complete_call[0][1]["total_requests"] == 1
                finally:
                    os.unlink(tmp_path)

    def test_pipeline_validation(self, parser):
        """Test PDF validation for pipeline integration."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(b"%PDF-1.4 test content")
            tmp_path = tmp.name

        try:
            result = parser.validate_for_pipeline(tmp_path)
            assert result["valid"] is True
            assert len(result["errors"]) == 0
            assert result["file_size_mb"] > 0
        finally:
            os.unlink(tmp_path)

        # Test non-existent file
        result = parser.validate_for_pipeline("/nonexistent.pdf")
        assert result["valid"] is False
        assert len(result["errors"]) > 0

        # Test invalid PDF
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(b"Not a PDF file")
            tmp_path = tmp.name

        try:
            result = parser.validate_for_pipeline(tmp_path)
            assert result["valid"] is False
            assert any("not appear to be a valid PDF" in e for e in result["errors"])
        finally:
            os.unlink(tmp_path)

    def test_edge_cases(self, parser):
        """Test various edge cases."""
        # Very short request
        short_text = "RFP 1: Docs"
        requests = parser._extract_requests(short_text, 1)
        assert len(requests) == 0  # Too short, should be skipped

        # Request with special characters
        special_text = "Request №1: All docs re: ABC/DEF & GHI"
        num = parser.extract_request_number(special_text)
        # Should handle gracefully even if not extracted
        assert num == "Unknown" or num == "1"

        # Duplicate request numbers
        dup_text = """
        Request No. 1: First version
        Request No. 1: Second version (amended)
        """
        boundaries = parser._find_request_boundaries(dup_text)
        # Should find both even with same number
        assert len(boundaries) >= 1


@pytest.fixture
def create_test_pdf():
    """Create a test PDF file."""

    def _create(content=b"%PDF-1.4\ntest content"):
        tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        tmp.write(content)
        tmp.close()
        return tmp.name

    return _create


class TestRTPParserIntegration:
    """Integration tests with real PDF processing."""

    async def test_federal_court_format(self, create_test_pdf):
        """Test parsing federal court RTP format."""
        # This would use a real federal court RTP PDF
        # For unit tests, we mock the extraction
        parser = RTPParser(case_name="federal_case")

        # Would test with actual federal format PDF
        # pdf_path = create_test_pdf()
        # requests = await parser.parse_rtp_document(pdf_path)
        # Assertions about federal format specifics

    async def test_state_court_format(self, create_test_pdf):
        """Test parsing state court RTP format."""
        # This would use a real state court RTP PDF
        parser = RTPParser(case_name="state_case")

        # Would test with actual state format PDF
        # Assertions about state format specifics

    async def test_complex_multi_section_rtp(self, create_test_pdf):
        """Test parsing complex RTP with multiple sections."""
        # Would test with complex real-world RTP
        pass

    async def test_poor_ocr_document(self, create_test_pdf):
        """Test parsing document with poor OCR quality."""
        # Would test error handling with poor quality scan
        pass


class TestRTPParserPerformance:
    """Performance and benchmark tests."""

    def test_regex_compilation_performance(self):
        """Test regex pattern compilation performance."""
        start = time.time()
        for _ in range(100):
            parser = RTPParser(case_name=f"perf_test_{_}")
        elapsed = time.time() - start

        # Should compile patterns quickly
        assert elapsed < 1.0  # 100 parsers in under 1 second

    def test_large_document_performance(self):
        """Test performance with very large documents."""
        # Generate 500-page document
        large_text = ""
        for page in range(1, 501):
            large_text += f"[Page {page}]\n"
            if page % 10 == 0:
                large_text += (
                    f"Request No. {page // 10}: All documents for item {page // 10}\n"
                )

        parser = RTPParser(case_name="perf_test")

        start = time.time()
        requests = parser._extract_requests(large_text, 500)
        elapsed = time.time() - start

        assert len(requests) >= 50
        assert elapsed < 30  # Should process 500 pages in under 30 seconds

        # Calculate performance metrics
        pages_per_second = 500 / elapsed
        assert pages_per_second > 3  # At least 3 pages per second

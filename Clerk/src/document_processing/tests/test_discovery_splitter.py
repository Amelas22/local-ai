"""
Tests for discovery document splitter with AI-powered boundary detection
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from src.document_processing.discovery_splitter import (
    DiscoveryProductionProcessor,
    DiscoverySegment,
    DiscoveryProductionResult,
    DocumentBoundary
)
from src.models.unified_document_models import DocumentType


class TestDiscoveryProductionProcessor:
    """Tests for discovery production processor"""

    @pytest.fixture
    def processor(self):
        """Create processor instance"""
        return DiscoveryProductionProcessor(case_name="test_case")

    @pytest.fixture
    def sample_pdf_content(self):
        """Sample PDF content pages"""
        return [
            "MOTION FOR SUMMARY JUDGMENT\nPlaintiff hereby moves this Court...",
            "Page 2 of motion continuing arguments...",
            "CERTIFICATE OF SERVICE\nI hereby certify...",
            "DEPOSITION OF JOHN SMITH\nDate: January 15, 2024",
            "Q: Please state your name.\nA: John Smith",
            "Q: What is your occupation?\nA: Software engineer",
            "EXHIBIT A\nPurchase Agreement dated...",
            "Terms and conditions of agreement...",
            "Dear Counsel,\nThis letter confirms our discussion...",
            "Sincerely,\nAttorney Name"
        ]

    @pytest.fixture
    def mock_openai_client(self):
        """Mock OpenAI client for boundary detection"""
        mock_client = Mock()
        mock_completion = Mock()
        mock_completion.choices = [Mock(message=Mock(content=""))]
        mock_client.chat.completions.create = Mock(return_value=mock_completion)
        return mock_client

    @pytest.mark.asyncio
    async def test_process_discovery_production_basic(self, processor, sample_pdf_content):
        """Test basic discovery production processing"""
        # Arrange
        with patch('pdfplumber.open') as mock_pdf:
            # Mock PDF pages
            mock_pages = []
            for i, content in enumerate(sample_pdf_content):
                mock_page = Mock()
                mock_page.extract_text.return_value = content
                mock_page.page_number = i + 1
                mock_pages.append(mock_page)
            
            mock_pdf.return_value.__enter__.return_value.pages = mock_pages
            
            # Mock AI boundary detection
            with patch.object(processor, '_detect_boundaries_with_ai') as mock_detect:
                mock_detect.return_value = [
                    DocumentBoundary(
                        page_number=1,
                        confidence=0.95,
                        boundary_type="new_document",
                        document_type=DocumentType.MOTION,
                        title="Motion for Summary Judgment",
                        bates_range="PROD0001-PROD0003",
                        indicators=["MOTION FOR SUMMARY JUDGMENT"]
                    ),
                    DocumentBoundary(
                        page_number=4,
                        confidence=0.90,
                        boundary_type="new_document",
                        document_type=DocumentType.DEPOSITION,
                        title="Deposition of John Smith",
                        bates_range="PROD0004-PROD0006",
                        indicators=["DEPOSITION OF", "Q:", "A:"]
                    ),
                    DocumentBoundary(
                        page_number=7,
                        confidence=0.88,
                        boundary_type="new_document",
                        document_type=DocumentType.EXHIBIT,
                        title="Exhibit A - Purchase Agreement",
                        bates_range="PROD0007-PROD0008",
                        indicators=["EXHIBIT A"]
                    ),
                    DocumentBoundary(
                        page_number=9,
                        confidence=0.92,
                        boundary_type="new_document",
                        document_type=DocumentType.CORRESPONDENCE,
                        title="Letter to Counsel",
                        bates_range="PROD0009-PROD0010",
                        indicators=["Dear Counsel"]
                    )
                ]
            
            # Act
            result = processor.process_discovery_production(
                pdf_path="test.pdf",
                production_metadata={
                    "production_batch": "BATCH001",
                    "producing_party": "Defendant"
                }
            )
        
        # Assert
        assert isinstance(result, DiscoveryProductionResult)
        assert len(result.segments_found) == 4
        assert result.total_pages == 10
        assert result.average_confidence > 0.8
        
        # Verify segments
        motion_segment = result.segments_found[0]
        assert motion_segment.document_type == DocumentType.MOTION
        assert motion_segment.start_page == 1
        assert motion_segment.end_page == 3
        assert motion_segment.title == "Motion for Summary Judgment"
        
        deposition_segment = result.segments_found[1]
        assert deposition_segment.document_type == DocumentType.DEPOSITION
        assert deposition_segment.start_page == 4
        assert deposition_segment.end_page == 6

    @pytest.mark.asyncio
    async def test_ai_boundary_detection(self, processor, mock_openai_client):
        """Test AI-powered boundary detection"""
        # Arrange
        processor.client = mock_openai_client
        
        # Configure mock response
        mock_response = '''[
            {
                "page_number": 1,
                "confidence": 0.95,
                "boundary_type": "new_document",
                "document_type": "motion",
                "indicators": ["MOTION FOR SUMMARY JUDGMENT", "Plaintiff moves"],
                "title": "Motion for Summary Judgment",
                "bates_start": "PROD0001"
            },
            {
                "page_number": 5,
                "confidence": 0.88,
                "boundary_type": "new_document", 
                "document_type": "deposition",
                "indicators": ["DEPOSITION OF", "sworn testimony"],
                "title": "Deposition of Jane Doe",
                "bates_start": "PROD0005"
            }
        ]'''
        
        mock_openai_client.chat.completions.create.return_value.choices[0].message.content = mock_response
        
        # Act
        boundaries = processor._detect_boundaries_with_ai(
            window_pages=["Page 1 content", "Page 2 content", "Page 3 content"],
            start_page_num=1
        )
        
        # Assert
        assert len(boundaries) == 2
        assert boundaries[0].page_number == 1
        assert boundaries[0].document_type == DocumentType.MOTION
        assert boundaries[0].confidence == 0.95
        assert boundaries[1].page_number == 5
        assert boundaries[1].document_type == DocumentType.DEPOSITION

    def test_create_segments_from_boundaries(self, processor):
        """Test segment creation from boundaries"""
        # Arrange
        boundaries = [
            DocumentBoundary(
                page_number=1,
                confidence=0.95,
                boundary_type="new_document",
                document_type=DocumentType.MOTION,
                title="Test Motion",
                bates_range="PROD0001",
                indicators=["MOTION"]
            ),
            DocumentBoundary(
                page_number=5,
                confidence=0.90,
                boundary_type="new_document",
                document_type=DocumentType.DEPOSITION,
                title="Test Deposition",
                bates_range="PROD0005",
                indicators=["DEPOSITION"]
            ),
            DocumentBoundary(
                page_number=10,
                confidence=0.85,
                boundary_type="new_document",
                document_type=DocumentType.EXHIBIT,
                title="Test Exhibit",
                bates_range="PROD0010",
                indicators=["EXHIBIT"]
            )
        ]
        
        # Act
        segments = processor._create_segments_from_boundaries(
            boundaries=boundaries,
            total_pages=15,
            production_metadata={"batch": "TEST001"}
        )
        
        # Assert
        assert len(segments) == 3
        
        # First segment
        assert segments[0].start_page == 1
        assert segments[0].end_page == 4
        assert segments[0].document_type == DocumentType.MOTION
        assert segments[0].page_count == 4
        
        # Second segment
        assert segments[1].start_page == 5
        assert segments[1].end_page == 9
        assert segments[1].document_type == DocumentType.DEPOSITION
        
        # Third segment (should extend to end)
        assert segments[2].start_page == 10
        assert segments[2].end_page == 15
        assert segments[2].page_count == 6

    def test_extract_bates_range(self, processor):
        """Test Bates number range extraction"""
        # Test various Bates formats
        test_cases = [
            ("This document BATES001234 contains", "BATES001234"),
            ("Beginning Bates: DEF-0001", "DEF-0001"),
            ("PROD 2024-001 through PROD 2024-005", "PROD 2024-001"),
            ("Bates Nos. ABC123-ABC127", "ABC123"),
            ("No bates number here", None)
        ]
        
        for text, expected in test_cases:
            result = processor._extract_bates_range(text, text)
            if expected:
                assert result == expected
            else:
                assert result is None

    def test_sliding_window_processing(self, processor):
        """Test sliding window approach for large PDFs"""
        # Arrange
        large_pdf_pages = ["Page " + str(i) for i in range(1, 101)]  # 100 pages
        
        with patch('pdfplumber.open') as mock_pdf:
            mock_pages = []
            for i, content in enumerate(large_pdf_pages):
                mock_page = Mock()
                mock_page.extract_text.return_value = content
                mock_page.page_number = i + 1
                mock_pages.append(mock_page)
            
            mock_pdf.return_value.__enter__.return_value.pages = mock_pages
            
            # Track window calls
            window_calls = []
            
            def track_windows(window_pages, start_page):
                window_calls.append((len(window_pages), start_page))
                return []  # No boundaries for this test
            
            with patch.object(processor, '_detect_boundaries_with_ai', side_effect=track_windows):
                # Act
                result = processor.process_discovery_production(
                    pdf_path="large.pdf",
                    production_metadata={}
                )
                
                # Assert - Verify sliding window was used
                assert len(window_calls) > 1  # Multiple windows processed
                assert all(len(pages) <= processor.default_window_size for pages, _ in window_calls)

    @pytest.mark.asyncio
    async def test_error_handling(self, processor):
        """Test error handling in discovery processing"""
        # Test file not found
        with pytest.raises(Exception):
            processor.process_discovery_production(
                pdf_path="/nonexistent/file.pdf",
                production_metadata={}
            )
        
        # Test AI detection failure
        with patch('pdfplumber.open') as mock_pdf:
            mock_pdf.return_value.__enter__.return_value.pages = [Mock()]
            
            with patch.object(processor, '_detect_boundaries_with_ai', side_effect=Exception("AI error")):
                result = processor.process_discovery_production(
                    pdf_path="test.pdf",
                    production_metadata={}
                )
                
                # Should still return result with single segment
                assert len(result.segments_found) == 1
                assert result.segments_found[0].document_type == DocumentType.UNKNOWN

    def test_confidence_threshold_filtering(self, processor):
        """Test that low confidence boundaries are filtered"""
        # Arrange
        boundaries = [
            DocumentBoundary(
                page_number=1,
                confidence=0.95,
                boundary_type="new_document",
                document_type=DocumentType.MOTION,
                title="High Confidence",
                bates_range="PROD0001",
                indicators=[]
            ),
            DocumentBoundary(
                page_number=5,
                confidence=0.45,  # Below threshold
                boundary_type="new_document",
                document_type=DocumentType.UNKNOWN,
                title="Low Confidence",
                bates_range="PROD0005",
                indicators=[]
            ),
            DocumentBoundary(
                page_number=10,
                confidence=0.85,
                boundary_type="new_document",
                document_type=DocumentType.EXHIBIT,
                title="Good Confidence",
                bates_range="PROD0010",
                indicators=[]
            )
        ]
        
        # Act
        segments = processor._create_segments_from_boundaries(
            boundaries=boundaries,
            total_pages=15,
            production_metadata={}
        )
        
        # Assert - Low confidence boundary should be tracked but not create segment
        assert len(segments) == 2  # Only high confidence boundaries
        assert segments[0].start_page == 1
        assert segments[1].start_page == 10


class TestDiscoverySegment:
    """Tests for DiscoverySegment model"""
    
    def test_segment_creation(self):
        """Test creating a discovery segment"""
        segment = DiscoverySegment(
            start_page=1,
            end_page=5,
            document_type=DocumentType.MOTION,
            confidence_score=0.95,
            title="Test Motion",
            bates_range="PROD0001-PROD0005",
            indicators=["MOTION", "Summary Judgment"]
        )
        
        assert segment.page_count == 5
        assert segment.document_type == DocumentType.MOTION
        assert segment.confidence_score == 0.95
        assert len(segment.indicators) == 2

    def test_segment_validation(self):
        """Test segment validation"""
        # Invalid page range
        with pytest.raises(ValueError):
            DiscoverySegment(
                start_page=5,
                end_page=3,  # End before start
                document_type=DocumentType.UNKNOWN,
                confidence_score=0.5,
                indicators=[]
            )
        
        # Invalid confidence
        with pytest.raises(ValueError):
            DiscoverySegment(
                start_page=1,
                end_page=5,
                document_type=DocumentType.UNKNOWN,
                confidence_score=1.5,  # Over 1.0
                indicators=[]
            )
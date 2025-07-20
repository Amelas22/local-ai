"""
Tests for discovery processing models
"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from src.models.discovery_models import (
    FactSource,
    ExtractedFactWithSource,
    DiscoveryProcessingRequest,
    DiscoveryProcessingStatus,
    FactUpdateRequest,
    FactReviewStatus,
)
from src.models.fact_models import FactCategory


class TestFactSource:
    """Test FactSource model"""

    def test_fact_source_creation(self):
        """Test creating a fact source with all fields"""
        source = FactSource(
            doc_id="doc-123",
            doc_title="Medical Records",
            page=42,
            bbox=[100.0, 200.0, 400.0, 250.0],
            text_snippet="patient was treated for back pain",
            bates_number="DEF00042",
        )

        assert source.doc_id == "doc-123"
        assert source.page == 42
        assert len(source.bbox) == 4
        assert source.bates_number == "DEF00042"

    def test_fact_source_without_bates(self):
        """Test creating fact source without optional bates number"""
        source = FactSource(
            doc_id="doc-456",
            doc_title="Deposition Transcript",
            page=15,
            bbox=[0, 0, 100, 100],
            text_snippet="witness testified that",
        )

        assert source.bates_number is None


class TestExtractedFactWithSource:
    """Test ExtractedFactWithSource model"""

    def test_extracted_fact_creation(self):
        """Test creating an extracted fact with source"""
        source = FactSource(
            doc_id="doc-789",
            doc_title="Police Report",
            page=3,
            bbox=[50, 100, 200, 150],
            text_snippet="accident occurred at intersection",
        )

        fact = ExtractedFactWithSource(
            id="fact-123",
            case_name="Smith_v_Jones_2024",
            content="The accident occurred on January 15, 2024",
            category=FactCategory.TIMELINE,
            source_document="doc-789",
            page_references=[3],
            extraction_timestamp=datetime.now(),
            confidence_score=0.95,
            source=source,
        )

        assert fact.source.doc_id == "doc-789"
        assert fact.is_edited is False
        assert len(fact.edit_history) == 0
        assert fact.reviewed is False

    def test_fact_with_edit_history(self):
        """Test fact with edit history"""
        source = FactSource(
            doc_id="doc-001",
            doc_title="Medical Report",
            page=5,
            bbox=[0, 0, 100, 50],
            text_snippet="diagnosis",
        )

        fact = ExtractedFactWithSource(
            id="fact-456",
            case_name="Test_Case",
            content="Updated content",
            category=FactCategory.MEDICAL,
            source_document="doc-001",
            page_references=[5],
            extraction_timestamp=datetime.now(),
            confidence_score=0.85,
            source=source,
            is_edited=True,
        )

        assert fact.is_edited is True


class TestDiscoveryProcessingRequest:
    """Test DiscoveryProcessingRequest model"""

    def test_basic_request(self):
        """Test basic discovery processing request"""
        request = DiscoveryProcessingRequest(
            discovery_files=["file1.pdf", "file2.pdf"], enable_ocr=True
        )

        assert len(request.discovery_files) == 2
        assert request.box_folder_id is None
        assert request.enable_ocr is True
        assert request.confidence_threshold == 0.7

    def test_request_with_box_folder(self):
        """Test request with Box folder ID"""
        request = DiscoveryProcessingRequest(
            box_folder_id="123456789", rfp_file="rfp_document.pdf"
        )

        assert request.box_folder_id == "123456789"
        assert request.rfp_file == "rfp_document.pdf"
        assert len(request.discovery_files) == 0

    def test_confidence_threshold_validation(self):
        """Test confidence threshold validation"""
        # Valid threshold
        request = DiscoveryProcessingRequest(confidence_threshold=0.5)
        assert request.confidence_threshold == 0.5

        # Invalid threshold should raise error
        with pytest.raises(ValidationError):
            DiscoveryProcessingRequest(confidence_threshold=1.5)

        with pytest.raises(ValidationError):
            DiscoveryProcessingRequest(confidence_threshold=-0.1)

    def test_deficiency_analysis_fields(self):
        """Test new deficiency analysis fields"""
        request = DiscoveryProcessingRequest(
            rtp_document_id="doc-rtp-123", oc_response_document_id="doc-oc-456"
        )

        assert request.rtp_document_id == "doc-rtp-123"
        assert request.oc_response_document_id == "doc-oc-456"
        assert request.enable_deficiency_analysis is False  # Default value

    def test_deficiency_analysis_with_files(self):
        """Test deficiency analysis with both file types"""
        request = DiscoveryProcessingRequest(
            rtp_file="base64encodedcontent",
            oc_response_file="base64encodedcontent",
            rtp_document_id="doc-rtp-789",
            oc_response_document_id="doc-oc-012",
            enable_deficiency_analysis=True,
        )

        assert request.rtp_file is not None
        assert request.oc_response_file is not None
        assert request.rtp_document_id == "doc-rtp-789"
        assert request.oc_response_document_id == "doc-oc-012"
        assert request.enable_deficiency_analysis is True

    def test_optional_deficiency_fields(self):
        """Test that deficiency analysis fields are optional"""
        # Request without any deficiency fields should work
        request = DiscoveryProcessingRequest(discovery_files=["test.pdf"])

        assert request.rtp_document_id is None
        assert request.oc_response_document_id is None
        assert request.rtp_file is None
        assert request.oc_response_file is None
        assert request.enable_deficiency_analysis is False


class TestDiscoveryProcessingStatus:
    """Test DiscoveryProcessingStatus model"""

    def test_status_creation(self):
        """Test creating processing status"""
        status = DiscoveryProcessingStatus(
            case_id="case-123", case_name="Smith_v_Jones", total_documents=10
        )

        assert status.processing_id is not None
        assert status.case_id == "case-123"
        assert status.total_documents == 10
        assert status.processed_documents == 0
        assert status.status == "initializing"
        assert status.documents == {}

    def test_status_with_documents(self):
        """Test status with document tracking"""
        status = DiscoveryProcessingStatus(
            case_id="case-456",
            case_name="Test_Case",
            total_documents=2,
            documents={
                "doc-1": {
                    "title": "Medical Records",
                    "pages": 50,
                    "facts": 15,
                    "status": "completed",
                },
                "doc-2": {
                    "title": "Police Report",
                    "pages": 10,
                    "facts": 5,
                    "status": "processing",
                },
            },
        )

        assert len(status.documents) == 2
        assert status.documents["doc-1"]["facts"] == 15


class TestFactReviewStatus:
    """Test FactReviewStatus model"""

    def test_review_status_creation(self):
        """Test creating review status"""
        status = FactReviewStatus(
            case_id="case-789", document_id="doc-123", total_facts=20
        )

        assert status.total_facts == 20
        assert status.reviewed_facts == 0
        assert status.is_complete is False
        assert status.review_percentage == 0.0

    def test_review_completion(self):
        """Test review completion calculation"""
        status = FactReviewStatus(
            case_id="case-789",
            document_id="doc-123",
            total_facts=10,
            reviewed_facts=10,
            edited_facts=2,
            deleted_facts=1,
        )

        assert status.is_complete is True
        assert status.review_percentage == 100.0

    def test_partial_review(self):
        """Test partial review calculation"""
        status = FactReviewStatus(
            case_id="case-789", document_id="doc-123", total_facts=20, reviewed_facts=15
        )

        assert status.is_complete is False
        assert status.review_percentage == 75.0

    def test_empty_document_review(self):
        """Test review status for document with no facts"""
        status = FactReviewStatus(
            case_id="case-789", document_id="doc-123", total_facts=0
        )

        assert status.is_complete is True
        assert status.review_percentage == 100.0


class TestFactUpdateRequest:
    """Test FactUpdateRequest model"""

    def test_update_request(self):
        """Test creating fact update request"""
        request = FactUpdateRequest(
            fact_id="fact-123",
            new_content="Corrected fact content",
            edit_reason="Fixed date error",
        )

        assert request.fact_id == "fact-123"
        assert request.new_content == "Corrected fact content"
        assert request.edit_reason == "Fixed date error"

    def test_update_without_reason(self):
        """Test update request without reason"""
        request = FactUpdateRequest(fact_id="fact-456", new_content="Updated content")

        assert request.edit_reason is None

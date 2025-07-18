"""
Unit tests for deficiency analysis data models.

Tests validation, edge cases, and data integrity for DeficiencyReport
and DeficiencyItem models.
"""

from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from src.models.deficiency_models import DeficiencyItem, DeficiencyReport


class TestDeficiencyItem:
    """Test suite for DeficiencyItem model validation."""
    
    @pytest.fixture
    def valid_item_data(self):
        """Provide valid DeficiencyItem data for testing."""
        return {
            "report_id": uuid4(),
            "request_number": "RFP No. 12",
            "request_text": "All emails between parties regarding the contract",
            "oc_response_text": "No responsive documents exist",
            "classification": "not_produced",
            "confidence_score": 0.85,
            "evidence_chunks": [
                {
                    "document_id": "doc123",
                    "chunk_text": "Email thread discussing contract terms",
                    "relevance_score": 0.92
                }
            ]
        }
    
    def test_valid_deficiency_item_creation(self, valid_item_data):
        """Test creating a DeficiencyItem with valid data."""
        item = DeficiencyItem(**valid_item_data)
        
        assert isinstance(item.id, UUID)
        assert item.report_id == valid_item_data["report_id"]
        assert item.request_number == "RFP No. 12"
        assert item.classification == "not_produced"
        assert item.confidence_score == 0.85
        assert len(item.evidence_chunks) == 1
        assert item.reviewer_notes is None
        assert item.modified_by is None
        assert item.modified_at is None
    
    def test_all_classification_values(self, valid_item_data):
        """Test all valid classification values."""
        classifications = [
            "fully_produced",
            "partially_produced",
            "not_produced",
            "no_responsive_docs"
        ]
        
        for classification in classifications:
            valid_item_data["classification"] = classification
            item = DeficiencyItem(**valid_item_data)
            assert item.classification == classification
    
    def test_invalid_classification(self, valid_item_data):
        """Test invalid classification value raises error."""
        valid_item_data["classification"] = "invalid_status"
        
        with pytest.raises(ValidationError) as exc_info:
            DeficiencyItem(**valid_item_data)
        
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert "classification" in str(errors[0])
    
    def test_confidence_score_boundaries(self, valid_item_data):
        """Test confidence score boundary values."""
        # Test valid boundaries
        for score in [0.0, 0.5, 1.0]:
            valid_item_data["confidence_score"] = score
            item = DeficiencyItem(**valid_item_data)
            assert item.confidence_score == score
    
    def test_invalid_confidence_score(self, valid_item_data):
        """Test invalid confidence scores raise errors."""
        invalid_scores = [-0.1, 1.1, 2.0, -1.0]
        
        for score in invalid_scores:
            valid_item_data["confidence_score"] = score
            with pytest.raises(ValidationError) as exc_info:
                DeficiencyItem(**valid_item_data)
            
            errors = exc_info.value.errors()
            assert "confidence_score" in str(errors[0])
    
    def test_optional_fields(self, valid_item_data):
        """Test optional fields can be set."""
        valid_item_data["reviewer_notes"] = "Found additional documents"
        valid_item_data["modified_by"] = "user@lawfirm.com"
        valid_item_data["modified_at"] = datetime.now(timezone.utc)
        
        item = DeficiencyItem(**valid_item_data)
        assert item.reviewer_notes == "Found additional documents"
        assert item.modified_by == "user@lawfirm.com"
        assert isinstance(item.modified_at, datetime)
    
    def test_empty_evidence_chunks(self, valid_item_data):
        """Test item can be created with empty evidence chunks."""
        valid_item_data["evidence_chunks"] = []
        item = DeficiencyItem(**valid_item_data)
        assert item.evidence_chunks == []
    
    def test_missing_required_fields(self):
        """Test missing required fields raise errors."""
        with pytest.raises(ValidationError) as exc_info:
            DeficiencyItem(
                request_number="RFP No. 1",
                # Missing required fields
            )
        
        errors = exc_info.value.errors()
        # Should have errors for missing required fields
        assert len(errors) >= 4


class TestDeficiencyReport:
    """Test suite for DeficiencyReport model validation."""
    
    @pytest.fixture
    def valid_report_data(self):
        """Provide valid DeficiencyReport data for testing."""
        return {
            "case_name": "Smith_v_Jones_2024",
            "production_id": uuid4(),
            "rtp_document_id": uuid4(),
            "oc_response_document_id": uuid4(),
            "analysis_status": "completed",
            "total_requests": 25,
            "summary_statistics": {
                "fully_produced": 10,
                "partially_produced": 5,
                "not_produced": 8,
                "no_responsive_docs": 2,
                "total_analyzed": 25
            }
        }
    
    def test_valid_deficiency_report_creation(self, valid_report_data):
        """Test creating a DeficiencyReport with valid data."""
        report = DeficiencyReport(**valid_report_data)
        
        assert isinstance(report.id, UUID)
        assert report.case_name == "Smith_v_Jones_2024"
        assert report.analysis_status == "completed"
        assert report.total_requests == 25
        assert isinstance(report.created_at, datetime)
        assert report.completed_at is None
        assert report.summary_statistics["fully_produced"] == 10
    
    def test_default_values(self):
        """Test default values are set correctly."""
        report = DeficiencyReport(
            case_name="Test_Case",
            production_id=uuid4(),
            rtp_document_id=uuid4(),
            oc_response_document_id=uuid4()
        )
        
        assert report.analysis_status == "pending"
        assert report.total_requests == 0
        assert isinstance(report.created_at, datetime)
        assert report.completed_at is None
        assert report.summary_statistics == {
            "fully_produced": 0,
            "partially_produced": 0,
            "not_produced": 0,
            "no_responsive_docs": 0,
            "total_analyzed": 0
        }
    
    def test_all_analysis_status_values(self, valid_report_data):
        """Test all valid analysis status values."""
        statuses = ["pending", "processing", "completed", "failed"]
        
        for status in statuses:
            valid_report_data["analysis_status"] = status
            report = DeficiencyReport(**valid_report_data)
            assert report.analysis_status == status
    
    def test_invalid_analysis_status(self, valid_report_data):
        """Test invalid analysis status raises error."""
        valid_report_data["analysis_status"] = "invalid_status"
        
        with pytest.raises(ValidationError) as exc_info:
            DeficiencyReport(**valid_report_data)
        
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert "analysis_status" in str(errors[0])
    
    def test_empty_case_name(self, valid_report_data):
        """Test empty case name raises error."""
        invalid_names = ["", "   ", None]
        
        for name in invalid_names:
            if name is not None:
                valid_report_data["case_name"] = name
                with pytest.raises(ValidationError) as exc_info:
                    DeficiencyReport(**valid_report_data)
                
                errors = exc_info.value.errors()
                assert "case_name" in str(errors[0])
    
    def test_case_name_trimming(self, valid_report_data):
        """Test case name is trimmed of whitespace."""
        valid_report_data["case_name"] = "  Test_Case  "
        report = DeficiencyReport(**valid_report_data)
        assert report.case_name == "Test_Case"
    
    def test_negative_total_requests(self, valid_report_data):
        """Test negative total requests raises error."""
        valid_report_data["total_requests"] = -1
        
        with pytest.raises(ValidationError) as exc_info:
            DeficiencyReport(**valid_report_data)
        
        errors = exc_info.value.errors()
        assert "total_requests" in str(errors[0])
    
    def test_completed_at_field(self, valid_report_data):
        """Test completed_at field can be set."""
        completed_time = datetime.now(timezone.utc)
        valid_report_data["completed_at"] = completed_time
        
        report = DeficiencyReport(**valid_report_data)
        assert report.completed_at == completed_time
    
    def test_empty_summary_statistics(self, valid_report_data):
        """Test empty summary statistics gets default structure."""
        valid_report_data["summary_statistics"] = {}
        report = DeficiencyReport(**valid_report_data)
        
        assert report.summary_statistics == {
            "fully_produced": 0,
            "partially_produced": 0,
            "not_produced": 0,
            "no_responsive_docs": 0,
            "total_analyzed": 0
        }
    
    def test_json_serialization(self, valid_report_data):
        """Test model can be serialized to JSON."""
        report = DeficiencyReport(**valid_report_data)
        json_data = report.model_dump_json()
        
        assert isinstance(json_data, str)
        assert "Smith_v_Jones_2024" in json_data
        assert "completed" in json_data
        
    def test_model_copy(self, valid_report_data):
        """Test model can be copied with updates."""
        report = DeficiencyReport(**valid_report_data)
        updated_report = report.model_copy(
            update={"analysis_status": "failed"}
        )
        
        assert updated_report.analysis_status == "failed"
        assert updated_report.case_name == report.case_name
        assert updated_report.id == report.id
"""
Unit tests for ReportGenerator service.

Tests report formatting, version tracking, and error handling
following existing test patterns.
"""

from uuid import uuid4
import pytest
from unittest.mock import patch

from src.models.deficiency_models import DeficiencyItem, DeficiencyReport
from src.services.report_generator import ReportGenerator, ReportVersion


class TestReportGenerator:
    """Test suite for ReportGenerator following existing patterns."""

    @pytest.fixture
    def generator(self):
        """Create ReportGenerator instance for testing."""
        with patch("src.services.report_generator.FileSystemLoader"):
            return ReportGenerator()

    @pytest.fixture
    def sample_report(self):
        """Create sample DeficiencyReport for testing."""
        return DeficiencyReport(
            id=uuid4(),
            case_name="Test_Case_2024",
            production_id=uuid4(),
            rtp_document_id=uuid4(),
            oc_response_document_id=uuid4(),
            analysis_status="completed",
            total_requests=3,
            summary_statistics={
                "fully_produced": 1,
                "partially_produced": 1,
                "not_produced": 1,
                "no_responsive_docs": 0,
                "total_analyzed": 3,
            },
        )

    @pytest.fixture
    def sample_items(self):
        """Create sample DeficiencyItem list for testing."""
        report_id = uuid4()
        return [
            DeficiencyItem(
                id=uuid4(),
                report_id=report_id,
                request_number="RFP No. 1",
                request_text="All contracts",
                oc_response_text="Produced",
                classification="fully_produced",
                confidence_score=0.95,
                evidence_chunks=[
                    {
                        "document_id": "doc1",
                        "chunk_text": "Contract agreement",
                        "relevance_score": 0.98,
                    }
                ],
            ),
            DeficiencyItem(
                id=uuid4(),
                report_id=report_id,
                request_number="RFP No. 2",
                request_text="All emails",
                oc_response_text="Partially produced",
                classification="partially_produced",
                confidence_score=0.80,
                evidence_chunks=[
                    {
                        "document_id": "doc2",
                        "chunk_text": "Email thread",
                        "relevance_score": 0.85,
                    },
                    {
                        "document_id": "doc3",
                        "chunk_text": "Another email",
                        "relevance_score": 0.75,
                    },
                ],
            ),
            DeficiencyItem(
                id=uuid4(),
                report_id=report_id,
                request_number="RFP No. 3",
                request_text="Meeting notes",
                oc_response_text="No responsive documents",
                classification="not_produced",
                confidence_score=0.90,
                evidence_chunks=[],
            ),
        ]

    @pytest.mark.asyncio
    async def test_format_deficiency_report_success(
        self, generator, sample_report, sample_items
    ):
        """Test successful report formatting."""
        # Act
        result = await generator.format_deficiency_report(
            report=sample_report,
            deficiency_items=sample_items,
            include_evidence=True,
            max_evidence_per_item=5,
        )

        # Assert
        assert result["report"] == sample_report
        assert len(result["deficiency_items"]) == 3
        assert result["metadata"]["total_items"] == 3
        assert result["metadata"]["evidence_included"] is True

    @pytest.mark.asyncio
    async def test_format_report_without_evidence(
        self, generator, sample_report, sample_items
    ):
        """Test report formatting without evidence chunks."""
        # Act
        result = await generator.format_deficiency_report(
            report=sample_report, deficiency_items=sample_items, include_evidence=False
        )

        # Assert
        for item in result["deficiency_items"]:
            assert item.evidence_chunks == []
        assert result["metadata"]["evidence_included"] is False

    @pytest.mark.asyncio
    async def test_format_report_with_evidence_limit(
        self, generator, sample_report, sample_items
    ):
        """Test report formatting with evidence limit."""
        # Act
        result = await generator.format_deficiency_report(
            report=sample_report,
            deficiency_items=sample_items,
            include_evidence=True,
            max_evidence_per_item=1,
        )

        # Assert
        for item in result["deficiency_items"]:
            assert len(item.evidence_chunks) <= 1

    @pytest.mark.asyncio
    async def test_format_report_none_report_error(self, generator):
        """Test error handling for None report."""
        # Act & Assert
        with pytest.raises(ValueError, match="Report cannot be None"):
            await generator.format_deficiency_report(report=None, deficiency_items=[])

    def test_get_report_version_info(self, generator):
        """Test report version information retrieval."""
        # Arrange
        report_id = uuid4()

        # Act
        version_info = generator.get_report_version_info(report_id, version=1)

        # Assert
        assert isinstance(version_info, ReportVersion)
        assert version_info.version == 1
        assert version_info.change_summary == "Initial report generation"

    def test_calculate_summary_statistics(self, generator, sample_items):
        """Test summary statistics calculation."""
        # Act
        stats = generator.calculate_summary_statistics(sample_items)

        # Assert
        assert stats["fully_produced"] == 1
        assert stats["partially_produced"] == 1
        assert stats["not_produced"] == 1
        assert stats["no_responsive_docs"] == 0
        assert stats["total_analyzed"] == 3
        assert stats["compliance_rate"] == 33.33
        assert stats["most_common_deficiency"] in [
            "fully_produced",
            "partially_produced",
            "not_produced",
        ]

    def test_calculate_summary_statistics_empty(self, generator):
        """Test summary statistics with empty items."""
        # Act
        stats = generator.calculate_summary_statistics([])

        # Assert
        assert stats["total_analyzed"] == 0
        assert stats["compliance_rate"] == 0.0
        assert stats["most_common_deficiency"] is None

    def test_generate_summary_insights_high_compliance(self, generator):
        """Test insight generation for high compliance."""
        # Arrange
        stats = {
            "compliance_rate": 85.0,
            "not_produced": 2,
            "most_common_deficiency": "fully_produced",
        }

        # Act
        insights = generator.generate_summary_insights(stats)

        # Assert
        assert any("High compliance rate" in i for i in insights)
        assert any("2 requests have no production" in i for i in insights)

    def test_generate_summary_insights_low_compliance(self, generator):
        """Test insight generation for low compliance."""
        # Arrange
        stats = {
            "compliance_rate": 25.0,
            "not_produced": 10,
            "most_common_deficiency": "not_produced",
        }

        # Act
        insights = generator.generate_summary_insights(stats)

        # Assert
        assert any("Low compliance rate" in i for i in insights)
        assert any("Most common issue: Not Produced" in i for i in insights)

    def test_format_detailed_findings(self, generator, sample_items):
        """Test detailed findings formatting."""
        # Act
        findings = generator.format_detailed_findings(sample_items)

        # Assert
        assert len(findings) == 3
        assert findings[0]["request_number"] == "RFP No. 1"
        assert findings[0]["classification"] == "Fully Produced"
        assert findings[0]["confidence_level"] == "Very High"
        assert findings[0]["evidence_count"] == 1
        assert len(findings[0]["evidence"]) == 1
        assert "citation" in findings[0]["evidence"][0]

    def test_format_detailed_findings_without_confidence(self, generator, sample_items):
        """Test findings formatting without confidence scores."""
        # Act
        findings = generator.format_detailed_findings(
            sample_items, include_confidence=False
        )

        # Assert
        assert "confidence_score" not in findings[0]
        assert "confidence_level" not in findings[0]

    def test_format_evidence_chunks_with_metadata(self, generator):
        """Test evidence chunk formatting with full metadata."""
        # Arrange
        chunks = [
            {
                "chunk_text": "Contract terms",
                "relevance_score": 0.95,
                "document_id": "doc123",
                "bates_range": "PROD001-005",
                "page_number": 3,
                "document_name": "Contract.pdf",
            }
        ]

        # Act
        formatted = generator._format_evidence_chunks(chunks)

        # Assert
        assert (
            formatted[0]["citation"]
            == "Bates: PROD001-005 | Page 3 | Doc: Contract.pdf"
        )
        assert formatted[0]["relevance_score"] == 0.95
        assert formatted[0]["collapsed"] is False  # First 3 shown

    def test_build_citation_variations(self, generator):
        """Test citation building with different metadata."""
        # Test with bates only
        citation1 = generator._build_citation({"bates_range": "PROD100-110"})
        assert citation1 == "Bates: PROD100-110"

        # Test with page only
        citation2 = generator._build_citation({"page_number": 42})
        assert citation2 == "Page 42"

        # Test with no metadata
        citation3 = generator._build_citation({"document_id": "doc999"})
        assert citation3 == "Doc ID: doc999"

    @pytest.mark.asyncio
    async def test_generate_report_json(self, generator, sample_report, sample_items):
        """Test JSON report generation."""
        # Act
        result = await generator.generate_report(
            sample_report, sample_items, format="json"
        )

        # Assert
        assert isinstance(result, str)
        import json

        data = json.loads(result)
        assert data["report"]["case_name"] == "Test_Case_2024"
        assert "statistics" in data
        assert "findings" in data

    @pytest.mark.asyncio
    async def test_generate_report_markdown(
        self, generator, sample_report, sample_items
    ):
        """Test Markdown report generation."""
        # Act
        result = await generator.generate_report(
            sample_report, sample_items, format="markdown"
        )

        # Assert
        assert isinstance(result, str)
        assert "# Deficiency Analysis Report" in result
        assert "Test_Case_2024" in result
        assert "RFP No. 1" in result

    @pytest.mark.asyncio
    async def test_generate_report_html(self, generator, sample_report, sample_items):
        """Test HTML report generation."""
        # Act
        result = await generator.generate_report(
            sample_report, sample_items, format="html"
        )

        # Assert
        assert isinstance(result, str)
        assert "<!DOCTYPE html>" in result
        assert "<title>Deficiency Analysis Report</title>" in result
        assert "Test_Case_2024" in result

    @pytest.mark.asyncio
    async def test_generate_report_invalid_format(
        self, generator, sample_report, sample_items
    ):
        """Test error handling for invalid format."""
        # Act & Assert
        with pytest.raises(ValueError, match="Format must be one of"):
            await generator.generate_report(
                sample_report, sample_items, format="invalid"
            )

    @pytest.mark.asyncio
    async def test_generate_report_with_options(
        self, generator, sample_report, sample_items
    ):
        """Test report generation with custom options."""
        # Act
        result = await generator.generate_report(
            sample_report,
            sample_items,
            format="json",
            options={
                "pretty": False,
                "include_evidence": False,
                "max_evidence_per_item": 1,
            },
        )

        # Assert
        assert isinstance(result, str)
        assert "\n" not in result  # No pretty printing

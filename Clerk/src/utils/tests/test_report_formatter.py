"""
Unit tests for ReportFormatter utility.

Tests JSON, Markdown, and HTML formatting capabilities.
"""

import json
from uuid import uuid4

import pytest

from src.utils.report_formatter import ReportFormatter


class TestReportFormatter:
    """Test suite for ReportFormatter utility."""

    @pytest.fixture
    def formatter(self):
        """Create ReportFormatter instance."""
        return ReportFormatter()

    @pytest.fixture
    def sample_report_data(self):
        """Create sample report data for testing."""
        return {
            "report": {
                "id": str(uuid4()),
                "case_name": "Test_Case_2024",
                "total_requests": 10,
                "analysis_status": "completed",
            },
            "statistics": {
                "fully_produced": 4,
                "partially_produced": 3,
                "not_produced": 2,
                "no_responsive_docs": 1,
                "fully_produced_percentage": 40.0,
                "partially_produced_percentage": 30.0,
                "not_produced_percentage": 20.0,
                "no_responsive_docs_percentage": 10.0,
                "total_analyzed": 10,
                "compliance_rate": 40.0,
            },
            "insights": [
                "Moderate compliance rate (40.0%) suggests room for improvement.",
                "Most common issue: Fully Produced",
            ],
            "findings": [
                {
                    "request_number": "RFP No. 1",
                    "request_text": "All contracts",
                    "oc_response": "Produced in full",
                    "classification": "Fully Produced",
                    "confidence_score": 0.95,
                    "confidence_level": "Very High",
                    "evidence": [
                        {
                            "text": "Contract document text...",
                            "citation": "Bates: PROD001-010 | Page 5",
                            "relevance_score": 0.98,
                        }
                    ],
                }
            ],
        }

    def test_to_json_pretty(self, formatter, sample_report_data):
        """Test JSON formatting with pretty printing."""
        # Act
        result = formatter.to_json(sample_report_data, pretty=True)

        # Assert
        assert isinstance(result, str)
        parsed = json.loads(result)
        assert parsed["report"]["case_name"] == "Test_Case_2024"
        assert "\n" in result  # Pretty printing adds newlines

    def test_to_json_compact(self, formatter, sample_report_data):
        """Test JSON formatting without pretty printing."""
        # Act
        result = formatter.to_json(sample_report_data, pretty=False)

        # Assert
        assert isinstance(result, str)
        parsed = json.loads(result)
        assert parsed["report"]["case_name"] == "Test_Case_2024"
        assert result.count("\n") == 0  # No newlines in compact format

    def test_to_markdown_with_toc(self, formatter, sample_report_data):
        """Test Markdown formatting with table of contents."""
        # Act
        result = formatter.to_markdown(sample_report_data, include_toc=True)

        # Assert
        assert isinstance(result, str)
        assert "# Deficiency Analysis Report" in result
        assert "## Table of Contents" in result
        assert "Test_Case_2024" in result
        assert "| Fully Produced | 4 | 40.0% |" in result
        assert "RFP No. 1" in result

    def test_to_markdown_without_toc(self, formatter, sample_report_data):
        """Test Markdown formatting without table of contents."""
        # Act
        result = formatter.to_markdown(sample_report_data, include_toc=False)

        # Assert
        assert isinstance(result, str)
        assert "## Table of Contents" not in result
        assert "# Deficiency Analysis Report" in result

    def test_to_html_default(self, formatter, sample_report_data):
        """Test HTML formatting with default template."""
        # Act
        result = formatter.to_html(sample_report_data)

        # Assert
        assert isinstance(result, str)
        assert "<!DOCTYPE html>" in result
        assert "<title>Deficiency Analysis Report</title>" in result
        assert "Test_Case_2024" in result
        assert "<table>" in result
        assert "<tr><td>Fully Produced</td><td>4</td><td>40.0%</td></tr>" in result

    def test_to_html_confidence_styling(self, formatter):
        """Test HTML confidence level styling."""
        # Arrange
        data = {
            "report": {"case_name": "Test"},
            "statistics": {},
            "findings": [
                {
                    "request_number": "RFP 1",
                    "request_text": "Test",
                    "oc_response": "Test",
                    "classification": "Test",
                    "confidence_score": 0.95,
                    "confidence_level": "Very High",
                },
                {
                    "request_number": "RFP 2",
                    "request_text": "Test",
                    "oc_response": "Test",
                    "classification": "Test",
                    "confidence_score": 0.75,
                    "confidence_level": "Moderate",
                },
            ],
        }

        # Act
        result = formatter.to_html(data)

        # Assert
        assert "class='confidence-high'" in result
        assert "class='confidence-moderate'" in result

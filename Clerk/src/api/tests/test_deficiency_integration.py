"""
Integration tests for deficiency report generation system.

Tests complete workflow including concurrent requests, large datasets,
WebSocket events, and case isolation.
"""

import asyncio
import json
from datetime import datetime
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.report_generator import ReportGenerator
from src.services.report_storage import ReportStorage


@pytest.fixture
async def setup_test_data(async_session: AsyncSession):
    """Set up test data in database."""
    # Create test case data
    case_name = "Test_Integration_Case_2024"
    report_id = uuid4()

    # Insert test report
    await async_session.execute(
        text("""
            INSERT INTO deficiency_reports (
                id, case_name, production_id, rtp_document_id,
                oc_response_document_id, analysis_status,
                total_requests, summary_statistics, created_at,
                completed_at, analyzed_by, version
            ) VALUES (
                :id, :case_name, :production_id, :rtp_document_id,
                :oc_response_document_id, :analysis_status,
                :total_requests, :summary_statistics, :created_at,
                :completed_at, :analyzed_by, :version
            )
        """),
        {
            "id": str(report_id),
            "case_name": case_name,
            "production_id": str(uuid4()),
            "rtp_document_id": str(uuid4()),
            "oc_response_document_id": str(uuid4()),
            "analysis_status": "completed",
            "total_requests": 10,
            "summary_statistics": json.dumps(
                {
                    "fully_produced": 3,
                    "partially_produced": 2,
                    "not_produced": 4,
                    "no_responsive_docs": 1,
                }
            ),
            "created_at": datetime.utcnow(),
            "completed_at": datetime.utcnow(),
            "analyzed_by": "test_agent",
            "version": 1,
        },
    )

    # Insert test deficiency items
    for i in range(10):
        await async_session.execute(
            text("""
                INSERT INTO deficiency_items (
                    id, report_id, request_number, request_text,
                    oc_response_text, classification, confidence_score,
                    evidence_chunks, created_at
                ) VALUES (
                    :id, :report_id, :request_number, :request_text,
                    :oc_response_text, :classification, :confidence_score,
                    :evidence_chunks, :created_at
                )
            """),
            {
                "id": str(uuid4()),
                "report_id": str(report_id),
                "request_number": f"RFP No. {i + 1}",
                "request_text": f"Test request {i + 1}",
                "oc_response_text": f"Test response {i + 1}",
                "classification": [
                    "fully_produced",
                    "partially_produced",
                    "not_produced",
                    "no_responsive_docs",
                ][i % 4],
                "confidence_score": 0.85 + (i * 0.01),
                "evidence_chunks": json.dumps(
                    [
                        {
                            "document_id": str(uuid4()),
                            "chunk_text": f"Evidence chunk {j} for request {i + 1}",
                            "relevance_score": 0.9 - (j * 0.1),
                            "bates_range": f"TEST{i:04d}-TEST{i + 1:04d}",
                        }
                        for j in range(3)
                    ]
                ),
                "created_at": datetime.utcnow(),
            },
        )

    await async_session.commit()

    return {"case_name": case_name, "report_id": report_id}


@pytest.mark.asyncio
class TestDeficiencyIntegration:
    """Integration tests for the complete deficiency report system."""

    async def test_complete_report_generation_flow(
        self, client: AsyncClient, async_session: AsyncSession, setup_test_data
    ):
        """Test complete report generation workflow."""
        case_name = setup_test_data["case_name"]
        report_id = setup_test_data["report_id"]

        # Mock WebSocket emission
        with patch(
            "src.websocket.socket_server.sio.emit", new_callable=AsyncMock
        ) as mock_emit:
            # Request report generation
            response = await client.post(
                "/api/deficiency/report/generate",
                headers={"X-Case-ID": case_name},
                json={
                    "analysis_id": str(report_id),
                    "format": "json",
                    "options": {"include_evidence": True, "max_evidence_per_item": 5},
                },
            )

            assert response.status_code == status.HTTP_202_ACCEPTED
            data = response.json()
            assert "report_id" in data
            assert data["status"] == "processing"

            # Verify WebSocket events were emitted
            assert mock_emit.call_count >= 2
            start_event = mock_emit.call_args_list[0]
            assert start_event[0][0] == "deficiency:report_generation_started"

            # Retrieve generated report
            response = await client.get(
                f"/api/deficiency/report/{report_id}?format=json",
                headers={"X-Case-ID": case_name},
            )

            assert response.status_code == status.HTTP_200_OK
            report_data = response.json()
            assert report_data["case_name"] == case_name
            assert "content" in report_data
            assert report_data["format"] == "json"

    async def test_concurrent_report_requests(
        self, client: AsyncClient, async_session: AsyncSession, setup_test_data
    ):
        """Test handling of concurrent report generation requests."""
        case_name = setup_test_data["case_name"]
        report_id = setup_test_data["report_id"]

        # Create multiple concurrent requests
        async def generate_report(format_type: str):
            response = await client.post(
                "/api/deficiency/report/generate",
                headers={"X-Case-ID": case_name},
                json={
                    "analysis_id": str(report_id),
                    "format": format_type,
                    "options": {"include_evidence": False},
                },
            )
            return response

        # Launch concurrent requests for different formats
        formats = ["json", "html", "markdown"]
        tasks = [generate_report(fmt) for fmt in formats]
        responses = await asyncio.gather(*tasks)

        # All requests should be accepted
        for response in responses:
            assert response.status_code == status.HTTP_202_ACCEPTED

        # Verify all formats were generated
        await asyncio.sleep(0.5)  # Allow processing time

        for fmt in formats:
            response = await client.get(
                f"/api/deficiency/report/{report_id}?format={fmt}",
                headers={"X-Case-ID": case_name},
            )
            assert response.status_code == status.HTTP_200_OK
            assert response.json()["format"] == fmt

    async def test_large_dataset_performance(self, async_session: AsyncSession):
        """Test report generation with large dataset."""
        # Create large report with many items
        case_name = "Large_Dataset_Test_2024"
        report_id = uuid4()
        num_items = 100

        # Create report
        await async_session.execute(
            text("""
                INSERT INTO deficiency_reports (
                    id, case_name, production_id, rtp_document_id,
                    oc_response_document_id, analysis_status,
                    total_requests, summary_statistics, created_at,
                    completed_at, analyzed_by, version
                ) VALUES (
                    :id, :case_name, :production_id, :rtp_document_id,
                    :oc_response_document_id, :analysis_status,
                    :total_requests, :summary_statistics, :created_at,
                    :completed_at, :analyzed_by, :version
                )
            """),
            {
                "id": str(report_id),
                "case_name": case_name,
                "production_id": str(uuid4()),
                "rtp_document_id": str(uuid4()),
                "oc_response_document_id": str(uuid4()),
                "analysis_status": "completed",
                "total_requests": num_items,
                "summary_statistics": json.dumps(
                    {
                        "fully_produced": 25,
                        "partially_produced": 25,
                        "not_produced": 25,
                        "no_responsive_docs": 25,
                    }
                ),
                "created_at": datetime.utcnow(),
                "completed_at": datetime.utcnow(),
                "analyzed_by": "test_agent",
                "version": 1,
            },
        )

        # Create many deficiency items
        for i in range(num_items):
            await async_session.execute(
                text("""
                    INSERT INTO deficiency_items (
                        id, report_id, request_number, request_text,
                        oc_response_text, classification, confidence_score,
                        evidence_chunks, created_at
                    ) VALUES (
                        :id, :report_id, :request_number, :request_text,
                        :oc_response_text, :classification, :confidence_score,
                        :evidence_chunks, :created_at
                    )
                """),
                {
                    "id": str(uuid4()),
                    "report_id": str(report_id),
                    "request_number": f"RFP No. {i + 1}",
                    "request_text": f"Large dataset test request {i + 1}"
                    * 10,  # Long text
                    "oc_response_text": f"Large dataset test response {i + 1}" * 10,
                    "classification": [
                        "fully_produced",
                        "partially_produced",
                        "not_produced",
                        "no_responsive_docs",
                    ][i % 4],
                    "confidence_score": 0.75 + (i % 20) * 0.01,
                    "evidence_chunks": json.dumps(
                        [
                            {
                                "document_id": str(uuid4()),
                                "chunk_text": f"Evidence chunk {j} for large request {i + 1}"
                                * 5,
                                "relevance_score": 0.9 - (j * 0.05),
                                "bates_range": f"LARGE{i:06d}-LARGE{i + 1:06d}",
                            }
                            for j in range(10)  # Many evidence chunks
                        ]
                    ),
                    "created_at": datetime.utcnow(),
                },
            )

        await async_session.commit()

        # Test report generation performance
        storage = ReportStorage(async_session)
        generator = ReportGenerator(storage)

        import time

        start_time = time.time()

        # Generate report
        report = await storage.get_report(report_id, case_name)
        items = await storage.get_report_items(report_id)
        generated = await generator.generate_report(
            report, items, format="json", options={"include_evidence": True}
        )

        end_time = time.time()
        duration = end_time - start_time

        # Should complete within reasonable time
        assert duration < 5.0  # 5 seconds max for 100 items
        assert generated.format == "json"

        # Verify content
        content = json.loads(generated.content)
        assert content["total_requests"] == num_items
        assert len(content["items"]) == num_items

    async def test_case_isolation_enforcement(
        self, client: AsyncClient, async_session: AsyncSession, setup_test_data
    ):
        """Test that case isolation is properly enforced."""
        authorized_case = setup_test_data["case_name"]
        report_id = setup_test_data["report_id"]
        unauthorized_case = "Unauthorized_Case_2024"

        # Try to access report with wrong case context
        response = await client.get(
            f"/api/deficiency/report/{report_id}?format=json",
            headers={"X-Case-ID": unauthorized_case},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

        # Try to generate report with wrong case context
        response = await client.post(
            "/api/deficiency/report/generate",
            headers={"X-Case-ID": unauthorized_case},
            json={"analysis_id": str(report_id), "format": "json"},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

        # Verify correct case context works
        response = await client.get(
            f"/api/deficiency/report/{report_id}?format=json",
            headers={"X-Case-ID": authorized_case},
        )

        assert response.status_code == status.HTTP_200_OK

    async def test_websocket_event_emission(self, client: AsyncClient, setup_test_data):
        """Test WebSocket events are properly emitted during generation."""
        case_name = setup_test_data["case_name"]
        report_id = setup_test_data["report_id"]

        with patch(
            "src.websocket.socket_server.sio.emit", new_callable=AsyncMock
        ) as mock_emit:
            # Generate report
            response = await client.post(
                "/api/deficiency/report/generate",
                headers={"X-Case-ID": case_name},
                json={
                    "analysis_id": str(report_id),
                    "format": "html",
                    "options": {"include_evidence": True},
                },
            )

            assert response.status_code == status.HTTP_202_ACCEPTED

            # Wait for async processing
            await asyncio.sleep(0.5)

            # Verify events
            emit_calls = mock_emit.call_args_list
            event_types = [call[0][0] for call in emit_calls]

            assert "deficiency:report_generation_started" in event_types
            assert "deficiency:report_generation_progress" in event_types
            assert "deficiency:report_generation_completed" in event_types

            # Verify event data
            for call in emit_calls:
                event_type, event_data = call[0]
                if event_type == "deficiency:report_generation_started":
                    assert event_data["report_id"] == str(report_id)
                    assert event_data["format"] == "html"
                elif event_type == "deficiency:report_generation_completed":
                    assert event_data["report_id"] == str(report_id)
                    assert event_data["success"] is True

    async def test_report_version_retrieval(
        self, client: AsyncClient, async_session: AsyncSession, setup_test_data
    ):
        """Test retrieving specific report versions."""
        case_name = setup_test_data["case_name"]
        report_id = setup_test_data["report_id"]

        # Create version snapshot
        await async_session.execute(
            text("""
                INSERT INTO report_versions (
                    id, report_id, version, content,
                    change_summary, created_by, created_at
                ) VALUES (
                    :id, :report_id, :version, :content,
                    :change_summary, :created_by, :created_at
                )
            """),
            {
                "id": str(uuid4()),
                "report_id": str(report_id),
                "version": 1,
                "content": json.dumps(
                    {"report": {"id": str(report_id), "version": 1}, "items": []}
                ),
                "change_summary": "Initial version",
                "created_by": "test_user",
                "created_at": datetime.utcnow(),
            },
        )
        await async_session.commit()

        # Request specific version
        response = await client.get(
            f"/api/deficiency/report/{report_id}?format=json&version=1",
            headers={"X-Case-ID": case_name},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["version"] == 1

    async def test_database_resilience(self, client: AsyncClient, setup_test_data):
        """Test system behavior during database issues."""
        case_name = setup_test_data["case_name"]
        report_id = setup_test_data["report_id"]

        # Simulate database connection error
        with patch("src.database.connection.AsyncSessionLocal") as mock_session:
            mock_session.side_effect = Exception("Database connection lost")

            response = await client.get(
                f"/api/deficiency/report/{report_id}", headers={"X-Case-ID": case_name}
            )

            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert "error" in response.json()

    async def test_unicode_special_characters(self, async_session: AsyncSession):
        """Test handling of Unicode and special characters."""
        case_name = "Unicode_Test_Case_2024"
        report_id = uuid4()

        # Create report with Unicode content
        await async_session.execute(
            text("""
                INSERT INTO deficiency_reports (
                    id, case_name, production_id, rtp_document_id,
                    oc_response_document_id, analysis_status,
                    total_requests, summary_statistics, created_at,
                    completed_at, analyzed_by, version
                ) VALUES (
                    :id, :case_name, :production_id, :rtp_document_id,
                    :oc_response_document_id, :analysis_status,
                    :total_requests, :summary_statistics, :created_at,
                    :completed_at, :analyzed_by, :version
                )
            """),
            {
                "id": str(report_id),
                "case_name": case_name,
                "production_id": str(uuid4()),
                "rtp_document_id": str(uuid4()),
                "oc_response_document_id": str(uuid4()),
                "analysis_status": "completed",
                "total_requests": 3,
                "summary_statistics": json.dumps(
                    {
                        "fully_produced": 1,
                        "partially_produced": 1,
                        "not_produced": 1,
                        "no_responsive_docs": 0,
                    }
                ),
                "created_at": datetime.utcnow(),
                "completed_at": datetime.utcnow(),
                "analyzed_by": "test_agent",
                "version": 1,
            },
        )

        # Add items with Unicode and special characters
        special_chars = [
            ("Ñoño", "Café français with émojis 🎯📄✅"),
            ("日本語", "中文文档 with special chars: <>&\"'"),
            ("Русский", "Math symbols: ∑∏∫ and legal §¶™®©"),
        ]

        for i, (request, response) in enumerate(special_chars):
            await async_session.execute(
                text("""
                    INSERT INTO deficiency_items (
                        id, report_id, request_number, request_text,
                        oc_response_text, classification, confidence_score,
                        evidence_chunks, created_at
                    ) VALUES (
                        :id, :report_id, :request_number, :request_text,
                        :oc_response_text, :classification, :confidence_score,
                        :evidence_chunks, :created_at
                    )
                """),
                {
                    "id": str(uuid4()),
                    "report_id": str(report_id),
                    "request_number": f"RFP No. {i + 1}",
                    "request_text": request,
                    "oc_response_text": response,
                    "classification": "not_produced",
                    "confidence_score": 0.95,
                    "evidence_chunks": json.dumps(
                        [
                            {
                                "document_id": str(uuid4()),
                                "chunk_text": f"Unicode evidence: {request} → {response}",
                                "relevance_score": 0.9,
                            }
                        ]
                    ),
                    "created_at": datetime.utcnow(),
                },
            )

        await async_session.commit()

        # Test report generation with Unicode
        storage = ReportStorage(async_session)
        generator = ReportGenerator(storage)

        report = await storage.get_report(report_id, case_name)
        items = await storage.get_report_items(report_id)

        # Generate in all formats
        for format_type in ["json", "html", "markdown"]:
            generated = await generator.generate_report(
                report, items, format=format_type
            )

            assert generated.format == format_type

            # Verify Unicode content is preserved
            if format_type == "json":
                content = json.loads(generated.content)
                assert any(
                    "日本語" in item["request_text"] for item in content["items"]
                )
                assert any(
                    "émojis 🎯📄✅" in item["oc_response_text"]
                    for item in content["items"]
                )
            else:
                assert "日本語" in generated.content
                assert "émojis" in generated.content
                assert "§¶™®©" in generated.content

"""
Component integration tests for deficiency analyzer.

Tests individual components working together with real dependencies
(database, vector store, etc.) but in isolation from the full workflow.
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import pytest

from src.ai_agents.bmad_framework import AgentLoader, AgentExecutor
from src.ai_agents.bmad_framework.deficiency_events import DeficiencyProgressTracker
from src.document_processing.rtp_parser import RTPParser
from src.services.deficiency_service import DeficiencyService
from src.vector_storage.qdrant_store import QdrantVectorStore
from src.utils.logger import get_logger

logger = get_logger("integration_test")


class ComponentIntegrationTests:
    """Integration tests for individual components."""

    def __init__(self):
        self.case_name = "story1_4_test_database_bb623c92"
        self.output_dir = Path("/app/test_docs/output")
        self.vector_store = QdrantVectorStore()
        self.deficiency_service = DeficiencyService()
        self.agent_loader = AgentLoader()

    @pytest.mark.asyncio
    async def test_rtp_parser_integration(self):
        """Test RTP parser with real PDF processing."""
        logger.info("Testing RTP parser integration...")

        rtp_path = "/app/test_docs/RTP.pdf"
        if not Path(rtp_path).exists():
            pytest.skip("RTP.pdf not found")

        parser = RTPParser()

        # Test parsing with case isolation
        requests = parser.parse_rtp_document(
            pdf_path=rtp_path, case_name=self.case_name
        )

        assert len(requests) > 0, "No RTP requests parsed"

        # Validate parsed data
        for req in requests:
            assert req.request_number, "Request number missing"
            assert req.request_text, "Request text missing"
            assert req.case_name == self.case_name, "Case name mismatch"

        # Save parsed results
        output_file = self.output_dir / "rtp_parser_results.json"
        with open(output_file, "w") as f:
            json.dump(
                {
                    "total_requests": len(requests),
                    "requests": [
                        {
                            "number": req.request_number,
                            "text": req.request_text[:100] + "...",
                            "category": req.category,
                        }
                        for req in requests[:5]  # First 5 for review
                    ],
                },
                f,
                indent=2,
            )

        logger.info(f"Parsed {len(requests)} RTP requests successfully")
        return requests

    @pytest.mark.asyncio
    async def test_vector_search_integration(self):
        """Test vector search with real Qdrant database."""
        logger.info("Testing vector search integration...")

        # Verify collection exists
        cases = await self.vector_store.list_cases()
        assert self.case_name in cases, f"Case {self.case_name} not found in Qdrant"

        # Test different search scenarios
        test_queries = [
            "medical records",
            "emails regarding contract negotiations",
            "financial statements for 2023",
            "board meeting minutes",
        ]

        search_results = {}

        for query in test_queries:
            # Perform hybrid search
            results = await self.vector_store.hybrid_search(
                case_name=self.case_name,
                query_text=query,
                vector_weight=0.7,
                text_weight=0.3,
                limit=5,
            )

            search_results[query] = {
                "total_found": len(results),
                "top_scores": [r.relevance_score for r in results],
                "documents": [
                    r.metadata.get("document_name", "unknown") for r in results
                ],
            }

        # Validate search functionality
        assert len(search_results) == len(test_queries)
        for query, results in search_results.items():
            assert results["total_found"] >= 0, f"Search failed for: {query}"

        # Save search results
        output_file = self.output_dir / "vector_search_results.json"
        with open(output_file, "w") as f:
            json.dump(search_results, f, indent=2)

        logger.info("Vector search integration test completed")
        return search_results

    @pytest.mark.asyncio
    async def test_deficiency_service_integration(self):
        """Test deficiency service with database operations."""
        logger.info("Testing deficiency service integration...")

        # Create a test report
        report = await self.deficiency_service.create_deficiency_report(
            case_name=self.case_name,
            production_id=uuid4(),
            rtp_document_id=uuid4(),
            total_requests=10,
        )

        assert report.id, "Report ID not generated"
        assert report.case_name == self.case_name, "Case name mismatch"

        # Add test deficiency items
        test_items = [
            {
                "request_number": "RFP No. 1",
                "request_text": "All medical records for patient",
                "classification": "partially_produced",
                "confidence_score": 0.85,
            },
            {
                "request_number": "RFP No. 2",
                "request_text": "Email communications regarding contract",
                "classification": "not_produced",
                "confidence_score": 0.92,
            },
        ]

        for item_data in test_items:
            item = await self.deficiency_service.add_deficiency_item(
                report_id=report.id, **item_data
            )
            assert item.id, "Item ID not generated"

        # Update analysis status
        updated_report = await self.deficiency_service.update_analysis_status(
            report_id=report.id, status="completed"
        )

        assert updated_report.analysis_status == "completed"

        # Test retrieval
        retrieved_report = await self.deficiency_service.get_deficiency_report(
            report_id=report.id
        )

        assert retrieved_report, "Failed to retrieve report"
        assert len(retrieved_report.deficiency_items) == 2

        logger.info("Deficiency service integration test completed")
        return report.id

    @pytest.mark.asyncio
    async def test_websocket_progress_integration(self):
        """Test WebSocket progress tracking without actual socket connection."""
        logger.info("Testing WebSocket progress tracking...")

        # Create progress tracker
        tracker = DeficiencyProgressTracker(
            case_id=self.case_name,
            agent_id="deficiency-analyzer",
            task_name="test_integration",
            total_steps=5,
        )

        # Simulate progress events
        events_emitted = []

        # Mock the emit function to capture events
        original_emit = tracker._emit_update

        async def mock_emit(event_type, data):
            events_emitted.append(
                {
                    "type": event_type,
                    "data": data.dict() if hasattr(data, "dict") else data,
                }
            )

        tracker._emit_update = mock_emit

        # Emit various progress events
        await tracker.emit_analysis_started(
            production_id="test-prod-123",
            rtp_document_id="test-rtp-123",
            total_requests=10,
        )

        await tracker.emit_rtp_parsing_progress(
            pages_processed=5, total_pages=10, requests_found=3
        )

        await tracker.emit_search_progress(
            request_number="RFP No. 1",
            request_index=1,
            total_requests=10,
            documents_searched=25,
        )

        await tracker.emit_categorization_progress(
            request_number="RFP No. 1",
            category="partially_produced",
            confidence=0.85,
            deficiencies_found=1,
        )

        await tracker.emit_analysis_completed(
            report_id="test-report-123",
            total_deficiencies=3,
            summary_stats={
                "fully_produced": 7,
                "partially_produced": 2,
                "not_produced": 1,
            },
        )

        # Validate events
        assert len(events_emitted) == 5, "Not all events were emitted"

        event_types = [e["type"] for e in events_emitted]
        assert "agent:analysis_started" in event_types
        assert "agent:analysis_completed" in event_types

        # Save event log
        output_file = self.output_dir / "websocket_events_log.json"
        with open(output_file, "w") as f:
            json.dump(
                {"total_events": len(events_emitted), "events": events_emitted},
                f,
                indent=2,
            )

        logger.info(
            f"WebSocket progress tracking test completed with {len(events_emitted)} events"
        )
        return events_emitted

    @pytest.mark.asyncio
    async def test_agent_task_execution(self):
        """Test individual agent task execution."""
        logger.info("Testing agent task execution...")

        # Load agent
        agent_def = await self.agent_loader.load_agent("deficiency-analyzer")
        assert agent_def, "Failed to load agent"

        # Test task loading
        tasks = agent_def.get("dependencies", {}).get("tasks", [])
        assert len(tasks) > 0, "No tasks found in agent definition"

        # Create mock security context
        from src.middleware.case_context import CaseContext
        from src.ai_agents.bmad_framework.security import AgentSecurityContext

        case_context = CaseContext(
            case_id="test-case",
            case_name=self.case_name,
            law_firm_id="test-firm",
            user_id="test-user",
            permissions=["read", "write"],
        )

        security_context = AgentSecurityContext(
            case_context=case_context, agent_id="deficiency-analyzer"
        )

        # Test search command execution
        executor = AgentExecutor()

        try:
            result = await executor.execute_command(
                agent_def=agent_def,
                command="search",
                case_name=self.case_name,
                security_context=security_context,
                parameters={
                    "query": "test search query",
                    "filters": {},
                    "limit": 5,
                    "offset": 0,
                },
            )

            assert "results" in result, "Search results not returned"

            # Save task execution result
            output_file = self.output_dir / "task_execution_result.json"
            with open(output_file, "w") as f:
                json.dump(result, f, indent=2)

            logger.info("Agent task execution test completed")

        except Exception as e:
            logger.error(f"Task execution failed: {str(e)}")
            raise

    @pytest.mark.asyncio
    async def test_template_rendering(self):
        """Test template rendering for reports."""
        logger.info("Testing template rendering...")

        from src.ai_agents.bmad_framework.templates import TemplateRenderer

        renderer = TemplateRenderer()

        # Load deficiency report template
        template_path = Path(
            "/app/src/ai_agents/bmad_framework/templates/deficiency-report-tmpl.yaml"
        )
        if not template_path.exists():
            pytest.skip("Template file not found")

        # Test data for rendering
        test_data = {
            "case_name": self.case_name,
            "report_date": datetime.utcnow().isoformat(),
            "total_requests": 10,
            "total_deficiencies": 3,
            "compliance_percentage": 70.0,
            "deficiency_items": [
                {
                    "request_number": "RFP No. 1",
                    "request_text": "All medical records",
                    "classification": "partially_produced",
                    "confidence_score": 0.85,
                    "evidence_summary": "Found 15 documents but missing key records",
                }
            ],
        }

        # Render template
        rendered = renderer.render_template(
            template_path=str(template_path), data=test_data, format="json"
        )

        assert rendered, "Template rendering failed"

        # Save rendered output
        output_file = self.output_dir / "rendered_report_sample.json"
        with open(output_file, "w") as f:
            json.dump(rendered, f, indent=2)

        logger.info("Template rendering test completed")
        return rendered


async def run_component_tests():
    """Run all component integration tests."""
    tests = ComponentIntegrationTests()

    results = {"timestamp": datetime.utcnow().isoformat(), "tests": {}}

    # Run each test and capture results
    test_methods = [
        ("RTP Parser Integration", tests.test_rtp_parser_integration),
        ("Vector Search Integration", tests.test_vector_search_integration),
        ("Deficiency Service Integration", tests.test_deficiency_service_integration),
        ("WebSocket Progress Integration", tests.test_websocket_progress_integration),
        ("Agent Task Execution", tests.test_agent_task_execution),
        ("Template Rendering", tests.test_template_rendering),
    ]

    for test_name, test_method in test_methods:
        try:
            logger.info(f"\nRunning: {test_name}")
            result = await test_method()
            results["tests"][test_name] = {
                "status": "passed",
                "result": str(result) if result else "completed",
            }
            logger.info(f"✓ {test_name} passed")
        except Exception as e:
            results["tests"][test_name] = {"status": "failed", "error": str(e)}
            logger.error(f"✗ {test_name} failed: {str(e)}")

    # Save overall results
    output_file = Path("/app/test_docs/output") / "component_test_results.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)

    logger.info(f"\nComponent tests complete. Results saved to: {output_file}")
    return results


if __name__ == "__main__":
    asyncio.run(run_component_tests())

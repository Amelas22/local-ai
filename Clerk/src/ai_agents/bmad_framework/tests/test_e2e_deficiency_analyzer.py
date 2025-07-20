"""
End-to-end integration test for deficiency analyzer agent using production data.

This test uses real PDF documents and an existing Qdrant database to validate
the complete deficiency analysis workflow.

Prerequisites:
    - RTP.pdf file in Clerk/test_docs/
    - Qdrant database: case_story1_4_test_database_bb623c92
    - Run inside Clerk Docker container
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
from uuid import uuid4

from pydantic import BaseModel

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from src.ai_agents.bmad_framework import AgentLoader, AgentExecutor
from src.ai_agents.bmad_framework.security import AgentSecurityContext
from src.middleware.case_context import CaseContext
from src.document_processing.pdf_extractor import PDFExtractor
from src.document_processing.rtp_parser import RTPParser
from src.services.deficiency_service import DeficiencyService
from src.vector_storage.qdrant_store import QdrantVectorStore
from src.utils.logger import get_logger

logger = get_logger("e2e_test")


class E2ETestConfig(BaseModel):
    """Configuration for E2E test."""

    rtp_path: str = "/app/test_docs/RTP.pdf"
    case_name: str = "story1_4_test_database_bb623c92"
    output_dir: str = "/app/test_docs/output"
    agent_id: str = "deficiency-analyzer"
    mock_user_id: str = "test-user-001"
    mock_case_id: str = "test-case-001"
    mock_law_firm_id: str = "test-firm-001"


class DeficiencyAnalyzerE2ETest:
    """
    End-to-end integration test for the deficiency analyzer agent.

    Tests the complete workflow from RTP parsing through report generation
    using production data and real vector database.
    """

    def __init__(self, config: E2ETestConfig):
        self.config = config
        self.agent_loader = AgentLoader()
        self.agent_executor = AgentExecutor()
        self.vector_store = QdrantVectorStore()
        self.deficiency_service = DeficiencyService()

        # Create output directory
        Path(self.config.output_dir).mkdir(parents=True, exist_ok=True)

        # Setup mock case context
        self.case_context = CaseContext(
            case_id=self.config.mock_case_id,
            case_name=self.config.case_name,
            law_firm_id=self.config.mock_law_firm_id,
            user_id=self.config.mock_user_id,
            permissions=["read", "write", "admin"],
        )

        self.security_context = AgentSecurityContext(
            case_context=self.case_context, agent_id=self.config.agent_id
        )

    async def test_full_workflow(self) -> Dict[str, Any]:
        """
        Test the complete deficiency analysis workflow.

        Steps:
        1. Verify prerequisites (RTP file, Qdrant database)
        2. Load the deficiency analyzer agent
        3. Parse RTP document
        4. Search production documents
        5. Categorize compliance for each request
        6. Generate deficiency report
        7. Save outputs for review

        Returns:
            Test results dictionary
        """
        test_results = {
            "test_id": str(uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "config": self.config.dict(),
            "steps": {},
        }

        try:
            # Step 1: Verify prerequisites
            logger.info("Step 1: Verifying prerequisites...")
            test_results["steps"]["prerequisites"] = await self._verify_prerequisites()

            # Step 2: Load agent
            logger.info("Step 2: Loading deficiency analyzer agent...")
            agent_def = await self.agent_loader.load_agent(self.config.agent_id)
            test_results["steps"]["agent_loading"] = {
                "status": "success",
                "agent_name": agent_def.name,
                "commands": agent_def.commands,
            }

            # Step 3: Parse RTP document
            logger.info("Step 3: Parsing RTP document...")
            rtp_results = await self._test_rtp_parsing()
            test_results["steps"]["rtp_parsing"] = rtp_results

            # Step 4: Test document search
            logger.info("Step 4: Testing document search...")
            search_results = await self._test_document_search(
                rtp_results["requests"][:3]  # Test first 3 requests
            )
            test_results["steps"]["document_search"] = search_results

            # Step 5: Test categorization
            logger.info("Step 5: Testing compliance categorization...")
            categorization_results = await self._test_categorization(
                rtp_results["requests"][:3], search_results
            )
            test_results["steps"]["categorization"] = categorization_results

            # Step 6: Test full analysis via agent
            logger.info("Step 6: Running full agent analysis...")
            analysis_results = await self._test_full_agent_analysis()
            test_results["steps"]["full_analysis"] = analysis_results

            # Step 7: Save outputs
            logger.info("Step 7: Saving test outputs...")
            await self._save_outputs(test_results)

            test_results["overall_status"] = "success"

        except Exception as e:
            logger.error(f"E2E test failed: {str(e)}")
            test_results["overall_status"] = "failed"
            test_results["error"] = str(e)

            # Still save outputs on failure
            await self._save_outputs(test_results)
            raise

        return test_results

    async def _verify_prerequisites(self) -> Dict[str, Any]:
        """Verify all prerequisites are met."""
        results = {}

        # Check RTP file exists
        rtp_exists = Path(self.config.rtp_path).exists()
        results["rtp_file_exists"] = rtp_exists
        if not rtp_exists:
            raise FileNotFoundError(f"RTP file not found: {self.config.rtp_path}")

        # Check Qdrant collection exists
        try:
            cases = self.vector_store.list_cases()
            case_names = [case.get("collection_name", "") for case in cases]
            collection_exists = self.config.case_name in case_names
            results["qdrant_collection_exists"] = collection_exists

            if collection_exists:
                # Get document count from collection info
                collection_info = next(
                    (
                        case
                        for case in cases
                        if case.get("collection_name") == self.config.case_name
                    ),
                    None,
                )
                if collection_info:
                    doc_count = collection_info.get("points_count", 0)
                    results["document_count"] = doc_count
                    logger.info(f"Found {doc_count} documents in collection")
                else:
                    results["document_count"] = "Unknown"
                    logger.warning("Could not get document count")
            else:
                raise ValueError(
                    f"Qdrant collection not found: {self.config.case_name}"
                )

        except Exception as e:
            results["qdrant_error"] = str(e)
            raise

        return results

    async def _test_rtp_parsing(self) -> Dict[str, Any]:
        """Test RTP document parsing."""
        results = {
            "file_path": self.config.rtp_path,
            "parse_time_start": datetime.utcnow().isoformat(),
        }

        try:
            # Extract text from PDF
            pdf_extractor = PDFExtractor()
            with open(self.config.rtp_path, "rb") as f:
                pdf_content = f.read()
            pdf_data = pdf_extractor.extract_text(pdf_content, filename="RTP.pdf")
            results["total_pages"] = pdf_data.metadata.get("page_count", 0)

            # Parse RTP requests
            rtp_parser = RTPParser(case_name=self.config.case_name)
            rtp_requests = await rtp_parser.parse_rtp_document(self.config.rtp_path)

            results["parse_time_end"] = datetime.utcnow().isoformat()
            results["total_requests"] = len(rtp_requests)
            results["requests"] = [
                {
                    "request_number": req.request_number,
                    "request_text": req.request_text[:200] + "..."
                    if len(req.request_text) > 200
                    else req.request_text,
                    "category": req.category,
                    "page_range": req.page_range,
                }
                for req in rtp_requests
            ]

            logger.info(f"Parsed {len(rtp_requests)} RTP requests")

        except Exception as e:
            results["error"] = str(e)
            raise

        return results

    async def _test_document_search(self, rtp_requests: list) -> Dict[str, Any]:
        """Test document search for RTP requests."""
        results = {"search_time_start": datetime.utcnow().isoformat(), "searches": []}

        for request in rtp_requests:
            search_result = {
                "request_number": request["request_number"],
                "query": request["request_text"][:100] + "...",
            }

            try:
                # Perform hybrid search
                search_results = await self.vector_store.hybrid_search(
                    case_name=self.config.case_name,
                    query_text=request["request_text"],
                    vector_weight=0.7,
                    text_weight=0.3,
                    limit=10,
                )

                search_result["documents_found"] = len(search_results)
                search_result["top_scores"] = [
                    result.relevance_score for result in search_results[:3]
                ]

                # Extract document names
                doc_names = list(
                    set(
                        [
                            result.metadata.get("document_name", "unknown")
                            for result in search_results
                        ]
                    )
                )
                search_result["unique_documents"] = doc_names[:5]

            except Exception as e:
                search_result["error"] = str(e)

            results["searches"].append(search_result)

        results["search_time_end"] = datetime.utcnow().isoformat()
        return results

    async def _test_categorization(
        self, rtp_requests: list, search_results: Dict
    ) -> Dict[str, Any]:
        """Test compliance categorization."""
        results = {
            "categorization_time_start": datetime.utcnow().isoformat(),
            "categorizations": [],
        }

        # Execute categorize command via agent
        agent_def = await self.agent_loader.load_agent(self.config.agent_id)

        for i, request in enumerate(rtp_requests):
            cat_result = {"request_number": request["request_number"]}

            try:
                # Get search results for this request
                search_data = search_results["searches"][i]

                # Mock OC response (in real test, this would come from parsed OC document)
                mock_oc_response = "All responsive documents have been produced."

                # Execute categorization
                result = await self.agent_executor.execute_command(
                    agent_def=agent_def,
                    command="categorize",
                    case_name=self.config.case_name,
                    security_context=self.security_context,
                    parameters={
                        "request_number": request["request_number"],
                        "request_text": request["request_text"],
                        "search_results": [],  # Simplified for test
                        "oc_response_text": mock_oc_response,
                    },
                )

                cat_result["classification"] = result.get("classification")
                cat_result["confidence_score"] = result.get("confidence_score")
                cat_result["evidence_summary"] = result.get("evidence_summary")

            except Exception as e:
                cat_result["error"] = str(e)

            results["categorizations"].append(cat_result)

        results["categorization_time_end"] = datetime.utcnow().isoformat()
        return results

    async def _test_full_agent_analysis(self) -> Dict[str, Any]:
        """Test full agent analysis workflow."""
        results = {"analysis_time_start": datetime.utcnow().isoformat()}

        try:
            # Create mock production and RTP document IDs
            production_id = str(uuid4())
            rtp_document_id = str(uuid4())

            # Load agent
            agent_def = await self.agent_loader.load_agent(self.config.agent_id)

            # Execute analyze command
            logger.info("Executing full analysis command...")

            # Note: This is a simplified version for testing
            # In production, this would trigger the full async workflow
            result = await self.agent_executor.execute_command(
                agent_def=agent_def,
                command="analyze",
                case_name=self.config.case_name,
                security_context=self.security_context,
                parameters={
                    "production_id": production_id,
                    "rtp_document_id": rtp_document_id,
                    "oc_response_id": None,
                    "options": {
                        "confidence_threshold": 0.7,
                        "include_partial_matches": True,
                    },
                },
            )

            results["processing_id"] = result.get("processing_id")
            results["status"] = "initiated"
            results["analysis_time_end"] = datetime.utcnow().isoformat()

        except Exception as e:
            results["error"] = str(e)
            raise

        return results

    async def _save_outputs(self, test_results: Dict[str, Any]) -> None:
        """Save all test outputs for review."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

        # Save main test results
        results_file = (
            Path(self.config.output_dir) / f"e2e_test_results_{timestamp}.json"
        )
        with open(results_file, "w") as f:
            json.dump(test_results, f, indent=2)
        logger.info(f"Saved test results to: {results_file}")

        # Save summary report
        summary_file = (
            Path(self.config.output_dir) / f"e2e_test_summary_{timestamp}.txt"
        )
        with open(summary_file, "w") as f:
            f.write("Deficiency Analyzer E2E Test Summary\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Test ID: {test_results.get('test_id', 'N/A')}\n")
            f.write(f"Timestamp: {test_results.get('timestamp', 'N/A')}\n")
            f.write(f"Case Name: {self.config.case_name}\n")
            f.write(f"Overall Status: {test_results.get('overall_status', 'N/A')}\n\n")

            if "steps" in test_results:
                f.write("Test Steps Summary:\n")
                f.write("-" * 30 + "\n")
                for step_name, step_data in test_results["steps"].items():
                    status = (
                        step_data.get("status", "N/A")
                        if isinstance(step_data, dict)
                        else "completed"
                    )
                    f.write(f"  - {step_name}: {status}\n")

            if "error" in test_results:
                f.write(f"\nError: {test_results['error']}\n")

        logger.info(f"Saved test summary to: {summary_file}")


async def run_e2e_test():
    """Run the E2E test."""
    config = E2ETestConfig()
    test = DeficiencyAnalyzerE2ETest(config)

    logger.info("Starting Deficiency Analyzer E2E Test...")
    logger.info(f"Configuration: {config.dict()}")

    try:
        results = await test.test_full_workflow()
        logger.info("E2E test completed successfully!")
        return results
    except Exception as e:
        logger.error(f"E2E test failed: {str(e)}")
        raise


if __name__ == "__main__":
    # Run the test
    asyncio.run(run_e2e_test())

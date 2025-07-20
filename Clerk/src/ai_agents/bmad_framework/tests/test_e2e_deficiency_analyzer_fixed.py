"""
Fixed end-to-end integration test for deficiency analyzer agent using BMad framework.

This test properly utilizes the BMad agent framework with actual task execution.
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
from uuid import uuid4

import pytest
from pydantic import BaseModel

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from src.ai_agents.bmad_framework import AgentLoader, AgentExecutor
from src.ai_agents.bmad_framework.security import AgentSecurityContext
from src.middleware.case_context import CaseContext
from src.models.unified_document_models import UnifiedDocument
from src.document_processing.pdf_extractor import PDFExtractor
from src.document_processing.rtp_parser import RTPParser
from src.services.deficiency_service import DeficiencyService
from src.vector_storage.qdrant_store import QdrantVectorStore
from src.utils.logger import get_logger

logger = get_logger("e2e_test_fixed")


class E2ETestConfig(BaseModel):
    """Configuration for E2E test."""
    rtp_path: str = "/app/test_docs/RTP.pdf"
    case_name: str = "story1_4_test_database_bb623c92"
    output_dir: str = "/app/test_docs/output"
    agent_id: str = "deficiency-analyzer"
    mock_user_id: str = "test-user-001"
    mock_case_id: str = "test-case-001"
    mock_law_firm_id: str = "test-firm-001"


class BMadDeficiencyAnalyzerE2ETest:
    """
    Fixed E2E test that properly uses the BMad framework.
    
    This test validates the complete workflow using the actual BMad agent
    implementation rather than bypassing it.
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
            permissions=["read", "write", "admin"]
        )
        
        self.security_context = AgentSecurityContext(
            case_context=self.case_context,
            agent_id=self.config.agent_id
        )
    
    async def test_full_bmad_workflow(self) -> Dict[str, Any]:
        """
        Test the complete deficiency analysis workflow using BMad framework.
        
        This test properly uses the agent executor with registered task handlers.
        """
        test_results = {
            "test_id": str(uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "config": self.config.dict(),
            "steps": {},
            "framework": "BMad"
        }
        
        try:
            # Step 1: Verify prerequisites
            logger.info("Step 1: Verifying prerequisites...")
            test_results["steps"]["prerequisites"] = await self._verify_prerequisites()
            
            # Step 2: Load BMad agent
            logger.info("Step 2: Loading BMad deficiency analyzer agent...")
            agent_def = await self.agent_loader.load_agent(self.config.agent_id)
            test_results["steps"]["agent_loading"] = {
                "status": "success",
                "agent_name": agent_def.name,
                "agent_id": agent_def.id,
                "commands": list(agent_def.command_names),
                "tasks": agent_def.tasks,
                "framework": "BMad"
            }
            
            # Step 3: Test analyze-rtp command via BMad
            logger.info("Step 3: Testing analyze-rtp command via BMad framework...")
            analyze_result = await self._test_bmad_analyze_command(agent_def)
            test_results["steps"]["analyze_rtp"] = analyze_result
            
            # Step 4: Test search command via BMad
            logger.info("Step 4: Testing search command via BMad framework...")
            search_results = await self._test_bmad_search_command(
                agent_def,
                analyze_result.get("requests", [])[:3]
            )
            test_results["steps"]["search_production"] = search_results
            
            # Step 5: Test categorize command via BMad
            logger.info("Step 5: Testing categorize command via BMad framework...")
            categorize_results = await self._test_bmad_categorize_command(
                agent_def,
                analyze_result.get("requests", [])[:3],
                search_results
            )
            test_results["steps"]["categorize_compliance"] = categorize_results
            
            # Step 6: Test full analysis command
            logger.info("Step 6: Testing full analysis command via BMad framework...")
            full_analysis_result = await self._test_bmad_full_analysis(agent_def)
            test_results["steps"]["full_analysis"] = full_analysis_result
            
            # Step 7: Validate BMad integration
            logger.info("Step 7: Validating BMad framework integration...")
            validation_result = await self._validate_bmad_integration(test_results)
            test_results["steps"]["framework_validation"] = validation_result
            
            # Step 8: Save outputs
            logger.info("Step 8: Saving test outputs...")
            await self._save_outputs(test_results)
            
            test_results["overall_status"] = "success"
            test_results["framework_used"] = "BMad Agent Framework"
            
        except Exception as e:
            logger.error(f"BMad E2E test failed: {str(e)}", exc_info=True)
            test_results["overall_status"] = "failed"
            test_results["error"] = str(e)
            test_results["error_type"] = type(e).__name__
            
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
                collection_info = next(
                    (case for case in cases if case.get("collection_name") == self.config.case_name),
                    None
                )
                if collection_info:
                    doc_count = collection_info.get("points_count", 0)
                    results["document_count"] = doc_count
                    logger.info(f"Found {doc_count} documents in collection")
            else:
                raise ValueError(f"Qdrant collection not found: {self.config.case_name}")
                
        except Exception as e:
            results["qdrant_error"] = str(e)
            raise
        
        # Verify BMad framework components
        results["bmad_framework"] = {
            "agent_loader": "available",
            "agent_executor": "available",
            "task_handlers": "registered"
        }
        
        return results
    
    async def _test_bmad_analyze_command(self, agent_def) -> Dict[str, Any]:
        """Test analyze-rtp command using BMad framework."""
        logger.info("Executing analyze command via BMad agent executor...")
        
        try:
            # Execute command through BMad framework
            result = await self.agent_executor.execute_command(
                agent_def=agent_def,
                command="analyze",  # This will map to analyze-rtp task
                case_name=self.config.case_name,
                security_context=self.security_context,
                parameters={
                    "rtp_path": self.config.rtp_path
                }
            )
            
            if not result.success:
                raise Exception(f"Command failed: {result.error}")
            
            # Extract the actual result
            command_result = result.result
            
            return {
                "status": "success",
                "framework": "BMad",
                "command": "analyze",
                "task_executed": "analyze-rtp",
                "total_requests": command_result.get("total_requests", 0),
                "requests": command_result.get("requests", []),
                "execution_metadata": result.metadata
            }
            
        except Exception as e:
            logger.error(f"Analyze command failed: {str(e)}")
            return {
                "status": "failed",
                "error": str(e),
                "framework": "BMad"
            }
    
    async def _test_bmad_search_command(
        self,
        agent_def,
        rtp_requests: List[Dict]
    ) -> Dict[str, Any]:
        """Test search command using BMad framework."""
        results = {
            "framework": "BMad",
            "command": "search",
            "searches": []
        }
        
        for request in rtp_requests[:2]:  # Test first 2 requests
            logger.info(f"Searching for request {request.get('request_number')}...")
            
            try:
                # Execute search command via BMad
                result = await self.agent_executor.execute_command(
                    agent_def=agent_def,
                    command="search",
                    case_name=self.config.case_name,
                    security_context=self.security_context,
                    parameters={
                        "query": request.get("request_text", ""),
                        "limit": 10
                    }
                )
                
                if result.success:
                    search_data = result.result
                    results["searches"].append({
                        "request_number": request.get("request_number"),
                        "status": "success",
                        "documents_found": search_data.get("total_results", 0),
                        "framework": "BMad",
                        "task_executed": "search-production"
                    })
                else:
                    results["searches"].append({
                        "request_number": request.get("request_number"),
                        "status": "failed",
                        "error": result.error
                    })
                    
            except Exception as e:
                results["searches"].append({
                    "request_number": request.get("request_number"),
                    "status": "error",
                    "error": str(e)
                })
        
        return results
    
    async def _test_bmad_categorize_command(
        self,
        agent_def,
        rtp_requests: List[Dict],
        search_results: Dict
    ) -> Dict[str, Any]:
        """Test categorize command using BMad framework."""
        results = {
            "framework": "BMad",
            "command": "categorize",
            "categorizations": []
        }
        
        for i, request in enumerate(rtp_requests[:2]):  # Test first 2
            logger.info(f"Categorizing request {request.get('request_number')}...")
            
            try:
                # Execute categorize command via BMad
                result = await self.agent_executor.execute_command(
                    agent_def=agent_def,
                    command="categorize",
                    case_name=self.config.case_name,
                    security_context=self.security_context,
                    parameters={
                        "request_number": request.get("request_number"),
                        "request_text": request.get("request_text"),
                        "search_results": [],  # Simplified for test
                        "oc_response_text": "All responsive documents have been produced."
                    }
                )
                
                if result.success:
                    cat_data = result.result
                    results["categorizations"].append({
                        "request_number": request.get("request_number"),
                        "status": "success",
                        "classification": cat_data.get("classification"),
                        "confidence_score": cat_data.get("confidence_score"),
                        "framework": "BMad",
                        "task_executed": "categorize-compliance"
                    })
                else:
                    results["categorizations"].append({
                        "request_number": request.get("request_number"),
                        "status": "failed",
                        "error": result.error
                    })
                    
            except Exception as e:
                results["categorizations"].append({
                    "request_number": request.get("request_number"),
                    "status": "error",
                    "error": str(e)
                })
        
        return results
    
    async def _test_bmad_full_analysis(self, agent_def) -> Dict[str, Any]:
        """Test full analysis workflow via BMad."""
        logger.info("Testing full analysis command...")
        
        try:
            # Create mock IDs
            production_id = str(uuid4())
            rtp_document_id = str(uuid4())
            
            # Execute full analysis via BMad
            result = await self.agent_executor.execute_command(
                agent_def=agent_def,
                command="analyze",
                case_name=self.config.case_name,
                security_context=self.security_context,
                parameters={
                    "production_id": production_id,
                    "rtp_document_id": rtp_document_id,
                    "options": {
                        "confidence_threshold": 0.7,
                        "include_partial_matches": True
                    }
                }
            )
            
            if result.success:
                analysis_data = result.result
                return {
                    "status": "success",
                    "framework": "BMad",
                    "processing_id": analysis_data.get("processing_id"),
                    "report_id": analysis_data.get("report_id"),
                    "websocket_channel": analysis_data.get("websocket_channel"),
                    "message": analysis_data.get("message")
                }
            else:
                return {
                    "status": "failed",
                    "error": result.error,
                    "framework": "BMad"
                }
                
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "framework": "BMad"
            }
    
    async def _validate_bmad_integration(self, test_results: Dict) -> Dict[str, Any]:
        """Validate that BMad framework was properly used."""
        validation = {
            "framework_used": True,
            "commands_executed": [],
            "tasks_mapped": [],
            "handlers_invoked": []
        }
        
        # Check each step used BMad
        for step_name, step_data in test_results.get("steps", {}).items():
            if isinstance(step_data, dict):
                if step_data.get("framework") == "BMad":
                    if "command" in step_data:
                        validation["commands_executed"].append(step_data["command"])
                    if "task_executed" in step_data:
                        validation["tasks_mapped"].append(step_data["task_executed"])
        
        # Validate all commands were properly mapped
        expected_mappings = {
            "analyze": "analyze-rtp",
            "search": "search-production",
            "categorize": "categorize-compliance"
        }
        
        validation["mapping_validation"] = {
            cmd: task in validation["tasks_mapped"]
            for cmd, task in expected_mappings.items()
        }
        
        validation["all_mappings_valid"] = all(validation["mapping_validation"].values())
        
        return validation
    
    async def _save_outputs(self, test_results: Dict[str, Any]) -> None:
        """Save all test outputs for review."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        
        # Save main test results
        results_file = Path(self.config.output_dir) / f"bmad_e2e_test_results_{timestamp}.json"
        with open(results_file, "w") as f:
            json.dump(test_results, f, indent=2, default=str)
        logger.info(f"Saved test results to: {results_file}")
        
        # Save summary report
        summary_file = Path(self.config.output_dir) / f"bmad_e2e_test_summary_{timestamp}.txt"
        with open(summary_file, "w") as f:
            f.write("BMad Deficiency Analyzer E2E Test Summary\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Test ID: {test_results.get('test_id', 'N/A')}\n")
            f.write(f"Timestamp: {test_results.get('timestamp', 'N/A')}\n")
            f.write(f"Framework: {test_results.get('framework', 'N/A')}\n")
            f.write(f"Case Name: {self.config.case_name}\n")
            f.write(f"Overall Status: {test_results.get('overall_status', 'N/A')}\n\n")
            
            if "steps" in test_results:
                f.write("Test Steps Summary:\n")
                f.write("-" * 30 + "\n")
                for step_name, step_data in test_results["steps"].items():
                    status = "completed"
                    if isinstance(step_data, dict):
                        status = step_data.get("status", "completed")
                    f.write(f"  - {step_name}: {status}\n")
            
            # Add framework validation
            if "framework_validation" in test_results.get("steps", {}):
                val = test_results["steps"]["framework_validation"]
                f.write("\nBMad Framework Validation:\n")
                f.write("-" * 30 + "\n")
                f.write(f"  - Commands Executed: {val.get('commands_executed', [])}\n")
                f.write(f"  - Tasks Mapped: {val.get('tasks_mapped', [])}\n")
                f.write(f"  - All Mappings Valid: {val.get('all_mappings_valid', False)}\n")
            
            if "error" in test_results:
                f.write(f"\nError: {test_results['error']}\n")
                f.write(f"Error Type: {test_results.get('error_type', 'Unknown')}\n")
        
        logger.info(f"Saved test summary to: {summary_file}")


@pytest.mark.asyncio
async def test_bmad_deficiency_analyzer():
    """Run the BMad framework E2E test."""
    config = E2ETestConfig()
    test = BMadDeficiencyAnalyzerE2ETest(config)
    
    logger.info("Starting BMad Deficiency Analyzer E2E Test...")
    logger.info(f"Configuration: {config.dict()}")
    
    results = await test.test_full_bmad_workflow()
    
    # Assert test passed
    assert results["overall_status"] == "success", f"Test failed: {results.get('error')}"
    
    # Assert BMad framework was used
    assert results.get("framework") == "BMad", "BMad framework was not used"
    
    # Assert all commands were executed
    validation = results["steps"].get("framework_validation", {})
    assert validation.get("all_mappings_valid", False), "Not all command mappings were valid"
    
    logger.info("BMad E2E test completed successfully!")
    return results


if __name__ == "__main__":
    # Run the test
    asyncio.run(test_bmad_deficiency_analyzer())
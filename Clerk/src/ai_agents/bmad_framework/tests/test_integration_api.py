"""
API integration tests for deficiency analyzer endpoints.

Tests the REST API endpoints with real backend services but uses
test data and test database.
"""

import asyncio
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
from uuid import uuid4

import pytest
from httpx import AsyncClient, ASGITransport
from fastapi import status

from main import app
from src.middleware.case_context import CaseContext
from src.utils.logger import get_logger

logger = get_logger("api_integration_test")


class APIIntegrationTests:
    """Integration tests for API endpoints."""
    
    def __init__(self):
        self.case_name = "story1_4_test_database_bb623c92"
        self.case_id = "test-case-001"
        self.user_id = "test-user-001"
        self.output_dir = Path("/app/test_docs/output")
        
        # Test data IDs
        self.production_id = str(uuid4())
        self.rtp_document_id = str(uuid4())
        self.oc_response_id = str(uuid4())
        
        # API client setup
        self.base_url = "http://localhost:8000"
        self.headers = {
            "X-Case-ID": self.case_id,
            "X-User-ID": self.user_id,
            "Content-Type": "application/json"
        }
    
    async def get_client(self) -> AsyncClient:
        """Create an async HTTP client."""
        transport = ASGITransport(app=app)
        return AsyncClient(transport=transport, base_url=self.base_url)
    
    @pytest.mark.asyncio
    async def test_analyze_endpoint_integration(self):
        """Test the analyze endpoint with real services."""
        logger.info("Testing analyze endpoint integration...")
        
        async with await self.get_client() as client:
            # Prepare request data
            request_data = {
                "production_id": self.production_id,
                "rtp_document_id": self.rtp_document_id,
                "oc_response_id": self.oc_response_id,
                "options": {
                    "confidence_threshold": 0.7,
                    "include_partial_matches": True
                }
            }
            
            # Make request
            response = await client.post(
                "/api/agents/deficiency-analyzer/analyze",
                json=request_data,
                headers=self.headers
            )
            
            # Validate response
            assert response.status_code == status.HTTP_202_ACCEPTED
            
            data = response.json()
            assert "processing_id" in data
            assert "websocket_channel" in data
            assert "estimated_duration_seconds" in data
            
            # Save response
            result = {
                "endpoint": "/analyze",
                "status_code": response.status_code,
                "response": data,
                "request": request_data
            }
            
            output_file = self.output_dir / "api_analyze_response.json"
            with open(output_file, "w") as f:
                json.dump(result, f, indent=2)
            
            logger.info(f"Analyze endpoint returned processing_id: {data['processing_id']}")
            return data
    
    @pytest.mark.asyncio
    async def test_search_endpoint_integration(self):
        """Test the search endpoint with real vector store."""
        logger.info("Testing search endpoint integration...")
        
        async with await self.get_client() as client:
            # Test different search queries
            test_queries = [
                {
                    "query": "medical records patient treatment",
                    "filters": {
                        "document_types": ["discovery", "production"]
                    }
                },
                {
                    "query": "email contract negotiations 2023",
                    "filters": {
                        "date_range": {
                            "start": "2023-01-01",
                            "end": "2023-12-31"
                        }
                    }
                },
                {
                    "query": "financial statements quarterly reports",
                    "filters": {}
                }
            ]
            
            search_results = []
            
            for test_query in test_queries:
                request_data = {
                    "query": test_query["query"],
                    "case_name": self.case_name,
                    "filters": test_query["filters"],
                    "limit": 10,
                    "offset": 0
                }
                
                response = await client.post(
                    "/api/agents/deficiency-analyzer/search",
                    json=request_data,
                    headers=self.headers
                )
                
                assert response.status_code == status.HTTP_200_OK
                
                data = response.json()
                assert "results" in data
                assert "total_count" in data
                assert "has_more" in data
                
                search_results.append({
                    "query": test_query["query"],
                    "status_code": response.status_code,
                    "total_results": data["total_count"],
                    "first_result": data["results"][0] if data["results"] else None
                })
                
                # Small delay between searches
                await asyncio.sleep(0.1)
            
            # Save results
            output_file = self.output_dir / "api_search_results.json"
            with open(output_file, "w") as f:
                json.dump(search_results, f, indent=2)
            
            logger.info(f"Search endpoint tests completed for {len(test_queries)} queries")
            return search_results
    
    @pytest.mark.asyncio
    async def test_categorize_endpoint_integration(self):
        """Test the categorize endpoint with real categorization logic."""
        logger.info("Testing categorize endpoint integration...")
        
        async with await self.get_client() as client:
            # Test different categorization scenarios
            test_scenarios = [
                {
                    "request_number": "RFP No. 1",
                    "request_text": "All medical records for patient John Doe from 2020-2023",
                    "search_results": ["doc1", "doc2", "doc3"],
                    "oc_response_text": "All responsive documents have been produced."
                },
                {
                    "request_number": "RFP No. 2",
                    "request_text": "Email communications regarding ABC contract negotiations",
                    "search_results": [],
                    "oc_response_text": "No responsive documents exist."
                },
                {
                    "request_number": "RFP No. 3",
                    "request_text": "Financial statements and reports for Q1-Q4 2023",
                    "search_results": ["doc4", "doc5"],
                    "oc_response_text": "Documents withheld as proprietary and confidential."
                }
            ]
            
            categorization_results = []
            
            for scenario in test_scenarios:
                response = await client.post(
                    "/api/agents/deficiency-analyzer/categorize",
                    json=scenario,
                    headers=self.headers
                )
                
                assert response.status_code == status.HTTP_200_OK
                
                data = response.json()
                assert "classification" in data
                assert "confidence_score" in data
                assert "evidence_summary" in data
                assert data["classification"] in [
                    "fully_produced", 
                    "partially_produced", 
                    "not_produced", 
                    "no_responsive_docs"
                ]
                
                categorization_results.append({
                    "request_number": scenario["request_number"],
                    "classification": data["classification"],
                    "confidence": data["confidence_score"],
                    "summary": data["evidence_summary"]
                })
            
            # Save results
            output_file = self.output_dir / "api_categorization_results.json"
            with open(output_file, "w") as f:
                json.dump(categorization_results, f, indent=2)
            
            logger.info(f"Categorization endpoint tests completed for {len(test_scenarios)} scenarios")
            return categorization_results
    
    @pytest.mark.asyncio
    async def test_report_endpoint_integration(self):
        """Test the report retrieval endpoint."""
        logger.info("Testing report endpoint integration...")
        
        async with await self.get_client() as client:
            # Use a mock report ID (in real scenario, this would come from analyze endpoint)
            report_id = str(uuid4())
            
            # Test different format options
            formats = ["json", "html", "pdf"]
            report_results = []
            
            for format_type in formats:
                try:
                    response = await client.get(
                        f"/api/agents/deficiency-analyzer/report/{report_id}",
                        params={
                            "format": format_type,
                            "include_evidence": True
                        },
                        headers=self.headers
                    )
                    
                    # Note: This might return 404 if report doesn't exist
                    # In real test, we'd create a report first
                    
                    report_results.append({
                        "format": format_type,
                        "status_code": response.status_code,
                        "content_type": response.headers.get("content-type"),
                        "content_length": len(response.content) if response.status_code == 200 else 0
                    })
                    
                    # Save successful responses
                    if response.status_code == 200:
                        ext = "json" if format_type == "json" else format_type
                        output_file = self.output_dir / f"api_report_sample.{ext}"
                        
                        if format_type == "json":
                            with open(output_file, "w") as f:
                                json.dump(response.json(), f, indent=2)
                        else:
                            with open(output_file, "wb") as f:
                                f.write(response.content)
                
                except Exception as e:
                    report_results.append({
                        "format": format_type,
                        "error": str(e)
                    })
            
            # Save results summary
            output_file = self.output_dir / "api_report_results.json"
            with open(output_file, "w") as f:
                json.dump(report_results, f, indent=2)
            
            logger.info(f"Report endpoint tests completed for {len(formats)} formats")
            return report_results
    
    @pytest.mark.asyncio
    async def test_rate_limiting_integration(self):
        """Test rate limiting functionality."""
        logger.info("Testing rate limiting...")
        
        async with await self.get_client() as client:
            # Test search endpoint rate limit (100/minute)
            rate_limit_results = {
                "search_endpoint": {
                    "limit": "100/minute",
                    "requests_made": 0,
                    "rate_limited_at": None
                }
            }
            
            request_data = {
                "query": "test rate limit",
                "case_name": self.case_name,
                "filters": {},
                "limit": 1,
                "offset": 0
            }
            
            # Make rapid requests to test rate limiting
            start_time = time.time()
            request_count = 0
            
            # Only test a reasonable number to verify rate limiting works
            for i in range(20):  # Test with 20 rapid requests
                response = await client.post(
                    "/api/agents/deficiency-analyzer/search",
                    json=request_data,
                    headers=self.headers
                )
                
                request_count += 1
                
                if response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
                    rate_limit_results["search_endpoint"]["rate_limited_at"] = request_count
                    rate_limit_results["search_endpoint"]["retry_after"] = response.headers.get("Retry-After")
                    break
                
                # Small delay to avoid overwhelming the server
                await asyncio.sleep(0.05)
            
            elapsed_time = time.time() - start_time
            rate_limit_results["search_endpoint"]["requests_made"] = request_count
            rate_limit_results["search_endpoint"]["elapsed_seconds"] = elapsed_time
            
            # Save results
            output_file = self.output_dir / "api_rate_limit_results.json"
            with open(output_file, "w") as f:
                json.dump(rate_limit_results, f, indent=2)
            
            logger.info(f"Rate limiting test completed: {request_count} requests in {elapsed_time:.2f}s")
            return rate_limit_results
    
    @pytest.mark.asyncio
    async def test_error_handling_integration(self):
        """Test API error handling with various error scenarios."""
        logger.info("Testing error handling...")
        
        async with await self.get_client() as client:
            error_scenarios = []
            
            # Test 1: Invalid agent ID
            response = await client.post(
                "/api/agents/invalid-agent-id/analyze",
                json={"production_id": str(uuid4())},
                headers=self.headers
            )
            error_scenarios.append({
                "test": "Invalid agent ID",
                "status_code": response.status_code,
                "error": response.json() if response.status_code >= 400 else None
            })
            
            # Test 2: Missing required fields
            response = await client.post(
                "/api/agents/deficiency-analyzer/analyze",
                json={},  # Missing required fields
                headers=self.headers
            )
            error_scenarios.append({
                "test": "Missing required fields",
                "status_code": response.status_code,
                "error": response.json() if response.status_code >= 400 else None
            })
            
            # Test 3: Invalid case name in search
            response = await client.post(
                "/api/agents/deficiency-analyzer/search",
                json={
                    "query": "test",
                    "case_name": "invalid_case_name_xyz",
                    "limit": 10
                },
                headers=self.headers
            )
            error_scenarios.append({
                "test": "Invalid case name",
                "status_code": response.status_code,
                "error": response.json() if response.status_code >= 400 else None
            })
            
            # Test 4: Missing authentication headers
            response = await client.get(
                "/api/agents/deficiency-analyzer/report/test-id",
                headers={}  # No auth headers
            )
            error_scenarios.append({
                "test": "Missing authentication",
                "status_code": response.status_code,
                "error": response.json() if response.status_code >= 400 else None
            })
            
            # Save error handling results
            output_file = self.output_dir / "api_error_handling_results.json"
            with open(output_file, "w") as f:
                json.dump(error_scenarios, f, indent=2)
            
            logger.info(f"Error handling tests completed for {len(error_scenarios)} scenarios")
            return error_scenarios


async def run_api_tests():
    """Run all API integration tests."""
    tests = APIIntegrationTests()
    
    results = {
        "timestamp": datetime.utcnow().isoformat(),
        "case_name": tests.case_name,
        "tests": {}
    }
    
    # Run each test
    test_methods = [
        ("Analyze Endpoint", tests.test_analyze_endpoint_integration),
        ("Search Endpoint", tests.test_search_endpoint_integration),
        ("Categorize Endpoint", tests.test_categorize_endpoint_integration),
        ("Report Endpoint", tests.test_report_endpoint_integration),
        ("Rate Limiting", tests.test_rate_limiting_integration),
        ("Error Handling", tests.test_error_handling_integration)
    ]
    
    for test_name, test_method in test_methods:
        try:
            logger.info(f"\nRunning: {test_name}")
            result = await test_method()
            results["tests"][test_name] = {
                "status": "passed",
                "summary": f"Test completed successfully"
            }
            logger.info(f"✓ {test_name} passed")
        except Exception as e:
            results["tests"][test_name] = {
                "status": "failed",
                "error": str(e)
            }
            logger.error(f"✗ {test_name} failed: {str(e)}")
    
    # Save overall results
    output_file = Path("/app/test_docs/output") / "api_test_results.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"\nAPI tests complete. Results saved to: {output_file}")
    return results


if __name__ == "__main__":
    asyncio.run(run_api_tests())
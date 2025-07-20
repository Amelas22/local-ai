"""
Simplified E2E test for deficiency analyzer focusing on core functionality.

Tests:
1. Parse first 3 RTP requests
2. Search for chunks in Qdrant database
3. Basic categorization logic
"""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
from uuid import uuid4

# Setup path
import sys

sys.path.append("/app")

from src.document_processing.rtp_parser import RTPParser
from src.vector_storage.qdrant_store import QdrantVectorStore
from src.vector_storage.embeddings import EmbeddingGenerator
from src.utils.logger import get_logger

logger = get_logger("e2e_test_simple")


class SimpleE2ETest:
    """Simplified E2E test focusing on core functionality."""

    def __init__(self):
        self.case_name = "story1_4_test_database_bb623c92"
        self.rtp_path = "/app/test_docs/RTP.pdf"
        self.output_dir = "/app/test_docs/output"
        self.vector_store = QdrantVectorStore()
        self.embedding_generator = EmbeddingGenerator()

        # Create output directory
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)

    async def test_workflow(self) -> Dict[str, Any]:
        """Run simplified test workflow."""
        test_id = str(uuid4())
        timestamp = datetime.utcnow().isoformat()

        logger.info(f"Starting simplified E2E test {test_id}")

        results = {
            "test_id": test_id,
            "timestamp": timestamp,
            "case_name": self.case_name,
            "steps": {},
        }

        try:
            # Step 1: Verify prerequisites
            logger.info("Step 1: Verifying prerequisites...")
            prereq_results = self._verify_prerequisites()
            results["steps"]["prerequisites"] = prereq_results

            # Step 2: Parse RTP (first 3 requests)
            logger.info("Step 2: Parsing RTP document...")
            rtp_results = await self._parse_rtp()
            results["steps"]["rtp_parsing"] = rtp_results

            # Step 3: Search for chunks
            logger.info("Step 3: Searching for chunks in database...")
            search_results = await self._search_chunks(rtp_results["requests"])
            results["steps"]["chunk_search"] = search_results

            # Step 4: Basic categorization
            logger.info("Step 4: Categorizing requests...")
            categorization_results = self._categorize_requests(
                rtp_results["requests"], search_results["searches"]
            )
            results["steps"]["categorization"] = categorization_results

            results["status"] = "SUCCESS"
            logger.info("Test completed successfully!")

        except Exception as e:
            results["status"] = "FAILED"
            results["error"] = str(e)
            logger.error(f"Test failed: {e}")
            raise

        finally:
            # Save results
            self._save_results(results)

        return results

    def _verify_prerequisites(self) -> Dict[str, Any]:
        """Verify test prerequisites."""
        results = {}

        # Check RTP file
        results["rtp_file_exists"] = os.path.exists(self.rtp_path)
        if not results["rtp_file_exists"]:
            raise FileNotFoundError(f"RTP file not found: {self.rtp_path}")

        # Check Qdrant collection
        cases = self.vector_store.list_cases()
        case_names = [case.get("collection_name", "") for case in cases]
        results["collection_exists"] = self.case_name in case_names

        if results["collection_exists"]:
            collection_info = next(
                (
                    case
                    for case in cases
                    if case.get("collection_name") == self.case_name
                ),
                None,
            )
            if collection_info:
                results["document_count"] = collection_info.get("points_count", 0)
                logger.info(
                    f"Found {results['document_count']} documents in collection"
                )
        else:
            raise ValueError(f"Qdrant collection not found: {self.case_name}")

        return results

    async def _parse_rtp(self) -> Dict[str, Any]:
        """Parse RTP document and extract first 3 requests."""
        results = {"parse_time_start": datetime.utcnow().isoformat()}

        try:
            # Parse RTP
            rtp_parser = RTPParser(case_name=self.case_name)
            all_requests = await rtp_parser.parse_rtp_document(self.rtp_path)

            # Take only first 3 requests
            requests = all_requests[:3]

            results["parse_time_end"] = datetime.utcnow().isoformat()
            results["total_requests_found"] = len(all_requests)
            results["requests_tested"] = len(requests)
            results["requests"] = [
                {
                    "request_number": req.request_number,
                    "request_text": req.request_text[:200] + "..."
                    if len(req.request_text) > 200
                    else req.request_text,
                    "category": req.category.value
                    if hasattr(req.category, "value")
                    else str(req.category),
                }
                for req in requests
            ]

            logger.info(f"Testing {len(requests)} out of {len(all_requests)} requests")

        except Exception as e:
            results["error"] = str(e)
            raise

        return results

    async def _search_chunks(self, requests: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Search for chunks related to each request."""
        results = {"search_time_start": datetime.utcnow().isoformat(), "searches": []}

        for request in requests:
            search_result = {
                "request_number": request["request_number"],
                "query": request["request_text"][:100] + "...",
            }

            try:
                # Generate embedding for the actual request
                # Truncate very long requests to avoid embedding issues
                query_text = (
                    request["request_text"][:500]
                    if len(request["request_text"]) > 500
                    else request["request_text"]
                )
                query_embedding, _ = self.embedding_generator.generate_embedding(
                    query_text
                )

                # Use regular search_documents method with low threshold
                chunks = self.vector_store.search_documents(
                    collection_name=self.case_name,
                    query_embedding=query_embedding,
                    limit=10,
                    threshold=0.3,  # Moderate threshold
                )

                logger.info(
                    f"Request {request['request_number']}: Searched with truncated query, found {len(chunks)} chunks"
                )

                search_result["chunks_found"] = len(chunks)
                search_result["chunks"] = []

                # Extract chunk details
                for chunk in chunks:
                    # Handle different result formats
                    if hasattr(chunk, "payload"):
                        chunk_info = {
                            "score": getattr(chunk, "score", 0),
                            "document_name": chunk.payload.get(
                                "document_name", "unknown"
                            ),
                            "page_number": chunk.payload.get("page_number", "unknown"),
                            "chunk_preview": chunk.payload.get("text", "")[:150] + "..."
                            if len(chunk.payload.get("text", "")) > 150
                            else chunk.payload.get("text", ""),
                        }
                    else:
                        chunk_info = {
                            "score": getattr(chunk, "relevance_score", 0),
                            "document_name": chunk.get("document_name", "unknown")
                            if isinstance(chunk, dict)
                            else "unknown",
                            "page_number": chunk.get("page_number", "unknown")
                            if isinstance(chunk, dict)
                            else "unknown",
                            "chunk_preview": str(chunk)[:150] + "...",
                        }
                    search_result["chunks"].append(chunk_info)

                # Get unique documents
                doc_names = list(
                    set([c["document_name"] for c in search_result["chunks"]])
                )
                search_result["unique_documents"] = doc_names

                logger.info(
                    f"Request {request['request_number']}: Found {len(chunks)} chunks from {len(doc_names)} documents"
                )

            except Exception as e:
                search_result["error"] = str(e)
                logger.error(
                    f"Search failed for request {request['request_number']}: {e}"
                )

            results["searches"].append(search_result)

        results["search_time_end"] = datetime.utcnow().isoformat()
        return results

    def _categorize_requests(
        self, requests: List[Dict[str, Any]], searches: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Basic categorization based on search results."""
        results = {
            "categorization_time_start": datetime.utcnow().isoformat(),
            "categorizations": [],
        }

        for request, search in zip(requests, searches):
            categorization = {
                "request_number": request["request_number"],
                "chunks_found": search.get("chunks_found", 0),
                "documents_found": len(search.get("unique_documents", [])),
            }

            # Simple categorization logic
            if search.get("error"):
                categorization["category"] = "ERROR"
                categorization["confidence"] = 0.0
            elif search.get("chunks_found", 0) == 0:
                categorization["category"] = "NOT_PRODUCED"
                categorization["confidence"] = 0.9
                categorization["reasoning"] = (
                    "No responsive documents found in production"
                )
            elif search.get("chunks_found", 0) < 3:
                categorization["category"] = "PARTIALLY_PRODUCED"
                categorization["confidence"] = 0.7
                categorization["reasoning"] = (
                    f"Found {search['chunks_found']} potentially responsive chunks"
                )
            else:
                categorization["category"] = "FULLY_PRODUCED"
                categorization["confidence"] = 0.8
                categorization["reasoning"] = (
                    f"Found {search['chunks_found']} responsive chunks from {len(search.get('unique_documents', []))} documents"
                )

            results["categorizations"].append(categorization)
            logger.info(
                f"Request {request['request_number']}: {categorization['category']} (confidence: {categorization['confidence']})"
            )

        results["categorization_time_end"] = datetime.utcnow().isoformat()
        return results

    def _save_results(self, results: Dict[str, Any]):
        """Save test results to file."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

        # Save JSON results
        json_path = os.path.join(
            self.output_dir, f"simple_e2e_results_{timestamp}.json"
        )
        with open(json_path, "w") as f:
            json.dump(results, f, indent=2, default=str)

        # Save summary
        summary_path = os.path.join(
            self.output_dir, f"simple_e2e_summary_{timestamp}.txt"
        )
        with open(summary_path, "w") as f:
            f.write("Simple E2E Test Summary\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Test ID: {results.get('test_id', 'N/A')}\n")
            f.write(f"Timestamp: {results.get('timestamp', 'N/A')}\n")
            f.write(f"Status: {results.get('status', 'UNKNOWN')}\n")
            f.write(f"Case: {results.get('case_name', 'N/A')}\n\n")

            if "steps" in results:
                # Prerequisites
                if "prerequisites" in results["steps"]:
                    prereq = results["steps"]["prerequisites"]
                    f.write("Prerequisites:\n")
                    f.write(
                        f"  - RTP file exists: {prereq.get('rtp_file_exists', False)}\n"
                    )
                    f.write(
                        f"  - Collection exists: {prereq.get('collection_exists', False)}\n"
                    )
                    f.write(
                        f"  - Document count: {prereq.get('document_count', 0)}\n\n"
                    )

                # RTP Parsing
                if "rtp_parsing" in results["steps"]:
                    rtp = results["steps"]["rtp_parsing"]
                    f.write("RTP Parsing:\n")
                    f.write(
                        f"  - Total requests found: {rtp.get('total_requests_found', 0)}\n"
                    )
                    f.write(f"  - Requests tested: {rtp.get('requests_tested', 0)}\n\n")

                # Categorization
                if "categorization" in results["steps"]:
                    cats = results["steps"]["categorization"]["categorizations"]
                    f.write("Categorization Results:\n")
                    for cat in cats:
                        f.write(
                            f"  - Request {cat['request_number']}: {cat['category']} "
                        )
                        f.write(f"(confidence: {cat.get('confidence', 0):.2f}, ")
                        f.write(f"chunks: {cat.get('chunks_found', 0)})\n")

            if "error" in results:
                f.write(f"\nError: {results['error']}\n")

        logger.info(f"Results saved to: {json_path}")
        logger.info(f"Summary saved to: {summary_path}")


async def main():
    """Run the simplified E2E test."""
    test = SimpleE2ETest()
    results = await test.test_workflow()

    print("\n" + "=" * 60)
    print("SIMPLE E2E TEST RESULTS")
    print("=" * 60)
    print(f"Status: {results['status']}")
    print(f"Test ID: {results['test_id']}")

    if results["status"] == "SUCCESS":
        cats = results["steps"]["categorization"]["categorizations"]
        print("\nCategorization Summary:")
        for cat in cats:
            print(
                f"  Request {cat['request_number']}: {cat['category']} (chunks: {cat['chunks_found']})"
            )
    else:
        print(f"\nError: {results.get('error', 'Unknown error')}")

    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

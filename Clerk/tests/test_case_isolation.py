"""
Comprehensive test suite for case isolation in the Clerk legal AI system
Ensures complete data separation between different legal matters
"""

import pytest
import asyncio

from src.models.fact_models import CaseIsolationConfig
from src.ai_agents.fact_extractor import FactExtractor
from src.document_processing.deposition_parser import DepositionParser
from src.document_processing.exhibit_indexer import ExhibitIndexer
from src.utils.timeline_generator import TimelineGenerator
from src.ai_agents.evidence_mapper import EvidenceMapper
from src.ai_agents.enhanced_rag_agent import (
    EnhancedRAGResearchAgent,
    EnhancedResearchRequest,
)
from src.vector_storage.qdrant_store import QdrantVectorStore


class TestCaseIsolation:
    """Test suite for verifying case isolation across all components"""

    @pytest.fixture
    def case_a_name(self):
        """Test case A name"""
        return "Smith_v_Jones_2024"

    @pytest.fixture
    def case_b_name(self):
        """Test case B name"""
        return "Doe_v_Roe_2024"

    @pytest.fixture
    def vector_store(self):
        """Vector store instance"""
        return QdrantVectorStore()

    @pytest.fixture
    def sample_document(self):
        """Sample document content"""
        return """
        On January 15, 2024, the defendant's vehicle collided with the plaintiff's car.
        The defendant testified in his deposition at page 45, line 12 that he was 
        checking his phone at the time. Exhibit A shows photos of the damage.
        """

    async def test_fact_extractor_isolation(
        self, case_a_name, case_b_name, sample_document
    ):
        """Test that fact extractors only access their assigned case"""
        # Create extractors for different cases
        extractor_a = FactExtractor(case_a_name)
        extractor_b = FactExtractor(case_b_name)

        # Extract facts for case A
        facts_a = await extractor_a.extract_facts_from_document("doc1", sample_document)

        # Try to search case A facts from case B extractor
        # This should return no results
        search_results = await extractor_b.search_facts("collision")

        assert len(search_results) == 0, "Case B extractor found Case A facts!"

        # Verify case A can find its own facts
        case_a_results = await extractor_a.search_facts("collision")
        assert len(case_a_results) > 0, "Case A cannot find its own facts"

        # Verify all facts have correct case name
        for fact in facts_a.facts:
            assert fact.case_name == case_a_name

    async def test_deposition_parser_isolation(
        self, case_a_name, case_b_name, sample_document
    ):
        """Test that deposition parsers maintain case isolation"""
        # Create parsers for different cases
        parser_a = DepositionParser(case_a_name)
        parser_b = DepositionParser(case_b_name)

        # Parse deposition for case A
        depositions_a = await parser_a.parse_deposition("depo1.pdf", sample_document)

        # Try to search case A depositions from case B parser
        search_results = await parser_b.search_testimony("phone")

        assert len(search_results) == 0, "Case B parser found Case A depositions!"

        # Verify case A can find its own depositions
        case_a_results = await parser_a.search_testimony("phone")
        assert len(case_a_results) > 0, "Case A cannot find its own depositions"

    async def test_exhibit_indexer_isolation(
        self, case_a_name, case_b_name, sample_document
    ):
        """Test that exhibit indexers maintain case isolation"""
        # Create indexers for different cases
        indexer_a = ExhibitIndexer(case_a_name)
        indexer_b = ExhibitIndexer(case_b_name)

        # Index exhibits for case A
        exhibits_a = await indexer_a.index_document_exhibits(
            "doc1.pdf", sample_document
        )

        # Try to search case A exhibits from case B indexer
        search_results = await indexer_b.search_exhibits("photos")

        assert len(search_results) == 0, "Case B indexer found Case A exhibits!"

        # Verify case A can find its own exhibits
        case_a_results = await indexer_a.search_exhibits("photos")
        assert len(case_a_results) > 0, "Case A cannot find its own exhibits"

    async def test_timeline_generator_isolation(self, case_a_name, case_b_name):
        """Test that timeline generators respect case boundaries"""
        # Create timeline generators
        timeline_a = TimelineGenerator(case_a_name)
        timeline_b = TimelineGenerator(case_b_name)

        # Generate timeline for case A
        # (Assuming facts were already extracted)
        timeline_data_a = await timeline_a.generate_timeline()

        # Case B timeline should be empty
        timeline_data_b = await timeline_b.generate_timeline()

        assert len(timeline_data_b.timeline_events) == 0, (
            "Case B has Case A timeline events!"
        )

    async def test_evidence_mapper_isolation(self, case_a_name, case_b_name):
        """Test that evidence mapper respects case boundaries"""
        # Create evidence mappers
        mapper_a = EvidenceMapper(case_a_name)
        mapper_b = EvidenceMapper(case_b_name)

        # Try to find evidence from case B mapper
        evidence = await mapper_b.find_supporting_evidence(
            "defendant was negligent", limit=10
        )

        # Should not find any evidence from case A
        assert len(evidence) == 0, "Case B mapper found Case A evidence!"

        # Verify evidence items have correct case name
        for item in evidence:
            assert mapper_b.validate_case_isolation(item), (
                "Evidence item has wrong case!"
            )

    async def test_rag_agent_isolation(self, case_a_name, case_b_name):
        """Test that RAG agent maintains case isolation"""
        rag_agent = EnhancedRAGResearchAgent()

        # Create research request for case A
        request_a = EnhancedResearchRequest(
            questions=["What evidence shows negligence?"],
            case_name=case_a_name,
            research_context="Looking for evidence of negligent driving",
        )

        # Perform research
        response_a = await rag_agent.research(request_a)

        # Verify case isolation
        assert response_a.case_isolation_verified, "Case isolation verification failed!"

        # All case-specific results should be from case A
        for fact in response_a.case_facts:
            assert case_a_name in str(fact.get("metadata", {})), "Wrong case in facts!"

    async def test_collection_naming_security(self, vector_store):
        """Test that collection names are secure and prevent injection"""
        # Test dangerous case names
        dangerous_names = [
            "case*",  # Wildcard
            "case[1-9]",  # Regex pattern
            "case{test}",  # Template
            "../other_case",  # Path traversal
            "case; DROP TABLE",  # SQL injection attempt
        ]

        for dangerous_name in dangerous_names:
            with pytest.raises(ValueError):
                # Should raise error on dangerous names
                FactExtractor(dangerous_name)

    async def test_shared_knowledge_access(self, case_a_name, case_b_name):
        """Test that both cases can access shared knowledge"""
        rag_agent = EnhancedRAGResearchAgent()

        # Research request for case A
        request_a = EnhancedResearchRequest(
            questions=["What does Florida statute 768.81 say about comparative fault?"],
            case_name=case_a_name,
            research_context="Researching comparative fault law",
        )

        # Research request for case B
        request_b = EnhancedResearchRequest(
            questions=["What does Florida statute 768.81 say about comparative fault?"],
            case_name=case_b_name,
            research_context="Researching comparative fault law",
        )

        # Both should find the same statute
        response_a = await rag_agent.research(request_a)
        response_b = await rag_agent.research(request_b)

        assert len(response_a.florida_statutes) > 0, (
            "Case A cannot access shared statutes"
        )
        assert len(response_b.florida_statutes) > 0, (
            "Case B cannot access shared statutes"
        )

        # Verify same statute content
        if response_a.florida_statutes and response_b.florida_statutes:
            assert (
                response_a.florida_statutes[0]["citation"]
                == response_b.florida_statutes[0]["citation"]
            )

    async def test_isolation_config_validation(self, case_a_name):
        """Test case isolation configuration validation"""
        config = CaseIsolationConfig(case_name=case_a_name)

        # Test valid collection access
        assert config.validate_collection_access(f"{case_a_name}_facts")
        assert config.validate_collection_access("florida_statutes")

        # Test invalid collection access
        assert not config.validate_collection_access("other_case_facts")
        assert not config.validate_collection_access("random_collection")

    async def test_audit_trail(self, case_a_name, vector_store):
        """Test that case access is properly audited"""
        # This would test audit logging functionality
        # Implementation depends on your audit system
        pass

    def test_performance_impact(self, case_a_name):
        """Test that isolation doesn't significantly impact performance"""
        import time

        # Time fact extraction with isolation
        start = time.time()
        extractor = FactExtractor(case_a_name)
        isolation_time = time.time() - start

        # Isolation overhead should be minimal
        assert isolation_time < 0.1, f"Isolation adds {isolation_time}s overhead"


class TestCaseIsolationIntegration:
    """Integration tests for case isolation across the full system"""

    async def test_full_pipeline_isolation(
        self, case_a_name, case_b_name, sample_document
    ):
        """Test isolation through complete document processing pipeline"""
        # Process document for case A
        extractor_a = FactExtractor(case_a_name)
        parser_a = DepositionParser(case_a_name)
        indexer_a = ExhibitIndexer(case_a_name)

        # Extract all evidence types
        facts_a = await extractor_a.extract_facts_from_document("doc1", sample_document)
        depos_a = await parser_a.parse_deposition("doc1", sample_document)
        exhibits_a = await indexer_a.index_document_exhibits("doc1", sample_document)

        # Create case B extractors
        extractor_b = FactExtractor(case_b_name)
        parser_b = DepositionParser(case_b_name)
        indexer_b = ExhibitIndexer(case_b_name)

        # Case B should not see any case A data
        facts_b = await extractor_b.search_facts("collision")
        depos_b = await parser_b.search_testimony("phone")
        exhibits_b = await indexer_b.search_exhibits("photos")

        assert len(facts_b) == 0, "Case isolation breach in facts!"
        assert len(depos_b) == 0, "Case isolation breach in depositions!"
        assert len(exhibits_b) == 0, "Case isolation breach in exhibits!"

    async def test_motion_drafting_isolation(self, case_a_name, case_b_name):
        """Test that motion drafting respects case boundaries"""
        # This would test the motion drafter with case isolation
        # Implementation depends on motion drafter integration
        pass


# Fixtures for pytest


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.mark.asyncio
async def test_isolation_suite():
    """Run the complete isolation test suite"""
    test = TestCaseIsolation()

    # Run critical isolation tests
    await test.test_fact_extractor_isolation("Case_A", "Case_B", "Test document")
    await test.test_deposition_parser_isolation("Case_A", "Case_B", "Test document")
    await test.test_exhibit_indexer_isolation("Case_A", "Case_B", "Test document")

    print("✓ All case isolation tests passed!")


if __name__ == "__main__":
    # Run tests
    asyncio.run(test_isolation_suite())

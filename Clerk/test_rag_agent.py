"""
Test script for the RAG Research Agent
"""

import asyncio
import logging
from src.ai_agents.rag_research_agent import rag_research_agent, ResearchRequest

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_rag_agent():
    """Test the RAG research agent with sample questions"""
    
    # Sample questions like those generated from outline
    test_questions = [
        "What dispatch records show about telematics overrides during peak seasons?",
        "How do successful motions argue negligent hiring claims in trucking cases?",
        "What evidence exists about brake failure tickets and maintenance issues?",
        "What legal precedents support employer liability separate from driver liability?",
        "What FMCSR violations or compliance issues are documented in the case?"
    ]
    
    try:
        logger.info("Testing RAG Research Agent")
        
        # Create research request
        request = ResearchRequest(
            questions=test_questions,
            database_name="test_case_database",
            research_context="Testing RAG agent query optimization and database selection",
            section_type="argument"
        )
        
        logger.info(f"Created research request with {len(test_questions)} questions")
        
        # Execute research
        response = await rag_research_agent.research_questions(request)
        
        # Display results
        logger.info(f"Research completed!")
        logger.info(f"Summary: {response.research_summary}")
        logger.info(f"Total results: {response.total_results}")
        
        categories = [
            ("Legal Precedents", response.legal_precedents),
            ("Case Facts", response.case_facts),
            ("Expert Evidence", response.expert_evidence),
            ("Regulatory Compliance", response.regulatory_compliance),
            ("Procedural History", response.procedural_history),
            ("Argument Strategies", response.argument_strategies)
        ]
        
        for category_name, results in categories:
            logger.info(f"{category_name}: {len(results)} results")
            for i, result in enumerate(results[:2]):  # Show first 2 results
                logger.info(f"  {i+1}. Score: {result['score']:.3f}, Source: {result['source']}")
                logger.info(f"     Content: {result['content'][:100]}...")
        
        logger.info("RAG Agent test completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"RAG Agent test failed: {str(e)}", exc_info=True)
        return False

if __name__ == "__main__":
    success = asyncio.run(test_rag_agent())
    if success:
        print("✅ RAG Agent test passed!")
    else:
        print("❌ RAG Agent test failed!")
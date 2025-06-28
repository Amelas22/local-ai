"""
Test script to debug motion drafter issues
Run this to test the motion drafting functionality in isolation
"""

import asyncio
import logging
import json
from datetime import datetime
from src.ai_agents.motion_drafter import motion_drafter, DocumentLength

# Configure logging to see all debug messages
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_motion_drafter():
    """Test the motion drafter with a simple outline"""
    
    # Create a simple test outline
    test_outline = {
        "title": "Motion to Dismiss - Test Case",
        "case_name": "Test v. Demo",
        "themes": ["negligence", "causation", "damages"],
        "sections": [
            {
                "title": "Introduction",
                "points": [
                    "This motion seeks dismissal of plaintiff's claims",
                    "Plaintiff has failed to state a claim upon which relief can be granted",
                    "The complaint lacks factual allegations supporting essential elements"
                ],
                "authorities": [
                    "Fed. R. Civ. P. 12(b)(6)",
                    "Bell Atlantic Corp. v. Twombly, 550 U.S. 544 (2007)",
                    "Ashcroft v. Iqbal, 556 U.S. 662 (2009)"
                ]
            },
            {
                "title": "Statement of Facts",
                "points": [
                    "Plaintiff alleges negligence in facility maintenance",
                    "Incident occurred on January 15, 2024",
                    "No specific facts support breach of duty"
                ],
                "authorities": []
            },
            {
                "title": "Legal Standard",
                "points": [
                    "Motion to dismiss standard under Rule 12(b)(6)",
                    "Complaint must contain sufficient factual matter",
                    "Court accepts factual allegations as true but not legal conclusions"
                ],
                "authorities": [
                    "Fed. R. Civ. P. 12(b)(6)",
                    "Twombly, 550 U.S. at 555",
                    "Iqbal, 556 U.S. at 678"
                ]
            },
            {
                "title": "Argument: Plaintiff Fails to Allege Duty",
                "points": [
                    "No allegations establishing defendant owed duty to plaintiff",
                    "Mere presence on premises insufficient",
                    "No special relationship alleged"
                ],
                "authorities": [
                    "Restatement (Second) of Torts § 314",
                    "Harper v. Herman, 499 N.W.2d 472 (Minn. 1993)"
                ]
            },
            {
                "title": "Conclusion",
                "points": [
                    "Complaint fails to state a claim",
                    "Dismissal with prejudice is appropriate",
                    "No amendment could cure deficiencies"
                ],
                "authorities": []
            }
        ]
    }
    
    logger.info("Starting motion drafter test")
    logger.info(f"Outline: {json.dumps(test_outline, indent=2)}")
    
    try:
        # Test the motion drafter
        result = await motion_drafter.draft_motion(
            outline=test_outline,
            database_name="cerrito_v_demo",
            target_length=DocumentLength.SHORT,
            motion_title="Motion to Dismiss for Failure to State a Claim"
        )
        
        logger.info("Motion drafting completed successfully!")
        logger.info(f"Total words: {result.total_word_count}")
        logger.info(f"Total pages: {result.total_page_estimate}")
        logger.info(f"Sections drafted: {len(result.sections)}")
        logger.info(f"Quality score: {result.coherence_score}")
        
        # Print first section as sample
        if result.sections:
            first_section = result.sections[0]
            logger.info(f"\nFirst section preview:")
            logger.info(f"Title: {first_section.outline_section.title}")
            logger.info(f"Word count: {first_section.word_count}")
            logger.info(f"Content preview: {first_section.content[:500]}...")
        
        return result
        
    except Exception as e:
        logger.error(f"Error in motion drafter test: {str(e)}", exc_info=True)
        raise


async def test_simple_agent_call():
    """Test a simple agent call to verify AI connectivity"""
    
    logger.info("Testing simple AI agent call")
    
    try:
        # Test the section writer agent directly
        simple_prompt = "Write a one paragraph introduction for a motion to dismiss."
        
        result = await motion_drafter.section_writer.run(simple_prompt)
        
        logger.info(f"AI agent responded successfully!")
        logger.info(f"Response: {str(result)[:200]}...")
        
        return result
        
    except Exception as e:
        logger.error(f"Error in simple agent test: {str(e)}", exc_info=True)
        raise


async def main():
    """Run tests"""
    
    print("=" * 60)
    print("MOTION DRAFTER TEST SUITE")
    print("=" * 60)
    
    # Test 1: Simple agent connectivity
    print("\n1. Testing AI agent connectivity...")
    try:
        await test_simple_agent_call()
        print("✓ AI agent connectivity test passed")
    except Exception as e:
        print(f"✗ AI agent connectivity test failed: {e}")
        return
    
    # Test 2: Full motion drafting
    print("\n2. Testing full motion drafting...")
    try:
        result = await test_motion_drafter()
        print("✓ Motion drafting test passed")
        
        # Save result to file for inspection
        output_file = f"test_motion_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w') as f:
            json.dump({
                "title": result.title,
                "case_name": result.case_name,
                "total_words": result.total_word_count,
                "total_pages": result.total_page_estimate,
                "quality_score": result.coherence_score,
                "sections": [
                    {
                        "title": s.outline_section.title,
                        "word_count": s.word_count,
                        "confidence_score": s.confidence_score
                    }
                    for s in result.sections
                ]
            }, f, indent=2)
        
        print(f"Results saved to: {output_file}")
        
    except Exception as e:
        print(f"✗ Motion drafting test failed: {e}")
    
    print("\n" + "=" * 60)
    print("TEST SUITE COMPLETED")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
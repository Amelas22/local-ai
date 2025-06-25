"""
Integration module for outline drafting and document conversion services
"""

import aiohttp
import asyncio
import json
import logging
from typing import Dict, Any, Optional, BinaryIO
from io import BytesIO
from datetime import datetime
from pathlib import Path

from src.utils.logger import get_logger

logger = get_logger(__name__)


class OutlineServices:
    """Client for interacting with outline drafting and conversion services"""
    
    def __init__(
        self,
        outline_drafter_url: str = "http://localhost:8001",
        docx_converter_url: str = "http://localhost:8000",
        timeout: int = 600
    ):
        """
        Initialize the outline services client.
        
        Args:
            outline_drafter_url: URL for the outline drafting service
            docx_converter_url: URL for the DOCX conversion service
            timeout: Request timeout in seconds
        """
        self.outline_drafter_url = outline_drafter_url.rstrip('/')
        self.docx_converter_url = docx_converter_url.rstrip('/')
        self.timeout = aiohttp.ClientTimeout(total=timeout)
    
    async def generate_outline(
        self,
        motion_text: str,
        counter_arguments: str,
        reasoning_effort: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a legal outline using the OpenAI o3 model.
        
        Args:
            motion_text: The opposing counsel's motion text
            counter_arguments: Our counter arguments and facts
            reasoning_effort: Optional reasoning effort level (low/medium/high)
            
        Returns:
            Dictionary containing the generated outline and metadata
            
        Raises:
            Exception: If the API call fails
        """
        logger.info(f"Generating legal outline with effort: {reasoning_effort or 'default'}")
        
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            try:
                request_data = {
                    "motion_text": motion_text,
                    "counter_arguments": counter_arguments
                }
                
                if reasoning_effort:
                    request_data["reasoning_effort"] = reasoning_effort
                
                async with session.post(
                    f"{self.outline_drafter_url}/generate-outline",
                    json=request_data
                ) as response:
                    result = await response.json()
                    
                    if response.status != 200:
                        raise Exception(f"API error: {result.get('error', 'Unknown error')}")
                    
                    if not result.get('success'):
                        raise Exception(f"Outline generation failed: {result.get('error')}")
                    
                    logger.info(f"Outline generated successfully. Tokens used: {result['metadata'].get('total_tokens', 'N/A')}, Effort: {result['metadata'].get('reasoning_effort', 'N/A')}")
                    return result
                    
            except asyncio.TimeoutError:
                logger.error("Outline generation timed out")
                raise Exception("Outline generation timed out after 10 minutes")
            except Exception as e:
                logger.error(f"Error generating outline: {e}")
                raise
    
    async def convert_outline_to_docx(
        self,
        outline_data: Dict[str, Any]
    ) -> bytes:
        """
        Convert a JSON outline to a DOCX document.
        
        Args:
            outline_data: The outline data in JSON format
            
        Returns:
            Bytes of the DOCX file
            
        Raises:
            Exception: If the conversion fails
        """
        logger.info("Converting outline to DOCX...")
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    f"{self.docx_converter_url}/generate-outline/",
                    json=outline_data
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"DOCX conversion failed: {error_text}")
                    
                    docx_bytes = await response.read()
                    logger.info("Outline converted to DOCX successfully")
                    return docx_bytes
                    
            except Exception as e:
                logger.error(f"Error converting to DOCX: {e}")
                raise
    
    async def parse_docx_to_outline(
        self,
        docx_file: BinaryIO,
        filename: str = "outline.docx"
    ) -> Dict[str, Any]:
        """
        Parse a DOCX file back to JSON outline format.
        
        Args:
            docx_file: File-like object containing the DOCX data
            filename: Name of the file
            
        Returns:
            Dictionary containing the parsed outline
            
        Raises:
            Exception: If the parsing fails
        """
        logger.info(f"Parsing DOCX file: {filename}")
        
        async with aiohttp.ClientSession() as session:
            try:
                # Prepare multipart form data
                data = aiohttp.FormData()
                data.add_field(
                    'file',
                    docx_file,
                    filename=filename,
                    content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                )
                
                async with session.post(
                    f"{self.docx_converter_url}/parse-outline/",
                    data=data
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"DOCX parsing failed: {error_text}")
                    
                    outline_data = await response.json()
                    logger.info("DOCX parsed to outline successfully")
                    return outline_data
                    
            except Exception as e:
                logger.error(f"Error parsing DOCX: {e}")
                raise
    
    async def parse_docx_sections(
        self,
        docx_file: BinaryIO,
        filename: str = "outline.docx"
    ) -> Dict[str, Any]:
        """
        Parse a DOCX file into sections for sequential processing.
        
        Args:
            docx_file: File-like object containing the DOCX data
            filename: Name of the file
            
        Returns:
            Dictionary containing the parsed sections
            
        Raises:
            Exception: If the parsing fails
        """
        logger.info(f"Parsing DOCX file into sections: {filename}")
        
        async with aiohttp.ClientSession() as session:
            try:
                # Prepare multipart form data
                data = aiohttp.FormData()
                data.add_field(
                    'file',
                    docx_file,
                    filename=filename,
                    content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                )
                
                async with session.post(
                    f"{self.docx_converter_url}/parse-outline-sections/",
                    data=data
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"DOCX section parsing failed: {error_text}")
                    
                    sections_data = await response.json()
                    logger.info("DOCX parsed into sections successfully")
                    return sections_data
                    
            except Exception as e:
                logger.error(f"Error parsing DOCX sections: {e}")
                raise
    
    async def validate_outline(
        self,
        outline_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate an outline to ensure it has all required sections.
        
        Args:
            outline_data: The outline data to validate
            
        Returns:
            Dictionary containing validation results
        """
        logger.info("Validating outline structure...")
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    f"{self.outline_drafter_url}/validate-outline",
                    json=outline_data
                ) as response:
                    validation_result = await response.json()
                    
                    if validation_result['valid']:
                        logger.info("Outline validation passed")
                    else:
                        logger.warning(f"Outline validation failed: {validation_result}")
                    
                    return validation_result
                    
            except Exception as e:
                logger.error(f"Error validating outline: {e}")
                raise
    
    async def get_model_info(self) -> Dict[str, Any]:
        """Get information about the AI model being used"""
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    f"{self.outline_drafter_url}/model-info"
                ) as response:
                    return await response.json()
            except Exception as e:
                logger.error(f"Error getting model info: {e}")
                raise
    
    async def complete_outline_workflow(
        self,
        motion_text: str,
        counter_arguments: str,
        output_path: Optional[Path] = None,
        reasoning_effort: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Complete workflow: generate outline and convert to DOCX.
        
        Args:
            motion_text: The opposing counsel's motion text
            counter_arguments: Our counter arguments and facts
            output_path: Optional path to save the DOCX file
            reasoning_effort: Optional reasoning effort level (low/medium/high)
            
        Returns:
            Dictionary containing the outline and file path
        """
        logger.info("Starting complete outline workflow...")
        
        # Generate the outline
        outline_result = await self.generate_outline(
            motion_text, counter_arguments, reasoning_effort
        )
        outline_data = outline_result['outline']
        
        # Validate the outline
        validation = await self.validate_outline(outline_data)
        if not validation['valid']:
            logger.warning(f"Outline validation issues: {validation}")
        
        # Convert to DOCX
        docx_bytes = await self.convert_outline_to_docx(outline_data)
        
        # Save if path provided
        saved_path = None
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Generate filename with timestamp if directory provided
            if output_path.is_dir():
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"legal_outline_{timestamp}.docx"
                output_path = output_path / filename
            
            output_path.write_bytes(docx_bytes)
            saved_path = str(output_path)
            logger.info(f"Outline saved to: {saved_path}")
        
        return {
            "outline": outline_data,
            "metadata": outline_result['metadata'],
            "validation": validation,
            "docx_bytes": docx_bytes,
            "saved_path": saved_path
        }


# Example usage
async def example_usage():
    """Example of how to use the OutlineServices client"""
    
    # Initialize the client
    client = OutlineServices()
    
    # Example motion text and counter arguments
    motion_text = """
    DEFENDANT'S MOTION TO DISMISS
    
    Defendant moves this Court to dismiss Plaintiff's complaint with prejudice 
    on the grounds that:
    
    1. The complaint fails to state a claim upon which relief can be granted
    2. This Court lacks subject matter jurisdiction
    3. The statute of limitations has expired
    """
    
    counter_arguments = """
    1. Plaintiff has clearly stated valid claims for breach of contract and fraud
    2. Federal jurisdiction exists under diversity jurisdiction - amount in controversy exceeds $75,000
    3. The discovery rule tolls the statute of limitations - plaintiff only discovered the fraud last month
    """
    
    try:
        # Example 1: Quick outline with low effort
        print("Generating quick outline with low effort...")
        quick_result = await client.generate_outline(
            motion_text=motion_text,
            counter_arguments=counter_arguments,
            reasoning_effort="low"
        )
        print(f"Quick outline generated in {quick_result['metadata']['generation_time']:.1f}s")
        
        # Example 2: Complete workflow with high effort
        print("\nGenerating comprehensive outline with high effort...")
        result = await client.complete_outline_workflow(
            motion_text=motion_text,
            counter_arguments=counter_arguments,
            output_path=Path("outputs/outlines/"),
            reasoning_effort="high"
        )
        
        print(f"Outline generated successfully!")
        print(f"Saved to: {result['saved_path']}")
        print(f"Total tokens used: {result['metadata']['total_tokens']}")
        print(f"Reasoning effort: {result['metadata']['reasoning_effort']}")
        
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(example_usage())
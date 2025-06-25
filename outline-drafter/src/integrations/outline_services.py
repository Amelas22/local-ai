"""
Integration module for outline drafting service with integrated DOCX conversion
"""

import aiohttp
import asyncio
import json
import logging
from typing import Dict, Any, Optional, BinaryIO, Union
from io import BytesIO
from datetime import datetime
from pathlib import Path

from src.utils.logger import get_logger

logger = get_logger(__name__)


class OutlineServices:
    """Client for interacting with the integrated outline drafting service"""
    
    def __init__(
        self,
        outline_drafter_url: str = "http://outline-drafter:8000",
        timeout: int = 600
    ):
        """
        Initialize the outline services client.
        
        Args:
            outline_drafter_url: URL for the outline drafting service
            timeout: Request timeout in seconds
        """
        self.outline_drafter_url = outline_drafter_url.rstrip('/')
        self.timeout = aiohttp.ClientTimeout(total=timeout)
    
    async def generate_outline(
        self,
        motion_text: str,
        counter_arguments: str,
        reasoning_effort: Optional[str] = None,
        output_format: str = "docx"
    ) -> Union[bytes, Dict[str, Any]]:
        """
        Generate a legal outline using the OpenAI o3 model.
        
        Args:
            motion_text: The opposing counsel's motion text
            counter_arguments: Our counter arguments and facts
            reasoning_effort: Optional reasoning effort level (low/medium/high)
            output_format: Output format - "docx" for binary file or "json" for structured data
            
        Returns:
            If output_format="docx": Bytes of the DOCX file
            If output_format="json": Dictionary containing the generated outline and metadata
            
        Raises:
            Exception: If the API call fails
        """
        logger.info(f"Generating legal outline with effort: {reasoning_effort or 'default'}, format: {output_format}")
        
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            try:
                request_data = {
                    "motion_text": motion_text,
                    "counter_arguments": counter_arguments,
                    "output_format": output_format
                }
                
                if reasoning_effort:
                    request_data["reasoning_effort"] = reasoning_effort
                
                # Set appropriate headers based on output format
                headers = {}
                if output_format == "json":
                    headers["Accept"] = "application/json"
                else:
                    headers["Accept"] = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                
                async with session.post(
                    f"{self.outline_drafter_url}/generate-outline",
                    json=request_data,
                    headers=headers
                ) as response:
                    # Handle JSON response
                    if output_format == "json" or response.content_type == "application/json":
                        result = await response.json()
                        
                        if response.status != 200:
                            raise Exception(f"API error: {result.get('error', 'Unknown error')}")
                        
                        if not result.get('success'):
                            raise Exception(f"Outline generation failed: {result.get('error')}")
                        
                        logger.info(f"Outline generated successfully. Tokens used: {result['metadata'].get('total_tokens', 'N/A')}, Effort: {result['metadata'].get('reasoning_effort', 'N/A')}")
                        return result
                    
                    # Handle DOCX response
                    else:
                        if response.status != 200:
                            error_text = await response.text()
                            raise Exception(f"Outline generation failed: {error_text}")
                        
                        docx_bytes = await response.read()
                        
                        # Extract metadata from header if available
                        metadata_str = response.headers.get('X-Metadata')
                        if metadata_str:
                            try:
                                metadata = json.loads(metadata_str)
                                logger.info(f"Outline generated successfully. Tokens used: {metadata.get('total_tokens', 'N/A')}, Effort: {metadata.get('reasoning_effort', 'N/A')}")
                            except:
                                logger.info("Outline generated successfully (DOCX format)")
                        else:
                            logger.info("Outline generated successfully (DOCX format)")
                        
                        return docx_bytes
                    
            except asyncio.TimeoutError:
                logger.error("Outline generation timed out")
                raise Exception("Outline generation timed out after 10 minutes")
            except Exception as e:
                logger.error(f"Error generating outline: {e}")
                raise
    
    async def generate_outline_json(
        self,
        motion_text: str,
        counter_arguments: str,
        reasoning_effort: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a legal outline and always return JSON format.
        
        This is a convenience method that always requests JSON output.
        
        Args:
            motion_text: The opposing counsel's motion text
            counter_arguments: Our counter arguments and facts
            reasoning_effort: Optional reasoning effort level (low/medium/high)
            
        Returns:
            Dictionary containing the generated outline and metadata
        """
        return await self.generate_outline(
            motion_text=motion_text,
            counter_arguments=counter_arguments,
            reasoning_effort=reasoning_effort,
            output_format="json"
        )
    
    async def generate_outline_docx(
        self,
        motion_text: str,
        counter_arguments: str,
        reasoning_effort: Optional[str] = None
    ) -> bytes:
        """
        Generate a legal outline and always return DOCX format.
        
        This is a convenience method that always requests DOCX output.
        
        Args:
            motion_text: The opposing counsel's motion text
            counter_arguments: Our counter arguments and facts
            reasoning_effort: Optional reasoning effort level (low/medium/high)
            
        Returns:
            Bytes of the DOCX file
        """
        return await self.generate_outline(
            motion_text=motion_text,
            counter_arguments=counter_arguments,
            reasoning_effort=reasoning_effort,
            output_format="docx"
        )
    
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
        reasoning_effort: Optional[str] = None,
        save_json: bool = False
    ) -> Dict[str, Any]:
        """
        Complete workflow: generate outline and save as DOCX.
        
        Args:
            motion_text: The opposing counsel's motion text
            counter_arguments: Our counter arguments and facts
            output_path: Optional path to save the DOCX file
            reasoning_effort: Optional reasoning effort level (low/medium/high)
            save_json: If True, also save the JSON outline
            
        Returns:
            Dictionary containing the file path and metadata
        """
        logger.info("Starting complete outline workflow...")
        
        # Generate the outline as DOCX
        docx_bytes = await self.generate_outline_docx(
            motion_text, counter_arguments, reasoning_effort
        )
        
        # If we need the JSON data (for validation or saving), make a separate request
        outline_data = None
        validation = None
        
        if save_json:
            json_result = await self.generate_outline_json(
                motion_text, counter_arguments, reasoning_effort
            )
            outline_data = json_result['outline']
            
            # Validate the outline
            validation = await self.validate_outline(outline_data)
            if not validation['valid']:
                logger.warning(f"Outline validation issues: {validation}")
        
        # Save files if path provided
        saved_docx_path = None
        saved_json_path = None
        
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Generate filename with timestamp if directory provided
            if output_path.is_dir():
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                docx_filename = f"legal_outline_{timestamp}.docx"
                json_filename = f"legal_outline_{timestamp}.json"
                docx_path = output_path / docx_filename
                json_path = output_path / json_filename
            else:
                # If specific file path provided
                docx_path = output_path
                json_path = output_path.with_suffix('.json')
            
            # Save DOCX
            docx_path.write_bytes(docx_bytes)
            saved_docx_path = str(docx_path)
            logger.info(f"DOCX outline saved to: {saved_docx_path}")
            
            # Save JSON if requested
            if save_json and outline_data:
                with open(json_path, 'w') as f:
                    json.dump(outline_data, f, indent=2)
                saved_json_path = str(json_path)
                logger.info(f"JSON outline saved to: {saved_json_path}")
        
        return {
            "docx_bytes": docx_bytes,
            "docx_path": saved_docx_path,
            "json_path": saved_json_path,
            "outline_data": outline_data,
            "validation": validation
        }


# Example usage
async def example_usage():
    """Example of how to use the integrated OutlineServices client"""
    
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
        # Example 1: Get DOCX directly (most common use case)
        print("Generating outline as DOCX...")
        docx_bytes = await client.generate_outline_docx(
            motion_text=motion_text,
            counter_arguments=counter_arguments,
            reasoning_effort="high"
        )
        print(f"Generated DOCX outline: {len(docx_bytes)} bytes")
        
        # Example 2: Get JSON for processing
        print("\nGenerating outline as JSON...")
        json_result = await client.generate_outline_json(
            motion_text=motion_text,
            counter_arguments=counter_arguments,
            reasoning_effort="medium"
        )
        print(f"Generated JSON outline with {len(json_result['outline']['arguments'])} arguments")
        print(f"Total tokens used: {json_result['metadata']['total_tokens']}")
        
        # Example 3: Complete workflow with file saving
        print("\nRunning complete workflow...")
        result = await client.complete_outline_workflow(
            motion_text=motion_text,
            counter_arguments=counter_arguments,
            output_path=Path("outputs/outlines/"),
            reasoning_effort="high",
            save_json=True  # Also save JSON version
        )
        
        print(f"Workflow completed successfully!")
        print(f"DOCX saved to: {result['docx_path']}")
        print(f"JSON saved to: {result['json_path']}")
        if result['validation']:
            print(f"Validation: {'✓ Passed' if result['validation']['valid'] else '✗ Failed'}")
        
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(example_usage())
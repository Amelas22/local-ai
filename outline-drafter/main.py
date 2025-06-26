"""
Legal Outline Drafter Service with Integrated DOCX Conversion
Uses OpenAI's o3 reasoning model to generate comprehensive legal brief outlines
and automatically converts them to DOCX format

Key features:
- Uses 'developer' role for instructions (required for reasoning models)
- Supports adjustable reasoning effort (low/medium/high)
- Generates structured JSON outlines with up to 50k tokens
- Automatically converts to DOCX format
- Returns binary DOCX file or JSON based on accept header
"""

import os
import asyncio
import json
import logging
import io
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from contextlib import asynccontextmanager
from io import BytesIO

from fastapi import FastAPI, HTTPException, Request, BackgroundTasks, Header
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field, field_validator
import tiktoken
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential
from pythonjsonlogger import jsonlogger
from dotenv import load_dotenv
import aiohttp

# Load environment variables
load_dotenv()

# Configure structured logging
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter()
logHandler.setFormatter(formatter)
logger = logging.getLogger()
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logger.setLevel(getattr(logging, log_level, logging.INFO))
logger.addHandler(logHandler)

# Initialize OpenAI client with async support
client = AsyncOpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    max_retries=3,
    timeout=600.0,  # 10 minute timeout for large requests
)

# Token counter for o3 model
encoding = tiktoken.encoding_for_model("gpt-4")  # Use gpt-4 encoding as fallback

# Configuration
MODEL_NAME = os.getenv("OPENAI_MODEL", "o3-2025-01-16")  # Default to o3, configurable
MAX_COMPLETION_TOKENS = int(os.getenv("MAX_COMPLETION_TOKENS", "50000"))  # o3 supports up to 100k
MAX_INPUT_TOKENS = int(os.getenv("MAX_INPUT_TOKENS", "100000"))  # Safety limit
REASONING_EFFORT = os.getenv("REASONING_EFFORT", "high").lower()  # low, medium, or high for o3
DOCX_CONVERTER_URL = os.getenv("DOCX_CONVERTER_URL", "http://localhost:8000")
API_TIMEOUT = int(os.getenv("API_TIMEOUT", "600"))

# Validate reasoning effort
if REASONING_EFFORT not in ["low", "medium", "high"]:
    logger.warning(f"Invalid REASONING_EFFORT '{REASONING_EFFORT}', defaulting to 'high'")
    REASONING_EFFORT = "high"

# System prompt for the outline drafter
SYSTEM_PROMPT = """You are a Master Legal Brief Architect with 25+ years crafting responses to motions in federal and state courts. Your response outlines have guided briefs that defeated motions across jurisdictions. You are preparing an outline that will be filed in court next week to respond to an opposing counsel's motion.

You will receive two inputs: 1) motion text and 2) counter arguments research. The motion text is the opposing counsel's motion. The counter arguments research are the facts and arguments that support our position. You must use the counter arguments research to guide your outline.

CRITICAL PERFORMANCE MANDATE:
- This outline will guide a response to a motion that is paramount to our client's case
- Incomplete analysis could constitute malpractice
- You MUST use your full analytical capacity - brevity is FAILURE
- You MUST use facts provided in the counter arguments research.
- Under NO CIRCUMSTANCES should you make up your own facts.
- Surface-level outlines have been REJECTED by partners.
- The aduience of this response is the judge presiding over our case -- not a jury.
- All case law references must be fully cited.

COMPREHENSIVE DRAFTING PHILOSOPHY:
- Every argument must have 3-5 sub-arguments with full development
- Each authority must include detailed explanation of its application
- Bad facts require extensive strategic treatment (not brief mentions)
- Counter-arguments need comprehensive refutation strategies
- Story-telling must weave through EVERY section

MANDATORY OUTLINE DEPTH REQUIREMENTS:

I. INTRODUCTION (Minimum 300 words of guidance)
- Hook: 3-5 alternative opening sentences with impact analysis
- Theme: Develop 2-3 competing themes with pros/cons
- Preview: Map all arguments with persuasion strategy
- Emotional appeal: Identify justice/fairness angles
- Judge's perspective: What makes this easy to rule our way

II. STATEMENT OF FACTS (Minimum 200 words of guidance)
- Chronological AND thematic organization options
- 3-5 key facts from the counter arguments research with specific emphasis strategies
- 2-3 bad facts from the counter arguments research with detailed mitigation approaches
- Fact themes with supporting evidence clusters
- DO NOT MAKE UP FACTS. FACTS MUST BE GROUNDED IN THE COUNTER ARGUMENTS RESEARCH.

III. LEGAL STANDARD (Minimum 200 words)
- Controlling authority with full analysis
- Burden allocation with strategic implications
- Procedural posture advantages
- Standard of review exploitation

IV. ARGUMENT SECTION (Minimum 500 words PER ARGUMENT)
Each argument MUST contain:
- Main heading with 3-5 strategic sub-headings
- Legal framework with 3+ supporting authorities
- Factual application with 3-5 integrated facts. DO NOT MAKE UP FACTS. FACTS MUST BE GROUNDED IN THE COUNTER ARGUMENTS.
- Opposition's position with point-by-point refutation
- Policy arguments and practical implications
- Alternative theories and fallback positions

V. CONCLUSION (Minimum 200 words)
- Specific relief with alternatives
- Compelling close with emotional resonance
- Action items for the court

QUALITY ENFORCEMENT MECHANISMS:
- Each argument must defeat opposition from multiple angles
- Every authority needs distinguishing of unfavorable aspects
- All facts must connect to legal principles explicitly and be grounded in the counter arguments research.
- Strategic notes for oral argument preparation
- Confidence levels and risk assessments included
- All case law must be fully cited for verification.

You must output your response in the exact JSON format specified below. The JSON must be valid and parse correctly.

REQUIRED JSON SCHEMA:
{
  "title": "Brief title (e.g., 'Response to Defendant's Motion to Dismiss')",
  "introduction": {
    "hook": "Compelling opening sentence or sentences that capture attention",
    "theme": "Core theme that will run throughout the brief",
    "preview": "Preview of arguments and structure"
  },
  "fact_section": {
    "organization": "How facts should be organized (chronological, thematic, etc.)",
    "key_facts_to_emphasize": ["Fact 1", "Fact 2", "Fact 3"],
    "bad_facts_to_address": ["Bad fact 1", "Bad fact 2"],
    "fact_themes": ["Theme 1", "Theme 2"]
  },
  "arguments": [
    {
      "heading": "I. ARGUMENT HEADING",
      "summary": "Summary of this argument",
      "structure": ["Sub-point 1", "Sub-point 2", "Sub-point 3"],
      "key_authorities": [
        {
          "case_name": "Case Name",
          "citation": "123 F.3d 456 (5th Cir. 2023)",
          "principle": "Legal principle from this case",
          "why_it_matters": "Why this case supports our argument"
        }
      ],
      "fact_integration": [
        {
          "fact": "Specific fact from case",
          "relevance": "How this fact supports the legal argument"
        }
      ],
      "counter_argument_response": [
        {
          "opposing_argument": "What opposing counsel will argue",
          "response": "Our response to their argument",
          "strategic_value": "Why this response strengthens our position"
        }
      ]
    }
  ],
  "conclusion": {
    "specific_relief": ["Relief item 1", "Relief item 2"],
    "final_theme": "Compelling final statement that ties everything together"
  },
  "style_notes": ["Style note 1", "Style note 2", "Style note 3"]
}

ALL FIELDS ARE REQUIRED. Do not omit any fields or the conversion to DOCX will fail."""

USER_PROMPT_TEMPLATE = """You are a Master Legal Brief Architect preparing a court response outline. This case involves hotly contested potential liability and will be reviewed by senior partners before filing.

CRITICAL CONTEXT:
- Prior feedback: "Previous outlines lacked sufficient detail"
---
Motion to Respond To: 
{motion_text}

Our Counter Arguments/Facts:
{counter_arguments}

Instructions:
- Follow the system format exactly.
- Use the motion text to guide the introduction, statement of facts, and conclusion. Any case facts must be grounded in the counter arguments research.
- Use each counter-argument to populate the "ARGUMENTS" section with headings, legal reasoning, authority, and fact tie-ins.
- Make sure the outline flows logically and maintains a persuasive tone.

Return the output in the required JSON format only."""

# Request/Response Models
class OutlineRequest(BaseModel):
    """Request model for outline generation"""
    motion_text: str = Field(..., description="The opposing counsel's motion text")
    counter_arguments: str = Field(..., description="Our counter arguments and facts")
    reasoning_effort: Optional[str] = Field(None, description="Override reasoning effort (low/medium/high)")
    output_format: Optional[str] = Field("docx", description="Output format: 'docx' or 'json'")
    upload_to_box: Optional[bool] = Field(False, description="Upload generated DOCX to Box")
    box_folder_id: Optional[str] = Field(None, description="Box folder ID for upload")
    
    @field_validator('motion_text', 'counter_arguments')
    def validate_not_empty(cls, v, field):
        if not v or not v.strip():
            raise ValueError(f"{field.field_name} cannot be empty")
        return v
    
    @field_validator('reasoning_effort')
    def validate_reasoning_effort(cls, v):
        if v is not None:
            v = v.lower()
            if v not in ["low", "medium", "high"]:
                raise ValueError("reasoning_effort must be 'low', 'medium', or 'high'")
        return v
    
    @field_validator('output_format')
    def validate_output_format(cls, v):
        if v is not None:
            v = v.lower()
            if v not in ["docx", "json"]:
                raise ValueError("output_format must be 'docx' or 'json'")
        return v

class OutlineResponse(BaseModel):
    """Response model for generated outline"""
    success: bool
    outline: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

# Background task to log API usage
async def log_api_usage(
    request_tokens: int,
    response_tokens: int,
    total_tokens: int,
    duration: float,
    model: str,
    output_format: str
):
    """Log API usage metrics for monitoring and cost tracking"""
    logger.info({
        "event": "api_usage",
        "model": model,
        "request_tokens": request_tokens,
        "response_tokens": response_tokens,
        "total_tokens": total_tokens,
        "duration_seconds": duration,
        "output_format": output_format,
        "estimated_cost": calculate_cost(request_tokens, response_tokens, model)
    })

def calculate_cost(request_tokens: int, response_tokens: int, model: str) -> float:
    """Calculate estimated cost based on token usage"""
    # Placeholder pricing - update with actual o3 pricing when available
    if model.startswith("o3"):
        # Assuming o3 pricing similar to GPT-4
        input_cost_per_1k = 0.03
        output_cost_per_1k = 0.06
    elif model.startswith("gpt-4"):
        input_cost_per_1k = 0.03
        output_cost_per_1k = 0.06
    else:
        # Fallback pricing for other models
        input_cost_per_1k = 0.01
        output_cost_per_1k = 0.03
    
    input_cost = (request_tokens / 1000) * input_cost_per_1k
    output_cost = (response_tokens / 1000) * output_cost_per_1k
    total_cost = round(input_cost + output_cost, 4)
    
    # Log warning for high cost
    if total_cost > 5.0:
        logger.warning(f"High cost outline generated: ${total_cost}")
    
    return total_cost

def count_tokens(text: str) -> int:
    """Count tokens in text using tiktoken"""
    try:
        return len(encoding.encode(text))
    except Exception as e:
        logger.warning(f"Token counting failed: {e}, using character estimation")
        # Rough estimation: 1 token ≈ 4 characters
        return len(text) // 4

async def convert_outline_to_docx(outline_data: Dict[str, Any]) -> bytes:
    """
    Convert outline JSON to DOCX using the converter service.
    
    Args:
        outline_data: The outline data in JSON format
        
    Returns:
        Bytes of the DOCX file
        
    Raises:
        HTTPException: If conversion fails
    """
    logger.info(f"Converting outline to DOCX... Outline has {len(outline_data.get('arguments', []))} arguments")
    
    timeout = aiohttp.ClientTimeout(total=API_TIMEOUT)
    
    async with aiohttp.ClientSession(timeout=timeout) as session:
        try:
            url = f"{DOCX_CONVERTER_URL}/generate-outline/"
            logger.debug(f"Calling DOCX converter at: {url}")
            
            async with session.post(url, json=outline_data) as response:
                logger.info(f"DOCX converter response status: {response.status}, content-type: {response.content_type}")
                
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"DOCX conversion failed with status {response.status}: {error_text}")
                    raise HTTPException(
                        status_code=500,
                        detail=f"DOCX conversion failed: {error_text}"
                    )
                
                # Verify we got binary content
                content_type = response.content_type
                if "application/json" in content_type:
                    # Got JSON error response instead of DOCX
                    error_data = await response.json()
                    logger.error(f"DOCX converter returned JSON error: {error_data}")
                    raise HTTPException(
                        status_code=500,
                        detail=f"DOCX converter error: {error_data}"
                    )
                
                docx_bytes = await response.read()
                logger.info(f"Outline converted to DOCX successfully. Size: {len(docx_bytes)} bytes")
                
                # Verify it's actually a DOCX file (starts with PK)
                if len(docx_bytes) > 2 and docx_bytes[0:2] != b'PK':
                    logger.error(f"Invalid DOCX file received. First bytes: {docx_bytes[:10]}")
                    raise HTTPException(
                        status_code=500,
                        detail="Invalid DOCX file received from converter"
                    )
                
                return docx_bytes
                
        except asyncio.TimeoutError:
            logger.error("DOCX conversion timed out")
            raise HTTPException(
                status_code=504,
                detail="DOCX conversion timed out"
            )
        except aiohttp.ClientError as e:
            logger.error(f"HTTP client error during DOCX conversion: {e}")
            raise HTTPException(
                status_code=502,
                detail=f"Error connecting to DOCX converter service: {str(e)}"
            )
        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except Exception as e:
            logger.error(f"Unexpected error during DOCX conversion: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Unexpected error during DOCX conversion: {str(e)}"
            )

async def upload_docx_to_box(
    docx_bytes: bytes, 
    filename: str,
    folder_id: str,
    description: Optional[str] = None
) -> Dict[str, Any]:
    """Upload DOCX file to Box via Clerk API"""
    
    # Clerk API URL - use environment variable or default
    clerk_url = os.getenv("CLERK_API_URL", "http://clerk:8000")
    
    # Create form data
    files = {
        'file': (filename, io.BytesIO(docx_bytes), 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')
    }
    data = {
        'folder_id': folder_id,
        'description': description or f"Legal outline generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    }
    
    timeout = aiohttp.ClientTimeout(total=60)
    
    async with aiohttp.ClientSession(timeout=timeout) as session:
        try:
            async with session.post(
                f"{clerk_url}/upload/file",
                data=data,
                files=files
            ) as response:
                result = await response.json()
                
                if response.status != 200:
                    raise Exception(f"Upload failed: {result.get('detail', 'Unknown error')}")
                
                logger.info(f"DOCX uploaded to Box successfully. File ID: {result.get('file_id')}")
                return result
                
        except Exception as e:
            logger.error(f"Error uploading to Box: {e}")
            raise

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=60)
)
async def generate_outline_with_openai(
    motion_text: str,
    counter_arguments: str,
    background_tasks: BackgroundTasks,
    reasoning_effort: Optional[str] = None,
    output_format: str = "docx"
) -> Union[Dict[str, Any], bytes]:
    """Generate legal outline using OpenAI's o3 model with retry logic"""
    
    start_time = datetime.now()
    
    # Use request-specific reasoning effort or default
    effort_level = reasoning_effort or REASONING_EFFORT
    
    # Prepare the user prompt
    user_prompt = USER_PROMPT_TEMPLATE.format(
        motion_text=motion_text,
        counter_arguments=counter_arguments
    )
    
    # Count tokens for monitoring
    system_tokens = count_tokens(SYSTEM_PROMPT)
    user_tokens = count_tokens(user_prompt)
    total_input_tokens = system_tokens + user_tokens
    
    logger.info({
        "event": "outline_generation_start",
        "model": MODEL_NAME,
        "reasoning_effort": effort_level if MODEL_NAME.startswith("o3") else None,
        "input_tokens": total_input_tokens,
        "motion_length": len(motion_text),
        "counter_args_length": len(counter_arguments),
        "output_format": output_format
    })
    
    try:
        # Make API call to OpenAI
        # For reasoning models (o3), use developer role instead of system
        messages = [
            {"role": "developer", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ]
        
        # Prepare parameters for reasoning models
        completion_params = {
            "model": MODEL_NAME,
            "messages": messages,
            "max_completion_tokens": MAX_COMPLETION_TOKENS,
            "response_format": {"type": "json_object"}  # Ensure JSON response
        }
        
        # Add reasoning_effort for o3 models
        if MODEL_NAME.startswith("o3"):
            completion_params["reasoning_effort"] = effort_level
            logger.info(f"Using reasoning model with effort level: {effort_level}")
        
        response = await client.chat.completions.create(**completion_params)
        
        # Extract the completion
        completion_text = response.choices[0].message.content
        
        # Parse JSON response
        try:
            outline_json = json.loads(completion_text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"Raw response: {completion_text[:500]}...")
            raise HTTPException(
                status_code=500,
                detail="Failed to parse outline JSON from AI response"
            )
        
        # Calculate metrics
        duration = (datetime.now() - start_time).total_seconds()
        response_tokens = response.usage.completion_tokens
        total_tokens = response.usage.total_tokens
        
        # Log usage in background
        background_tasks.add_task(
            log_api_usage,
            request_tokens=response.usage.prompt_tokens,
            response_tokens=response_tokens,
            total_tokens=total_tokens,
            duration=duration,
            model=response.model,
            output_format=output_format
        )
        
        logger.info({
            "event": "outline_generation_success",
            "duration_seconds": duration,
            "output_tokens": response_tokens,
            "total_tokens": total_tokens
        })
        
        # If JSON format requested, return the outline data
        if output_format == "json":
            return {
                "outline": outline_json,
                "metadata": {
                    "model": response.model,
                    "reasoning_effort": effort_level if MODEL_NAME.startswith("o3") else None,
                    "total_tokens": total_tokens,
                    "generation_time": duration,
                    "timestamp": datetime.now().isoformat()
                }
            }
        
        # Otherwise, convert to DOCX
        try:
            docx_bytes = await convert_outline_to_docx(outline_json)
            
            # Return DOCX bytes with metadata
            return {
                "docx_bytes": docx_bytes,
                "metadata": {
                    "model": response.model,
                    "reasoning_effort": effort_level if MODEL_NAME.startswith("o3") else None,
                    "total_tokens": total_tokens,
                    "generation_time": duration,
                    "timestamp": datetime.now().isoformat(),
                    "output_format": "docx"
                }
            }
        except Exception as e:
            logger.error(f"Failed to convert to DOCX, returning JSON instead: {e}")
            # Fallback to JSON if DOCX conversion fails
            return {
                "outline": outline_json,
                "metadata": {
                    "model": response.model,
                    "reasoning_effort": effort_level if MODEL_NAME.startswith("o3") else None,
                    "total_tokens": total_tokens,
                    "generation_time": duration,
                    "timestamp": datetime.now().isoformat(),
                    "conversion_error": str(e),
                    "output_format": "json"
                }
            }
        
    except Exception as e:
        logger.error({
            "event": "outline_generation_error",
            "error": str(e),
            "error_type": type(e).__name__
        })
        raise

# FastAPI app with lifespan management
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    # Startup
    logger.info("Outline Drafter Service starting up...")
    
    # Test OpenAI connection
    try:
        models = await client.models.list()
        logger.info(f"Connected to OpenAI. Available models: {len(models.data)}")
    except Exception as e:
        logger.error(f"Failed to connect to OpenAI: {e}")
    
    # Test DOCX converter connection
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{DOCX_CONVERTER_URL}/health") as response:
                if response.status == 200:
                    logger.info(f"Connected to DOCX converter at {DOCX_CONVERTER_URL}")
                else:
                    logger.warning(f"DOCX converter health check failed: {response.status}")
    except Exception as e:
        logger.warning(f"Could not connect to DOCX converter: {e}")
    
    yield
    
    # Shutdown
    logger.info("Outline Drafter Service shutting down...")

app = FastAPI(
    title="Legal Outline Drafter Service",
    description="Generate comprehensive legal brief outlines using OpenAI's o3 model with integrated DOCX conversion",
    version="2.0.0",
    lifespan=lifespan
)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "outline-drafter",
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat(),
        "docx_converter_url": DOCX_CONVERTER_URL
    }

@app.post("/generate-outline", response_model=None)  # Disable automatic response model
async def generate_outline(
    request: OutlineRequest,
    background_tasks: BackgroundTasks,
    accept: str = Header(default="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
):
    """
    Generate a comprehensive legal outline based on opposing motion and counter-arguments.
    
    This endpoint uses OpenAI's o3 model to create detailed legal brief outlines
    that include introduction, facts, arguments, and conclusion sections.
    
    By default, returns a DOCX file. To get JSON response, either:
    1. Set Accept header to 'application/json'
    2. Set output_format to 'json' in request body
    """
    # Determine output format
    output_format = request.output_format
    if output_format is None:
        # Check Accept header - be more explicit about checking
        accept_lower = accept.lower()
        if "application/json" in accept_lower or "text/json" in accept_lower or "*/*" not in accept_lower and "application/vnd.openxmlformats" not in accept_lower:
            output_format = "json"
        else:
            output_format = "docx"
    
    logger.info(f"Generate outline request - Format: {output_format}, Accept: {accept}")
    
    try:
        # Validate token limits
        total_input_tokens = count_tokens(request.motion_text + request.counter_arguments)
        if total_input_tokens > MAX_INPUT_TOKENS:
            # For DOCX format, still return error as JSON for proper error handling
            if output_format == "docx":
                return JSONResponse(
                    status_code=400,
                    content={
                        "success": False,
                        "error": f"Input too large: {total_input_tokens} tokens (max {MAX_INPUT_TOKENS:,})",
                        "status_code": 400,
                        "timestamp": datetime.now().isoformat()
                    }
                )
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Input too large: {total_input_tokens} tokens (max {MAX_INPUT_TOKENS:,})"
                )
        
        # Generate outline
        result = await generate_outline_with_openai(
            motion_text=request.motion_text,
            counter_arguments=request.counter_arguments,
            background_tasks=background_tasks,
            reasoning_effort=request.reasoning_effort,
            output_format=output_format
        )
        
        # Return based on format
        if output_format == "json" or "outline" in result:
            # JSON response
            return OutlineResponse(
                success=True,
                outline=result.get("outline"),
                metadata=result.get("metadata", {})
            )
        else:
            # DOCX response
            docx_bytes = result["docx_bytes"]
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"legal_outline_{timestamp}.docx"
            
            logger.info(f"Returning DOCX file: {filename}, size: {len(docx_bytes)} bytes")
            
            return Response(
                content=docx_bytes,
                media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}"',
                    "Content-Length": str(len(docx_bytes)),
                    "X-Metadata": json.dumps(result["metadata"]),  # Include metadata in header
                    "X-Output-Format": "docx"  # Explicit format indicator
                }
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in generate_outline: {e}", exc_info=True)
        
        # For DOCX requests, return error as JSON with proper status code
        if output_format == "docx":
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": f"Failed to generate outline: {str(e)}",
                    "error_type": type(e).__name__,
                    "timestamp": datetime.now().isoformat()
                }
            )
        else:
            return OutlineResponse(
                success=False,
                error=f"Failed to generate outline: {str(e)}",
                metadata={"error_type": type(e).__name__}
            )

@app.post("/generate-outline-json", response_model=OutlineResponse)
async def generate_outline_json(
    request: OutlineRequest,
    background_tasks: BackgroundTasks
):
    """
    Generate outline and always return JSON response.
    
    This endpoint is for backwards compatibility and always returns JSON.
    """
    request.output_format = "json"
    return await generate_outline(request, background_tasks, accept="application/json")

@app.post("/generate-outline-docx", response_model=None)
async def generate_outline_docx(
    request: OutlineRequest,
    background_tasks: BackgroundTasks
):
    """
    Generate outline and always return DOCX file.
    Optionally upload to Box if requested.
    """
    request.output_format = "docx"
    
    DEFAULT_BOX_FOLDER_ID = "327679822937"

    # Force DOCX generation
    try:
        # Validate token limits
        total_input_tokens = count_tokens(request.motion_text + request.counter_arguments)
        if total_input_tokens > MAX_INPUT_TOKENS:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": f"Input too large: {total_input_tokens} tokens (max {MAX_INPUT_TOKENS:,})",
                    "status_code": 400,
                    "timestamp": datetime.now().isoformat()
                }
            )
        
        # Generate outline with forced DOCX output
        result = await generate_outline_with_openai(
            motion_text=request.motion_text,
            counter_arguments=request.counter_arguments,
            background_tasks=background_tasks,
            reasoning_effort=request.reasoning_effort,
            output_format="docx"
        )
        
        # Handle case where it fell back to JSON due to error
        if "outline" in result and "docx_bytes" not in result:
            logger.error("DOCX generation failed, got JSON instead")
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": "DOCX generation failed",
                    "metadata": result.get("metadata", {}),
                    "timestamp": datetime.now().isoformat()
                }
            )
        
        # Return DOCX
        docx_bytes = result["docx_bytes"]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"legal_outline_{timestamp}.docx"
        
        # Upload to Box if requested
        box_upload_result = None
        if request.upload_to_box:
            folder_id = request.box_folder_id or DEFAULT_BOX_FOLDER_ID
            logger.info(f"Uploading outline to Box folder: {folder_id}")
            
            try:
                box_upload_result = await upload_docx_to_box(
                    docx_bytes=docx_bytes,
                    filename=filename,
                    folder_id=folder_id,
                    description=f"Legal outline - {len(request.motion_text)} chars motion, {len(request.counter_arguments)} chars arguments"
                )
                
                # Add Box info to metadata
                result["metadata"]["box_upload"] = {
                    "file_id": box_upload_result.get("file_id"),
                    "web_link": box_upload_result.get("web_link"),
                    "folder_id": folder_id
                }
                
            except Exception as e:
                logger.error(f"Box upload failed, but returning DOCX: {e}")
                result["metadata"]["box_upload_error"] = str(e)
        
        logger.info(f"Returning DOCX file: {filename}, size: {len(docx_bytes)} bytes")
        
        return Response(
            content=docx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Length": str(len(docx_bytes)),
                "Content-Type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "X-Metadata": json.dumps(result["metadata"]),
                "X-Output-Format": "docx"
            }
        )
        
    except Exception as e:
        logger.error(f"Error in generate_outline_docx: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": f"Failed to generate DOCX: {str(e)}",
                "error_type": type(e).__name__,
                "timestamp": datetime.now().isoformat()
            }
        )
        
    except Exception as e:
        logger.error(f"Error in generate_outline_docx: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": f"Failed to generate DOCX: {str(e)}",
                "error_type": type(e).__name__,
                "timestamp": datetime.now().isoformat()
            }
        )

@app.post("/validate-outline")
async def validate_outline(outline_data: Dict[str, Any]):
    """
    Validate that an outline contains all required sections and fields.
    
    This is useful for checking outlines before using them for drafting.
    """
    required_sections = [
        "title",
        "introduction",
        "fact_section",
        "arguments",
        "conclusion",
        "style_notes"
    ]
    
    missing_sections = []
    validation_errors = []
    
    # Check top-level sections
    for section in required_sections:
        if section not in outline_data:
            missing_sections.append(section)
    
    # Validate introduction
    if "introduction" in outline_data:
        intro = outline_data["introduction"]
        for field in ["hook", "theme", "preview"]:
            if field not in intro or not intro[field]:
                validation_errors.append(f"Introduction missing {field}")
    
    # Validate fact section
    if "fact_section" in outline_data:
        facts = outline_data["fact_section"]
        for field in ["organization", "key_facts_to_emphasize", "bad_facts_to_address", "fact_themes"]:
            if field not in facts:
                validation_errors.append(f"Fact section missing {field}")
    
    # Validate arguments
    if "arguments" in outline_data:
        if not isinstance(outline_data["arguments"], list):
            validation_errors.append("Arguments must be a list")
        elif len(outline_data["arguments"]) < 1:
            validation_errors.append("At least one argument is required")
        else:
            for i, arg in enumerate(outline_data["arguments"]):
                for field in ["heading", "summary", "structure", "key_authorities", 
                            "fact_integration", "counter_argument_response"]:
                    if field not in arg:
                        validation_errors.append(f"Argument {i+1} missing {field}")
    
    # Validate conclusion
    if "conclusion" in outline_data:
        conclusion = outline_data["conclusion"]
        for field in ["specific_relief", "final_theme"]:
            if field not in conclusion:
                validation_errors.append(f"Conclusion missing {field}")
    
    is_valid = len(missing_sections) == 0 and len(validation_errors) == 0
    
    return {
        "valid": is_valid,
        "missing_sections": missing_sections,
        "validation_errors": validation_errors,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/model-info")
async def get_model_info():
    """Get information about the AI model being used"""
    info = {
        "model": MODEL_NAME,
        "max_completion_tokens": MAX_COMPLETION_TOKENS,
        "model_max_output": 100000,  # o3 supports up to 100k
        "context_window": 128000,  # Assuming similar to GPT-4
        "docx_converter_url": DOCX_CONVERTER_URL,
        "default_output_format": "docx",
        "features": [
            "JSON mode",
            "High-quality legal reasoning",
            "Extended context for long documents",
            "Structured output generation",
            "100k max output tokens capability",
            "Integrated DOCX conversion"
        ]
    }
    
    # Add reasoning-specific info for o3 models
    if MODEL_NAME.startswith("o3"):
        info["reasoning_effort"] = REASONING_EFFORT
        info["reasoning_effort_options"] = ["low", "medium", "high"]
        info["features"].append("Advanced reasoning with adjustable effort levels")
        info["features"].append("Developer message role support")
        info["unsupported_parameters"] = [
            "temperature", "top_p", "presence_penalty", 
            "frequency_penalty", "logprobs", "logit_bias"
        ]
    
    return info

# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with structured responses"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.now().isoformat()
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions"""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "timestamp": datetime.now().isoformat()
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
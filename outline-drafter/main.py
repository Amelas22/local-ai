"""
Legal Outline Drafter Service
Uses OpenAI's o3 reasoning model to generate comprehensive legal brief outlines

Key features:
- Uses 'developer' role for instructions (required for reasoning models)
- Supports adjustable reasoning effort (low/medium/high)
- Generates structured JSON outlines with up to 50k tokens
- Does NOT support temperature or other standard parameters
"""

import os
import asyncio
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
import tiktoken
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential
from pythonjsonlogger import jsonlogger
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure structured logging
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter()
logHandler.setFormatter(formatter)
logger = logging.getLogger()
logger.setLevel(logging.INFO)
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

# Validate reasoning effort
if REASONING_EFFORT not in ["low", "medium", "high"]:
    logger.warning(f"Invalid REASONING_EFFORT '{REASONING_EFFORT}', defaulting to 'high'")
    REASONING_EFFORT = "high"

# System prompt for the outline drafter
SYSTEM_PROMPT = """You are a Master Legal Brief Architect with 25+ years crafting winning arguments in federal and state courts. Your outlines have guided briefs that secured successful verdicts and defeated motions. You are preparing an outline that WILL BE FILED IN COURT NEXT WEEK.

CRITICAL PERFORMANCE MANDATE:
- This outline will guide a response that is paramount to our client's case
- Incomplete analysis could constitute malpractice
- Surface-level outlines have been REJECTED by partners
- You MUST use your full analytical capacity - brevity is FAILURE

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

II. STATEMENT OF FACTS (Minimum 500 words of guidance)
- Chronological AND thematic organization options
- 10-15 key facts with specific emphasis strategies
- 5-7 bad facts with detailed mitigation approaches
- Fact themes with supporting evidence clusters
- Visual/demonstrative evidence integration points

III. LEGAL STANDARD (Minimum 200 words)
- Controlling authority with full analysis
- Burden allocation with strategic implications
- Procedural posture advantages
- Standard of review exploitation

IV. ARGUMENT SECTION (Minimum 800 words PER ARGUMENT)
Each argument MUST contain:
- Main heading with 3-5 strategic sub-headings
- Legal framework with 5+ supporting authorities
- Factual application with 8-10 integrated facts
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
- All facts must connect to legal principles explicitly
- Strategic notes for oral argument preparation
- Confidence levels and risk assessments included

You must output your response in the exact JSON format specified. The JSON must be valid and parse correctly."""

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
- Use the motion text to guide the introduction, statement of facts, and conclusion.
- Use each counter-argument to populate the "ARGUMENTS" section with headings, legal reasoning, authority, and fact tie-ins.
- Make sure the outline flows logically and maintains a persuasive tone.

Return the output in the required JSON format only."""

# Request/Response Models
class OutlineRequest(BaseModel):
    """Request model for outline generation"""
    motion_text: str = Field(..., description="The opposing counsel's motion text")
    counter_arguments: str = Field(..., description="Our counter arguments and facts")
    reasoning_effort: Optional[str] = Field(None, description="Override reasoning effort (low/medium/high)")
    
    @validator('motion_text', 'counter_arguments')
    def validate_not_empty(cls, v, field):
        if not v or not v.strip():
            raise ValueError(f"{field.name} cannot be empty")
        return v
    
    @validator('reasoning_effort')
    def validate_reasoning_effort(cls, v):
        if v is not None:
            v = v.lower()
            if v not in ["low", "medium", "high"]:
                raise ValueError("reasoning_effort must be 'low', 'medium', or 'high'")
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
    model: str
):
    """Log API usage metrics for monitoring and cost tracking"""
    logger.info({
        "event": "api_usage",
        "model": model,
        "request_tokens": request_tokens,
        "response_tokens": response_tokens,
        "total_tokens": total_tokens,
        "duration_seconds": duration,
        "estimated_cost": calculate_cost(request_tokens, response_tokens, model)
    })

def calculate_cost(request_tokens: int, response_tokens: int, model: str) -> float:
    """Calculate estimated cost based on token usage"""
    # Placeholder pricing - update with actual o3 pricing when available
    if model.startswith("o3"):
        # Assuming o3 pricing similar to GPT-4
        input_cost_per_1k = 0.02
        output_cost_per_1k = 0.08
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

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=60)
)
async def generate_outline_with_openai(
    motion_text: str,
    counter_arguments: str,
    background_tasks: BackgroundTasks,
    reasoning_effort: Optional[str] = None
) -> Dict[str, Any]:
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
        "counter_args_length": len(counter_arguments)
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
            model=response.model
        )
        
        logger.info({
            "event": "outline_generation_success",
            "duration_seconds": duration,
            "output_tokens": response_tokens,
            "total_tokens": total_tokens
        })
        
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
    
    yield
    
    # Shutdown
    logger.info("Outline Drafter Service shutting down...")

app = FastAPI(
    title="Legal Outline Drafter Service",
    description="Generate comprehensive legal brief outlines using OpenAI's o3 model",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "outline-drafter",
        "timestamp": datetime.now().isoformat()
    }

@app.post("/generate-outline", response_model=OutlineResponse)
async def generate_outline(
    request: OutlineRequest,
    background_tasks: BackgroundTasks
):
    """
    Generate a comprehensive legal outline based on opposing motion and counter-arguments.
    
    This endpoint uses OpenAI's o3 model to create detailed legal brief outlines
    that include introduction, facts, arguments, and conclusion sections.
    """
    try:
        # Validate token limits
        total_input_tokens = count_tokens(request.motion_text + request.counter_arguments)
        if total_input_tokens > MAX_INPUT_TOKENS:
            raise HTTPException(
                status_code=400,
                detail=f"Input too large: {total_input_tokens} tokens (max {MAX_INPUT_TOKENS:,})"
            )
        
        # Generate outline
        result = await generate_outline_with_openai(
            motion_text=request.motion_text,
            counter_arguments=request.counter_arguments,
            background_tasks=background_tasks,
            reasoning_effort=request.reasoning_effort
        )
        
        return OutlineResponse(
            success=True,
            outline=result["outline"],
            metadata=result["metadata"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in generate_outline: {e}")
        return OutlineResponse(
            success=False,
            error=f"Failed to generate outline: {str(e)}",
            metadata={"error_type": type(e).__name__}
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
        "features": [
            "JSON mode",
            "High-quality legal reasoning",
            "Extended context for long documents",
            "Structured output generation",
            "100k max output tokens capability"
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
    uvicorn.run(app, host="0.0.0.0", port=8015)
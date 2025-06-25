# Legal Outline Services

This directory contains two microservices for the Clerk legal AI system:

1. **Outline Drafter** - Generates comprehensive legal brief outlines using OpenAI's o3 model
2. **DOCX Converter** - Converts JSON outlines to/from Microsoft Word documents

## Services Overview

### Outline Drafter Service (Port 8015)

The outline drafter uses OpenAI's o3-2025-04-16 reasoning model to generate detailed legal brief outlines. It's optimized for:
- Large input handling (40-50k tokens typical)
- Maximum completion tokens: 50,000 (model supports up to 100k)
- Structured JSON output
- Comprehensive legal analysis
- Advanced reasoning with adjustable effort levels

**Key Features for Reasoning Models:**
- Supports `reasoning_effort` parameter (low/medium/high)
- Does NOT support: temperature, top_p, presence_penalty, frequency_penalty
- Optimized for complex multi-step reasoning tasks

**Note**: The o3 model name includes a date (2025-01-16). Update this in `main.py` if using a different version.

Key features:
- Generates introduction, facts, arguments, and conclusion sections
- Includes multiple counter-arguments and authorities per argument
- Provides strategic guidance and oral argument notes
- Validates outline structure

### DOCX Converter Service (Port 8000)

Converts between JSON outline format and Microsoft Word documents for attorney review.

Key features:
- JSON → DOCX conversion with proper formatting
- DOCX → JSON parsing for edited outlines
- Section-based parsing for sequential processing
- Preserves legal citation formatting

## Quick Start

### 1. Set up environment variables

```bash
cp .env.example .env
# Edit .env and add your OpenAI API key
```

### 2. Run with Docker Compose

```bash
docker-compose up -d
```

### 3. Verify services are running

```bash
# Check health endpoints
curl http://localhost:8000/health  # DOCX converter
curl http://localhost:8015/health  # Outline drafter
```

## API Documentation

### Outline Drafter Endpoints

#### Generate Outline
```bash
POST /generate-outline
Content-Type: application/json

{
  "motion_text": "The opposing counsel's motion text...",
  "counter_arguments": "Our counter arguments and facts...",
  "reasoning_effort": "high"  # Optional: override default effort level
}

Response:
{
  "success": true,
  "outline": { /* Generated outline JSON */ },
  "metadata": {
    "model": "o3-2025-04-16",
    "total_tokens": 65000,
    "generation_time": 45.2,
    "timestamp": "2025-06-25T10:30:00Z"
  }
}
```

#### Get Model Info
```bash
GET /model-info

Response:
{
  "model": "o3-2025-04-16",
  "max_completion_tokens": 50000,
  "reasoning_effort": "high",
  "reasoning_effort_options": ["low", "medium", "high"],
  "features": [...],
  "unsupported_parameters": ["temperature", "top_p", ...]
}
```

#### Validate Outline
```bash
POST /validate-outline
Content-Type: application/json

{ /* Outline JSON to validate */ }

Response:
{
  "valid": true,
  "missing_sections": [],
  "validation_errors": []
}
```

### DOCX Converter Endpoints

#### Convert to DOCX
```bash
POST /generate-outline/
Content-Type: application/json

{ /* Outline JSON */ }

Response: Binary DOCX file
```

#### Parse DOCX to JSON
```bash
POST /parse-outline/
Content-Type: multipart/form-data

file: outline.docx

Response: JSON outline
```

## Integration with Clerk

Use the provided integration module in your Clerk codebase:

```python
from src.integrations.outline_services import OutlineServices

# Initialize client
client = OutlineServices()

# Generate outline and save as DOCX
result = await client.complete_outline_workflow(
    motion_text=motion_text,
    counter_arguments=counter_arguments,
    output_path=Path("outputs/outlines/")
)
```

## Performance Considerations

### Token Limits
- Input: Maximum ~100,000 tokens (safety limit)
- Output: Maximum 50,000 tokens (configured limit, o3 supports up to 100k)
- Typical usage: 40-50k input tokens, 20-30k output tokens

**Note**: You can adjust both output limits and reasoning effort:
```bash
# For faster, simpler outlines
REASONING_EFFORT=low MAX_COMPLETION_TOKENS=10000 docker-compose up

# For maximum depth and detail
REASONING_EFFORT=high MAX_COMPLETION_TOKENS=75000 docker-compose up
```

### Timeouts
- Default timeout: 600 seconds (10 minutes)
- Adjustable via API_TIMEOUT environment variable
- Response times vary by reasoning effort:
  - Low effort: 30-60 seconds
  - Medium effort: 60-120 seconds
  - High effort: 120-180 seconds (for 50k output)

### Resource Requirements
- Memory: 2-4GB recommended
- CPU: 2 cores recommended
- Network: Stable connection for OpenAI API calls

## Cost Estimation

Using o3 model pricing (when available):
- Input: ~$0.03 per 1K tokens
- Output: ~$0.06 per 1K tokens
- Typical outline (40k input, 25k output): $2.70 - $4.20
- Maximum outline (50k input, 50k output): $4.50

**⚠️ Cost Warning**: 
- Higher reasoning effort levels use more internal reasoning tokens, increasing costs
- With 50k output tokens at high effort, each outline can cost $3-5
- Monitor your usage carefully
- Consider using lower effort levels for testing:
```bash
# Low cost testing configuration
REASONING_EFFORT=low MAX_COMPLETION_TOKENS=10000 docker-compose up
```

## Best Practices for Reasoning Models

### Prompt Engineering for o3
1. **Keep prompts direct**: Reasoning models work best with clear, straightforward instructions
2. **Avoid chain-of-thought prompts**: The model handles reasoning internally
3. **Don't use "think step by step"**: This is redundant with reasoning models
4. **Be specific about output format**: The model follows structure instructions well

### Optimal Settings for Legal Work
- **Reasoning Effort**: Use "high" for complex litigation, "medium" for routine motions
- **Max Completion Tokens**: 30,000-50,000 for comprehensive outlines
- **Developer Messages**: Use clear, professional legal instructions

### When to Use Different Effort Levels
- **Low**: Simple procedural motions, discovery requests
- **Medium**: Standard motions to dismiss, summary judgment outlines
- **High**: Complex multi-party litigation, appellate briefs, class actions

## Development

### Running Locally

```bash
# Outline drafter
cd outline-drafter
pip install -r requirements.txt
python main.py

# DOCX converter
cd convert-to-docx
pip install -r requirements.txt
python main.py
```

### Testing

```bash
# Test outline generation
curl -X POST http://localhost:8001/generate-outline \
  -H "Content-Type: application/json" \
  -d @test_data/sample_motion.json

# Test DOCX conversion
curl -X POST http://localhost:8000/generate-outline/ \
  -H "Content-Type: application/json" \
  -d @test_data/sample_outline.json \
  -o test_outline.docx
```

## Monitoring

Both services log in structured JSON format:
- API usage metrics
- Token counts
- Error tracking
- Performance metrics

View logs:
```bash
docker-compose logs -f outline-drafter
docker-compose logs -f convert-to-docx
```

## Troubleshooting

### Common Issues

1. **Timeout errors**
   - Increase API_TIMEOUT in .env
   - Check OpenAI API status
   - Reduce input size

2. **JSON parsing errors**
   - Validate outline structure
   - Check for proper escaping
   - Use validation endpoint

3. **Memory issues**
   - Increase Docker memory limits
   - Process documents in chunks
   - Monitor container resources

### Debug Mode

Enable debug logging:
```bash
LOG_LEVEL=DEBUG docker-compose up
```

## Security Notes

- OpenAI API key is required and must be kept secure
- Services should run behind a reverse proxy in production
- No case data is stored; everything is processed in memory
- Consider rate limiting for production deployment
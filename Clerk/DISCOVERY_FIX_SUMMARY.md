# Discovery Endpoint Fix Summary

## Issue
The discovery endpoint was failing with validation errors because:
1. It was trying to create a `DiscoveryProcessingRequest` from `unified_document_models` which expects different fields
2. The endpoint was configured for multipart/form-data but the frontend was sending JSON

## Solution
1. Fixed the model confusion by using the correct `EndpointDiscoveryRequest` (aliased from `discovery_models.DiscoveryProcessingRequest`)
2. Changed the endpoint to accept JSON data instead of form data
3. Added base64 decoding for file content sent from the frontend

## Changes Made

### `/src/api/discovery_endpoints.py`
- Changed endpoint signature to accept `request_data: Dict[str, Any]` instead of individual Form/File parameters
- Extract all fields from the JSON request data
- Handle base64-encoded file content from the frontend
- Fixed model instantiation to use `EndpointDiscoveryRequest`

## Testing
After rebuilding the Docker container, the endpoint should now accept requests in this format:

```json
{
    "discovery_files": [
        {
            "filename": "document.pdf",
            "content": "<base64-encoded-content>"
        }
    ],
    "box_folder_id": null,
    "production_batch": "Batch001",
    "producing_party": "Opposing Counsel",
    "enable_fact_extraction": true,
    "responsive_to_requests": [],
    "confidentiality_designation": null
}
```

## Next Steps
1. Rebuild the Clerk Docker container:
   ```bash
   cd /mnt/c/Users/jlemr/Test2/local-ai-package
   docker compose -p localai --profile cpu -f docker-compose.yml -f docker-compose.clerk.yml build clerk --no-cache
   ```

2. Restart the services:
   ```bash
   docker compose -p localai --profile cpu -f docker-compose.yml -f docker-compose.clerk.yml up clerk
   ```

The discovery processing should now work correctly with document splitting functionality!
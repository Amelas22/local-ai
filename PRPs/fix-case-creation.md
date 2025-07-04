name: "Fix Case Creation 405 Error - Caddy Proxy Configuration"
description: |

## Purpose
Fix the case creation functionality by correcting the Caddy reverse proxy configuration that's stripping the `/api` prefix from requests, causing 405 Method Not Allowed errors.

## Core Principles
1. **Context is King**: Include ALL necessary documentation, examples, and caveats
2. **Validation Loops**: Provide executable tests/lints the AI can run and fix
3. **Information Dense**: Use keywords and patterns from the codebase
4. **Progressive Success**: Start simple, validate, then enhance
5. **Global rules**: Be sure to follow all rules in CLAUDE.md

---

## Goal
Fix the case creation functionality so users can successfully create cases through the Clerk frontend without encountering 405 Method Not Allowed errors.

## Why
- Users cannot create new cases in the system, blocking a core workflow
- The issue affects all case-dependent features (document processing, search, etc.)
- The fix is simple but critical for system functionality

## What
The issue is a misconfiguration in the Caddy reverse proxy. The proxy is stripping the `/api` prefix from requests before forwarding to the backend, but the backend expects the full path including `/api`.

### Success Criteria
- [ ] Case creation completes without terminal errors
- [ ] New case appears in case dropdown list
- [ ] Case can be selected and used for document operations
- [ ] All Docker services remain healthy during operation
- [ ] Browser console shows no JavaScript errors
- [ ] API endpoints respond with appropriate success messages

## All Needed Context

### Documentation & References
```yaml
# MUST READ - Include these in your context window
- file: main.py
  why: Lines 503-526 show the POST /api/cases endpoint implementation
  
- file: Caddyfile
  why: Line 55 has the problematic "uri strip_prefix /api" directive
  
- file: Caddyfile.dev
  why: Shows the correct configuration without prefix stripping
  
- file: src/services/case_manager.py
  why: Implements the case creation logic
  
- file: src/models/case_models.py
  why: Defines the case data models and validation
  
- file: DEBUG-CREATE-CASE.md
  why: Contains the error details and debugging context
  
- file: docker-compose.yml
  why: Shows how services are configured
  
- file: CLAUDE.md
  why: Project conventions and testing requirements
```

### Current Codebase tree
```bash
Clerk/
    main.py                     # FastAPI application with /api/cases endpoint
    Caddyfile                   # Production Caddy config (HAS THE BUG)
    Caddyfile.dev              # Development Caddy config (CORRECT)
    src/
        services/
            case_manager.py     # Case management service
            tests/
                test_case_manager.py
        models/
            case_models.py      # Case data models
        middleware/
            case_context.py     # Case context middleware
            tests/
                test_case_context.py
```

### Desired Codebase tree with files to be added and responsibility of file
```bash
# No new files needed - only configuration fix
Clerk/
    Caddyfile                   # Fixed production Caddy config
```

### Known Gotchas of our codebase & Library Quirks
```python
# CRITICAL: Caddy proxy configuration affects API routing
# The backend expects full paths like /api/cases
# The frontend sends requests to /api/* endpoints
# Caddy should NOT strip the /api prefix - it should forward the full path

# CRITICAL: The development Caddyfile works correctly
# Compare lines 15-22 of Caddyfile.dev with lines 54-57 of Caddyfile
# The dev file doesn't have "uri strip_prefix /api"

# CRITICAL: After fixing Caddyfile, services need to be restarted
# Use: docker-compose restart caddy
```

## Implementation Blueprint

### Data models and structure
No new data models needed - existing models are correct:
- `Case` model in case_models.py
- `CaseCreateRequest` for API validation
- `CaseManager` service for business logic

### List of tasks to be completed to fulfill the PRP in the order they should be completed

```yaml
Task 1:
MODIFY Caddyfile:
  - FIND pattern: "handle /api/* {"
  - REMOVE line: "uri strip_prefix /api"
  - KEEP all other proxy settings identical
  - MATCH pattern from Caddyfile.dev lines 15-22

Task 2:
TEST the fix locally:
  - Restart Caddy container
  - Test case creation through frontend
  - Verify API endpoint responds correctly

Task 3:
CREATE integration test for case creation:
  - Add test to verify /api/cases POST endpoint
  - Test both success and error cases
  - Ensure proper status codes returned
```

### Per task pseudocode as needed added to each task
```python
# Task 1 - Fix Caddyfile
# The corrected section should look like:
"""
# API proxy - forward API calls to backend
handle /api/* {
    reverse_proxy clerk:8000
}
"""
# NOT:
"""
handle /api/* {
    uri strip_prefix /api  # <- REMOVE THIS LINE
    reverse_proxy clerk:8000
}
"""

# Task 3 - Integration test pattern
async def test_case_creation_api():
    """Test case creation through API endpoint"""
    # Use existing test patterns from test_case_manager.py
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/cases",
            json={"name": "Test Case v State"},
            headers={"X-User-ID": "test-user", "X-Law-Firm-ID": "test-firm"}
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Test Case v State"
```

### Integration Points
```yaml
CADDY:
  - file: Caddyfile
  - section: "Clerk Frontend Application" (lines 48-76)
  - change: Remove "uri strip_prefix /api" from handle /api/* block
  
DOCKER:
  - command: "docker-compose restart caddy"
  - verify: "docker ps" shows caddy container healthy
  
TESTING:
  - manual: Use frontend to create a case
  - api: "curl -X POST http://localhost:8010/api/cases -H 'Content-Type: application/json' -d '{\"name\":\"Test Case\"}'"
```

## Validation Loop

### Level 1: Configuration Validation
```bash
# Check Caddyfile syntax is valid
docker run --rm -v $(pwd)/Caddyfile:/etc/caddy/Caddyfile caddy:2 caddy validate --config /etc/caddy/Caddyfile

# Expected: Valid configuration
```

### Level 2: Service Health Check
```bash
# Restart Caddy with new configuration
docker-compose restart caddy

# Check service health
docker ps | grep caddy
curl http://localhost:8010/health

# Expected: Container running, health endpoint responds
```

### Level 3: API Endpoint Test
```bash
# Test the case creation endpoint directly
curl -X POST http://localhost:8010/api/cases \
  -H "Content-Type: application/json" \
  -H "X-User-ID: test-user" \
  -H "X-Law-Firm-ID: test-firm" \
  -d '{"name": "Integration Test Case"}'

# Expected: 200 OK with case data
# NOT: 405 Method Not Allowed
```

### Level 4: Frontend Integration Test
```bash
# Open browser to http://localhost:8010/dashboard
# Click "Add Case"
# Enter case name: "Frontend Test Case"  
# Click "Create Case"

# Expected: 
# - No console errors
# - Case created successfully
# - Case appears in dropdown
```

### Level 5: Automated Tests
```bash
# Run existing case manager tests
cd Clerk
python -m pytest src/services/tests/test_case_manager.py -v

# Run API integration tests
python -m pytest tests/test_api_integration.py::test_case_creation -v

# Expected: All tests pass
```

## Final validation Checklist
- [ ] Caddyfile no longer has "uri strip_prefix /api" in the API handler
- [ ] Caddy container restarted successfully
- [ ] curl test to /api/cases returns 200 OK, not 405
- [ ] Frontend case creation works without errors
- [ ] Case appears in dropdown after creation
- [ ] WebSocket connections still work
- [ ] Other API endpoints still function correctly
- [ ] No regression in existing functionality

---

## Anti-Patterns to Avoid
- ❌ Don't modify the backend API routes - they're correct
- ❌ Don't change the frontend API calls - they're correct
- ❌ Don't add new middleware or complex routing logic
- ❌ Don't forget to restart Caddy after config changes
- ❌ Don't use the dev Caddyfile in production - just copy the fix
- ❌ Don't skip testing other API endpoints after the fix
# PRP: Fix Supabase Client Initialization Error in Clerk Backend

## Problem Statement
When creating a case in the Clerk frontend, the API returns a 500 error with "Supabase client not initialized. Check your configuration." The error occurs because the Clerk backend Docker container cannot properly initialize the Supabase client due to missing/incorrect environment variables and network configuration.

## Context
- **Stack**: local-ai package with Docker Compose managing Supabase + Clerk services
- **Root Cause**: 
  1. Clerk backend container missing Supabase environment variables in docker-compose.yml
  2. Using incorrect URL (http://localhost:8000 instead of http://kong:8000 for container-to-container communication)
  3. Environment variables from .env not properly passed to Clerk container

## Research Findings

### 1. Current Implementation (Files to Reference)
- `/mnt/c/Users/jlemr/Test2/local-ai-package/Clerk/src/services/case_manager.py` - CaseManager initialization (line 477)
- `/mnt/c/Users/jlemr/Test2/local-ai-package/Clerk/config/settings.py` - SupabaseSettings config (lines 205-214)  
- `/mnt/c/Users/jlemr/Test2/local-ai-package/docker-compose.yml` - Missing env vars for Clerk service
- `/mnt/c/Users/jlemr/Test2/local-ai-package/.env` - Contains Supabase credentials

### 2. Docker Networking
- All services run on same Docker network (project: localai)
- Supabase Kong gateway accessible at `http://kong:8000` from within containers
- External access via `http://localhost:8000`

### 3. Environment Variable Flow
```
.env → docker-compose.yml → Container Environment → pydantic Settings → Supabase Client
```

## Implementation Blueprint

### Phase 1: Quick Fix (Immediate Solution)

1. **Update docker-compose.yml**
```yaml
# In services → clerk → environment section, add:
- SUPABASE_URL=http://kong:8000
- SUPABASE_ANON_KEY=${ANON_KEY}
- SUPABASE_SERVICE_ROLE_KEY=${SERVICE_ROLE_KEY}
- SUPABASE_JWT_SECRET=${JWT_SECRET}
```

2. **Verify environment variable loading**
- Add debug logging to case_manager.py initialization
- Log the actual values being used (without exposing keys)

3. **Handle initialization failures gracefully**
```python
# In case_manager.py _initialize_client method:
def _initialize_client(self) -> None:
    """Initialize Supabase client with retry logic"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # Existing initialization code
            if self._client:
                logger.info("Supabase client initialized successfully")
                return
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
    
    logger.error("Failed to initialize Supabase client after all retries")
```

### Phase 2: Environment Variable Validation

1. **Create environment validator**
```python
# New file: Clerk/src/utils/env_validator.py
def validate_supabase_config():
    """Validate Supabase configuration on startup"""
    required_vars = ['SUPABASE_URL', 'SUPABASE_ANON_KEY']
    missing = [var for var in required_vars if not os.getenv(var)]
    
    if missing:
        raise EnvironmentError(f"Missing required environment variables: {missing}")
    
    # Validate URL format
    url = os.getenv('SUPABASE_URL')
    if not url.startswith(('http://', 'https://')):
        raise ValueError(f"Invalid SUPABASE_URL format: {url}")
```

2. **Add startup validation to main.py**

### Phase 3: Alternative Solution (Migration Path)

If Supabase continues to cause issues, implement a simpler auth solution:

1. **Option A: PostgreSQL + FastAPI-Users**
```python
# Use existing PostgreSQL database
# Implement auth with fastapi-users library
# Simpler, fewer moving parts
```

2. **Option B: PocketBase Integration**
```yaml
# Add to docker-compose.yml:
pocketbase:
  image: pocketbase/pocketbase:latest
  volumes:
    - pocketbase_data:/pb_data
  ports:
    - "8090:8090"
```

## Tasks (In Order)

1. **Fix Docker Compose Environment Variables**
   - [ ] Update docker-compose.yml with Supabase env vars
   - [ ] Ensure SUPABASE_URL uses kong:8000 for internal access
   - [ ] Test container environment variable passing

2. **Add Retry Logic to Supabase Initialization**
   - [ ] Implement retry mechanism in case_manager.py
   - [ ] Add proper logging for debugging
   - [ ] Handle initialization failures gracefully

3. **Create Environment Validator**
   - [ ] Create env_validator.py utility
   - [ ] Add startup validation in main.py
   - [ ] Document required environment variables

4. **Test Case Creation Flow**
   - [ ] Rebuild and restart containers
   - [ ] Test case creation via frontend
   - [ ] Verify Supabase client initialization

5. **Update Documentation**
   - [ ] Update README.md with env var requirements
   - [ ] Document Docker networking setup
   - [ ] Add troubleshooting section

## Validation Gates

```bash
# 1. Syntax/Style Check
cd /mnt/c/Users/jlemr/Test2/local-ai-package/Clerk
ruff check . --fix
ruff format .

# 2. Unit Tests (Create new test for env validation)
cd /mnt/c/Users/jlemr/Test2/local-ai-package/Clerk
python -m pytest src/services/tests/test_case_manager.py -v

# 3. Integration Test
cd /mnt/c/Users/jlemr/Test2/local-ai-package
python start_services.py --profile cpu
sleep 30  # Wait for services
curl -X GET http://localhost:8011/api/cases  # Should not error

# 4. End-to-End Test
# Open http://localhost:8010
# Try creating a new case
# Should succeed without 500 error
```

## Error Handling Strategy

1. **Initialization Errors**: Log detailed error, provide actionable message
2. **Network Errors**: Retry with exponential backoff
3. **Auth Errors**: Clear error messages about missing/invalid credentials
4. **Fallback**: If Supabase unavailable, allow read-only mode with warning

## Gotchas & Known Issues

1. **Docker Network Timing**: Supabase may not be ready when Clerk starts
   - Solution: Add health check or retry logic

2. **Environment Variable Precedence**: Docker Compose env overrides .env file
   - Solution: Use ${VAR:-default} syntax in docker-compose.yml

3. **URL Resolution**: localhost doesn't work inside containers
   - Solution: Always use service names (kong) for internal communication

4. **Key Rotation**: Changing keys requires container restart
   - Solution: Document key rotation process

## External Resources

- Docker Compose networking: https://docs.docker.com/compose/networking/
- Supabase self-hosting: https://supabase.com/docs/guides/self-hosting/docker
- FastAPI settings management: https://fastapi.tiangolo.com/advanced/settings/
- Alternative: FastAPI-Users docs: https://fastapi-users.github.io/fastapi-users/

## Success Metrics

- [ ] No "Supabase client not initialized" errors
- [ ] Case creation works consistently
- [ ] Clear error messages if configuration is wrong
- [ ] Environment variables properly validated on startup

## Confidence Score: 8/10

The solution is straightforward - adding missing environment variables to docker-compose.yml. The main risk is timing issues between service startup, which is addressed with retry logic. The alternative migration path provides a fallback if Supabase continues to be problematic.
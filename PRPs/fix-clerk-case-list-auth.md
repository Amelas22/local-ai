# PRP: Fix Clerk Case List Authentication Issues

## Quick Fix (Immediate Resolution)

Based on the PostgreSQL error logs, run these commands to fix the issue immediately:

```bash
# 1. Fix column name mismatch (database has 'admin' but code expects 'is_admin')
docker exec -it localai-postgres-1 psql -U postgres -d clerk -c "ALTER TABLE users RENAME COLUMN admin TO is_admin;"

# 2. Add missing last_login column
docker exec -it localai-postgres-1 psql -U postgres -d clerk -c "ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login TIMESTAMP WITH TIME ZONE;"

# 3. Create development law firm and user
docker exec -it localai-postgres-1 psql -U postgres -d clerk -c "
INSERT INTO law_firms (id, name, domain, is_active) 
VALUES ('dev-firm-123', 'Development Law Firm', 'dev.clerk.ai', true) 
ON CONFLICT (id) DO NOTHING;

INSERT INTO users (id, email, password_hash, name, law_firm_id, is_active, is_admin) 
VALUES ('dev-user-123', 'dev@clerk.ai', '\$2b\$12\$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewKyNiGHTGpFyNBC', 'Development User', 'dev-firm-123', true, true) 
ON CONFLICT (id) DO NOTHING;
"

# 4. Restart clerk service to pick up changes
docker restart clerk
```

## Context

The Clerk frontend is experiencing 401 Unauthorized errors when fetching cases, despite being in development mode with authentication supposedly disabled. The root causes include:

1. Database schema mismatches (column `users.admin` exists but code expects `users.is_admin`)
2. Missing `last_login` column that the User model expects
3. Missing development user (`dev-user-123`) in the database
4. Authentication middleware fails to load user and doesn't properly fallback to mock user

## Documentation URLs

- FastAPI Authentication: https://fastapi.tiangolo.com/tutorial/security/
- JWT Authentication: https://pyjwt.readthedocs.io/en/stable/
- SQLAlchemy ORM: https://docs.sqlalchemy.org/en/20/orm/
- React Query (for API calls): https://tanstack.com/query/latest
- PostgreSQL Foreign Keys: https://www.postgresql.org/docs/current/ddl-constraints.html#DDL-CONSTRAINTS-FK

## Code References to Study

- `start_services_with_postgres.py` - Main entry point for launching stack
- `docker-compose.yml`, `docker-compose.clerk-jwt.yml` - Docker configuration
- `Clerk/src/middleware/auth_middleware.py:38-70` - Authentication middleware logic
- `Clerk/src/api/case_endpoints.py:20-35` - Case API endpoints
- `Clerk/src/models/case_models.py` - Database models
- `Clerk/frontend/src/services/auth.service.ts` - Frontend auth service
- `Clerk/frontend/src/services/apiClient.ts:15-40` - API client with auth headers

## Implementation Blueprint

```pseudocode
PHASE 1: Database Schema Fix
1. Create database initialization script that:
   - Checks if tables exist
   - Creates missing columns
   - Seeds development data
   
PHASE 2: Authentication Middleware Enhancement
1. Update auth_middleware.py to:
   - Better handle database connection errors
   - Provide clear error messages
   - Gracefully fallback in dev mode
   
PHASE 3: Frontend Auth Service Fix
1. Ensure dev auth service properly sets tokens
2. Verify API client sends correct headers
3. Add better error handling for 401s

PHASE 4: Integration Testing
1. Create test script to verify full auth flow
2. Test case creation and listing
3. Verify WebSocket remains functional
```

## Tasks

### 1. Create Database Fix Script (`Clerk/scripts/fix_dev_database.py`)
```python
"""
Fix database schema and ensure development data exists.
Based on existing patterns from init_db.py
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from src.database.models import User, LawFirm
from src.config.settings import get_settings
import logging

logger = logging.getLogger(__name__)

async def ensure_dev_data():
    settings = get_settings()
    engine = create_async_engine(settings.database.url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        try:
            # Check if dev law firm exists
            result = await session.execute(
                select(LawFirm).where(LawFirm.id == "dev-firm-123")
            )
            law_firm = result.scalar_one_or_none()
            
            if not law_firm:
                # Create dev law firm
                law_firm = LawFirm(
                    id="dev-firm-123",
                    name="Development Law Firm",
                    domain="dev.clerk.ai",
                    is_active=True
                )
                session.add(law_firm)
                await session.commit()
                logger.info("Created development law firm")
            
            # Check if dev user exists
            result = await session.execute(
                select(User).where(User.id == "dev-user-123")
            )
            user = result.scalar_one_or_none()
            
            if not user:
                # Create dev user with proper schema
                user = User(
                    id="dev-user-123",
                    email="dev@clerk.ai",
                    password_hash="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewKyNiGHTGpFyNBC",  # "password"
                    name="Development User",
                    law_firm_id="dev-firm-123",
                    is_active=True,
                    is_admin=True,
                    last_login=None  # This column exists in the model
                )
                session.add(user)
                await session.commit()
                logger.info("Created development user")
                
        except Exception as e:
            logger.error(f"Error ensuring dev data: {e}")
            await session.rollback()
            raise
```

### 2. Update Authentication Middleware (`Clerk/src/middleware/auth_middleware.py`)
Update the `get_current_user` function to handle database errors gracefully:
```python
# Around line 65, update the dev mode handling
if not settings.auth.auth_enabled and settings.is_development:
    if token == settings.auth.dev_mock_token:
        try:
            # Try to fetch actual dev user from database
            result = await db.execute(
                select(User)
                .options(selectinload(User.law_firm))
                .where(User.id == "dev-user-123")
            )
            dev_user = result.scalar_one_or_none()
            
            if dev_user:
                return dev_user
            else:
                logger.warning("Dev user not found in database, using mock user")
                # Return mock user with proper structure
                from src.database.models import User, LawFirm
                mock_law_firm = LawFirm(
                    id="dev-firm-123",
                    name="Development Law Firm",
                    domain="dev.clerk.ai",
                    is_active=True
                )
                return User(
                    id="dev-user-123",
                    email="dev@clerk.ai",
                    name="Development User",
                    law_firm_id="dev-firm-123",
                    law_firm=mock_law_firm,
                    is_active=True,
                    is_admin=True
                )
        except Exception as e:
            logger.error(f"Database error in dev mode: {e}")
            # Return minimal mock user on any database error
            return type('MockUser', (), {
                'id': 'dev-user-123',
                'email': 'dev@clerk.ai',
                'name': 'Development User',
                'law_firm_id': 'dev-firm-123',
                'is_active': True,
                'is_admin': True
            })()
```

### 3. Update init_db.py to Include Dev Data
Add to the existing `init_db.py` after admin user creation:
```python
# Around line 90, after creating admin user
if not settings.auth.auth_enabled:
    # Also ensure dev data exists in development mode
    from scripts.fix_dev_database import ensure_dev_data
    await ensure_dev_data()
    logger.info("Ensured development data exists")
```

### 4. Create Docker Entrypoint Script (`Clerk/docker-entrypoint.sh`)
```bash
#!/bin/bash
set -e

echo "Waiting for database to be ready..."
while ! nc -z ${DATABASE_HOST:-postgres} ${DATABASE_PORT:-5432}; do
  sleep 1
done
echo "Database is ready!"

# Run database initialization
echo "Initializing database..."
python init_db.py

# Fix dev data if in development mode
if [ "$AUTH_ENABLED" = "false" ]; then
  echo "Ensuring development data exists..."
  python scripts/fix_dev_database.py
fi

# Start the application
echo "Starting Clerk application..."
exec python main.py
```

### 5. Update Frontend Token Service (`Clerk/frontend/src/services/token.service.ts`)
Ensure the token service properly handles dev mode:
```typescript
// Add better logging for debugging
export const tokenService = {
  getAccessToken(): string | null {
    const token = localStorage.getItem('access_token');
    if (import.meta.env.DEV && !import.meta.env.VITE_AUTH_ENABLED) {
      console.log('[TokenService] Dev mode - returning mock token');
      return 'dev-token-123456';
    }
    return token;
  },
  
  setTokens(accessToken: string, refreshToken: string): void {
    console.log('[TokenService] Setting tokens');
    localStorage.setItem('access_token', accessToken);
    localStorage.setItem('refresh_token', refreshToken);
  }
};
```

### 6. Fix Database Schema Mismatch (`Clerk/scripts/fix_column_names.sql`)
Based on PostgreSQL error logs, create SQL to fix column name mismatches:
```sql
-- Fix column name mismatches based on error logs
-- The model expects is_admin but database has admin
ALTER TABLE users 
  RENAME COLUMN admin TO is_admin;

-- Add missing last_login column if it doesn't exist
ALTER TABLE users 
  ADD COLUMN IF NOT EXISTS last_login TIMESTAMP WITH TIME ZONE;

-- Verify the schema matches the model
-- Expected columns: id, email, password_hash, name, law_firm_id, 
-- is_active, is_admin, last_login, created_at, updated_at
```

### 7. Create Integration Test (`Clerk/tests/test_dev_auth_flow.py`)
```python
import pytest
from httpx import AsyncClient
from src.config.settings import get_settings

@pytest.mark.asyncio
async def test_dev_auth_case_list(async_client: AsyncClient):
    """Test that case list works in dev mode"""
    settings = get_settings()
    
    # Ensure we're in dev mode
    assert not settings.auth.auth_enabled
    
    # Test case list with dev token
    response = await async_client.get(
        "/api/cases",
        headers={"Authorization": f"Bearer {settings.auth.dev_mock_token}"}
    )
    
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    
@pytest.mark.asyncio
async def test_create_case_dev_mode(async_client: AsyncClient):
    """Test case creation in dev mode"""
    settings = get_settings()
    
    response = await async_client.post(
        "/api/cases",
        json={
            "name": "Test Case v Demo Case",
            "description": "Test case creation"
        },
        headers={"Authorization": f"Bearer {settings.auth.dev_mock_token}"}
    )
    
    assert response.status_code in [200, 201]
    data = response.json()
    assert data["name"] == "Test Case v Demo Case"
    assert data["law_firm_id"] == "dev-firm-123"
```

## Known Gotchas

1. **SQLAlchemy Relationships**: The `law_firm` relationship must be properly defined with `selectinload`
2. **JWT Token Format**: Dev token must be exactly `dev-token-123456`
3. **Database URL**: Must use the internal Docker network hostname `postgres:5432`
4. **Column Name Mismatch**: PostgreSQL logs show `users.is_admin` column exists as `users.admin` - verify exact column names
5. **Missing Columns**: `last_login` column might not exist in database but is in the model
6. **Frontend ENV**: `VITE_AUTH_ENABLED` must be `false` (string) not boolean
7. **Docker Network**: Services communicate via internal network, not localhost

## Implementation Order

1. **First**: Create and test database fix script locally
2. **Second**: Update auth middleware with better error handling
3. **Third**: Integrate database fix into Docker startup
4. **Fourth**: Test full stack with `start_services_with_postgres.py`
5. **Fifth**: Add integration tests
6. **Finally**: Update documentation

## Error Handling Strategy

Follow the existing pattern from `case_endpoints.py`:
```python
# Service layer error handling
try:
    # Service logic
    result = await service_method(db, **params)
    return ResponseModel.model_validate(result)
except ValueError as e:
    # Business logic errors
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=str(e)
    )
except Exception as e:
    # Unexpected errors
    logger.error(f"Unexpected error in endpoint: {str(e)}")
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="An unexpected error occurred"
    )
```

## Validation Gates

```bash
# 1. Python syntax and style check
cd Clerk && ruff check --fix src/ tests/

# 2. Database schema validation
docker exec clerk python scripts/fix_database_schema.py --verify

# 3. Unit tests for auth middleware
docker exec clerk pytest src/middleware/tests/test_auth_middleware.py -v

# 4. Integration test - full auth flow
docker exec clerk pytest tests/test_auth_integration.py -v

# 5. Frontend build check
cd Clerk/frontend && npm run build

# 6. Full stack test
python test_services.py --test-auth --test-cases
```

## Success Criteria

1. No 401 errors when fetching cases in dev mode
2. Case list loads successfully in frontend
3. Can create new cases without errors
4. WebSocket continues to function
5. No breaking changes to existing functionality
6. Clear logging shows auth flow working

## Debugging Commands

Quick commands to diagnose the issue:
```bash
# 1. Check if dev user exists in database
docker exec -it localai-postgres-1 psql -U postgres -d clerk -c "SELECT id, email, law_firm_id FROM users WHERE id = 'dev-user-123';"

# 2. Check actual column names in users table
docker exec -it localai-postgres-1 psql -U postgres -d clerk -c "\d users"

# 3. Check clerk container environment
docker exec clerk env | grep -E "AUTH_ENABLED|DEV_MOCK_TOKEN|DATABASE_URL"

# 4. Test API directly with curl
curl -v -H "Authorization: Bearer dev-token-123456" http://localhost:8011/api/cases

# 5. Check clerk logs for auth errors
docker logs clerk 2>&1 | grep -i "auth\|401\|user"

# 6. Fix column names immediately
docker exec -it localai-postgres-1 psql -U postgres -d clerk -c "ALTER TABLE users RENAME COLUMN admin TO is_admin;"
docker exec -it localai-postgres-1 psql -U postgres -d clerk -c "ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login TIMESTAMP WITH TIME ZONE;"

# 7. Create dev data immediately
docker exec -it localai-postgres-1 psql -U postgres -d clerk -c "
INSERT INTO law_firms (id, name, domain, is_active) 
VALUES ('dev-firm-123', 'Development Law Firm', 'dev.clerk.ai', true) 
ON CONFLICT (id) DO NOTHING;

INSERT INTO users (id, email, password_hash, name, law_firm_id, is_active, is_admin) 
VALUES ('dev-user-123', 'dev@clerk.ai', '\$2b\$12\$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewKyNiGHTGpFyNBC', 'Development User', 'dev-firm-123', true, true) 
ON CONFLICT (id) DO NOTHING;
"
```

## Rollback Plan

If issues arise:
1. Check docker logs: `docker logs clerk`
2. Verify database state: `docker exec clerk python scripts/fix_dev_database.py --verify`
3. Reset to previous state: `docker-compose down && docker-compose up -d`
4. Check environment variables are correctly set
5. Manually fix database schema using debugging commands above

## Confidence Score: 8/10

High confidence because:
- Clear understanding of the authentication flow
- Specific error messages point to exact issues
- Development mode should simplify the fix
- Existing code patterns to follow

Points deducted for:
- Complex multi-service architecture
- Potential for cascading effects
- Database state dependencies
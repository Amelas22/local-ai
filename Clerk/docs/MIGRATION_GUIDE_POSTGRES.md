# PostgreSQL + JWT Migration Guide

This guide walks you through migrating from Supabase to PostgreSQL + JWT authentication for the Clerk Legal AI System.

## Overview

The migration replaces Supabase with:
- **PostgreSQL**: Direct database access using SQLAlchemy async
- **JWT Authentication**: Custom JWT implementation with refresh tokens
- **Compatibility Layer**: Maintains existing API contracts

## Migration Steps

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

New dependencies added:
- `sqlalchemy[asyncio]>=2.0.0`
- `asyncpg>=0.29.0`
- `python-jose[cryptography]>=3.3.0`
- `passlib[bcrypt]>=1.7.4`
- `python-multipart>=0.0.6`
- `alembic>=1.13.0`

### 2. Configure Environment Variables

Update your `.env` file with the new configuration:

```bash
# PostgreSQL Database Configuration
DATABASE_URL=postgresql://postgres:password@localhost:5432/postgres

# JWT Authentication Configuration
JWT_SECRET_KEY=<generate-a-secure-32-char-key>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Admin User Configuration
ADMIN_EMAIL=admin@yourdomain.com
ADMIN_PASSWORD=<secure-password>

# Shared Resources Configuration
SHARED_COLLECTIONS=florida_statutes,fmcsr_regulations,federal_rules,case_law_precedents
```

### 3. Initialize Database

First, ensure PostgreSQL is accessible:

#### Option A: Expose PostgreSQL from Docker (Recommended for Development)

```bash
# From the parent directory (local-ai-package)
docker-compose -f docker-compose.yml -f docker-compose.postgres-expose.yml up -d postgres

# Wait for PostgreSQL to be ready
docker-compose logs postgres | grep "database system is ready to accept connections"
```

#### Option B: Use External PostgreSQL

Update your `.env` file with the connection string to your PostgreSQL instance:
```bash
DATABASE_URL=postgresql://user:password@host:port/database
```

#### Run the Initialization Script

```bash
# From the Clerk directory
cd Clerk
python init_db.py
```

This will:
- Create all necessary tables
- Run database migrations
- Create an admin user
- Configure shared resources

#### Troubleshooting

If you get a connection error:
1. Check PostgreSQL is running: `docker-compose ps postgres`
2. Verify the connection string in your `.env` file
3. Ensure PostgreSQL is accessible on the specified port
4. Check PostgreSQL logs: `docker-compose logs postgres`

### 4. Run Migrations Manually (Optional)

If you need to run migrations separately:

```bash
# Initialize Alembic (first time only)
alembic init src/migrations

# Create a new migration
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1
```

### 5. API Changes

#### Authentication Endpoints

New endpoints added:
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login (OAuth2 compatible)
- `POST /api/auth/refresh` - Refresh access token
- `POST /api/auth/logout` - Logout user
- `GET /api/auth/me` - Get current user info
- `POST /api/auth/change-password` - Change password

#### Case Management Endpoints

Endpoints moved to `/api/cases/*`:
- `GET /api/cases` - List user cases
- `POST /api/cases` - Create new case
- `GET /api/cases/{id}` - Get case details
- `PUT /api/cases/{id}` - Update case
- `POST /api/cases/{id}/permissions` - Grant permissions

### 6. Frontend Integration

Update your frontend to:

1. **Login Flow**:
```javascript
// Login request
const response = await fetch('/api/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  body: new URLSearchParams({
    username: email, // Note: OAuth2 uses 'username' field
    password: password
  })
});

const { access_token, refresh_token } = await response.json();

// Store tokens securely
localStorage.setItem('access_token', access_token);
localStorage.setItem('refresh_token', refresh_token);
```

2. **Authenticated Requests**:
```javascript
// Add token to requests
const response = await fetch('/api/cases', {
  headers: {
    'Authorization': `Bearer ${access_token}`,
    'X-Case-ID': caseId  // Still required for case context
  }
});
```

3. **Token Refresh**:
```javascript
// Refresh token when access token expires
const response = await fetch('/api/auth/refresh', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ refresh_token })
});

const { access_token, refresh_token: new_refresh_token } = await response.json();
```

### 7. Middleware Changes

The application now uses two middleware layers:

1. **AuthMiddleware**: Validates JWT tokens and injects user info
2. **CaseContextMiddleware**: Validates case access (requires auth)

Both work together to provide authentication and authorization.

### 8. Database Schema

The new schema includes:

- `law_firms` - Law firm organizations
- `users` - User accounts with password hashes
- `cases` - Legal cases
- `user_case_permissions` - User permissions for cases
- `refresh_tokens` - JWT refresh token storage

### 9. Backward Compatibility

The `case_manager` service maintains the same interface, so existing code continues to work without changes.

### 10. Security Considerations

1. **JWT Secret**: Generate a strong secret key (32+ characters)
2. **Password Requirements**: Implement strong password policies
3. **Token Expiration**: Adjust token lifetimes based on security needs
4. **HTTPS**: Always use HTTPS in production
5. **Rate Limiting**: Implement rate limiting on auth endpoints

## Troubleshooting

### Database Connection Issues

```bash
# Test database connection
python -c "from src.database.connection import test_connection; import asyncio; print(asyncio.run(test_connection()))"
```

### Migration Errors

```bash
# Check migration status
alembic current

# Show migration history
alembic history
```

### Authentication Issues

1. Check JWT secret is set correctly
2. Verify token format in Authorization header: `Bearer <token>`
3. Check token expiration times
4. Ensure middleware order is correct (Auth before CaseContext)

## Rollback Plan

If you need to rollback to Supabase:

1. Keep original `case_manager_supabase_backup.py`
2. Restore Supabase environment variables
3. Update imports to use the backup file
4. Remove new middleware from `main.py`

## Performance Considerations

1. **Connection Pooling**: Configured with 20 connections + 10 overflow
2. **Async Operations**: All database operations are async
3. **Caching**: Case access validation cached for 5 minutes
4. **Indexes**: Added on frequently queried columns

## Next Steps

1. Update frontend authentication service
2. Implement password reset functionality
3. Add multi-factor authentication (optional)
4. Set up database backups
5. Configure monitoring and logging
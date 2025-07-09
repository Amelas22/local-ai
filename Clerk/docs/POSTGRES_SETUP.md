# PostgreSQL Setup for Clerk JWT Authentication

This guide explains how to set up PostgreSQL for Clerk's JWT authentication when using the `start_services.py` script.

## Quick Start

### Option 1: Using docker-compose.override.yml (Recommended)

The simplest approach is to use Docker Compose's automatic override feature:

1. **Ensure docker-compose.override.yml exists** in the parent directory:
   ```bash
   # This file is already created and will automatically expose PostgreSQL
   ```

2. **Start services normally**:
   ```bash
   python start_services.py --profile cpu
   ```

3. **Initialize Clerk database**:
   ```bash
   # From the parent directory
   python init_clerk_db.py
   ```

### Option 2: Using Modified Start Script

Use the enhanced start script that handles PostgreSQL exposure:

```bash
# Start services with PostgreSQL exposed
python start_services_with_postgres.py --profile cpu

# The script will prompt you to initialize the database
```

### Option 3: Manual Setup

1. **Start services with PostgreSQL exposed**:
   ```bash
   docker-compose -p localai \
     -f docker-compose.yml \
     -f docker-compose.clerk.yml \
     -f docker-compose.postgres-expose.yml \
     up -d
   ```

2. **Wait for PostgreSQL to be ready**:
   ```bash
   docker exec localai-postgres-1 pg_isready -U postgres
   ```

3. **Initialize database**:
   ```bash
   cd Clerk
   python init_db.py
   ```

## Environment Configuration

Ensure your `.env` file has the correct PostgreSQL configuration:

```env
# PostgreSQL connection (password should match POSTGRES_PASSWORD)
DATABASE_URL=postgresql://postgres:YOUR_POSTGRES_PASSWORD@localhost:5432/postgres

# JWT Configuration
JWT_SECRET_KEY=your-secret-key-min-32-chars
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Admin user for initial setup
ADMIN_EMAIL=admin@yourdomain.com
ADMIN_PASSWORD=secure-password-change-immediately
```

## Troubleshooting

### PostgreSQL Connection Refused

If you get "connection refused" errors:

1. **Check if PostgreSQL is running**:
   ```bash
   docker ps | grep postgres
   ```

2. **Check if port 5432 is exposed**:
   ```bash
   docker port localai-postgres-1
   ```

3. **Verify DATABASE_URL password matches POSTGRES_PASSWORD**:
   ```bash
   # Check your .env file
   grep "POSTGRES_PASSWORD\|DATABASE_URL" .env
   ```

### Database Already Exists

If you get "database already exists" errors, the database is already initialized. You can:

1. **Skip initialization** - The database is ready to use
2. **Reset the database** (WARNING: This will delete all data):
   ```bash
   docker exec localai-postgres-1 psql -U postgres -c "DROP DATABASE IF EXISTS postgres"
   docker exec localai-postgres-1 psql -U postgres -c "CREATE DATABASE postgres"
   ```

### Module Not Found Errors

If you get Python module errors:

```bash
# Install required dependencies
pip install sqlalchemy[asyncio] asyncpg python-jose[cryptography] passlib[bcrypt] alembic
```

## Integration with Existing Services

The PostgreSQL + JWT setup integrates seamlessly with your existing stack:

- **Clerk Frontend** (port 3001) - Will use JWT authentication
- **Clerk API** (port 8000) - Handles JWT validation
- **PostgreSQL** (port 5432) - Stores users, cases, and permissions
- **Qdrant** - Continues to store vector embeddings

## Security Notes

1. **Change default passwords** immediately after setup
2. **Generate a strong JWT_SECRET_KEY**:
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```
3. **Don't expose PostgreSQL in production** - Remove docker-compose.override.yml
4. **Use HTTPS in production** for JWT token transmission

## Next Steps

After successful setup:

1. **Login to Clerk**: http://localhost:3001
2. **Use admin credentials** shown during initialization
3. **Create law firms and users** through the API
4. **Start processing cases** with full authentication

## Reverting to Supabase

If you need to revert to Supabase:

1. Remove the docker-compose.override.yml file
2. Update environment variables to use Supabase
3. Restart services
4. The compatibility layer will automatically use Supabase
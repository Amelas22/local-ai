# Development Setup Guide

This guide explains how to run the Local AI Package in development mode with hot reloading and better debugging capabilities.

## Quick Start

```bash
# Make the script executable
chmod +x start_services_dev.py

# Start all services in development mode
python start_services_dev.py

# Or with debug tools
docker-compose -p localai -f docker-compose.yml -f docker-compose.clerk.yml -f docker-compose.dev.yml --profile debug up -d
```

## What's Different in Development Mode?

### 1. **Hot Reloading**
- **Backend**: Python files are mounted as volumes, uvicorn runs with `--reload`
- **Frontend**: Vite dev server with HMR (Hot Module Replacement)
- Changes to code are reflected immediately without rebuilding containers

### 2. **Better Logging**
- Debug level logging enabled
- Logs are more verbose and helpful
- Real-time log streaming with `docker-compose logs -f`

### 3. **Development URLs**
- Frontend (Vite): http://localhost:3000 - Direct access to Vite dev server
- Frontend (Caddy): http://localhost:8010 - Through reverse proxy (production-like)
- API: http://localhost:8010/api - Clerk backend API
- WebSocket: ws://localhost:8010/ws - Real-time updates

### 4. **Source Code Mounting**
```yaml
volumes:
  - ./Clerk:/app:cached           # Backend code
  - ./Clerk/frontend:/app:cached   # Frontend code
```

## Common Development Tasks

### Viewing Logs
```bash
# All services
docker-compose -p localai logs -f

# Specific services
docker-compose -p localai logs -f clerk clerk-frontend

# Clerk backend only
docker-compose -p localai logs -f clerk
```

### Restarting Services
```bash
# Restart backend after major changes
docker-compose -p localai restart clerk

# Restart frontend (usually not needed with HMR)
docker-compose -p localai restart clerk-frontend
```

### Debugging Database Issues
```bash
# Start with pgAdmin
docker-compose -p localai --profile debug up -d pgadmin

# Access at http://localhost:5050
# Login: admin@localhost.com / admin
# Add server: postgres:5432, postgres/your-super-secret-password
```

### Making Code Changes

1. **Backend Changes** (Python files):
   - Just save the file
   - Uvicorn will automatically reload
   - Check logs for any errors

2. **Frontend Changes** (React/TypeScript):
   - Save the file
   - Vite HMR updates the browser instantly
   - No manual refresh needed

3. **Environment Variables**:
   - Update `.env` file
   - Restart the affected service: `docker-compose -p localai restart clerk`

## Troubleshooting

### Frontend not updating?
```bash
# Clear Vite cache
docker-compose -p localai exec clerk-frontend rm -rf node_modules/.vite

# Restart frontend
docker-compose -p localai restart clerk-frontend
```

### API returns 401 Unauthorized?
- Check if you're hitting Kong (port 8000) instead of the app (port 8010)
- Ensure `VITE_API_URL` is set correctly
- Use relative URLs in frontend code

### WebSocket connection issues?
- Check browser console for connection errors
- Ensure `/ws` routes are properly proxied in Caddy
- Verify `VITE_WS_URL` environment variable

### Database connection issues?
```bash
# Check if Supabase is running
docker-compose -p localai ps | grep postgres

# View Supabase logs
docker-compose -p localai logs postgres auth
```

## Switching Between Development and Production

### To Development Mode:
```bash
python start_services_dev.py
```

### To Production Mode:
```bash
python start_services.py
```

### Clean Restart:
```bash
# Stop everything
docker-compose -p localai down

# Remove volumes (careful - this deletes data!)
docker-compose -p localai down -v

# Start fresh
python start_services_dev.py
```

## Performance Tips

1. **Use cached mounts**: The `:cached` flag improves performance on macOS
2. **Exclude large directories**: node_modules and venv are excluded from mounts
3. **Use named volumes**: Better performance than bind mounts for dependencies

## Next Steps

- Modify code in `Clerk/` for backend changes
- Modify code in `Clerk/frontend/` for UI changes
- Add new services to `docker-compose.dev.yml`
- Configure VS Code for remote container debugging
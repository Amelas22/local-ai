# Clerk Legal AI - Frontend

## Overview

This is the React/TypeScript frontend for the Clerk Legal AI System. It provides a modern, responsive interface for legal teams to process discovery documents, draft motions, and search case documents.

## Features

- **Discovery Processing**: Real-time visualization of document processing
- **Motion Drafting**: AI-powered legal motion generation
- **Document Search**: Advanced search across case documents
- **Authentication**: Secure login with Supabase
- **Real-time Updates**: WebSocket integration for live processing status

## Technology Stack

- React 18 with TypeScript
- Material-UI for components
- Redux Toolkit for state management
- React Router for navigation
- Supabase for authentication
- Socket.io for WebSocket communication
- Vite for build tooling

## Setup Instructions

### Development

1. Copy `.env.example` to `.env` and configure:
   ```bash
   cp .env.example .env
   ```

2. Update the environment variables:
   ```
   VITE_API_URL=http://localhost:8000
   VITE_WS_URL=ws://localhost:8000
   VITE_SUPABASE_URL=http://localhost:54321
   VITE_SUPABASE_ANON_KEY=your-anon-key
   ```

3. Install dependencies:
   ```bash
   npm install
   ```

4. Start the development server:
   ```bash
   npm run dev
   ```

### Production with Docker

The frontend is configured to run with the main docker-compose setup:

```bash
# From the root local-ai directory
docker-compose -f docker-compose.yml -f docker-compose.clerk.yml up
```

### Caddy Configuration

The frontend is served through Caddy reverse proxy. Add these environment variables to your `.env` file:

```bash
# Caddy hostnames
CLERK_HOSTNAME=app.yourdomain.com
CLERK_API_HOSTNAME=api.yourdomain.com

# For local development
# CLERK_HOSTNAME=localhost:3080
# CLERK_API_HOSTNAME=localhost:8080
```

## Authentication Setup

### Supabase Configuration

1. The frontend uses Supabase for authentication
2. Users must have an account in the Supabase database
3. The following tables are required:

```sql
-- Users table (extends Supabase auth.users)
CREATE TABLE public.users (
  id UUID REFERENCES auth.users(id) PRIMARY KEY,
  email TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  role TEXT DEFAULT 'user',
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- User sessions tracking
CREATE TABLE public.user_sessions (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID REFERENCES public.users(id) NOT NULL,
  started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  ended_at TIMESTAMP WITH TIME ZONE
);

-- Enable Row Level Security
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_sessions ENABLE ROW LEVEL SECURITY;

-- Policies
CREATE POLICY "Users can view own profile" ON public.users
  FOR SELECT USING (auth.uid() = id);

CREATE POLICY "Users can update own profile" ON public.users
  FOR UPDATE USING (auth.uid() = id);

CREATE POLICY "Users can view own sessions" ON public.user_sessions
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can create own sessions" ON public.user_sessions
  FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own sessions" ON public.user_sessions
  FOR UPDATE USING (auth.uid() = user_id);
```

### Creating Users

Users can be created through:
1. The signup page at `/signup`
2. Supabase dashboard
3. SQL directly:

```sql
-- Create auth user first
INSERT INTO auth.users (email, encrypted_password, email_confirmed_at)
VALUES ('user@lawfirm.com', crypt('password123', gen_salt('bf')), NOW());

-- Then create profile
INSERT INTO public.users (id, email, name, role)
VALUES (
  (SELECT id FROM auth.users WHERE email = 'user@lawfirm.com'),
  'user@lawfirm.com',
  'John Doe',
  'attorney'
);
```

## Deployment

### With Caddy (Recommended)

1. The frontend is built and served directly by Caddy (no nginx required)
2. Caddy handles SSL certificates automatically
3. Static files are served efficiently by Caddy
4. API calls are proxied to the backend
5. Access the app at `https://app.yourdomain.com`

### Architecture

```
Internet → Caddy (SSL + Static Files) → React App
                ↘
                  → /api/* → Clerk Backend
                  → /ws/* → WebSocket to Backend
```

The frontend is built in a Docker container and the resulting static files are served directly by Caddy. This eliminates the need for an additional nginx container and provides better performance.

### Environment Variables

For production deployment, ensure these are set:

```bash
# In docker-compose environment
CLERK_HOSTNAME=app.yourdomain.com
SUPABASE_URL=https://your-project.supabase.co
ANON_KEY=your-supabase-anon-key
LETSENCRYPT_EMAIL=admin@yourdomain.com
```

## Development Guidelines

### Code Structure

```
src/
├── components/      # Reusable UI components
├── pages/          # Route pages
├── services/       # API and external services
├── store/          # Redux store and slices
├── hooks/          # Custom React hooks
├── types/          # TypeScript type definitions
├── utils/          # Utility functions
└── styles/         # Global styles and theme
```

### Adding New Features

1. Create components in the appropriate directory
2. Add types to `types/` directory
3. Use Material-UI components for consistency
4. Follow the existing Redux patterns for state management
5. Add authentication checks for protected features

### Testing

```bash
# Run unit tests
npm test

# Run E2E tests
npm run test:e2e

# Check types
npm run type-check

# Lint code
npm run lint
```

## Security Considerations

1. All routes except login/signup are protected
2. JWT tokens are stored in memory only (not localStorage)
3. API calls include authentication headers
4. CORS is configured for the specific backend URL
5. Content Security Policy is enforced

## Troubleshooting

### Common Issues

1. **Cannot connect to backend**
   - Check that Clerk backend is running on port 8000
   - Verify VITE_API_URL in .env

2. **Authentication not working**
   - Verify Supabase is running
   - Check VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY
   - Ensure user exists in Supabase

3. **WebSocket connection failed**
   - Check VITE_WS_URL configuration
   - Ensure backend WebSocket endpoint is implemented

4. **Caddy SSL issues**
   - Ensure domain DNS points to your server
   - Check LETSENCRYPT_EMAIL is valid
   - Review Caddy logs: `docker-compose logs caddy`

## Support

For issues or questions:
1. Check the main Clerk documentation
2. Review docker-compose logs
3. Verify all environment variables are set correctly
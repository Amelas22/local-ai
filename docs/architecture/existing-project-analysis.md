# Existing Project Analysis

**Current Project State:**
- **Primary Purpose:** Legal AI system for motion drafting and document management for law firms
- **Current Tech Stack:** FastAPI (Python 3.11+), Qdrant, PostgreSQL, OpenAI, Box API, n8n, Docker Compose, React 19/Vite frontend, Caddy
- **Architecture Style:** Vertical slice architecture with domain-driven design, comprehensive AI agent system
- **Deployment Method:** Docker Compose with multi-service orchestration (PostgreSQL, n8n, Clerk, Qdrant, Caddy)

**Available Documentation:**
- CLAUDE.md (project-specific AI coding guidelines and principles)
- Discovery Deficiency Analysis PRD (docs/prd.md)

**Identified Constraints:**
- Must maintain compatibility with existing n8n workflows
- Database isolation requirement for multi-tenancy (separate Qdrant DBs per case)
- Docker Compose orchestration with specific service dependencies
- Strict vertical slice architecture must be maintained
- Python 3.11+ with type safety requirements
- Caddy for HTTPS/TLS management in production

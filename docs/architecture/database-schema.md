# Database Schema

## Overview

The Clerk Legal AI System uses a hybrid database architecture combining PostgreSQL for relational data and Qdrant for vector storage. This document outlines the complete database schema and data relationships.

## Database Systems

### PostgreSQL
- **Purpose**: Case management, user data, and relational data
- **Connection**: `postgresql://postgres:${POSTGRES_PASSWORD}@postgres:5432/postgres`
- **Important**: NEVER use Supabase - all database operations use PostgreSQL directly

### Qdrant Vector Database
- **Purpose**: Document embeddings and semantic search
- **Collections**: Organized by case_name for isolation
- **Shared Collections**: `florida_statutes`, `fmcsr_regulations`, `federal_rules`, `case_law_precedents`

## PostgreSQL Schema

### Core Tables

#### cases
```sql
CREATE TABLE cases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) UNIQUE NOT NULL,
    law_firm_id UUID NOT NULL,
    created_by UUID NOT NULL,
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}',
    
    CONSTRAINT cases_status_check CHECK (status IN ('active', 'archived', 'deleted')),
    INDEX idx_cases_law_firm (law_firm_id),
    INDEX idx_cases_name (name),
    INDEX idx_cases_status (status)
);
```

#### case_permissions
```sql
CREATE TABLE case_permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    permission VARCHAR(20) NOT NULL,
    granted_by UUID NOT NULL,
    granted_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT case_permissions_permission_check 
        CHECK (permission IN ('read', 'write', 'admin')),
    UNIQUE (case_id, user_id, permission),
    INDEX idx_case_permissions_user (user_id),
    INDEX idx_case_permissions_case (case_id)
);
```

### Document Management Tables

#### documents
```sql
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    box_file_id VARCHAR(255),
    file_name VARCHAR(255) NOT NULL,
    file_path TEXT,
    document_type VARCHAR(50),
    processing_status VARCHAR(20) DEFAULT 'pending',
    page_count INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}',
    
    CONSTRAINT documents_status_check 
        CHECK (processing_status IN ('pending', 'processing', 'completed', 'failed')),
    INDEX idx_documents_case (case_id),
    INDEX idx_documents_box_id (box_file_id),
    INDEX idx_documents_status (processing_status)
);
```

#### document_chunks
```sql
CREATE TABLE document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    page_number INTEGER,
    embedding_id VARCHAR(255), -- Qdrant point ID
    created_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}',
    
    UNIQUE (document_id, chunk_index),
    INDEX idx_chunks_document (document_id),
    INDEX idx_chunks_embedding (embedding_id)
);
```

### Discovery Processing Tables

#### discovery_productions
```sql
CREATE TABLE discovery_productions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    production_batch VARCHAR(100) NOT NULL,
    producing_party VARCHAR(255),
    production_date DATE,
    responsive_to_requests TEXT[],
    confidentiality_designation VARCHAR(50),
    rtp_document_id UUID REFERENCES documents(id),
    oc_response_document_id UUID REFERENCES documents(id),
    processing_status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}',
    
    INDEX idx_discovery_case (case_id),
    INDEX idx_discovery_batch (production_batch),
    INDEX idx_discovery_status (processing_status)
);
```

#### discovery_documents
```sql
CREATE TABLE discovery_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    production_id UUID NOT NULL REFERENCES discovery_productions(id) ON DELETE CASCADE,
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    bates_start VARCHAR(50),
    bates_end VARCHAR(50),
    document_type VARCHAR(100),
    classification VARCHAR(50),
    confidence_score DECIMAL(3,2),
    
    UNIQUE (production_id, document_id),
    INDEX idx_discovery_docs_production (production_id),
    INDEX idx_discovery_docs_document (document_id)
);
```

### Deficiency Analysis Tables

#### deficiency_reports
```sql
CREATE TABLE deficiency_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    production_id UUID NOT NULL REFERENCES discovery_productions(id) ON DELETE CASCADE,
    rtp_document_id UUID NOT NULL REFERENCES documents(id),
    oc_response_document_id UUID NOT NULL REFERENCES documents(id),
    analysis_status VARCHAR(20) DEFAULT 'pending',
    total_requests INTEGER,
    fully_produced INTEGER DEFAULT 0,
    partially_produced INTEGER DEFAULT 0,
    not_produced INTEGER DEFAULT 0,
    no_responsive_docs INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}',
    
    CONSTRAINT deficiency_status_check 
        CHECK (analysis_status IN ('pending', 'processing', 'completed', 'failed')),
    INDEX idx_deficiency_case (case_id),
    INDEX idx_deficiency_production (production_id),
    INDEX idx_deficiency_status (analysis_status)
);
```

#### deficiency_items
```sql
CREATE TABLE deficiency_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    report_id UUID NOT NULL REFERENCES deficiency_reports(id) ON DELETE CASCADE,
    request_number VARCHAR(50) NOT NULL,
    request_text TEXT NOT NULL,
    oc_response_text TEXT,
    classification VARCHAR(50) NOT NULL,
    confidence_score DECIMAL(3,2),
    evidence_chunks JSONB DEFAULT '[]', -- Array of {document_id, chunk_text, relevance_score}
    reviewer_notes TEXT,
    reviewed_by UUID,
    reviewed_at TIMESTAMPTZ,
    
    CONSTRAINT deficiency_classification_check 
        CHECK (classification IN ('fully_produced', 'partially_produced', 
                                 'not_produced', 'no_responsive_docs')),
    INDEX idx_deficiency_items_report (report_id),
    INDEX idx_deficiency_items_classification (classification)
);
```

### Motion Drafting Tables

#### motion_outlines
```sql
CREATE TABLE motion_outlines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    motion_type VARCHAR(100) NOT NULL,
    title VARCHAR(500) NOT NULL,
    sections JSONB NOT NULL, -- Array of section objects
    created_by UUID NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    INDEX idx_motion_outlines_case (case_id),
    INDEX idx_motion_outlines_type (motion_type)
);
```

#### drafted_motions
```sql
CREATE TABLE drafted_motions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    outline_id UUID REFERENCES motion_outlines(id),
    motion_type VARCHAR(100) NOT NULL,
    title VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,
    version INTEGER DEFAULT 1,
    status VARCHAR(20) DEFAULT 'draft',
    created_by UUID NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT motion_status_check 
        CHECK (status IN ('draft', 'review', 'final', 'filed')),
    INDEX idx_drafted_motions_case (case_id),
    INDEX idx_drafted_motions_outline (outline_id),
    INDEX idx_drafted_motions_status (status)
);
```

### Good Faith Letter Tables

#### good_faith_letters
```sql
CREATE TABLE good_faith_letters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    deficiency_report_id UUID NOT NULL REFERENCES deficiency_reports(id),
    template_id VARCHAR(100),
    letter_content TEXT NOT NULL,
    version INTEGER DEFAULT 1,
    status VARCHAR(20) DEFAULT 'draft',
    created_by UUID NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    sent_at TIMESTAMPTZ,
    
    CONSTRAINT letter_status_check 
        CHECK (status IN ('draft', 'review', 'final', 'sent')),
    INDEX idx_letters_case (case_id),
    INDEX idx_letters_report (deficiency_report_id),
    INDEX idx_letters_status (status)
);
```

### Audit and Tracking Tables

#### processing_logs
```sql
CREATE TABLE processing_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    entity_type VARCHAR(50) NOT NULL,
    entity_id UUID NOT NULL,
    action VARCHAR(100) NOT NULL,
    user_id UUID,
    details JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    INDEX idx_logs_case (case_id),
    INDEX idx_logs_entity (entity_type, entity_id),
    INDEX idx_logs_created (created_at)
);
```

#### cost_tracking
```sql
CREATE TABLE cost_tracking (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    service VARCHAR(50) NOT NULL,
    operation VARCHAR(100) NOT NULL,
    tokens_used INTEGER,
    cost_usd DECIMAL(10,4),
    model_used VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}',
    
    INDEX idx_cost_case (case_id),
    INDEX idx_cost_service (service),
    INDEX idx_cost_created (created_at)
);
```

## Qdrant Collections Schema

### Document Collections (Per Case)

Each case has its own collection named after the case (e.g., `Smith_v_Jones_2024`):

```json
{
  "vectors": {
    "size": 1536,  // OpenAI ada-002 embedding size
    "distance": "Cosine"
  },
  "payload_schema": {
    "document_id": "keyword",
    "chunk_index": "integer",
    "page_number": "integer",
    "document_type": "keyword",
    "case_name": "keyword",
    "production_batch": "keyword",
    "bates_number": "keyword",
    "content": "text",
    "metadata": "json"
  }
}
```

### Shared Resource Collections

Shared collections available across all cases:

```json
{
  "collections": [
    "florida_statutes",
    "fmcsr_regulations", 
    "federal_rules",
    "case_law_precedents"
  ],
  "schema": {
    "vectors": {
      "size": 1536,
      "distance": "Cosine"
    },
    "payload_schema": {
      "statute_number": "keyword",
      "title": "text",
      "content": "text",
      "effective_date": "datetime",
      "jurisdiction": "keyword"
    }
  }
}
```

## Data Relationships

### Case Isolation Pattern
```
Case
 ├─> Case Permissions (User Access)
 ├─> Documents
 │    └─> Document Chunks → Qdrant Vectors
 ├─> Discovery Productions
 │    ├─> Discovery Documents
 │    └─> Deficiency Reports
 │         ├─> Deficiency Items
 │         └─> Good Faith Letters
 └─> Motion Outlines
      └─> Drafted Motions
```

### Processing Flow
```
Document Upload → Document Record → Chunking → Vector Storage
                                              ↓
                                   Discovery Processing
                                              ↓
                                   Deficiency Analysis
                                              ↓
                                   Report Generation
```

## Indexes and Performance

### Critical Indexes
- Case name lookups: `idx_cases_name`
- Document retrieval: `idx_documents_case`, `idx_documents_box_id`
- Discovery tracking: `idx_discovery_batch`, `idx_discovery_status`
- Vector mappings: `idx_chunks_embedding`

### Query Patterns
1. **Case-scoped queries**: Always filter by case_id first
2. **Batch operations**: Use bulk inserts for chunks
3. **Status tracking**: Index on processing_status fields
4. **Audit trails**: Time-based indexes for logs

## Migration Guidelines

### Schema Evolution
1. All changes must be backward compatible
2. Use migrations with rollback capabilities
3. Never drop columns in production
4. Add new columns with defaults or nullable

### Data Migration
1. Test migrations on copy of production data
2. Implement gradual migrations for large tables
3. Maintain audit trail of all migrations
4. Backup before any schema changes

## Security Considerations

### Access Control
- Row-level security through case_permissions
- No direct database access from frontend
- API layer enforces all permissions
- Audit logging for compliance

### Data Isolation
- Case data completely isolated
- No cross-case joins allowed
- Shared resources read-only
- Temporary data properly scoped

## Backup and Recovery

### Backup Strategy
- PostgreSQL: Daily full backups, hourly incrementals
- Qdrant: Daily snapshots of collections
- Retention: 30 days for backups
- Test restores monthly

### Disaster Recovery
- RPO (Recovery Point Objective): 1 hour
- RTO (Recovery Time Objective): 4 hours
- Automated failover for PostgreSQL
- Qdrant replication across zones
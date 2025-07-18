# Source Tree Integration

## Existing Project Structure
```plaintext
Clerk/
├── src/
│   ├── ai_agents/           # AI agent modules
│   ├── api/                 # API endpoints
│   ├── models/              # Data models
│   ├── services/            # Business logic
│   ├── document_processing/ # PDF processing
│   ├── vector_storage/      # Qdrant integration
│   └── websocket/           # Real-time updates
├── frontend/
│   ├── src/
│   │   ├── components/      # React components
│   │   ├── services/        # API clients
│   │   └── hooks/           # Custom hooks
└── tests/                   # Integration tests
```

## New File Organization
```plaintext
Clerk/
├── src/
│   ├── ai_agents/
│   │   ├── deficiency_analyzer.py         # NEW: Deficiency analysis agent
│   │   ├── good_faith_letter_agent.py     # NEW: Letter generation agent
│   │   └── tests/
│   │       ├── test_deficiency_analyzer.py
│   │       └── test_good_faith_letter_agent.py
│   │
│   ├── api/
│   │   ├── deficiency_endpoints.py        # NEW: Deficiency API routes
│   │   └── tests/
│   │       └── test_deficiency_endpoints.py
│   │
│   ├── models/
│   │   ├── deficiency_models.py           # NEW: Pydantic models
│   │   └── tests/
│   │       └── test_deficiency_models.py
│   │
│   ├── services/
│   │   ├── deficiency_service.py          # NEW: Orchestration service
│   │   └── tests/
│   │       └── test_deficiency_service.py
│   │
│   ├── document_processing/
│   │   ├── rtp_parser.py                  # NEW: RTP document parser
│   │   └── tests/
│   │       └── test_rtp_parser.py
│   │
│   └── migrations/
│       └── versions/
│           └── 004_add_deficiency_tables.py # NEW: DB migration
│
├── frontend/
│   └── src/
│       ├── components/
│       │   └── deficiency/                # NEW: Deficiency UI components
│       │       ├── DeficiencyReport.tsx
│       │       ├── DeficiencyItemEditor.tsx
│       │       ├── GoodFaithLetterPreview.tsx
│       │       └── __tests__/
│       │
│       ├── services/
│       │   └── api/
│       │       └── deficiencyService.ts   # NEW: Deficiency API client
│       │
│       └── hooks/
│           └── useDeficiencyAnalysis.ts   # NEW: Deficiency hooks
│
└── templates/
    └── good_faith_letters/                # NEW: Letter templates
        ├── florida_10_day_standard.jinja2
        └── texas_30_day_standard.jinja2
```

## Integration Guidelines
- **File Naming:** Follow snake_case for Python, PascalCase for React components
- **Folder Organization:** New files placed in existing module structure
- **Import/Export Patterns:** Use existing __init__.py patterns for module exports

# 4. Technical Constraints and Integration Requirements

## Existing Technology Stack

**Languages**: Python 3.11+
**Frameworks**: FastAPI, Pydantic v2, Socket.io
**Database**: Qdrant (vector), PostgreSQL for case management (NEVER USE SUPABASE)
**AI/ML**: OpenAI GPT models, Cohere reranking v3.5, spaCy for NER
**Document Processing**: pdfplumber, PyPDF2, pdfminer
**Infrastructure**: Docker for tech stack
**External Dependencies**: OpenAI API, Cohere API

## Integration Approach

**Database Integration Strategy**: 
- Extend existing discovery production metadata to include RTP and OC response references
- Create new tables in PostgreSQL for Detailed Deficiency Matrix Output including: 
   - RFP
   - OC Response
   - Classification label
   - Retrieved content excerpts
   - Match confidence and explanation
   - Flag indicators (transient, not permanent storage)
- Leverage existing case isolation patterns using case_name as database selector

**API Integration Strategy**:
- Add new endpoints to existing FastAPI routes following RESTful patterns
- Extend discovery processing endpoint to accept RTP and OC response uploads
- Create new WebSocket event types for deficiency analysis progress

**Frontend Integration Strategy**:
- Extend existing discovery upload components to include new file fields
- Reuse existing WebSocket connection for real-time updates
- Leverage existing document viewer components for report display

**Testing Integration Strategy**:
- Follow existing pytest patterns with tests in same directory structure
- Mock external API calls (OpenAI, Cohere) for unit tests
- Create integration tests for full pipeline execution

## Code Organization and Standards

**File Structure Approach**:
```
src/
  ai_agents/
    deficiency_analyzer.py       # New AI agent for deficiency analysis
    good_faith_letter_agent.py   # New AI agent for letter generation
    tests/
      test_deficiency_analyzer.py
      test_good_faith_letter_agent.py
  
  models/
    deficiency_models.py         # New Pydantic models for deficiency data
    
  services/
    deficiency_service.py        # Business logic for deficiency workflow
    tests/
      test_deficiency_service.py
```

**Naming Conventions**: 
- Follow existing snake_case for files and functions
- PascalCase for classes and Pydantic models
- Descriptive names following existing patterns (e.g., DeficiencyAnalyzer, GoodFaithLetterAgent)

**Coding Standards**:
- Type hints required for all functions
- Google-style docstrings mandatory
- Maximum 500 lines per file, functions under 50 lines
- Follow KISS and YAGNI principles from CLAUDE.md

**Documentation Standards**:
- Update README.md with new endpoints and features
- Add new dependencies to requirements.txt
- Update CLAUDE.md with new patterns and types

## Deployment and Operations

**Build Process Integration**:
- No changes to existing Docker build process
- New dependencies added to requirements.txt
- Environment variables follow existing patterns

**Deployment Strategy**:
- Feature flag for gradual rollout (ENABLE_DEFICIENCY_ANALYSIS)
- Backward compatible - existing discovery processing continues to work
- No database migrations required (using existing structures)

**Monitoring and Logging**:
- Extend existing cost tracking for new AI operations
- Use existing logger configuration ("clerk_api")
- Add new WebSocket event types to monitoring

**Configuration Management**:
- New environment variables for deficiency analysis thresholds
- Template paths configurable via settings
- Reuse existing API key configurations

## Risk Assessment and Mitigation

**Technical Risks**:
- AI hallucination in document comparison - Mitigated by requiring human review before letter generation
- Large RTP documents may exceed token limits - Mitigated by chunking and windowing strategies
- Performance impact on existing pipeline - Mitigated by async processing and optional feature flag

**Integration Risks**:
- WebSocket event conflicts - Mitigated by namespaced event names (deficiency:*)
- Discovery pipeline failure affecting deficiency analysis - Mitigated by graceful degradation and error recovery

**Deployment Risks**:
- Breaking existing discovery processing - Mitigated by extensive integration testing and feature flag
- API rate limits from increased AI usage - Mitigated by request queuing and cost tracking

**Mitigation Strategies**:
- Comprehensive error handling with fallback to manual process
- Detailed audit logging for compliance requirements
- Phased rollout with monitoring at each stage
- Ability to disable feature without affecting core discovery processing

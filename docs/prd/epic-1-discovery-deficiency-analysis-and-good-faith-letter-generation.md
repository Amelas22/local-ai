# 6. Epic 1: Discovery Deficiency Analysis and Good Faith Letter Generation

**Epic Goal**: Enable automated analysis of discovery productions against RTP requests, generate comprehensive deficiency reports, and draft Good Faith letters to streamline the discovery compliance process.

**Integration Requirements**: 
- Seamless integration with existing discovery processing pipeline
- Maintain case isolation and security standards
- Preserve existing discovery processing functionality
- Enable feature flag for gradual rollout

## Story 1.1: Create Deficiency Analysis Data Models and Service Foundation

As a developer,
I want to establish the data models and service foundation for deficiency analysis,
so that we have a solid architectural base for the feature.

### Acceptance Criteria
1: Create Pydantic models for deficiency analysis data structures (RTPItem, DeficiencyReport, etc.)
2: Implement DeficiencyService with basic initialization and case isolation
3: Add configuration settings for deficiency analysis thresholds
4: Create unit tests for all new models and service initialization
5: Update CLAUDE.md with new types and patterns

### Integration Verification
- IV1: Verify existing discovery models remain unchanged
- IV2: Confirm case isolation patterns are properly implemented
- IV3: Ensure no impact on existing discovery processing endpoints

## Story 1.2: Extend Discovery Pipeline to Accept RTP and OC Response Documents

As a legal team member,
I want to upload RTP and OC response documents during discovery processing,
so that they can be used for automated deficiency analysis.

### Acceptance Criteria
1: Modify discovery processing endpoint to accept additional file uploads (RTP and OC response)
2: Store document references in discovery production metadata
3: Update WebSocket events to include new document processing stages
4: Ensure documents are accessible throughout the processing lifecycle
5: Add validation for PDF file types and size limits

### Integration Verification
- IV1: Verify existing discovery upload functionality remains intact
- IV2: Confirm backward compatibility for discovery batches without RTP/OC documents
- IV3: Test that fact extraction process is not affected by new fields

## Story 1.3: Implement RTP Document Parser and Request Extractor

As a developer,
I want to parse RTP documents and extract individual requests,
so that we can analyze each request against the production.

### Acceptance Criteria
1: Create RTPParser class to extract text from RTP PDFs
2: Implement AI-powered request identification and numbering
3: Handle various RTP formats and structures
4: Extract request categories (documents, communications, etc.)
5: Create comprehensive unit tests for parser edge cases

### Integration Verification
- IV1: Ensure parser uses existing PDF processing libraries (pdfplumber, PyPDF2)
- IV2: Verify memory usage stays within acceptable limits
- IV3: Confirm error handling doesn't crash discovery pipeline

## Story 1.3.5: Create Legal AI Agent Framework Using BMad Creator Tools

As a developer,
I want to adapt the BMad creator tools and framework for legal AI agents,
so that all AI agents follow proven BMad patterns with API-driven execution.

### Acceptance Criteria
1: Set up BMad framework adaptation layer in Clerk/src/ai_agents/bmad-framework/
2: Create agent_executor.py to load BMad-style YAML definitions and execute via API
3: Implement api_mapper.py to convert BMad commands to FastAPI endpoints
4: Adapt BMad's create-doc pattern for legal document generation
5: Create base legal tasks following BMad task structure:
   - create-doc.md (adapted from BMad)
   - analyze-rtp.md
   - search-production.md
   - categorize-compliance.md
6: Set up legal templates directory with BMad template format
7: Implement WebSocket progress tracking for long-running tasks
8: Create unit tests for all framework components
9: Document BMad adaptation patterns in CLAUDE.md

### Integration Verification
- IV1: Verify BMad YAML definitions load correctly
- IV2: Ensure API endpoints follow existing FastAPI patterns
- IV3: Confirm create-doc task works with legal templates
- IV4: Validate WebSocket events integrate properly

## Story 1.4: Build Deficiency Analysis AI Agent Using BMad Creator Tools

As a developer,
I want to create a deficiency analysis agent using BMad creator tools and patterns,
so that we can automatically categorize compliance status following proven BMad workflows.

### Acceptance Criteria
1: Use BMad create-agent task to generate deficiency-analyzer agent:
   - Follow BMad agent-tmpl.yaml structure exactly
   - Include activation-instructions and startup sections
   - Define persona with legal expertise focus
   - Map commands to API operations
2: Create required BMad-style tasks in tasks/ directory:
   - analyze-rtp.md: Parse and structure RTP requests
   - search-production.md: RAG search on production documents
   - categorize-compliance.md: Classify document compliance
   - generate-evidence-chunks.md: Extract citations with page numbers
3: Create legal templates using BMad template format:
   - deficiency-report-tmpl.yaml: Report generation template
   - evidence-citation-tmpl.yaml: Citation formatting template
4: Create compliance checklists:
   - pre-analysis-validation.md: Validate inputs before analysis
   - deficiency-categorization.md: Guide categorization decisions
   - report-completeness.md: Ensure report quality
5: Implement API endpoints that map to agent commands
6: Add WebSocket progress events for each task execution
7: Create comprehensive tests for agent and all tasks

### Integration Verification
- IV1: Verify agent loads correctly via agent_executor.py
- IV2: Ensure all tasks follow BMad task structure
- IV3: Confirm create-doc works with legal templates
- IV4: Validate case isolation in all operations
- IV5: Test API endpoint mapping functions correctly

## Story 1.5: Create Deficiency Report Generation System

As a legal team member,
I want to receive a structured deficiency report,
so that I can review and understand what was not properly produced.

### Acceptance Criteria
1: Implement report generator that formats analysis results
2: Include summary statistics (total requests, compliance breakdown)
3: Provide detailed findings for each RTP request with evidence and citations including bates numbers and/or page numbers
4: Generate report in both JSON and human-readable formats
5: Store report data for later retrieval and editing

### Integration Verification
- IV1: Ensure report generation doesn't interfere with existing processes
- IV2: Verify WebSocket events properly communicate report generation progress
- IV3: Confirm report storage follows existing document patterns

## Story 1.6: Implement Deficiency Analysis Trigger After Fact Extraction

As a system administrator,
I want deficiency analysis to automatically start after fact extraction,
so that the process is seamless and requires no manual intervention.

### Acceptance Criteria
1: Add completion hook to fact extraction process
2: Implement automatic triggering of deficiency analysis
3: Handle cases where RTP/OC documents are not provided
4: Add feature flag (ENABLE_DEFICIENCY_ANALYSIS) for controlled rollout
5: Implement proper error handling and recovery

### Integration Verification
- IV1: Verify fact extraction completion is not delayed
- IV2: Test graceful degradation when deficiency analysis fails
- IV3: Ensure discovery pipeline continues even if analysis is disabled

## Story 1.7: Build Frontend Components for Report Review and Editing

As a legal team member,
I want to review and edit the deficiency report findings,
so that I can add context and correct any misunderstandings.

### Acceptance Criteria
1: Create React components for deficiency report display
2: Implement inline editing for categorizations and notes
3: Add bulk actions for updating multiple items
4: Include evidence expansion/collapse functionality
5: Implement save functionality with optimistic updates

### Integration Verification
- IV1: Verify components use existing design system
- IV2: Ensure WebSocket integration for real-time updates
- IV3: Confirm compatibility with existing authentication/authorization

## Story 1.8: Create Good Faith Letter Template System

As a developer,
I want to implement a template system for Good Faith letters,
so that we can generate jurisdiction-appropriate letters.

### Acceptance Criteria
1: Create template storage and retrieval system
2: Implement template variables for dynamic content insertion
3: Support multiple letter formats (formal, informal, etc.)
4: Add template versioning for compliance tracking
5: Create default templates for common jurisdictions

### Integration Verification
- IV1: Ensure templates follow existing document storage patterns
- IV2: Verify template system doesn't conflict with motion templates
- IV3: Confirm proper case isolation for template access

## Story 1.9: Implement Good Faith Letter Generation Agent Using BMad Creator Tools

As a legal team member,
I want to automatically generate Good Faith letters using a BMad-created agent,
so that I can quickly communicate deficiencies following BMad's create-doc pattern.

### Acceptance Criteria
1: Use BMad create-agent task to generate good-faith-letter agent:
   - Follow BMad agent-tmpl.yaml structure
   - Define persona as legal correspondence specialist
   - Use create-doc pattern for letter generation
   - Include customization for API-only execution
2: Create required BMad-style tasks:
   - select-letter-template.md: Choose jurisdiction-appropriate template
   - populate-deficiency-findings.md: Insert analysis results
   - generate-signature-block.md: Create appropriate signature
3: Create letter templates using BMad template format:
   - good-faith-letter-federal.yaml: Federal court template
   - good-faith-letter-state.yaml: State court template
4: Create compliance checklists:
   - letter-requirements-federal.md: Federal requirements
   - letter-requirements-state.md: State-specific requirements
   - professional-tone-review.md: Tone and language validation
5: Create data files:
   - jurisdiction-requirements.json: Legal requirements by jurisdiction
   - standard-legal-phrases.json: Approved legal language
6: Implement API endpoints for letter generation workflow
7: Support letter customization via API parameters
8: Create unit tests for all components

### Integration Verification
- IV1: Verify create-doc pattern works with letter templates
- IV2: Ensure all templates meet legal compliance standards
- IV3: Confirm jurisdiction selection logic works correctly
- IV4: Validate API-driven customization functions properly
- IV5: Test framework integration with deficiency analysis results

## Story 1.10: Build Frontend Letter Preview and Export Interface

As a legal team member,
I want to preview and export Good Faith letters,
so that I can review before sending to opposing counsel.

### Acceptance Criteria
1: Create letter preview component with rich text display
2: Implement editing capabilities for letter customization
3: Add export functionality (PDF, Word formats)
4: Include version tracking for letter drafts
5: Implement email integration preparation

### Integration Verification
- IV1: Ensure export formats match existing document standards
- IV2: Verify preview accurately represents final output
- IV3: Confirm integration with existing document management

## Story 1.11: Implement Comprehensive Testing and Documentation

As a developer,
I want comprehensive tests and documentation,
so that the feature is maintainable and reliable.

### Acceptance Criteria
1: Create integration tests for complete deficiency analysis flow
2: Add performance tests for large discovery productions
3: Implement E2E tests for critical user journeys
4: Update README.md with new feature documentation
5: Create user guide for legal teams

### Integration Verification
- IV1: Verify all existing tests still pass
- IV2: Ensure new tests follow existing testing patterns
- IV3: Confirm documentation is consistent with project standards

## Story Sequence Rationale

This story sequence is designed to minimize risk to your existing system:

1. **Foundation First (1.1-1.3)**: Establish data models and parsing without touching existing code
2. **Core Functionality (1.4-1.6)**: Build analysis capabilities with careful integration points
3. **User Interface (1.7, 1.10)**: Add frontend only after backend is stable
4. **Advanced Features (1.8-1.9)**: Letter generation as final enhancement
5. **Quality Assurance (1.11)**: Comprehensive testing before release

Each story can be deployed independently while maintaining system integrity, and the feature flag allows gradual rollout with immediate rollback capability if issues arise.
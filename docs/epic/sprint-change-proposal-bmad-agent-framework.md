# Sprint Change Proposal: BMad Agent Framework Adoption (Revised with Creator Tools)

**Date**: 2025-07-19  
**Author**: Sarah (Product Owner)  
**Change Type**: Architectural Enhancement  
**Impact Level**: High (Stories 1.3.5, 1.4 and 1.9)  
**Risk Level**: Low (Additive changes)  
**Revision**: 2.0 - Updated to utilize BMad Creator Tools

## Executive Summary

This proposal outlines the adoption of the BMad agent methodology using BMad Creator Tools for the Clerk Legal AI System, specifically targeting Epic 1 (Discovery Deficiency Analysis). The change leverages existing BMad creator tools and patterns to build standardized AI agents with consistent context delivery, structured workflows, and API-driven execution.

## Change Trigger

**Primary Catalyst**: Need for a standardized methodology to build AI agents for plaintiff law firms that:
- Maintains full context and understanding of agent roles
- Provides structured tasks and workflows
- Enables human-in-the-loop interactions
- Scales consistently across future legal AI agents

**Current State**: No existing production AI agents; motion_drafter.py is legacy code pending rebuild.

**New Discovery**: BMad Creator Tools available at /bmad-creator-tools provide:
- Standardized agent creation workflow (create-agent task)
- Agent template (agent-tmpl.yaml) with proven structure
- Task-driven architecture patterns
- Template-based document generation via create-doc

## Impact Analysis

### Affected Stories

| Story | Impact Level | Description |
|-------|-------------|-------------|
| 1.3.5 (NEW) | N/A | Create Legal AI Agent Framework |
| 1.4 | Major | Complete redesign using BMad patterns |
| 1.9 | Major | Implement using established framework |

### Technical Impact

1. **New Framework Introduction**
   - BMad-inspired agent structure within Clerk
   - API endpoint mapping for agent commands
   - WebSocket integration for progress tracking

2. **No Breaking Changes**
   - Existing code remains untouched
   - No backward compatibility requirements
   - Additive enhancement only

3. **Future Benefits**
   - Standardized pattern for all AI agents
   - Reduced development time for future agents
   - Consistent quality and documentation

## Recommended Approach: Incremental Adoption

### Implementation Sequence

1. **Story 1.3.5**: Create Legal AI Agent Framework (NEW)
   - Build foundational framework before agent implementation
   - Establish patterns and documentation
   - Create reusable components

2. **Story 1.4**: Build Deficiency Analysis AI Agent
   - Implement using new framework
   - Validate patterns with real use case
   - Refine based on learnings

3. **Story 1.9**: Build Good Faith Letter Agent  
   - Leverage proven framework
   - Reuse common components
   - Demonstrate framework scalability

## Specific Proposed Changes (Updated with BMad Creator Tools)

### 1. Epic Document Updates

**File**: `docs/epic/epic-1-discovery-deficiency-analysis-and-good-faith-letter-generation.md`

#### Story 1.3.5 (Updated to use BMad Creator Tools)

```markdown
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
```

#### Story 1.4 (Updated to use BMad Creator Tools)

```markdown
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
```

#### Story 1.9 (Updated to use BMad Creator Tools)

```markdown
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
   - format-legal-citations.md: Ensure proper legal formatting
   - calculate-deadlines.md: Compute response deadlines
   - generate-signature-block.md: Create appropriate signature
3: Create letter templates using BMad template format:
   - good-faith-letter-federal.yaml: Federal court template
   - good-faith-letter-california.yaml: California state template
   - good-faith-letter-florida.yaml: Florida state template
   - good-faith-letter-texas.yaml: Texas state template
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
```

### 2. CLAUDE.md Framework Documentation

Add new section "LEGAL AI AGENT FRAMEWORK" with:
- BMad-inspired directory structure
- Agent definition pattern with YAML examples
- API endpoint mapping conventions
- Task execution patterns
- Context management approach

### 3. New Directory Structure (Aligned with BMad Creator Tools)

```
Clerk/src/ai_agents/
    bmad-framework/                 # BMad adaptation layer
        agent_executor.py           # Load and execute BMad agents via API
        agent_loader.py             # Parse BMad YAML definitions
        api_mapper.py               # Map BMad commands to REST endpoints
    agents/                         # BMad-style agent definitions
        deficiency-analyzer.md      # Created via BMad create-agent task
        good-faith-letter.md        # Created via BMad create-agent task
    tasks/                          # BMad task format
        create-doc.md               # Adapted from BMad
        analyze-rtp.md              # Legal-specific task
        search-production.md        # Legal-specific task
        categorize-compliance.md    # Legal-specific task
        [additional tasks per story requirements]
    templates/                      # BMad template format
        deficiency-report-tmpl.yaml
        good-faith-letter-*.yaml    # Multiple jurisdiction templates
    checklists/                     # BMad checklist format
        deficiency-validation.md
        letter-requirements-*.md
    data/                           # Reference data
        jurisdiction-requirements.json
        standard-legal-phrases.json
```

### 4. Agent Definition Examples

Created detailed YAML definitions for:
- Deficiency Analyzer Agent (with persona, commands, dependencies)
- Good Faith Letter Agent (with jurisdiction awareness)

## Benefits & Justification (Enhanced with BMad Creator Tools)

1. **Proven Framework**: Leverage existing BMad creator tools and patterns
2. **Standardized Creation**: Use create-agent task for consistent agent generation
3. **Task-Driven Architecture**: Every action has a corresponding task file
4. **Template Pattern**: Document generation via create-doc ensures consistency
5. **Maintainability**: BMad's structured approach with clear dependencies
6. **API Integration**: Adapt BMad commands to REST endpoints seamlessly
7. **Quality Control**: Built-in checklists and validation patterns
8. **Rapid Development**: Creator tools accelerate agent development

## Risk Mitigation

| Risk | Mitigation Strategy |
|------|-------------------|
| Team unfamiliarity with BMad | Comprehensive documentation and examples |
| Over-engineering | Start with MVP framework, iterate |
| Timeline impact | Incremental approach, no breaking changes |

## Next Steps

1. **Approval**: Confirm this proposal meets requirements
2. **Story Creation**: Add Story 1.3.5 to sprint backlog
3. **Implementation**: Begin with framework development
4. **Documentation**: Update all affected artifacts

## Recommendation

**Proceed with implementation** of this architectural enhancement. The incremental approach minimizes risk while establishing a solid foundation for current and future AI agent development.

---

*This change proposal was generated following the BMad change management process to ensure thorough analysis and planning.*
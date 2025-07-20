# 2. Agent Definition Phase

[← Previous: Agent Creation Phase](01-agent-creation-phase.md) | [Next: Agent Activation Phase →](03-agent-activation-phase.md)

---

## YAML Structure Guide

### Activation Instructions Block

```yaml
activation-instructions:
  # Required steps for agent startup
  - STEP 1: Read THIS ENTIRE FILE - contains complete persona
  - STEP 2: Adopt persona defined in agent and persona sections
  - STEP 3: Greet user with name/role and available commands
  
  # Optional advanced instructions
  - STEP 4: Load case context if provided
  - STEP 5: Initialize security boundaries
  
  # Critical behavioral rules
  - CRITICAL: Maintain case isolation at all times
  - DO NOT: Load external files during activation
  - ONLY: Load dependencies when executing commands
```

Examples of activation variations:

```yaml
# Minimal activation
activation-instructions:
  - Read and adopt persona
  - Greet user

# Security-focused activation
activation-instructions:
  - STEP 1: Read complete configuration
  - STEP 2: Validate security context
  - STEP 3: Adopt secure persona
  - CRITICAL: No cross-case data access

# Multi-mode activation
activation-instructions:
  - STEP 1: Read configuration
  - STEP 2: Check execution mode (interactive/API)
  - STEP 3: Adopt appropriate persona
  - IF API: Skip greeting, await commands
  - IF Interactive: Greet and show help
```

### Agent Metadata Block

```yaml
agent:
  name: string        # Human-readable name (required)
  id: string         # Unique identifier (required)
  title: string      # Professional title (optional)
  icon: string       # Emoji representation (optional)
  whenToUse: string  # Usage guidance (optional)
  customization: string  # Behavioral overrides (optional)
  version: string    # Semantic version (optional)
  author: string     # Creator attribution (optional)
  tags: [string]     # Categorization tags (optional)
```

Field specifications:
- `name`: 3-50 characters, no special chars except spaces
- `id`: 3-50 characters, lowercase, hyphens only
- `title`: Up to 100 characters
- `icon`: Single emoji character
- `whenToUse`: Up to 200 characters
- `customization`: Detailed override instructions
- `version`: SemVer format (e.g., "1.2.3")
- `tags`: Array of lowercase strings

### Persona Block

```yaml
persona:
  role: string              # Core role description (required)
  style: string            # Communication style (optional)
  identity: string         # Background/experience (optional)
  focus: string           # Primary areas of focus (optional)
  core_principles: [string]  # Guiding principles (optional)
  constraints: [string]    # Behavioral limitations (optional)
  expertise: [string]      # Areas of expertise (optional)
```

Style examples:
- "Precise, methodical, detail-oriented"
- "Friendly but professional, clear communicator"
- "Direct, no-nonsense, results-focused"

### Commands Block

```yaml
commands:
  - command: description     # Simple format
  
  # Advanced format with parameters
  - analyze:
      description: Analyze discovery documents
      parameters:
        - name: document_id
          type: string
          required: true
        - name: depth
          type: enum[shallow|deep]
          default: deep
```

Command naming conventions:
- Use verbs: `analyze`, `search`, `generate`, `validate`
- Be specific: `analyze-rtp` not just `analyze`
- Keep short: 1-3 words maximum
- No special characters except hyphens

### Dependencies Block

```yaml
dependencies:
  tasks:          # Task files (.md)
    - analyze-rtp.md
    - search-production.md
    
  templates:      # Template files (.yaml)
    - motion-tmpl.yaml
    - letter-tmpl.yaml
    
  checklists:     # Checklist files (.md)
    - validation-checklist.md
    
  data:          # Data files (.json)
    - jurisdiction-rules.json
    
  utils:         # Utility files
    - legal-formatter.py
```

## YAML Validation Requirements

### Required Sections

```yaml
# Minimal valid agent
activation-instructions: [...]  # Required
agent:                         # Required
  name: string                 # Required
  id: string                   # Required
persona:                       # Required
  role: string                 # Required
commands: [...]                # Required
```

### Field Type Specifications

```yaml
# String fields
name: "Agent Name"

# Array fields
commands:
  - help: Show help
  - analyze: Run analysis

# Object fields
parameters:
  document_id:
    type: string
    required: true

# Enum fields
status: pending|active|deprecated
```

### Character Limits

- Agent name: 50 characters
- Agent ID: 50 characters
- Command names: 30 characters
- Descriptions: 200 characters
- Activation instructions: 100 chars/line

## Troubleshooting Guide

### Common YAML Errors

1. **Indentation Error**
   ```yaml
   # Wrong
   agent:
   name: Test
   
   # Correct
   agent:
     name: Test
   ```

2. **Missing Quotes**
   ```yaml
   # Wrong
   description: Analyze docs: fast
   
   # Correct
   description: "Analyze docs: fast"
   ```

3. **Invalid Characters**
   ```yaml
   # Wrong
   id: discovery@analyzer
   
   # Correct
   id: discovery-analyzer
   ```

### Validation Error Messages

- `Missing required field: agent.name` - Add name field
- `Invalid ID format` - Use lowercase and hyphens only
- `Duplicate command: analyze` - Each command must be unique
- `Circular dependency detected` - Check task dependencies

### Debug Techniques

1. **YAML Linting**
   ```bash
   # Validate YAML syntax
   python -m yaml agent-definition.md
   ```

2. **Schema Validation**
   ```python
   from bmad_framework import validate_agent
   validate_agent("path/to/agent.md")
   ```

3. **Verbose Loading**
   ```python
   loader = AgentLoader(debug=True)
   agent = loader.load_agent("my-agent")
   ```

## Definition Templates

### Minimal Agent

```yaml
activation-instructions:
  - Read and adopt persona
  - Greet user

agent:
  name: Basic Agent
  id: basic-agent

persona:
  role: Simple task executor

commands:
  - help: Show commands
  - execute: Run task
```

### Full-Featured Agent

```yaml
activation-instructions:
  - STEP 1: Read THIS ENTIRE FILE
  - STEP 2: Adopt complete persona
  - STEP 3: Initialize case context
  - STEP 4: Greet with capabilities
  - CRITICAL: Maintain isolation

agent:
  name: Advanced Legal Agent
  id: advanced-legal-v2
  title: Senior Legal Analysis Expert
  icon: ⚖️
  whenToUse: Complex legal document analysis
  customization: "Enhanced with domain expertise"
  version: "2.1.0"
  author: "Legal AI Team"
  tags: ["discovery", "analysis", "ml-enhanced"]

persona:
  role: Expert legal analyst with litigation focus
  style: Precise, thorough, legally astute
  identity: Former litigator with 20 years experience
  focus: Discovery deficiencies and compliance
  core_principles:
    - Accuracy and verifiability
    - Complete case coverage
    - Clear legal reasoning
    - Ethical compliance
  constraints:
    - No legal advice
    - Case isolation required
    - Audit trail mandatory
  expertise:
    - Federal discovery rules
    - State procedural law
    - Document analysis
    - Deficiency identification

commands:
  - help: Display all available commands
  - analyze:
      description: Deep analysis of discovery
      parameters:
        - name: rtp_id
          type: string
          required: true
        - name: production_id
          type: string
          required: true
  - search: Semantic search across productions
  - categorize: Classify compliance status
  - report: Generate deficiency report
  - evidence: Extract supporting chunks
  - validate: Verify analysis results

dependencies:
  tasks:
    - analyze-rtp.md
    - search-production.md
    - categorize-compliance.md
    - extract-evidence.md
    - validate-results.md
  templates:
    - deficiency-report-tmpl.yaml
    - evidence-citation-tmpl.yaml
    - compliance-matrix-tmpl.yaml
  checklists:
    - pre-analysis-validation.md
    - deficiency-categories.md
    - post-analysis-review.md
  data:
    - federal-rules.json
    - state-rules-fl.json
    - objection-patterns.json
  utils:
    - legal_citation_formatter.py
    - date_calculator.py
```

### Domain-Specific Variations

```yaml
# Motion Drafter Agent
agent:
  name: Motion Drafter
  id: motion-drafter
  tags: ["motion", "drafting", "generation"]

# Letter Generator Agent  
agent:
  name: Letter Generator
  id: letter-generator
  tags: ["correspondence", "generation"]

# Research Agent
agent:
  name: Legal Researcher
  id: legal-researcher
  tags: ["research", "case-law", "analysis"]
```

---

[← Previous: Agent Creation Phase](01-agent-creation-phase.md) | [Next: Agent Activation Phase →](03-agent-activation-phase.md)
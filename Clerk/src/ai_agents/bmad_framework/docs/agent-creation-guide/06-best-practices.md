# 6. BMad Best Practices

[← Previous: Legal Agent Creation Walkthrough](05-legal-agent-walkthrough.md) | [Next: Example Legal Agents →](07-example-agents.md)

---

## Activation Instruction Patterns

### Standard 5-Step Activation

```yaml
activation-instructions:
  - STEP 1: Read THIS ENTIRE FILE - contains complete persona
  - STEP 2: Adopt persona defined in agent and persona sections
  - STEP 3: Greet user with name/role and available commands
  - STEP 4: List key capabilities using numbered format
  - STEP 5: Await user command (all commands start with *)
```

### Custom Activation Variations

```yaml
# API-Only Activation
activation-instructions:
  - STEP 1: Read configuration
  - STEP 2: Initialize API mode - skip greeting
  - STEP 3: Load security context
  - CRITICAL: No interactive prompts in API mode

# Multi-Modal Activation
activation-instructions:
  - STEP 1: Read complete configuration
  - STEP 2: Detect execution mode (CLI/API/WebSocket)
  - STEP 3: Apply mode-specific behavior:
    - CLI: Full interactive mode with greeting
    - API: Silent mode, JSON responses only
    - WebSocket: Event-driven mode
  - STEP 4: Initialize appropriate handlers

# Secure Activation
activation-instructions:
  - STEP 1: Read and validate configuration
  - STEP 2: Verify security context and permissions
  - STEP 3: Initialize audit logging
  - STEP 4: Adopt secure persona with constraints
  - CRITICAL: All operations require case_name
  - CRITICAL: No cross-case data access
```

### Context-Specific Instructions

```yaml
# Development Environment
activation-instructions:
  - STEP 1: Read configuration
  - STEP 2: Enable debug mode and verbose logging
  - STEP 3: Load test data and mocks
  - DEV ONLY: Show internal state in responses

# Production Environment  
activation-instructions:
  - STEP 1: Read configuration
  - STEP 2: Verify production credentials
  - STEP 3: Initialize monitoring and alerts
  - CRITICAL: No debug information in responses
  - CRITICAL: Rate limiting enforced
```

### Error Recovery Patterns

```yaml
activation-instructions:
  - STEP 1: Read configuration
  - STEP 2: Validate all dependencies exist
  - ON ERROR: Enter degraded mode with limited commands
  - STEP 3: Report missing dependencies to user
  - STEP 4: Offer recovery options
```

## IDE-FILE-RESOLUTION Guide

### Path Resolution Algorithm

```python
class FileResolver:
    def resolve(self, reference: str, dep_type: str) -> Path:
        """
        Resolve file references using BMad conventions.
        
        Examples:
            "create-doc.md" -> "tasks/create-doc.md"
            "motion-tmpl.yaml" -> "templates/motion-tmpl.yaml"
        """
        # 1. Check if absolute path
        if reference.startswith("/"):
            return Path(reference)
        
        # 2. Check current agent directory
        local_path = Path(f"bmad-framework/{dep_type}/{reference}")
        if local_path.exists():
            return local_path
        
        # 3. Check .bmad-core
        core_path = Path(f".bmad-core/{dep_type}/{reference}")
        if core_path.exists():
            return core_path
        
        # 4. Check bmad-creator-tools
        tools_path = Path(f"bmad-creator-tools/{dep_type}/{reference}")
        if tools_path.exists():
            return tools_path
        
        raise FileNotFoundError(f"Cannot resolve: {reference}")
```

### Dependency Mapping Examples

```yaml
# Agent definition
dependencies:
  tasks:
    - analyze-rtp.md  # -> bmad-framework/tasks/analyze-rtp.md
    - create-doc.md   # -> .bmad-core/tasks/create-doc.md
    
  templates:
    - legal-doc-tmpl.yaml  # -> bmad-framework/templates/legal-doc-tmpl.yaml
    
  checklists:
    - validation.md   # -> bmad-framework/checklists/validation.md
```

### Override Mechanisms

```yaml
# In agent definition
resolution_overrides:
  tasks:
    create-doc.md: /custom/path/to/create-doc.md
    
  templates:
    "*-tmpl.yaml": /shared/templates/
```

### Performance Implications

- File resolution cached per session
- Dependency paths validated at load time
- Missing dependencies fail fast
- Circular dependencies detected

## Elicitation Patterns

### When to Use elicit: true

```markdown
# Task requiring user input

## Elicitation Required
elicit: true

## Elicitation Steps
1. Present numbered options to user
2. Wait for selection (1-9)
3. Validate input
4. Proceed with selection
```

Use elicitation for:
- Multiple choice decisions
- Confirmation of critical actions
- Gathering additional parameters
- Clarifying ambiguous requests

### Interactive Workflow Design

```python
class ElicitationFlow:
    async def handle_elicitation(self, task: Task, context: Context):
        # 1. Check if elicitation required
        if not task.elicitation_required:
            return await self.execute_directly(task, context)
        
        # 2. Present options
        options = await self.build_options(task, context)
        response = await self.present_options(options)
        
        # 3. Validate selection
        if not self.is_valid_selection(response):
            return await self.handle_invalid(response)
        
        # 4. Execute with selection
        context.user_selection = response
        return await self.execute_with_selection(task, context)
```

### Numbered Options Protocol

```python
def format_numbered_options(options: List[str]) -> str:
    """
    Format options in BMad numbered style.
    
    Example output:
    Please select an option:
    1. Analyze entire production
    2. Analyze specific date range
    3. Analyze by document type
    4. Custom analysis parameters
    """
    formatted = ["Please select an option:"]
    for i, option in enumerate(options[:9], 1):  # Limit to 9
        formatted.append(f"{i}. {option}")
    return "\n".join(formatted)
```

### User Feedback Loops

```yaml
# Task with feedback loop
feedback_points:
  - after: parse_document
    ask: "Document parsed. Review summary? (y/n)"
    
  - after: initial_analysis
    ask: "Found {count} issues. Continue to detailed analysis?"
    
  - before: generate_report
    options:
      - Generate summary report
      - Generate detailed report
      - Skip report generation
```

## Command Convention Guide

### * Prefix Requirement

All agent commands MUST start with `*`:
- Distinguishes commands from regular text
- Enables command parsing
- Prevents accidental execution

```yaml
commands:
  - "*analyze": Run full analysis
  - "*help": Show available commands
  - "*search {query}": Search documents
```

### Command Naming Best Practices

```yaml
# Good command names
commands:
  - analyze-rtp      # Specific action + target
  - search-docs      # Clear verb + noun
  - generate-report  # Action + output
  - validate-data    # Process + subject

# Bad command names  
commands:
  - process         # Too vague
  - rtp            # No verb
  - do-the-thing   # Unclear
  - a              # Too short
```

### Parameter Passing Patterns

```yaml
# Simple parameters
*search contract
*analyze rtp-123

# Named parameters
*generate-report --format=detailed --include-evidence

# Complex parameters
*analyze --rtp-id=123 --production-id=456 --depth=full

# JSON parameters
*configure {"timeout": 300, "max_results": 100}
```

### Help Text Guidelines

```yaml
commands:
  - help: |
      Display all available commands with descriptions.
      Usage: *help
      
  - analyze:
      description: Perform deficiency analysis
      usage: "*analyze <rtp-id> <production-id>"
      example: "*analyze rtp-123 prod-456"
      options:
        --depth: Analysis depth (shallow|deep)
        --format: Output format (summary|detailed)
```

---

[← Previous: Legal Agent Creation Walkthrough](05-legal-agent-walkthrough.md) | [Next: Example Legal Agents →](07-example-agents.md)
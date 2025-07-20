# 1. Agent Creation Phase

[← Back to Overview](00-overview.md) | [Next: Agent Definition Phase →](02-agent-definition-phase.md)

---

## Using the BMad Create-Agent Task

The BMad framework provides an interactive task for creating new agents. This ensures consistency and completeness.

### Invocation

```bash
# From the project root, execute:
claude-code /BMad:tasks:create-agent
```

### Interactive Prompts

The create-agent task will guide you through:

1. **Agent Name**: Human-readable name (e.g., "Discovery Analyzer")
2. **Agent ID**: Unique identifier (e.g., "discovery-analyzer")
3. **Title**: Professional title (e.g., "Legal Discovery Analysis Specialist")
4. **Icon**: Emoji representation (e.g., "🔍")
5. **When to Use**: Usage guidance for the agent
6. **Customization**: Additional behavioral modifications

### Output Structure

The task generates:
- Agent definition file: `Clerk/src/ai_agents/bmad-framework/agents/{agent-id}.md`
- Initial task files in `tasks/` directory
- Template stubs in `templates/` directory

## Agent Creation Checklist

Before creating an agent, ensure you have:

- [ ] Clear understanding of the agent's purpose
- [ ] Identified all required commands
- [ ] Listed necessary dependencies (tasks, templates, checklists)
- [ ] Determined integration points with existing services
- [ ] Defined security requirements

## ID Generation Patterns

Agent IDs follow these conventions:

```
{domain}-{function}-{version}
```

Examples:
- `discovery-analyzer` - Discovery analysis agent
- `letter-generator` - Legal letter generation
- `compliance-checker-v2` - Version 2 of compliance checking

### Namespace Conventions

Legal agents use these namespaces:
- `discovery-*` - Discovery-related agents
- `motion-*` - Motion drafting agents
- `letter-*` - Letter generation agents
- `research-*` - Legal research agents
- `compliance-*` - Compliance verification agents

### Conflict Resolution

If an ID already exists:
1. Add version suffix (e.g., `-v2`, `-enhanced`)
2. Use more specific function name
3. Consider subdomain prefix

## Creation Examples

### Basic Agent Creation

```yaml
# Minimal agent for simple document analysis
activation-instructions:
  - STEP 1: Read THIS ENTIRE FILE
  - STEP 2: Adopt persona
  - STEP 3: Greet user

agent:
  name: Doc Analyzer
  id: doc-analyzer
  title: Document Analyst

persona:
  role: Document analysis specialist

commands:
  - help: Show commands
  - analyze: Analyze document
```

### Advanced Agent Creation

```yaml
# Full-featured discovery agent
activation-instructions:
  - STEP 1: Read THIS ENTIRE FILE
  - STEP 2: Adopt persona defined below
  - STEP 3: Greet with name and role
  - STEP 4: Load security context
  - CRITICAL: Maintain case isolation

agent:
  name: Discovery Specialist
  id: discovery-specialist-v3
  title: Senior Discovery Analysis Expert
  icon: 🔍
  whenToUse: Complex discovery analysis with ML
  customization: "Enhanced with GPT-4 capabilities"

persona:
  role: Expert legal analyst
  style: Precise, thorough, legally astute
  identity: 20+ years discovery experience
  focus: Deficiency identification
  core_principles:
    - Accuracy above all
    - Complete coverage
    - Clear documentation

commands:
  - help: Show all available commands
  - analyze: Deep analysis of discovery
  - search: Semantic search with context
  - report: Generate comprehensive report

dependencies:
  tasks:
    - analyze-rtp.md
    - ml-document-analysis.md
  templates:
    - discovery-report-tmpl.yaml
  checklists:
    - pre-analysis-validation.md
```

## Common Creation Errors

1. **Duplicate IDs**: Check existing agents first
2. **Missing Required Fields**: Use checklist above
3. **Invalid YAML**: Validate syntax before saving
4. **Circular Dependencies**: Avoid task A requiring task B requiring task A

---

[← Back to Overview](00-overview.md) | [Next: Agent Definition Phase →](02-agent-definition-phase.md)
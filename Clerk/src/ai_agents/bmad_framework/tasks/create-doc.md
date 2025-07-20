# Create Legal Document from Template

## Purpose
Generate legal documents using BMad YAML templates with appropriate legal formatting, case isolation, and jurisdiction-specific requirements.

## Task Execution

### 1. Template Discovery and Selection
- Load template from `templates/` directory or `.bmad-core/templates/`
- If no template specified, list available legal templates:
  - Motion templates (summary judgment, dismissal, etc.)
  - Letter templates (good faith, deficiency, etc.)
  - Report templates (analysis, compliance, etc.)
- Validate template has required legal metadata (jurisdiction, document type)

### 2. Case Context Validation
- Verify case_name parameter is provided
- Load case context from security context
- Ensure user has write permission for document generation
- Extract relevant case facts and legal authorities

### 3. Parse Template Structure
- Load YAML template with sections and metadata
- Identify required vs optional sections
- Check jurisdiction-specific requirements
- Note any conditional sections based on case type

### 4. Process Each Section
For each section in the template:
- Check section conditions (e.g., only for federal cases)
- Apply section-specific legal formatting rules
- If section requires case facts, search vector store
- If section requires legal authorities, retrieve citations
- Format content according to legal standards:
  - Proper citation format (Bluebook or local rules)
  - Numbered paragraphs where required
  - Signature blocks and certificates

### 5. Handle Elicitation (if enabled)
When elicit: true for a section:
- Present drafted content with legal rationale
- Offer jurisdiction-specific alternatives
- Provide options for:
  1. Proceed with current draft
  2. Add more supporting facts
  3. Include additional legal authorities
  4. Adjust tone (more aggressive/defensive)
  5. Add procedural history
  6. Include relief sought
  7. Add exhibits/attachments reference
  8. Modify for local rules
  9. Request senior review

### 6. Legal Validation
- Verify all required sections are complete
- Check citation formatting
- Validate jurisdiction requirements
- Ensure proper case caption format
- Verify signature block compliance

### 7. Save and Store Document
- Save to case-specific document folder
- Generate unique document ID
- Store metadata in database
- Update case document index
- Create audit trail entry

## Elicitation Required
elicit: configurable per template section

## WebSocket Events
- agent:task_started - Document generation started
- agent:task_progress - Section completed
- agent:section_draft - Draft ready for review
- agent:validation_complete - Document validated
- agent:task_completed - Document saved

## Legal-Specific Considerations

### Jurisdiction Handling
- Federal vs State formatting differences
- Local rule compliance
- Court-specific requirements

### Document Security
- Ensure document is tied to correct case
- Apply appropriate access controls
- Mark privileged sections if applicable

### Version Control
- Maintain document revision history
- Track who made changes and when
- Allow rollback to previous versions

### Integration Points
- Vector store for case facts
- Legal authority database
- Template management system
- Document storage (Box)
- Case management system

## Error Handling
- Missing required template fields
- Insufficient case facts
- Invalid legal citations
- Permission denied errors
- Template not found

## Example Template Structure
```yaml
metadata:
  type: motion
  subtype: summary_judgment
  jurisdiction: federal
  title: Motion for Summary Judgment

sections:
  - name: caption
    required: true
    
  - name: introduction
    elicit: true
    instruction: Draft compelling introduction stating relief sought
    
  - name: statement_of_facts
    elicit: true
    use_case_facts: true
    instruction: Present undisputed material facts
    
  - name: legal_standard
    instruction: State applicable summary judgment standard
    
  - name: argument
    elicit: true
    subsections:
      - name: issue_one
        instruction: First legal argument
      - name: issue_two
        instruction: Second legal argument
        
  - name: conclusion
    instruction: Summarize relief requested
    
  - name: signature_block
    required: true
```
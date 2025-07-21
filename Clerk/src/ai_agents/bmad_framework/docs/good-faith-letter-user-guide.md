# Good Faith Letter Generation User Guide

## Overview

The Good Faith Letter Agent automates the creation of discovery deficiency correspondence using the BMad framework. This guide walks through the complete workflow from deficiency analysis to final letter export.

## Prerequisites

1. **Completed Deficiency Analysis**: A DeficiencyReport must exist from analyzing RTP requests against discovery production
2. **Case Context**: Valid case ID and permissions
3. **Attorney Information**: Contact details for signature block

## Workflow Steps

### Step 1: Generate Initial Letter

```http
POST /api/agents/good-faith-letter/generate-letter
Authorization: Bearer {token}
X-Case-ID: {case_id}

{
  "report_id": "789e0123-e89b-12d3-a456-426614174000",
  "jurisdiction": "federal",
  "state_code": null,
  "include_evidence": true,
  "evidence_format": "inline",
  "attorney_info": {
    "name": "Jane Smith, Esq.",
    "title": "Partner",
    "firm": "Smith & Associates, P.A.",
    "bar_number": "12345",
    "address": ["123 Main Street", "Suite 400", "Miami, FL 33131"],
    "phone": "(305) 555-1234",
    "email": "jsmith@smithlaw.com"
  },
  "additional_variables": {
    "OPPOSING_COUNSEL_NAME": "John Doe, Esq.",
    "OPPOSING_LAW_FIRM": "Doe & Partners",
    "SALUTATION": "Counsel",
    "LETTER_DATE": "January 20, 2024"
  }
}
```

**Response:**
```json
{
  "letter_id": "letter-123e4567-e89b-12d3-a456-426614174000",
  "status": "draft",
  "agent_execution_id": "exec-456789",
  "preview_url": "/api/agents/good-faith-letter/preview/letter-123..."
}
```

### Step 2: Preview Generated Letter

```http
GET /api/agents/good-faith-letter/preview/{letter_id}
Authorization: Bearer {token}
X-Case-ID: {case_id}
```

**Response:**
```json
{
  "letter_id": "letter-123...",
  "status": "draft",
  "content": "Dear Counsel:\n\nI am writing to follow up on...",
  "metadata": {
    "jurisdiction": "federal",
    "created_at": "2024-01-20T14:00:00Z",
    "version": 1,
    "editable": true
  }
}
```

### Step 3: Customize Letter (Optional)

If edits are needed:

```http
PUT /api/agents/good-faith-letter/customize/{letter_id}
Authorization: Bearer {token}
X-Case-ID: {case_id}

{
  "section_edits": [
    {
      "section": "opening_paragraph",
      "content": "Dear Counsel:\n\nI am writing to address the numerous deficiencies..."
    },
    {
      "section": "closing_paragraph",
      "content": "We look forward to receiving complete responses within ten (10) days..."
    }
  ],
  "editor_notes": "Strengthened opening, clarified deadline"
}
```

### Step 4: Finalize Letter

Once approved:

```http
POST /api/agents/good-faith-letter/finalize/{letter_id}
Authorization: Bearer {token}
X-Case-ID: {case_id}

{
  "approved_by": "senior.partner@smithlaw.com",
  "export_formats": ["pdf", "docx"]
}
```

**Response:**
```json
{
  "letter_id": "letter-123...",
  "status": "finalized",
  "approved_by": "senior.partner@smithlaw.com",
  "approved_at": "2024-01-20T15:30:00Z",
  "export_urls": {
    "pdf": "/api/agents/good-faith-letter/export/letter-123.../pdf",
    "docx": "/api/agents/good-faith-letter/export/letter-123.../docx"
  }
}
```

### Step 5: Export Letter

Download in desired format:

```http
GET /api/agents/good-faith-letter/export/{letter_id}/pdf
Authorization: Bearer {token}
X-Case-ID: {case_id}
```

Returns: Binary file download with appropriate headers

## Letter Components

### Required Information

1. **Case Information**
   - Case name and number
   - Court jurisdiction

2. **Discovery Details**
   - RTP request numbers and text
   - Opposing counsel responses
   - Deficiency classifications

3. **Attorney Information**
   - Sending attorney details
   - Law firm information
   - Contact information

4. **Recipient Information**
   - Opposing counsel name
   - Law firm
   - Address

### Jurisdiction-Specific Requirements

#### Federal Letters
- FRCP Rule 37 compliance
- Meet and confer certification
- 10-14 day response period

#### State Letters
- State-specific rule citations
- Jurisdiction-specific deadlines:
  - Florida: 10 days
  - Texas: 30 days
  - California: 10-15 days
  - New York: 14-30 days

## Evidence Inclusion Options

### Inline Format (Default)
Evidence chunks are included directly in the deficiency description:

```
Request No. 5 – Not Produced. Your response stated "No responsive 
documents," however, we have identified the following responsive 
materials in your production:

- Email from John Doe dated 1/15/2023 discussing "contract terms"
  (Document ID: DOC-12345, Page 15, Relevance: 0.92)
```

### Footnote Format
Evidence is referenced with footnotes:

```
Request No. 5 – Not Produced. Your response stated "No responsive 
documents," however, responsive materials exist.[1]

[1] See Document ID: DOC-12345, Page 15 (Email discussing contract)
```

### Appendix Format
Evidence is collected in an appendix section at the end.

## Status Workflow

Letters progress through these statuses:

1. **DRAFT**: Initial generation, fully editable
2. **REVIEW**: After first edit, awaiting approval
3. **APPROVED**: Approved by senior attorney
4. **FINALIZED**: Locked for sending, export only

## Best Practices

1. **Review Thoroughly**: Always preview before finalizing
2. **Check Tone**: Ensure professional, non-accusatory language
3. **Verify Evidence**: Confirm evidence citations are accurate
4. **Follow Jurisdiction Rules**: Use correct deadlines and citations
5. **Document Edits**: Add notes explaining significant changes

## Troubleshooting

### Letter Not Generating
- Verify DeficiencyReport exists and is completed
- Check case permissions
- Ensure all required attorney info provided

### Export Failing
- Letter must be in FINALIZED status
- Check supported formats: pdf, docx, html
- Verify case access permissions

### Evidence Not Appearing
- Set `include_evidence: true` in request
- Check evidence exists in DeficiencyReport
- Verify relevance scores meet threshold

## WebSocket Events

Monitor real-time progress:

```javascript
socket.on('agent:activated', (data) => {
  console.log('Letter generation started:', data.execution_id);
});

socket.on('letter:generation_started', (data) => {
  console.log('Processing deficiency report:', data.report_id);
});

socket.on('letter:draft_created', (data) => {
  console.log('Draft ready:', data.letter_id);
});

socket.on('letter:finalized', (data) => {
  console.log('Letter finalized:', data.letter_id);
});
```

## API Rate Limits

- Letter generation: 10 per minute per case
- Customization: 30 edits per hour per letter
- Export: 20 exports per hour per case

## Support

For assistance:
- Check letter requirements checklists in BMad framework
- Review jurisdiction-specific requirements
- Contact system administrator for permissions issues
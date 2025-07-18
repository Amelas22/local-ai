# Data Models and Schema Changes

## New Data Models

**DeficiencyReport**
- **Purpose:** Root model for storing complete deficiency analysis results
- **Integration:** Links to discovery production and case records

**Key Attributes:**
- id: UUID - Unique identifier
- case_name: str - Case identifier for isolation
- production_id: UUID - Links to discovery production
- rtp_document_id: UUID - Reference to uploaded RTP document
- oc_response_document_id: UUID - Reference to OC response document
- analysis_status: str - pending|processing|completed|failed
- created_at: datetime - Analysis start time
- completed_at: datetime - Analysis completion time
- total_requests: int - Number of RTP items analyzed
- summary_statistics: JSON - Breakdown by category

**Relationships:**
- **With Existing:** Links to discovery_productions table via production_id
- **With New:** One-to-many with DeficiencyItem records

**DeficiencyItem**
- **Purpose:** Individual RTP request analysis result
- **Integration:** Child of DeficiencyReport, references vector search results

**Key Attributes:**
- id: UUID - Unique identifier
- report_id: UUID - Parent DeficiencyReport reference
- request_number: str - RTP item number (e.g., "RFP No. 12")
- request_text: str - Full text of the RTP request
- oc_response_text: str - Opposing counsel's response
- classification: str - fully_produced|partially_produced|not_produced|no_responsive_docs
- confidence_score: float - AI confidence in classification (0-1)
- evidence_chunks: JSON - Array of matched document chunks with metadata
- reviewer_notes: str - Legal team annotations
- modified_by: str - User who made changes
- modified_at: datetime - Last modification time

**Relationships:**
- **With Existing:** References document chunks via evidence_chunks JSON
- **With New:** Many-to-one with DeficiencyReport

**GoodFaithLetter**
- **Purpose:** Generated letter drafts with version tracking
- **Integration:** Links to DeficiencyReport for source data

**Key Attributes:**
- id: UUID - Unique identifier
- report_id: UUID - Source DeficiencyReport
- template_name: str - Template used for generation
- version: int - Draft version number
- content: str - Letter content in markdown
- metadata: JSON - Jurisdiction, deadlines, etc.
- created_by: str - User who generated
- created_at: datetime - Generation timestamp

**Relationships:**
- **With Existing:** Uses case_name for access control
- **With New:** Many-to-one with DeficiencyReport

## Schema Integration Strategy

**Database Changes Required:**
- **New Tables:** deficiency_reports, deficiency_items, good_faith_letters
- **Modified Tables:** discovery_productions (add has_deficiency_analysis boolean)
- **New Indexes:** case_name + created_at for reports, report_id + request_number for items
- **Migration Strategy:** Alembic migration with zero downtime deployment

**Backward Compatibility:**
- All changes are additive - no existing columns modified
- Discovery pipeline continues to function without deficiency analysis
- Feature flag controls whether analysis is triggered

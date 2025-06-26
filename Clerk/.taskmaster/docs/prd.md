# Product Requirements Document: Legal AI Knowledge Management & Motion Drafting System
**Project Code Name: Clerk**

## 1. Introduction/Overview

This feature creates an AI-powered system for our law firm to automatically organize case documents and draft legal motions. Currently, attorneys spend hours searching through case files and drafting responses to motions from scratch. This system will solve these problems by:

- Automatically reading and organizing all PDF documents from our Box folders
- Creating searchable databases for each legal case
- Using AI to draft responses to opposing counsel's motions
- Tracking deadlines and assigning daily tasks to team members (Future state -- not in scope for Phase 1)

**Goal:** Build a system that saves attorney time on document research and motion drafting while ensuring all case information remains separate and secure.

## 2. Goals

1. **Reduce motion drafting time** from 8+ hours to under 2 hours per motion
2. **Enable instant access** to any case information through natural language questions
3. **Achieve 80% daily usage** by all attorneys within 6 months of launch
4. **Maintain 100% data isolation** between different legal cases
5. **Process 100% of existing PDF documents** from Box into searchable format (approximately 4,000-6,000 documents across all cases)

## 3. User Stories

### Attorney Stories
1. **As an attorney**, I want to upload a motion filed by opposing counsel and receive a complete outline for our response, so that I can focus on legal strategy rather than research.

2. **As an attorney**, I want to ask questions like "What did the expert witness say about the accident timeline?" or "What were the patient's vitals on the day of the incident?" and get immediate answers with source documents, so that I can quickly prepare for depositions.

3. **As an attorney**, I want to provide basic case facts and have the system draft an initial complaint using our firm's style and successful examples, so that I can file cases faster.

4. **As an attorney**, I want clear explanations when the AI cannot answer my question (like "I don't have enough information about that topic in this case"), so that I know what additional research is needed.

## 4. Functional Requirements

1. **The system must connect to Box API** and access all matter folders
2. **The system must extract text from PDF documents** (OCR already completed by firm) including:
   - Motion practice documents
   - Medical records
   - Expert reports
   - Discovery documents
   - Correspondence
3. **The system must detect duplicate documents** using file hashes and avoid processing the same content twice
4. **The system must handle large PDF files** (medical records can be 200+ pages) by:
   - Splitting into manageable sections
   - Summarizing each section
   - Creating contextual chunks with summaries
5. **The system must store document chunks in a vector database** with metadata including:
   - Matter ID
   - Original document location
   - Document type (pleading, expert report, etc.)
   - Date added
7. **The system must maintain a separate firm-wide knowledge base** containing:
   - Successful motion examples
   - Firm writing style guides
   - Legal argument templates
7. **The system must allow users to upload a defense motion** and generate:
   - Research from the case database
   - Research from external sources (Perplexity, Jina APIs)
   - A complete outline with legal citations
   - Export to spreadsheet format
8. **The system must allow users to edit outlines in a spreadsheet** and mark them ready for drafting
9. **The system must generate complete motion drafts** in .docx format, drafting section by section
10. **The system must save all generated documents back to the correct Box folder**
11. **The system must track deadlines from:**
    - Manual entry by staff
    - Trial orders uploaded to Box
    - Filing timestamps on documents
12. **The system must provide a chat interface** where any user can ask questions about any case
13. **The system must ensure case data isolation** - facts from Case A must never appear in responses about Case B
14. **The system must format legal citations in Bluebook style** but must NEVER create fictional citations
15. **The system must handle document versioning** by deleting old vectors when updated documents are uploaded
16. **The system must maintain an error log** that tracks:
    - Failed document processing attempts
    - API connection failures
    - Cases where AI cannot provide answers
17. **The system must chunk documents at ~1400 characters** and add contextual summaries to each chunk before storing

## 5. Non-Goals (Out of Scope)

1. This feature will **NOT** integrate with Westlaw or LexisNexis for citation checking (APIs not available)
2. This feature will **NOT** handle non-PDF documents (Word docs, emails, etc.)
3. This feature will **NOT** automatically file documents with the court
4. This feature will **NOT** manage billing or timekeeping
5. This feature will **NOT** provide legal advice or replace attorney judgment
6. This feature will **NOT** handle documents that aren't already OCR'd

## 6. Design Considerations

### User Interface
- Primary interface: Open WebUI (ChatGPT-like interface)
- Users interact through natural language chat
- Simple web forms for deadline entry
- Frontend still in development

### User Flow Example
1. Frontend WIP: Current Frontend is a Google Sheet
2. Attorney opens Google Sheet and inputs case name, Box file_id number for motion and complaint. Database name is autopopulated based on case name. 
3. Attorney updates status to "Ready for Outline"
4. n8n workflow beings outline generation by downloading motion and complaint from Box, then pushes motion to legal-motion-api to analyze argument and continues the process.
5. Once complete, the document outline is uploaded to Box and the Google Sheet is updated. 
6. Attorney reviews outline and makes edits.
7. Once edits are complete, the attorney marks the document as "Ready for Draft"
8. n8n workflow for draft generation begins.
9. Once complete, the response draft is uploaded to Box and the Google Sheet is updated.

## 7. Technical Considerations

### Infrastructure Setup
- **Python 3.11+** for document processing scripts
- **Qdrant** for vector database (single collection with metadata filtering)
- **Box API** for document access
- **Open WebUI** for chat interface
- **n8n** for workflow automation

### Key Technical Decisions
- All infrastructure runs locally except LLM API calls
- Use existing Box folder structure to organize documents
- Plan for significant storage needs due to medical records and extensive motion practice
- Deploy to VPS for production use with caching layer (currently deployed to hostinger)
- Use file hashes for duplicate detection
- Implement contextual chunking with ~1400 character chunks plus summaries

### Integration Points
- Box API (must maintain authentication)
- Perplexity Deep Research API
- Jina Deep Search API
- Future: Potential Westlaw/LexisNexis integration

## 8. Success Metrics

1. **Primary Metric:** 80% of attorneys use the system daily after 6 months
2. **Time Savings:** Average motion outline generated in under 15 minutes
3. **Accuracy:** Zero instances of case data mixing between matters
4. **Adoption:** 10+ queries per day per attorney after first month
5. **Quality:** 75% of generated outlines require only minor edits

## 9. Resolved Decisions (Previously Open Questions)

1. **Duplicate Detection:** Use file hashes to identify duplicate documents.

2. **Chunk Size:** Document chunks will be ~1400 characters with contextual summaries added before vector storage.

3. **LLM Selection:** To be determined based on testing and performance requirements.

4. **Permissions:** All users have access to all cases (no restrictions needed).

5. **Version Control:** Keep only the most recent version of documents. Delete old vectors when updated versions are uploaded.

6. **Training Data:** Final filed motions will be used to improve the system while maintaining client confidentiality.

7. **Error Handling:** 
   - AI provides clear explanations when it cannot complete tasks (e.g., "I don't have enough information to answer that")
   - Maintain error log for debugging and system improvement

8. **Citation Format:** System will format legal citations in proper Bluebook style but MUST NOT create fictional citations.

9. **Performance:** 
   - Deploy to VPS for production use
   - Implement caching for frequently accessed data
   - Response time is not critical (quality over speed)

10. **Medical Record Processing:** 
    - Split large documents into sections
    - Summarize each section
    - Combine summaries for contextual chunking
    - Different context window than standard legal documents

## 10. Remaining Open Questions

1. **Contextual Chunking Method:** What specific approach should we use to generate the contextual summary that gets added to each 1400-character chunk?

2. **VPS Requirements:** What are the minimum server specifications needed to handle 240,000+ vectors and concurrent users?

3. **Caching Strategy:** Should we cache at the query level, document level, or chunk level? What cache invalidation strategy?

4. **Citation Verification:** How do we ensure the AI never creates fictional citations? Should we maintain a citation database for validation?

## 11. Project File Structure

WIP

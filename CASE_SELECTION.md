## FEATURE: Case Context Management with Multi-Tenant Data Isolation

Overview

This update introduces a centralized case selection system that enforces strict data isolation boundaries and manages database scope across the entire Clerk interface. The implementation ensures complete separation between cases while preparing the architecture for multi-law firm deployment.

Core Implementation Requirements

The foundation of this update begins with adjusting our case naming system. Currently, case names are automatically generated from BOX folder names through the document injector. We will implement an "Add Case Function" in the frontend that allows users to create case names directly, storing them in Supabase before creating the corresponding collections in Qdrant. Case names will be limited to 50 characters to accommodate Qdrant's 63-character collection name limit. To prevent naming collisions and ensure uniqueness, we'll implement case ID hashing for collection names while maintaining a clear case_name to collection_name mapping in Supabase.
For database isolation, we'll transition to using Qdrant's database feature where each case receives its own database instance through QdrantVectorStore(database_name=case_name). This provides true isolation beyond our current collection-based approach. When a case is selected from the sidebar dropdown, the system will automatically load all case-specific databases following standardized naming patterns such as {caseName}_facts, {caseName}_timeline, and {caseName}_depositions. A registry of these naming patterns will ensure proper identification and scoping of case-specific collections.

Global Context Management

Once a case is selected, that context propagates throughout the entire interface. All components that previously required case name input will automatically inherit the global case context. Case selection fields in other views including discovery processing and document upload interfaces will convert to read-only display elements showing the current active case. Users will maintain visual confirmation of their current case context across all interface screens, with case changes only permitted through the primary sidebar dropdown. This eliminates confusion about which case is currently active and prevents accidental cross-case data contamination.

Shared Resource Configuration

The system will implement intelligent differentiation between case-specific and shared legal resources. Shared databases such as fmscr_regulations and florida_statutes will be identified through a configuration system and excluded from case-specific dropdown menus. These shared resources remain globally available regardless of case selection, ensuring users always have access to general legal reference materials while maintaining strict isolation of case-specific data.

Multi-Tenant Architecture

Law firm context will serve as the top-level data boundary, displayed prominently in the top bar of the Clerk interface. Users will only access cases within their assigned law firm, with database architecture prepared for multi-firm deployment while maintaining full functionality for current single-firm use. This creates a scalable foundation for SaaS deployment without disrupting existing workflows.

Technical Implementation Details

Data isolation enforcement occurs at multiple levels. Server-side validation of case context happens on every request, with middleware validating case access permissions before any data operations. The system maintains case ownership tracking and implements comprehensive audit logging for all case data access. Vector queries are automatically scoped to the selected case's databases, with case-specific vector store instances reducing connection overhead.
Performance optimization includes collection optimization based on case size and implementation of collection archiving for closed cases. Error handling improvements provide clear messages for case isolation violations, automatic fallback mechanisms for collection creation failures, and validation ensuring case_name consistency throughout the entire data pipeline.

Security and Compliance

Law firm boundaries are enforced at the database query level, not just the application layer. Every case context change triggers audit logging, creating a complete trail of data access patterns. Strict validation rules prevent unauthorized cross-case data access, with automatic detection and prevention of any queries that might violate case isolation boundaries.

This comprehensive update ensures that Case A data never appears in Case B responses, reduces query scope by filtering to relevant databases upfront, eliminates user confusion about active case context, and creates a foundation for secure multi-firm deployment. The implementation maintains backward compatibility while establishing the infrastructure necessary for future expansion into a true multi-tenant SaaS platform.

## EXAMPLES:

`Clerk/src/vector_storage/qdrant_store.py`, `Clerk/src/vector_storage/embeddings.py`, `Clerk/src/vector_storage/sparse_encoder.py`: python files for vector storage and embeddings
`Clerk/src/document_injector.py`: python file for document processing and injection into Qdrant
`Clerk/src/ai_agents/fact_extractor.py`: python file for fact extraction

Strucutre of the Qdrant collections:

```
Qdrant Collections:
├── Case-Specific (Isolated per matter)
│   ├── {case_name}               # Full case database for RAG search
│   ├── {case_name}_facts         # Extracted facts with embeddings
│   ├── {case_name}_timeline      # Chronological events
│   └── {case_name}_depositions   # Deposition citations
│
└── Shared Knowledge (Firm-wide access)
    ├── florida_statutes          # Florida statutory law
    ├── fmcsr_regulations         # Federal motor carrier regulations
    ├── case_law_precedents       # Important case law (future)
    └── legal_standards           # Common legal tests (future)
```

## DOCUMENTATION:

url: https://react.dev/reference/react
why: React documentation

url: https://python-socketio.readthedocs.io/en/stable/api.html
why: SocketIO documentation

url: https://supabase.com/llms/python.txt
why: Supabase documentation

file: CLAUDE.md
why: rules for project strucutre and testing

mcp: Context7 MCP Server
why: Use to look up additional documentation by library name (qdrant, for example)

mcp: Brave-search MCP Server
why: Use to search the web for information in your research

file: docker-compose.yml
why: docker compose file for local development with tech stack and full services

## OTHER CONSIDERATIONS:

Always make sure you are properly using socketio with React 19. Current implementation works.
The Clerk system is part of a tech stack that is run via the python start_services --profile cpu command. When rebuilding, make sure new services are added to the docker-compose.yml file. If a container needs to be rebuilt or restarted, ensure it remains part of the stack.

Potential Vulnerabilities:

1. No explicit database-level isolation - All cases share same Qdrant instance
2. Collection naming collisions - Similar case names could collide after sanitization
3. Cross-case queries possible - Nothing prevents querying wrong collection if name is known
4. Shared vector store instance - All operations use same QdrantVectorStore()

AI Agents:
- Most agents expect database_name parameter (which is the case/collection name)
- Enhanced RAG agent has explicit case isolation with CaseIsolationConfig
- Fact extractors, deposition parsers, and exhibit indexers all require case_name
- AI Agents may need to be updated to utilize new case naming strucutre


Recommendations for Enhancement:

1. Implement True Database Isolation
- Use Qdrant's database feature: QdrantVectorStore(database_name=case_name)
- Each case gets its own database, not just collection

2. Add Case Name Validation
- Implement strict validation rules
- Use case ID hashing for collection names to prevent collisions
- Maintain case_name → collection_name mapping

3. Enforce Access Control
- Add middleware to validate case access permissions
- Implement case ownership tracking
- Add audit logging for all case data access

4. Improve Error Handling
- Better error messages for case isolation violations
- Automatic fallback for collection creation failures
- Validation that case_name matches throughout pipeline

5. Consider Performance
- Case-specific vector store instances to reduce connection overhead
- Collection optimization per case size
- Implement collection archiving for closed cases


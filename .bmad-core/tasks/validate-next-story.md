# Validate Next Story Task

## Purpose

To comprehensively validate a story draft before implementation begins, ensuring it is complete, accurate, and provides sufficient context for successful development. This task identifies issues and gaps that need to be addressed, preventing hallucinations and ensuring implementation readiness.

## SEQUENTIAL Task Execution (Do not proceed until current Task is complete)

### 0. Load Core Configuration and Inputs

- Load `.bmad-core/core-config.yaml`
- If the file does not exist, HALT and inform the user: "core-config.yaml not found. This file is required for story validation."
- Extract key configurations: `devStoryLocation`, `prd.*`, `architecture.*`
- Identify and load the following inputs:
  - **Story file**: The drafted story to validate (provided by user or discovered in `devStoryLocation`)
  - **Parent epic**: The epic containing this story's requirements
  - **Architecture documents**: Based on configuration (sharded or monolithic)
  - **Story template**: `bmad-core/templates/story-tmpl.md` for completeness validation

### 1. Template Completeness Validation

- Load `bmad-core/templates/story-tmpl.md` and extract all section headings from the template
- **Missing sections check**: Compare story sections against template sections to verify all required sections are present
- **Placeholder validation**: Ensure no template placeholders remain unfilled (e.g., `{{EpicNum}}`, `{{role}}`, `_TBD_`)
- **Agent section verification**: Confirm all sections from template exist for future agent use
- **Structure compliance**: Verify story follows template structure and formatting

### 2. File Structure and Source Tree Validation

- **File paths clarity**: Are new/existing files to be created/modified clearly specified?
- **Source tree relevance**: Is relevant project structure included in Dev Notes?
- **Directory structure**: Are new directories/components properly located according to project structure?
- **File creation sequence**: Do tasks specify where files should be created in logical order?
- **Path accuracy**: Are file paths consistent with project structure from architecture docs?

### 3. UI/Frontend Completeness Validation (if applicable)

- **Component specifications**: Are UI components sufficiently detailed for implementation?
- **Styling/design guidance**: Is visual implementation guidance clear?
- **User interaction flows**: Are UX patterns and behaviors specified?
- **Responsive/accessibility**: Are these considerations addressed if required?
- **Integration points**: Are frontend-backend integration points clear?

### 4. Acceptance Criteria Satisfaction Assessment

- **AC coverage**: Will all acceptance criteria be satisfied by the listed tasks?
- **AC testability**: Are acceptance criteria measurable and verifiable?
- **Missing scenarios**: Are edge cases or error conditions covered?
- **Success definition**: Is "done" clearly defined for each AC?
- **Task-AC mapping**: Are tasks properly linked to specific acceptance criteria?

### 5. Validation and Testing Instructions Review (TDD Focus)

- **TDD structure validation**: Are tasks organized into Phase 1 (Test Creation) and Phase 2 (Implementation)?
- **Test-first approach**: Do test creation tasks precede implementation tasks?
- **Test coverage requirements**: Is the Test Coverage Requirements section properly populated?
- **Test approach clarity**: Are testing methods clearly specified?
- **Test scenarios**: Are key test cases identified for each acceptance criterion?
- **Validation steps**: Are acceptance criteria validation steps clear?
- **Testing tools/frameworks**: Are required testing tools specified?
- **Test data requirements**: Are test data needs identified?
- **RED phase verification**: Do test tasks include verification that tests fail initially?

### 6. Security Considerations Assessment (if applicable)

- **Security requirements**: Are security needs identified and addressed?
- **Authentication/authorization**: Are access controls specified?
- **Data protection**: Are sensitive data handling requirements clear?
- **Vulnerability prevention**: Are common security issues addressed?
- **Compliance requirements**: Are regulatory/compliance needs addressed?

### 7. Tasks/Subtasks Sequence Validation (TDD Workflow)

- **TDD phase separation**: Are tasks clearly divided into Phase 1 (Test Creation) and Phase 2 (Implementation)?
- **Test-first sequence**: Do ALL test creation tasks come before implementation tasks?
- **Phase completeness**: Does Phase 1 create tests for ALL acceptance criteria?
- **Logical order**: Do tasks within each phase follow proper sequence?
- **Dependencies**: Are task dependencies clear and correct?
- **Granularity**: Are tasks appropriately sized and actionable?
- **Completeness**: Do tasks cover all requirements and acceptance criteria?
- **Blocking issues**: Are there any tasks that would block others?
- **Test-to-implementation mapping**: Can each implementation task be traced to corresponding tests?

### 8. Anti-Hallucination Verification

- **Source verification**: Every technical claim must be traceable to source documents
- **Architecture alignment**: Dev Notes content matches architecture specifications
- **No invented details**: Flag any technical decisions not supported by source documents
- **Reference accuracy**: Verify all source references are correct and accessible
- **Fact checking**: Cross-reference claims against epic and architecture documents

### 9. Dev Agent Implementation Readiness

- **Self-contained context**: Can the story be implemented without reading external docs?
- **Clear instructions**: Are implementation steps unambiguous?
- **Complete technical context**: Are all required technical details present in Dev Notes?
- **Missing information**: Identify any critical information gaps
- **Actionability**: Are all tasks actionable by a development agent?

### 10. Generate Validation Report

Provide a structured validation report including:

#### Template Compliance Issues

- Missing sections from story template
- Unfilled placeholders or template variables
- Structural formatting issues

#### Critical Issues (Must Fix - Story Blocked)

- Missing essential information for implementation
- Inaccurate or unverifiable technical claims
- Incomplete acceptance criteria coverage
- Missing required sections
- TDD workflow violations (no test/implementation phase separation)
- Implementation tasks before test creation tasks
- Missing test coverage requirements section
- No tests defined for one or more acceptance criteria

#### Should-Fix Issues (Important Quality Improvements)

- Unclear implementation guidance
- Missing security considerations
- Task sequencing problems
- Incomplete testing instructions

#### Nice-to-Have Improvements (Optional Enhancements)

- Additional context that would help implementation
- Clarifications that would improve efficiency
- Documentation improvements

#### Anti-Hallucination Findings

- Unverifiable technical claims
- Missing source references
- Inconsistencies with architecture documents
- Invented libraries, patterns, or standards

#### TDD Readiness Assessment

- **Test Phase Completeness**: Are all ACs covered by test tasks?
- **Implementation Phase Alignment**: Do implementation tasks map to tests?
- **Coverage Requirements**: Are coverage targets clearly defined?
- **Test-First Compliance**: Is the TDD workflow properly structured?

#### Final Assessment

- **GO**: Story is ready for TDD workflow (test creation → review → implementation)
- **NO-GO**: Story requires fixes before entering TDD workflow
- **TDD Readiness Score**: 1-10 scale
- **Implementation Readiness Score**: 1-10 scale
- **Confidence Level**: High/Medium/Low for successful TDD implementation
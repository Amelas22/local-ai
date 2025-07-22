# TDD Story Checklist

This checklist validates that stories properly incorporate Test-Driven Development requirements, ensuring developers can follow a test-first approach with clear guidance on what tests to write before implementation.

[[LLM: INITIALIZATION INSTRUCTIONS - TDD STORY VALIDATION

Before proceeding with this checklist, ensure you have:
1. The story document with TDD requirements
2. Access to testing standards from architecture
3. Understanding of the test-engineer TDD principles
4. The story's acceptance criteria and tasks

VALIDATION FOCUS:
- Test scenarios exist BEFORE implementation tasks
- Coverage requirements are explicit
- Red-Green-Refactor cycle is clear
- Tests focus on behavior, not implementation

REMEMBER: TDD means tests are written FIRST, not after.]]

## 1. TEST SCENARIO COMPLETENESS

[[LLM: Every feature needs test scenarios defined upfront. Check:
1. Each acceptance criterion has corresponding test scenarios
2. Test scenarios use Given-When-Then format
3. Happy path AND error cases are covered
4. Tests focus on WHAT, not HOW
5. Test boundaries (unit/integration/e2e) are clear]]

- [ ] Test scenarios exist for ALL acceptance criteria
- [ ] Each test scenario follows Given-When-Then format
- [ ] Both positive and negative test cases are defined
- [ ] Error handling scenarios are explicitly tested
- [ ] Test types (unit/integration/e2e) are specified
- [ ] Edge cases and boundary conditions are covered

## 2. COVERAGE REQUIREMENTS

[[LLM: Coverage targets ensure quality. Verify:
1. Overall coverage target is specified (minimum 80%)
2. Critical paths requiring 100% coverage are identified
3. Coverage exceptions (if any) are justified
4. Coverage is measurable and verifiable
5. Both line and branch coverage are considered]]

- [ ] Minimum coverage target is explicitly stated (80%+)
- [ ] Critical paths requiring 100% coverage are listed
- [ ] Coverage measurement approach is defined
- [ ] Any coverage exceptions are justified with reasoning
- [ ] Coverage includes both functionality and error paths

## 3. RED-GREEN-REFACTOR STRUCTURE

[[LLM: TDD follows a specific cycle. Ensure:
1. Tasks show clear Red phase (write failing tests)
2. Green phase tasks are minimal implementations
3. Refactor phase is explicitly planned
4. Cycle repeats for each feature increment
5. No implementation before test writing]]

- [ ] Story tasks start with "Write test for..." items
- [ ] Implementation tasks reference specific tests to pass
- [ ] Refactoring tasks are included after green phase
- [ ] Task order enforces test-first approach
- [ ] Each feature follows complete TDD cycle

## 4. TEST IMPLEMENTATION GUIDANCE

[[LLM: Developers need clear test writing guidance. Check:
1. Test framework/tools are specified
2. Test file locations follow project standards
3. Test data/fixtures approach is defined
4. Mocking/stubbing guidance is provided
5. Test naming conventions are clear]]

- [ ] Testing framework and tools are specified
- [ ] Test file locations match project structure
- [ ] Test naming conventions are defined
- [ ] Mock/stub requirements are identified
- [ ] Test data management approach is clear

## 5. BEHAVIORAL TEST FOCUS

[[LLM: Good tests focus on behavior, not implementation. Verify:
1. Tests describe WHAT the code should do
2. Tests avoid HOW the code works internally
3. Tests remain valid even if implementation changes
4. Tests are readable as specifications
5. Tests avoid testing private methods]]

- [ ] Test scenarios describe expected behaviors
- [ ] Tests are implementation-agnostic
- [ ] Test descriptions read like specifications
- [ ] No tests for private/internal methods
- [ ] Tests focus on public interfaces and outcomes

## 6. TDD ANTI-PATTERN CHECK

[[LLM: Avoid common TDD mistakes. Ensure story DOESN'T:
1. Define implementation before tests
2. Write all tests at once (should be incremental)
3. Skip refactoring phase
4. Test implementation details
5. Have vague or untestable criteria]]

- [ ] No implementation details before test definitions
- [ ] Tests are incremental, not all-at-once
- [ ] Refactoring is explicitly included
- [ ] No tests coupled to implementation
- [ ] All acceptance criteria are testable

## VALIDATION RESULT

[[LLM: TDD VALIDATION REPORT

Generate a comprehensive validation report:

1. TDD Readiness Assessment
   - Status: TDD-READY / NEEDS TDD WORK / NOT TDD-COMPLIANT
   - TDD Score (1-10)
   - Test-first feasibility

2. Fill validation table:
   - PASS: TDD requirement fully met
   - PARTIAL: Some TDD elements present
   - FAIL: Missing critical TDD components

3. Specific TDD Gaps (if any)
   - List missing test scenarios
   - Identify unclear coverage requirements
   - Note any test-last patterns

4. Developer TDD Perspective
   - Can developer start by writing tests?
   - Are test scenarios clear enough?
   - Will TDD cycle be natural to follow?

Be strict - TDD requires discipline and the story must enforce it.]]

| TDD Requirement                  | Status | Issues |
| -------------------------------- | ------ | ------ |
| 1. Test Scenario Completeness    | _TBD_  |        |
| 2. Coverage Requirements         | _TBD_  |        |
| 3. Red-Green-Refactor Structure  | _TBD_  |        |
| 4. Test Implementation Guidance  | _TBD_  |        |
| 5. Behavioral Test Focus         | _TBD_  |        |
| 6. TDD Anti-Pattern Check        | _TBD_  |        |

**TDD Compliance Assessment:**

- TDD-READY: Story enforces test-first development
- NEEDS TDD WORK: Story requires updates for TDD compliance
- NOT TDD-COMPLIANT: Story follows test-last approach

**Recommended Actions:**
[List specific steps to achieve TDD compliance]
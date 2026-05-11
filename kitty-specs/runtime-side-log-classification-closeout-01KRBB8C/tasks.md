# Tasks: Runtime Side-Log Classification Closeout

**Mission**: `runtime-side-log-classification-closeout-01KRBB8C`  
**Target branch**: `main`

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|---------:|
| T001 | Run test suite: test_teamspace_migration.py, test_events.py, test_contract_parity.py | WP01 | |
| T002 | Run ruff + mypy on teamspace_migration.py | WP01 | [P] |
| T003 | Verify fixture coverage: MissionNextInvoked, NextStepIssued, MissionRunStarted | WP01 | |
| T004 | Verify status_authority and direct_teamspace_import are false for all runtime event types | WP01 | |
| T005 | Verify CLI dry-run boundary: spec-kitty doctor --teamspace-dry-run on runtime repo | WP01 | |
| T006 | Write wp01-verification-results.md with all evidence | WP01 | |
| T007 | Post evidence comment on spec-kitty-runtime#17 and close it | WP02 | |
| T008 | Post progress comment on spec-kitty#920 | WP02 | |
| T009 | Write wp02-issue-closeout-evidence.md | WP02 | |

## Work Packages

### WP01: Verify Acceptance Criteria Against Main

**Priority**: P0  
**Dependencies**: none  
**Execution mode**: planning_artifact (operational verification steps)

- [ ] T001 Run test suite (WP01)
- [ ] T002 Run ruff + mypy (WP01)
- [ ] T003 Verify fixture coverage (WP01)
- [ ] T004 Verify status_authority/direct_teamspace_import (WP01)
- [ ] T005 Verify CLI dry-run boundary (WP01)
- [ ] T006 Write wp01-verification-results.md (WP01)

**Definition of Done**: All 6 FRs (FR-001 through FR-007) verified; evidence written to `checklists/wp01-verification-results.md`.

### WP02: Issue Closeout

**Priority**: P0  
**Dependencies**: WP01  
**Execution mode**: planning_artifact (GitHub actions + evidence file)

- [ ] T007 Close spec-kitty-runtime#17 with evidence comment (WP02)
- [ ] T008 Post progress on spec-kitty#920 (WP02)
- [ ] T009 Write wp02-issue-closeout-evidence.md (WP02)

**Definition of Done**: #17 CLOSED; #920 updated; evidence written to `checklists/wp02-issue-closeout-evidence.md`.

## FR Coverage

| WP | Spec FRs |
|----|---------|
| WP01 | FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-007, NFR-001, NFR-002 |
| WP02 | FR-008, FR-009, C-001, C-002 |

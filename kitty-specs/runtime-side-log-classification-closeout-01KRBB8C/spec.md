# Runtime Side-Log Classification Closeout

## Overview

PR #19 (`feat: classify runtime logs for TeamSpace migration`) is already merged on `main`.
This mission verifies all acceptance criteria from issue `spec-kitty-runtime#17` are met,
then closes the issue with evidence.

## Goals

- Verify all acceptance criteria from `spec-kitty-runtime#17` against current `main`.
- Confirm the runtime `teamspace_migration.py` classifier correctly labels runtime logs as
  `local_only_side_log` / `deferred_not_launch_import` with `status_authority: false`.
- Confirm `spec-kitty` CLI dry-run boundary: runtime side logs reported as skipped, not as status transitions.
- Close `spec-kitty-runtime#17` with documented evidence.
- Post a progress update on parent epic `spec-kitty#920`.

## Non-Goals

- **NG-1**: This mission does not implement new features. All code changes landed in PR #19.
- **NG-2**: This mission does not modify `src/spec_kitty_runtime/` source code unless a
  verification failure requires a targeted fix.
- **NG-3**: This mission does not close `spec-kitty#920`; that closes only after all three
  missions in `start-here.md` are complete.

## Decisions

- **D-1**: If any acceptance criterion fails, a targeted fix PR is required before closing #17.
- **D-2**: CLI dry-run evidence from Mission 1 WP04 T016 (spec-kitty-runtime dry-run: valid=true, errors=[], side_logs=[]) constitutes valid CLI boundary evidence.
- **D-3**: The `spec-kitty` CLI's use of `side_logs` array (not `side_logs_skipped` scalar) is the actual schema; all evidence uses actual field names.

## Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | `uv run pytest tests/test_teamspace_migration.py tests/test_events.py tests/test_contract_parity.py -q` passes on current `main` with all 11 tests. | Approved |
| FR-002 | Tests include fixtures for `MissionNextInvoked`, `NextStepIssued`, and `MissionRunStarted` event types. | Approved |
| FR-003 | `is_teamspace_status_authority_event_type()` returns `False` for all runtime event types and `True` only for `WPStatusChanged`. | Approved |
| FR-004 | `RuntimeLogClassification` output has `status_authority: false`, `direct_teamspace_import: false`, `disposition: local_only_side_log`. | Approved |
| FR-005 | Unknown runtime event types appear in `unknown_event_types` field (not silently swallowed). | Approved |
| FR-006 | `spec-kitty doctor mission-state --teamspace-dry-run --json` on spec-kitty-runtime repo returns `valid: true`, `errors: []`. | Approved |
| FR-007 | No runtime log produces a status transition envelope in dry-run output. | Approved |
| FR-008 | `spec-kitty-runtime#17` is closed with an evidence comment referencing test results, PR #19, and the CLI dry-run result. | Approved |
| FR-009 | `spec-kitty#920` receives a progress comment noting Mission 2 completion. | Approved |

## Non-Functional Requirements

| ID | Requirement | Threshold | Status |
|----|-------------|-----------|--------|
| NFR-001 | All tests pass in < 30s on the installed uv environment. | < 30s | Approved |
| NFR-002 | ruff and mypy (strict, follow-imports=skip) pass on teamspace_migration.py. | Zero errors | Approved |

## Constraints

| ID | Constraint | Status |
|----|------------|--------|
| C-001 | Do not close #920 — that requires all three missions to complete. | Approved |
| C-002 | Do not add new source code unless a verification failure requires it. | Approved |

## Success Criteria

1. All 11 tests pass on current `main`.
2. ruff and mypy clean on `teamspace_migration.py`.
3. CLI dry-run for spec-kitty-runtime: `valid: true`, `errors: []`.
4. No runtime log treated as a status transition.
5. `spec-kitty-runtime#17` closed with evidence.
6. `spec-kitty#920` updated with Mission 2 completion note.

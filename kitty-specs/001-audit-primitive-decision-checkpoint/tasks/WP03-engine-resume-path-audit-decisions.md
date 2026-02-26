---
work_package_id: WP03
title: Engine Resume Path for Audit Decisions
lane: "for_review"
dependencies: '[]'
base_branch: main
base_commit: 31af87b219286d03319240adfab9154b312fc19d
created_at: '2026-02-26T14:39:28.494768+00:00'
subtasks:
- T014
- T015
- T016
- T017
- T018
- T019
phase: Phase 3 - Engine Integration
assignee: ''
agent: claude-implementer
shell_pid: '5370'
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-02-26T00:00:00Z'
  lane: planned
  agent: system
  action: Prompt generated via /spec-kitty.specify
depends_on:
- WP02
feature: 001-audit-primitive-decision-checkpoint
---

# Work Package Prompt: WP03 – Engine Resume Path for Audit Decisions

## Context

This WP builds on WP02 (planner). The engine at `src/spec_kitty_runtime/engine.py` contains `provide_decision_answer` which currently handles `input:` prefixed decision IDs to write answers into `snapshot.inputs`.

Audit decisions use a different prefix (`audit:`) and different semantics:
- `"approve"` → add audit step to `completed_steps`, run continues
- `"reject"` → set `blocked_reason`, run is permanently blocked

**Prerequisites**: WP01 (schema) and WP02 (planner) must be complete.

## Objective

Extend `provide_decision_answer` in `engine.py` to handle `audit:` prefixed decision IDs, implementing the approve/reject resume path with correct snapshot state transitions and event emission.

## Subtasks

- [ ] T014 In `provide_decision_answer`, detect when `decision_id.startswith("audit:")` and extract the `audit_step_id = decision_id[len("audit:"):]`
- [ ] T015 Validate that `answer` is exactly `"approve"` or `"reject"`; raise `MissionRuntimeError(f"Invalid audit answer '{answer}': must be 'approve' or 'reject'")` otherwise
- [ ] T016 On `"approve"`: remove `decision_id` from `pending_decisions`; add `audit_step_id` to `completed_steps` in snapshot; write updated snapshot
- [ ] T017 On `"reject"`: remove `decision_id` from `pending_decisions`; set `blocked_reason = f"Audit step '{audit_step_id}' rejected by {actor.actor_id}"` in snapshot; write updated snapshot
- [ ] T018 Emit `DECISION_INPUT_ANSWERED` event in both approve and reject paths (same as existing input-keyed behavior)
- [ ] T019 Write `tests/test_audit_engine.py` with full engine integration tests (no mocks — uses actual filesystem run dirs via `tmp_path`) covering AC-5 and AC-6

## Acceptance Criteria

### AC-5: Resume path — approve
- After `provide_decision_answer(decision_id="audit:audit-01", answer="approve", ...)`:
  - `"audit-01"` appears in `snapshot.completed_steps`
  - `"audit:audit-01"` is removed from `snapshot.pending_decisions`
  - Subsequent `next_step(...)` call returns the next eligible step (or `terminal` if no more steps)

### AC-6: Resume path — reject
- After `provide_decision_answer(decision_id="audit:audit-01", answer="reject", ...)`:
  - `snapshot.blocked_reason` is set and references `"audit-01"`
  - `"audit:audit-01"` is removed from `snapshot.pending_decisions`
  - Subsequent `next_step(...)` call returns `kind="blocked"` with matching `reason`

### Additional: Invalid answer
- `provide_decision_answer(decision_id="audit:audit-01", answer="maybe", ...)` raises `MissionRuntimeError`

### Additional: Event emission
- `DECISION_INPUT_ANSWERED` event is appended to `run.events.jsonl` for both approve and reject

## Test Cases Required

```python
# tests/test_audit_engine.py

class TestAuditApproveResumeePath:
    def test_approve_adds_to_completed_steps(self, tmp_path): ...
    def test_approve_removes_from_pending_decisions(self, tmp_path): ...
    def test_approve_next_step_continues(self, tmp_path): ...
    def test_approve_terminal_when_no_more_steps(self, tmp_path): ...

class TestAuditRejectBlocksRun:
    def test_reject_sets_blocked_reason(self, tmp_path): ...
    def test_reject_removes_from_pending_decisions(self, tmp_path): ...
    def test_reject_next_step_returns_blocked(self, tmp_path): ...
    def test_reject_blocked_reason_references_step_id(self, tmp_path): ...

class TestAuditInvalidAnswer:
    def test_invalid_answer_raises_runtime_error(self, tmp_path): ...

class TestAuditEventEmission:
    def test_approve_emits_decision_answered_event(self, tmp_path): ...
    def test_reject_emits_decision_answered_event(self, tmp_path): ...
```

## Test Setup Pattern

Tests should use the real engine functions (`start_mission_run`, `next_step`, `provide_decision_answer`) with `tmp_path` for the run store. A minimal blocking audit mission fixture is needed:

```python
# In conftest.py or inline in test
BLOCKING_AUDIT_MISSION = """
mission:
  key: test-blocking-audit
  name: Test Blocking Audit
  version: "1.0.0"
steps:
  - id: step-01
    title: First step
audit_steps:
  - id: audit-01
    title: Post-merge check
    depends_on: ["step-01"]
    audit:
      trigger_mode: manual
      enforcement: blocking
"""
```

Full flow to set up an audit checkpoint state:
1. `start_mission_run(...)` → `run_ref`
2. `next_step(run_ref, ...)` → returns `kind="step"` for step-01
3. `next_step(run_ref, ..., result="success")` → returns `kind="decision_required"` for audit-01
4. Now test `provide_decision_answer(run_ref, "audit:audit-01", "approve"/"reject", actor)`

## Implementation Notes

- The existing `provide_decision_answer` already handles `input:` prefix by writing to `snapshot.inputs`. The `audit:` prefix has different semantics and must be handled in a separate code path (no sharing).
- `rejected` audit answers set `blocked_reason` — this is **permanent** in a run. The run cannot be un-blocked by the engine (no recovery path within 2.x scope).
- The `actor.actor_id` used in the `blocked_reason` message comes from the caller-supplied `ActorIdentity` argument.
- Both the `approve` and `reject` paths must remove the decision_id from `pending_decisions` to prevent re-issuance of the same decision on subsequent `plan_next` calls.

## Files to Modify

- **Modify**: `src/spec_kitty_runtime/engine.py`
- **Create**: `tests/test_audit_engine.py`

## Completion Steps

1. Implement all subtasks
2. Run: `python -m pytest tests/test_audit_engine.py tests/test_audit_planner.py tests/test_audit_schema.py -v`
3. Run full suite: `python -m pytest tests/ -v`
4. Ensure all tests pass
5. Commit: `git add -A && git commit -m "feat(WP03): engine audit decision resume path"`
6. Mark subtasks done: `spec-kitty agent tasks mark-status T014 T015 T016 T017 T018 T019 --status done --feature 001-audit-primitive-decision-checkpoint`
7. Move to review: `spec-kitty agent tasks move-task WP03 --to for_review --feature 001-audit-primitive-decision-checkpoint --note "Engine audit resume path complete, all tests passing"`

## Activity Log

- 2026-02-26T14:39:28Z – claude-implementer – shell_pid=5370 – lane=doing – Assigned agent via workflow command
- 2026-02-26T14:43:59Z – claude-implementer – shell_pid=5370 – lane=for_review – Engine audit resume path complete. 20 integration tests covering AC-5 (approve: completed_steps updated, run continues/terminal), AC-6 (reject: blocked_reason set, run permanently blocked), invalid answer guard, and DECISION_INPUT_ANSWERED event emission. All 206 tests passing.

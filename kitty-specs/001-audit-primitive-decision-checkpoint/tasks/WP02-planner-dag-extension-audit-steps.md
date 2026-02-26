---
work_package_id: WP02
title: Planner DAG Extension for Audit Steps
lane: "doing"
dependencies: '[]'
base_branch: main
base_commit: 5df98f2229229aa9ef51b58860e8118cd6d92746
created_at: '2026-02-26T14:20:12.525363+00:00'
subtasks:
- T008
- T009
- T010
- T011
- T012
- T013
phase: Phase 2 - Planner Logic
assignee: ''
agent: "claude-reviewer"
shell_pid: "3626"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-02-26T00:00:00Z'
  lane: planned
  agent: system
  action: Prompt generated via /spec-kitty.specify
depends_on:
- WP01
feature: 001-audit-primitive-decision-checkpoint
---

# Work Package Prompt: WP02 – Planner DAG Extension for Audit Steps

## Context

This WP builds on WP01 (schema). The planner at `src/spec_kitty_runtime/planner.py` currently handles `PromptStep` objects only. It uses `_resolve_next_step` for DAG traversal and `plan_next` as the public entry point.

The planner is **stateless and deterministic**: given the same `MissionRunSnapshot` + `MissionTemplate` it always returns the same `NextDecision`. This invariant must be preserved.

**Prerequisite**: WP01 must be completed and merged (i.e., `AuditConfig`, `AuditStep`, and `MissionTemplate.audit_steps` must exist in `schema.py`).

## Objective

Extend the planner to handle `AuditStep` entries from `MissionTemplate.audit_steps` in the DAG traversal, and emit the correct `NextDecision` kind based on the audit step's `enforcement` value.

## Subtasks

- [ ] T008 Extend `_resolve_next_step` (or replace with a new `_resolve_next_unified_step`) to build a combined ordered sequence of `PromptStep | AuditStep` objects. The combined sequence must be deterministic: regular `steps` first (in template order), then `audit_steps` with `depends_on` dependency resolution
- [ ] T009 Apply the same `depends_on` DAG logic to `AuditStep` entries — an audit step is skipped until all its `depends_on` step IDs are in `snapshot.completed_steps`
- [ ] T010 When the next resolved step is an `AuditStep` with `enforcement="advisory"`, emit `NextDecision(kind="step", step_id=audit_step.id, step_title=audit_step.title, ...)`
- [ ] T011 When the next resolved step is an `AuditStep` with `enforcement="blocking"`, emit `NextDecision(kind="decision_required", decision_id=f"audit:{audit_step.id}", question=f"Audit checkpoint: {audit_step.title}. Approve to continue?", options=["approve", "reject"])` for all `trigger_mode` values
- [ ] T012 Ensure `input_key=None` for audit decision checkpoints (audit decisions are NOT input-keyed)
- [ ] T013 Write `tests/test_audit_planner.py` with deterministic tests covering AC-3, AC-4, AC-7, AC-9

## Acceptance Criteria

### AC-3: Planner — blocking enforcement
- For `enforcement=blocking`, `plan_next` returns `kind="decision_required"`
- `decision_id` is exactly `"audit:<step_id>"`
- `question` is non-empty and contains the audit step title
- `options` is exactly `["approve", "reject"]`
- This holds for all three `trigger_mode` values: `manual`, `post_merge`, `both`

### AC-4: Planner — advisory enforcement
- For `enforcement=advisory`, `plan_next` returns `kind="step"` for the audit step
- The step can then be completed normally (advisory steps don't gate the run)

### AC-7: DAG ordering
- An audit step with `depends_on: ["step-01"]` is NOT issued until `step-01` is in `completed_steps`
- An audit step with no `depends_on` appears AFTER all regular steps complete (appended at end)
- Two audit steps maintain relative template order when both become eligible simultaneously

### AC-9: Determinism
- Same `MissionRunSnapshot` + same `MissionTemplate` → identical `NextDecision` always
- `serialize_decision(plan_next(snapshot, template, policy))` is stable across calls

## Test Cases Required

```python
# tests/test_audit_planner.py

class TestPlannerBlockingAudit:
    def test_blocking_audit_emits_decision_required(self): ...
    def test_decision_id_format(self): ...  # "audit:audit-01"
    def test_question_contains_title(self): ...
    def test_options_are_approve_reject(self): ...
    def test_input_key_is_none(self): ...
    def test_blocking_applies_to_all_trigger_modes(self): ...  # parametrize

class TestPlannerAdvisoryAudit:
    def test_advisory_audit_emits_step(self): ...
    def test_advisory_step_id_correct(self): ...

class TestPlannerAuditDagOrdering:
    def test_audit_with_depends_on_waits_for_dependency(self): ...
    def test_audit_no_depends_on_after_all_steps(self): ...
    def test_regular_steps_before_audit_steps(self): ...

class TestPlannerDeterminism:
    def test_same_input_same_output(self): ...
    def test_serialize_decision_stable(self): ...
    def test_audit_only_mission(self): ...  # no regular steps
```

## Implementation Notes

- The combined sequence order must be deterministic: iterate `template.steps` first, then `template.audit_steps`. Within each list, template order is preserved.
- The `depends_on` check for audit steps uses the same `completed_steps` set as regular steps — audit step IDs can appear in `depends_on` of other steps too (cross-type dependencies)
- `AuditStep` does NOT have `requires_inputs`, so the missing-inputs check in `plan_next` only applies to `PromptStep` instances
- The `context: StepContextBundle` for advisory audit steps should be populated as for regular steps
- For decision_required audit steps, `context` can be `None` (consistent with existing decision_required behavior)

## Files to Modify

- **Modify**: `src/spec_kitty_runtime/planner.py`
- **Create**: `tests/test_audit_planner.py`

## Completion Steps

1. Implement all subtasks
2. Run: `python -m pytest tests/test_audit_planner.py tests/test_audit_schema.py -v`
3. Run full suite to check for regressions: `python -m pytest tests/ -v`
4. Ensure all tests pass
5. Commit: `git add -A && git commit -m "feat(WP02): planner DAG extension for audit steps"`
6. Mark subtasks done: `spec-kitty agent tasks mark-status T008 T009 T010 T011 T012 T013 --status done --feature 001-audit-primitive-decision-checkpoint`
7. Move to review: `spec-kitty agent tasks move-task WP02 --to for_review --feature 001-audit-primitive-decision-checkpoint --note "Planner audit step DAG complete, all tests passing"`

## Activity Log

- 2026-02-26T14:20:12Z – claude-implementer – shell_pid=94636 – lane=doing – Assigned agent via workflow command
- 2026-02-26T14:25:32Z – claude-implementer – shell_pid=94636 – lane=for_review – Planner audit step DAG complete. 30 new tests passing, 186 total (0 regressions). Blocking=decision_required, advisory=step, full DAG ordering and determinism verified.
- 2026-02-26T14:26:04Z – claude-reviewer – shell_pid=97759 – lane=doing – Started review via workflow command
- 2026-02-26T14:30:37Z – claude-reviewer – shell_pid=97759 – lane=in_progress – Changes requested
- 2026-02-26T14:31:28Z – claude-implementer – shell_pid=655 – lane=doing – Started implementation via workflow command
- 2026-02-26T14:35:30Z – claude-implementer – shell_pid=655 – lane=for_review – Ready for review: Fixed both P1 findings - (1) added pythonpath=['src'] to pyproject.toml pytest.ini_options for deterministic imports, (2) rewrote branch to single clean commit with only WP02 files (pyproject.toml, planner.py, test_audit_planner.py) - no kitty-specs in history. 186/186 tests passing.
- 2026-02-26T14:36:06Z – claude-reviewer – shell_pid=3626 – lane=doing – Started review via workflow command

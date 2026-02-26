---
feature: 001-audit-primitive-decision-checkpoint
total_wps: 4
---

# Tasks: Mission Audit Primitive + Decision Checkpoint Plumbing

## WP01 — AuditConfig + AuditStep Schema

**Depends on**: (none)
**Scope**: `src/spec_kitty_runtime/schema.py`, `tests/test_audit_schema.py`

### Subtasks

- [x] T001 Add `AuditConfig` Pydantic model with `trigger_mode` and `enforcement` literal fields (both required, no defaults)
- [x] T002 Add optional `label: str | None` and `metadata: dict[str, Any] | None` to `AuditConfig`
- [x] T003 Add `AuditStep` Pydantic model with `id`, `title`, `description`, `audit: AuditConfig`, `depends_on: list[str]`
- [x] T004 Extend `MissionTemplate` with `audit_steps: list[AuditStep]` field (default empty list)
- [x] T005 Extend `load_mission_template_file` to parse `audit_steps` from YAML
- [x] T006 Add validation in `load_mission_template_file`: raise `MissionRuntimeError` if neither `steps` nor `audit_steps` is non-empty
- [x] T007 Write `tests/test_audit_schema.py` covering AC-1 and AC-2 (schema validation + YAML loading)

### Acceptance Criteria

- AC-1: `AuditConfig` validates correctly; invalid `trigger_mode`/`enforcement` raises `ValidationError`
- AC-2: YAML loading handles `audit_steps`; missing both `steps` and `audit_steps` raises `MissionRuntimeError`

---

## WP02 — Planner DAG Extension for Audit Steps

**Depends on**: WP01
**Scope**: `src/spec_kitty_runtime/planner.py`, `tests/test_audit_planner.py`

### Subtasks

- [x] T008 Build combined ordered sequence of `PromptStep | AuditStep` in `_resolve_next_step`
- [x] T009 Apply same `depends_on` DAG logic to `AuditStep` entries
- [x] T010 Emit `kind="step"` for `enforcement=advisory` audit steps
- [x] T011 Emit `kind="decision_required"` for `enforcement=blocking` audit steps with `decision_id="audit:<step_id>"`, `question`, and `options=["approve","reject"]`
- [x] T012 Ensure `input_key=None` for audit decision checkpoints
- [x] T013 Write `tests/test_audit_planner.py` covering AC-3, AC-4, AC-7, AC-9 (blocking/advisory decisions, DAG ordering, determinism)

### Acceptance Criteria

- AC-3: Blocking enforcement → `decision_required` with correct `decision_id`, `question`, `options`
- AC-4: Advisory enforcement → `step` kind
- AC-7: `depends_on` respected for audit steps
- AC-9: Deterministic output — same input always yields same `NextDecision`

---

## WP03 — Engine Resume Path for Audit Decisions

**Depends on**: WP02
**Scope**: `src/spec_kitty_runtime/engine.py`, `tests/test_audit_engine.py`

### Subtasks

- [x] T014 Extend `provide_decision_answer` to detect `audit:` prefix in `decision_id`
- [x] T015 Validate that answer is `"approve"` or `"reject"`; raise `MissionRuntimeError` on invalid answer
- [x] T016 On `"approve"`: add audit step id to `completed_steps` in snapshot; remove from `pending_decisions`
- [x] T017 On `"reject"`: set `blocked_reason` referencing audit step id; remove from `pending_decisions`
- [x] T018 Emit `DECISION_INPUT_ANSWERED` event for both approve and reject paths
- [x] T019 Write `tests/test_audit_engine.py` covering AC-5 and AC-6 (approve → continue, reject → blocked)

### Acceptance Criteria

- AC-5: `approve` → audit step in `completed_steps`, next step proceeds
- AC-6: `reject` → `blocked_reason` set, next `plan_next` returns `kind="blocked"`

---

## WP04 — Compatibility Diagnostics API + Fixtures

**Depends on**: WP01
**Scope**: `src/spec_kitty_runtime/diagnostics.py` (new), `tests/test_compat_diagnostics.py`, `tests/fixtures/*.yaml`

### Subtasks

- [x] T020 Create `src/spec_kitty_runtime/diagnostics.py` with `CompatibilityIssue` and `CompatibilityReport` models
- [x] T021 Implement `validate_mission_template_compatibility(path)` with all 8 validation checks from spec §3.5
- [x] T022 Create `tests/fixtures/audit_valid_blocking.yaml` — valid blocking enforcement mission
- [x] T023 Create `tests/fixtures/audit_valid_advisory.yaml` — valid advisory enforcement mission
- [x] T024 Create `tests/fixtures/audit_mixed_steps.yaml` — combined `steps` + `audit_steps`
- [x] T025 Create `tests/fixtures/audit_only_steps.yaml` — `audit_steps` only (no regular steps)
- [x] T026 Create `tests/fixtures/audit_invalid_trigger.yaml` — bad `trigger_mode` → `UNKNOWN_TRIGGER_MODE`
- [x] T027 Create `tests/fixtures/audit_missing_config.yaml` — missing `audit` block → `MISSING_AUDIT_CONFIG`
- [x] T028 Create `tests/fixtures/audit_bad_dependency.yaml` — broken `depends_on` → `UNRESOLVED_DEPENDENCY`
- [x] T029 Write `tests/test_compat_diagnostics.py` covering AC-8 (all issue codes + valid fixture)

### Acceptance Criteria

- AC-8: `validate_mission_template_compatibility` returns correct `CompatibilityReport` for all fixture files

<!-- status-model:start -->
## Canonical Status (Generated)
- WP01: done
- WP02: done
- WP03: for_review
- WP04: done
<!-- status-model:end -->

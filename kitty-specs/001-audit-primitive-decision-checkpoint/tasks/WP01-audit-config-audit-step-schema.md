---
work_package_id: "WP01"
title: "AuditConfig + AuditStep Schema"
lane: "planned"
feature: "001-audit-primitive-decision-checkpoint"
subtasks:
  - "T001"
  - "T002"
  - "T003"
  - "T004"
  - "T005"
  - "T006"
  - "T007"
depends_on: []
phase: "Phase 1 - Schema Foundation"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
dependencies: "[]"
history:
  - timestamp: "2026-02-26T00:00:00Z"
    lane: "planned"
    agent: "system"
    action: "Prompt generated via /spec-kitty.specify"
---

# Work Package Prompt: WP01 – AuditConfig + AuditStep Schema

## Context

This is the foundation WP for feature `001-audit-primitive-decision-checkpoint` in the `spec-kitty-runtime` Python library.

The codebase is at `src/spec_kitty_runtime/`. The main schema file is `src/spec_kitty_runtime/schema.py` which contains all Pydantic models including `MissionTemplate`, `PromptStep`, `MissionPolicySnapshot`, etc. Tests live under `tests/`.

All models use `pydantic>=2.0` with `ConfigDict(frozen=True)`. The project uses `pytest>=8.0`.

**Key constraint**: 2.x only. No 1.x compat. No fallback mechanisms. Code must fail explicitly on invalid config.

## Objective

Add `AuditConfig` and `AuditStep` Pydantic models to `schema.py`, extend `MissionTemplate` to include `audit_steps`, and extend `load_mission_template_file` to parse and validate the new schema.

## Subtasks

- [ ] T001 Add `AuditConfig` Pydantic model with required `trigger_mode: Literal["manual", "post_merge", "both"]` and required `enforcement: Literal["advisory", "blocking"]` — both fields have NO defaults (explicit declaration enforced)
- [ ] T002 Add optional `label: str | None = None` and `metadata: dict[str, Any] | None = None` to `AuditConfig`
- [ ] T003 Add `AuditStep` Pydantic model with `id: str`, `title: str`, `description: str = ""`, `audit: AuditConfig`, `depends_on: list[str] = []` — NO `prompt`, `prompt_template`, or `requires_inputs` fields
- [ ] T004 Extend `MissionTemplate` with `audit_steps: list[AuditStep] = Field(default_factory=list)`
- [ ] T005 Extend `load_mission_template_file` to parse `audit_steps` key from YAML (alongside existing `steps` parsing)
- [ ] T006 Add validation in `load_mission_template_file`: raise `MissionRuntimeError` if both `steps` and `audit_steps` are empty after loading
- [ ] T007 Write `tests/test_audit_schema.py` with deterministic tests (no mocks, no network) covering all acceptance criteria below

## Acceptance Criteria

### AC-1: Schema validation
- `AuditConfig(trigger_mode="manual", enforcement="blocking")` parses without error
- `AuditConfig(trigger_mode="invalid", enforcement="blocking")` raises `pydantic.ValidationError`
- `AuditConfig(trigger_mode="manual", enforcement="invalid")` raises `pydantic.ValidationError`
- `AuditStep` without `audit` field raises `pydantic.ValidationError`
- `AuditConfig` without `trigger_mode` raises `pydantic.ValidationError` (no default)
- `AuditConfig` without `enforcement` raises `pydantic.ValidationError` (no default)

### AC-2: YAML loading
- Mission YAML with `audit_steps` list loads successfully via `load_mission_template_file`
- Mission YAML with only `audit_steps` (no `steps` key) loads successfully
- Mission YAML with neither `steps` nor `audit_steps` (or both empty) raises `MissionRuntimeError`
- Mission YAML with unknown field in `audit:` block must fail validation (Pydantic strict mode or `model_config = ConfigDict(extra="forbid")` on `AuditConfig`)

## Example YAML that must load successfully

```yaml
mission:
  key: test-audit-mission
  name: Test Audit Mission
  version: "1.0.0"
steps:
  - id: step-01
    title: Initial step
audit_steps:
  - id: audit-01
    title: Post-merge policy check
    audit:
      trigger_mode: post_merge
      enforcement: blocking
```

## Implementation Notes

- Use `model_config = ConfigDict(frozen=True, extra="forbid")` on `AuditConfig` to enforce unknown-field rejection
- The `depends_on` field in `AuditStep` follows the same semantics as `PromptStep.depends_on` (list of step IDs that must complete first)
- `AuditStep` is intentionally NOT a subclass of `PromptStep` — it is a distinct schema type
- `MissionTemplate.audit_steps` should default to empty list (compatible with existing missions that have no audit steps)

## Files to Create/Modify

- **Modify**: `src/spec_kitty_runtime/schema.py`
- **Create**: `tests/test_audit_schema.py`

## Test Structure

```python
# tests/test_audit_schema.py
import pytest
from pydantic import ValidationError
from spec_kitty_runtime.schema import AuditConfig, AuditStep, MissionTemplate, MissionRuntimeError, load_mission_template_file

class TestAuditConfig:
    def test_valid_manual_blocking(self): ...
    def test_valid_post_merge_advisory(self): ...
    def test_invalid_trigger_mode(self): ...
    def test_invalid_enforcement(self): ...
    def test_trigger_mode_required(self): ...
    def test_enforcement_required(self): ...
    def test_extra_fields_forbidden(self): ...
    def test_optional_label(self): ...
    def test_optional_metadata(self): ...

class TestAuditStep:
    def test_valid_audit_step(self): ...
    def test_missing_audit_field_raises(self): ...
    def test_no_prompt_field(self): ...
    def test_depends_on_default_empty(self): ...

class TestMissionTemplateWithAuditSteps:
    def test_load_with_audit_steps(self, tmp_path): ...
    def test_load_audit_steps_only(self, tmp_path): ...
    def test_load_neither_raises(self, tmp_path): ...
    def test_load_both_empty_raises(self, tmp_path): ...
```

## Completion Steps

1. Implement all subtasks
2. Run: `python -m pytest tests/test_audit_schema.py -v`
3. Ensure all tests pass
4. Commit: `git add -A && git commit -m "feat(WP01): AuditConfig + AuditStep schema"`
5. Mark subtasks done: `spec-kitty agent tasks mark-status T001 T002 T003 T004 T005 T006 T007 --status done --feature 001-audit-primitive-decision-checkpoint`
6. Move to review: `spec-kitty agent tasks move-task WP01 --to for_review --feature 001-audit-primitive-decision-checkpoint --note "Schema implementation complete, all tests passing"`

---
work_package_id: WP04
title: Compatibility Diagnostics API + Fixtures
lane: "done"
dependencies: '[]'
base_branch: main
base_commit: 85f890303f434bb2fd345df7e5863692d1d200b4
created_at: '2026-02-26T14:20:08.621531+00:00'
subtasks:
- T020
- T021
- T022
- T023
- T024
- T025
- T026
- T027
- T028
- T029
phase: Phase 2 - Diagnostics
assignee: ''
agent: claude-reviewer
shell_pid: '97688'
review_status: "approved"
reviewed_by: "Robert Douglass"
history:
- timestamp: '2026-02-26T00:00:00Z'
  lane: planned
  agent: system
  action: Prompt generated via /spec-kitty.specify
depends_on:
- WP01
feature: 001-audit-primitive-decision-checkpoint
---

# Work Package Prompt: WP04 – Compatibility Diagnostics API + Fixtures

## Context

This WP builds on WP01 (schema only). It is independent of WP02 and WP03 and can be worked in parallel after WP01 completes.

The diagnostics API is a host-repo–facing validation tool. Host repos import `validate_mission_template_compatibility` to check their mission YAML files against the 2.x schema without starting a mission run. The function must never raise — it always returns a `CompatibilityReport`.

## Objective

Create `src/spec_kitty_runtime/diagnostics.py` with `CompatibilityReport`, `CompatibilityIssue`, and `validate_mission_template_compatibility`. Create 7 fixture YAML files. Write `tests/test_compat_diagnostics.py` covering all AC-8 cases.

## Subtasks

- [ ] T020 Create `src/spec_kitty_runtime/diagnostics.py` with:
  - `CompatibilityIssue(BaseModel)` — frozen, fields: `code: str`, `field: str`, `message: str`, `severity: Literal["error", "warning"]`
  - `CompatibilityReport(BaseModel)` — frozen, fields: `path: str`, `is_compatible: bool`, `schema_valid: bool`, `audit_steps_valid: bool`, `issues: list[CompatibilityIssue]`, `warnings: list[str]`

- [ ] T021 Implement `validate_mission_template_compatibility(path: Path | str) -> CompatibilityReport` with these 8 checks (in order):
  1. YAML parses without error (if fails: `schema_valid=False`, issue `YAML_PARSE_ERROR`)
  2. `mission` block has required `key`, `name`, `version` (if fails: `schema_valid=False`, issue `MISSING_MISSION_META`)
  3. At least one of `steps` or `audit_steps` is non-empty (if fails: `audit_steps_valid=False`, issue `NO_STEPS_DEFINED`)
  4. Each `audit_steps` entry has `id` and `title` (if fails: issue `MISSING_STEP_FIELDS`)
  5. Each `audit_steps` entry has an `audit` block (if fails: issue `MISSING_AUDIT_CONFIG`)
  6. `audit.trigger_mode` is one of `manual | post_merge | both` (if fails: issue `UNKNOWN_TRIGGER_MODE`)
  7. `audit.enforcement` is one of `advisory | blocking` (if fails: issue `UNKNOWN_ENFORCEMENT`)
  8. `depends_on` references in `audit_steps` resolve to known `step` or `audit_step` IDs (if fails: issue `UNRESOLVED_DEPENDENCY`)
  9. No duplicate step IDs across `steps` and `audit_steps` (if fails: issue `DUPLICATE_STEP_ID`)

  Function never raises — all exceptions are caught and converted to issues.

- [ ] T022 Create `tests/fixtures/audit_valid_blocking.yaml`:
```yaml
mission:
  key: valid-blocking
  name: Valid Blocking Mission
  version: "1.0.0"
steps:
  - id: step-01
    title: Initial step
audit_steps:
  - id: audit-01
    title: Post-merge policy check
    depends_on: ["step-01"]
    audit:
      trigger_mode: post_merge
      enforcement: blocking
```

- [ ] T023 Create `tests/fixtures/audit_valid_advisory.yaml`:
```yaml
mission:
  key: valid-advisory
  name: Valid Advisory Mission
  version: "1.0.0"
steps:
  - id: step-01
    title: Initial step
audit_steps:
  - id: audit-01
    title: Advisory compliance check
    audit:
      trigger_mode: manual
      enforcement: advisory
```

- [ ] T024 Create `tests/fixtures/audit_mixed_steps.yaml`:
```yaml
mission:
  key: mixed-steps
  name: Mixed Steps Mission
  version: "1.0.0"
steps:
  - id: step-01
    title: First regular step
  - id: step-02
    title: Second regular step
    depends_on: ["step-01"]
audit_steps:
  - id: audit-01
    title: Mid-flight check
    depends_on: ["step-01"]
    audit:
      trigger_mode: both
      enforcement: blocking
  - id: audit-02
    title: Final check
    depends_on: ["step-02", "audit-01"]
    audit:
      trigger_mode: manual
      enforcement: advisory
```

- [ ] T025 Create `tests/fixtures/audit_only_steps.yaml`:
```yaml
mission:
  key: audit-only
  name: Audit Only Mission
  version: "1.0.0"
audit_steps:
  - id: audit-01
    title: Standalone audit check
    audit:
      trigger_mode: manual
      enforcement: blocking
```

- [ ] T026 Create `tests/fixtures/audit_invalid_trigger.yaml`:
```yaml
mission:
  key: invalid-trigger
  name: Invalid Trigger Mission
  version: "1.0.0"
steps:
  - id: step-01
    title: Regular step
audit_steps:
  - id: audit-01
    title: Broken audit
    audit:
      trigger_mode: on_deploy
      enforcement: blocking
```

- [ ] T027 Create `tests/fixtures/audit_missing_config.yaml`:
```yaml
mission:
  key: missing-config
  name: Missing Config Mission
  version: "1.0.0"
steps:
  - id: step-01
    title: Regular step
audit_steps:
  - id: audit-01
    title: Audit without config block
```

- [ ] T028 Create `tests/fixtures/audit_bad_dependency.yaml`:
```yaml
mission:
  key: bad-dependency
  name: Bad Dependency Mission
  version: "1.0.0"
steps:
  - id: step-01
    title: Regular step
audit_steps:
  - id: audit-01
    title: Audit with broken dep
    depends_on: ["step-99"]
    audit:
      trigger_mode: manual
      enforcement: blocking
```

- [ ] T029 Write `tests/test_compat_diagnostics.py` with tests for all issue codes and valid fixtures

## Acceptance Criteria

### AC-8: Compatibility diagnostics

| Fixture | Expected `is_compatible` | Expected issue code |
|---------|--------------------------|---------------------|
| `audit_valid_blocking.yaml` | `True` | (none) |
| `audit_valid_advisory.yaml` | `True` | (none) |
| `audit_mixed_steps.yaml` | `True` | (none) |
| `audit_only_steps.yaml` | `True` | (none) |
| `audit_invalid_trigger.yaml` | `False` | `UNKNOWN_TRIGGER_MODE` |
| `audit_missing_config.yaml` | `False` | `MISSING_AUDIT_CONFIG` |
| `audit_bad_dependency.yaml` | `False` | `UNRESOLVED_DEPENDENCY` |

### Additional
- `validate_mission_template_compatibility` never raises; always returns `CompatibilityReport`
- Valid fixtures → `issues=[]`, `is_compatible=True`, `schema_valid=True`, `audit_steps_valid=True`
- `field` in `CompatibilityIssue` uses dot notation, e.g. `"audit_steps[0].audit.trigger_mode"`

## Test Structure

```python
# tests/test_compat_diagnostics.py
import pytest
from pathlib import Path
from spec_kitty_runtime.diagnostics import validate_mission_template_compatibility, CompatibilityReport

FIXTURES = Path(__file__).parent / "fixtures"

class TestValidFixtures:
    def test_valid_blocking_is_compatible(self): ...
    def test_valid_advisory_is_compatible(self): ...
    def test_mixed_steps_is_compatible(self): ...
    def test_audit_only_is_compatible(self): ...

class TestInvalidFixtures:
    def test_invalid_trigger_mode(self): ...  # UNKNOWN_TRIGGER_MODE
    def test_missing_audit_config(self): ...  # MISSING_AUDIT_CONFIG
    def test_bad_dependency(self): ...        # UNRESOLVED_DEPENDENCY

class TestReportStructure:
    def test_returns_compatibility_report_type(self): ...
    def test_never_raises_on_nonexistent_file(self): ...  # path doesn't exist
    def test_never_raises_on_invalid_yaml(self): ...
    def test_issue_field_uses_dot_notation(self): ...
    def test_path_field_in_report(self): ...
```

## Implementation Notes

- `validate_mission_template_compatibility` is a pure validation function — it does NOT start a mission run
- All YAML parsing done with `yaml.safe_load` (same as existing code)
- The function accepts either `Path` or `str` for the path argument
- Issue `severity` is always `"error"` for compatibility failures; `"warning"` can be used for deprecation notices in future
- The function should catch all exceptions from YAML parsing and schema validation and convert them to `CompatibilityIssue` objects — never let exceptions propagate out
- `CompatibilityReport.is_compatible` is `True` only when `len(issues) == 0` (no errors), regardless of warnings

## Files to Create

- **Create**: `src/spec_kitty_runtime/diagnostics.py`
- **Create**: `tests/fixtures/audit_valid_blocking.yaml`
- **Create**: `tests/fixtures/audit_valid_advisory.yaml`
- **Create**: `tests/fixtures/audit_mixed_steps.yaml`
- **Create**: `tests/fixtures/audit_only_steps.yaml`
- **Create**: `tests/fixtures/audit_invalid_trigger.yaml`
- **Create**: `tests/fixtures/audit_missing_config.yaml`
- **Create**: `tests/fixtures/audit_bad_dependency.yaml`
- **Create**: `tests/test_compat_diagnostics.py`

## Completion Steps

1. Implement all subtasks
2. Run: `python -m pytest tests/test_compat_diagnostics.py -v`
3. Run full suite: `python -m pytest tests/ -v`
4. Ensure all tests pass
5. Commit: `git add -A && git commit -m "feat(WP04): compatibility diagnostics API + fixtures"`
6. Mark subtasks done: `spec-kitty agent tasks mark-status T020 T021 T022 T023 T024 T025 T026 T027 T028 T029 --status done --feature 001-audit-primitive-decision-checkpoint`
7. Move to review: `spec-kitty agent tasks move-task WP04 --to for_review --feature 001-audit-primitive-decision-checkpoint --note "Diagnostics API + 7 fixtures complete, all tests passing"`

## Activity Log

- 2026-02-26T14:20:08Z – claude-implementer – shell_pid=94422 – lane=doing – Assigned agent via workflow command
- 2026-02-26T14:23:44Z – claude-implementer – shell_pid=94422 – lane=for_review – Diagnostics API + 7 fixtures complete, 23/23 new tests passing, 153/153 total tests passing
- 2026-02-26T14:26:03Z – claude-reviewer – shell_pid=97688 – lane=doing – Started review via workflow command
- 2026-02-26T14:27:29Z – claude-reviewer – shell_pid=97688 – lane=done – Review passed: All 23 WP04 tests pass (179 total suite). CompatibilityReport + CompatibilityIssue models correctly frozen. validate_mission_template_compatibility implements all 9 checks, never raises, handles YAML errors, missing files, and all 7 fixture cases per AC-8. Dot-notation field paths verified. WP01 schema dependency confirmed merged to main.

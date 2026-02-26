# Spec: Mission Audit Primitive + Decision Checkpoint Plumbing

## Feature ID
`001-audit-primitive-decision-checkpoint`

## Version
2.x (no 1.x compat)

## Status
specified

---

## 1. Objective

Add a mission-declarable **audit primitive** with configurable `trigger_mode` and `enforcement` settings, plus **decision checkpoint** plumbing that enables a `decision_required` pause/resume path tied to audit outcomes.

The mission YAML is the single control entity. Audit is a **first-class mission primitive**, not a side-effect or host-layer concern.

---

## 2. Scope

### In scope
- `AuditConfig` schema: `trigger_mode` (`manual | post_merge | both`), `enforcement` (`advisory | blocking`)
- `AuditStep` schema: extends `PromptStep` with `audit` field (`AuditConfig`)
- `MissionTemplate` schema: accept `audit_steps` list alongside existing `steps`
- Schema/policy parsing: load and validate `audit_steps` from mission YAML
- Engine/planner primitive contract:
  - Planner recognises `audit` steps in DAG traversal
  - When an audit step is reached and `enforcement=blocking`, planner emits `decision_required` instead of `step`
  - Resume path: `provide_decision_answer` unblocks audit decision checkpoints
- Deterministic test suite (no mocks, no fallbacks)
- Built-in mission-template compatibility diagnostics API:
  - `validate_mission_template_compatibility(path)` → `CompatibilityReport`
  - Fixture YAML files for host-repo validation harness

### Out of scope
- CLI naming migration
- SaaS UI / projection work
- 1.x compatibility shims
- Remote/network audit backends
- Audit result storage/archival

---

## 3. Requirements

### 3.1 Schema

#### `AuditConfig`
```yaml
trigger_mode: manual | post_merge | both   # required
enforcement:  advisory | blocking           # required
label:        <string>                      # optional, human label
metadata:     <dict>                        # optional, passthrough
```

**Validation rules:**
- `trigger_mode` must be one of `manual`, `post_merge`, `both`
- `enforcement` must be one of `advisory`, `blocking`
- Both fields are required; no defaults (explicit declaration enforced)

#### `AuditStep`
```yaml
id:          <string>            # required
title:       <string>            # required
description: <string>            # optional
audit:       <AuditConfig>       # required (makes this an audit step)
depends_on:  [<step_id>, ...]    # optional
```

`AuditStep` inherits the DAG `depends_on` mechanism from `PromptStep`. It does **not** have `prompt`, `prompt_template`, or `requires_inputs` — audit steps are checkpoint primitives, not prompt-execution steps.

#### `MissionTemplate` extension
```yaml
mission:
  key: ...
  ...
steps:
  - id: ...           # existing PromptStep list
audit_steps:
  - id: audit-01
    title: Post-merge policy check
    audit:
      trigger_mode: post_merge
      enforcement: blocking
```

Both `steps` and `audit_steps` are optional lists; a mission may have either or both. At least one of `steps` or `audit_steps` must be non-empty.

### 3.2 Policy Parsing

- `load_mission_template_file` must parse `audit_steps` from YAML
- `AuditStep.audit` must be validated against `AuditConfig` field constraints
- Unknown keys in `audit:` block must raise `MissionRuntimeError` (strict, no passthrough of unknown)
- A mission YAML with `audit_steps` but no `steps` is valid
- A mission YAML with neither `steps` nor `audit_steps` must raise `MissionRuntimeError`

### 3.3 Planner / Engine Contract

#### DAG traversal with audit steps

The planner's `_resolve_next_step` must be extended to a unified resolver that handles both `PromptStep` and `AuditStep` entries in a combined ordered sequence.

Combined step sequence (for DAG traversal):
- `steps` entries are `PromptStep` objects
- `audit_steps` entries are `AuditStep` objects
- Ordering for interleaving: audit steps appear **after** all steps listed in their `depends_on`; if no `depends_on`, they are appended after all regular `steps` by default
- The combined order is deterministic (defined by position in their respective lists and dependency resolution)

#### Planner decision for audit steps

When the planner reaches an `AuditStep`:

| `enforcement`  | `trigger_mode`        | Planner decision kind   |
|----------------|-----------------------|-------------------------|
| `advisory`     | any                   | `step` (non-blocking)   |
| `blocking`     | `manual`              | `decision_required`     |
| `blocking`     | `post_merge`          | `decision_required`     |
| `blocking`     | `both`                | `decision_required`     |

For `decision_required` audit checkpoints:
- `decision_id` = `audit:<step_id>`
- `question` = derived from step title (e.g., `"Audit checkpoint: <title>. Approve to continue?"`)
- `options` = `["approve", "reject"]`
- `input_key` = `None` (audit decisions are not input-keyed)

For `advisory` audit steps:
- Emitted as `kind="step"` with `step_id` = audit step id
- The agent executes it like a normal step (informational)

#### Resume path

`provide_decision_answer`:
- Accepts `decision_id` starting with `audit:` prefix
- Valid answers: `"approve"` or `"reject"`
- On `"approve"`: moves audit step to completed, next `plan_next` continues DAG
- On `"reject"`: sets `blocked_reason` on snapshot, next `plan_next` returns `kind="blocked"`
- `"reject"` answer is **final** — the run is blocked, no automatic recovery

### 3.4 Events

Audit decision checkpoints must use the existing event infrastructure:
- `DECISION_INPUT_REQUESTED` emitted when audit `decision_required` is returned
- `DECISION_INPUT_ANSWERED` emitted when `provide_decision_answer` is called
- No new event types required in this feature

### 3.5 Compatibility Diagnostics API

New public function in `spec_kitty_runtime.discovery` (or a new `diagnostics` module):

```python
def validate_mission_template_compatibility(
    path: Path | str,
) -> CompatibilityReport:
    ...
```

#### `CompatibilityReport`

```python
class CompatibilityReport(BaseModel):
    path: str
    is_compatible: bool
    schema_valid: bool
    audit_steps_valid: bool
    issues: list[CompatibilityIssue]
    warnings: list[str]
```

#### `CompatibilityIssue`

```python
class CompatibilityIssue(BaseModel):
    code: str         # e.g. "MISSING_AUDIT_CONFIG", "UNKNOWN_TRIGGER_MODE"
    field: str        # e.g. "audit_steps[0].audit.trigger_mode"
    message: str
    severity: Literal["error", "warning"]
```

#### Validation checks performed

1. YAML parses without error
2. `mission` block is present and has required `key`, `name`, `version`
3. At least one of `steps` or `audit_steps` is non-empty
4. Each `audit_steps` entry has `id`, `title`, and `audit` block
5. `audit.trigger_mode` is one of `manual | post_merge | both`
6. `audit.enforcement` is one of `advisory | blocking`
7. `depends_on` references in `audit_steps` resolve to known `step` or `audit_step` IDs
8. No duplicate step IDs across `steps` and `audit_steps`

---

## 4. Acceptance Criteria

### AC-1: Schema validation
- `AuditConfig` with valid `trigger_mode` and `enforcement` parses without error
- `AuditConfig` with invalid `trigger_mode` raises `ValidationError`
- `AuditConfig` with invalid `enforcement` raises `ValidationError`
- `AuditStep` without `audit` field raises `ValidationError`

### AC-2: YAML loading
- Mission YAML with `audit_steps` loads via `load_mission_template_file`
- Mission YAML with only `audit_steps` (no `steps`) loads successfully
- Mission YAML with neither `steps` nor `audit_steps` raises `MissionRuntimeError`
- Mission YAML with unknown field in `audit:` block raises `MissionRuntimeError`

### AC-3: Planner — blocking enforcement
- For `enforcement=blocking`, planner returns `kind="decision_required"` with `decision_id="audit:<step_id>"`
- `question` field is non-empty and references the audit step title
- `options` contains exactly `["approve", "reject"]`

### AC-4: Planner — advisory enforcement
- For `enforcement=advisory`, planner returns `kind="step"` for audit step

### AC-5: Resume path — approve
- After `provide_decision_answer(decision_id="audit:X", answer="approve")`, next `plan_next` returns next eligible step (or `terminal` if done)
- Audit step appears in `completed_steps` after approval

### AC-6: Resume path — reject
- After `provide_decision_answer(decision_id="audit:X", answer="reject")`, next `plan_next` returns `kind="blocked"`
- `blocked_reason` is set and references the audit step

### AC-7: DAG ordering
- Audit step with `depends_on` is not issued until all dependencies complete
- Audit step with no `depends_on` appears after all regular steps are complete (default ordering)

### AC-8: Compatibility diagnostics
- `validate_mission_template_compatibility(path)` returns `CompatibilityReport`
- Valid mission YAML → `is_compatible=True`, `issues=[]`
- Mission with invalid `trigger_mode` → `is_compatible=False`, issue code `UNKNOWN_TRIGGER_MODE`
- Mission with missing `audit` block in audit step → `is_compatible=False`, issue code `MISSING_AUDIT_CONFIG`
- Mission with broken `depends_on` reference → `is_compatible=False`, issue code `UNRESOLVED_DEPENDENCY`

### AC-9: Determinism
- Same mission YAML + same run state → identical `NextDecision` output (verified via `serialize_decision`)
- No randomness, no time-dependent branching in planner output

### AC-10: No 1.x compat
- No fallback shims, no legacy field aliases, no optional-field bridges to 1.x schema

---

## 5. Architecture Notes

### Where code lives

| Module | Change |
|--------|--------|
| `schema.py` | Add `AuditConfig`, `AuditStep`; extend `MissionTemplate` |
| `planner.py` | Extend `_resolve_next_step` to handle `AuditStep`; add audit decision logic |
| `engine.py` | Extend `provide_decision_answer` for `audit:` prefixed decision IDs |
| `discovery.py` or new `diagnostics.py` | Add `validate_mission_template_compatibility` |
| `tests/` | New test files: `test_audit_schema.py`, `test_audit_planner.py`, `test_audit_engine.py`, `test_compat_diagnostics.py` |
| `tests/fixtures/` | New fixture YAML files for compatibility validation harness |

### Design invariants (must not be violated)

1. `MissionTemplate` is the central control entity — audit is declared in the mission, not injected externally
2. Planner is stateless and deterministic — given snapshot + template → same output always
3. No network calls in any code path touched by this feature
4. No fallback mechanisms — code must fail explicitly on invalid configuration

---

## 6. Non-Goals (Explicitly Excluded)

- CLI naming migration
- SaaS UI or projection work
- Audit result storage, archival, or querying
- Remote audit backends
- 1.x compatibility shims or aliases
- Gradual migration / optional adoption flags for audit config

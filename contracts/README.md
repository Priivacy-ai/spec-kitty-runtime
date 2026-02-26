# Runtime Audit Primitive Contracts

This directory documents the serialized payload shapes for the `spec-kitty-runtime` audit
primitive contracts. These contracts are frozen as of v0.4.0 and must not be changed without
a corresponding version bump and migration guide.

---

## Table of Contents

1. [AuditConfig Schema](#auditconfig-schema)
2. [AuditStep Schema](#auditstep-schema)
3. [Planner Decision Contract (NextDecision)](#planner-decision-contract-nextdecision)
4. [Engine Decision-Answer Semantics (DecisionAnswer)](#engine-decision-answer-semantics-decisionanswer)
5. [Compatibility Diagnostics Report Model](#compatibility-diagnostics-report-model)
   - [CompatibilityReport](#compatibilityreport)
   - [CompatibilityIssue](#compatibilityissue)
   - [Issue Codes](#issue-codes)

---

## AuditConfig Schema

`AuditConfig` is the policy block embedded inside every `AuditStep`. It declares when an audit
step fires and whether it gates mission progress.

```python
class AuditConfig(BaseModel):
    trigger_mode: Literal["manual", "post_merge", "both"]
    enforcement: Literal["advisory", "blocking"]
    label: str | None = None
    metadata: dict[str, Any] | None = None
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `trigger_mode` | `"manual" \| "post_merge" \| "both"` | Yes | When the audit step fires. `manual` = explicit invocation only; `post_merge` = triggered automatically after a merge event; `both` = both paths. |
| `enforcement` | `"advisory" \| "blocking"` | Yes | Whether a failing audit blocks mission progress. `advisory` = non-blocking warning; `blocking` = halts the run until resolved. |
| `label` | `str \| None` | No | Human-readable label for display. |
| `metadata` | `dict \| None` | No | Arbitrary metadata for tooling extensions. |

**Serialized example:**

```json
{
  "trigger_mode": "post_merge",
  "enforcement": "blocking",
  "label": null,
  "metadata": null
}
```

---

## AuditStep Schema

`AuditStep` extends the regular `PromptStep` with an embedded `AuditConfig`. Audit steps
appear in the `audit_steps` list of a `MissionTemplate`.

```python
class AuditStep(BaseModel):
    id: str
    title: str
    description: str = ""
    audit: AuditConfig
    depends_on: list[str] = []
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | `str` | Yes | Unique step identifier (must be unique across `steps` and `audit_steps`). |
| `title` | `str` | Yes | Human-readable step title. |
| `description` | `str` | No | Extended description. Defaults to `""`. |
| `audit` | `AuditConfig` | Yes | Audit policy configuration block. |
| `depends_on` | `list[str]` | No | List of step IDs from `steps` or `audit_steps` that must complete before this step runs. |

**Serialized example:**

```json
{
  "id": "audit-01",
  "title": "Post-merge policy check",
  "description": "",
  "audit": {
    "trigger_mode": "post_merge",
    "enforcement": "blocking",
    "label": null,
    "metadata": null
  },
  "depends_on": ["step-01"]
}
```

---

## Planner Decision Contract (NextDecision)

`NextDecision` is the output contract of `plan_next()`. It is a frozen, deterministic payload
describing what the runtime engine should do next.

```python
class NextDecision(BaseModel):
    kind: Literal["step", "decision_required", "blocked", "terminal"]
    run_id: str
    mission_key: str
    step_id: str | None = None
    step_title: str | None = None
    prompt: str | None = None
    context: StepContextBundle | None = None
    decision_id: str | None = None
    input_key: str | None = None
    question: str | None = None
    options: list[str] | None = None
    reason: str | None = None
```

### Decision Kinds

| `kind` | Meaning | Required fields |
|--------|---------|-----------------|
| `"step"` | A step prompt is ready to execute | `step_id`, `step_title`, `prompt`, `context` |
| `"decision_required"` | A required input or decision blocks progression | `step_id`, `decision_id`, `question` |
| `"blocked"` | Mission is halted (template drift, unmet deps, or explicit block) | `reason` |
| `"terminal"` | All steps completed; mission is done | `reason` |

### Serialization

Use `serialize_decision()` for canonical deterministic serialization:

```python
from spec_kitty_runtime.planner import serialize_decision
json_str = serialize_decision(decision)  # sort_keys=True, compact separators
```

**Serialized example (kind=step):**

```json
{
  "context": null,
  "decision_id": null,
  "input_key": null,
  "kind": "step",
  "mission_key": "my-mission",
  "options": null,
  "prompt": "Execute step 'step-01': Initial step",
  "reason": null,
  "run_id": "run-abc123",
  "step_id": "step-01",
  "step_title": "Initial step",
  "question": null
}
```

**Serialized example (kind=decision_required):**

```json
{
  "decision_id": "input:target_branch",
  "input_key": "target_branch",
  "kind": "decision_required",
  "mission_key": "my-mission",
  "options": null,
  "prompt": null,
  "question": "Input required before step 'step-01': provide value for 'target_branch'.",
  "reason": "missing_required_input",
  "run_id": "run-abc123",
  "step_id": "step-01",
  "step_title": null,
  "context": null
}
```

---

## Engine Decision-Answer Semantics (DecisionAnswer)

`DecisionAnswer` is the contract for resolving a pending `DecisionRequest`. The engine stores
answers in `MissionRunSnapshot.decisions` keyed by `decision_id`.

```python
class DecisionAnswer(BaseModel):
    decision_id: str
    answer: str
    answered_by: ActorIdentity
    answered_at: datetime
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `decision_id` | `str` | Yes | Must match the `decision_id` from the corresponding `DecisionRequest`. |
| `answer` | `str` | Yes | The answer value (always a string; callers coerce types). |
| `answered_by` | `ActorIdentity` | Yes | Identity of the actor providing the answer. |
| `answered_at` | `datetime` | Yes | ISO-8601 timestamp of when the answer was recorded. |

### Answer Semantics

- `decision_id` starting with `"input:"` maps to a `requires_inputs` field on the step.
  The `input_key` is the suffix after `"input:"`.
- Answers are stored in `snapshot.decisions[decision_id]` as serialized model data.
- Once a `decision_id` answer is present, `plan_next()` no longer emits
  `kind="decision_required"` for that decision.
- `DecisionAnswer` is frozen; callers must create a new snapshot with the answer applied.

**Serialized example:**

```json
{
  "decision_id": "input:target_branch",
  "answer": "main",
  "answered_by": {
    "actor_type": "human",
    "actor_id": "user-001"
  },
  "answered_at": "2026-02-26T14:00:00Z"
}
```

---

## Compatibility Diagnostics Report Model

The diagnostics API (`spec_kitty_runtime.diagnostics`) provides host-repo–facing validation
without starting a mission run. All functions return frozen models and never raise.

### CompatibilityReport

```python
class CompatibilityReport(BaseModel):
    path: str
    is_compatible: bool
    schema_valid: bool
    audit_steps_valid: bool
    issues: list[CompatibilityIssue]
    warnings: list[str]
```

| Field | Type | Description |
|-------|------|-------------|
| `path` | `str` | Absolute or relative path to the validated YAML file. |
| `is_compatible` | `bool` | `True` only when `issues` is empty (no errors). |
| `schema_valid` | `bool` | `False` if YAML parsing or `mission` block validation fails. |
| `audit_steps_valid` | `bool` | `False` if no steps or audit_steps are defined. |
| `issues` | `list[CompatibilityIssue]` | All detected compatibility errors. |
| `warnings` | `list[str]` | Non-blocking advisory messages (e.g., deprecation notices). |

**Serialized example (valid):**

```json
{
  "path": "missions/my-mission.yaml",
  "is_compatible": true,
  "schema_valid": true,
  "audit_steps_valid": true,
  "issues": [],
  "warnings": []
}
```

### CompatibilityIssue

```python
class CompatibilityIssue(BaseModel):
    code: str
    field: str
    message: str
    severity: Literal["error", "warning"]
```

| Field | Type | Description |
|-------|------|-------------|
| `code` | `str` | Machine-readable issue code (see [Issue Codes](#issue-codes)). |
| `field` | `str` | Dot-notation path to the offending field (e.g., `"audit_steps[0].audit.trigger_mode"`). |
| `message` | `str` | Human-readable description of the issue. |
| `severity` | `"error" \| "warning"` | `"error"` for compatibility failures; `"warning"` for non-blocking notices. |

**Serialized example:**

```json
{
  "code": "UNKNOWN_TRIGGER_MODE",
  "field": "audit_steps[0].audit.trigger_mode",
  "message": "audit_steps[0].audit.trigger_mode 'on_deploy' is not valid; must be one of: both, manual, post_merge",
  "severity": "error"
}
```

### Issue Codes

| Code | Severity | Description | Affected `is_compatible` |
|------|----------|-------------|--------------------------|
| `YAML_PARSE_ERROR` | `error` | YAML file could not be parsed or root is not a mapping | `False` |
| `MISSING_MISSION_META` | `error` | `mission` block is missing or lacks `key`, `name`, or `version` | `False` |
| `NO_STEPS_DEFINED` | `error` | Neither `steps` nor `audit_steps` is non-empty | `False` |
| `MISSING_STEP_FIELDS` | `error` | An `audit_steps` entry is missing `id` or `title` | `False` |
| `MISSING_AUDIT_CONFIG` | `error` | An `audit_steps` entry has no `audit` block | `False` |
| `UNKNOWN_TRIGGER_MODE` | `error` | `audit.trigger_mode` is not one of `manual`, `post_merge`, `both` | `False` |
| `UNKNOWN_ENFORCEMENT` | `error` | `audit.enforcement` is not one of `advisory`, `blocking` | `False` |
| `UNRESOLVED_DEPENDENCY` | `error` | `depends_on` references an ID not found in `steps` or `audit_steps` | `False` |
| `DUPLICATE_STEP_ID` | `error` | The same `id` appears more than once across `steps` and `audit_steps` | `False` |

---

## Usage Example

```python
from pathlib import Path
from spec_kitty_runtime.diagnostics import validate_mission_template_compatibility

report = validate_mission_template_compatibility("missions/my-mission.yaml")

if report.is_compatible:
    print("Mission template is compatible.")
else:
    for issue in report.issues:
        print(f"[{issue.severity.upper()}] {issue.code} at {issue.field}: {issue.message}")
```

---

## Contract Stability

These contracts are frozen as of **spec-kitty-runtime v0.4.0**. Any breaking change to
serialized field names, types, or enumeration values requires:

1. A semantic version bump (minor for additions, major for removals/renames).
2. An entry in `CHANGELOG.md` with migration guidance.
3. An updated fixture in `tests/fixtures/` demonstrating the new shape.

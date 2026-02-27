# Data Model: Runtime Significance Threshold & Timeout Policy

**Feature**: 004-runtime-significance-threshold-timeout-policy
**Date**: 2026-02-27
**Module**: `src/spec_kitty_runtime/significance.py`

All models use `ConfigDict(frozen=True, extra="forbid")` unless noted.

## Core Entities

### SignificanceDimension

Represents one of six fixed impact dimensions with a name and score.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `name` | `str` | One of 6 fixed values | Dimension identifier |
| `score` | `int` | 0–3, validated | Impact score for this dimension |
| `description` | `str` | Default: "" | Optional human-readable description |

**Fixed Dimension Names** (V1, per C-001):
1. `user_customer_impact`
2. `architectural_system_impact`
3. `data_security_compliance_impact`
4. `operational_reliability_impact`
5. `financial_commercial_impact`
6. `cross_team_blast_radius`

**Validation**: `@model_validator` rejects scores outside 0–3 and names not in the fixed set.

### SignificanceScore

The composite evaluation result for a decision across all six dimensions.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `dimensions` | `tuple[SignificanceDimension, ...]` | Exactly 6, validated | Individual dimension scores |
| `composite` | `int` | 0–18, computed | Sum of all dimension scores |
| `band` | `RoutingBand` | Computed from composite + cutoffs | Resolved routing band |
| `hard_trigger_classes` | `tuple[HardTriggerClass, ...]` | Default: () | Matching hard-trigger overrides |
| `effective_band` | `RoutingBand` | Computed | `high` if any hard_trigger_classes, else `band` |

**Validation**:
- Exactly 6 dimensions, one per fixed name (no duplicates, no omissions)
- `composite` must equal sum of dimension scores
- `effective_band` must be `high` when `hard_trigger_classes` is non-empty

### RoutingBand

Enum-like frozen model representing a significance tier.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `name` | `Literal["low", "medium", "high"]` | Required | Band identifier |
| `min_score` | `int` | 0–18 | Lower boundary (inclusive) |
| `max_score` | `int` | 0–18, >= min_score | Upper boundary (inclusive) |

**Default Bands**:
- `low`: 0–6 (auto-proceed, logged)
- `medium`: 7–11 (soft gate)
- `high`: 12–18 (hard gate)

### HardTriggerClass

One of five predefined conditions that override numeric scoring.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `class_id` | `str` | One of 5 fixed values | Trigger class identifier |
| `description` | `str` | Required | Human-readable description |

**Fixed Classes** (V1, per C-003):
1. `production_data_destructive` — Production data-destructive or schema-impacting changes
2. `security_privacy_access_control` — Security/privacy/access-control changes
3. `legal_compliance_regulatory` — Legal/compliance/regulatory impact
4. `billing_financial_commitment` — Billing/financial commitment changes
5. `architecture_foundation` — Architecture-foundation changes (language, framework, runtime, datastore, infrastructure)

### TimeoutPolicy

Configuration governing the timeout window for a decision.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `default_timeout_seconds` | `int` | > 0, validated | Default timeout for all decisions (default: 600) |
| `per_decision_timeout_seconds` | `int \| None` | > 0 if set | Per-decision override (set by responsible human) |
| `effective_timeout_seconds` | `int` | Computed | `per_decision_timeout_seconds or default_timeout_seconds` |

**Validation**: `@model_validator` rejects timeout <= 0.

### SoftGateDecision

A medium-band decision record capturing the responsible human's chosen action.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `decision_id` | `str` | Non-empty | Reference to the decision |
| `action` | `Literal["decide_solo", "open_stand_up", "defer"]` | Required | Chosen action |
| `actor` | `ActorIdentity` | Must be human | Who made the decision |
| `timestamp` | `datetime` | UTC | When the decision was made |
| `significance_score` | `SignificanceScore` | Required | Full significance evaluation |
| `participants` | `tuple[ActorIdentity, ...]` | Default: () | Stand-up participants (for open_stand_up) |
| `outcome` | `str \| None` | None until resolved | Final outcome (approve/reject/defer) |
| `rationale` | `str \| None` | None if not provided | Human-provided rationale |

## Event Payload Models

### SignificanceEvaluatedPayload

Emitted when a decision's significance is evaluated and routed.

| Field | Type | Description |
|-------|------|-------------|
| `run_id` | `str` | Mission run identifier |
| `decision_id` | `str` | Decision identifier |
| `step_id` | `str` | Associated step identifier |
| `significance_score` | `dict` | Serialized SignificanceScore (dimension scores, composite, band) |
| `hard_trigger_classes` | `tuple[str, ...]` | Matching hard-trigger class IDs |
| `effective_band` | `str` | Final routing band after hard-trigger override |
| `actor` | `ActorIdentity` | System actor (scoring is system-initiated) |

### TimeoutExpiredPayload

Emitted when a decision exceeds its configured timeout window.

| Field | Type | Description |
|-------|------|-------------|
| `run_id` | `str` | Mission run identifier |
| `decision_id` | `str` | Decision identifier |
| `step_id` | `str` | Associated step identifier |
| `significance_score` | `dict` | Serialized SignificanceScore |
| `effective_band` | `str` | Routing band at timeout |
| `timeout_configured_seconds` | `int` | Configured timeout value |
| `escalation_targets` | `tuple[ActorIdentity, ...]` | Actors to escalate to |
| `raci_snapshot` | `dict` | Serialized ResolvedRACIBinding at escalation time |
| `actor` | `ActorIdentity` | System actor (timeout is system-initiated) |

## Result Models

### TimeoutEscalationResult

Returned by `engine.notify_decision_timeout()` to the caller.

| Field | Type | Description |
|-------|------|-------------|
| `decision_id` | `str` | Decision identifier |
| `escalation_targets` | `tuple[ActorIdentity, ...]` | Actors to notify |
| `band` | `str` | Routing band at timeout |
| `timeout_expired_payload` | `TimeoutExpiredPayload` | The emitted event payload |

### DimensionScoreOverride

Audit record for runtime score overrides (secondary scoring path).

| Field | Type | Description |
|-------|------|-------------|
| `decision_id` | `str` | Decision identifier |
| `overridden_by` | `ActorIdentity` | Must be human (FR-018) |
| `override_reason` | `str` | Non-empty mandatory justification |
| `original_scores` | `dict[str, int]` | Before-values (dimension_name → score) |
| `new_scores` | `dict[str, int]` | After-values (dimension_name → score) |
| `override_timestamp` | `datetime` | UTC timestamp |

## Relationships

```
MissionTemplate
  └── AuditStep
        └── significance (optional block)
              ├── dimensions: dict[str, int]  (6 dimension scores)
              └── hard_triggers: list[str]     (hard-trigger class IDs)

MissionPolicySnapshot.extras
  ├── significance_band_cutoffs: dict[str, list[int]]
  └── significance_default_timeout_seconds: int

MissionRunSnapshot.decisions
  ├── "significance:<decision_id>": SignificanceScore (serialized)
  ├── "raci:<step_id>": ResolvedRACIBinding (serialized, existing)
  └── "timeout:<decision_id>": TimeoutExpiredPayload (serialized)
```

## State Transitions

```
Decision Raised
  │
  ├─ evaluate_significance(step, policy)
  │     │
  │     ├─ Hard-trigger matched? ──YES──► effective_band = HIGH (hard gate)
  │     │                                   └─ Record all matching classes
  │     │
  │     └─ No hard-trigger
  │           │
  │           ├─ composite 0–6  ──► LOW  (auto-proceed, log)
  │           ├─ composite 7–11 ──► MEDIUM (soft gate)
  │           └─ composite 12–18──► HIGH (hard gate)
  │
  ├─ LOW band: auto-proceed, emit SignificanceEvaluated, log to audit trail
  │
  ├─ MEDIUM band: raise soft gate
  │     ├─ Human chooses: decide_solo → gate clears
  │     ├─ Human chooses: open_stand_up → await outcome → gate clears
  │     ├─ Human chooses: defer → record deferral, timeout continues
  │     └─ Timeout expires → escalate to mission_owner, run stays blocked
  │
  └─ HIGH / HARD-TRIGGER band: raise hard gate
        ├─ Human approves → gate clears, step proceeds
        ├─ Human rejects → step rejected, planner decides next action
        └─ Timeout expires → escalate to mission_owner + A + C from RACI
```

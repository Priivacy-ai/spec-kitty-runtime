# Quickstart: Runtime Significance Threshold & Timeout Policy

**Feature**: 004-runtime-significance-threshold-timeout-policy
**Date**: 2026-02-27

## Adding Significance to a Mission Template

Declare dimension scores and optional hard-trigger classes on an `AuditStep`:

```yaml
# mission.yaml
mission:
  key: deploy-review
  name: Production Deployment Review
  version: "1.0.0"

steps:
  - id: prepare
    title: Prepare deployment artifacts
    prompt: "Gather deployment artifacts for review"

audit_steps:
  - id: deploy-approval
    title: Production deployment approval
    audit:
      trigger_mode: manual
      enforcement: blocking
    significance:
      dimensions:
        user_customer_impact: 2
        architectural_system_impact: 1
        data_security_compliance_impact: 3
        operational_reliability_impact: 2
        financial_commercial_impact: 1
        cross_team_blast_radius: 1
      hard_triggers:
        - production_data_destructive
    depends_on: [prepare]
```

**Dimension scores**: Each of the six fixed dimensions scored 0–3.
**Hard triggers**: Optional list of hard-trigger class IDs that force hard-gate routing regardless of numeric score.

## Significance Evaluation Flow

When the engine reaches an audit step with a `significance` block:

```python
from spec_kitty_runtime.significance import evaluate_significance

# The engine calls this internally during plan_next/next_step:
score = evaluate_significance(
    dimension_scores={
        "user_customer_impact": 2,
        "architectural_system_impact": 1,
        "data_security_compliance_impact": 3,
        "operational_reliability_impact": 2,
        "financial_commercial_impact": 1,
        "cross_team_blast_radius": 1,
    },
    hard_trigger_classes=["production_data_destructive"],
    band_cutoffs=None,  # None = use defaults (low: 0-6, medium: 7-11, high: 12-18)
)

assert score.composite == 10
assert score.band.name == "medium"
assert score.effective_band.name == "high"  # hard-trigger override
assert "production_data_destructive" in [ht.class_id for ht in score.hard_trigger_classes]
```

## Routing Behavior by Band

| Effective Band | Behavior | Human Action Required |
|---|---|---|
| **low** (0–6) | Auto-proceed, logged | No |
| **medium** (7–11) | Soft gate: decide-solo / open-stand-up / defer | Yes |
| **high** (12–18) or hard-trigger | Hard gate: approve / reject | Yes |

## Custom Policy Configuration

Override band cutoffs and default timeout via `MissionPolicySnapshot.extras`:

```python
from spec_kitty_runtime.schema import MissionPolicySnapshot

policy = MissionPolicySnapshot(
    extras={
        "significance_band_cutoffs": {
            "low": [0, 5],
            "medium": [6, 10],
            "high": [11, 18],
        },
        "significance_default_timeout_seconds": 1200,  # 20 minutes
    }
)
```

**Validation**: Cutoffs must be contiguous, non-overlapping, and cover 0–18. Invalid configurations raise `ValidationError` at policy load time.

## Timeout and Escalation

The runtime caller manages wall-clock timers. When a timeout expires, call:

```python
from spec_kitty_runtime.engine import notify_decision_timeout
from spec_kitty_events.mission_next import RuntimeActorIdentity

# Caller detects timeout has expired
result = notify_decision_timeout(
    run_ref=run_ref,
    decision_id="audit:deploy-approval",
    actor=RuntimeActorIdentity(actor_type="service", actor_id="runtime"),
)

# Result contains escalation targets for notification delivery
for target in result.escalation_targets:
    print(f"Escalate to: {target.actor_type} / {target.actor_id}")
    # Medium band: mission_owner only
    # High/hard-trigger: mission_owner + accountable + consulted from RACI
```

**Fail-closed**: The run remains blocked after timeout. No silent approvals.

## Runtime Score Override (Secondary Path)

A responsible human can override template-declared scores at decision time:

```python
from spec_kitty_runtime.significance import DimensionScoreOverride

override = DimensionScoreOverride(
    decision_id="audit:deploy-approval",
    overridden_by=RuntimeActorIdentity(actor_type="human", actor_id="reviewer-001"),
    override_reason="Actual schema impact is lower than template estimate",
    original_scores={"data_security_compliance_impact": 3},
    new_scores={"data_security_compliance_impact": 1},
    override_timestamp=datetime.now(timezone.utc),
)
# Re-evaluate significance with overridden scores
# Full audit trail: who, why, before/after values
```

## Event Payloads

Two new events emitted by the runtime:

1. **`significance_evaluated`** — When a decision's significance is scored and routed
2. **`decision_timeout_expired`** — When a decision exceeds its timeout window

Both events are persisted in the JSONL event log and delivered via `RuntimeEventEmitter`.

## Testing Fixtures

The feature ships with YAML fixtures for all bands:

| Fixture | Composite | Band | Hard-Trigger |
|---------|-----------|------|---|
| `mission_significance_low.yaml` | 6 | low | No |
| `mission_significance_medium.yaml` | 9 | medium | No |
| `mission_significance_high.yaml` | 15 | high | No |
| `mission_hard_trigger.yaml` | 2 | low→high | Yes |

## P0 Invariant

The mission owner remains final human authority. LLMs participate only in Consulted/Informed RACI roles. LLMs cannot score dimensions, override significance evaluations, or approve/reject decisions at any band (FR-018, C-005).

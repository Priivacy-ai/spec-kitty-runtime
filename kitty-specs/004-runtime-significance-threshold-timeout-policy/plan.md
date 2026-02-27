# Implementation Plan: Runtime Significance Threshold & Timeout Policy

**Branch**: `main` | **Date**: 2026-02-27 | **Spec**: `kitty-specs/004-runtime-significance-threshold-timeout-policy/spec.md`
**Input**: Feature specification from `kitty-specs/004-runtime-significance-threshold-timeout-policy/spec.md`

## Summary

Introduce a significance scoring model that classifies each blocking decision by impact across six fixed dimensions (composite score 0–18), routes decisions to one of three bands (low/medium/high), enforces five hard-trigger override classes, and implements a configurable timeout policy with escalation targeting using existing RACI bindings. All new models and evaluation logic live in a cohesive `significance.py` module. Event payloads are defined locally in the runtime (not dependent on spec-kitty-events v2.4.0). The engine exposes an explicit `notify_decision_timeout()` API for caller-driven timeout notification. Template-declared dimension scores are the primary scoring path; runtime human overrides are secondary with mandatory audit fields.

## Technical Context

**Language/Version**: Python 3.11+ (matching existing codebase)
**Primary Dependencies**: Pydantic v2 (>=2.0,<3.0), PyYAML, spec-kitty-events==2.3.1
**Storage**: JSON snapshot files (existing `run_state.json` pattern in engine.py)
**Testing**: pytest (deterministic, fixture-based, no randomness)
**Target Platform**: Local runtime (offline, no network calls per NFR-004)
**Project Type**: Single Python package (`src/spec_kitty_runtime/`)
**Performance Goals**: Significance evaluation <50ms on commodity hardware (NFR-001), timeout accuracy ±1s (NFR-002)
**Constraints**: Deterministic evaluation (NFR-003), frozen Pydantic schemas (NFR-005), six fixed dimensions (C-001), five fixed hard-trigger classes (C-003), caller manages wall-clock timers (C-004)
**Scale/Scope**: Extends existing runtime (~545 lines schema.py, ~400 lines engine.py) with new ~400-line significance.py module

## Constitution Check

*Constitution file absent (`.kittify/constitution/constitution.md` not found). Gate check skipped.*

## Project Structure

### Documentation (this feature)

```
kitty-specs/004-runtime-significance-threshold-timeout-policy/
├── plan.md              # This file
├── spec.md              # Feature specification (exists)
├── meta.json            # Feature metadata (exists)
├── research/
│   └── research.md      # Phase 0 research findings
├── data-model.md        # Phase 1 entity model reference
├── quickstart.md        # Phase 1 integration guide
├── contracts/
│   ├── significance-evaluation.yaml   # SignificanceScore payload shape
│   ├── timeout-expired-event.yaml     # TimeoutExpiredPayload shape
│   └── soft-gate-decision.yaml        # SoftGateDecision payload shape
└── tasks.md             # Phase 2 output (NOT created by /spec-kitty.plan)
```

### Source Code (repository root)

```
src/spec_kitty_runtime/
├── significance.py      # NEW: Models + evaluation logic (primary deliverable)
├── schema.py            # EXISTING: Cross-cutting types (MissionPolicySnapshot, AuditStep)
├── engine.py            # MODIFIED: Add notify_decision_timeout(), integrate scoring
├── events.py            # MODIFIED: Extend RuntimeEventEmitter protocol
├── __init__.py          # MODIFIED: Re-export significance public API
├── raci.py              # READ-ONLY: Used for escalation target resolution
├── planner.py           # READ-ONLY: DAG resolution (significance hooks after plan_next)
└── ...                  # Other modules unchanged

tests/
├── test_significance.py             # NEW: Core scoring, routing, hard-trigger tests
├── test_significance_timeout.py     # NEW: Timeout policy, escalation, event emission tests
├── test_significance_integration.py # NEW: Engine integration, YAML fixtures, audit trail
├── fixtures/
│   ├── mission_significance_low.yaml     # NEW: Low-band fixture (score 6)
│   ├── mission_significance_medium.yaml  # NEW: Medium-band fixture (score 9)
│   ├── mission_significance_high.yaml    # NEW: High-band fixture (score 15)
│   └── mission_hard_trigger.yaml         # NEW: Hard-trigger override fixture
└── ...
```

**Structure Decision**: New `significance.py` module in existing `src/spec_kitty_runtime/` package. Models and evaluation logic are co-located for cohesion. Public types re-exported via `__init__.py`. No new packages or directories in `src/`.

## Engineering Decisions

### ED-1: Module Organization — New `significance.py`

All significance-related Pydantic models (SignificanceDimension, SignificanceScore, RoutingBand, HardTriggerClass, TimeoutPolicy, SoftGateDecision) and evaluation functions (evaluate_significance, resolve_escalation_targets) live in `significance.py`. Cross-cutting types (MissionPolicySnapshot, AuditStep) remain in `schema.py`. Public API re-exported via `__init__.py`.

**Rationale**: Keeps the significance subsystem cohesive without bloating `schema.py` (~545 lines). Matches the pattern of `raci.py` (models + logic co-located).

### ED-2: Event Payloads — Local Definition

Significance event payload models (SignificanceEvaluatedPayload, TimeoutExpiredPayload) are defined locally in `significance.py` as frozen Pydantic schemas. `RuntimeEventEmitter` protocol in `events.py` is extended with new methods. `NullEmitter` updated with no-op implementations.

**Rationale**: Decouples Feature 004 from spec-kitty-events v2.4.0 release timeline. Payload field names are intentionally aligned with expected events contracts to minimize migration effort when Feature 018 lands.

**Compatibility Note**: When spec-kitty-events v2.4.0 publishes canonical payload types, the local definitions should be replaced with imports from the events package. Field names and shapes are designed for 1:1 migration.

### ED-3: Timeout Notification — Explicit Engine API

The engine exposes `notify_decision_timeout(run_ref, decision_id, actor)` as the public contract for timeout notification. The caller (host process) tracks wall-clock time and invokes this method when a timeout expires. The engine internally evaluates escalation targets (from persisted RACI bindings), emits the timeout-expired event, and returns escalation information.

**Rationale**: Encapsulates escalation logic and event emission in the engine, preventing duplication across callers. A small pure helper in `significance.py` handles the computation (testable in isolation).

### ED-4: Scoring Entry Point — Template-Declared Primary

Dimension scores and hard-trigger classes are declared in the mission YAML template as metadata on audit steps (or a new `significance` block). This is the primary, deterministic, fixture-testable path. Runtime-provided overrides are a secondary mechanism requiring mandatory audit fields: `overridden_by` (actor identity), `override_reason` (string), `original_scores` (before values).

**Rationale**: Template-declared scores are deterministic and reproducible. Runtime overrides are constrained to responsible-human actors with full audit trail, preventing silent score manipulation.

## Integration Points

### With Feature 001 (Audit Primitives)

- Significance scoring extends the existing `enforcement="blocking"` behavior on `AuditStep`
- Hard-trigger class matching evaluates audit step metadata
- Audit trail capture uses the existing `decisions` dict in `MissionRunSnapshot` (keyed as `significance:<decision_id>`)
- The `provide_decision_answer()` flow in engine.py checks significance routing before allowing approve/reject

### With Feature 003 (RACI Inference)

- Timeout escalation queries persisted `ResolvedRACIBinding` (already stored as `decisions["raci:<step_id>"]` in engine.py:306)
- Medium-band escalation: targets mission owner (from `accountable.actor_id`)
- High-band/hard-trigger escalation: targets mission owner + `accountable.actor_id` + `[c.actor_id for c in consulted]`
- Empty consulted set is logged but does not block escalation (per spec edge case)

### With MissionPolicySnapshot

- Significance configuration lives in `MissionPolicySnapshot.extras` under well-defined keys:
  - `extras["significance_band_cutoffs"]` — custom band boundaries
  - `extras["significance_default_timeout_seconds"]` — custom default timeout
- Validation at policy load time rejects invalid cutoffs (overlapping, gaps, not covering 0–18)
- Default values used when extras keys are absent (low: 0–6, medium: 7–11, high: 12–18, timeout: 600s)

## Complexity Tracking

*No constitution violations to justify — constitution absent.*

| Aspect | Complexity | Justification |
|--------|-----------|---------------|
| New module (`significance.py`) | Moderate | 7+ frozen Pydantic models + 3 evaluation functions; cohesive single module |
| Engine modification | Low | Add 1 new public function (`notify_decision_timeout`), extend decision flow |
| Event protocol extension | Low | Add 2 new methods to `RuntimeEventEmitter` protocol + `NullEmitter` |
| Test surface | Moderate | ~3 new test files, ~8 YAML fixtures, targeting 40+ tests |

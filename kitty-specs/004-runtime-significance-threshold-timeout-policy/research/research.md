# Research: Runtime Significance Threshold & Timeout Policy

**Feature**: 004-runtime-significance-threshold-timeout-policy
**Date**: 2026-02-27

## R-001: Module Organization for Significance Subsystem

**Decision**: New `significance.py` module in `src/spec_kitty_runtime/`

**Rationale**: The feature introduces 7+ new domain entities and 3+ evaluation functions. Adding these to `schema.py` (~545 lines) would push it past reasonable cohesion limits. The `raci.py` module (models + inference logic co-located, ~258 lines) establishes the precedent for domain-specific modules. Public types re-exported via `__init__.py` preserves API discoverability.

**Alternatives Considered**:
- **Add to schema.py**: Rejected — would grow schema.py to ~900+ lines with mixed concerns (mission templates + significance scoring). Harder to navigate and test independently.
- **Separate models.py + evaluator.py**: Rejected — over-splits a cohesive domain. Significance models are tightly coupled to evaluation logic (RoutingBand boundaries define scoring behavior).

## R-002: Event Payload Ownership

**Decision**: Define significance event payloads locally in `significance.py` as frozen Pydantic models. Field names aligned with anticipated spec-kitty-events v2.4.0 contracts.

**Rationale**: spec-kitty-events is currently at v2.3.1. Feature 018 (Runtime v0.4.0 Release & Contract Freeze) will repin to v2.4.0, but that dependency is not yet available. Defining payloads locally allows Feature 004 to ship independently. The field naming convention follows existing payload patterns from `spec_kitty_events.mission_next` (snake_case, `run_id`/`step_id`/`actor` as standard fields).

**Alternatives Considered**:
- **Wait for spec-kitty-events v2.4.0**: Rejected — creates a hard dependency on another team's release timeline. Feature 004 would be blocked.
- **Define in events.py**: Rejected — would mix runtime-local payloads with imported payloads. Keeping them in `significance.py` maintains subsystem cohesion.

**Migration Path**: When spec-kitty-events v2.4.0 publishes canonical types:
1. Replace local payload classes with imports from `spec_kitty_events.mission_next`
2. Verify field-level compatibility (names, types, optionality)
3. Update `RuntimeEventEmitter` method signatures if payload types change

## R-003: Timeout Notification Architecture

**Decision**: Explicit `notify_decision_timeout(run_ref, decision_id, actor)` method on the engine.

**Rationale**: Constraint C-004 states the runtime caller manages wall-clock timers. The runtime needs a clear entry point for timeout notification that encapsulates escalation logic. The engine already owns event emission (JSONL log + emitter protocol) and RACI resolution — timeout escalation is a natural extension.

**Internal Structure**:
- `significance.py` exposes `compute_escalation_targets(raci_binding, band, policy)` — pure function, deterministically testable
- `engine.py` calls this function, reads persisted RACI, builds the payload, emits the event
- Return type from `notify_decision_timeout()`: a `TimeoutEscalationResult` (frozen Pydantic) containing escalation targets and the emitted event payload — caller uses this for notification delivery

**Alternatives Considered**:
- **Stateless evaluator only**: Rejected — pushes event emission and RACI lookup to every caller, risking inconsistency. Multiple callers would duplicate escalation logic.
- **Timeout managed internally**: Rejected — violates C-004 (no internal wall-clock timers). Would require asyncio or threading, adding complexity.

## R-004: Scoring Entry Point and Override Audit

**Decision**: Template-declared dimension scores as primary path. Runtime override as secondary with mandatory audit trail.

**Rationale**: Template-declared scores are deterministic and fixture-testable — the same mission YAML always produces the same significance evaluation. This aligns with the existing pattern where `AuditConfig` (enforcement, trigger_mode) is declared in YAML. Runtime overrides serve the use case where a responsible human adjusts scores at decision time (e.g., "this change looks more impactful than the template suggested").

**Template Declaration Shape** (in mission YAML):
```yaml
audit_steps:
  - id: audit-deploy
    title: Production deployment review
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
        cross_team_blast_radius: 0
      hard_triggers:
        - security_privacy_access_control
        - production_data_destructive
```

**Override Audit Fields** (when scores are provided at runtime):
- `overridden_by`: ActorIdentity (must be human, per FR-018)
- `override_reason`: str (non-empty, mandatory)
- `original_scores`: dict (snapshot of template-declared scores before override)
- `override_timestamp`: datetime (UTC)

**Alternatives Considered**:
- **Runtime-only scores (no template declaration)**: Rejected — breaks determinism and fixture testability. Every test would need to simulate a human providing scores.
- **Equal treatment of both paths**: Rejected — adds implementation complexity for V1 with no clear benefit. Template path covers the common case; override path is the exception.

## R-005: Integration Pattern with AuditStep

**Decision**: Extend `AuditStep` YAML schema with an optional `significance` block rather than creating a new step type.

**Rationale**: Significance scoring is an attribute of a blocking decision, not a new kind of step. Existing `AuditStep` already represents "a step that requires human decision." Adding an optional `significance` block preserves backward compatibility — missions without significance declarations continue to work exactly as before (enforcement="blocking" routes as hard-gate by default when no significance is declared).

**Backward Compatibility**:
- `AuditStep` without `significance` block: existing behavior unchanged (enforcement-based routing)
- `AuditStep` with `significance` block: new significance-based routing overrides enforcement-based routing
- `PromptStep`: never evaluated for significance (LLM steps don't have human decision points)

**Alternatives Considered**:
- **New `SignificanceDecisionStep` type**: Rejected — duplicates AuditStep structure, forces migration of existing templates. Violates KISS.
- **Significance as a standalone declaration (not on steps)**: Rejected — loses the association between a specific decision point and its significance. Would require a separate mapping table.

## R-006: Band Cutoff Validation

**Decision**: Validate band cutoffs at policy load time. Cutoffs must be contiguous, non-overlapping, and cover the full 0–18 range.

**Rationale**: Invalid cutoffs (gaps or overlaps) would cause undefined routing behavior. Fail-closed validation at load time prevents runtime surprises. This follows the existing pattern where `RACIAssignment` validates P0 invariants via `@model_validator`.

**Validation Rules**:
1. Exactly three bands must be defined
2. Lowest band must start at 0
3. Highest band must end at 18
4. Each band's `min` must equal the previous band's `max + 1` (contiguous, no gaps)
5. Each band's `min` must be <= its `max` (non-degenerate)

**Default Cutoffs**: `{"low": [0, 6], "medium": [7, 11], "high": [12, 18]}`

## R-007: Timeout Duration Representation

**Decision**: Store timeout as integer seconds in `MissionPolicySnapshot.extras`, expose as seconds in the API.

**Rationale**: The spec mentions "10-minute timeout" and "custom timeout of 30 minutes" but C-004 delegates clock management to the caller. Using seconds (not minutes) as the canonical unit provides finer granularity without floating-point issues. The default of 600 seconds (10 minutes) matches the spec.

**Validation**:
- Timeout must be a positive integer (> 0)
- Minimum: 1 second
- No maximum enforced (caller responsibility)
- Per-decision override must also be positive integer

## R-008: Determinism Guarantees

**Decision**: Significance evaluation is a pure function of (dimension_scores, hard_trigger_classes, band_cutoffs) with no side effects, no randomness, and no external state.

**Verification Approach** (from NFR-003 and SC-008):
- Same SignificanceScore inputs → identical composite, band, hard-trigger classification
- Serialization uses `sort_keys=True`, compact separators (matching existing JsonlEventLog pattern)
- Tests verify bit-for-bit identity across 5+ independent evaluations
- No datetime.now() in evaluation — timestamps only in event payloads (provided by caller or engine)

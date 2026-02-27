# Work Packages: Runtime Significance Threshold & Timeout Policy

**Inputs**: Design documents from `/kitty-specs/004-runtime-significance-threshold-timeout-policy/`
**Prerequisites**: plan.md (required), spec.md (user stories), research.md, data-model.md, contracts/, quickstart.md
**Feature**: 004-runtime-significance-threshold-timeout-policy

**Tests**: Included — the plan explicitly targets ~40+ tests across 3 test files, and success criteria (SC-008) require deterministic verification across 5+ independent runs.

**Organization**: Fine-grained subtasks (`Txxx`) roll up into work packages (`WPxx`). Each work package is independently deliverable and testable. The feature adds ~400 lines to a new `significance.py` module, extends `engine.py`, `events.py`, and `__init__.py`, and ships 3 test files with 4 YAML fixtures.

---

## Work Package WP01: Core Significance Models & Registries (Priority: P0)

**Goal**: Create the foundational Pydantic models in `significance.py` — SignificanceDimension, RoutingBand, HardTriggerClass — with their fixed registries and band cutoff validation. This establishes the type system every other WP builds upon.
**Independent Test**: Models instantiate with valid data, reject invalid data, and registries expose the correct fixed sets.
**Prompt**: `tasks/WP01-core-significance-models.md`
**Estimated Prompt Size**: ~350 lines
**Requirement Refs**: FR-001, FR-002, FR-003, FR-008, FR-015

### Included Subtasks
- [x] T001 Create `src/spec_kitty_runtime/significance.py` with SignificanceDimension frozen Pydantic model
- [x] T002 Implement RoutingBand model with default band definitions and factory function
- [x] T003 Implement HardTriggerClass model with 5 fixed class definitions and registry
- [x] T004 Implement band cutoff validation logic (contiguous, non-overlapping, cover 0–18)
- [x] T005 Create DIMENSION_NAMES and HARD_TRIGGER_REGISTRY constant registries

### Implementation Notes
- All models use `ConfigDict(frozen=True, extra="forbid")` matching existing codebase conventions (see `raci.py`, `schema.py`)
- SignificanceDimension uses `@model_validator(mode="after")` to reject scores outside 0–3 and names not in the fixed set of 6
- RoutingBand defaults: low (0–6), medium (7–11), high (12–18)
- Band cutoff validation: exactly 3 bands, lowest starts at 0, highest ends at 18, contiguous (no gaps), non-overlapping
- HardTriggerClass registry: 5 fixed classes with `class_id` and `description`

### Parallel Opportunities
- T001–T003 can each be implemented independently (different model classes)
- T004 depends on T002 (uses RoutingBand)
- T005 depends on T001, T003 (collects into registry constants)

### Dependencies
- None (first work package — foundation)

### Risks & Mitigations
- Naming drift with contracts/ YAML: Use the exact field names from `contracts/significance-evaluation.yaml`
- Over-engineering models: Keep KISS — no optional fields unless data-model.md specifies them

---

## Work Package WP02: Significance Scoring Engine (Priority: P0)

**Goal**: Implement the core evaluation logic — SignificanceScore model with composite/band/effective_band computation, the `evaluate_significance()` pure function, TimeoutPolicy model, and policy parsing helpers. This is the computational heart of the feature.
**Independent Test**: `evaluate_significance()` returns correct SignificanceScore for all band ranges, hard-trigger overrides force `effective_band=high`, policy parsing extracts cutoffs and timeout from extras dict.
**Prompt**: `tasks/WP02-scoring-engine.md`
**Estimated Prompt Size**: ~450 lines
**Requirement Refs**: FR-001, FR-002, FR-003, FR-010, FR-016, FR-017

### Included Subtasks
- [ ] T006 Implement SignificanceScore model with composite, band, hard_trigger_classes, effective_band
- [ ] T007 Implement `evaluate_significance()` pure function (dimension_scores, hard_trigger_classes, band_cutoffs → SignificanceScore)
- [ ] T008 Implement TimeoutPolicy model with default 600s, per-decision override, validation (>0)
- [ ] T009 Implement `parse_band_cutoffs_from_policy()` for MissionPolicySnapshot.extras
- [ ] T010 Implement `parse_timeout_from_policy()` for MissionPolicySnapshot.extras

### Implementation Notes
- SignificanceScore validates: exactly 6 dimensions, composite == sum of scores, effective_band == high when hard_trigger_classes non-empty
- `evaluate_significance()` is a pure function with NO side effects, NO randomness, NO external state (NFR-003, R-008)
- Policy parsing reads `extras["significance_band_cutoffs"]` and `extras["significance_default_timeout_seconds"]` from MissionPolicySnapshot
- When extras keys are absent, defaults apply (low: 0–6, medium: 7–11, high: 12–18, timeout: 600s)
- TimeoutPolicy: default_timeout_seconds (int, >0), per_decision_timeout_seconds (int|None, >0 if set), effective_timeout_seconds (computed)

### Parallel Opportunities
- T008 (TimeoutPolicy) can proceed in parallel with T006–T007 (different models)
- T009 and T010 are independent of each other

### Dependencies
- Depends on WP01 (uses SignificanceDimension, RoutingBand, HardTriggerClass models)

### Risks & Mitigations
- Evaluation correctness at band boundaries: Test boundary scores 0, 6, 7, 11, 12, 18 explicitly
- Policy parsing with missing keys: Use `.get()` with sensible defaults, never crash on missing extras

---

## Work Package WP03: Event Payloads & Decision Models (Priority: P1)

**Goal**: Implement the event payload models (SignificanceEvaluatedPayload, TimeoutExpiredPayload), the decision capture models (SoftGateDecision, DimensionScoreOverride), and extend the RuntimeEventEmitter protocol with new emission methods.
**Independent Test**: Event payloads serialize to the shapes defined in `contracts/`, SoftGateDecision captures all three actions, emitter protocol has 2 new methods, NullEmitter has no-op implementations.
**Prompt**: `tasks/WP03-event-payloads-decision-models.md`
**Estimated Prompt Size**: ~400 lines
**Requirement Refs**: FR-005, FR-006, FR-009, FR-011, FR-018, FR-019

### Included Subtasks
- [ ] T011 Implement SignificanceEvaluatedPayload frozen model in `significance.py`
- [ ] T012 Implement TimeoutExpiredPayload frozen model in `significance.py`
- [ ] T013 Implement SoftGateDecision model (decide_solo, open_stand_up, defer actions)
- [ ] T014 Implement DimensionScoreOverride model for runtime score override audit trail
- [ ] T015 [P] Extend RuntimeEventEmitter protocol in `events.py` with 2 new emit methods
- [ ] T016 [P] Update NullEmitter in `events.py` with no-op implementations

### Implementation Notes
- Event payloads are defined locally in `significance.py` (not in spec-kitty-events) per ED-2 decision
- Field names aligned with `contracts/timeout-expired-event.yaml` and `contracts/significance-evaluation.yaml`
- SoftGateDecision: action ∈ {decide_solo, open_stand_up, defer}, actor must be human (FR-018)
- DimensionScoreOverride: overridden_by must be human, override_reason non-empty (mandatory), original_scores + new_scores for before/after
- New emitter methods: `emit_significance_evaluated(payload)` and `emit_decision_timeout_expired(payload)`
- NullEmitter gets pass-through implementations (matching existing pattern)

### Parallel Opportunities
- T011–T014 are independent model definitions (can be implemented in parallel)
- T015–T016 are related but independent files (events.py changes)

### Dependencies
- Depends on WP02 (uses SignificanceScore in payload models)

### Risks & Mitigations
- Payload shape drift from contracts/: Validate field names against contract YAML during implementation
- ActorIdentity type usage: Use existing `RACIRoleBinding` from schema.py for actor fields (not a new type)

---

## Work Package WP04: Timeout Escalation & Engine API (Priority: P1)

**Goal**: Implement the escalation logic — `compute_escalation_targets()` pure function that resolves escalation targets from RACI bindings, TimeoutEscalationResult return type, and the `notify_decision_timeout()` public API in engine.py.
**Independent Test**: Escalation targets correct for medium (→ mission owner) and high (→ owner + accountable + consulted) bands, timeout events emitted and persisted, empty consulted set handled gracefully.
**Prompt**: `tasks/WP04-timeout-escalation-engine.md`
**Estimated Prompt Size**: ~400 lines
**Requirement Refs**: FR-011, FR-012, FR-013, FR-014

### Included Subtasks
- [ ] T017 Implement `compute_escalation_targets()` pure function in `significance.py`
- [ ] T018 Implement TimeoutEscalationResult frozen model in `significance.py`
- [ ] T019 Implement `notify_decision_timeout()` in `engine.py`
- [ ] T020 Persist timeout events to `MissionRunSnapshot.decisions` dict

### Implementation Notes
- `compute_escalation_targets(raci_binding, effective_band)` — pure function, deterministic
  - medium band: `[accountable]` (mission owner)
  - high/hard-trigger: `[accountable] + consulted` (mission owner + A + C from RACI snapshot)
  - Empty consulted set: logged but does not block escalation
- `notify_decision_timeout()` in engine.py:
  1. Load persisted RACI binding from `decisions[f"raci:{step_id}"]`
  2. Load significance score from `decisions[f"significance:{decision_id}"]`
  3. Call `compute_escalation_targets(raci_binding, effective_band)`
  4. Build TimeoutExpiredPayload
  5. Emit via `emit_decision_timeout_expired()`
  6. Persist payload to `decisions[f"timeout:{decision_id}"]`
  7. Return TimeoutEscalationResult
- Run remains blocked after timeout (fail-closed, FR-014)

### Parallel Opportunities
- T017 and T018 can proceed in parallel (function vs model)
- T019–T020 are sequential (engine API + persistence)

### Dependencies
- Depends on WP03 (uses TimeoutExpiredPayload, emitter methods)

### Risks & Mitigations
- Missing RACI binding: If `decisions[f"raci:{step_id}"]` not found, raise MissionRuntimeError with clear message
- Missing significance score: Same — fail-closed, not fail-open
- Concurrent timeout calls: Not applicable — runtime is single-threaded per C-004

---

## Work Package WP05: AuditStep Extension & Engine Integration (Priority: P1)

**Goal**: Wire significance evaluation into the existing engine flow — extend AuditStep schema with an optional significance block, integrate scoring into `next_step()` and `provide_decision_answer()`, persist significance data, and export the public API.
**Independent Test**: A mission with a significance block on an audit step produces correct routing, gates, and audit trail entries when processed through the engine.
**Prompt**: `tasks/WP05-auditstep-engine-integration.md`
**Estimated Prompt Size**: ~450 lines
**Requirement Refs**: FR-004, FR-005, FR-007, FR-008, FR-017, FR-018

### Included Subtasks
- [ ] T021 Extend AuditStep schema in `schema.py` with optional `significance` block
- [ ] T022 Integrate significance evaluation into `next_step()` flow in `engine.py`
- [ ] T023 Integrate significance routing into `provide_decision_answer()` flow in `engine.py`
- [ ] T024 Persist significance data in `MissionRunSnapshot.decisions` under `"significance:<decision_id>"`
- [ ] T025 Update `__init__.py` to re-export significance public API types and functions

### Implementation Notes
- AuditStep gets optional `significance: SignificanceBlock | None = None` field
- SignificanceBlock is a new frozen model: `dimensions: dict[str, int]`, `hard_triggers: list[str] = []`
- In `next_step()`: after RACI resolution (line ~286-310), if audit step has significance block → call `evaluate_significance()`, persist result, determine gate type
- In `provide_decision_answer()`: check significance routing — low band: auto-proceed (shouldn't reach here), medium: accept decide_solo/open_stand_up/defer, high: accept approve/reject only
- AuditStep without significance block: existing behavior unchanged (enforcement-based routing)
- Public API exports: `evaluate_significance`, `compute_escalation_targets`, `notify_decision_timeout`, `SignificanceScore`, `SignificanceDimension`, `RoutingBand`, `HardTriggerClass`, `TimeoutPolicy`, `SoftGateDecision`, `DimensionScoreOverride`, `TimeoutEscalationResult`

### Parallel Opportunities
- T021 (schema change) and T025 (__init__.py) can proceed early
- T022–T024 are sequential (engine flow changes)

### Dependencies
- Depends on WP04 (uses notify_decision_timeout(), compute_escalation_targets(), all models)

### Risks & Mitigations
- Backward compatibility: Missions without significance blocks must work exactly as before
- Engine complexity: Keep significance integration minimal — evaluate → persist → adjust gate behavior
- Schema migration: significance field is optional with default None — no breaking change

---

## Work Package WP06: Test Fixtures & Scoring Test Suite (Priority: P1)

**Goal**: Create YAML test fixtures for all band scenarios and write the core test suite for significance scoring, band routing, hard-trigger overrides, boundary conditions, and band cutoff validation.
**Independent Test**: All tests pass with `pytest tests/test_significance.py -v`, fixtures load correctly.
**Prompt**: `tasks/WP06-test-fixtures-scoring-tests.md`
**Estimated Prompt Size**: ~450 lines
**Requirement Refs**: FR-001, FR-002, FR-003, FR-008, FR-015

### Included Subtasks
- [ ] T026 [P] Create 4 YAML mission fixtures in `tests/fixtures/` (low, medium, high, hard-trigger)
- [ ] T027 Write dimension validation tests in `tests/test_significance.py`
- [ ] T028 Write composite & band routing tests for all three bands
- [ ] T029 Write hard-trigger override tests (all 5 classes, multiple classes, high score + trigger)
- [ ] T030 Write boundary score tests (0, 6, 7, 11, 12, 18 — exact boundaries)
- [ ] T031 Write band cutoff validation tests (valid custom, overlapping, gaps, defaults)

### Implementation Notes
- Fixtures follow existing YAML pattern from `tests/fixtures/` (see raci_*.yaml, audit_*.yaml)
- Each fixture is a complete mission template with significance block on audit step
- test_significance.py mirrors existing test structure (helper functions, fixture-based, deterministic)
- Boundary tests are critical — verify the exact score at band transitions (6=low, 7=medium, 11=medium, 12=high)
- Hard-trigger tests must verify ALL 5 classes independently + multiple simultaneous classes
- Band cutoff tests: valid custom cutoffs, overlapping ranges (reject), gaps (reject), degenerate ranges (reject)

### Parallel Opportunities
- T026 (fixtures) is independent of T027–T031 (tests use fixtures but can be developed in parallel)
- T027–T031 test different aspects and can be written in parallel

### Dependencies
- Depends on WP02 (tests the scoring engine from WP01+WP02)

### Risks & Mitigations
- Fixture format drift: Follow exact YAML structure from contracts/significance-evaluation.yaml
- Test isolation: Each test must be fully independent (no shared mutable state)
- Flaky tests: No randomness, no datetime.now(), no network (NFR-003, NFR-004)

---

## Work Package WP07: Integration Tests, Timeout Tests & Edge Cases (Priority: P2)

**Goal**: Write timeout policy/escalation tests, engine integration tests exercising the full significance flow through the runtime, determinism verification (5+ runs), and edge case coverage. Validate quickstart.md examples.
**Independent Test**: All tests pass with `pytest tests/test_significance_timeout.py tests/test_significance_integration.py -v`.
**Prompt**: `tasks/WP07-integration-tests-edge-cases.md`
**Estimated Prompt Size**: ~500 lines
**Requirement Refs**: FR-010, FR-011, FR-012, FR-013, FR-014, FR-016, FR-017, FR-019

### Included Subtasks
- [ ] T032 Write timeout policy & escalation target tests in `tests/test_significance_timeout.py`
- [ ] T033 Write timeout event emission tests (JSONL log, emitter protocol)
- [ ] T034 Write engine flow integration tests in `tests/test_significance_integration.py`
- [ ] T035 Write audit trail capture tests (significance score, timeout events in decisions dict)
- [ ] T036 Write determinism verification tests (5+ independent runs, bit-for-bit identical output)
- [ ] T037 Write edge case tests + validate quickstart.md code examples

### Implementation Notes
- Timeout tests: default timeout, custom timeout, per-decision override, timeout=0 rejection
- Escalation tests: medium→owner, high→owner+A+C, empty consulted, responsible==owner
- Integration tests: full engine flow from start_mission_run → next_step (audit with significance) → provide_decision_answer, verify state.json and events.jsonl
- Determinism tests (SC-008): Run evaluate_significance() 5+ times with identical inputs, verify bit-for-bit identical serialized output using sort_keys=True
- Edge cases: score 0 (all zeros), score 18 (all threes), multiple simultaneous hard-triggers, <6 dimensions (reject), dimension score out of range (reject), timeout=0 (reject), invalid cutoffs, RACI snapshot with no consulted actors
- Quickstart validation: Verify code examples from quickstart.md actually work against implemented API

### Parallel Opportunities
- T032–T033 (timeout tests) are independent of T034–T035 (integration tests)
- T036 (determinism) and T037 (edge cases) are independent of each other

### Dependencies
- Depends on WP05 (engine integration must be complete)
- Depends on WP06 (uses YAML fixtures created in WP06)

### Risks & Mitigations
- Integration test complexity: Keep tests focused on one flow per test function
- Fixture dependency: If fixtures change shape, integration tests may break — use fixture loading helpers
- Determinism verification: Use JSON serialization with sort_keys=True and compare string output

---

## Dependency & Execution Summary

```
WP01 → WP02 → WP03 → WP04 → WP05 → WP07
                ↓                       ↑
              WP06 ─────────────────────┘
```

- **Critical Path**: WP01 → WP02 → WP03 → WP04 → WP05 → WP07
- **Parallel Branch**: WP06 can start after WP02 completes (parallel with WP03–WP05)
- **Convergence**: WP07 waits for both WP05 and WP06

### Parallelization Opportunities
- **After WP02**: WP03 (event payloads) and WP06 (scoring tests) can proceed in parallel
- **After WP05**: WP07 starts (needs both WP05 + WP06 complete)

### MVP Scope
- **WP01 + WP02**: Delivers the core significance scoring engine (US1, US2 — both P1)
- **WP01 + WP02 + WP06**: Adds verified test coverage for scoring and routing
- **Full feature**: All 7 WPs deliver complete significance + timeout + escalation + tests

### Execution Sequence
1. WP01 (foundation models) — start immediately
2. WP02 (scoring engine) — after WP01
3. WP03 + WP06 (parallel: event payloads + test fixtures/scoring tests) — after WP02
4. WP04 (timeout/escalation) — after WP03
5. WP05 (engine integration) — after WP04
6. WP07 (integration tests + edge cases) — after WP05 + WP06

---

## Subtask Index (Reference)

| Subtask ID | Summary | Work Package | Priority | Parallel? |
|------------|---------|--------------|----------|-----------|
| T001 | Create significance.py with SignificanceDimension model | WP01 | P0 | No |
| T002 | Implement RoutingBand model with defaults | WP01 | P0 | Yes |
| T003 | Implement HardTriggerClass model with fixed registry | WP01 | P0 | Yes |
| T004 | Implement band cutoff validation logic | WP01 | P0 | No |
| T005 | Create DIMENSION_NAMES and HARD_TRIGGER_REGISTRY constants | WP01 | P0 | No |
| T006 | Implement SignificanceScore model | WP02 | P0 | No |
| T007 | Implement evaluate_significance() pure function | WP02 | P0 | No |
| T008 | Implement TimeoutPolicy model | WP02 | P0 | Yes |
| T009 | Implement parse_band_cutoffs_from_policy() | WP02 | P0 | Yes |
| T010 | Implement parse_timeout_from_policy() | WP02 | P0 | Yes |
| T011 | Implement SignificanceEvaluatedPayload model | WP03 | P1 | Yes |
| T012 | Implement TimeoutExpiredPayload model | WP03 | P1 | Yes |
| T013 | Implement SoftGateDecision model | WP03 | P1 | Yes |
| T014 | Implement DimensionScoreOverride model | WP03 | P1 | Yes |
| T015 | Extend RuntimeEventEmitter protocol | WP03 | P1 | Yes |
| T016 | Update NullEmitter with no-op implementations | WP03 | P1 | Yes |
| T017 | Implement compute_escalation_targets() | WP04 | P1 | Yes |
| T018 | Implement TimeoutEscalationResult model | WP04 | P1 | Yes |
| T019 | Implement notify_decision_timeout() in engine.py | WP04 | P1 | No |
| T020 | Persist timeout events to decisions dict | WP04 | P1 | No |
| T021 | Extend AuditStep schema with significance block | WP05 | P1 | No |
| T022 | Integrate significance into next_step() | WP05 | P1 | No |
| T023 | Integrate significance into provide_decision_answer() | WP05 | P1 | No |
| T024 | Persist significance data in decisions dict | WP05 | P1 | No |
| T025 | Update __init__.py re-exports | WP05 | P1 | Yes |
| T026 | Create 4 YAML mission fixtures | WP06 | P1 | Yes |
| T027 | Dimension validation tests | WP06 | P1 | Yes |
| T028 | Composite & band routing tests | WP06 | P1 | Yes |
| T029 | Hard-trigger override tests | WP06 | P1 | Yes |
| T030 | Boundary score tests | WP06 | P1 | Yes |
| T031 | Band cutoff validation tests | WP06 | P1 | Yes |
| T032 | Timeout policy & escalation tests | WP07 | P2 | Yes |
| T033 | Timeout event emission tests | WP07 | P2 | Yes |
| T034 | Engine flow integration tests | WP07 | P2 | Yes |
| T035 | Audit trail capture tests | WP07 | P2 | Yes |
| T036 | Determinism verification tests | WP07 | P2 | Yes |
| T037 | Edge case tests + quickstart validation | WP07 | P2 | Yes |

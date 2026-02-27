# Feature Specification: Runtime Significance Threshold & Timeout Policy

**Feature Branch**: `004-runtime-significance-threshold-timeout-policy`
**Created**: 2026-02-27
**Status**: Draft
**Input**: User description: "runtime significance threshold timeout policy"

## Overview

The runtime currently treats all blocking decisions equally — any audit checkpoint with `enforcement=blocking` halts the mission run indefinitely with no differentiation by impact level. This creates two problems: low-impact decisions unnecessarily block mission progression, and high-impact decisions lack escalation mechanisms when responsible actors are unavailable.

This feature introduces a **significance scoring model** that classifies each decision by impact across six fixed dimensions, producing a composite score that determines routing behavior. It also introduces a **timeout policy** governing escalation when decisions stall, ensuring no silent approvals occur at medium or high significance levels while allowing low-significance decisions to auto-proceed.

The P0 invariant is preserved: the mission owner remains final human authority, and LLMs participate only in Consulted/Informed RACI roles.

## User Scenarios & Testing

### User Story 1 — Score a Decision and Route by Significance Band (Priority: P1)

A mission step reaches a decision point. The runtime evaluates the decision against six fixed significance dimensions, computes a composite score (0–18), and routes the decision to the appropriate band: auto-proceed (low), soft gate (medium), or hard gate (high).

**Why this priority**: This is the foundational capability — without scoring and routing, no other behavior (timeouts, escalation, hard-triggers) can function.

**Independent Test**: Can be fully tested by presenting a decision with known dimension scores and verifying the runtime selects the correct routing band and emits the corresponding event.

**Acceptance Scenarios**:

1. **Given** a decision with all six dimensions scored at 1 (total 6), **When** the runtime evaluates significance, **Then** the decision is routed to the low band (0–6), logged, and the step auto-proceeds without a human gate.
2. **Given** a decision with dimensions totaling 9, **When** the runtime evaluates significance, **Then** the decision is routed to the medium band (7–11) and a soft gate is raised with a stand-up suggestion and recommended participants.
3. **Given** a decision with dimensions totaling 15, **When** the runtime evaluates significance, **Then** the decision is routed to the high band (12–18) and a hard gate is raised requiring explicit human approve/reject.
4. **Given** a decision with dimensions totaling exactly 7 (lower boundary of medium), **When** the runtime evaluates significance, **Then** the decision is routed to the medium band, not the low band.
5. **Given** a decision with dimensions totaling exactly 12 (lower boundary of high), **When** the runtime evaluates significance, **Then** the decision is routed to the high band, not the medium band.

---

### User Story 2 — Hard-Trigger Class Override (Priority: P1)

A decision matches one or more hard-trigger classes regardless of its numeric significance score. The runtime bypasses band routing and forces the decision into hard-gate behavior (equivalent to high band), requiring explicit human approve/reject.

**Why this priority**: Hard-trigger classes protect against catastrophic outcomes (production data loss, security breaches, compliance violations) and must work independently of the scoring model.

**Independent Test**: Can be tested by presenting a decision with a low numeric score (e.g., total 3) that matches a hard-trigger class, and verifying it routes as hard-gate rather than auto-proceed.

**Acceptance Scenarios**:

1. **Given** a decision with total score 2 (low band) but flagged as "production data-destructive," **When** the runtime evaluates significance, **Then** the hard-trigger override activates and the decision requires explicit human approve/reject.
2. **Given** a decision flagged with "security/privacy/access-control changes," **When** the runtime evaluates significance, **Then** the decision routes as hard-gate regardless of numeric score.
3. **Given** a decision flagged with "billing/financial commitment changes," **When** the runtime evaluates significance, **Then** the decision routes as hard-gate regardless of numeric score.
4. **Given** a decision flagged with "architecture-foundation changes" (language, framework, runtime, datastore, or infrastructure), **When** the runtime evaluates significance, **Then** the decision routes as hard-gate regardless of numeric score.
5. **Given** a decision flagged with "legal/compliance/regulatory impact," **When** the runtime evaluates significance, **Then** the decision routes as hard-gate regardless of numeric score.
6. **Given** a decision with a high numeric score (14) AND a hard-trigger class, **When** the runtime evaluates significance, **Then** the hard-trigger is recorded in the audit trail alongside the numeric score (both are captured, hard-trigger takes routing precedence).

---

### User Story 3 — Timeout Expiry and Escalation at Medium Band (Priority: P2)

A medium-band decision is raised and the responsible human does not act within the configured timeout window. The runtime emits a timeout-expired event, escalates to the mission owner (if the responsible human is not already the mission owner), and keeps the run blocked until explicit human action.

**Why this priority**: Timeout escalation prevents medium-significance decisions from stalling indefinitely, while the fail-closed behavior ensures no implicit approvals.

**Independent Test**: Can be tested by raising a medium-band decision, simulating timeout expiry, and verifying the escalation event targets the mission owner and the run remains blocked.

**Acceptance Scenarios**:

1. **Given** a medium-band decision with the default 10-minute timeout and responsible human ≠ mission owner, **When** the timeout expires without action, **Then** the runtime emits a timeout-expired event, escalates to the mission owner, and the run remains blocked.
2. **Given** a medium-band decision where responsible human = mission owner, **When** the timeout expires without action, **Then** the runtime emits a timeout-expired event (no escalation target change) and the run remains blocked.
3. **Given** a medium-band decision with a custom timeout of 30 minutes set by the responsible human, **When** 10 minutes elapse, **Then** no timeout event is emitted; the decision remains in its original state.
4. **Given** a medium-band decision that has timed out and escalated, **When** the mission owner provides an explicit decision (decide-solo, open-stand-up, or defer), **Then** the run unblocks and proceeds according to the chosen action.

---

### User Story 4 — Timeout Expiry and Escalation at High Band / Hard-Trigger (Priority: P2)

A high-band or hard-trigger decision is raised and the responsible human does not act within the configured timeout window. The runtime emits a timeout-expired event, escalates to the mission owner AND the accountable/consulted set from the current RACI snapshot, and keeps the run blocked until explicit human approve/reject.

**Why this priority**: High-significance and hard-trigger decisions carry the greatest risk. Escalation to the full RACI stakeholder set ensures visibility.

**Independent Test**: Can be tested by raising a high-band decision, simulating timeout expiry, and verifying the escalation event targets the mission owner plus accountable and consulted actors from the RACI snapshot.

**Acceptance Scenarios**:

1. **Given** a high-band decision with the default 10-minute timeout, **When** the timeout expires, **Then** the runtime emits a timeout-expired event, escalates to mission owner + accountable + consulted actors from the RACI snapshot, and the run remains blocked.
2. **Given** a hard-trigger decision (e.g., security/privacy change) with a custom 5-minute timeout, **When** 5 minutes elapse without action, **Then** the runtime emits a timeout-expired event with the same escalation behavior as high-band.
3. **Given** a high-band decision that has timed out and escalated, **When** the mission owner provides an explicit approve, **Then** the run unblocks and the step proceeds. The escalation event and resolution are captured in the audit trail.
4. **Given** a high-band decision that has timed out and escalated, **When** the mission owner provides an explicit reject, **Then** the run unblocks, the step is marked rejected, and the planner determines the next action (re-route or terminal).

---

### User Story 5 — Medium-Band Soft Gate Decision Capture (Priority: P2)

A medium-band decision is raised and the responsible human is presented with three action choices: decide-solo, open-stand-up, or defer. The chosen action and any rationale are recorded in the decision audit trail.

**Why this priority**: The soft gate is the distinguishing behavior of the medium band. Without structured decision capture, the medium band degrades to either low (no gate) or high (hard gate).

**Independent Test**: Can be tested by raising a medium-band decision, providing each of the three action choices, and verifying the decision record captures the action, actor, timestamp, and any participants.

**Acceptance Scenarios**:

1. **Given** a medium-band decision, **When** the responsible human chooses "decide-solo," **Then** the decision is recorded with action=decide-solo, the gate clears, and the step proceeds.
2. **Given** a medium-band decision, **When** the responsible human chooses "open-stand-up," **Then** the runtime records the stand-up participants, the decision outcome (approve/reject/defer), and the gate clears only after a final decision is captured.
3. **Given** a medium-band decision, **When** the responsible human chooses "defer," **Then** the deferral is recorded with a reason, and the timeout clock continues (or resets, per policy configuration).
4. **Given** a medium-band decision, **When** the responsible human provides a decision, **Then** the audit trail includes: actor identity, action chosen, timestamp, significance score, and routing band.

---

### User Story 6 — Configurable Threshold Cutoffs and Timeout via Policy (Priority: P3)

A runtime consumer configures custom band boundaries (e.g., shifting medium to 5–10 instead of 7–11) and a custom default timeout (e.g., 20 minutes instead of 10) through the mission policy settings. The runtime applies these overrides deterministically.

**Why this priority**: Configurability enables different teams/organizations to tune the system to their risk tolerance, but the defaults are sufficient for V1 launch.

**Independent Test**: Can be tested by providing a custom policy with modified cutoffs, scoring a decision, and verifying it routes to the band defined by the custom cutoffs rather than the defaults.

**Acceptance Scenarios**:

1. **Given** a policy with custom band cutoffs [0–5, 6–10, 11–18], **When** a decision scores 6, **Then** it routes to the medium band (not low, as it would under defaults).
2. **Given** a policy with a custom default timeout of 20 minutes, **When** a medium-band decision is raised, **Then** the timeout window is 20 minutes.
3. **Given** a policy with no custom overrides, **When** a decision is evaluated, **Then** the default cutoffs [0–6, 7–11, 12–18] and 10-minute timeout apply.
4. **Given** a policy with invalid cutoffs (overlapping ranges or gaps), **When** the policy is loaded, **Then** the runtime rejects the policy with a validation error identifying the specific problem.

---

### Edge Cases

- What happens when a decision has all six dimensions scored at 0 (total 0)? Routes to low band, auto-proceeds, logged.
- What happens when a decision has all six dimensions scored at 3 (total 18)? Routes to high band, hard gate enforced.
- What happens when a decision matches multiple hard-trigger classes simultaneously? All matching classes are recorded in the audit trail; routing behavior is the same as a single hard-trigger (hard gate).
- What happens when the responsible human edits the timeout to 0 minutes? The runtime rejects this as invalid; minimum timeout must be greater than zero.
- What happens when the responsible human edits the timeout after the original timeout has already expired? The escalation event has already fired; the edit applies to any subsequent timeout cycle if the decision is re-presented.
- What happens when a dimension score is outside the 0–3 range? The runtime rejects the score at validation time with a clear error identifying the out-of-range dimension.
- What happens when fewer than six dimensions are provided? The runtime rejects the input; all six dimensions are required for V1 (no partial scoring).
- What happens when the RACI snapshot has no consulted actors for a high-band timeout escalation? Escalation targets mission owner + accountable only; the empty consulted set is logged but does not block escalation.

## Requirements

### Functional Requirements

- **FR-001**: System MUST evaluate each decision against six fixed significance dimensions (user/customer impact, architectural/system impact, data/security/compliance impact, operational reliability impact, financial/commercial impact, cross-team blast radius), each scored 0–3.
  - Status: Approved

- **FR-002**: System MUST compute a composite significance score (0–18) as the sum of all six dimension scores.
  - Status: Approved

- **FR-003**: System MUST route decisions to one of three bands based on composite score: low (0–6), medium (7–11), high (12–18).
  - Status: Approved

- **FR-004**: System MUST auto-proceed and log decisions in the low band (0–6) without requiring a human gate.
  - Status: Approved

- **FR-005**: System MUST raise a soft gate for medium-band decisions (7–11), surfacing a stand-up suggestion with recommended participants and offering the responsible human three actions: decide-solo, open-stand-up, or defer.
  - Status: Approved

- **FR-006**: System MUST record the chosen action, actor identity, timestamp, significance score, and routing band for every medium-band decision.
  - Status: Approved

- **FR-007**: System MUST raise a hard gate for high-band decisions (12–18), requiring explicit human approve/reject before the step proceeds.
  - Status: Approved

- **FR-008**: System MUST recognize five hard-trigger classes that override numeric score and force hard-gate routing: (1) production data-destructive or schema-impacting changes, (2) security/privacy/access-control changes, (3) legal/compliance/regulatory impact, (4) billing/financial commitment changes, (5) architecture-foundation changes (language, framework, runtime, datastore, infrastructure).
  - Status: Approved

- **FR-009**: System MUST record all matching hard-trigger classes in the decision audit trail alongside the numeric significance score.
  - Status: Approved

- **FR-010**: System MUST enforce a configurable default decision timeout of 10 minutes, editable per decision by the responsible human.
  - Status: Approved

- **FR-011**: System MUST emit a timeout-expired event when a medium-band or high-band decision exceeds the configured timeout window.
  - Status: Approved

- **FR-012**: System MUST escalate medium-band timeout-expired decisions to the mission owner (when responsible human ≠ mission owner) and keep the run blocked until explicit human action.
  - Status: Approved

- **FR-013**: System MUST escalate high-band and hard-trigger timeout-expired decisions to the mission owner AND the accountable/consulted actors from the current RACI snapshot, keeping the run blocked until explicit human approve/reject.
  - Status: Approved

- **FR-014**: System MUST NOT auto-proceed on timeout for medium-band, high-band, or hard-trigger decisions (no silent approvals at P0).
  - Status: Approved

- **FR-015**: System MUST validate that all six dimension scores are provided and each is in the range 0–3; reject with a clear error otherwise.
  - Status: Approved

- **FR-016**: System MUST validate that timeout values are greater than zero; reject with a clear error otherwise.
  - Status: Approved

- **FR-017**: System MUST support configurable band cutoffs and default timeout via policy settings, with validation that cutoff ranges are contiguous, non-overlapping, and cover the full 0–18 range.
  - Status: Approved

- **FR-018**: System MUST preserve the P0 invariant: mission owner is final human authority, LLMs participate only in Consulted/Informed RACI roles and cannot approve/reject decisions at any significance band.
  - Status: Approved

- **FR-019**: System MUST capture the complete significance evaluation (dimension scores, composite score, routing band, hard-trigger classes, timeout configuration) in the decision audit trail for every decision point.
  - Status: Approved

### Non-Functional Requirements

- **NFR-001**: Significance evaluation MUST complete within 50 milliseconds for a single decision on commodity hardware, ensuring it does not meaningfully delay step progression.
  - Status: Approved

- **NFR-002**: Timeout tracking MUST be accurate to within 1 second of the configured timeout window.
  - Status: Approved

- **NFR-003**: All significance evaluation logic MUST be deterministic — the same inputs MUST produce the same score, routing band, and hard-trigger classification across independent runs.
  - Status: Approved

- **NFR-004**: Significance models MUST be offline and local-only (no network calls during evaluation), consistent with the existing runtime design.
  - Status: Approved

- **NFR-005**: All new models MUST use frozen Pydantic schemas, consistent with the existing codebase immutability pattern.
  - Status: Approved

### Constraints

- **C-001**: The six significance dimensions are fixed in V1; per-mission custom dimensions are out of scope.
  - Status: Approved

- **C-002**: Band cutoffs and timeout values are configurable via MissionPolicySnapshot; dimension definitions are not.
  - Status: Approved

- **C-003**: Hard-trigger classes are a fixed set of five in V1; custom hard-trigger definitions are out of scope.
  - Status: Approved

- **C-004**: Timeout clock is managed by the runtime caller (host process); the runtime computes and emits timeout events but does not implement wall-clock timers internally.
  - Status: Approved

- **C-005**: LLMs cannot score dimensions or override significance evaluations; scoring is performed by the mission template author or the responsible human actor.
  - Status: Approved

- **C-006**: This feature builds on existing RACI (feature 003) and audit primitive (feature 001) infrastructure; it does not replace or duplicate those capabilities.
  - Status: Approved

### Key Entities

- **SignificanceDimension**: One of six fixed impact dimensions with a name, description, and score (0–3). Represents a single axis of decision impact evaluation.

- **SignificanceScore**: The composite evaluation of a decision across all six dimensions. Contains individual dimension scores, composite total (0–18), the resolved routing band, and any matching hard-trigger classes.

- **RoutingBand**: One of three significance tiers (low, medium, high) that determines the gating behavior for a decision. Defined by configurable lower and upper score boundaries.

- **HardTriggerClass**: One of five predefined conditions that override numeric scoring and force hard-gate routing. Each class has a unique identifier and description.

- **TimeoutPolicy**: Configuration governing the timeout window for a decision, including the default duration, per-decision overrides, and the escalation behavior on expiry.

- **TimeoutExpiredEvent**: An event payload emitted when a decision exceeds its configured timeout window. Contains the decision identity, significance evaluation, escalation targets, and the current RACI snapshot.

- **SoftGateDecision**: A medium-band decision record capturing the responsible human's chosen action (decide-solo, open-stand-up, defer), participants, outcome, and rationale.

## Success Criteria

### Measurable Outcomes

- **SC-001**: 100% of decisions evaluated by the runtime receive a significance score and are routed to the correct band based on their composite score and hard-trigger classification.

- **SC-002**: Zero decisions at medium, high, or hard-trigger bands proceed without explicit human action (no silent approvals).

- **SC-003**: All hard-trigger class decisions route to hard-gate behavior regardless of numeric score, verified across all five hard-trigger classes.

- **SC-004**: Timeout-expired events fire within 1 second of the configured timeout window for medium-band and high-band decisions.

- **SC-005**: Escalation on timeout correctly targets mission owner (medium band) or mission owner + accountable/consulted actors (high band and hard-trigger), verified against the RACI snapshot.

- **SC-006**: Custom band cutoffs and timeout values applied via policy override default behavior deterministically, with validation rejecting invalid configurations.

- **SC-007**: Complete audit trail captured for every decision: dimension scores, composite score, routing band, hard-trigger classes, timeout configuration, escalation events, and resolution outcome.

- **SC-008**: All significance evaluation logic is deterministic — identical inputs produce identical outputs across 5+ independent runs with bit-for-bit identical audit payloads.

## Assumptions

- The existing `MissionPolicySnapshot.extras` dict is the extension point for significance threshold and timeout policy configuration; no new top-level policy fields are added to the snapshot model.
- Dimension scores are provided as part of the decision declaration in the mission template or at decision-raise time; the runtime does not infer or calculate dimension scores from mission content.
- The runtime caller (host process) is responsible for wall-clock timeout tracking and notifying the runtime when a timeout expires; the runtime defines the policy and emits events but does not run internal timers.
- Stand-up suggestions in medium-band soft gates are informational (recommended participants list); the runtime does not orchestrate stand-up meetings or video calls.
- The "defer" action in medium-band decisions does not reset the timeout clock by default; it records the deferral and the timeout continues counting from the original start.

## Scope Boundaries

### In Scope
- Six fixed significance dimensions with 0–3 scoring
- Composite score computation (0–18) and three-band routing
- Five fixed hard-trigger classes with override behavior
- Timeout policy (configurable default, per-decision editable)
- Timeout-expired event emission and escalation routing
- Medium-band soft gate with decide-solo/open-stand-up/defer actions
- High-band hard gate with approve/reject actions
- Configurable band cutoffs and timeout via policy settings
- Audit trail capture for all significance-related decisions
- Integration with existing RACI bindings for escalation targeting

### Out of Scope
- Per-mission custom significance dimensions (V1 uses fixed set)
- Custom hard-trigger class definitions
- Wall-clock timer implementation (caller responsibility)
- Stand-up meeting orchestration or video call integration
- LLM-driven significance scoring or override
- UI/dashboard for significance visualization
- Historical significance trend analysis or reporting
- Notification delivery mechanisms (email, Slack, etc.) — the runtime emits events; delivery is a consumer concern

## Dependencies

- **Feature 001** (Audit Primitive & Decision Checkpoint): Provides AuditConfig, AuditStep, and decision checkpoint infrastructure that significance routing extends.
- **Feature 003** (RACI Inference & Override): Provides ResolvedRACIBinding and RACI snapshot used for escalation targeting on timeout.
- **MissionPolicySnapshot**: Existing policy model extended via `extras` dict for threshold cutoffs and timeout configuration.
- **spec-kitty-events**: Event payload definitions for timeout-expired and significance-related events.

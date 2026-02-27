---
work_package_id: WP03
title: Event Payloads & Decision Models
lane: "for_review"
dependencies: [WP02]
base_branch: main
base_commit: c94e977540297d57ab1133d99ae3f68046a95e52
created_at: '2026-02-27T21:20:48.217361+00:00'
subtasks:
- T011
- T012
- T013
- T014
- T015
- T016
phase: Phase 1 - Communication Layer
assignee: ''
agent: claude-opus
shell_pid: '18308'
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-02-27T20:43:12Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
requirement_refs:
- FR-005
- FR-006
- FR-009
- FR-011
- FR-018
- FR-019
---

# Work Package Prompt: WP03 – Event Payloads & Decision Models

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: Update `review_status: acknowledged` when you begin addressing feedback.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Markdown Formatting
Wrap HTML/XML tags in backticks: `` `<div>` ``, `` `<script>` ``
Use language identifiers in code blocks: ````python`, ````bash`

---

## Implementation Command

Depends on WP02:

```bash
spec-kitty implement WP03 --base WP02
```

---

## Objectives & Success Criteria

- Implement `SignificanceEvaluatedPayload` and `TimeoutExpiredPayload` event models in `significance.py`
- Implement `SoftGateDecision` model for medium-band decision capture (decide_solo, open_stand_up, defer)
- Implement `DimensionScoreOverride` model for runtime score override audit trail
- Extend `RuntimeEventEmitter` protocol in `events.py` with 2 new emit methods
- Update `NullEmitter` with no-op implementations for the new methods
- All payload field names align with `contracts/` YAML definitions for future spec-kitty-events migration

## Context & Constraints

- **Spec reference**: FR-005, FR-006, FR-009, FR-011, FR-018, FR-019
- **Data model**: SignificanceEvaluatedPayload, TimeoutExpiredPayload, SoftGateDecision, DimensionScoreOverride in `data-model.md`
- **Contracts**: `contracts/significance-evaluation.yaml`, `contracts/timeout-expired-event.yaml`, `contracts/soft-gate-decision.yaml`
- **Research**: R-002 (event payload ownership — local definition, aligned with anticipated spec-kitty-events v2.4.0)
- **Engineering Decision ED-2**: Payloads defined locally in significance.py, NOT imported from spec-kitty-events
- **Pattern to follow**: Study `events.py` for RuntimeEventEmitter protocol and NullEmitter implementation

## Subtasks & Detailed Guidance

### Subtask T011 – Implement SignificanceEvaluatedPayload

- **Purpose**: Event payload emitted when a decision's significance is scored and routed. Persisted in JSONL event log.

- **Steps**:
  1. Add to `significance.py`:
     ```python
     class SignificanceEvaluatedPayload(BaseModel):
         model_config = ConfigDict(frozen=True, extra="forbid")

         run_id: str = Field(..., min_length=1)
         decision_id: str = Field(..., min_length=1)
         step_id: str = Field(..., min_length=1)
         significance_score: dict  # Serialized SignificanceScore
         hard_trigger_classes: tuple[str, ...] = Field(default_factory=tuple)
         effective_band: Literal["low", "medium", "high"]
         actor: RACIRoleBinding  # System actor (service/runtime)
     ```
  2. Note: `significance_score` is a dict (serialized form) rather than SignificanceScore model — this matches the event log serialization pattern used by JsonlEventLog
  3. `actor` uses `RACIRoleBinding` from `schema.py` (same type used for RACI actors)

- **Files**: `src/spec_kitty_runtime/significance.py`
- **Parallel?**: Yes — independent of T012–T014
- **Notes**: Field names must match `contracts/significance-evaluation.yaml`. Import `RACIRoleBinding` from `schema.py`.

### Subtask T012 – Implement TimeoutExpiredPayload

- **Purpose**: Event payload emitted when a decision exceeds its configured timeout window.

- **Steps**:
  1. Add to `significance.py`:
     ```python
     class TimeoutExpiredPayload(BaseModel):
         model_config = ConfigDict(frozen=True, extra="forbid")

         run_id: str = Field(..., min_length=1)
         decision_id: str = Field(..., min_length=1)
         step_id: str = Field(..., min_length=1)
         significance_score: dict  # Serialized SignificanceScore
         effective_band: Literal["medium", "high"]  # Never "low" — low auto-proceeds
         timeout_configured_seconds: int = Field(..., gt=0)
         escalation_targets: tuple[RACIRoleBinding, ...] = Field(default_factory=tuple)
         raci_snapshot: dict  # Serialized ResolvedRACIBinding
         actor: RACIRoleBinding  # System actor (service/runtime)
     ```
  2. Note: `effective_band` excludes "low" — low-band decisions auto-proceed and never timeout
  3. `raci_snapshot` is serialized ResolvedRACIBinding (dict form) for the event log

- **Files**: `src/spec_kitty_runtime/significance.py`
- **Parallel?**: Yes — independent of T011, T013, T014
- **Notes**: Match field names to `contracts/timeout-expired-event.yaml` exactly

### Subtask T013 – Implement SoftGateDecision Model

- **Purpose**: Captures the responsible human's action on a medium-band decision (FR-005, FR-006).

- **Steps**:
  1. Add to `significance.py`:
     ```python
     class SoftGateDecision(BaseModel):
         model_config = ConfigDict(frozen=True, extra="forbid")

         decision_id: str = Field(..., min_length=1)
         action: Literal["decide_solo", "open_stand_up", "defer"]
         actor: RACIRoleBinding  # Must be human
         timestamp: datetime  # UTC
         significance_score: SignificanceScore
         participants: tuple[RACIRoleBinding, ...] = Field(default_factory=tuple)
         outcome: str | None = None  # approve/reject/defer — None until resolved
         rationale: str | None = None

         @model_validator(mode="after")
         def _validate_actor_human(self) -> SoftGateDecision:
             if self.actor.actor_type != "human":
                 raise ValueError(f"SoftGateDecision actor must be human, got {self.actor.actor_type}")
             return self
     ```
  2. Import `datetime` from standard library
  3. Validator enforces FR-018: only humans can make decisions

- **Files**: `src/spec_kitty_runtime/significance.py`
- **Parallel?**: Yes — independent of T011, T012, T014
- **Notes**: Match contract shape from `contracts/soft-gate-decision.yaml`. The `outcome` starts as None and is set when the gate resolves.

### Subtask T014 – Implement DimensionScoreOverride Model

- **Purpose**: Audit record for runtime score overrides — the secondary scoring path where a human adjusts template-declared scores.

- **Steps**:
  1. Add to `significance.py`:
     ```python
     class DimensionScoreOverride(BaseModel):
         model_config = ConfigDict(frozen=True, extra="forbid")

         decision_id: str = Field(..., min_length=1)
         overridden_by: RACIRoleBinding  # Must be human (FR-018)
         override_reason: str = Field(..., min_length=1)  # Mandatory justification
         original_scores: dict[str, int]  # dimension_name → before value
         new_scores: dict[str, int]  # dimension_name → after value
         override_timestamp: datetime  # UTC

         @model_validator(mode="after")
         def _validate_override(self) -> DimensionScoreOverride:
             if self.overridden_by.actor_type != "human":
                 raise ValueError(f"Overrides must be by human actors, got {self.overridden_by.actor_type}")
             # Validate that overridden dimensions exist in DIMENSION_NAMES
             for name in {**self.original_scores, **self.new_scores}:
                 if name not in DIMENSION_NAMES:
                     raise ValueError(f"Unknown dimension: {name}")
             return self
     ```
  2. Both `original_scores` and `new_scores` use dimension name keys
  3. Only changed dimensions need to appear (sparse dict, not full 6)

- **Files**: `src/spec_kitty_runtime/significance.py`
- **Parallel?**: Yes — independent of T011–T013
- **Notes**: Per research R-004 and ED-4: override is the secondary path. Template-declared scores are primary.

### Subtask T015 – Extend RuntimeEventEmitter Protocol

- **Purpose**: Add emission methods for the two new significance event types.

- **Steps**:
  1. In `src/spec_kitty_runtime/events.py`, add to the `RuntimeEventEmitter` protocol:
     ```python
     def emit_significance_evaluated(self, payload: SignificanceEvaluatedPayload) -> None: ...
     def emit_decision_timeout_expired(self, payload: TimeoutExpiredPayload) -> None: ...
     ```
  2. Import `SignificanceEvaluatedPayload` and `TimeoutExpiredPayload` from `significance`:
     ```python
     from spec_kitty_runtime.significance import (
         SignificanceEvaluatedPayload,
         TimeoutExpiredPayload,
     )
     ```
  3. Place the new methods after the existing `emit_mission_run_completed` method

- **Files**: `src/spec_kitty_runtime/events.py`
- **Parallel?**: Yes — can develop alongside model subtasks
- **Notes**: Follow the existing protocol method pattern (single payload parameter, returns None)

### Subtask T016 – Update NullEmitter with No-Op Implementations

- **Purpose**: Ensure the default NullEmitter satisfies the extended protocol.

- **Steps**:
  1. In `src/spec_kitty_runtime/events.py`, add to `NullEmitter`:
     ```python
     def emit_significance_evaluated(self, payload: SignificanceEvaluatedPayload) -> None:
         pass

     def emit_decision_timeout_expired(self, payload: TimeoutExpiredPayload) -> None:
         pass
     ```
  2. Verify NullEmitter still satisfies the `RuntimeEventEmitter` protocol

- **Files**: `src/spec_kitty_runtime/events.py`
- **Parallel?**: Yes — but logically pairs with T015
- **Notes**: Existing NullEmitter uses `pass` for all methods. Follow the same pattern.

## Risks & Mitigations

- **Payload shape drift**: Field names MUST match contract YAML exactly. Cross-reference during implementation.
- **Import from schema.py**: Using `RACIRoleBinding` from `schema.py` is safe — it's a stable type. Avoid importing unstable engine types.
- **Circular imports**: `events.py` imports from `significance.py`, `significance.py` imports from `schema.py`. Verify no circular dependency chain.
- **FR-018 enforcement**: SoftGateDecision and DimensionScoreOverride validators MUST reject non-human actors. This is the P0 invariant.

## Review Guidance

- Verify all payload field names match their respective contract YAML files
- Verify SoftGateDecision validates: actor must be human, action must be one of the three literals
- Verify DimensionScoreOverride validates: overridden_by must be human, override_reason non-empty, dimension names valid
- Verify TimeoutExpiredPayload excludes "low" from effective_band (low band never times out)
- Verify RuntimeEventEmitter protocol has exactly 2 new methods with correct signatures
- Verify NullEmitter has matching no-op implementations

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

- 2026-02-27T20:43:12Z – system – lane=planned – Prompt created.
- 2026-02-27T21:20:48Z – claude-opus – shell_pid=18308 – lane=doing – Assigned agent via workflow command
- 2026-02-27T21:25:02Z – claude-opus – shell_pid=18308 – lane=for_review – Ready for review: 4 payload/decision models (T011-T014), protocol extension (T015-T016), 46 tests, 478 total passing

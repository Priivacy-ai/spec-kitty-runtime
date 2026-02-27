---
work_package_id: WP05
title: AuditStep Extension & Engine Integration
lane: "doing"
dependencies: [WP04]
base_branch: main
base_commit: 9c618e3f6de48ddb8eca1dcdcadf470716b4f711
created_at: '2026-02-27T21:56:39.191608+00:00'
subtasks:
- T021
- T022
- T023
- T024
- T025
phase: Phase 2 - Integration
assignee: ''
agent: "claude-opus-reviewer"
shell_pid: "40129"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-02-27T20:43:12Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
requirement_refs:
- FR-004
- FR-005
- FR-007
- FR-008
- FR-017
- FR-018
---

# Work Package Prompt: WP05 – AuditStep Extension & Engine Integration

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

Depends on WP04:

```bash
spec-kitty implement WP05 --base WP04
```

---

## Objectives & Success Criteria

- Extend `AuditStep` in `schema.py` with an optional `significance` block
- Integrate significance evaluation into the `next_step()` flow in `engine.py`
- Integrate significance routing into `provide_decision_answer()` flow
- Persist significance data in `MissionRunSnapshot.decisions` under `"significance:<decision_id>"`
- Update `__init__.py` to re-export all significance public API types and functions
- **Backward compatibility**: Missions without significance blocks work exactly as before

## Context & Constraints

- **Spec reference**: All FRs — this WP wires everything together
- **Research**: R-005 (integration pattern — extend AuditStep, not new step type)
- **Engineering Decision ED-1**: significance.py is the model+logic module, engine.py does integration
- **Backward compatibility (R-005)**: AuditStep without significance → existing behavior unchanged
- **Key engine integration points**:
  - `next_step()` at line ~286-310: after RACI resolution, evaluate significance
  - `provide_decision_answer()` at line ~366+: check significance routing before allowing answer
- **Pattern**: Significance evaluation extends the existing `enforcement="blocking"` behavior

## Subtasks & Detailed Guidance

### Subtask T021 – Extend AuditStep Schema with Significance Block

- **Purpose**: Add an optional `significance` block to `AuditStep` that declares dimension scores and hard-trigger classes.

- **Steps**:
  1. Create a new `SignificanceBlock` frozen model in `schema.py`:
     ```python
     class SignificanceBlock(BaseModel):
         model_config = ConfigDict(frozen=True, extra="forbid")

         dimensions: dict[str, int]  # dimension_name → score (0-3)
         hard_triggers: list[str] = Field(default_factory=list)  # hard-trigger class IDs

         @model_validator(mode="after")
         def _validate_dimensions(self) -> SignificanceBlock:
             from spec_kitty_runtime.significance import validate_dimension_scores, HARD_TRIGGER_REGISTRY
             validate_dimension_scores(self.dimensions)
             for trigger_id in self.hard_triggers:
                 if trigger_id not in HARD_TRIGGER_REGISTRY:
                     raise ValueError(f"Unknown hard-trigger class: {trigger_id}")
             return self
     ```
  2. Add to `AuditStep`:
     ```python
     class AuditStep(BaseModel):
         # ... existing fields ...
         significance: SignificanceBlock | None = None  # NEW: optional significance declaration
     ```
  3. The field is optional with default None — no breaking change for existing missions

- **Files**: `src/spec_kitty_runtime/schema.py`
- **Parallel?**: No — schema change that other subtasks depend on
- **Notes**:
  - Import from significance is done inside the validator to avoid circular imports at module level
  - The dimensions dict maps dimension name strings to integer scores — matches YAML template format from quickstart.md
  - hard_triggers is a list of class_id strings matching HARD_TRIGGER_REGISTRY keys

### Subtask T022 – Integrate Significance Evaluation into next_step()

- **Purpose**: When the engine reaches an audit step with a significance block, evaluate significance and adjust gate behavior.

- **Steps**:
  1. In `engine.py`, after RACI resolution (around line 286-310), add significance evaluation:
     ```python
     # After RACI resolution for audit steps...
     if isinstance(step_obj, AuditStep) and step_obj.significance is not None:
         significance_score = evaluate_significance(
             dimension_scores=step_obj.significance.dimensions,
             hard_trigger_classes=step_obj.significance.hard_triggers,
             band_cutoffs=parse_band_cutoffs_from_policy(effective_policy),
         )
         # Persist significance score to decisions dict
         updated_decisions[f"significance:audit:{step_obj.id}"] = significance_score.model_dump()

         # Emit significance evaluated event
         sig_payload = SignificanceEvaluatedPayload(
             run_id=snapshot.run_id,
             decision_id=f"audit:{step_obj.id}",
             step_id=step_obj.id,
             significance_score=significance_score.model_dump(),
             hard_trigger_classes=tuple(ht.class_id for ht in significance_score.hard_trigger_classes),
             effective_band=significance_score.effective_band.name,
             actor=RACIRoleBinding(actor_type="service", actor_id="runtime"),
         )
         emitter_instance.emit_significance_evaluated(sig_payload)
     ```
  2. Adjust gate behavior based on effective_band:
     ```python
     # LOW band: auto-proceed (do not raise a decision gate)
     if significance_score.effective_band.name == "low":
         # Add to completed_steps, emit auto-completed event
         # ... (skip the decision_required branch)

     # MEDIUM band: raise decision with soft-gate options
     elif significance_score.effective_band.name == "medium":
         # decision_required with options: ["decide_solo", "open_stand_up", "defer"]
         decision = NextDecision(
             kind="decision_required",
             step_id=step_obj.id,
             decision_id=f"audit:{step_obj.id}",
             prompt=step_obj.title,
             options=["decide_solo", "open_stand_up", "defer"],
         )

     # HIGH band (or hard-trigger): raise hard gate
     else:  # "high"
         # decision_required with options: ["approve", "reject"]
         decision = NextDecision(
             kind="decision_required",
             step_id=step_obj.id,
             decision_id=f"audit:{step_obj.id}",
             prompt=step_obj.title,
             options=["approve", "reject"],
         )
     ```
  3. Import new functions:
     ```python
     from spec_kitty_runtime.significance import (
         evaluate_significance,
         parse_band_cutoffs_from_policy,
         SignificanceEvaluatedPayload,
     )
     ```

- **Files**: `src/spec_kitty_runtime/engine.py`
- **Parallel?**: No — depends on T021 (needs SignificanceBlock on AuditStep)
- **Notes**:
  - For LOW band: the audit step auto-proceeds (like advisory enforcement) — no human gate. This is the key differentiator from the current behavior where all blocking audits require human action.
  - For MEDIUM band: the options change from ["approve", "reject"] to ["decide_solo", "open_stand_up", "defer"]
  - For HIGH band: same as current blocking behavior (approve/reject)
  - AuditStep WITHOUT significance block: existing behavior unchanged (enforcement determines routing)
  - Be careful with the snapshot update — use the existing pattern for building updated decisions dict

### Subtask T023 – Integrate Significance Routing into provide_decision_answer()

- **Purpose**: Validate that the answer matches the expected options for the decision's significance band.

- **Steps**:
  1. In `provide_decision_answer()`, after extracting the audit step, check for significance:
     ```python
     # If this decision has a significance evaluation, validate the answer
     significance_key = f"significance:{decision_id}"
     if significance_key in snapshot.decisions:
         sig_data = snapshot.decisions[significance_key]
         effective_band = sig_data.get("effective_band", {}).get("name")

         if effective_band == "medium":
             valid_answers = {"decide_solo", "open_stand_up", "defer"}
             if answer not in valid_answers:
                 raise MissionRuntimeError(
                     f"Medium-band decision requires one of {sorted(valid_answers)}, got: {answer!r}"
                 )
         elif effective_band == "high":
             valid_answers = {"approve", "reject"}
             if answer not in valid_answers:
                 raise MissionRuntimeError(
                     f"High-band decision requires one of {sorted(valid_answers)}, got: {answer!r}"
                 )
     ```
  2. Handle medium-band answers:
     - `"decide_solo"` → gate clears, add to completed_steps (like approve)
     - `"open_stand_up"` → record stand-up participants, gate stays open until final decision
     - `"defer"` → record deferral with reason, timeout continues
  3. Handle high-band answers (same as existing):
     - `"approve"` → add to completed_steps
     - `"reject"` → set blocked_reason
  4. Persist `SoftGateDecision` for medium-band answers:
     ```python
     from spec_kitty_runtime.significance import SoftGateDecision

     if effective_band == "medium":
         soft_gate = SoftGateDecision(
             decision_id=decision_id,
             action=answer,
             actor=RACIRoleBinding(actor_type=actor.actor_type, actor_id=actor.actor_id),
             timestamp=datetime.now(timezone.utc),
             significance_score=reconstructed_score,
             participants=tuple(),  # Populated by caller for open_stand_up
             outcome=answer if answer == "decide_solo" else None,
         )
         updated_decisions[f"soft_gate:{decision_id}"] = soft_gate.model_dump()
     ```

- **Files**: `src/spec_kitty_runtime/engine.py`
- **Parallel?**: No — depends on T022 (significance evaluation must happen first in flow)
- **Notes**:
  - The `decide_solo` action immediately clears the gate (like approve)
  - The `open_stand_up` action requires a follow-up decision after the stand-up (implementable as a re-raised decision)
  - The `defer` action records the deferral but does NOT clear the gate or reset the timeout
  - FR-018: Only human actors can provide answers — the existing authority check in `provide_decision_answer()` already enforces this

### Subtask T024 – Persist Significance Data in MissionRunSnapshot.decisions

- **Purpose**: Ensure the complete significance evaluation is captured in the audit trail (FR-019, SC-007).

- **Steps**:
  1. Verify that T022 persists `SignificanceScore.model_dump()` to `decisions[f"significance:{decision_id}"]`
  2. Verify that T023 persists `SoftGateDecision.model_dump()` to `decisions[f"soft_gate:{decision_id}"]`
  3. Verify that T019 (WP04) persists `TimeoutExpiredPayload.model_dump()` to `decisions[f"timeout:{decision_id}"]`
  4. Ensure all persisted dicts use the same serialization approach: `model_dump()` which produces JSON-serializable dicts
  5. Add the significance-related data to the JSONL event log as well (via emitter methods)
  6. Decision key convention:
     ```
     decisions["significance:audit:{step_id}"]  → SignificanceScore
     decisions["soft_gate:audit:{step_id}"]     → SoftGateDecision (medium band)
     decisions["timeout:audit:{step_id}"]       → TimeoutExpiredPayload
     decisions["raci:{step_id}"]                → ResolvedRACIBinding (existing)
     ```

- **Files**: `src/spec_kitty_runtime/engine.py`
- **Parallel?**: No — verification of T022/T023 work
- **Notes**: The decision key format uses colons as separators, matching the existing `"raci:{step_id}"` convention. All payloads are serialized via `model_dump()` to produce JSON-compatible dicts.

### Subtask T025 – Update __init__.py to Re-Export Significance Public API

- **Purpose**: Make significance types and functions discoverable via the package's public API.

- **Steps**:
  1. In `src/spec_kitty_runtime/__init__.py`, add imports and exports:
     ```python
     from spec_kitty_runtime.significance import (
         # Models
         SignificanceDimension,
         SignificanceScore,
         RoutingBand,
         HardTriggerClass,
         TimeoutPolicy,
         SoftGateDecision,
         DimensionScoreOverride,
         TimeoutEscalationResult,
         SignificanceEvaluatedPayload,
         TimeoutExpiredPayload,
         # Functions
         evaluate_significance,
         compute_escalation_targets,
         validate_band_cutoffs,
         validate_dimension_scores,
         parse_band_cutoffs_from_policy,
         parse_timeout_from_policy,
         resolve_hard_triggers,
         # Constants
         DIMENSION_NAMES,
         HARD_TRIGGER_REGISTRY,
         DEFAULT_BANDS,
     )
     ```
  2. Also export `notify_decision_timeout` from engine:
     ```python
     from spec_kitty_runtime.engine import notify_decision_timeout
     ```
  3. Export `SignificanceBlock` from schema:
     ```python
     from spec_kitty_runtime.schema import SignificanceBlock
     ```
  4. Verify all exports are accessible: `from spec_kitty_runtime import evaluate_significance`

- **Files**: `src/spec_kitty_runtime/__init__.py`
- **Parallel?**: Yes — can be done early but finalized after all other subtasks
- **Notes**: Follow the existing export pattern in `__init__.py` (grouped by module with comments)

## Risks & Mitigations

- **Backward compatibility regression**: The most critical risk. Test with an existing mission YAML that has NO significance block — it must work identically to before this feature.
- **Engine complexity creep**: Keep the significance integration in engine.py minimal. The evaluation logic lives in significance.py. Engine.py only orchestrates: evaluate → persist → adjust gate.
- **Circular imports**: schema.py imports from significance.py inside the validator (lazy import). This avoids module-level circular dependency.
- **NextDecision options change**: Medium-band decisions change the options from ["approve", "reject"] to ["decide_solo", "open_stand_up", "defer"]. Ensure the consumer (caller) handles these new option values.

## Review Guidance

- **Backward compatibility test**: An AuditStep without `significance` field must produce identical behavior to the current codebase
- **Low-band auto-proceed**: Verify that a low-band decision auto-proceeds without human gate
- **Medium-band options**: Verify decision options are ["decide_solo", "open_stand_up", "defer"]
- **High-band options**: Verify decision options remain ["approve", "reject"]
- **Persistence**: Verify all three significance-related keys are persisted in decisions dict
- **Event emission**: Verify `emit_significance_evaluated()` is called during evaluation
- **Public API**: Verify all types and functions listed in T025 are importable from `spec_kitty_runtime`

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

- 2026-02-27T20:43:12Z – system – lane=planned – Prompt created.
- 2026-02-27T21:56:39Z – claude-opus – shell_pid=34730 – lane=doing – Assigned agent via workflow command
- 2026-02-27T22:07:49Z – claude-opus – shell_pid=34730 – lane=for_review – Ready for review: All 5 subtasks implemented and tested. 44 new tests, 552 total passing. SignificanceBlock schema, next_step significance evaluation (LOW auto-proceed, MEDIUM soft-gate, HIGH hard-gate), provide_decision_answer significance routing, persistence verification, and public API re-exports.
- 2026-02-27T22:08:38Z – claude-opus-reviewer – shell_pid=40129 – lane=doing – Started review via workflow command

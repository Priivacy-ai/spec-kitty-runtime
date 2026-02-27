---
work_package_id: WP07
title: Integration Tests, Timeout Tests & Edge Cases
lane: "for_review"
dependencies: [WP05, WP06]
base_branch: main
base_commit: 51b0204963f0731497e0c74c41af917779ff47bf
created_at: '2026-02-27T22:22:08.056901+00:00'
subtasks:
- T032
- T033
- T034
- T035
- T036
- T037
phase: Phase 3 - Comprehensive Validation
assignee: ''
agent: claude-opus
shell_pid: '47123'
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-02-27T20:43:12Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
requirement_refs:
- FR-010
- FR-011
- FR-012
- FR-013
- FR-014
- FR-016
- FR-017
- FR-019
---

# Work Package Prompt: WP07 – Integration Tests, Timeout Tests & Edge Cases

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

Depends on WP05 and WP06 (both must be complete):

```bash
spec-kitty implement WP07 --base WP05
```

Note: WP06 (test fixtures) must also be merged before implementing this WP.

---

## Objectives & Success Criteria

- Write timeout policy & escalation target computation tests in `tests/test_significance_timeout.py`
- Write timeout event emission and JSONL log tests
- Write full engine flow integration tests in `tests/test_significance_integration.py`
- Write audit trail capture verification tests
- Write determinism verification tests — 5+ independent runs with bit-for-bit identical output (SC-008)
- Write edge case tests covering all spec edge cases
- Validate quickstart.md code examples compile and run against implemented API
- Target: ~20+ new tests across 2 test files, zero flaky

## Context & Constraints

- **Spec reference**: SC-004 through SC-008, all edge cases listed in spec
- **Test patterns**: Follow existing patterns from `tests/test_audit_engine.py` for integration tests
- **Fixtures**: Use the 4 YAML fixtures created in WP06
- **Determinism requirement (SC-008)**: Identical inputs → identical outputs across 5+ independent evaluations
- **Engine integration testing pattern**: `start_mission_run()` → `next_step()` → `provide_decision_answer()` → verify state
- **NFR-002**: Timeout accuracy ±1s (test with simulated time, not real wall-clock)

## Subtasks & Detailed Guidance

### Subtask T032 – Write Timeout Policy & Escalation Target Tests

- **Purpose**: Verify TimeoutPolicy validation and compute_escalation_targets() correctness (FR-011 through FR-013).

- **Steps**:
  1. Create `tests/test_significance_timeout.py`:
     ```python
     import pytest
     from spec_kitty_runtime.significance import (
         TimeoutPolicy,
         compute_escalation_targets,
         TimeoutEscalationResult,
         parse_timeout_from_policy,
     )
     from spec_kitty_runtime.schema import (
         MissionPolicySnapshot,
         RACIRoleBinding,
         ResolvedRACIBinding,
     )
     ```
  2. Test TimeoutPolicy:
     ```python
     def test_default_timeout():
         policy = TimeoutPolicy()
         assert policy.default_timeout_seconds == 600
         assert policy.effective_timeout_seconds == 600

     def test_custom_timeout():
         policy = TimeoutPolicy(default_timeout_seconds=1200)
         assert policy.effective_timeout_seconds == 1200

     def test_per_decision_override():
         policy = TimeoutPolicy(default_timeout_seconds=600, per_decision_timeout_seconds=300)
         assert policy.effective_timeout_seconds == 300

     def test_zero_timeout_rejected():
         with pytest.raises(ValueError):
             TimeoutPolicy(default_timeout_seconds=0)

     def test_negative_timeout_rejected():
         with pytest.raises(ValueError):
             TimeoutPolicy(default_timeout_seconds=-1)

     def test_zero_per_decision_rejected():
         with pytest.raises(ValueError):
             TimeoutPolicy(per_decision_timeout_seconds=0)
     ```
  3. Test compute_escalation_targets:
     ```python
     def _make_raci(consulted_count=0):
         owner = RACIRoleBinding(actor_type="human", actor_id="owner-001")
         consulted = [
             RACIRoleBinding(actor_type="human", actor_id=f"consulted-{i}")
             for i in range(consulted_count)
         ]
         return ResolvedRACIBinding(
             step_id="test-step",
             responsible=RACIRoleBinding(actor_type="human", actor_id="responsible-001"),
             accountable=owner,
             consulted=consulted,
             informed=[],
             source="inferred",
             inferred_rule="audit_blocking",
         )

     def test_medium_escalation_owner_only():
         raci = _make_raci(consulted_count=0)
         targets = compute_escalation_targets(raci, "medium")
         assert len(targets) == 1
         assert targets[0].actor_id == "owner-001"

     def test_high_escalation_owner_plus_consulted():
         raci = _make_raci(consulted_count=2)
         targets = compute_escalation_targets(raci, "high")
         assert len(targets) == 3  # owner + 2 consulted
         assert targets[0].actor_id == "owner-001"

     def test_high_escalation_empty_consulted():
         raci = _make_raci(consulted_count=0)
         targets = compute_escalation_targets(raci, "high")
         assert len(targets) == 1  # owner only, no error
         assert targets[0].actor_id == "owner-001"
     ```
  4. Test parse_timeout_from_policy:
     ```python
     def test_parse_timeout_default():
         policy = MissionPolicySnapshot()
         assert parse_timeout_from_policy(policy) == 600

     def test_parse_timeout_custom():
         policy = MissionPolicySnapshot(extras={"significance_default_timeout_seconds": 1200})
         assert parse_timeout_from_policy(policy) == 1200

     def test_parse_timeout_invalid():
         policy = MissionPolicySnapshot(extras={"significance_default_timeout_seconds": -1})
         with pytest.raises(ValueError):
             parse_timeout_from_policy(policy)
     ```

- **Files**: `tests/test_significance_timeout.py` (new file)
- **Parallel?**: Yes — independent of T033
- **Notes**: The escalation test for "responsible == mission owner" (US3.2): medium band, the target is still the owner. No target change, but the event is still emitted.

### Subtask T033 – Write Timeout Event Emission Tests

- **Purpose**: Verify that timeout events are emitted via the emitter protocol and persisted to JSONL log.

- **Steps**:
  1. Create a test-specific emitter that captures emitted events:
     ```python
     class CapturingEmitter:
         """Test emitter that captures all emitted events."""
         def __init__(self):
             self.significance_evaluated = []
             self.timeout_expired = []
             # ... all other emit methods as no-ops

         def emit_significance_evaluated(self, payload):
             self.significance_evaluated.append(payload)

         def emit_decision_timeout_expired(self, payload):
             self.timeout_expired.append(payload)

         # ... no-op implementations for all other protocol methods
     ```
  2. Test timeout event emission:
     ```python
     def test_timeout_event_emitted(tmp_path):
         # Set up a run with a significance-evaluated medium-band decision
         # ... (use start_mission_run + next_step to get to a pending decision)

         emitter = CapturingEmitter()
         result = notify_decision_timeout(
             run_ref=run_ref,
             decision_id="audit:review-step",
             actor=RACIRoleBinding(actor_type="service", actor_id="runtime"),
             emitter=emitter,
         )

         assert len(emitter.timeout_expired) == 1
         payload = emitter.timeout_expired[0]
         assert payload.decision_id == "audit:review-step"
         assert payload.effective_band in ("medium", "high")
         assert len(payload.escalation_targets) > 0
     ```
  3. Test timeout event persisted to JSONL log:
     ```python
     def test_timeout_persisted_to_event_log(tmp_path):
         # Use JsonlEventLog + set up run + trigger timeout
         log = JsonlEventLog(tmp_path / "events.jsonl")
         # ... verify event appears in log.read_all()
     ```
  4. Test timeout event persisted to decisions dict:
     ```python
     def test_timeout_persisted_to_decisions(tmp_path):
         # ... trigger timeout, reload snapshot
         snapshot = _load_snapshot(run_ref)
         assert f"timeout:audit:review-step" in snapshot.decisions
     ```

- **Files**: `tests/test_significance_timeout.py`
- **Parallel?**: Yes — can be written alongside T032
- **Notes**: The CapturingEmitter pattern is common in the existing test suite. Follow the test setup helpers from `test_audit_engine.py` for creating runs and advancing to audit steps.

### Subtask T034 – Write Engine Flow Integration Tests

- **Purpose**: Test the complete engine flow with significance-enabled mission templates (start → next_step → evaluate significance → decide → complete).

- **Steps**:
  1. Create `tests/test_significance_integration.py`:
     ```python
     import pytest
     from pathlib import Path
     from spec_kitty_runtime.engine import start_mission_run, next_step, provide_decision_answer
     from spec_kitty_runtime.schema import MissionPolicySnapshot, MissionRunRef
     ```
  2. Test low-band auto-proceed flow:
     ```python
     def test_low_band_auto_proceeds(tmp_path):
         """Low significance decisions auto-proceed without a human gate (FR-004)."""
         # Load mission_significance_low.yaml fixture
         # Start run, advance to audit step
         # next_step() should auto-complete the audit step (no decision_required)
         # Verify step is in completed_steps
     ```
  3. Test medium-band soft gate flow:
     ```python
     def test_medium_band_soft_gate(tmp_path):
         """Medium band raises soft gate with decide_solo/open_stand_up/defer options (FR-005)."""
         # Load mission_significance_medium.yaml fixture
         # Start run, advance to audit step
         # next_step() returns decision_required with medium-band options
         decision = next_step(run_ref, agent_id="test")
         assert decision.kind == "decision_required"
         # options should include decide_solo, open_stand_up, defer
     ```
  4. Test medium-band decide_solo clears gate:
     ```python
     def test_medium_decide_solo_clears_gate(tmp_path):
         # ... advance to medium-band decision
         provide_decision_answer(run_ref, decision_id, "decide_solo", actor)
         # Verify gate cleared, step in completed_steps
     ```
  5. Test high-band hard gate flow:
     ```python
     def test_high_band_hard_gate(tmp_path):
         """High band raises hard gate with approve/reject options (FR-007)."""
         # Load mission_significance_high.yaml fixture
         # Verify decision_required with approve/reject options
     ```
  6. Test hard-trigger override flow:
     ```python
     def test_hard_trigger_overrides_to_hard_gate(tmp_path):
         """Hard trigger forces hard gate even with low numeric score (FR-008, US2)."""
         # Load mission_hard_trigger.yaml fixture (score=1, trigger=production_data_destructive)
         # Verify effective_band=high despite low numeric score
         # Verify decision_required with approve/reject options
     ```
  7. Test backward compatibility:
     ```python
     def test_audit_without_significance_unchanged(tmp_path):
         """AuditStep without significance block works exactly as before."""
         # Load existing audit fixture (no significance block)
         # Verify behavior identical to pre-feature behavior
     ```

- **Files**: `tests/test_significance_integration.py` (new file)
- **Parallel?**: Yes — independent of timeout tests
- **Notes**:
  - Use tmp_path fixture for isolated run directories
  - Follow the setup pattern from `test_audit_engine.py` (helper functions for run setup)
  - Each test exercises the full engine flow end-to-end
  - Backward compatibility test is critical — load an existing fixture without significance

### Subtask T035 – Write Audit Trail Capture Tests

- **Purpose**: Verify that every significance decision captures the complete audit trail (FR-019, SC-007).

- **Steps**:
  1. Test significance score in decisions dict:
     ```python
     def test_significance_score_in_audit_trail(tmp_path):
         # Set up run with significance-enabled audit step
         # Advance to audit step
         snapshot = _load_snapshot(run_ref)
         sig_key = "significance:audit:review-step"
         assert sig_key in snapshot.decisions
         sig_data = snapshot.decisions[sig_key]
         assert "dimensions" in sig_data
         assert "composite" in sig_data
         assert "band" in sig_data
         assert "hard_trigger_classes" in sig_data
         assert "effective_band" in sig_data
     ```
  2. Test soft gate decision in audit trail:
     ```python
     def test_soft_gate_decision_in_audit_trail(tmp_path):
         # Set up medium-band decision, provide decide_solo answer
         snapshot = _load_snapshot(run_ref)
         sg_key = "soft_gate:audit:review-step"
         assert sg_key in snapshot.decisions
         sg_data = snapshot.decisions[sg_key]
         assert sg_data["action"] == "decide_solo"
         assert sg_data["actor"]["actor_type"] == "human"
     ```
  3. Test RACI binding + significance coexist:
     ```python
     def test_raci_and_significance_both_persisted(tmp_path):
         # Verify both raci:{step_id} and significance:{decision_id} exist
         snapshot = _load_snapshot(run_ref)
         assert "raci:review-step" in snapshot.decisions
         assert "significance:audit:review-step" in snapshot.decisions
     ```
  4. Test hard-trigger classes recorded alongside numeric score:
     ```python
     def test_hard_trigger_recorded_in_audit(tmp_path):
         # Use hard-trigger fixture
         snapshot = _load_snapshot(run_ref)
         sig_data = snapshot.decisions["significance:audit:review-step"]
         assert len(sig_data["hard_trigger_classes"]) > 0
         assert sig_data["composite"] == 1  # low numeric
         assert sig_data["effective_band"]["name"] == "high"  # forced high
     ```
  5. Test significance event in JSONL log:
     ```python
     def test_significance_event_in_jsonl(tmp_path):
         # Read events.jsonl, verify significance_evaluated event present
         events = _read_events(run_ref)
         sig_events = [e for e in events if e.get("event_type") == "significance_evaluated"]
         assert len(sig_events) == 1
     ```

- **Files**: `tests/test_significance_integration.py`
- **Parallel?**: Yes — can be written alongside T034
- **Notes**: The audit trail tests verify SC-007 (complete audit trail) and FR-019 (capture full evaluation in trail).

### Subtask T036 – Write Determinism Verification Tests

- **Purpose**: Prove that significance evaluation is 100% reproducible (SC-008, NFR-003).

- **Steps**:
  1. Test bit-for-bit identical output across 5+ runs:
     ```python
     def test_deterministic_evaluation():
         """SC-008: Identical inputs produce identical outputs across 5+ independent runs."""
         scores = {
             "user_customer_impact": 2,
             "architectural_system_impact": 1,
             "data_security_compliance_impact": 3,
             "operational_reliability_impact": 2,
             "financial_commercial_impact": 1,
             "cross_team_blast_radius": 1,
         }
         results = []
         for _ in range(10):  # Run 10 times for extra confidence
             result = evaluate_significance(
                 dimension_scores=scores,
                 hard_trigger_classes=["production_data_destructive"],
             )
             results.append(result.model_dump())

         # Serialize with sort_keys for canonical comparison
         import json
         serialized = [json.dumps(r, sort_keys=True, separators=(",", ":")) for r in results]

         # All must be identical
         assert len(set(serialized)) == 1, f"Got {len(set(serialized))} distinct outputs across 10 runs"
     ```
  2. Test deterministic dimension ordering:
     ```python
     def test_deterministic_dimension_ordering():
         """Dimensions are always in the same order regardless of input dict ordering."""
         scores_a = dict(sorted({name: 1 for name in DIMENSION_NAMES}.items()))
         scores_b = dict(reversed(sorted({name: 1 for name in DIMENSION_NAMES}.items())))

         result_a = evaluate_significance(dimension_scores=scores_a)
         result_b = evaluate_significance(dimension_scores=scores_b)

         # Dimensions tuple must be in the same order
         assert result_a.dimensions == result_b.dimensions
     ```
  3. Test serialization determinism:
     ```python
     def test_serialization_determinism():
         """Serialized output is bit-for-bit identical across runs."""
         import json
         scores = {name: 2 for name in DIMENSION_NAMES}

         dumps = set()
         for _ in range(5):
             result = evaluate_significance(dimension_scores=scores)
             dumps.add(json.dumps(result.model_dump(), sort_keys=True, separators=(",", ":")))

         assert len(dumps) == 1
     ```

- **Files**: `tests/test_significance_integration.py`
- **Parallel?**: Yes — independent of other test subtasks
- **Notes**: Uses `json.dumps(sort_keys=True, separators=(",", ":"))` matching the JsonlEventLog serialization pattern for canonical comparison.

### Subtask T037 – Write Edge Case Tests + Validate Quickstart Examples

- **Purpose**: Cover all edge cases listed in the spec and verify quickstart.md code examples work.

- **Steps**:
  1. Edge case: all zeros (total 0):
     ```python
     def test_edge_all_zeros():
         scores = {name: 0 for name in DIMENSION_NAMES}
         result = evaluate_significance(dimension_scores=scores)
         assert result.composite == 0
         assert result.band.name == "low"
     ```
  2. Edge case: multiple hard-triggers simultaneously:
     ```python
     def test_edge_multiple_hard_triggers():
         scores = {name: 0 for name in DIMENSION_NAMES}
         result = evaluate_significance(
             dimension_scores=scores,
             hard_trigger_classes=list(HARD_TRIGGER_REGISTRY.keys()),  # all 5
         )
         assert result.effective_band.name == "high"
         assert len(result.hard_trigger_classes) == 5
     ```
  3. Edge case: fewer than 6 dimensions:
     ```python
     def test_edge_fewer_than_six_dimensions():
         scores = {"user_customer_impact": 1, "architectural_system_impact": 1}
         with pytest.raises(ValueError, match="missing"):
             evaluate_significance(dimension_scores=scores)
     ```
  4. Edge case: dimension score outside range:
     ```python
     def test_edge_score_out_of_range():
         scores = {name: 1 for name in DIMENSION_NAMES}
         scores["user_customer_impact"] = 5
         with pytest.raises(ValueError):
             evaluate_significance(dimension_scores=scores)
     ```
  5. Edge case: timeout = 0 rejected:
     ```python
     def test_edge_timeout_zero():
         with pytest.raises(ValueError):
             TimeoutPolicy(default_timeout_seconds=0)
     ```
  6. Edge case: invalid band cutoffs (overlapping):
     ```python
     def test_edge_cutoffs_overlapping():
         with pytest.raises(ValueError):
             evaluate_significance(
                 dimension_scores={name: 1 for name in DIMENSION_NAMES},
                 band_cutoffs={"low": [0, 7], "medium": [6, 11], "high": [12, 18]},
             )
     ```
  7. Edge case: RACI snapshot with no consulted (high-band escalation):
     ```python
     def test_edge_escalation_no_consulted():
         raci = ResolvedRACIBinding(
             step_id="test",
             responsible=RACIRoleBinding(actor_type="human", actor_id="r-001"),
             accountable=RACIRoleBinding(actor_type="human", actor_id="owner-001"),
             consulted=[],  # empty!
             informed=[],
             source="inferred",
             inferred_rule="audit_blocking",
         )
         targets = compute_escalation_targets(raci, "high")
         assert len(targets) == 1  # owner only, no error
     ```
  8. Validate quickstart.md code examples:
     ```python
     def test_quickstart_evaluate_significance():
         """Verify the code example from quickstart.md works."""
         from spec_kitty_runtime.significance import evaluate_significance

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
             band_cutoffs=None,
         )

         assert score.composite == 10
         assert score.band.name == "medium"
         assert score.effective_band.name == "high"  # hard-trigger override
         assert "production_data_destructive" in [
             ht.class_id for ht in score.hard_trigger_classes
         ]
     ```

- **Files**: `tests/test_significance_integration.py` (edge cases), `tests/test_significance_timeout.py` (timeout edge cases)
- **Parallel?**: Yes — independent of other test subtasks
- **Notes**:
  - The quickstart validation test directly copies the code from `quickstart.md` and verifies it works. If any assertion fails, either the implementation or the quickstart needs updating.
  - Edge cases cover ALL items from the "Edge Cases" section of spec.md

## Risks & Mitigations

- **Integration test complexity**: Keep each test focused on one scenario. Use shared setup helpers but avoid complex fixture chains.
- **Fixture dependency**: Tests in this WP use fixtures from WP06. Ensure WP06 is merged first.
- **Determinism testing**: The json.dumps comparison is the canonical approach. Don't use `==` on Pydantic models directly (field ordering may vary).
- **Quickstart drift**: If quickstart.md examples don't match the implementation, update the test (and flag to update quickstart.md).

## Review Guidance

- Verify determinism tests use 5+ independent runs (SC-008)
- Verify all spec edge cases are covered (check against spec.md "Edge Cases" section)
- Verify integration tests exercise the full engine flow (not just individual functions)
- Verify audit trail tests check all keys: significance, soft_gate, timeout, raci
- Verify backward compatibility test exists (mission without significance block)
- Verify quickstart code examples pass
- Verify zero flaky tests (no randomness, no datetime.now in assertions)

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

- 2026-02-27T20:43:12Z – system – lane=planned – Prompt created.
- 2026-02-27T22:22:08Z – claude-opus – shell_pid=47123 – lane=doing – Assigned agent via workflow command
- 2026-02-27T22:27:31Z – claude-opus – shell_pid=47123 – lane=for_review – Ready for review: 85 new tests across 2 files (test_significance_timeout.py, test_significance_integration.py). Covers T032-T037: timeout policy validation, escalation targets, event emission, full engine flow integration (all bands + hard-trigger + backward compat), audit trail capture, determinism verification (10 independent runs), edge cases, and quickstart API validation. 730 total tests passing, zero flaky.

"""WP07 – T034/T035/T036/T037: Integration, Audit Trail, Determinism, and Edge Case Tests.

Covers:
- T034: Full engine flow integration tests (start → next_step → evaluate → decide → complete)
- T035: Audit trail capture verification (significance, soft_gate, RACI, hard-trigger)
- T036: Determinism verification (SC-008, 5+ independent runs, bit-for-bit identical)
- T037: Edge case tests + quickstart example validation

All tests deterministic, offline, no randomness (NFR-003, NFR-004).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from spec_kitty_runtime.discovery import DiscoveryContext
from spec_kitty_runtime.engine import next_step, provide_decision_answer, start_mission_run
from spec_kitty_runtime.schema import (
    ActorIdentity,
    MissionPolicySnapshot,
    MissionRuntimeError,
    RACIRoleBinding,
    ResolvedRACIBinding,
    SignificanceBlock,
)
from spec_kitty_runtime.significance import (
    DEFAULT_BANDS,
    DIMENSION_NAMES,
    HARD_TRIGGER_REGISTRY,
    TimeoutPolicy,
    compute_escalation_targets,
    evaluate_significance,
    validate_band_cutoffs,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FIXTURES = Path(__file__).parent / "fixtures"


def _all_dimensions(score: int) -> dict[str, int]:
    return {name: score for name in sorted(DIMENSION_NAMES)}


def _setup(
    tmp_path: Path,
    yaml_content: str,
    key: str,
) -> DiscoveryContext:
    mission_file = tmp_path / "pack" / "missions" / key / "mission.yaml"
    mission_file.parent.mkdir(parents=True, exist_ok=True)
    mission_file.write_text(yaml_content, encoding="utf-8")
    return DiscoveryContext(explicit_paths=[tmp_path / "pack"], builtin_roots=[])


def _actor(actor_id: str = "human-reviewer") -> ActorIdentity:
    return ActorIdentity(actor_id=actor_id, actor_type="human")


def _read_snapshot_raw(run_ref) -> dict:
    state_file = Path(run_ref.run_dir) / "state.json"
    with open(state_file, encoding="utf-8") as f:
        return json.load(f)


def _read_events(run_ref) -> list[dict]:
    events_file = Path(run_ref.run_dir) / "run.events.jsonl"
    events = []
    with open(events_file, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                events.append(json.loads(line))
    return events


def _advance_to_audit(
    tmp_path: Path,
    yaml_content: str,
    key: str,
    inputs: dict | None = None,
):
    """Advance a mission run to the audit checkpoint.

    Returns (run_ref, decision, context).
    """
    context = _setup(tmp_path, yaml_content, key)
    policy = MissionPolicySnapshot()
    resolved_inputs = inputs if inputs is not None else {"mission_owner_id": "human-reviewer"}
    run_ref = start_mission_run(
        template_key=key,
        inputs=resolved_inputs,
        policy_snapshot=policy,
        context=context,
        run_store=tmp_path / "runs",
    )
    # Advance past the prepare step
    d1 = next_step(run_ref, agent_id="agent-01", context=context)
    assert d1.kind == "step"

    d2 = next_step(run_ref, agent_id="agent-01", result="success", context=context)
    return run_ref, d2, context


# ---------------------------------------------------------------------------
# Mission YAML templates (using fixture-aligned dimensions)
# ---------------------------------------------------------------------------

# composite=6 → low band (auto-proceed)
MISSION_LOW = """\
mission:
  key: int-sig-low
  name: Integration Low Significance
  version: "1.0.0"
steps:
  - id: prepare
    title: Prepare
    prompt: "Gather artifacts"
  - id: follow-up
    title: Follow-up step
    depends_on: ["low-review"]
audit_steps:
  - id: low-review
    title: Low-impact check
    depends_on: ["prepare"]
    audit:
      trigger_mode: manual
      enforcement: blocking
    significance:
      dimensions:
        architectural_system_impact: 1
        cross_team_blast_radius: 1
        data_security_compliance_impact: 1
        financial_commercial_impact: 1
        operational_reliability_impact: 1
        user_customer_impact: 1
"""

# composite=9 → medium band (soft gate)
MISSION_MEDIUM = """\
mission:
  key: int-sig-medium
  name: Integration Medium Significance
  version: "1.0.0"
steps:
  - id: prepare
    title: Prepare
    prompt: "Gather artifacts"
audit_steps:
  - id: medium-review
    title: Medium-impact check
    depends_on: ["prepare"]
    audit:
      trigger_mode: manual
      enforcement: blocking
    significance:
      dimensions:
        architectural_system_impact: 1
        cross_team_blast_radius: 1
        data_security_compliance_impact: 2
        financial_commercial_impact: 1
        operational_reliability_impact: 2
        user_customer_impact: 2
"""

# composite=18 → high band (hard gate)
MISSION_HIGH = """\
mission:
  key: int-sig-high
  name: Integration High Significance
  version: "1.0.0"
steps:
  - id: prepare
    title: Prepare
    prompt: "Gather artifacts"
audit_steps:
  - id: high-review
    title: High-impact check
    depends_on: ["prepare"]
    audit:
      trigger_mode: manual
      enforcement: blocking
    significance:
      dimensions:
        architectural_system_impact: 3
        cross_team_blast_radius: 3
        data_security_compliance_impact: 3
        financial_commercial_impact: 3
        operational_reliability_impact: 3
        user_customer_impact: 3
"""

# composite=1 but hard-trigger → overrides to high
MISSION_HARD_TRIGGER = """\
mission:
  key: int-sig-hard-trigger
  name: Integration Hard Trigger
  version: "1.0.0"
steps:
  - id: prepare
    title: Prepare
    prompt: "Gather artifacts"
audit_steps:
  - id: trigger-review
    title: Security check
    depends_on: ["prepare"]
    audit:
      trigger_mode: manual
      enforcement: blocking
    significance:
      dimensions:
        architectural_system_impact: 0
        cross_team_blast_radius: 0
        data_security_compliance_impact: 1
        financial_commercial_impact: 0
        operational_reliability_impact: 0
        user_customer_impact: 0
      hard_triggers:
        - production_data_destructive
"""

# No significance block (backward compat)
MISSION_NO_SIGNIFICANCE = """\
mission:
  key: int-no-sig
  name: Integration No Significance
  version: "1.0.0"
steps:
  - id: prepare
    title: Prepare
    prompt: "Gather artifacts"
audit_steps:
  - id: basic-review
    title: Basic check
    depends_on: ["prepare"]
    audit:
      trigger_mode: manual
      enforcement: blocking
"""


# ============================================================================
# T034: Engine Flow Integration Tests
# ============================================================================


class TestLowBandAutoProceed:
    """Low significance decisions auto-proceed without a human gate (FR-004)."""

    def test_low_band_auto_proceeds(self, tmp_path: Path) -> None:
        """Low band audit auto-completes without decision_required."""
        run_ref, d2, _ = _advance_to_audit(
            tmp_path, MISSION_LOW, "int-sig-low"
        )
        # Low band should auto-proceed — either step or terminal, NOT decision_required
        assert d2.kind != "decision_required" or d2.decision_id != "audit:low-review"

    def test_low_band_in_completed_steps(self, tmp_path: Path) -> None:
        """Low band audit step is auto-added to completed_steps."""
        run_ref, _, _ = _advance_to_audit(
            tmp_path, MISSION_LOW, "int-sig-low"
        )
        state = _read_snapshot_raw(run_ref)
        assert "low-review" in state["completed_steps"]

    def test_low_band_dag_continues(self, tmp_path: Path) -> None:
        """After low band auto-proceed, next step is available."""
        run_ref, d2, context = _advance_to_audit(
            tmp_path, MISSION_LOW, "int-sig-low"
        )
        # follow-up depends on low-review; since low-review auto-proceeded, follow-up is next
        assert d2.kind == "step"
        assert d2.step_id == "follow-up"


class TestMediumBandSoftGate:
    """Medium band raises soft gate with decide_solo/open_stand_up/defer (FR-005)."""

    def test_medium_band_returns_decision_required(self, tmp_path: Path) -> None:
        run_ref, d2, _ = _advance_to_audit(
            tmp_path, MISSION_MEDIUM, "int-sig-medium"
        )
        assert d2.kind == "decision_required"
        assert d2.decision_id == "audit:medium-review"

    def test_medium_band_options(self, tmp_path: Path) -> None:
        run_ref, d2, _ = _advance_to_audit(
            tmp_path, MISSION_MEDIUM, "int-sig-medium"
        )
        assert d2.options == ["decide_solo", "open_stand_up", "defer"]

    def test_medium_decide_solo_clears_gate(self, tmp_path: Path) -> None:
        run_ref, _, _ = _advance_to_audit(
            tmp_path, MISSION_MEDIUM, "int-sig-medium"
        )
        provide_decision_answer(run_ref, "audit:medium-review", "decide_solo", _actor())

        state = _read_snapshot_raw(run_ref)
        assert "medium-review" in state["completed_steps"]
        assert "audit:medium-review" not in state["pending_decisions"]

    def test_medium_open_stand_up_keeps_gate_open(self, tmp_path: Path) -> None:
        run_ref, _, _ = _advance_to_audit(
            tmp_path, MISSION_MEDIUM, "int-sig-medium"
        )
        provide_decision_answer(run_ref, "audit:medium-review", "open_stand_up", _actor())

        state = _read_snapshot_raw(run_ref)
        assert "medium-review" not in state["completed_steps"]
        assert "audit:medium-review" in state["pending_decisions"]

    def test_medium_defer_keeps_gate_open(self, tmp_path: Path) -> None:
        run_ref, _, _ = _advance_to_audit(
            tmp_path, MISSION_MEDIUM, "int-sig-medium"
        )
        provide_decision_answer(run_ref, "audit:medium-review", "defer", _actor())

        state = _read_snapshot_raw(run_ref)
        assert "medium-review" not in state["completed_steps"]
        assert "audit:medium-review" in state["pending_decisions"]

    def test_medium_rejects_approve(self, tmp_path: Path) -> None:
        """Medium band rejects 'approve' answer."""
        run_ref, _, _ = _advance_to_audit(
            tmp_path, MISSION_MEDIUM, "int-sig-medium"
        )
        with pytest.raises(MissionRuntimeError, match="Medium-band"):
            provide_decision_answer(run_ref, "audit:medium-review", "approve", _actor())

    def test_medium_rejects_reject(self, tmp_path: Path) -> None:
        """Medium band rejects 'reject' answer."""
        run_ref, _, _ = _advance_to_audit(
            tmp_path, MISSION_MEDIUM, "int-sig-medium"
        )
        with pytest.raises(MissionRuntimeError, match="Medium-band"):
            provide_decision_answer(run_ref, "audit:medium-review", "reject", _actor())


class TestHighBandHardGate:
    """High band raises hard gate with approve/reject options (FR-007)."""

    def test_high_band_returns_decision_required(self, tmp_path: Path) -> None:
        run_ref, d2, _ = _advance_to_audit(
            tmp_path, MISSION_HIGH, "int-sig-high"
        )
        assert d2.kind == "decision_required"
        assert d2.decision_id == "audit:high-review"

    def test_high_band_options_approve_reject(self, tmp_path: Path) -> None:
        run_ref, d2, _ = _advance_to_audit(
            tmp_path, MISSION_HIGH, "int-sig-high"
        )
        assert d2.options == ["approve", "reject"]

    def test_high_band_approve_clears_gate(self, tmp_path: Path) -> None:
        run_ref, _, _ = _advance_to_audit(
            tmp_path, MISSION_HIGH, "int-sig-high"
        )
        provide_decision_answer(run_ref, "audit:high-review", "approve", _actor())

        state = _read_snapshot_raw(run_ref)
        assert "high-review" in state["completed_steps"]

    def test_high_band_reject_blocks_run(self, tmp_path: Path) -> None:
        run_ref, _, _ = _advance_to_audit(
            tmp_path, MISSION_HIGH, "int-sig-high"
        )
        provide_decision_answer(run_ref, "audit:high-review", "reject", _actor())

        state = _read_snapshot_raw(run_ref)
        assert state["blocked_reason"] is not None

    def test_high_band_rejects_decide_solo(self, tmp_path: Path) -> None:
        run_ref, _, _ = _advance_to_audit(
            tmp_path, MISSION_HIGH, "int-sig-high"
        )
        with pytest.raises(MissionRuntimeError, match="High-band"):
            provide_decision_answer(run_ref, "audit:high-review", "decide_solo", _actor())


class TestHardTriggerOverride:
    """Hard trigger forces hard gate even with low numeric score (FR-008, US2)."""

    def test_hard_trigger_overrides_to_hard_gate(self, tmp_path: Path) -> None:
        run_ref, d2, _ = _advance_to_audit(
            tmp_path, MISSION_HARD_TRIGGER, "int-sig-hard-trigger"
        )
        assert d2.kind == "decision_required"
        assert d2.options == ["approve", "reject"]

    def test_hard_trigger_effective_band_high(self, tmp_path: Path) -> None:
        run_ref, _, _ = _advance_to_audit(
            tmp_path, MISSION_HARD_TRIGGER, "int-sig-hard-trigger"
        )
        state = _read_snapshot_raw(run_ref)
        sig = state["decisions"]["significance:audit:trigger-review"]
        eb = sig["effective_band"]
        band_name = eb["name"] if isinstance(eb, dict) else eb
        assert band_name == "high"

    def test_hard_trigger_low_composite_persisted(self, tmp_path: Path) -> None:
        run_ref, _, _ = _advance_to_audit(
            tmp_path, MISSION_HARD_TRIGGER, "int-sig-hard-trigger"
        )
        state = _read_snapshot_raw(run_ref)
        sig = state["decisions"]["significance:audit:trigger-review"]
        assert sig["composite"] == 1  # low numeric score


class TestBackwardCompatNoSignificance:
    """AuditStep without significance block works exactly as before."""

    def test_no_significance_returns_decision_required(self, tmp_path: Path) -> None:
        run_ref, d2, _ = _advance_to_audit(
            tmp_path, MISSION_NO_SIGNIFICANCE, "int-no-sig"
        )
        assert d2.kind == "decision_required"
        assert d2.decision_id == "audit:basic-review"

    def test_no_significance_options_approve_reject(self, tmp_path: Path) -> None:
        run_ref, d2, _ = _advance_to_audit(
            tmp_path, MISSION_NO_SIGNIFICANCE, "int-no-sig"
        )
        assert d2.options == ["approve", "reject"]

    def test_no_significance_approve_works(self, tmp_path: Path) -> None:
        run_ref, _, _ = _advance_to_audit(
            tmp_path, MISSION_NO_SIGNIFICANCE, "int-no-sig"
        )
        provide_decision_answer(run_ref, "audit:basic-review", "approve", _actor())

        state = _read_snapshot_raw(run_ref)
        assert "basic-review" in state["completed_steps"]

    def test_no_significance_reject_blocks(self, tmp_path: Path) -> None:
        run_ref, _, _ = _advance_to_audit(
            tmp_path, MISSION_NO_SIGNIFICANCE, "int-no-sig"
        )
        provide_decision_answer(run_ref, "audit:basic-review", "reject", _actor())

        state = _read_snapshot_raw(run_ref)
        assert state["blocked_reason"] is not None

    def test_no_significance_key_absent(self, tmp_path: Path) -> None:
        """No significance key in decisions dict without significance block."""
        run_ref, _, _ = _advance_to_audit(
            tmp_path, MISSION_NO_SIGNIFICANCE, "int-no-sig"
        )
        state = _read_snapshot_raw(run_ref)
        assert "significance:audit:basic-review" not in state["decisions"]


# ============================================================================
# T035: Audit Trail Capture Tests
# ============================================================================


class TestAuditTrailCapture:
    """Verify every significance decision captures the complete audit trail (FR-019, SC-007)."""

    def test_significance_score_in_audit_trail(self, tmp_path: Path) -> None:
        """Significance evaluation persisted to decisions dict."""
        run_ref, _, _ = _advance_to_audit(
            tmp_path, MISSION_MEDIUM, "int-sig-medium"
        )
        state = _read_snapshot_raw(run_ref)
        sig_key = "significance:audit:medium-review"
        assert sig_key in state["decisions"]
        sig_data = state["decisions"][sig_key]
        assert "dimensions" in sig_data
        assert "composite" in sig_data
        assert "band" in sig_data
        assert "hard_trigger_classes" in sig_data
        assert "effective_band" in sig_data

    def test_soft_gate_decision_in_audit_trail(self, tmp_path: Path) -> None:
        """Soft gate decision persisted with correct action."""
        run_ref, _, _ = _advance_to_audit(
            tmp_path, MISSION_MEDIUM, "int-sig-medium"
        )
        provide_decision_answer(run_ref, "audit:medium-review", "decide_solo", _actor())

        state = _read_snapshot_raw(run_ref)
        sg_key = "soft_gate:audit:medium-review"
        assert sg_key in state["decisions"]
        sg_data = state["decisions"][sg_key]
        assert sg_data["action"] == "decide_solo"
        assert sg_data["actor"]["actor_type"] == "human"

    def test_raci_and_significance_both_persisted(self, tmp_path: Path) -> None:
        """Both RACI and significance keys exist in decisions dict."""
        run_ref, _, _ = _advance_to_audit(
            tmp_path, MISSION_MEDIUM, "int-sig-medium"
        )
        state = _read_snapshot_raw(run_ref)
        assert "raci:medium-review" in state["decisions"]
        assert "significance:audit:medium-review" in state["decisions"]

    def test_hard_trigger_recorded_in_audit(self, tmp_path: Path) -> None:
        """Hard-trigger classes recorded alongside numeric score."""
        run_ref, _, _ = _advance_to_audit(
            tmp_path, MISSION_HARD_TRIGGER, "int-sig-hard-trigger"
        )
        state = _read_snapshot_raw(run_ref)
        sig_data = state["decisions"]["significance:audit:trigger-review"]
        assert len(sig_data["hard_trigger_classes"]) > 0
        assert sig_data["composite"] == 1  # low numeric
        eb = sig_data["effective_band"]
        band_name = eb["name"] if isinstance(eb, dict) else eb
        assert band_name == "high"  # forced high

    def test_significance_event_in_jsonl(self, tmp_path: Path) -> None:
        """SignificanceEvaluated event present in JSONL event log."""
        run_ref, _, _ = _advance_to_audit(
            tmp_path, MISSION_MEDIUM, "int-sig-medium"
        )
        events = _read_events(run_ref)
        sig_events = [e for e in events if e["event_type"] == "SignificanceEvaluated"]
        assert len(sig_events) == 1
        assert sig_events[0]["payload"]["effective_band"] == "medium"

    def test_significance_event_for_low_band_in_jsonl(self, tmp_path: Path) -> None:
        """SignificanceEvaluated event emitted even for low band."""
        run_ref, _, _ = _advance_to_audit(
            tmp_path, MISSION_LOW, "int-sig-low"
        )
        events = _read_events(run_ref)
        sig_events = [e for e in events if e["event_type"] == "SignificanceEvaluated"]
        assert len(sig_events) == 1
        assert sig_events[0]["payload"]["effective_band"] == "low"

    def test_high_band_significance_in_jsonl(self, tmp_path: Path) -> None:
        """SignificanceEvaluated event for high band has correct fields."""
        run_ref, _, _ = _advance_to_audit(
            tmp_path, MISSION_HIGH, "int-sig-high"
        )
        events = _read_events(run_ref)
        sig_events = [e for e in events if e["event_type"] == "SignificanceEvaluated"]
        assert len(sig_events) == 1
        payload = sig_events[0]["payload"]
        assert payload["effective_band"] == "high"
        assert "decision_id" in payload
        assert "step_id" in payload


# ============================================================================
# T036: Determinism Verification Tests
# ============================================================================


class TestDeterministicEvaluation:
    """Prove significance evaluation is 100% reproducible (SC-008, NFR-003)."""

    def test_deterministic_evaluation_10_runs(self) -> None:
        """SC-008: Identical inputs produce identical outputs across 10 independent runs."""
        scores = {
            "user_customer_impact": 2,
            "architectural_system_impact": 1,
            "data_security_compliance_impact": 3,
            "operational_reliability_impact": 2,
            "financial_commercial_impact": 1,
            "cross_team_blast_radius": 1,
        }
        results = []
        for _ in range(10):
            result = evaluate_significance(
                dimension_scores=scores,
                hard_trigger_classes=["production_data_destructive"],
            )
            results.append(result.model_dump())

        serialized = [json.dumps(r, sort_keys=True, separators=(",", ":")) for r in results]
        assert len(set(serialized)) == 1, f"Got {len(set(serialized))} distinct outputs across 10 runs"

    def test_deterministic_dimension_ordering(self) -> None:
        """Dimensions are always in the same order regardless of input dict ordering."""
        scores_a = dict(sorted({name: 1 for name in DIMENSION_NAMES}.items()))
        scores_b = dict(reversed(sorted({name: 1 for name in DIMENSION_NAMES}.items())))

        result_a = evaluate_significance(dimension_scores=scores_a)
        result_b = evaluate_significance(dimension_scores=scores_b)

        # Dimensions tuple must be in the same order
        assert result_a.dimensions == result_b.dimensions

    def test_serialization_determinism(self) -> None:
        """Serialized output is bit-for-bit identical across runs."""
        scores = {name: 2 for name in DIMENSION_NAMES}

        dumps = set()
        for _ in range(5):
            result = evaluate_significance(dimension_scores=scores)
            dumps.add(json.dumps(result.model_dump(), sort_keys=True, separators=(",", ":")))

        assert len(dumps) == 1

    def test_deterministic_with_hard_triggers(self) -> None:
        """Deterministic even with hard-trigger classes."""
        scores = {name: 0 for name in DIMENSION_NAMES}
        dumps = set()
        for _ in range(5):
            result = evaluate_significance(
                dimension_scores=scores,
                hard_trigger_classes=["production_data_destructive", "security_privacy_access_control"],
            )
            dumps.add(json.dumps(result.model_dump(), sort_keys=True, separators=(",", ":")))

        assert len(dumps) == 1

    def test_deterministic_with_custom_cutoffs(self) -> None:
        """Deterministic with custom band cutoffs."""
        scores = {name: 1 for name in DIMENSION_NAMES}
        cutoffs = {"low": [0, 5], "medium": [6, 10], "high": [11, 18]}
        dumps = set()
        for _ in range(5):
            result = evaluate_significance(
                dimension_scores=scores,
                band_cutoffs=cutoffs,
            )
            dumps.add(json.dumps(result.model_dump(), sort_keys=True, separators=(",", ":")))

        assert len(dumps) == 1

    def test_deterministic_engine_integration(self, tmp_path: Path) -> None:
        """Full engine flow produces deterministic significance evaluation across runs."""
        snapshots = []
        for i in range(5):
            run_tmp = tmp_path / f"run-{i}"
            run_tmp.mkdir()
            run_ref, _, _ = _advance_to_audit(
                run_tmp, MISSION_MEDIUM, "int-sig-medium"
            )
            state = _read_snapshot_raw(run_ref)
            sig = state["decisions"]["significance:audit:medium-review"]
            snapshots.append(json.dumps(sig, sort_keys=True, separators=(",", ":")))

        assert len(set(snapshots)) == 1, f"Got {len(set(snapshots))} distinct significance evals across 5 engine runs"


# ============================================================================
# T037: Edge Case Tests
# ============================================================================


class TestEdgeCases:
    """Cover all edge cases listed in spec."""

    def test_edge_all_zeros(self) -> None:
        """All zeros → composite=0 → low band."""
        scores = {name: 0 for name in DIMENSION_NAMES}
        result = evaluate_significance(dimension_scores=scores)
        assert result.composite == 0
        assert result.band.name == "low"

    def test_edge_all_max(self) -> None:
        """All 3s → composite=18 → high band."""
        scores = {name: 3 for name in DIMENSION_NAMES}
        result = evaluate_significance(dimension_scores=scores)
        assert result.composite == 18
        assert result.band.name == "high"

    def test_edge_multiple_hard_triggers(self) -> None:
        """Multiple hard-triggers simultaneously."""
        scores = {name: 0 for name in DIMENSION_NAMES}
        result = evaluate_significance(
            dimension_scores=scores,
            hard_trigger_classes=list(HARD_TRIGGER_REGISTRY.keys()),
        )
        assert result.effective_band.name == "high"
        assert len(result.hard_trigger_classes) == 5

    def test_edge_fewer_than_six_dimensions(self) -> None:
        """Fewer than 6 dimensions raises ValueError."""
        scores = {"user_customer_impact": 1, "architectural_system_impact": 1}
        with pytest.raises(ValueError, match="missing"):
            evaluate_significance(dimension_scores=scores)

    def test_edge_extra_dimension(self) -> None:
        """Extra unknown dimension raises ValueError."""
        scores = {name: 1 for name in DIMENSION_NAMES}
        scores["bogus_dimension"] = 1
        with pytest.raises(ValueError, match="unexpected"):
            evaluate_significance(dimension_scores=scores)

    def test_edge_score_out_of_range_high(self) -> None:
        """Dimension score > 3 raises ValueError."""
        scores = {name: 1 for name in DIMENSION_NAMES}
        scores["user_customer_impact"] = 5
        with pytest.raises(ValueError):
            evaluate_significance(dimension_scores=scores)

    def test_edge_score_out_of_range_negative(self) -> None:
        """Negative dimension score raises ValueError."""
        scores = {name: 1 for name in DIMENSION_NAMES}
        scores["user_customer_impact"] = -1
        with pytest.raises(ValueError):
            evaluate_significance(dimension_scores=scores)

    def test_edge_timeout_zero(self) -> None:
        """Timeout=0 rejected."""
        with pytest.raises(ValueError):
            TimeoutPolicy(default_timeout_seconds=0)

    def test_edge_cutoffs_overlapping(self) -> None:
        """Overlapping band cutoffs rejected."""
        with pytest.raises(ValueError, match="Overlap"):
            validate_band_cutoffs({"low": [0, 7], "medium": [6, 11], "high": [12, 18]})

    def test_edge_cutoffs_gap(self) -> None:
        """Gap in band cutoffs rejected."""
        with pytest.raises(ValueError, match="Gap"):
            validate_band_cutoffs({"low": [0, 5], "medium": [7, 11], "high": [12, 18]})

    def test_edge_cutoffs_wrong_start(self) -> None:
        """Band cutoffs not starting at 0 rejected."""
        with pytest.raises(ValueError, match="start at 0"):
            validate_band_cutoffs({"low": [1, 6], "medium": [7, 11], "high": [12, 18]})

    def test_edge_cutoffs_wrong_end(self) -> None:
        """Band cutoffs not ending at 18 rejected."""
        with pytest.raises(ValueError, match="end at 18"):
            validate_band_cutoffs({"low": [0, 6], "medium": [7, 11], "high": [12, 17]})

    def test_edge_unknown_hard_trigger(self) -> None:
        """Unknown hard-trigger class raises ValueError."""
        scores = {name: 1 for name in DIMENSION_NAMES}
        with pytest.raises(ValueError, match="Unknown hard-trigger"):
            evaluate_significance(
                dimension_scores=scores,
                hard_trigger_classes=["nonexistent_trigger"],
            )

    def test_edge_escalation_no_consulted(self) -> None:
        """RACI with no consulted → high-band escalation still works (owner only)."""
        raci = ResolvedRACIBinding(
            step_id="test",
            responsible=RACIRoleBinding(actor_type="human", actor_id="r-001"),
            accountable=RACIRoleBinding(actor_type="human", actor_id="owner-001"),
            consulted=[],
            informed=[],
            source="inferred",
            inferred_rule="audit_blocking",
        )
        targets = compute_escalation_targets(raci, "high")
        assert len(targets) == 1
        assert targets[0].actor_id == "owner-001"


class TestQuickstartExamples:
    """Verify quickstart code examples work against implemented API."""

    def test_quickstart_evaluate_significance(self) -> None:
        """Verify the core evaluate_significance example from docs."""
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

    def test_quickstart_timeout_policy(self) -> None:
        """Verify TimeoutPolicy usage example."""
        from spec_kitty_runtime.significance import TimeoutPolicy

        policy = TimeoutPolicy(default_timeout_seconds=600)
        assert policy.effective_timeout_seconds == 600

        override = TimeoutPolicy(default_timeout_seconds=600, per_decision_timeout_seconds=120)
        assert override.effective_timeout_seconds == 120

    def test_quickstart_compute_escalation(self) -> None:
        """Verify compute_escalation_targets usage example."""
        from spec_kitty_runtime.significance import compute_escalation_targets

        raci = ResolvedRACIBinding(
            step_id="deploy",
            responsible=RACIRoleBinding(actor_type="llm", actor_id="agent-1"),
            accountable=RACIRoleBinding(actor_type="human", actor_id="owner-1"),
            consulted=[RACIRoleBinding(actor_type="human", actor_id="sec-lead")],
            informed=[],
            source="inferred",
            inferred_rule="audit_blocking",
        )

        medium_targets = compute_escalation_targets(raci, "medium")
        assert len(medium_targets) == 1
        assert medium_targets[0].actor_id == "owner-1"

        high_targets = compute_escalation_targets(raci, "high")
        assert len(high_targets) == 2
        assert high_targets[0].actor_id == "owner-1"
        assert high_targets[1].actor_id == "sec-lead"

    def test_quickstart_dimension_names_and_registry(self) -> None:
        """Verify DIMENSION_NAMES and HARD_TRIGGER_REGISTRY constants."""
        from spec_kitty_runtime.significance import DIMENSION_NAMES, HARD_TRIGGER_REGISTRY

        assert len(DIMENSION_NAMES) == 6
        assert "user_customer_impact" in DIMENSION_NAMES
        assert len(HARD_TRIGGER_REGISTRY) == 5
        assert "production_data_destructive" in HARD_TRIGGER_REGISTRY

    def test_quickstart_routing_band_thresholds(self) -> None:
        """Verify band routing thresholds match documentation."""
        # Low: 0-6
        low = evaluate_significance(dimension_scores={name: 1 for name in DIMENSION_NAMES})
        assert low.band.name == "low"  # composite=6

        # Medium: 7-11
        names = sorted(DIMENSION_NAMES)
        med_scores = {name: 1 for name in names}
        med_scores[names[0]] = 2  # composite=7
        medium = evaluate_significance(dimension_scores=med_scores)
        assert medium.band.name == "medium"

        # High: 12-18
        high = evaluate_significance(dimension_scores={name: 2 for name in DIMENSION_NAMES})
        assert high.band.name == "high"  # composite=12

    def test_quickstart_significance_block_on_audit_step(self) -> None:
        """Verify SignificanceBlock can be constructed as shown in docs."""
        block = SignificanceBlock(
            dimensions={
                "user_customer_impact": 2,
                "architectural_system_impact": 1,
                "data_security_compliance_impact": 3,
                "operational_reliability_impact": 2,
                "financial_commercial_impact": 1,
                "cross_team_blast_radius": 1,
            },
            hard_triggers=["production_data_destructive"],
        )
        assert sum(block.dimensions.values()) == 10
        assert len(block.hard_triggers) == 1

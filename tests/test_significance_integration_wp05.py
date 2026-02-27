"""WP05: AuditStep Extension & Engine Integration tests.

Tests significance-aware audit gate routing in next_step() and provide_decision_answer().
Covers:
- T021: SignificanceBlock on AuditStep
- T022: Significance evaluation in next_step()
- T023: Significance routing in provide_decision_answer()
- T024: Persistence verification
- T025: Public API re-exports
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from spec_kitty_runtime.discovery import DiscoveryContext
from spec_kitty_runtime.engine import next_step, provide_decision_answer, start_mission_run
from spec_kitty_runtime.schema import (
    ActorIdentity,
    AuditStep,
    MissionPolicySnapshot,
    MissionRuntimeError,
    SignificanceBlock,
)
from spec_kitty_runtime.significance import DIMENSION_NAMES


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _all_dimensions(score: int) -> dict[str, int]:
    """Return all 6 dimensions with the same score."""
    return {name: score for name in sorted(DIMENSION_NAMES)}


def _mixed_dimensions(low: int = 0, high: int = 3) -> dict[str, int]:
    """Return dimensions with mixed scores. First 3 get `low`, last 3 get `high`."""
    names = sorted(DIMENSION_NAMES)
    return {n: low if i < 3 else high for i, n in enumerate(names)}


LOW_SCORE_DIMS = _all_dimensions(0)       # composite=0  → low band
MEDIUM_SCORE_DIMS = _mixed_dimensions(1, 2)  # composite=9  → medium band
HIGH_SCORE_DIMS = _all_dimensions(3)       # composite=18 → high band


# ---------------------------------------------------------------------------
# Mission YAML templates
# ---------------------------------------------------------------------------

# All 6 dimensions at 0 → composite=0 → low band
AUDIT_WITH_LOW_SIGNIFICANCE = """\
mission:
  key: test-sig-low
  name: Test Low Significance
  version: "1.0.0"
steps:
  - id: step-01
    title: First step
  - id: step-02
    title: Second step
    depends_on: ["audit-01"]
audit_steps:
  - id: audit-01
    title: Low-impact check
    depends_on: ["step-01"]
    audit:
      trigger_mode: manual
      enforcement: blocking
    significance:
      dimensions:
        architectural_system_impact: 0
        cross_team_blast_radius: 0
        data_security_compliance_impact: 0
        financial_commercial_impact: 0
        operational_reliability_impact: 0
        user_customer_impact: 0
"""

# 3 dims at 1, 3 dims at 2 → composite=9 → medium band
AUDIT_WITH_MEDIUM_SIGNIFICANCE = """\
mission:
  key: test-sig-medium
  name: Test Medium Significance
  version: "1.0.0"
steps:
  - id: step-01
    title: First step
audit_steps:
  - id: audit-01
    title: Medium-impact check
    depends_on: ["step-01"]
    audit:
      trigger_mode: manual
      enforcement: blocking
    significance:
      dimensions:
        architectural_system_impact: 1
        cross_team_blast_radius: 1
        data_security_compliance_impact: 1
        financial_commercial_impact: 2
        operational_reliability_impact: 2
        user_customer_impact: 2
"""

# All 6 dimensions at 3 → composite=18 → high band
AUDIT_WITH_HIGH_SIGNIFICANCE = """\
mission:
  key: test-sig-high
  name: Test High Significance
  version: "1.0.0"
steps:
  - id: step-01
    title: First step
audit_steps:
  - id: audit-01
    title: High-impact check
    depends_on: ["step-01"]
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

# Low numeric score but hard trigger → overrides to high band
AUDIT_WITH_HARD_TRIGGER = """\
mission:
  key: test-sig-hard-trigger
  name: Test Hard Trigger
  version: "1.0.0"
steps:
  - id: step-01
    title: First step
audit_steps:
  - id: audit-01
    title: Security check
    depends_on: ["step-01"]
    audit:
      trigger_mode: manual
      enforcement: blocking
    significance:
      dimensions:
        architectural_system_impact: 0
        cross_team_blast_radius: 0
        data_security_compliance_impact: 0
        financial_commercial_impact: 0
        operational_reliability_impact: 0
        user_customer_impact: 0
      hard_triggers:
        - security_privacy_access_control
"""

AUDIT_WITHOUT_SIGNIFICANCE = """\
mission:
  key: test-no-sig
  name: Test No Significance
  version: "1.0.0"
steps:
  - id: step-01
    title: First step
audit_steps:
  - id: audit-01
    title: Basic check
    depends_on: ["step-01"]
    audit:
      trigger_mode: manual
      enforcement: blocking
"""


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
    # Advance past step-01
    d1 = next_step(run_ref, agent_id="agent-01", context=context)
    assert d1.kind == "step" and d1.step_id == "step-01"

    d2 = next_step(run_ref, agent_id="agent-01", result="success", context=context)
    return run_ref, d2, context


# ============================================================================
# T021: SignificanceBlock schema tests
# ============================================================================

class TestSignificanceBlockSchema:
    def test_significance_block_valid(self) -> None:
        block = SignificanceBlock(dimensions=_all_dimensions(1))
        assert block.dimensions == _all_dimensions(1)
        assert block.hard_triggers == []

    def test_significance_block_with_hard_triggers(self) -> None:
        block = SignificanceBlock(
            dimensions=_all_dimensions(1),
            hard_triggers=["production_data_destructive"],
        )
        assert len(block.hard_triggers) == 1

    def test_significance_block_invalid_dimension(self) -> None:
        dims = _all_dimensions(1)
        dims["bogus_dimension"] = 1
        with pytest.raises(ValueError, match="unexpected"):
            SignificanceBlock(dimensions=dims)

    def test_significance_block_invalid_hard_trigger(self) -> None:
        with pytest.raises(ValueError, match="Unknown hard-trigger class"):
            SignificanceBlock(
                dimensions=_all_dimensions(1),
                hard_triggers=["nonexistent_trigger"],
            )

    def test_audit_step_without_significance(self) -> None:
        step = AuditStep(
            id="a1",
            title="Test",
            audit={"trigger_mode": "manual", "enforcement": "blocking"},
        )
        assert step.significance is None

    def test_audit_step_with_significance(self) -> None:
        step = AuditStep(
            id="a1",
            title="Test",
            audit={"trigger_mode": "manual", "enforcement": "blocking"},
            significance={"dimensions": _all_dimensions(2)},
        )
        assert step.significance is not None
        assert step.significance.dimensions == _all_dimensions(2)


# ============================================================================
# T022: next_step() significance integration
# ============================================================================

class TestNextStepLowBand:
    """LOW band: auto-proceed without human gate."""

    def test_low_band_auto_proceeds(self, tmp_path: Path) -> None:
        """LOW significance audit auto-proceeds — no decision_required."""
        run_ref, d2, context = _advance_to_audit(
            tmp_path, AUDIT_WITH_LOW_SIGNIFICANCE, "test-sig-low"
        )
        # With low significance, the audit should auto-proceed.
        # d2 should NOT be decision_required for the audit.
        # Instead it should be the next step or terminal.
        assert d2.kind != "decision_required" or d2.decision_id != "audit:audit-01"

    def test_low_band_adds_to_completed_steps(self, tmp_path: Path) -> None:
        """LOW band adds audit step to completed_steps automatically."""
        run_ref, _, _ = _advance_to_audit(
            tmp_path, AUDIT_WITH_LOW_SIGNIFICANCE, "test-sig-low"
        )
        state = _read_snapshot_raw(run_ref)
        assert "audit-01" in state["completed_steps"]

    def test_low_band_next_step_continues(self, tmp_path: Path) -> None:
        """After LOW band auto-proceed, DAG continues to next step."""
        run_ref, d2, context = _advance_to_audit(
            tmp_path, AUDIT_WITH_LOW_SIGNIFICANCE, "test-sig-low"
        )
        # step-02 depends on audit-01, which auto-proceeded
        assert d2.kind == "step"
        assert d2.step_id == "step-02"

    def test_low_band_persists_significance_score(self, tmp_path: Path) -> None:
        """Significance evaluation is persisted even for low band."""
        run_ref, _, _ = _advance_to_audit(
            tmp_path, AUDIT_WITH_LOW_SIGNIFICANCE, "test-sig-low"
        )
        state = _read_snapshot_raw(run_ref)
        assert "significance:audit:audit-01" in state["decisions"]
        sig = state["decisions"]["significance:audit:audit-01"]
        assert sig["composite"] == 0

    def test_low_band_emits_significance_event(self, tmp_path: Path) -> None:
        """SignificanceEvaluated event is emitted for low band."""
        run_ref, _, _ = _advance_to_audit(
            tmp_path, AUDIT_WITH_LOW_SIGNIFICANCE, "test-sig-low"
        )
        events = _read_events(run_ref)
        sig_events = [e for e in events if e["event_type"] == "SignificanceEvaluated"]
        assert len(sig_events) == 1
        assert sig_events[0]["payload"]["effective_band"] == "low"


class TestNextStepMediumBand:
    """MEDIUM band: soft gate with different options."""

    def test_medium_band_returns_decision_required(self, tmp_path: Path) -> None:
        """MEDIUM significance returns decision_required."""
        run_ref, d2, _ = _advance_to_audit(
            tmp_path, AUDIT_WITH_MEDIUM_SIGNIFICANCE, "test-sig-medium"
        )
        assert d2.kind == "decision_required"
        assert d2.decision_id == "audit:audit-01"

    def test_medium_band_options(self, tmp_path: Path) -> None:
        """MEDIUM band offers decide_solo, open_stand_up, defer options."""
        run_ref, d2, _ = _advance_to_audit(
            tmp_path, AUDIT_WITH_MEDIUM_SIGNIFICANCE, "test-sig-medium"
        )
        assert d2.options == ["decide_solo", "open_stand_up", "defer"]

    def test_medium_band_persists_significance_score(self, tmp_path: Path) -> None:
        """Significance score persisted for medium band."""
        run_ref, _, _ = _advance_to_audit(
            tmp_path, AUDIT_WITH_MEDIUM_SIGNIFICANCE, "test-sig-medium"
        )
        state = _read_snapshot_raw(run_ref)
        assert "significance:audit:audit-01" in state["decisions"]
        sig = state["decisions"]["significance:audit:audit-01"]
        eb = sig["effective_band"]
        band_name = eb["name"] if isinstance(eb, dict) else eb
        assert band_name == "medium"

    def test_medium_band_emits_significance_event(self, tmp_path: Path) -> None:
        """SignificanceEvaluated event emitted for medium band."""
        run_ref, _, _ = _advance_to_audit(
            tmp_path, AUDIT_WITH_MEDIUM_SIGNIFICANCE, "test-sig-medium"
        )
        events = _read_events(run_ref)
        sig_events = [e for e in events if e["event_type"] == "SignificanceEvaluated"]
        assert len(sig_events) == 1
        assert sig_events[0]["payload"]["effective_band"] == "medium"


class TestNextStepHighBand:
    """HIGH band: hard gate with approve/reject."""

    def test_high_band_returns_decision_required(self, tmp_path: Path) -> None:
        """HIGH significance returns decision_required."""
        run_ref, d2, _ = _advance_to_audit(
            tmp_path, AUDIT_WITH_HIGH_SIGNIFICANCE, "test-sig-high"
        )
        assert d2.kind == "decision_required"
        assert d2.decision_id == "audit:audit-01"

    def test_high_band_options(self, tmp_path: Path) -> None:
        """HIGH band keeps approve/reject options."""
        run_ref, d2, _ = _advance_to_audit(
            tmp_path, AUDIT_WITH_HIGH_SIGNIFICANCE, "test-sig-high"
        )
        assert d2.options == ["approve", "reject"]

    def test_high_band_persists_significance_score(self, tmp_path: Path) -> None:
        """Significance score persisted for high band."""
        run_ref, _, _ = _advance_to_audit(
            tmp_path, AUDIT_WITH_HIGH_SIGNIFICANCE, "test-sig-high"
        )
        state = _read_snapshot_raw(run_ref)
        assert "significance:audit:audit-01" in state["decisions"]
        sig = state["decisions"]["significance:audit:audit-01"]
        assert sig["composite"] == 18


class TestNextStepHardTrigger:
    """Hard-trigger overrides numeric score to HIGH."""

    def test_hard_trigger_forces_high_band(self, tmp_path: Path) -> None:
        """Hard trigger overrides low numeric score to HIGH band."""
        run_ref, d2, _ = _advance_to_audit(
            tmp_path, AUDIT_WITH_HARD_TRIGGER, "test-sig-hard-trigger"
        )
        assert d2.kind == "decision_required"
        assert d2.options == ["approve", "reject"]

    def test_hard_trigger_persists_trigger_classes(self, tmp_path: Path) -> None:
        """Hard trigger classes persisted in significance score."""
        run_ref, _, _ = _advance_to_audit(
            tmp_path, AUDIT_WITH_HARD_TRIGGER, "test-sig-hard-trigger"
        )
        state = _read_snapshot_raw(run_ref)
        sig = state["decisions"]["significance:audit:audit-01"]
        assert len(sig["hard_trigger_classes"]) == 1


class TestNextStepNoSignificance:
    """Backward compatibility: AuditStep without significance."""

    def test_no_significance_returns_decision_required(self, tmp_path: Path) -> None:
        """Without significance, blocking audit returns decision_required as before."""
        run_ref, d2, _ = _advance_to_audit(
            tmp_path, AUDIT_WITHOUT_SIGNIFICANCE, "test-no-sig"
        )
        assert d2.kind == "decision_required"
        assert d2.decision_id == "audit:audit-01"

    def test_no_significance_approve_reject_options(self, tmp_path: Path) -> None:
        """Without significance, options are approve/reject."""
        run_ref, d2, _ = _advance_to_audit(
            tmp_path, AUDIT_WITHOUT_SIGNIFICANCE, "test-no-sig"
        )
        assert d2.options == ["approve", "reject"]

    def test_no_significance_no_sig_in_decisions(self, tmp_path: Path) -> None:
        """Without significance, no significance key in decisions."""
        run_ref, _, _ = _advance_to_audit(
            tmp_path, AUDIT_WITHOUT_SIGNIFICANCE, "test-no-sig"
        )
        state = _read_snapshot_raw(run_ref)
        assert "significance:audit:audit-01" not in state["decisions"]


# ============================================================================
# T023: provide_decision_answer() significance routing
# ============================================================================

class TestProvideAnswerMediumBand:
    """Medium-band answer routing."""

    def test_decide_solo_clears_gate(self, tmp_path: Path) -> None:
        """decide_solo clears the gate like approve."""
        run_ref, _, _ = _advance_to_audit(
            tmp_path, AUDIT_WITH_MEDIUM_SIGNIFICANCE, "test-sig-medium"
        )
        provide_decision_answer(run_ref, "audit:audit-01", "decide_solo", _actor())

        state = _read_snapshot_raw(run_ref)
        assert "audit-01" in state["completed_steps"]
        assert "audit:audit-01" not in state["pending_decisions"]

    def test_decide_solo_persists_soft_gate_decision(self, tmp_path: Path) -> None:
        """decide_solo persists SoftGateDecision."""
        run_ref, _, _ = _advance_to_audit(
            tmp_path, AUDIT_WITH_MEDIUM_SIGNIFICANCE, "test-sig-medium"
        )
        provide_decision_answer(run_ref, "audit:audit-01", "decide_solo", _actor())

        state = _read_snapshot_raw(run_ref)
        assert "soft_gate:audit:audit-01" in state["decisions"]
        soft_gate = state["decisions"]["soft_gate:audit:audit-01"]
        assert soft_gate["action"] == "decide_solo"
        assert soft_gate["outcome"] == "decide_solo"

    def test_open_stand_up_keeps_gate_open(self, tmp_path: Path) -> None:
        """open_stand_up keeps the gate open (decision stays pending)."""
        run_ref, _, _ = _advance_to_audit(
            tmp_path, AUDIT_WITH_MEDIUM_SIGNIFICANCE, "test-sig-medium"
        )
        provide_decision_answer(run_ref, "audit:audit-01", "open_stand_up", _actor())

        state = _read_snapshot_raw(run_ref)
        assert "audit-01" not in state["completed_steps"]
        assert "audit:audit-01" in state["pending_decisions"]

    def test_defer_keeps_gate_open(self, tmp_path: Path) -> None:
        """defer keeps the gate open."""
        run_ref, _, _ = _advance_to_audit(
            tmp_path, AUDIT_WITH_MEDIUM_SIGNIFICANCE, "test-sig-medium"
        )
        provide_decision_answer(run_ref, "audit:audit-01", "defer", _actor())

        state = _read_snapshot_raw(run_ref)
        assert "audit-01" not in state["completed_steps"]
        assert "audit:audit-01" in state["pending_decisions"]

    def test_medium_band_rejects_approve(self, tmp_path: Path) -> None:
        """Medium band rejects 'approve' answer."""
        run_ref, _, _ = _advance_to_audit(
            tmp_path, AUDIT_WITH_MEDIUM_SIGNIFICANCE, "test-sig-medium"
        )
        with pytest.raises(MissionRuntimeError, match="Medium-band"):
            provide_decision_answer(run_ref, "audit:audit-01", "approve", _actor())

    def test_medium_band_rejects_reject(self, tmp_path: Path) -> None:
        """Medium band rejects 'reject' answer."""
        run_ref, _, _ = _advance_to_audit(
            tmp_path, AUDIT_WITH_MEDIUM_SIGNIFICANCE, "test-sig-medium"
        )
        with pytest.raises(MissionRuntimeError, match="Medium-band"):
            provide_decision_answer(run_ref, "audit:audit-01", "reject", _actor())

    def test_defer_then_decide_solo(self, tmp_path: Path) -> None:
        """After defer, can still decide_solo to clear gate."""
        run_ref, _, _ = _advance_to_audit(
            tmp_path, AUDIT_WITH_MEDIUM_SIGNIFICANCE, "test-sig-medium"
        )
        provide_decision_answer(run_ref, "audit:audit-01", "defer", _actor())
        provide_decision_answer(run_ref, "audit:audit-01", "decide_solo", _actor())

        state = _read_snapshot_raw(run_ref)
        assert "audit-01" in state["completed_steps"]
        assert "audit:audit-01" not in state["pending_decisions"]


class TestProvideAnswerHighBand:
    """High-band answer routing."""

    def test_high_band_approve_clears_gate(self, tmp_path: Path) -> None:
        """HIGH band approve works as before."""
        run_ref, _, _ = _advance_to_audit(
            tmp_path, AUDIT_WITH_HIGH_SIGNIFICANCE, "test-sig-high"
        )
        provide_decision_answer(run_ref, "audit:audit-01", "approve", _actor())

        state = _read_snapshot_raw(run_ref)
        assert "audit-01" in state["completed_steps"]

    def test_high_band_reject_blocks_run(self, tmp_path: Path) -> None:
        """HIGH band reject blocks the run."""
        run_ref, _, _ = _advance_to_audit(
            tmp_path, AUDIT_WITH_HIGH_SIGNIFICANCE, "test-sig-high"
        )
        provide_decision_answer(run_ref, "audit:audit-01", "reject", _actor())

        state = _read_snapshot_raw(run_ref)
        assert state["blocked_reason"] is not None

    def test_high_band_rejects_decide_solo(self, tmp_path: Path) -> None:
        """HIGH band rejects 'decide_solo' answer."""
        run_ref, _, _ = _advance_to_audit(
            tmp_path, AUDIT_WITH_HIGH_SIGNIFICANCE, "test-sig-high"
        )
        with pytest.raises(MissionRuntimeError, match="High-band"):
            provide_decision_answer(run_ref, "audit:audit-01", "decide_solo", _actor())


class TestProvideAnswerNoSignificance:
    """Backward compat: no significance block."""

    def test_no_significance_approve(self, tmp_path: Path) -> None:
        """Without significance, approve works as before."""
        run_ref, _, _ = _advance_to_audit(
            tmp_path, AUDIT_WITHOUT_SIGNIFICANCE, "test-no-sig"
        )
        provide_decision_answer(run_ref, "audit:audit-01", "approve", _actor())

        state = _read_snapshot_raw(run_ref)
        assert "audit-01" in state["completed_steps"]

    def test_no_significance_reject(self, tmp_path: Path) -> None:
        """Without significance, reject works as before."""
        run_ref, _, _ = _advance_to_audit(
            tmp_path, AUDIT_WITHOUT_SIGNIFICANCE, "test-no-sig"
        )
        provide_decision_answer(run_ref, "audit:audit-01", "reject", _actor())

        state = _read_snapshot_raw(run_ref)
        assert state["blocked_reason"] is not None

    def test_no_significance_invalid_answer(self, tmp_path: Path) -> None:
        """Without significance, invalid answers still rejected."""
        run_ref, _, _ = _advance_to_audit(
            tmp_path, AUDIT_WITHOUT_SIGNIFICANCE, "test-no-sig"
        )
        with pytest.raises(MissionRuntimeError, match="Invalid audit answer"):
            provide_decision_answer(run_ref, "audit:audit-01", "decide_solo", _actor())


# ============================================================================
# T024: Persistence verification
# ============================================================================

class TestPersistenceKeys:
    """Verify all significance-related keys in decisions dict."""

    def test_significance_key_format(self, tmp_path: Path) -> None:
        """significance:audit:{step_id} key present."""
        run_ref, _, _ = _advance_to_audit(
            tmp_path, AUDIT_WITH_MEDIUM_SIGNIFICANCE, "test-sig-medium"
        )
        state = _read_snapshot_raw(run_ref)
        assert "significance:audit:audit-01" in state["decisions"]

    def test_raci_key_for_significance_step(self, tmp_path: Path) -> None:
        """RACI binding resolved for significance audit step."""
        run_ref, _, _ = _advance_to_audit(
            tmp_path, AUDIT_WITH_MEDIUM_SIGNIFICANCE, "test-sig-medium"
        )
        state = _read_snapshot_raw(run_ref)
        assert "raci:audit-01" in state["decisions"]

    def test_soft_gate_key_format(self, tmp_path: Path) -> None:
        """soft_gate:audit:{step_id} key present after medium-band answer."""
        run_ref, _, _ = _advance_to_audit(
            tmp_path, AUDIT_WITH_MEDIUM_SIGNIFICANCE, "test-sig-medium"
        )
        provide_decision_answer(run_ref, "audit:audit-01", "decide_solo", _actor())

        state = _read_snapshot_raw(run_ref)
        assert "soft_gate:audit:audit-01" in state["decisions"]

    def test_significance_score_serialization(self, tmp_path: Path) -> None:
        """Significance score is JSON-serializable dict."""
        run_ref, _, _ = _advance_to_audit(
            tmp_path, AUDIT_WITH_HIGH_SIGNIFICANCE, "test-sig-high"
        )
        state = _read_snapshot_raw(run_ref)
        sig = state["decisions"]["significance:audit:audit-01"]
        assert isinstance(sig, dict)
        assert "composite" in sig
        assert "band" in sig
        assert "effective_band" in sig
        assert "dimensions" in sig


# ============================================================================
# T025: Public API re-exports
# ============================================================================

class TestPublicAPIExports:
    """Verify all significance types importable from spec_kitty_runtime."""

    def test_import_models(self) -> None:
        from spec_kitty_runtime import (
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
            SignificanceBlock,
        )
        # Verify they're actual classes
        assert SignificanceDimension is not None
        assert SignificanceScore is not None
        assert SignificanceBlock is not None

    def test_import_functions(self) -> None:
        from spec_kitty_runtime import (
            evaluate_significance,
            compute_escalation_targets,
            validate_band_cutoffs,
            validate_dimension_scores,
            parse_band_cutoffs_from_policy,
            parse_timeout_from_policy,
            resolve_hard_triggers,
        )
        assert callable(evaluate_significance)
        assert callable(parse_band_cutoffs_from_policy)

    def test_import_constants(self) -> None:
        from spec_kitty_runtime import (
            DIMENSION_NAMES,
            HARD_TRIGGER_REGISTRY,
            DEFAULT_BANDS,
        )
        assert len(DIMENSION_NAMES) == 6
        assert len(HARD_TRIGGER_REGISTRY) == 5
        assert len(DEFAULT_BANDS) == 3

    def test_import_notify_decision_timeout(self) -> None:
        from spec_kitty_runtime import notify_decision_timeout
        assert callable(notify_decision_timeout)

"""Tests for WP03 – Event Payloads & Decision Models.

Covers:
- T011: SignificanceEvaluatedPayload
- T012: TimeoutExpiredPayload
- T013: SoftGateDecision
- T014: DimensionScoreOverride
- T015: RuntimeEventEmitter protocol extension
- T016: NullEmitter no-op implementations
"""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from spec_kitty_runtime.events import NullEmitter, RuntimeEventEmitter
from spec_kitty_runtime.schema import RACIRoleBinding
from spec_kitty_runtime.significance import (
    DEFAULT_BANDS,
    DIMENSION_NAMES,
    DimensionScoreOverride,
    SignificanceEvaluatedPayload,
    SignificanceScore,
    SoftGateDecision,
    TimeoutExpiredPayload,
    evaluate_significance,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _human_actor() -> RACIRoleBinding:
    return RACIRoleBinding(actor_type="human", actor_id="user-1")


def _service_actor() -> RACIRoleBinding:
    return RACIRoleBinding(actor_type="service", actor_id="runtime")


def _llm_actor() -> RACIRoleBinding:
    return RACIRoleBinding(actor_type="llm", actor_id="gpt-5")


def _all_zero_scores() -> dict[str, int]:
    return {name: 0 for name in sorted(DIMENSION_NAMES)}


def _medium_scores() -> dict[str, int]:
    """Scores that sum to 8 → medium band."""
    names = sorted(DIMENSION_NAMES)
    scores = {name: 1 for name in names}
    # bump two to 2 to reach 8
    scores[names[0]] = 2
    scores[names[1]] = 2
    return scores


def _make_significance_score() -> SignificanceScore:
    return evaluate_significance(_medium_scores())


def _serialized_significance_score() -> dict:
    return _make_significance_score().model_dump()


# ---------------------------------------------------------------------------
# T011: SignificanceEvaluatedPayload
# ---------------------------------------------------------------------------

class TestSignificanceEvaluatedPayload:
    """Tests for SignificanceEvaluatedPayload model."""

    def test_valid_payload(self) -> None:
        payload = SignificanceEvaluatedPayload(
            run_id="run-1",
            decision_id="dec-1",
            step_id="step-1",
            significance_score=_serialized_significance_score(),
            hard_trigger_classes=(),
            effective_band="medium",
            actor=_service_actor(),
        )
        assert payload.run_id == "run-1"
        assert payload.decision_id == "dec-1"
        assert payload.step_id == "step-1"
        assert payload.effective_band == "medium"
        assert payload.hard_trigger_classes == ()
        assert payload.actor.actor_type == "service"

    def test_with_hard_triggers(self) -> None:
        payload = SignificanceEvaluatedPayload(
            run_id="run-1",
            decision_id="dec-1",
            step_id="step-1",
            significance_score=_serialized_significance_score(),
            hard_trigger_classes=("production_data_destructive",),
            effective_band="high",
            actor=_service_actor(),
        )
        assert payload.hard_trigger_classes == ("production_data_destructive",)
        assert payload.effective_band == "high"

    def test_frozen(self) -> None:
        payload = SignificanceEvaluatedPayload(
            run_id="run-1",
            decision_id="dec-1",
            step_id="step-1",
            significance_score={},
            effective_band="low",
            actor=_service_actor(),
        )
        with pytest.raises(ValidationError):
            payload.run_id = "changed"  # type: ignore[misc]

    def test_extra_fields_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            SignificanceEvaluatedPayload(
                run_id="run-1",
                decision_id="dec-1",
                step_id="step-1",
                significance_score={},
                effective_band="low",
                actor=_service_actor(),
                extra_field="not allowed",  # type: ignore[call-arg]
            )

    def test_empty_run_id_rejected(self) -> None:
        with pytest.raises(ValidationError):
            SignificanceEvaluatedPayload(
                run_id="",
                decision_id="dec-1",
                step_id="step-1",
                significance_score={},
                effective_band="low",
                actor=_service_actor(),
            )

    def test_empty_decision_id_rejected(self) -> None:
        with pytest.raises(ValidationError):
            SignificanceEvaluatedPayload(
                run_id="run-1",
                decision_id="",
                step_id="step-1",
                significance_score={},
                effective_band="low",
                actor=_service_actor(),
            )

    def test_empty_step_id_rejected(self) -> None:
        with pytest.raises(ValidationError):
            SignificanceEvaluatedPayload(
                run_id="run-1",
                decision_id="dec-1",
                step_id="",
                significance_score={},
                effective_band="low",
                actor=_service_actor(),
            )

    def test_invalid_band_rejected(self) -> None:
        with pytest.raises(ValidationError):
            SignificanceEvaluatedPayload(
                run_id="run-1",
                decision_id="dec-1",
                step_id="step-1",
                significance_score={},
                effective_band="ultra",  # type: ignore[arg-type]
                actor=_service_actor(),
            )

    def test_default_hard_trigger_classes(self) -> None:
        payload = SignificanceEvaluatedPayload(
            run_id="run-1",
            decision_id="dec-1",
            step_id="step-1",
            significance_score={},
            effective_band="low",
            actor=_service_actor(),
        )
        assert payload.hard_trigger_classes == ()

    def test_serialization_roundtrip(self) -> None:
        payload = SignificanceEvaluatedPayload(
            run_id="run-1",
            decision_id="dec-1",
            step_id="step-1",
            significance_score=_serialized_significance_score(),
            hard_trigger_classes=("security_privacy_access_control",),
            effective_band="high",
            actor=_service_actor(),
        )
        data = payload.model_dump()
        restored = SignificanceEvaluatedPayload.model_validate(data)
        assert restored == payload


# ---------------------------------------------------------------------------
# T012: TimeoutExpiredPayload
# ---------------------------------------------------------------------------

class TestTimeoutExpiredPayload:
    """Tests for TimeoutExpiredPayload model."""

    def test_valid_payload(self) -> None:
        payload = TimeoutExpiredPayload(
            run_id="run-1",
            decision_id="dec-1",
            step_id="step-1",
            significance_score=_serialized_significance_score(),
            effective_band="medium",
            timeout_configured_seconds=600,
            escalation_targets=(_human_actor(),),
            raci_snapshot={"step_id": "step-1", "responsible": {"actor_type": "human"}},
            actor=_service_actor(),
        )
        assert payload.timeout_configured_seconds == 600
        assert payload.effective_band == "medium"
        assert len(payload.escalation_targets) == 1

    def test_high_band_valid(self) -> None:
        payload = TimeoutExpiredPayload(
            run_id="run-1",
            decision_id="dec-1",
            step_id="step-1",
            significance_score={},
            effective_band="high",
            timeout_configured_seconds=300,
            raci_snapshot={},
            actor=_service_actor(),
        )
        assert payload.effective_band == "high"

    def test_low_band_rejected(self) -> None:
        """Low-band decisions auto-proceed and never timeout."""
        with pytest.raises(ValidationError):
            TimeoutExpiredPayload(
                run_id="run-1",
                decision_id="dec-1",
                step_id="step-1",
                significance_score={},
                effective_band="low",  # type: ignore[arg-type]
                timeout_configured_seconds=600,
                raci_snapshot={},
                actor=_service_actor(),
            )

    def test_zero_timeout_rejected(self) -> None:
        with pytest.raises(ValidationError):
            TimeoutExpiredPayload(
                run_id="run-1",
                decision_id="dec-1",
                step_id="step-1",
                significance_score={},
                effective_band="medium",
                timeout_configured_seconds=0,
                raci_snapshot={},
                actor=_service_actor(),
            )

    def test_negative_timeout_rejected(self) -> None:
        with pytest.raises(ValidationError):
            TimeoutExpiredPayload(
                run_id="run-1",
                decision_id="dec-1",
                step_id="step-1",
                significance_score={},
                effective_band="medium",
                timeout_configured_seconds=-1,
                raci_snapshot={},
                actor=_service_actor(),
            )

    def test_frozen(self) -> None:
        payload = TimeoutExpiredPayload(
            run_id="run-1",
            decision_id="dec-1",
            step_id="step-1",
            significance_score={},
            effective_band="medium",
            timeout_configured_seconds=600,
            raci_snapshot={},
            actor=_service_actor(),
        )
        with pytest.raises(ValidationError):
            payload.timeout_configured_seconds = 999  # type: ignore[misc]

    def test_extra_fields_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            TimeoutExpiredPayload(
                run_id="run-1",
                decision_id="dec-1",
                step_id="step-1",
                significance_score={},
                effective_band="medium",
                timeout_configured_seconds=600,
                raci_snapshot={},
                actor=_service_actor(),
                bogus="nope",  # type: ignore[call-arg]
            )

    def test_default_escalation_targets(self) -> None:
        payload = TimeoutExpiredPayload(
            run_id="run-1",
            decision_id="dec-1",
            step_id="step-1",
            significance_score={},
            effective_band="medium",
            timeout_configured_seconds=600,
            raci_snapshot={},
            actor=_service_actor(),
        )
        assert payload.escalation_targets == ()

    def test_serialization_roundtrip(self) -> None:
        payload = TimeoutExpiredPayload(
            run_id="run-1",
            decision_id="dec-1",
            step_id="step-1",
            significance_score=_serialized_significance_score(),
            effective_band="high",
            timeout_configured_seconds=300,
            escalation_targets=(_human_actor(),),
            raci_snapshot={"step_id": "step-1"},
            actor=_service_actor(),
        )
        data = payload.model_dump()
        restored = TimeoutExpiredPayload.model_validate(data)
        assert restored == payload


# ---------------------------------------------------------------------------
# T013: SoftGateDecision
# ---------------------------------------------------------------------------

class TestSoftGateDecision:
    """Tests for SoftGateDecision model."""

    def test_valid_decide_solo(self) -> None:
        decision = SoftGateDecision(
            decision_id="dec-1",
            action="decide_solo",
            actor=_human_actor(),
            timestamp=datetime(2026, 2, 27, tzinfo=timezone.utc),
            significance_score=_make_significance_score(),
        )
        assert decision.action == "decide_solo"
        assert decision.outcome is None
        assert decision.rationale is None
        assert decision.participants == ()

    def test_valid_open_stand_up(self) -> None:
        decision = SoftGateDecision(
            decision_id="dec-1",
            action="open_stand_up",
            actor=_human_actor(),
            timestamp=datetime(2026, 2, 27, tzinfo=timezone.utc),
            significance_score=_make_significance_score(),
            participants=(_human_actor(), _human_actor()),
        )
        assert decision.action == "open_stand_up"
        assert len(decision.participants) == 2

    def test_valid_defer(self) -> None:
        decision = SoftGateDecision(
            decision_id="dec-1",
            action="defer",
            actor=_human_actor(),
            timestamp=datetime(2026, 2, 27, tzinfo=timezone.utc),
            significance_score=_make_significance_score(),
            rationale="Need more data",
        )
        assert decision.action == "defer"
        assert decision.rationale == "Need more data"

    def test_with_outcome(self) -> None:
        decision = SoftGateDecision(
            decision_id="dec-1",
            action="decide_solo",
            actor=_human_actor(),
            timestamp=datetime(2026, 2, 27, tzinfo=timezone.utc),
            significance_score=_make_significance_score(),
            outcome="approve",
        )
        assert decision.outcome == "approve"

    def test_non_human_actor_rejected(self) -> None:
        """FR-018: only humans can make soft-gate decisions."""
        with pytest.raises(ValidationError, match="actor must be human"):
            SoftGateDecision(
                decision_id="dec-1",
                action="decide_solo",
                actor=_service_actor(),
                timestamp=datetime(2026, 2, 27, tzinfo=timezone.utc),
                significance_score=_make_significance_score(),
            )

    def test_llm_actor_rejected(self) -> None:
        with pytest.raises(ValidationError, match="actor must be human"):
            SoftGateDecision(
                decision_id="dec-1",
                action="decide_solo",
                actor=_llm_actor(),
                timestamp=datetime(2026, 2, 27, tzinfo=timezone.utc),
                significance_score=_make_significance_score(),
            )

    def test_invalid_action_rejected(self) -> None:
        with pytest.raises(ValidationError):
            SoftGateDecision(
                decision_id="dec-1",
                action="invalid_action",  # type: ignore[arg-type]
                actor=_human_actor(),
                timestamp=datetime(2026, 2, 27, tzinfo=timezone.utc),
                significance_score=_make_significance_score(),
            )

    def test_empty_decision_id_rejected(self) -> None:
        with pytest.raises(ValidationError):
            SoftGateDecision(
                decision_id="",
                action="decide_solo",
                actor=_human_actor(),
                timestamp=datetime(2026, 2, 27, tzinfo=timezone.utc),
                significance_score=_make_significance_score(),
            )

    def test_frozen(self) -> None:
        decision = SoftGateDecision(
            decision_id="dec-1",
            action="decide_solo",
            actor=_human_actor(),
            timestamp=datetime(2026, 2, 27, tzinfo=timezone.utc),
            significance_score=_make_significance_score(),
        )
        with pytest.raises(ValidationError):
            decision.action = "defer"  # type: ignore[misc]

    def test_extra_fields_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            SoftGateDecision(
                decision_id="dec-1",
                action="decide_solo",
                actor=_human_actor(),
                timestamp=datetime(2026, 2, 27, tzinfo=timezone.utc),
                significance_score=_make_significance_score(),
                extra="nope",  # type: ignore[call-arg]
            )

    def test_serialization_roundtrip(self) -> None:
        decision = SoftGateDecision(
            decision_id="dec-1",
            action="open_stand_up",
            actor=_human_actor(),
            timestamp=datetime(2026, 2, 27, tzinfo=timezone.utc),
            significance_score=_make_significance_score(),
            participants=(_human_actor(),),
            outcome="approve",
            rationale="Team consensus",
        )
        data = decision.model_dump()
        restored = SoftGateDecision.model_validate(data)
        assert restored == decision


# ---------------------------------------------------------------------------
# T014: DimensionScoreOverride
# ---------------------------------------------------------------------------

class TestDimensionScoreOverride:
    """Tests for DimensionScoreOverride model."""

    def test_valid_override(self) -> None:
        override = DimensionScoreOverride(
            decision_id="dec-1",
            overridden_by=_human_actor(),
            override_reason="Customer escalation requires higher impact score",
            original_scores={"user_customer_impact": 1},
            new_scores={"user_customer_impact": 3},
            override_timestamp=datetime(2026, 2, 27, tzinfo=timezone.utc),
        )
        assert override.original_scores["user_customer_impact"] == 1
        assert override.new_scores["user_customer_impact"] == 3

    def test_multiple_dimensions(self) -> None:
        override = DimensionScoreOverride(
            decision_id="dec-1",
            overridden_by=_human_actor(),
            override_reason="Re-evaluated multiple dimensions",
            original_scores={
                "user_customer_impact": 1,
                "financial_commercial_impact": 0,
            },
            new_scores={
                "user_customer_impact": 3,
                "financial_commercial_impact": 2,
            },
            override_timestamp=datetime(2026, 2, 27, tzinfo=timezone.utc),
        )
        assert len(override.original_scores) == 2
        assert len(override.new_scores) == 2

    def test_non_human_actor_rejected(self) -> None:
        """FR-018: only humans can override scores."""
        with pytest.raises(ValidationError, match="human actors"):
            DimensionScoreOverride(
                decision_id="dec-1",
                overridden_by=_service_actor(),
                override_reason="Some reason",
                original_scores={"user_customer_impact": 1},
                new_scores={"user_customer_impact": 3},
                override_timestamp=datetime(2026, 2, 27, tzinfo=timezone.utc),
            )

    def test_llm_actor_rejected(self) -> None:
        with pytest.raises(ValidationError, match="human actors"):
            DimensionScoreOverride(
                decision_id="dec-1",
                overridden_by=_llm_actor(),
                override_reason="Some reason",
                original_scores={"user_customer_impact": 1},
                new_scores={"user_customer_impact": 3},
                override_timestamp=datetime(2026, 2, 27, tzinfo=timezone.utc),
            )

    def test_unknown_dimension_in_original_rejected(self) -> None:
        with pytest.raises(ValidationError, match="Unknown dimension"):
            DimensionScoreOverride(
                decision_id="dec-1",
                overridden_by=_human_actor(),
                override_reason="Some reason",
                original_scores={"nonexistent_dimension": 1},
                new_scores={"user_customer_impact": 3},
                override_timestamp=datetime(2026, 2, 27, tzinfo=timezone.utc),
            )

    def test_unknown_dimension_in_new_rejected(self) -> None:
        with pytest.raises(ValidationError, match="Unknown dimension"):
            DimensionScoreOverride(
                decision_id="dec-1",
                overridden_by=_human_actor(),
                override_reason="Some reason",
                original_scores={"user_customer_impact": 1},
                new_scores={"bogus_dimension": 3},
                override_timestamp=datetime(2026, 2, 27, tzinfo=timezone.utc),
            )

    def test_empty_override_reason_rejected(self) -> None:
        with pytest.raises(ValidationError):
            DimensionScoreOverride(
                decision_id="dec-1",
                overridden_by=_human_actor(),
                override_reason="",
                original_scores={"user_customer_impact": 1},
                new_scores={"user_customer_impact": 3},
                override_timestamp=datetime(2026, 2, 27, tzinfo=timezone.utc),
            )

    def test_empty_decision_id_rejected(self) -> None:
        with pytest.raises(ValidationError):
            DimensionScoreOverride(
                decision_id="",
                overridden_by=_human_actor(),
                override_reason="Some reason",
                original_scores={"user_customer_impact": 1},
                new_scores={"user_customer_impact": 3},
                override_timestamp=datetime(2026, 2, 27, tzinfo=timezone.utc),
            )

    def test_sparse_dict_allowed(self) -> None:
        """Only changed dimensions need to appear (sparse dict, not full 6)."""
        override = DimensionScoreOverride(
            decision_id="dec-1",
            overridden_by=_human_actor(),
            override_reason="Single dimension update",
            original_scores={"cross_team_blast_radius": 0},
            new_scores={"cross_team_blast_radius": 2},
            override_timestamp=datetime(2026, 2, 27, tzinfo=timezone.utc),
        )
        assert len(override.original_scores) == 1
        assert len(override.new_scores) == 1

    def test_frozen(self) -> None:
        override = DimensionScoreOverride(
            decision_id="dec-1",
            overridden_by=_human_actor(),
            override_reason="Reason",
            original_scores={"user_customer_impact": 1},
            new_scores={"user_customer_impact": 3},
            override_timestamp=datetime(2026, 2, 27, tzinfo=timezone.utc),
        )
        with pytest.raises(ValidationError):
            override.override_reason = "new"  # type: ignore[misc]

    def test_extra_fields_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            DimensionScoreOverride(
                decision_id="dec-1",
                overridden_by=_human_actor(),
                override_reason="Reason",
                original_scores={"user_customer_impact": 1},
                new_scores={"user_customer_impact": 3},
                override_timestamp=datetime(2026, 2, 27, tzinfo=timezone.utc),
                extra_field="nope",  # type: ignore[call-arg]
            )

    def test_serialization_roundtrip(self) -> None:
        override = DimensionScoreOverride(
            decision_id="dec-1",
            overridden_by=_human_actor(),
            override_reason="Customer escalation",
            original_scores={"user_customer_impact": 1, "financial_commercial_impact": 0},
            new_scores={"user_customer_impact": 3, "financial_commercial_impact": 2},
            override_timestamp=datetime(2026, 2, 27, tzinfo=timezone.utc),
        )
        data = override.model_dump()
        restored = DimensionScoreOverride.model_validate(data)
        assert restored == override


# ---------------------------------------------------------------------------
# T015 & T016: RuntimeEventEmitter protocol + NullEmitter extensions
# ---------------------------------------------------------------------------

class TestRuntimeEventEmitterExtension:
    """Tests for RuntimeEventEmitter protocol extension and NullEmitter no-ops."""

    def test_null_emitter_has_significance_evaluated(self) -> None:
        emitter = NullEmitter()
        payload = SignificanceEvaluatedPayload(
            run_id="run-1",
            decision_id="dec-1",
            step_id="step-1",
            significance_score={},
            effective_band="low",
            actor=_service_actor(),
        )
        # Should not raise
        emitter.emit_significance_evaluated(payload)

    def test_null_emitter_has_decision_timeout_expired(self) -> None:
        emitter = NullEmitter()
        payload = TimeoutExpiredPayload(
            run_id="run-1",
            decision_id="dec-1",
            step_id="step-1",
            significance_score={},
            effective_band="medium",
            timeout_configured_seconds=600,
            raci_snapshot={},
            actor=_service_actor(),
        )
        # Should not raise
        emitter.emit_decision_timeout_expired(payload)

    def test_null_emitter_satisfies_protocol(self) -> None:
        """NullEmitter is structurally compatible with RuntimeEventEmitter."""
        emitter = NullEmitter()
        # Protocol structural check: all required methods exist
        assert hasattr(emitter, "emit_significance_evaluated")
        assert hasattr(emitter, "emit_decision_timeout_expired")
        assert callable(emitter.emit_significance_evaluated)
        assert callable(emitter.emit_decision_timeout_expired)

    def test_protocol_has_new_methods(self) -> None:
        """RuntimeEventEmitter protocol declares the two new emit methods."""
        # Check protocol has the methods defined
        assert hasattr(RuntimeEventEmitter, "emit_significance_evaluated")
        assert hasattr(RuntimeEventEmitter, "emit_decision_timeout_expired")

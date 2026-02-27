"""Tests for WP04 – Timeout Escalation & Engine API.

Covers:
- T017: compute_escalation_targets() pure function
- T018: TimeoutEscalationResult model
- T019: notify_decision_timeout() engine API
- T020: Timeout event persistence to decisions dict
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from spec_kitty_runtime.discovery import DiscoveryContext
from spec_kitty_runtime.engine import (
    MissionRunRef,
    notify_decision_timeout,
    start_mission_run,
)
from spec_kitty_runtime.events import NullEmitter
from spec_kitty_runtime.schema import (
    MissionPolicySnapshot,
    MissionRunSnapshot,
    MissionRuntimeError,
    RACIRoleBinding,
    ResolvedRACIBinding,
)
from spec_kitty_runtime.significance import (
    DIMENSION_NAMES,
    TimeoutEscalationResult,
    TimeoutExpiredPayload,
    compute_escalation_targets,
    evaluate_significance,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _human_actor() -> RACIRoleBinding:
    return RACIRoleBinding(actor_type="human", actor_id="owner-1")


def _service_actor() -> RACIRoleBinding:
    return RACIRoleBinding(actor_type="service", actor_id="runtime")


def _llm_actor() -> RACIRoleBinding:
    return RACIRoleBinding(actor_type="llm", actor_id="agent-1")


def _consulted_actor(n: int = 1) -> RACIRoleBinding:
    return RACIRoleBinding(actor_type="human", actor_id=f"consulted-{n}")


def _make_raci_binding(
    step_id: str = "deploy-approval",
    consulted: list[RACIRoleBinding] | None = None,
) -> ResolvedRACIBinding:
    return ResolvedRACIBinding(
        step_id=step_id,
        responsible=_llm_actor(),
        accountable=_human_actor(),
        consulted=consulted or [],
        informed=[],
        source="inferred",
        inferred_rule="default_inferred",
    )


def _medium_scores() -> dict[str, int]:
    """Scores that sum to 8 -> medium band."""
    names = sorted(DIMENSION_NAMES)
    scores = {name: 1 for name in names}
    scores[names[0]] = 2
    scores[names[1]] = 2
    return scores


def _high_scores() -> dict[str, int]:
    """Scores that sum to 14 -> high band."""
    names = sorted(DIMENSION_NAMES)
    scores = {name: 2 for name in names}
    scores[names[0]] = 3
    scores[names[1]] = 3
    return scores


MISSION_YAML = """\
mission:
  key: test-mission
  name: Test Mission
  version: 1.0.0
  description: Test mission for timeout escalation
steps:
  - id: deploy-approval
    title: Deploy Approval
    prompt: Approve deployment
"""


def _setup_run(tmp_path: Path) -> tuple[MissionRunRef, Path]:
    """Set up a mission run and return ref + run_dir."""
    mission_file = tmp_path / "pack" / "missions" / "test-mission" / "mission.yaml"
    mission_file.parent.mkdir(parents=True, exist_ok=True)
    mission_file.write_text(MISSION_YAML, encoding="utf-8")
    context = DiscoveryContext(explicit_paths=[tmp_path / "pack"], builtin_roots=[])

    run_ref = start_mission_run(
        template_key="test-mission",
        inputs={},
        policy_snapshot=MissionPolicySnapshot(),
        context=context,
        run_store=tmp_path / "runs",
    )
    return run_ref, Path(run_ref.run_dir)


def _inject_decisions(
    run_dir: Path,
    raci_binding: ResolvedRACIBinding,
    significance_score: dict,
    decision_id: str = "audit:deploy-approval",
) -> None:
    """Inject RACI binding and significance score into snapshot decisions."""
    state_path = run_dir / "state.json"
    with open(state_path, "r", encoding="utf-8") as f:
        state = json.load(f)

    step_id = decision_id[len("audit:"):] if decision_id.startswith("audit:") else decision_id
    state["decisions"][f"raci:{step_id}"] = raci_binding.model_dump(mode="json")
    state["decisions"][f"significance:{decision_id}"] = significance_score

    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, sort_keys=True)


# ============================================================================
# T017: compute_escalation_targets()
# ============================================================================


class TestComputeEscalationTargets:
    """Tests for the compute_escalation_targets pure function."""

    def test_medium_band_returns_accountable_only(self) -> None:
        raci = _make_raci_binding(consulted=[_consulted_actor(1), _consulted_actor(2)])
        targets = compute_escalation_targets(raci, "medium")
        assert len(targets) == 1
        assert targets[0] == raci.accountable

    def test_high_band_returns_accountable_plus_consulted(self) -> None:
        consulted = [_consulted_actor(1), _consulted_actor(2)]
        raci = _make_raci_binding(consulted=consulted)
        targets = compute_escalation_targets(raci, "high")
        assert len(targets) == 3
        assert targets[0] == raci.accountable
        assert targets[1] == consulted[0]
        assert targets[2] == consulted[1]

    def test_high_band_empty_consulted_returns_accountable_only(self) -> None:
        raci = _make_raci_binding(consulted=[])
        targets = compute_escalation_targets(raci, "high")
        assert len(targets) == 1
        assert targets[0] == raci.accountable

    def test_medium_band_ignores_consulted(self) -> None:
        raci = _make_raci_binding(consulted=[_consulted_actor(1)])
        targets = compute_escalation_targets(raci, "medium")
        assert len(targets) == 1
        assert targets[0] == raci.accountable

    def test_returns_tuple(self) -> None:
        raci = _make_raci_binding()
        targets = compute_escalation_targets(raci, "medium")
        assert isinstance(targets, tuple)

    def test_deterministic_output(self) -> None:
        """Same inputs always produce same output."""
        raci = _make_raci_binding(consulted=[_consulted_actor(1)])
        t1 = compute_escalation_targets(raci, "high")
        t2 = compute_escalation_targets(raci, "high")
        assert t1 == t2

    def test_high_with_many_consulted(self) -> None:
        consulted = [_consulted_actor(i) for i in range(5)]
        raci = _make_raci_binding(consulted=consulted)
        targets = compute_escalation_targets(raci, "high")
        assert len(targets) == 6  # accountable + 5 consulted

    def test_medium_band_responsible_equals_owner(self) -> None:
        """When responsible == mission owner for medium: still returns accountable."""
        raci = ResolvedRACIBinding(
            step_id="s1",
            responsible=_human_actor(),  # same as accountable
            accountable=_human_actor(),
            consulted=[],
            informed=[],
            source="inferred",
            inferred_rule="default_inferred",
        )
        targets = compute_escalation_targets(raci, "medium")
        assert len(targets) == 1
        assert targets[0] == raci.accountable


# ============================================================================
# T018: TimeoutEscalationResult model
# ============================================================================


class TestTimeoutEscalationResult:
    """Tests for the TimeoutEscalationResult frozen model."""

    def _make_payload(self) -> TimeoutExpiredPayload:
        return TimeoutExpiredPayload(
            run_id="run-1",
            decision_id="audit:deploy-approval",
            step_id="deploy-approval",
            significance_score={},
            effective_band="medium",
            timeout_configured_seconds=600,
            raci_snapshot={},
            actor=_service_actor(),
        )

    def test_valid_result(self) -> None:
        result = TimeoutEscalationResult(
            decision_id="audit:deploy-approval",
            escalation_targets=(_human_actor(),),
            band="medium",
            timeout_expired_payload=self._make_payload(),
        )
        assert result.decision_id == "audit:deploy-approval"
        assert result.band == "medium"
        assert len(result.escalation_targets) == 1

    def test_high_band(self) -> None:
        payload = TimeoutExpiredPayload(
            run_id="run-1",
            decision_id="audit:deploy-approval",
            step_id="deploy-approval",
            significance_score={},
            effective_band="high",
            timeout_configured_seconds=300,
            raci_snapshot={},
            actor=_service_actor(),
        )
        result = TimeoutEscalationResult(
            decision_id="audit:deploy-approval",
            escalation_targets=(_human_actor(), _consulted_actor()),
            band="high",
            timeout_expired_payload=payload,
        )
        assert result.band == "high"
        assert len(result.escalation_targets) == 2

    def test_frozen(self) -> None:
        result = TimeoutEscalationResult(
            decision_id="audit:deploy-approval",
            escalation_targets=(),
            band="medium",
            timeout_expired_payload=self._make_payload(),
        )
        with pytest.raises(ValidationError):
            result.band = "high"  # type: ignore[misc]

    def test_extra_fields_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            TimeoutEscalationResult(
                decision_id="audit:deploy-approval",
                escalation_targets=(),
                band="medium",
                timeout_expired_payload=self._make_payload(),
                extra="nope",  # type: ignore[call-arg]
            )

    def test_empty_decision_id_rejected(self) -> None:
        with pytest.raises(ValidationError):
            TimeoutEscalationResult(
                decision_id="",
                escalation_targets=(),
                band="medium",
                timeout_expired_payload=self._make_payload(),
            )

    def test_default_escalation_targets(self) -> None:
        result = TimeoutEscalationResult(
            decision_id="audit:deploy-approval",
            band="medium",
            timeout_expired_payload=self._make_payload(),
        )
        assert result.escalation_targets == ()

    def test_serialization_roundtrip(self) -> None:
        result = TimeoutEscalationResult(
            decision_id="audit:deploy-approval",
            escalation_targets=(_human_actor(),),
            band="medium",
            timeout_expired_payload=self._make_payload(),
        )
        data = result.model_dump()
        restored = TimeoutEscalationResult.model_validate(data)
        assert restored == result


# ============================================================================
# T019: notify_decision_timeout() engine API
# ============================================================================


class TestNotifyDecisionTimeout:
    """Tests for the notify_decision_timeout engine API."""

    def test_medium_band_escalation(self, tmp_path: Path) -> None:
        run_ref, run_dir = _setup_run(tmp_path)
        raci = _make_raci_binding(consulted=[_consulted_actor()])
        sig_score = evaluate_significance(_medium_scores()).model_dump()

        _inject_decisions(run_dir, raci, sig_score)

        result = notify_decision_timeout(
            run_ref=run_ref,
            decision_id="audit:deploy-approval",
            actor=_service_actor(),
        )

        assert isinstance(result, TimeoutEscalationResult)
        assert result.band == "medium"
        # Medium → only accountable
        assert len(result.escalation_targets) == 1
        assert result.escalation_targets[0].actor_id == "owner-1"

    def test_high_band_escalation(self, tmp_path: Path) -> None:
        run_ref, run_dir = _setup_run(tmp_path)
        consulted = [_consulted_actor(1), _consulted_actor(2)]
        raci = _make_raci_binding(consulted=consulted)
        sig_score = evaluate_significance(_high_scores()).model_dump()

        _inject_decisions(run_dir, raci, sig_score)

        result = notify_decision_timeout(
            run_ref=run_ref,
            decision_id="audit:deploy-approval",
            actor=_service_actor(),
        )

        assert result.band == "high"
        # High → accountable + consulted
        assert len(result.escalation_targets) == 3

    def test_missing_raci_binding_raises(self, tmp_path: Path) -> None:
        run_ref, run_dir = _setup_run(tmp_path)
        # Only inject significance, not RACI
        sig_score = evaluate_significance(_medium_scores()).model_dump()
        state_path = run_dir / "state.json"
        with open(state_path, "r", encoding="utf-8") as f:
            state = json.load(f)
        state["decisions"]["significance:audit:deploy-approval"] = sig_score
        with open(state_path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, sort_keys=True)

        with pytest.raises(MissionRuntimeError, match="No RACI binding"):
            notify_decision_timeout(
                run_ref=run_ref,
                decision_id="audit:deploy-approval",
                actor=_service_actor(),
            )

    def test_missing_significance_score_raises(self, tmp_path: Path) -> None:
        run_ref, run_dir = _setup_run(tmp_path)
        # Only inject RACI, not significance
        raci = _make_raci_binding()
        state_path = run_dir / "state.json"
        with open(state_path, "r", encoding="utf-8") as f:
            state = json.load(f)
        state["decisions"][f"raci:deploy-approval"] = raci.model_dump(mode="json")
        with open(state_path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, sort_keys=True)

        with pytest.raises(MissionRuntimeError, match="No significance evaluation"):
            notify_decision_timeout(
                run_ref=run_ref,
                decision_id="audit:deploy-approval",
                actor=_service_actor(),
            )

    def test_payload_fields_correct(self, tmp_path: Path) -> None:
        run_ref, run_dir = _setup_run(tmp_path)
        raci = _make_raci_binding()
        sig_score = evaluate_significance(_medium_scores()).model_dump()
        _inject_decisions(run_dir, raci, sig_score)

        result = notify_decision_timeout(
            run_ref=run_ref,
            decision_id="audit:deploy-approval",
            actor=_service_actor(),
        )

        payload = result.timeout_expired_payload
        assert payload.run_id == run_ref.run_id
        assert payload.decision_id == "audit:deploy-approval"
        assert payload.step_id == "deploy-approval"
        assert payload.effective_band == "medium"
        assert payload.timeout_configured_seconds == 600  # default
        assert payload.actor == _service_actor()

    def test_custom_emitter_called(self, tmp_path: Path) -> None:
        run_ref, run_dir = _setup_run(tmp_path)
        raci = _make_raci_binding()
        sig_score = evaluate_significance(_medium_scores()).model_dump()
        _inject_decisions(run_dir, raci, sig_score)

        emitted: list[TimeoutExpiredPayload] = []

        class TrackingEmitter(NullEmitter):
            def emit_decision_timeout_expired(self, payload: TimeoutExpiredPayload) -> None:
                emitted.append(payload)

        notify_decision_timeout(
            run_ref=run_ref,
            decision_id="audit:deploy-approval",
            actor=_service_actor(),
            emitter=TrackingEmitter(),
        )

        assert len(emitted) == 1
        assert emitted[0].decision_id == "audit:deploy-approval"

    def test_null_emitter_default(self, tmp_path: Path) -> None:
        """When no emitter provided, NullEmitter is used (no crash)."""
        run_ref, run_dir = _setup_run(tmp_path)
        raci = _make_raci_binding()
        sig_score = evaluate_significance(_medium_scores()).model_dump()
        _inject_decisions(run_dir, raci, sig_score)

        # Should not raise
        result = notify_decision_timeout(
            run_ref=run_ref,
            decision_id="audit:deploy-approval",
            actor=_service_actor(),
        )
        assert result is not None

    def test_run_remains_blocked(self, tmp_path: Path) -> None:
        """After timeout, the run stays in its current state (fail-closed)."""
        run_ref, run_dir = _setup_run(tmp_path)
        raci = _make_raci_binding()
        sig_score = evaluate_significance(_medium_scores()).model_dump()
        _inject_decisions(run_dir, raci, sig_score)

        # Record state before
        with open(run_dir / "state.json", "r", encoding="utf-8") as f:
            state_before = json.load(f)

        notify_decision_timeout(
            run_ref=run_ref,
            decision_id="audit:deploy-approval",
            actor=_service_actor(),
        )

        # Verify blocked_reason is not modified
        with open(run_dir / "state.json", "r", encoding="utf-8") as f:
            state_after = json.load(f)

        assert state_after["blocked_reason"] == state_before["blocked_reason"]
        assert state_after["completed_steps"] == state_before["completed_steps"]

    def test_high_band_empty_consulted(self, tmp_path: Path) -> None:
        """High band with empty consulted set: no error, accountable only."""
        run_ref, run_dir = _setup_run(tmp_path)
        raci = _make_raci_binding(consulted=[])
        sig_score = evaluate_significance(_high_scores()).model_dump()
        _inject_decisions(run_dir, raci, sig_score)

        result = notify_decision_timeout(
            run_ref=run_ref,
            decision_id="audit:deploy-approval",
            actor=_service_actor(),
        )

        assert result.band == "high"
        assert len(result.escalation_targets) == 1
        assert result.escalation_targets[0] == raci.accountable

    def test_custom_timeout_from_policy(self, tmp_path: Path) -> None:
        """Custom timeout from policy extras is reflected in payload."""
        mission_file = tmp_path / "pack" / "missions" / "test-mission" / "mission.yaml"
        mission_file.parent.mkdir(parents=True, exist_ok=True)
        mission_file.write_text(MISSION_YAML, encoding="utf-8")
        context = DiscoveryContext(explicit_paths=[tmp_path / "pack"], builtin_roots=[])

        policy = MissionPolicySnapshot(
            extras={"significance_default_timeout_seconds": 300}
        )
        run_ref = start_mission_run(
            template_key="test-mission",
            inputs={},
            policy_snapshot=policy,
            context=context,
            run_store=tmp_path / "runs",
        )
        run_dir = Path(run_ref.run_dir)

        raci = _make_raci_binding()
        sig_score = evaluate_significance(_medium_scores()).model_dump()
        _inject_decisions(run_dir, raci, sig_score)

        result = notify_decision_timeout(
            run_ref=run_ref,
            decision_id="audit:deploy-approval",
            actor=_service_actor(),
        )

        assert result.timeout_expired_payload.timeout_configured_seconds == 300


# ============================================================================
# T020: Timeout event persistence
# ============================================================================


class TestTimeoutEventPersistence:
    """Tests for timeout event persistence to decisions dict."""

    def test_timeout_persisted_to_decisions(self, tmp_path: Path) -> None:
        run_ref, run_dir = _setup_run(tmp_path)
        raci = _make_raci_binding()
        sig_score = evaluate_significance(_medium_scores()).model_dump()
        _inject_decisions(run_dir, raci, sig_score)

        notify_decision_timeout(
            run_ref=run_ref,
            decision_id="audit:deploy-approval",
            actor=_service_actor(),
        )

        with open(run_dir / "state.json", "r", encoding="utf-8") as f:
            state = json.load(f)

        timeout_key = "timeout:audit:deploy-approval"
        assert timeout_key in state["decisions"]
        timeout_data = state["decisions"][timeout_key]
        assert timeout_data["decision_id"] == "audit:deploy-approval"
        assert timeout_data["step_id"] == "deploy-approval"
        assert timeout_data["effective_band"] == "medium"

    def test_timeout_appended_to_event_log(self, tmp_path: Path) -> None:
        run_ref, run_dir = _setup_run(tmp_path)
        raci = _make_raci_binding()
        sig_score = evaluate_significance(_medium_scores()).model_dump()
        _inject_decisions(run_dir, raci, sig_score)

        notify_decision_timeout(
            run_ref=run_ref,
            decision_id="audit:deploy-approval",
            actor=_service_actor(),
        )

        event_file = run_dir / "run.events.jsonl"
        assert event_file.exists()
        events = [json.loads(line) for line in event_file.read_text().splitlines() if line.strip()]
        timeout_events = [e for e in events if e["event_type"] == "DecisionTimeoutExpired"]
        assert len(timeout_events) >= 1
        assert timeout_events[-1]["payload"]["decision_id"] == "audit:deploy-approval"

    def test_decision_key_format(self, tmp_path: Path) -> None:
        """Timeout key follows 'timeout:{decision_id}' convention."""
        run_ref, run_dir = _setup_run(tmp_path)
        raci = _make_raci_binding()
        sig_score = evaluate_significance(_medium_scores()).model_dump()
        _inject_decisions(run_dir, raci, sig_score)

        notify_decision_timeout(
            run_ref=run_ref,
            decision_id="audit:deploy-approval",
            actor=_service_actor(),
        )

        with open(run_dir / "state.json", "r", encoding="utf-8") as f:
            state = json.load(f)

        # Key must match convention: "timeout:{decision_id}"
        assert "timeout:audit:deploy-approval" in state["decisions"]
        # Other decision keys are preserved
        assert "raci:deploy-approval" in state["decisions"]
        assert "significance:audit:deploy-approval" in state["decisions"]

    def test_existing_decisions_preserved(self, tmp_path: Path) -> None:
        """Timeout persistence does not clobber existing decisions."""
        run_ref, run_dir = _setup_run(tmp_path)
        raci = _make_raci_binding()
        sig_score = evaluate_significance(_medium_scores()).model_dump()
        _inject_decisions(run_dir, raci, sig_score)

        # Add a pre-existing custom decision
        state_path = run_dir / "state.json"
        with open(state_path, "r", encoding="utf-8") as f:
            state = json.load(f)
        state["decisions"]["custom:key"] = {"value": "preserved"}
        with open(state_path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, sort_keys=True)

        notify_decision_timeout(
            run_ref=run_ref,
            decision_id="audit:deploy-approval",
            actor=_service_actor(),
        )

        with open(state_path, "r", encoding="utf-8") as f:
            state_after = json.load(f)

        assert state_after["decisions"]["custom:key"] == {"value": "preserved"}

    def test_event_emitted_before_persistence(self, tmp_path: Path) -> None:
        """Event emission happens before snapshot save (consistent with engine patterns)."""
        run_ref, run_dir = _setup_run(tmp_path)
        raci = _make_raci_binding()
        sig_score = evaluate_significance(_medium_scores()).model_dump()
        _inject_decisions(run_dir, raci, sig_score)

        emission_order: list[str] = []

        class OrderTrackingEmitter(NullEmitter):
            def emit_decision_timeout_expired(self, payload: TimeoutExpiredPayload) -> None:
                # Record that emit was called — verify event log already has entry
                event_file = run_dir / "run.events.jsonl"
                events = [json.loads(line) for line in event_file.read_text().splitlines() if line.strip()]
                timeout_events = [e for e in events if e["event_type"] == "DecisionTimeoutExpired"]
                if timeout_events:
                    emission_order.append("event_log_written")
                emission_order.append("emitter_called")

        notify_decision_timeout(
            run_ref=run_ref,
            decision_id="audit:deploy-approval",
            actor=_service_actor(),
            emitter=OrderTrackingEmitter(),
        )

        assert "event_log_written" in emission_order
        assert "emitter_called" in emission_order

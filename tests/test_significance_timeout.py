"""WP07 – T032/T033: Timeout Policy, Escalation Target, and Timeout Event Tests.

Covers:
- T032: TimeoutPolicy validation, compute_escalation_targets(), parse_timeout_from_policy()
- T033: Timeout event emission via emitter protocol and JSONL log persistence

All tests deterministic, offline, no randomness (NFR-003, NFR-004).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from spec_kitty_runtime.discovery import DiscoveryContext
from spec_kitty_runtime.engine import (
    MissionRunRef,
    notify_decision_timeout,
    start_mission_run,
)
from spec_kitty_runtime.events import NullEmitter
from spec_kitty_runtime.schema import (
    MissionPolicySnapshot,
    MissionRuntimeError,
    RACIRoleBinding,
    ResolvedRACIBinding,
)
from spec_kitty_runtime.significance import (
    DIMENSION_NAMES,
    TimeoutEscalationResult,
    TimeoutExpiredPayload,
    TimeoutPolicy,
    compute_escalation_targets,
    evaluate_significance,
    parse_timeout_from_policy,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _human_actor(actor_id: str = "owner-001") -> RACIRoleBinding:
    return RACIRoleBinding(actor_type="human", actor_id=actor_id)


def _service_actor() -> RACIRoleBinding:
    return RACIRoleBinding(actor_type="service", actor_id="runtime")


def _llm_actor() -> RACIRoleBinding:
    return RACIRoleBinding(actor_type="llm", actor_id="agent-1")


def _consulted_actor(n: int = 0) -> RACIRoleBinding:
    return RACIRoleBinding(actor_type="human", actor_id=f"consulted-{n}")


def _make_raci(consulted_count: int = 0) -> ResolvedRACIBinding:
    consulted = [
        RACIRoleBinding(actor_type="human", actor_id=f"consulted-{i}")
        for i in range(consulted_count)
    ]
    return ResolvedRACIBinding(
        step_id="test-step",
        responsible=RACIRoleBinding(actor_type="human", actor_id="responsible-001"),
        accountable=_human_actor(),
        consulted=consulted,
        informed=[],
        source="inferred",
        inferred_rule="audit_blocking",
    )


def _medium_scores() -> dict[str, int]:
    """Scores that sum to 8 → medium band."""
    names = sorted(DIMENSION_NAMES)
    scores = {name: 1 for name in names}
    scores[names[0]] = 2
    scores[names[1]] = 2
    return scores


def _high_scores() -> dict[str, int]:
    """Scores that sum to 14 → high band."""
    names = sorted(DIMENSION_NAMES)
    scores = {name: 2 for name in names}
    scores[names[0]] = 3
    scores[names[1]] = 3
    return scores


MISSION_YAML = """\
mission:
  key: test-timeout-mission
  name: Test Timeout Mission
  version: 1.0.0
  description: Test mission for timeout tests
steps:
  - id: deploy-approval
    title: Deploy Approval
    prompt: Approve deployment
"""


def _setup_run(
    tmp_path: Path,
    policy: MissionPolicySnapshot | None = None,
) -> tuple[MissionRunRef, Path]:
    """Set up a mission run and return ref + run_dir."""
    mission_file = tmp_path / "pack" / "missions" / "test-timeout-mission" / "mission.yaml"
    mission_file.parent.mkdir(parents=True, exist_ok=True)
    mission_file.write_text(MISSION_YAML, encoding="utf-8")
    context = DiscoveryContext(explicit_paths=[tmp_path / "pack"], builtin_roots=[])

    run_ref = start_mission_run(
        template_key="test-timeout-mission",
        inputs={},
        policy_snapshot=policy or MissionPolicySnapshot(),
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
# T032: TimeoutPolicy validation
# ============================================================================


class TestTimeoutPolicyValidation:
    """Tests for TimeoutPolicy model validation."""

    def test_default_timeout(self) -> None:
        policy = TimeoutPolicy()
        assert policy.default_timeout_seconds == 600
        assert policy.effective_timeout_seconds == 600

    def test_custom_timeout(self) -> None:
        policy = TimeoutPolicy(default_timeout_seconds=1200)
        assert policy.effective_timeout_seconds == 1200

    def test_per_decision_override(self) -> None:
        policy = TimeoutPolicy(default_timeout_seconds=600, per_decision_timeout_seconds=300)
        assert policy.effective_timeout_seconds == 300

    def test_zero_timeout_rejected(self) -> None:
        with pytest.raises(ValueError):
            TimeoutPolicy(default_timeout_seconds=0)

    def test_negative_timeout_rejected(self) -> None:
        with pytest.raises(ValueError):
            TimeoutPolicy(default_timeout_seconds=-1)

    def test_zero_per_decision_rejected(self) -> None:
        with pytest.raises(ValueError):
            TimeoutPolicy(per_decision_timeout_seconds=0)

    def test_negative_per_decision_rejected(self) -> None:
        with pytest.raises(ValueError):
            TimeoutPolicy(per_decision_timeout_seconds=-1)

    def test_frozen(self) -> None:
        policy = TimeoutPolicy()
        with pytest.raises(Exception):
            policy.default_timeout_seconds = 999  # type: ignore[misc]


# ============================================================================
# T032: compute_escalation_targets() tests
# ============================================================================


class TestComputeEscalationTargets:
    """Tests for compute_escalation_targets pure function (FR-011 through FR-013)."""

    def test_medium_escalation_owner_only(self) -> None:
        raci = _make_raci(consulted_count=0)
        targets = compute_escalation_targets(raci, "medium")
        assert len(targets) == 1
        assert targets[0].actor_id == "owner-001"

    def test_medium_escalation_ignores_consulted(self) -> None:
        raci = _make_raci(consulted_count=3)
        targets = compute_escalation_targets(raci, "medium")
        assert len(targets) == 1
        assert targets[0].actor_id == "owner-001"

    def test_high_escalation_owner_plus_consulted(self) -> None:
        raci = _make_raci(consulted_count=2)
        targets = compute_escalation_targets(raci, "high")
        assert len(targets) == 3  # owner + 2 consulted
        assert targets[0].actor_id == "owner-001"
        assert targets[1].actor_id == "consulted-0"
        assert targets[2].actor_id == "consulted-1"

    def test_high_escalation_empty_consulted(self) -> None:
        raci = _make_raci(consulted_count=0)
        targets = compute_escalation_targets(raci, "high")
        assert len(targets) == 1  # owner only, no error
        assert targets[0].actor_id == "owner-001"

    def test_high_escalation_many_consulted(self) -> None:
        raci = _make_raci(consulted_count=5)
        targets = compute_escalation_targets(raci, "high")
        assert len(targets) == 6  # owner + 5 consulted

    def test_medium_responsible_equals_owner(self) -> None:
        """US3.2: When responsible == mission owner for medium, still returns accountable."""
        raci = ResolvedRACIBinding(
            step_id="s1",
            responsible=_human_actor(),  # same as accountable
            accountable=_human_actor(),
            consulted=[],
            informed=[],
            source="inferred",
            inferred_rule="audit_blocking",
        )
        targets = compute_escalation_targets(raci, "medium")
        assert len(targets) == 1
        assert targets[0].actor_id == "owner-001"

    def test_returns_tuple(self) -> None:
        raci = _make_raci()
        targets = compute_escalation_targets(raci, "medium")
        assert isinstance(targets, tuple)

    def test_deterministic_output(self) -> None:
        raci = _make_raci(consulted_count=2)
        t1 = compute_escalation_targets(raci, "high")
        t2 = compute_escalation_targets(raci, "high")
        assert t1 == t2


# ============================================================================
# T032: parse_timeout_from_policy() tests
# ============================================================================


class TestParseTimeoutFromPolicy:
    """Tests for parse_timeout_from_policy()."""

    def test_parse_timeout_default(self) -> None:
        policy = MissionPolicySnapshot()
        assert parse_timeout_from_policy(policy) == 600

    def test_parse_timeout_custom(self) -> None:
        policy = MissionPolicySnapshot(extras={"significance_default_timeout_seconds": 1200})
        assert parse_timeout_from_policy(policy) == 1200

    def test_parse_timeout_invalid_negative(self) -> None:
        policy = MissionPolicySnapshot(extras={"significance_default_timeout_seconds": -1})
        with pytest.raises(ValueError):
            parse_timeout_from_policy(policy)

    def test_parse_timeout_invalid_zero(self) -> None:
        policy = MissionPolicySnapshot(extras={"significance_default_timeout_seconds": 0})
        with pytest.raises(ValueError):
            parse_timeout_from_policy(policy)

    def test_parse_timeout_invalid_type(self) -> None:
        policy = MissionPolicySnapshot(extras={"significance_default_timeout_seconds": "600"})
        with pytest.raises(ValueError):
            parse_timeout_from_policy(policy)


# ============================================================================
# T033: Timeout Event Emission Tests
# ============================================================================


class CapturingEmitter(NullEmitter):
    """Test emitter that captures all emitted events."""

    def __init__(self) -> None:
        super().__init__()
        self.significance_evaluated: list = []
        self.timeout_expired: list[TimeoutExpiredPayload] = []

    def emit_significance_evaluated(self, payload) -> None:
        self.significance_evaluated.append(payload)

    def emit_decision_timeout_expired(self, payload: TimeoutExpiredPayload) -> None:
        self.timeout_expired.append(payload)


class TestTimeoutEventEmission:
    """Tests for timeout event emission via emitter protocol."""

    def test_timeout_event_emitted(self, tmp_path: Path) -> None:
        """Timeout event is emitted via the emitter protocol."""
        run_ref, run_dir = _setup_run(tmp_path)
        raci = _make_raci(consulted_count=1)
        sig_score = evaluate_significance(_medium_scores()).model_dump()
        _inject_decisions(run_dir, raci, sig_score)

        emitter = CapturingEmitter()
        result = notify_decision_timeout(
            run_ref=run_ref,
            decision_id="audit:deploy-approval",
            actor=_service_actor(),
            emitter=emitter,
        )

        assert len(emitter.timeout_expired) == 1
        payload = emitter.timeout_expired[0]
        assert payload.decision_id == "audit:deploy-approval"
        assert payload.effective_band in ("medium", "high")
        assert len(result.escalation_targets) > 0

    def test_timeout_event_payload_complete(self, tmp_path: Path) -> None:
        """Timeout event payload contains all required fields."""
        run_ref, run_dir = _setup_run(tmp_path)
        raci = _make_raci(consulted_count=1)
        sig_score = evaluate_significance(_medium_scores()).model_dump()
        _inject_decisions(run_dir, raci, sig_score)

        emitter = CapturingEmitter()
        notify_decision_timeout(
            run_ref=run_ref,
            decision_id="audit:deploy-approval",
            actor=_service_actor(),
            emitter=emitter,
        )

        payload = emitter.timeout_expired[0]
        assert payload.run_id == run_ref.run_id
        assert payload.step_id == "deploy-approval"
        assert payload.timeout_configured_seconds == 600
        assert payload.actor == _service_actor()
        assert isinstance(payload.significance_score, dict)
        assert isinstance(payload.raci_snapshot, dict)

    def test_timeout_high_band_emitted(self, tmp_path: Path) -> None:
        """High-band timeout event emitted with correct band."""
        run_ref, run_dir = _setup_run(tmp_path)
        raci = _make_raci(consulted_count=2)
        sig_score = evaluate_significance(_high_scores()).model_dump()
        _inject_decisions(run_dir, raci, sig_score)

        emitter = CapturingEmitter()
        notify_decision_timeout(
            run_ref=run_ref,
            decision_id="audit:deploy-approval",
            actor=_service_actor(),
            emitter=emitter,
        )

        payload = emitter.timeout_expired[0]
        assert payload.effective_band == "high"

    def test_timeout_custom_timeout_in_payload(self, tmp_path: Path) -> None:
        """Custom timeout value from policy appears in payload."""
        policy = MissionPolicySnapshot(
            extras={"significance_default_timeout_seconds": 300}
        )
        run_ref, run_dir = _setup_run(tmp_path, policy=policy)
        raci = _make_raci()
        sig_score = evaluate_significance(_medium_scores()).model_dump()
        _inject_decisions(run_dir, raci, sig_score)

        emitter = CapturingEmitter()
        notify_decision_timeout(
            run_ref=run_ref,
            decision_id="audit:deploy-approval",
            actor=_service_actor(),
            emitter=emitter,
        )

        payload = emitter.timeout_expired[0]
        assert payload.timeout_configured_seconds == 300


class TestTimeoutEventPersistence:
    """Tests for timeout event persistence to JSONL log and decisions dict."""

    def test_timeout_persisted_to_event_log(self, tmp_path: Path) -> None:
        """Timeout event written to run.events.jsonl."""
        run_ref, run_dir = _setup_run(tmp_path)
        raci = _make_raci()
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

    def test_timeout_persisted_to_decisions(self, tmp_path: Path) -> None:
        """Timeout record appears in decisions dict with correct key format."""
        run_ref, run_dir = _setup_run(tmp_path)
        raci = _make_raci()
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

    def test_timeout_does_not_clobber_existing_decisions(self, tmp_path: Path) -> None:
        """Existing decisions preserved after timeout persistence."""
        run_ref, run_dir = _setup_run(tmp_path)
        raci = _make_raci()
        sig_score = evaluate_significance(_medium_scores()).model_dump()
        _inject_decisions(run_dir, raci, sig_score)

        notify_decision_timeout(
            run_ref=run_ref,
            decision_id="audit:deploy-approval",
            actor=_service_actor(),
        )

        with open(run_dir / "state.json", "r", encoding="utf-8") as f:
            state = json.load(f)

        # Original decisions preserved
        assert "raci:deploy-approval" in state["decisions"]
        assert "significance:audit:deploy-approval" in state["decisions"]
        # Timeout added
        assert "timeout:audit:deploy-approval" in state["decisions"]

    def test_run_stays_blocked_after_timeout(self, tmp_path: Path) -> None:
        """After timeout, run state is not mutated (fail-closed)."""
        run_ref, run_dir = _setup_run(tmp_path)
        raci = _make_raci()
        sig_score = evaluate_significance(_medium_scores()).model_dump()
        _inject_decisions(run_dir, raci, sig_score)

        with open(run_dir / "state.json", "r", encoding="utf-8") as f:
            state_before = json.load(f)

        notify_decision_timeout(
            run_ref=run_ref,
            decision_id="audit:deploy-approval",
            actor=_service_actor(),
        )

        with open(run_dir / "state.json", "r", encoding="utf-8") as f:
            state_after = json.load(f)

        assert state_after["blocked_reason"] == state_before["blocked_reason"]
        assert state_after["completed_steps"] == state_before["completed_steps"]

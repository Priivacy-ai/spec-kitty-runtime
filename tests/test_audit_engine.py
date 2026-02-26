"""Integration tests for the engine audit decision resume path (WP03).

Covers AC-5 (approve resume path) and AC-6 (reject blocks run).
Uses real filesystem run dirs via tmp_path — no mocks.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from spec_kitty_runtime.discovery import DiscoveryContext
from spec_kitty_runtime.engine import next_step, provide_decision_answer, start_mission_run
from spec_kitty_runtime.schema import ActorIdentity, MissionPolicySnapshot, MissionRuntimeError


# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------

BLOCKING_AUDIT_MISSION = """\
mission:
  key: test-blocking-audit
  name: Test Blocking Audit
  version: "1.0.0"
steps:
  - id: step-01
    title: First step
audit_steps:
  - id: audit-01
    title: Post-merge check
    depends_on: ["step-01"]
    audit:
      trigger_mode: manual
      enforcement: blocking
"""

TWO_STEP_BLOCKING_AUDIT_MISSION = """\
mission:
  key: test-two-step-audit
  name: Test Two Step Audit
  version: "1.0.0"
steps:
  - id: step-01
    title: First step
  - id: step-02
    title: Second step
    depends_on: ["audit-01"]
audit_steps:
  - id: audit-01
    title: Post-merge check
    depends_on: ["step-01"]
    audit:
      trigger_mode: manual
      enforcement: blocking
"""


def _setup(
    tmp_path: Path,
    yaml_content: str = BLOCKING_AUDIT_MISSION,
    key: str = "test-blocking-audit",
) -> tuple[DiscoveryContext, Path]:
    mission_file = tmp_path / "pack" / "missions" / key / "mission.yaml"
    mission_file.parent.mkdir(parents=True, exist_ok=True)
    mission_file.write_text(yaml_content, encoding="utf-8")
    context = DiscoveryContext(explicit_paths=[tmp_path / "pack"], builtin_roots=[])
    return context, mission_file


def _actor(actor_id: str = "human-reviewer") -> ActorIdentity:
    return ActorIdentity(actor_id=actor_id, actor_type="human")


def _advance_to_audit_checkpoint(
    tmp_path: Path,
    yaml_content: str = BLOCKING_AUDIT_MISSION,
    key: str = "test-blocking-audit",
):
    """Set up a run that has reached an audit checkpoint.

    Steps:
    1. start_mission_run -> run_ref
    2. next_step -> kind=step (step-01)
    3. next_step(result=success) -> kind=decision_required for audit-01

    Returns (run_ref, decision) where decision.decision_id == "audit:audit-01".
    """
    context, _ = _setup(tmp_path, yaml_content, key)
    policy = MissionPolicySnapshot()
    run_ref = start_mission_run(
        template_key=key,
        inputs={},
        policy_snapshot=policy,
        context=context,
        run_store=tmp_path / "runs",
    )
    # Advance past step-01
    d1 = next_step(run_ref, agent_id="agent-01", context=context)
    assert d1.kind == "step", f"Expected step, got {d1.kind}"
    assert d1.step_id == "step-01"

    d2 = next_step(run_ref, agent_id="agent-01", result="success", context=context)
    assert d2.kind == "decision_required", f"Expected decision_required, got {d2.kind}"
    assert d2.decision_id == "audit:audit-01"

    return run_ref, d2


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


# ---------------------------------------------------------------------------
# AC-5: Resume path — approve
# ---------------------------------------------------------------------------

class TestAuditApproveResumePath:
    def test_approve_adds_to_completed_steps(self, tmp_path: Path) -> None:
        """After approve, audit-01 appears in snapshot.completed_steps."""
        run_ref, _ = _advance_to_audit_checkpoint(tmp_path)
        provide_decision_answer(run_ref, "audit:audit-01", "approve", _actor())

        state = _read_snapshot_raw(run_ref)
        assert "audit-01" in state["completed_steps"]

    def test_approve_removes_from_pending_decisions(self, tmp_path: Path) -> None:
        """After approve, audit:audit-01 is removed from pending_decisions."""
        run_ref, _ = _advance_to_audit_checkpoint(tmp_path)
        provide_decision_answer(run_ref, "audit:audit-01", "approve", _actor())

        state = _read_snapshot_raw(run_ref)
        assert "audit:audit-01" not in state["pending_decisions"]

    def test_approve_blocked_reason_unchanged(self, tmp_path: Path) -> None:
        """After approve, blocked_reason remains None."""
        run_ref, _ = _advance_to_audit_checkpoint(tmp_path)
        provide_decision_answer(run_ref, "audit:audit-01", "approve", _actor())

        state = _read_snapshot_raw(run_ref)
        assert state["blocked_reason"] is None

    def test_approve_next_step_continues(self, tmp_path: Path) -> None:
        """After approve, next_step returns the next eligible step."""
        context, _ = _setup(tmp_path, TWO_STEP_BLOCKING_AUDIT_MISSION, "test-two-step-audit")
        policy = MissionPolicySnapshot()
        run_ref = start_mission_run(
            template_key="test-two-step-audit",
            inputs={},
            policy_snapshot=policy,
            context=context,
            run_store=tmp_path / "runs",
        )

        # step-01
        d1 = next_step(run_ref, agent_id="agent-01", context=context)
        assert d1.kind == "step" and d1.step_id == "step-01"

        # audit-01 (blocking)
        d2 = next_step(run_ref, agent_id="agent-01", result="success", context=context)
        assert d2.kind == "decision_required" and d2.decision_id == "audit:audit-01"

        # Approve the audit
        provide_decision_answer(run_ref, "audit:audit-01", "approve", _actor())

        # step-02 should now be eligible (depends_on audit-01)
        d3 = next_step(run_ref, agent_id="agent-01", context=context)
        assert d3.kind == "step"
        assert d3.step_id == "step-02"

    def test_approve_terminal_when_no_more_steps(self, tmp_path: Path) -> None:
        """After approve with no further steps, next_step returns terminal."""
        run_ref, _ = _advance_to_audit_checkpoint(tmp_path)

        # Approve: no more steps after audit-01 in BLOCKING_AUDIT_MISSION
        provide_decision_answer(run_ref, "audit:audit-01", "approve", _actor())

        context, _ = _setup(tmp_path)
        d = next_step(run_ref, agent_id="agent-01", context=context)
        assert d.kind == "terminal"


# ---------------------------------------------------------------------------
# AC-6: Resume path — reject
# ---------------------------------------------------------------------------

class TestAuditRejectBlocksRun:
    def test_reject_sets_blocked_reason(self, tmp_path: Path) -> None:
        """After reject, snapshot.blocked_reason is set."""
        run_ref, _ = _advance_to_audit_checkpoint(tmp_path)
        provide_decision_answer(run_ref, "audit:audit-01", "reject", _actor())

        state = _read_snapshot_raw(run_ref)
        assert state["blocked_reason"] is not None
        assert len(state["blocked_reason"]) > 0

    def test_reject_removes_from_pending_decisions(self, tmp_path: Path) -> None:
        """After reject, audit:audit-01 is removed from pending_decisions."""
        run_ref, _ = _advance_to_audit_checkpoint(tmp_path)
        provide_decision_answer(run_ref, "audit:audit-01", "reject", _actor())

        state = _read_snapshot_raw(run_ref)
        assert "audit:audit-01" not in state["pending_decisions"]

    def test_reject_next_step_returns_blocked(self, tmp_path: Path) -> None:
        """After reject, next_step returns kind=blocked."""
        run_ref, _ = _advance_to_audit_checkpoint(tmp_path)
        provide_decision_answer(run_ref, "audit:audit-01", "reject", _actor())

        context, _ = _setup(tmp_path)
        d = next_step(run_ref, agent_id="agent-01", context=context)
        assert d.kind == "blocked"

    def test_reject_blocked_reason_references_step_id(self, tmp_path: Path) -> None:
        """Blocked reason mentions the audit step ID."""
        run_ref, _ = _advance_to_audit_checkpoint(tmp_path)
        provide_decision_answer(run_ref, "audit:audit-01", "reject", _actor())

        state = _read_snapshot_raw(run_ref)
        assert "audit-01" in state["blocked_reason"]

    def test_reject_blocked_reason_references_actor_id(self, tmp_path: Path) -> None:
        """Blocked reason includes the actor_id of the reviewer."""
        run_ref, _ = _advance_to_audit_checkpoint(tmp_path)
        actor = _actor("security-lead")
        provide_decision_answer(run_ref, "audit:audit-01", "reject", actor)

        state = _read_snapshot_raw(run_ref)
        assert "security-lead" in state["blocked_reason"]

    def test_reject_blocked_reason_matches_next_step_reason(self, tmp_path: Path) -> None:
        """next_step reason matches the blocked_reason stored in snapshot."""
        run_ref, _ = _advance_to_audit_checkpoint(tmp_path)
        provide_decision_answer(run_ref, "audit:audit-01", "reject", _actor())

        state = _read_snapshot_raw(run_ref)
        context, _ = _setup(tmp_path)
        d = next_step(run_ref, agent_id="agent-01", context=context)
        assert d.kind == "blocked"
        assert d.reason == state["blocked_reason"]

    def test_reject_does_not_add_to_completed_steps(self, tmp_path: Path) -> None:
        """After reject, audit-01 is NOT added to completed_steps."""
        run_ref, _ = _advance_to_audit_checkpoint(tmp_path)
        provide_decision_answer(run_ref, "audit:audit-01", "reject", _actor())

        state = _read_snapshot_raw(run_ref)
        assert "audit-01" not in state["completed_steps"]


# ---------------------------------------------------------------------------
# Invalid answer
# ---------------------------------------------------------------------------

class TestAuditInvalidAnswer:
    def test_invalid_answer_raises_runtime_error(self, tmp_path: Path) -> None:
        """Providing an answer other than approve/reject raises MissionRuntimeError."""
        run_ref, _ = _advance_to_audit_checkpoint(tmp_path)
        with pytest.raises(MissionRuntimeError, match="Invalid audit answer"):
            provide_decision_answer(run_ref, "audit:audit-01", "maybe", _actor())

    def test_invalid_answer_empty_string_raises(self, tmp_path: Path) -> None:
        """Empty string answer raises MissionRuntimeError."""
        run_ref, _ = _advance_to_audit_checkpoint(tmp_path)
        with pytest.raises(MissionRuntimeError, match="Invalid audit answer"):
            provide_decision_answer(run_ref, "audit:audit-01", "", _actor())

    def test_invalid_answer_does_not_mutate_snapshot(self, tmp_path: Path) -> None:
        """After an invalid answer, snapshot state is unchanged (decision still pending)."""
        run_ref, _ = _advance_to_audit_checkpoint(tmp_path)
        state_before = _read_snapshot_raw(run_ref)

        with pytest.raises(MissionRuntimeError):
            provide_decision_answer(run_ref, "audit:audit-01", "maybe", _actor())

        # The invalid answer raises before writing — pending_decisions should still have the entry
        state_after = _read_snapshot_raw(run_ref)
        assert state_after["pending_decisions"] == state_before["pending_decisions"]


# ---------------------------------------------------------------------------
# Event emission (T018)
# ---------------------------------------------------------------------------

class TestAuditEventEmission:
    def test_approve_emits_decision_answered_event(self, tmp_path: Path) -> None:
        """Approving emits a DECISION_INPUT_ANSWERED event."""
        run_ref, _ = _advance_to_audit_checkpoint(tmp_path)
        provide_decision_answer(run_ref, "audit:audit-01", "approve", _actor())

        events = _read_events(run_ref)
        answered = [e for e in events if e["event_type"] == "DecisionInputAnswered"]
        assert len(answered) == 1
        assert answered[0]["payload"]["decision_id"] == "audit:audit-01"
        assert answered[0]["payload"]["answer"] == "approve"

    def test_reject_emits_decision_answered_event(self, tmp_path: Path) -> None:
        """Rejecting emits a DECISION_INPUT_ANSWERED event."""
        run_ref, _ = _advance_to_audit_checkpoint(tmp_path)
        provide_decision_answer(run_ref, "audit:audit-01", "reject", _actor())

        events = _read_events(run_ref)
        answered = [e for e in events if e["event_type"] == "DecisionInputAnswered"]
        assert len(answered) == 1
        assert answered[0]["payload"]["decision_id"] == "audit:audit-01"
        assert answered[0]["payload"]["answer"] == "reject"

    def test_approve_event_contains_actor(self, tmp_path: Path) -> None:
        """The DECISION_INPUT_ANSWERED event includes the actor."""
        run_ref, _ = _advance_to_audit_checkpoint(tmp_path)
        actor = _actor("compliance-bot")
        provide_decision_answer(run_ref, "audit:audit-01", "approve", actor)

        events = _read_events(run_ref)
        answered = [e for e in events if e["event_type"] == "DecisionInputAnswered"]
        assert answered[0]["payload"]["actor"]["actor_id"] == "compliance-bot"

    def test_reject_event_contains_actor(self, tmp_path: Path) -> None:
        """The DECISION_INPUT_ANSWERED event includes the actor on reject path too."""
        run_ref, _ = _advance_to_audit_checkpoint(tmp_path)
        actor = _actor("security-reviewer")
        provide_decision_answer(run_ref, "audit:audit-01", "reject", actor)

        events = _read_events(run_ref)
        answered = [e for e in events if e["event_type"] == "DecisionInputAnswered"]
        assert answered[0]["payload"]["actor"]["actor_id"] == "security-reviewer"


# ---------------------------------------------------------------------------
# Guard: invalid answer must not write state before raising
# ---------------------------------------------------------------------------

class TestAuditInvalidAnswerGuard:
    def test_invalid_answer_decision_still_pending_after_error(self, tmp_path: Path) -> None:
        """After invalid answer error, the decision remains in pending_decisions."""
        run_ref, _ = _advance_to_audit_checkpoint(tmp_path)

        with pytest.raises(MissionRuntimeError):
            provide_decision_answer(run_ref, "audit:audit-01", "APPROVE", _actor())

        state = _read_snapshot_raw(run_ref)
        assert "audit:audit-01" in state["pending_decisions"]

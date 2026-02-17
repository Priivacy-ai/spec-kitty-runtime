"""Tests for byte-identical JSON determinism guarantees."""

from datetime import datetime, timezone

from spec_kitty_runtime.planner import plan_next, serialize_decision
from spec_kitty_runtime.schema import (
    MissionPolicySnapshot,
    MissionRunSnapshot,
    MissionTemplate,
    NextDecision,
)


HASH_PLACEHOLDER = "0" * 64


def _template() -> MissionTemplate:
    return MissionTemplate.model_validate(
        {
            "mission": {
                "key": "det-test",
                "name": "Determinism Test",
                "version": "1.0.0",
            },
            "steps": [
                {"id": "S1", "title": "Step One", "prompt": "Do one"},
                {"id": "S2", "title": "Step Two", "prompt": "Do two", "depends_on": ["S1"]},
            ],
        }
    )


def _snapshot(**overrides) -> MissionRunSnapshot:
    defaults = dict(
        run_id="r1",
        mission_key="det-test",
        template_path="/tmp/mission.yaml",
        template_hash=HASH_PLACEHOLDER,
        issued_step_id=None,
        completed_steps=[],
        inputs={},
        decisions={},
        pending_decisions={},
        blocked_reason=None,
    )
    defaults.update(overrides)
    return MissionRunSnapshot(**defaults)


def test_byte_identical_next_decision_json() -> None:
    """Same snapshot+template 100x produces byte-identical output."""
    template = _template()
    snapshot = _snapshot()
    policy = MissionPolicySnapshot()

    first = serialize_decision(plan_next(snapshot, template, policy))
    for _ in range(99):
        result = serialize_decision(plan_next(snapshot, template, policy))
        assert result == first, "Non-deterministic: different bytes on same input"


def test_determinism_across_all_four_decision_kinds() -> None:
    """Each of the four decision kinds serializes deterministically."""
    template = _template()
    policy = MissionPolicySnapshot()

    # step
    step_snap = _snapshot()
    step_json = serialize_decision(plan_next(step_snap, template, policy))
    assert serialize_decision(plan_next(step_snap, template, policy)) == step_json

    # decision_required (via pending_decisions)
    req_snap = _snapshot(
        pending_decisions={
            "d1": {
                "decision_id": "d1",
                "step_id": "S1",
                "question": "Which approach?",
                "options": ["A", "B"],
                "requested_by": {
                    "actor_id": "agent-1",
                    "actor_type": "llm",
                },
                "requested_at": "2026-01-01T00:00:00+00:00",
            }
        }
    )
    req_json = serialize_decision(plan_next(req_snap, template, policy))
    assert serialize_decision(plan_next(req_snap, template, policy)) == req_json

    # blocked
    blocked_snap = _snapshot(blocked_reason="Something broke")
    blocked_json = serialize_decision(plan_next(blocked_snap, template, policy))
    assert serialize_decision(plan_next(blocked_snap, template, policy)) == blocked_json

    # terminal (all steps completed)
    terminal_snap = _snapshot(completed_steps=["S1", "S2"])
    terminal_json = serialize_decision(plan_next(terminal_snap, template, policy))
    assert serialize_decision(plan_next(terminal_snap, template, policy)) == terminal_json


def test_serialize_decision_stable_with_datetime() -> None:
    """datetime fields serialize consistently via default=str."""
    decision = NextDecision(
        kind="step",
        run_id="r1",
        mission_key="det-test",
        step_id="S1",
        step_title="Step One",
        prompt="Do one",
    )
    s1 = serialize_decision(decision)
    s2 = serialize_decision(decision)
    assert s1 == s2
    assert '"kind":"step"' in s1

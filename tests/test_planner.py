"""Tests for the deterministic DAG-based planner."""

import hashlib
from pathlib import Path

from spec_kitty_runtime.planner import plan_next
from spec_kitty_runtime.schema import MissionPolicySnapshot, MissionRunSnapshot, MissionTemplate


HASH_PLACEHOLDER = "0" * 64


def _template() -> MissionTemplate:
    return MissionTemplate.model_validate(
        {
            "mission": {
                "key": "software-dev",
                "name": "Software Development",
                "version": "1.0.0",
                "description": "",
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
        mission_key="software-dev",
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


def test_planner_is_deterministic_for_same_snapshot() -> None:
    template = _template()
    snapshot = _snapshot()
    policy = MissionPolicySnapshot()

    d1 = plan_next(snapshot, template, policy)
    d2 = plan_next(snapshot, template, policy)

    assert d1.model_dump() == d2.model_dump()
    assert d1.kind == "step"
    assert d1.step_id == "S1"


def test_dag_skips_completed_steps() -> None:
    template = _template()
    snapshot = _snapshot(completed_steps=["S1"])
    policy = MissionPolicySnapshot()

    d = plan_next(snapshot, template, policy)
    assert d.kind == "step"
    assert d.step_id == "S2"


def test_dag_respects_dependencies() -> None:
    """S2 depends on S1; if S1 not completed, S2 is not eligible."""
    template = MissionTemplate.model_validate(
        {
            "mission": {"key": "dep-test", "name": "Dep Test", "version": "1.0.0"},
            "steps": [
                {"id": "S1", "title": "Step One", "prompt": "Do one"},
                {"id": "S2", "title": "Step Two", "prompt": "Do two", "depends_on": ["S1"]},
                {"id": "S3", "title": "Step Three", "prompt": "Do three", "depends_on": ["S2"]},
            ],
        }
    )
    # S1 is issued (in progress), S2/S3 blocked by deps.
    snapshot = _snapshot(
        mission_key="dep-test",
        issued_step_id="S1",
    )
    policy = MissionPolicySnapshot()

    d = plan_next(snapshot, template, policy)
    # S1 is issued, S2 blocked by S1, S3 blocked by S2 -> unschedulable, not terminal.
    assert d.kind == "blocked"
    assert "unmet dependencies" in d.reason


def test_dag_picks_first_eligible_by_template_order() -> None:
    """When multiple steps are eligible, pick the first by template order."""
    template = MissionTemplate.model_validate(
        {
            "mission": {"key": "order-test", "name": "Order Test", "version": "1.0.0"},
            "steps": [
                {"id": "A", "title": "Alpha", "prompt": "Do A"},
                {"id": "B", "title": "Beta", "prompt": "Do B"},
                {"id": "C", "title": "Charlie", "prompt": "Do C"},
            ],
        }
    )
    snapshot = _snapshot(mission_key="order-test")
    policy = MissionPolicySnapshot()

    d = plan_next(snapshot, template, policy)
    assert d.step_id == "A"  # First by template order


def test_pending_decision_blocks_before_dag() -> None:
    """Pending decisions are checked before DAG traversal."""
    template = _template()
    snapshot = _snapshot(
        pending_decisions={
            "d1": {
                "decision_id": "d1",
                "step_id": "S1",
                "question": "Which framework?",
                "options": ["React", "Vue"],
                "requested_by": {"actor_id": "agent-1", "actor_type": "llm"},
                "requested_at": "2026-01-01T00:00:00+00:00",
            }
        }
    )
    policy = MissionPolicySnapshot()

    d = plan_next(snapshot, template, policy)
    assert d.kind == "decision_required"
    assert d.decision_id == "d1"
    assert d.question == "Which framework?"
    assert d.options == ["React", "Vue"]


def test_blocked_reason_takes_priority() -> None:
    """blocked_reason overrides everything including pending decisions."""
    template = _template()
    snapshot = _snapshot(
        blocked_reason="Manual intervention required",
        pending_decisions={
            "d1": {
                "decision_id": "d1",
                "step_id": "S1",
                "question": "Q?",
                "requested_by": {"actor_id": "a1", "actor_type": "human"},
                "requested_at": "2026-01-01T00:00:00+00:00",
            }
        },
    )
    policy = MissionPolicySnapshot()

    d = plan_next(snapshot, template, policy)
    assert d.kind == "blocked"
    assert d.reason == "Manual intervention required"


def test_template_drift_returns_blocked(tmp_path: Path) -> None:
    """If live template hash differs from frozen hash, return blocked."""
    template = _template()
    live_file = tmp_path / "mission.yaml"
    live_file.write_text("different content", encoding="utf-8")

    live_hash = hashlib.sha256(live_file.read_bytes()).hexdigest()
    # Use a different hash so drift is detected.
    snapshot = _snapshot(template_hash="not_the_same_hash")
    policy = MissionPolicySnapshot()

    d = plan_next(snapshot, template, policy, live_template_path=live_file)
    assert d.kind == "blocked"
    assert "Migration required" in d.reason


# ---------------------------------------------------------------------------
# P0: Input-keyed decisions
# ---------------------------------------------------------------------------

def test_missing_input_returns_input_keyed_decision() -> None:
    """Missing requires_inputs returns decision_required with input-keyed decision_id."""
    template = MissionTemplate.model_validate(
        {
            "mission": {"key": "input-test", "name": "Input Test", "version": "1.0.0"},
            "steps": [
                {
                    "id": "S1",
                    "title": "Step One",
                    "prompt": "Do one",
                    "requires_inputs": ["framework", "language"],
                },
            ],
        }
    )
    snapshot = _snapshot(mission_key="input-test")
    policy = MissionPolicySnapshot()

    d = plan_next(snapshot, template, policy)
    assert d.kind == "decision_required"
    assert d.decision_id == "input:framework"
    assert d.input_key == "framework"
    assert "framework" in d.question


def test_input_keyed_decision_resolved_by_inputs() -> None:
    """Once input is in snapshot.inputs, decision is not re-raised."""
    template = MissionTemplate.model_validate(
        {
            "mission": {"key": "input-test", "name": "Input Test", "version": "1.0.0"},
            "steps": [
                {
                    "id": "S1",
                    "title": "Step One",
                    "prompt": "Do one",
                    "requires_inputs": ["framework"],
                },
            ],
        }
    )
    snapshot = _snapshot(mission_key="input-test", inputs={"framework": "React"})
    policy = MissionPolicySnapshot()

    d = plan_next(snapshot, template, policy)
    assert d.kind == "step"
    assert d.step_id == "S1"


# ---------------------------------------------------------------------------
# P2: Unschedulable DAG vs terminal
# ---------------------------------------------------------------------------

def test_unschedulable_dag_returns_blocked_not_terminal() -> None:
    """Steps with unmet deps but not completed -> blocked, not terminal."""
    template = MissionTemplate.model_validate(
        {
            "mission": {"key": "dag-test", "name": "DAG Test", "version": "1.0.0"},
            "steps": [
                {"id": "S1", "title": "Step One", "prompt": "Do one"},
                {"id": "S2", "title": "Step Two", "prompt": "Do two", "depends_on": ["S1"]},
            ],
        }
    )
    # S1 is issued (being worked on), S2 depends on S1 which isn't completed.
    snapshot = _snapshot(mission_key="dag-test", issued_step_id="S1")
    policy = MissionPolicySnapshot()

    d = plan_next(snapshot, template, policy)
    assert d.kind == "blocked"
    assert "unmet dependencies" in d.reason


def test_true_terminal_when_all_steps_completed() -> None:
    """All steps completed -> terminal."""
    template = _template()
    snapshot = _snapshot(completed_steps=["S1", "S2"])
    policy = MissionPolicySnapshot()

    d = plan_next(snapshot, template, policy)
    assert d.kind == "terminal"
    assert "completed" in d.reason

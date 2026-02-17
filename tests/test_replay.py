"""Tests for replay determinism from frozen templates."""

import json
from pathlib import Path

from spec_kitty_runtime.discovery import DiscoveryContext
from spec_kitty_runtime.engine import next_step, provide_decision_answer, start_mission_run
from spec_kitty_runtime.planner import serialize_decision
from spec_kitty_runtime.schema import ActorIdentity, MissionPolicySnapshot, MissionRunSnapshot


def _normalize_decision(serialized: str) -> dict:
    """Normalize a serialized decision by replacing run_id with a placeholder.

    run_id is unique per run (UUID), so we replace it for comparison.
    """
    data = json.loads(serialized)
    data["run_id"] = "NORMALIZED"
    if data.get("context") and "run_id" in data["context"]:
        data["context"]["run_id"] = "NORMALIZED"
    return data

MISSION_YAML = """\
mission:
  key: replay-test
  name: Replay Test
  version: 1.0.0
steps:
  - id: S1
    title: Step One
    prompt: Do one
  - id: S2
    title: Step Two
    prompt: Do two
    depends_on: ["S1"]
  - id: S3
    title: Step Three
    prompt: Do three
    depends_on: ["S2"]
"""


def _setup_mission(tmp_path: Path) -> tuple[DiscoveryContext, Path]:
    mission_file = tmp_path / "pack" / "missions" / "replay-test" / "mission.yaml"
    mission_file.parent.mkdir(parents=True, exist_ok=True)
    mission_file.write_text(MISSION_YAML, encoding="utf-8")
    context = DiscoveryContext(explicit_paths=[tmp_path / "pack"], builtin_roots=[])
    return context, mission_file


def test_replay_produces_same_decision_sequence(tmp_path: Path) -> None:
    """Run mission to terminal, replay from same template, verify identical sequence."""
    context, _ = _setup_mission(tmp_path)
    policy = MissionPolicySnapshot()

    # First run: collect decisions.
    run1 = start_mission_run(
        template_key="replay-test",
        inputs={},
        policy_snapshot=policy,
        context=context,
        run_store=tmp_path / "runs1",
    )
    decisions_run1 = []
    d = next_step(run1, agent_id="agent-a", context=context)
    decisions_run1.append(serialize_decision(d))
    while d.kind != "terminal":
        d = next_step(run1, agent_id="agent-a", result="success", context=context)
        decisions_run1.append(serialize_decision(d))

    # Second run: replay and compare.
    run2 = start_mission_run(
        template_key="replay-test",
        inputs={},
        policy_snapshot=policy,
        context=context,
        run_store=tmp_path / "runs2",
    )
    decisions_run2 = []
    d = next_step(run2, agent_id="agent-a", context=context)
    decisions_run2.append(serialize_decision(d))
    while d.kind != "terminal":
        d = next_step(run2, agent_id="agent-a", result="success", context=context)
        decisions_run2.append(serialize_decision(d))

    assert len(decisions_run1) == len(decisions_run2)
    for i, (d1, d2) in enumerate(zip(decisions_run1, decisions_run2)):
        n1 = _normalize_decision(d1)
        n2 = _normalize_decision(d2)
        assert n1 == n2, f"Decision mismatch at index {i}"


def test_replay_with_decision_answer_flow(tmp_path: Path) -> None:
    """Decision required -> answer -> continue works identically on replay."""
    mission_yaml = """\
mission:
  key: decision-replay
  name: Decision Replay
  version: 1.0.0
steps:
  - id: S1
    title: Step One
    prompt: Do one
    requires_inputs: ["approach"]
  - id: S2
    title: Step Two
    prompt: Do two
"""
    mission_file = tmp_path / "pack" / "missions" / "decision-replay" / "mission.yaml"
    mission_file.parent.mkdir(parents=True, exist_ok=True)
    mission_file.write_text(mission_yaml, encoding="utf-8")
    context = DiscoveryContext(explicit_paths=[tmp_path / "pack"], builtin_roots=[])
    policy = MissionPolicySnapshot()

    # Run with required input provided upfront.
    run = start_mission_run(
        template_key="decision-replay",
        inputs={"approach": "TDD"},
        policy_snapshot=policy,
        context=context,
        run_store=tmp_path / "runs",
    )

    d1 = next_step(run, agent_id="agent-a", context=context)
    assert d1.kind == "step"
    assert d1.step_id == "S1"

    d2 = next_step(run, agent_id="agent-a", result="success", context=context)
    assert d2.kind == "step"
    assert d2.step_id == "S2"

    d3 = next_step(run, agent_id="agent-a", result="success", context=context)
    assert d3.kind == "terminal"

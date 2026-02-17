"""Tests for the mission run engine."""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from spec_kitty_runtime.discovery import DiscoveryContext
from spec_kitty_runtime.engine import next_step, provide_decision_answer, start_mission_run
from spec_kitty_runtime.schema import ActorIdentity, MissionPolicySnapshot, MissionRunSnapshot


MISSION_YAML = """\
mission:
  key: software-dev
  name: Software Development
  version: 1.0.0
  description: Test mission
steps:
  - id: S1
    title: Step One
    prompt: Do one
  - id: S2
    title: Step Two
    prompt: Do two
"""


def _setup(tmp_path: Path, yaml_content: str = MISSION_YAML, key: str = "software-dev") -> tuple[DiscoveryContext, Path]:
    mission_file = tmp_path / "pack" / "missions" / key / "mission.yaml"
    mission_file.parent.mkdir(parents=True, exist_ok=True)
    mission_file.write_text(yaml_content, encoding="utf-8")
    context = DiscoveryContext(explicit_paths=[tmp_path / "pack"], builtin_roots=[])
    return context, mission_file


def test_engine_next_loop_to_terminal(tmp_path: Path) -> None:
    context, _ = _setup(tmp_path)

    run = start_mission_run(
        template_key="software-dev",
        inputs={},
        policy_snapshot=MissionPolicySnapshot(),
        context=context,
        run_store=tmp_path / "runs",
    )

    d1 = next_step(run, agent_id="codex", context=context)
    assert d1.kind == "step"
    assert d1.step_id == "S1"

    d2 = next_step(run, agent_id="codex", result="success", context=context)
    assert d2.kind == "step"
    assert d2.step_id == "S2"

    d3 = next_step(run, agent_id="codex", result="success", context=context)
    assert d3.kind == "terminal"


def test_full_mission_with_decision_flow(tmp_path: Path) -> None:
    """Mission with pending decision -> answer -> continue."""
    context, _ = _setup(tmp_path)

    run = start_mission_run(
        template_key="software-dev",
        inputs={},
        policy_snapshot=MissionPolicySnapshot(),
        context=context,
        run_store=tmp_path / "runs",
    )

    # Manually inject a pending decision into the snapshot.
    run_dir = Path(run.run_dir)
    with open(run_dir / "state.json", "r", encoding="utf-8") as f:
        state = json.load(f)
    state["pending_decisions"] = {
        "d1": {
            "decision_id": "d1",
            "step_id": "S1",
            "question": "Which approach?",
            "options": ["A", "B"],
            "requested_by": {"actor_id": "agent-1", "actor_type": "llm"},
            "requested_at": "2026-01-01T00:00:00+00:00",
        }
    }
    with open(run_dir / "state.json", "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, sort_keys=True)

    # Next step should return decision_required.
    d = next_step(run, agent_id="codex", context=context)
    assert d.kind == "decision_required"
    assert d.decision_id == "d1"

    # Answer the decision.
    actor = ActorIdentity(actor_id="human-1", actor_type="human")
    provide_decision_answer(run, "d1", "A", actor)

    # Now next step should proceed.
    d = next_step(run, agent_id="codex", context=context)
    assert d.kind == "step"
    assert d.step_id == "S1"


def test_provide_decision_answer_unblocks_run(tmp_path: Path) -> None:
    """After answering all pending decisions, the run proceeds."""
    context, _ = _setup(tmp_path)

    run = start_mission_run(
        template_key="software-dev",
        inputs={},
        policy_snapshot=MissionPolicySnapshot(),
        context=context,
        run_store=tmp_path / "runs",
    )

    # Inject two pending decisions.
    run_dir = Path(run.run_dir)
    with open(run_dir / "state.json", "r", encoding="utf-8") as f:
        state = json.load(f)
    state["pending_decisions"] = {
        "d1": {
            "decision_id": "d1",
            "step_id": "S1",
            "question": "Q1?",
            "requested_by": {"actor_id": "a1", "actor_type": "human"},
            "requested_at": "2026-01-01T00:00:00+00:00",
        },
        "d2": {
            "decision_id": "d2",
            "step_id": "S1",
            "question": "Q2?",
            "requested_by": {"actor_id": "a1", "actor_type": "human"},
            "requested_at": "2026-01-01T00:00:00+00:00",
        },
    }
    with open(run_dir / "state.json", "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, sort_keys=True)

    actor = ActorIdentity(actor_id="human-1", actor_type="human")
    provide_decision_answer(run, "d1", "yes", actor)
    provide_decision_answer(run, "d2", "no", actor)

    d = next_step(run, agent_id="codex", context=context)
    assert d.kind == "step"


def test_failed_step_blocks_run(tmp_path: Path) -> None:
    context, _ = _setup(tmp_path)

    run = start_mission_run(
        template_key="software-dev",
        inputs={},
        policy_snapshot=MissionPolicySnapshot(),
        context=context,
        run_store=tmp_path / "runs",
    )

    d1 = next_step(run, agent_id="codex", context=context)
    assert d1.kind == "step"

    d2 = next_step(run, agent_id="codex", result="failed", context=context)
    assert d2.kind == "blocked"
    assert "failed" in d2.reason


def test_frozen_template_used_not_live_file(tmp_path: Path) -> None:
    """Frozen template is byte-identical to original and used for planning."""
    context, mission_file = _setup(tmp_path)
    original_bytes = mission_file.read_bytes()

    run = start_mission_run(
        template_key="software-dev",
        inputs={},
        policy_snapshot=MissionPolicySnapshot(),
        context=context,
        run_store=tmp_path / "runs",
    )

    # Verify frozen template exists and matches original.
    run_dir = Path(run.run_dir)
    frozen = run_dir / "mission_template_frozen.yaml"
    assert frozen.exists()
    assert frozen.read_bytes() == original_bytes

    # Verify hash in state matches the frozen bytes.
    with open(run_dir / "state.json") as f:
        state = json.load(f)
    assert state["template_hash"] == hashlib.sha256(original_bytes).hexdigest()

    # First step comes from frozen template.
    d1 = next_step(run, agent_id="codex", context=context)
    assert d1.kind == "step"
    assert d1.step_id == "S1"

    # Modifying live file triggers drift detection (separate concern from frozen usage).
    mission_file.write_text(MISSION_YAML + "\n# extra\n", encoding="utf-8")
    d2 = next_step(run, agent_id="codex", result="success", context=context)
    assert d2.kind == "blocked"
    assert "Migration required" in d2.reason


def test_template_drift_blocks_active_run(tmp_path: Path) -> None:
    """Changing live file triggers drift detection and blocks the run.

    No manual state.json manipulation needed - engine now resolves the
    actual filesystem path at run start for key-based discoveries.
    """
    context, mission_file = _setup(tmp_path)

    run = start_mission_run(
        template_key="software-dev",
        inputs={},
        policy_snapshot=MissionPolicySnapshot(),
        context=context,
        run_store=tmp_path / "runs",
    )

    # Verify template_path was resolved to an actual file, not the key string.
    run_dir = Path(run.run_dir)
    with open(run_dir / "state.json", "r", encoding="utf-8") as f:
        state = json.load(f)
    assert Path(state["template_path"]).exists(), "template_path should be a resolved file path"

    # Modify live YAML so hash differs.
    mission_file.write_text(
        MISSION_YAML + "\n# extra comment to change hash\n",
        encoding="utf-8",
    )

    d = next_step(run, agent_id="codex", context=context)
    assert d.kind == "blocked"
    assert "Migration required" in d.reason


# ---------------------------------------------------------------------------
# P0: Input-keyed decision round-trip
# ---------------------------------------------------------------------------

def test_input_keyed_decision_roundtrip(tmp_path: Path) -> None:
    """requires_inputs triggers input-keyed decision that is answerable via provide_decision_answer."""
    yaml_with_inputs = """\
mission:
  key: input-test
  name: Input Test
  version: 1.0.0
steps:
  - id: S1
    title: Step One
    prompt: Do one
    requires_inputs: ["framework"]
  - id: S2
    title: Step Two
    prompt: Do two
"""
    context, _ = _setup(tmp_path, yaml_content=yaml_with_inputs, key="input-test")

    run = start_mission_run(
        template_key="input-test",
        inputs={},
        policy_snapshot=MissionPolicySnapshot(),
        context=context,
        run_store=tmp_path / "runs",
    )

    # First call: missing input returns decision_required with input-keyed decision_id.
    d1 = next_step(run, agent_id="codex", context=context)
    assert d1.kind == "decision_required"
    assert d1.decision_id == "input:framework"
    assert d1.input_key == "framework"
    assert "framework" in d1.question

    # Decision was persisted in pending_decisions.
    run_dir = Path(run.run_dir)
    with open(run_dir / "state.json", "r") as f:
        state = json.load(f)
    assert "input:framework" in state["pending_decisions"]

    # Answer the input-keyed decision.
    actor = ActorIdentity(actor_id="human-1", actor_type="human")
    provide_decision_answer(run, "input:framework", "React", actor)

    # Verify the answer was written into inputs (not just decisions).
    with open(run_dir / "state.json", "r") as f:
        state = json.load(f)
    assert state["inputs"]["framework"] == "React"
    assert "input:framework" not in state["pending_decisions"]
    assert "input:framework" in state["decisions"]

    # Now the step should proceed.
    d2 = next_step(run, agent_id="codex", context=context)
    assert d2.kind == "step"
    assert d2.step_id == "S1"


# ---------------------------------------------------------------------------
# P1: Policy persistence
# ---------------------------------------------------------------------------

def test_policy_snapshot_persisted_and_used(tmp_path: Path) -> None:
    """policy_snapshot from run start is persisted and used by next_step."""
    context, _ = _setup(tmp_path)

    custom_policy = MissionPolicySnapshot(strictness="max", default_route="separate_context")

    run = start_mission_run(
        template_key="software-dev",
        inputs={},
        policy_snapshot=custom_policy,
        context=context,
        run_store=tmp_path / "runs",
    )

    # Verify policy is persisted in state.
    run_dir = Path(run.run_dir)
    with open(run_dir / "state.json", "r") as f:
        state = json.load(f)
    assert state["policy_snapshot"]["strictness"] == "max"
    assert state["policy_snapshot"]["default_route"] == "separate_context"

    # Call next_step WITHOUT passing policy_snapshot - should use persisted one.
    d = next_step(run, agent_id="codex", context=context)
    assert d.kind == "step"
    assert d.context.policy_snapshot.strictness == "max"
    assert d.context.policy_snapshot.default_route == "separate_context"


# ---------------------------------------------------------------------------
# P1: Key-based drift detection (no manual state.json injection)
# ---------------------------------------------------------------------------

def test_drift_detection_works_for_key_based_discovery(tmp_path: Path) -> None:
    """Drift detection works out-of-the-box for key-based runs without manual path injection."""
    context, mission_file = _setup(tmp_path)

    run = start_mission_run(
        template_key="software-dev",
        inputs={},
        policy_snapshot=MissionPolicySnapshot(),
        context=context,
        run_store=tmp_path / "runs",
    )

    # No manual state.json manipulation - template_path is auto-resolved.
    mission_file.write_text(MISSION_YAML + "\n# drift\n", encoding="utf-8")

    d = next_step(run, agent_id="codex", context=context)
    assert d.kind == "blocked"
    assert "Migration required" in d.reason


# ---------------------------------------------------------------------------
# P1: Emitter wiring
# ---------------------------------------------------------------------------

def test_emitter_receives_calls(tmp_path: Path) -> None:
    """RuntimeEventEmitter receives calls from engine operations."""
    context, _ = _setup(tmp_path)
    calls: list[tuple[str, tuple]] = []

    class RecordingEmitter:
        def __init__(self, correlation_id: str = "") -> None:
            self.correlation_id = correlation_id

        def emit_mission_started(self, run_id, mission_key, actor):
            calls.append(("mission_started", (run_id, mission_key)))

        def emit_next_step_issued(self, run_id, step_id, agent_id):
            calls.append(("next_step_issued", (run_id, step_id, agent_id)))

        def emit_next_step_auto_completed(self, run_id, step_id, result, agent_id):
            calls.append(("next_step_auto_completed", (run_id, step_id, result, agent_id)))

        def emit_decision_requested(self, run_id, request):
            calls.append(("decision_requested", (run_id,)))

        def emit_decision_answered(self, run_id, answer):
            calls.append(("decision_answered", (run_id,)))

        def emit_mission_completed(self, run_id, mission_key):
            calls.append(("mission_completed", (run_id, mission_key)))

    emitter = RecordingEmitter()

    run = start_mission_run(
        template_key="software-dev",
        inputs={},
        policy_snapshot=MissionPolicySnapshot(),
        context=context,
        run_store=tmp_path / "runs",
    )

    # First next_step: issues S1.
    d1 = next_step(run, agent_id="codex", context=context, emitter=emitter)
    assert d1.step_id == "S1"
    assert any(c[0] == "next_step_issued" for c in calls)

    # Second next_step: auto-completes S1, issues S2.
    d2 = next_step(run, agent_id="codex", result="success", context=context, emitter=emitter)
    assert d2.step_id == "S2"
    assert any(c[0] == "next_step_auto_completed" for c in calls)


# ---------------------------------------------------------------------------
# P1: Event names use constants
# ---------------------------------------------------------------------------

def test_event_log_uses_canonical_names(tmp_path: Path) -> None:
    """JSONL event log uses constant names, not ad-hoc strings."""
    from spec_kitty_runtime.events import (
        DECISION_INPUT_REQUESTED,
        MISSION_RUN_STARTED,
        NEXT_STEP_AUTO_COMPLETED,
        NEXT_STEP_ISSUED,
    )

    context, _ = _setup(tmp_path)
    run = start_mission_run(
        template_key="software-dev",
        inputs={},
        policy_snapshot=MissionPolicySnapshot(),
        context=context,
        run_store=tmp_path / "runs",
    )

    next_step(run, agent_id="codex", context=context)
    next_step(run, agent_id="codex", result="success", context=context)

    # Read the JSONL events.
    run_dir = Path(run.run_dir)
    events = []
    with open(run_dir / "run.events.jsonl", "r") as f:
        for line in f:
            events.append(json.loads(line.strip()))

    event_types = [e["event_type"] for e in events]
    assert MISSION_RUN_STARTED in event_types
    assert NEXT_STEP_ISSUED in event_types
    assert NEXT_STEP_AUTO_COMPLETED in event_types


# ---------------------------------------------------------------------------
# input_key preserved on re-poll of pending decision
# ---------------------------------------------------------------------------

def test_input_key_preserved_on_repoll(tmp_path: Path) -> None:
    """Repeated next() calls for the same pending input decision still return input_key."""
    yaml_with_inputs = """\
mission:
  key: repoll-test
  name: Repoll Test
  version: 1.0.0
steps:
  - id: S1
    title: Step One
    prompt: Do one
    requires_inputs: ["approach"]
"""
    context, _ = _setup(tmp_path, yaml_content=yaml_with_inputs, key="repoll-test")

    run = start_mission_run(
        template_key="repoll-test",
        inputs={},
        policy_snapshot=MissionPolicySnapshot(),
        context=context,
        run_store=tmp_path / "runs",
    )

    # First call creates the pending decision.
    d1 = next_step(run, agent_id="codex", context=context)
    assert d1.kind == "decision_required"
    assert d1.decision_id == "input:approach"
    assert d1.input_key == "approach"

    # Second call re-reads from pending_decisions — input_key must still be present.
    d2 = next_step(run, agent_id="codex", context=context)
    assert d2.kind == "decision_required"
    assert d2.decision_id == "input:approach"
    assert d2.input_key == "approach"
    assert d2.step_id == "S1"


# ---------------------------------------------------------------------------
# Emitter fires all protocol methods at correct lifecycle points
# ---------------------------------------------------------------------------

def test_emitter_full_lifecycle(tmp_path: Path) -> None:
    """Emitter receives mission_started, step_issued, auto_completed, decision_requested, mission_completed."""
    yaml_with_inputs = """\
mission:
  key: lifecycle-test
  name: Lifecycle Test
  version: 1.0.0
steps:
  - id: S1
    title: Step One
    prompt: Do one
    requires_inputs: ["x"]
  - id: S2
    title: Step Two
    prompt: Do two
"""
    context, _ = _setup(tmp_path, yaml_content=yaml_with_inputs, key="lifecycle-test")
    calls: list[str] = []

    class LifecycleEmitter:
        def __init__(self, correlation_id=""): self.correlation_id = correlation_id
        def emit_mission_started(self, *a): calls.append("mission_started")
        def emit_next_step_issued(self, *a): calls.append("next_step_issued")
        def emit_next_step_auto_completed(self, *a): calls.append("next_step_auto_completed")
        def emit_decision_requested(self, *a): calls.append("decision_requested")
        def emit_decision_answered(self, *a): calls.append("decision_answered")
        def emit_mission_completed(self, *a): calls.append("mission_completed")

    emitter = LifecycleEmitter()

    run = start_mission_run(
        template_key="lifecycle-test",
        inputs={},
        policy_snapshot=MissionPolicySnapshot(),
        context=context,
        run_store=tmp_path / "runs",
        emitter=emitter,
    )
    assert "mission_started" in calls

    # Missing input -> decision_requested.
    d = next_step(run, agent_id="a", context=context, emitter=emitter)
    assert d.kind == "decision_required"
    assert "decision_requested" in calls

    # Answer the input.
    actor = ActorIdentity(actor_id="h1", actor_type="human")
    provide_decision_answer(run, "input:x", "val", actor, emitter=emitter)
    assert "decision_answered" in calls

    # Now S1 is issued.
    d = next_step(run, agent_id="a", context=context, emitter=emitter)
    assert d.kind == "step" and d.step_id == "S1"
    assert "next_step_issued" in calls

    # Complete S1, get S2.
    d = next_step(run, agent_id="a", result="success", context=context, emitter=emitter)
    assert d.kind == "step" and d.step_id == "S2"
    assert "next_step_auto_completed" in calls

    # Complete S2, terminal.
    d = next_step(run, agent_id="a", result="success", context=context, emitter=emitter)
    assert d.kind == "terminal"
    assert "mission_completed" in calls


# ---------------------------------------------------------------------------
# No duplicate DecisionInputRequested events on re-poll
# ---------------------------------------------------------------------------

def test_no_duplicate_decision_events_on_repoll(tmp_path: Path) -> None:
    """Polling the same pending decision multiple times emits only one DecisionInputRequested event."""
    yaml_with_inputs = """\
mission:
  key: dedup-test
  name: Dedup Test
  version: 1.0.0
steps:
  - id: S1
    title: Step One
    prompt: Do one
    requires_inputs: ["thing"]
"""
    context, _ = _setup(tmp_path, yaml_content=yaml_with_inputs, key="dedup-test")

    run = start_mission_run(
        template_key="dedup-test",
        inputs={},
        policy_snapshot=MissionPolicySnapshot(),
        context=context,
        run_store=tmp_path / "runs",
    )

    # First poll: creates the pending decision and emits event.
    next_step(run, agent_id="a", context=context)
    # Second poll: decision already pending, should NOT emit another event.
    next_step(run, agent_id="a", context=context)
    # Third poll.
    next_step(run, agent_id="a", context=context)

    run_dir = Path(run.run_dir)
    events = []
    with open(run_dir / "run.events.jsonl", "r") as f:
        for line in f:
            events.append(json.loads(line.strip()))

    decision_events = [e for e in events if e["event_type"] == "DecisionInputRequested"]
    assert len(decision_events) == 1, f"Expected 1 DecisionInputRequested, got {len(decision_events)}"


# ---------------------------------------------------------------------------
# MissionCompleted event emitted on terminal
# ---------------------------------------------------------------------------

def test_mission_completed_event_on_terminal(tmp_path: Path) -> None:
    """MissionCompleted event is emitted in JSONL when run reaches terminal."""
    from spec_kitty_runtime.events import MISSION_COMPLETED

    context, _ = _setup(tmp_path)
    run = start_mission_run(
        template_key="software-dev",
        inputs={},
        policy_snapshot=MissionPolicySnapshot(),
        context=context,
        run_store=tmp_path / "runs",
    )

    next_step(run, agent_id="a", context=context)
    next_step(run, agent_id="a", result="success", context=context)
    d = next_step(run, agent_id="a", result="success", context=context)
    assert d.kind == "terminal"

    run_dir = Path(run.run_dir)
    events = []
    with open(run_dir / "run.events.jsonl", "r") as f:
        for line in f:
            events.append(json.loads(line.strip()))

    completed_events = [e for e in events if e["event_type"] == MISSION_COMPLETED]
    assert len(completed_events) == 1


# ---------------------------------------------------------------------------
# Regression: MissionCompleted must be emitted exactly once across re-polls
# ---------------------------------------------------------------------------

def test_mission_completed_emitted_exactly_once_on_repeated_polls(tmp_path: Path) -> None:
    """Calling next_step() after terminal must NOT emit additional MissionCompleted events.

    Regression test for idempotency: the terminal transition emits exactly one
    MissionCompleted event (JSONL + emitter), and subsequent polls produce no more.
    """
    from spec_kitty_runtime.events import MISSION_COMPLETED

    context, _ = _setup(tmp_path)
    emitter_calls: list[str] = []

    class CountingEmitter:
        def __init__(self, correlation_id=""): self.correlation_id = correlation_id
        def emit_mission_started(self, *a): emitter_calls.append("mission_started")
        def emit_next_step_issued(self, *a): emitter_calls.append("next_step_issued")
        def emit_next_step_auto_completed(self, *a): emitter_calls.append("next_step_auto_completed")
        def emit_decision_requested(self, *a): emitter_calls.append("decision_requested")
        def emit_decision_answered(self, *a): emitter_calls.append("decision_answered")
        def emit_mission_completed(self, *a): emitter_calls.append("mission_completed")

    emitter = CountingEmitter()

    run = start_mission_run(
        template_key="software-dev",
        inputs={},
        policy_snapshot=MissionPolicySnapshot(),
        context=context,
        run_store=tmp_path / "runs",
        emitter=emitter,
    )

    # Drive to terminal: issue S1, complete S1 + issue S2, complete S2 -> terminal.
    next_step(run, agent_id="a", context=context, emitter=emitter)
    next_step(run, agent_id="a", result="success", context=context, emitter=emitter)
    d = next_step(run, agent_id="a", result="success", context=context, emitter=emitter)
    assert d.kind == "terminal"

    # At this point exactly one MissionCompleted should exist.
    assert emitter_calls.count("mission_completed") == 1

    # Poll 3 more times after terminal — must remain at exactly 1.
    for _ in range(3):
        d = next_step(run, agent_id="a", context=context, emitter=emitter)
        assert d.kind == "terminal"

    assert emitter_calls.count("mission_completed") == 1, (
        f"Expected exactly 1 mission_completed call, got {emitter_calls.count('mission_completed')}"
    )

    # Verify JSONL log also has exactly one MissionCompleted event.
    run_dir = Path(run.run_dir)
    events = []
    with open(run_dir / "run.events.jsonl", "r") as f:
        for line in f:
            events.append(json.loads(line.strip()))

    completed_events = [e for e in events if e["event_type"] == MISSION_COMPLETED]
    assert len(completed_events) == 1, (
        f"Expected exactly 1 MissionCompleted in JSONL, got {len(completed_events)}"
    )

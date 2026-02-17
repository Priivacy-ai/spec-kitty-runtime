"""Contract parity tests: validate emitted payloads against canonical spec-kitty-events models."""

import json
from pathlib import Path

from spec_kitty_events.mission_next import (
    DECISION_INPUT_ANSWERED,
    DECISION_INPUT_REQUESTED,
    MISSION_RUN_COMPLETED,
    MISSION_RUN_STARTED,
    NEXT_STEP_AUTO_COMPLETED,
    NEXT_STEP_ISSUED,
    DecisionInputAnsweredPayload,
    DecisionInputRequestedPayload,
    MissionRunCompletedPayload,
    MissionRunStartedPayload,
    NextStepAutoCompletedPayload,
    NextStepIssuedPayload,
)

from spec_kitty_runtime.discovery import DiscoveryContext
from spec_kitty_runtime.engine import next_step, provide_decision_answer, start_mission_run
from spec_kitty_runtime.schema import ActorIdentity, MissionPolicySnapshot


LIFECYCLE_YAML = """\
mission:
  key: parity-test
  name: Parity Test
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


def _setup(tmp_path: Path) -> tuple[DiscoveryContext, Path]:
    mission_file = tmp_path / "pack" / "missions" / "parity-test" / "mission.yaml"
    mission_file.parent.mkdir(parents=True, exist_ok=True)
    mission_file.write_text(LIFECYCLE_YAML, encoding="utf-8")
    context = DiscoveryContext(explicit_paths=[tmp_path / "pack"], builtin_roots=[])
    return context, mission_file


# ---------------------------------------------------------------------------
# Map event_type string -> canonical payload model class
# ---------------------------------------------------------------------------

EVENT_TYPE_TO_MODEL = {
    MISSION_RUN_STARTED: MissionRunStartedPayload,
    NEXT_STEP_ISSUED: NextStepIssuedPayload,
    NEXT_STEP_AUTO_COMPLETED: NextStepAutoCompletedPayload,
    DECISION_INPUT_REQUESTED: DecisionInputRequestedPayload,
    DECISION_INPUT_ANSWERED: DecisionInputAnsweredPayload,
    MISSION_RUN_COMPLETED: MissionRunCompletedPayload,
}


class RecordingEmitter:
    """Captures payload objects for parity validation."""

    def __init__(self, correlation_id: str = "") -> None:
        self.correlation_id = correlation_id
        self.payloads: list[tuple[str, object]] = []

    def emit_mission_run_started(self, payload):
        self.payloads.append((MISSION_RUN_STARTED, payload))

    def emit_next_step_issued(self, payload):
        self.payloads.append((NEXT_STEP_ISSUED, payload))

    def emit_next_step_auto_completed(self, payload):
        self.payloads.append((NEXT_STEP_AUTO_COMPLETED, payload))

    def emit_decision_input_requested(self, payload):
        self.payloads.append((DECISION_INPUT_REQUESTED, payload))

    def emit_decision_input_answered(self, payload):
        self.payloads.append((DECISION_INPUT_ANSWERED, payload))

    def emit_mission_run_completed(self, payload):
        self.payloads.append((MISSION_RUN_COMPLETED, payload))


def _run_full_lifecycle(tmp_path: Path) -> tuple[RecordingEmitter, Path]:
    """Drive a complete mission lifecycle and return the recording emitter + run_dir."""
    context, _ = _setup(tmp_path)
    emitter = RecordingEmitter()

    run = start_mission_run(
        template_key="parity-test",
        inputs={},
        policy_snapshot=MissionPolicySnapshot(),
        context=context,
        run_store=tmp_path / "runs",
        emitter=emitter,
    )

    # Decision required for missing input.
    d = next_step(run, agent_id="codex", context=context, emitter=emitter)
    assert d.kind == "decision_required"

    # Answer the decision.
    actor = ActorIdentity(actor_id="human-1", actor_type="human")
    provide_decision_answer(run, "input:framework", "React", actor, emitter=emitter)

    # S1 issued.
    d = next_step(run, agent_id="codex", context=context, emitter=emitter)
    assert d.kind == "step" and d.step_id == "S1"

    # Complete S1 -> S2 issued.
    d = next_step(run, agent_id="codex", result="success", context=context, emitter=emitter)
    assert d.kind == "step" and d.step_id == "S2"

    # Complete S2 -> terminal.
    d = next_step(run, agent_id="codex", result="success", context=context, emitter=emitter)
    assert d.kind == "terminal"

    return emitter, Path(run.run_dir)


# ---------------------------------------------------------------------------
# Test 1: Emitted payloads are instances of canonical model classes
# ---------------------------------------------------------------------------

def test_emitted_payloads_are_canonical_instances(tmp_path: Path) -> None:
    """Every payload emitted by the engine is an instance of its canonical model."""
    emitter, _ = _run_full_lifecycle(tmp_path)

    for event_type, payload in emitter.payloads:
        expected_cls = EVENT_TYPE_TO_MODEL[event_type]
        assert isinstance(payload, expected_cls), (
            f"Expected {expected_cls.__name__} for {event_type}, got {type(payload).__name__}"
        )


# ---------------------------------------------------------------------------
# Test 2: JSONL payloads round-trip through canonical models
# ---------------------------------------------------------------------------

def test_jsonl_payloads_validate_as_canonical_models(tmp_path: Path) -> None:
    """Every JSONL event payload can be parsed by its canonical model."""
    _, run_dir = _run_full_lifecycle(tmp_path)

    events = []
    with open(run_dir / "run.events.jsonl", "r") as f:
        for line in f:
            events.append(json.loads(line.strip()))

    for event in events:
        event_type = event["event_type"]
        payload_dict = event["payload"]
        model_cls = EVENT_TYPE_TO_MODEL.get(event_type)
        assert model_cls is not None, f"Unknown event type in JSONL: {event_type}"
        # Validate by constructing the model from the payload dict.
        parsed = model_cls(**payload_dict)
        assert parsed.run_id, f"Missing run_id in {event_type} payload"
        assert parsed.actor, f"Missing actor in {event_type} payload"


# ---------------------------------------------------------------------------
# Test 3: DecisionInputRequestedPayload includes input_key and options
# ---------------------------------------------------------------------------

def test_decision_payload_includes_input_key_and_options(tmp_path: Path) -> None:
    """DecisionInputRequestedPayload has input_key and options fields set."""
    emitter, _ = _run_full_lifecycle(tmp_path)

    decision_payloads = [
        p for et, p in emitter.payloads if et == DECISION_INPUT_REQUESTED
    ]
    assert len(decision_payloads) == 1

    payload = decision_payloads[0]
    assert isinstance(payload, DecisionInputRequestedPayload)
    assert payload.input_key == "framework"
    assert payload.decision_id == "input:framework"
    assert payload.step_id == "S1"


# ---------------------------------------------------------------------------
# Test 4: Terminal idempotency — re-polls emit zero additional events
# ---------------------------------------------------------------------------

def test_terminal_idempotency_no_extra_events(tmp_path: Path) -> None:
    """Re-polling after terminal emits zero additional events."""
    context, _ = _setup(tmp_path)

    simple_yaml = """\
mission:
  key: idem-test
  name: Idem Test
  version: 1.0.0
steps:
  - id: S1
    title: Step One
    prompt: Do one
"""
    mission_file = tmp_path / "pack" / "missions" / "idem-test" / "mission.yaml"
    mission_file.parent.mkdir(parents=True, exist_ok=True)
    mission_file.write_text(simple_yaml, encoding="utf-8")
    context = DiscoveryContext(explicit_paths=[tmp_path / "pack"], builtin_roots=[])
    emitter = RecordingEmitter()

    run = start_mission_run(
        template_key="idem-test",
        inputs={},
        policy_snapshot=MissionPolicySnapshot(),
        context=context,
        run_store=tmp_path / "runs",
        emitter=emitter,
    )

    # Issue S1.
    next_step(run, agent_id="a", context=context, emitter=emitter)
    # Complete S1 -> terminal.
    d = next_step(run, agent_id="a", result="success", context=context, emitter=emitter)
    assert d.kind == "terminal"

    count_at_terminal = len(emitter.payloads)

    # Re-poll 3 times.
    for _ in range(3):
        d = next_step(run, agent_id="a", context=context, emitter=emitter)
        assert d.kind == "terminal"

    assert len(emitter.payloads) == count_at_terminal, (
        f"Expected no additional emitter calls after terminal, got {len(emitter.payloads) - count_at_terminal} extra"
    )


# ---------------------------------------------------------------------------
# Test 5: All canonical event types appear in full lifecycle
# ---------------------------------------------------------------------------

def test_all_canonical_event_types_emitted(tmp_path: Path) -> None:
    """A full lifecycle emits all 6 canonical event types."""
    emitter, _ = _run_full_lifecycle(tmp_path)

    emitted_types = {et for et, _ in emitter.payloads}
    expected = {
        MISSION_RUN_STARTED,
        NEXT_STEP_ISSUED,
        NEXT_STEP_AUTO_COMPLETED,
        DECISION_INPUT_REQUESTED,
        DECISION_INPUT_ANSWERED,
        MISSION_RUN_COMPLETED,
    }
    assert expected == emitted_types, f"Missing event types: {expected - emitted_types}"

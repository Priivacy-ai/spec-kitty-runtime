"""Tests for event emission infrastructure."""

from pathlib import Path

from spec_kitty_events.mission_next import (
    DecisionInputAnsweredPayload,
    DecisionInputRequestedPayload,
    MissionRunCompletedPayload,
    MissionRunStartedPayload,
    NextStepAutoCompletedPayload,
    NextStepIssuedPayload,
    RuntimeActorIdentity,
)
from spec_kitty_runtime.events import JsonlEventLog, NullEmitter


def test_null_emitter_is_noop() -> None:
    """NullEmitter methods are callable and do nothing."""
    emitter = NullEmitter(correlation_id="test-corr")
    assert emitter.correlation_id == "test-corr"

    actor = RuntimeActorIdentity(actor_id="a1", actor_type="llm")
    emitter.emit_mission_run_started(
        MissionRunStartedPayload(run_id="r1", mission_key="key", actor=actor)
    )
    emitter.emit_next_step_issued(
        NextStepIssuedPayload(run_id="r1", step_id="S1", agent_id="agent-1", actor=actor)
    )
    emitter.emit_next_step_auto_completed(
        NextStepAutoCompletedPayload(run_id="r1", step_id="S1", agent_id="agent-1", result="success", actor=actor)
    )
    emitter.emit_decision_input_requested(
        DecisionInputRequestedPayload(run_id="r1", decision_id="d1", step_id="S1", question="Q?", actor=actor)
    )
    emitter.emit_decision_input_answered(
        DecisionInputAnsweredPayload(run_id="r1", decision_id="d1", answer="A", actor=actor)
    )
    emitter.emit_mission_run_completed(
        MissionRunCompletedPayload(run_id="r1", mission_key="key", actor=actor)
    )


def test_jsonl_log_append_and_read_roundtrip(tmp_path: Path) -> None:
    """Records appended to JSONL can be read back identically."""
    log = JsonlEventLog(tmp_path / "events.jsonl")

    log.append({"event_type": "A", "data": 1})
    log.append({"event_type": "B", "data": 2})

    records = log.read_all()
    assert len(records) == 2
    assert records[0]["event_type"] == "A"
    assert records[0]["data"] == 1
    assert records[1]["event_type"] == "B"
    assert records[1]["data"] == 2


def test_jsonl_log_sort_keys_determinism(tmp_path: Path) -> None:
    """JSONL output uses sort_keys for deterministic ordering."""
    log = JsonlEventLog(tmp_path / "events.jsonl")

    log.append({"zebra": 1, "alpha": 2, "middle": 3})

    raw_line = (tmp_path / "events.jsonl").read_text().strip()
    # With sort_keys, alpha comes before middle comes before zebra.
    assert raw_line.index('"alpha"') < raw_line.index('"middle"')
    assert raw_line.index('"middle"') < raw_line.index('"zebra"')


def test_jsonl_log_read_empty(tmp_path: Path) -> None:
    """Reading a non-existent log returns empty list."""
    log = JsonlEventLog(tmp_path / "nonexistent.jsonl")
    assert log.read_all() == []

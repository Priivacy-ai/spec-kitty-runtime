"""Tests for event emission infrastructure."""

from pathlib import Path

from spec_kitty_runtime.events import JsonlEventLog, NullEmitter
from spec_kitty_runtime.schema import ActorIdentity, DecisionRequest


def test_null_emitter_is_noop() -> None:
    """NullEmitter methods are callable and do nothing."""
    emitter = NullEmitter(correlation_id="test-corr")
    assert emitter.correlation_id == "test-corr"

    actor = ActorIdentity(actor_id="a1", actor_type="llm")
    emitter.emit_mission_started("r1", "key", actor)
    emitter.emit_next_step_issued("r1", "S1", "agent-1")
    emitter.emit_next_step_auto_completed("r1", "S1", "success", "agent-1")
    emitter.emit_mission_completed("r1", "key")


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

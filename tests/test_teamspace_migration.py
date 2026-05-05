"""Runtime log classification for TeamSpace launch migration."""

from __future__ import annotations

from pathlib import Path

from spec_kitty_runtime.teamspace_migration import (
    RUNTIME_SIDE_LOG_DISPOSITION,
    RUNTIME_SIDE_LOG_REASON,
    classify_runtime_log,
    is_runtime_side_log_event_type,
    is_teamspace_status_authority_event_type,
)


FIXTURE = Path(__file__).parent / "fixtures" / "teamspace_migration" / "runtime_side_log.jsonl"


def test_runtime_side_log_fixture_is_reported_as_deferred_local_side_log() -> None:
    classification = classify_runtime_log(FIXTURE, display_path=".kittify/runtime/runs/run-001/run.events.jsonl")

    assert classification.row_count == 4
    assert classification.disposition == RUNTIME_SIDE_LOG_DISPOSITION
    assert classification.reason == RUNTIME_SIDE_LOG_REASON
    assert not classification.status_authority
    assert not classification.direct_teamspace_import
    assert classification.unknown_event_types == ()
    assert classification.event_type_counts == {
        "MissionNextInvoked": 1,
        "MissionRunCompleted": 1,
        "MissionRunStarted": 1,
        "NextStepIssued": 1,
    }


def test_runtime_event_types_are_not_wp_status_authority() -> None:
    for event_type in ("MissionNextInvoked", "NextStepIssued", "MissionRunStarted", "MissionRunCompleted"):
        assert is_runtime_side_log_event_type(event_type)
        assert not is_teamspace_status_authority_event_type(event_type)

    assert is_teamspace_status_authority_event_type("WPStatusChanged")

"""TeamSpace launch-migration classification for runtime side logs.

Runtime ``run.events.jsonl`` files are local mission-next audit logs. They
carry canonical mission-next payloads, but they are not WP status authority and
are not full TeamSpace event envelopes for the launch migration.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

RUNTIME_SIDE_LOG_DISPOSITION = "local_only_side_log"
RUNTIME_SIDE_LOG_REASON = "deferred_not_launch_import"

RUNTIME_SIDE_LOG_EVENT_TYPES = frozenset(
    {
        "MissionNextInvoked",
        "MissionRunStarted",
        "NextStepIssued",
        "NextStepAutoCompleted",
        "DecisionInputRequested",
        "DecisionInputAnswered",
        "MissionRunCompleted",
        "SignificanceEvaluated",
        "DecisionTimeoutExpired",
    }
)

TEAMSPACE_STATUS_EVENT_TYPES = frozenset({"WPStatusChanged"})


@dataclass(frozen=True)
class RuntimeLogClassification:
    """Classification summary for one runtime JSONL log."""

    artifact_path: str
    row_count: int
    event_type_counts: dict[str, int]
    unknown_event_types: tuple[str, ...]
    disposition: str = RUNTIME_SIDE_LOG_DISPOSITION
    reason: str = RUNTIME_SIDE_LOG_REASON
    status_authority: bool = False
    direct_teamspace_import: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_path": self.artifact_path,
            "row_count": self.row_count,
            "event_type_counts": dict(self.event_type_counts),
            "unknown_event_types": list(self.unknown_event_types),
            "disposition": self.disposition,
            "reason": self.reason,
            "status_authority": self.status_authority,
            "direct_teamspace_import": self.direct_teamspace_import,
        }


def classify_runtime_log(path: Path, *, display_path: str | None = None) -> RuntimeLogClassification:
    """Classify a runtime ``run.events.jsonl`` file for TeamSpace migration.

    The classifier is deterministic and read-only. It never attempts to adapt
    runtime rows into TeamSpace envelopes; launch migration should report them
    as explicit side logs.
    """
    event_type_counts: Counter[str] = Counter()
    row_count = 0
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            row_count += 1
            row = json.loads(stripped)
            event_type = row.get("event_type") if isinstance(row, dict) else None
            event_type_counts[str(event_type or "<missing>")] += 1

    unknown = tuple(sorted(key for key in event_type_counts if key not in RUNTIME_SIDE_LOG_EVENT_TYPES))
    return RuntimeLogClassification(
        artifact_path=display_path or str(path),
        row_count=row_count,
        event_type_counts=dict(sorted(event_type_counts.items())),
        unknown_event_types=unknown,
    )


def is_runtime_side_log_event_type(event_type: str) -> bool:
    """Return True for event types treated as runtime side logs at launch."""
    return event_type in RUNTIME_SIDE_LOG_EVENT_TYPES


def is_teamspace_status_authority_event_type(event_type: str) -> bool:
    """Return True only for TeamSpace status-authority event types."""
    return event_type in TEAMSPACE_STATUS_EVENT_TYPES


__all__ = [
    "RUNTIME_SIDE_LOG_DISPOSITION",
    "RUNTIME_SIDE_LOG_EVENT_TYPES",
    "RUNTIME_SIDE_LOG_REASON",
    "RuntimeLogClassification",
    "classify_runtime_log",
    "is_runtime_side_log_event_type",
    "is_teamspace_status_authority_event_type",
]

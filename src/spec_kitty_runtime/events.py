"""Mission runtime event emission interface and persistence.

Concrete event emission is blocked until spec-kitty-events ships
mission-next payload contracts. Until then, engine uses NullEmitter.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Protocol

from spec_kitty_runtime.schema import ActorIdentity, DecisionAnswer, DecisionRequest

# ---------------------------------------------------------------------------
# Required event types (pending spec-kitty-events contracts)
# ---------------------------------------------------------------------------

MISSION_RUN_STARTED = "MissionRunStarted"
NEXT_STEP_PLANNED = "NextStepPlanned"
NEXT_STEP_ISSUED = "NextStepIssued"
NEXT_STEP_AUTO_COMPLETED = "NextStepAutoCompleted"
DECISION_INPUT_REQUESTED = "DecisionInputRequested"
DECISION_INPUT_ANSWERED = "DecisionInputAnswered"
DECISION_RESOLVED = "DecisionResolved"
MISSION_COMPLETED = "MissionCompleted"
TEMPLATE_MIGRATION_REQUIRED = "TemplateMigrationRequired"


# ---------------------------------------------------------------------------
# RuntimeEventEmitter protocol
# ---------------------------------------------------------------------------

class RuntimeEventEmitter(Protocol):
    """Interface for mission runtime event emission.

    Concrete implementation is blocked until spec-kitty-events ships
    mission-next payload contracts. Until then, engine uses NullEmitter.

    Implementations MUST accept correlation_id in __init__(), set before
    any emit_* call. No lazy initialization.
    """

    def emit_mission_started(self, run_id: str, mission_key: str, actor: ActorIdentity) -> None: ...

    def emit_next_step_issued(self, run_id: str, step_id: str, agent_id: str) -> None: ...

    def emit_next_step_auto_completed(self, run_id: str, step_id: str, result: str, agent_id: str) -> None: ...

    def emit_decision_requested(self, run_id: str, request: DecisionRequest) -> None: ...

    def emit_decision_answered(self, run_id: str, answer: DecisionAnswer) -> None: ...

    def emit_mission_completed(self, run_id: str, mission_key: str) -> None: ...


# ---------------------------------------------------------------------------
# NullEmitter (no-op, used until contracts land)
# ---------------------------------------------------------------------------

class NullEmitter:
    """No-op emitter used while event contracts are pending."""

    def __init__(self, correlation_id: str = "") -> None:
        self.correlation_id = correlation_id

    def emit_mission_started(self, run_id: str, mission_key: str, actor: ActorIdentity) -> None:
        pass

    def emit_next_step_issued(self, run_id: str, step_id: str, agent_id: str) -> None:
        pass

    def emit_next_step_auto_completed(self, run_id: str, step_id: str, result: str, agent_id: str) -> None:
        pass

    def emit_decision_requested(self, run_id: str, request: DecisionRequest) -> None:
        pass

    def emit_decision_answered(self, run_id: str, answer: DecisionAnswer) -> None:
        pass

    def emit_mission_completed(self, run_id: str, mission_key: str) -> None:
        pass


# ---------------------------------------------------------------------------
# JsonlEventLog (append-only JSONL persistence)
# ---------------------------------------------------------------------------

class JsonlEventLog:
    """Append-only JSONL log. Writes dicts with sort_keys for determinism.

    Engine uses JsonlEventLog for raw persistence (pre-event-contract).
    When contracts land, JsonlEventLog.append() will accept
    Event.model_dump() output directly.
    """

    def __init__(self, path: Path) -> None:
        self._path = path

    @property
    def path(self) -> Path:
        return self._path

    def append(self, record: dict[str, Any]) -> None:
        """Append a single record as a JSON line."""
        line = json.dumps(record, sort_keys=True, separators=(",", ":"), default=str)
        with open(self._path, "a", encoding="utf-8") as handle:
            handle.write(line + "\n")

    def read_all(self) -> list[dict[str, Any]]:
        """Read all records from the log file."""
        if not self._path.exists():
            return []
        records: list[dict[str, Any]] = []
        with open(self._path, "r", encoding="utf-8") as handle:
            for line in handle:
                stripped = line.strip()
                if stripped:
                    records.append(json.loads(stripped))
        return records

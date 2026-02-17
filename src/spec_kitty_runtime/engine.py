"""Mission run engine for deterministic `next()` progression."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from spec_kitty_runtime.discovery import DiscoveryContext, load_mission_template
from spec_kitty_runtime.planner import plan_next
from spec_kitty_runtime.schema import (
    MissionPolicySnapshot,
    MissionRunSnapshot,
    NextDecision,
)


ResultType = Literal["success", "failed", "blocked"]


class MissionRunRef(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: str
    run_dir: str
    mission_key: str


def _runtime_runs_dir(run_store: Path | None = None) -> Path:
    if run_store is not None:
        return run_store
    return Path.cwd() / ".kittify" / "runtime" / "runs"


def _append_event(run_dir: Path, event_type: str, payload: dict[str, Any]) -> None:
    event_file = run_dir / "run.events.jsonl"
    event = {
        "event_type": event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": payload,
    }
    with open(event_file, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True) + "\n")


def _read_snapshot(run_dir: Path) -> MissionRunSnapshot:
    with open(run_dir / "state.json", "r", encoding="utf-8") as handle:
        raw = json.load(handle)
    return MissionRunSnapshot.model_validate(raw)


def _write_snapshot(run_dir: Path, snapshot: MissionRunSnapshot) -> None:
    with open(run_dir / "state.json", "w", encoding="utf-8") as handle:
        json.dump(snapshot.model_dump(), handle, indent=2, sort_keys=True)


def start_mission_run(
    template_key: str,
    inputs: dict[str, Any] | None,
    policy_snapshot: MissionPolicySnapshot,
    context: DiscoveryContext | None = None,
    run_store: Path | None = None,
) -> MissionRunRef:
    """Start and persist a new mission run."""
    template = load_mission_template(template_key, context=context)

    runs_dir = _runtime_runs_dir(run_store)
    run_id = uuid4().hex
    run_dir = runs_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=False)

    template_path = template_key
    if Path(template_key).exists():
        template_path = str(Path(template_key).resolve())

    snapshot = MissionRunSnapshot(
        run_id=run_id,
        mission_key=template.mission.key,
        template_path=template_path,
        step_index=0,
        issued_step_id=None,
        completed_steps=[],
        inputs=inputs or {},
        decisions={},
        blocked_reason=None,
    )
    _write_snapshot(run_dir, snapshot)
    _append_event(run_dir, "MissionRunStarted", {"mission_key": template.mission.key})

    return MissionRunRef(run_id=run_id, run_dir=str(run_dir), mission_key=template.mission.key)


def next_step(
    run_ref: MissionRunRef,
    agent_id: str,
    result: ResultType = "success",
    policy_snapshot: MissionPolicySnapshot | None = None,
    actor_context: dict[str, Any] | None = None,
    context: DiscoveryContext | None = None,
) -> NextDecision:
    """Advance current issued step and compute the next deterministic decision."""
    policy_snapshot = policy_snapshot or MissionPolicySnapshot()
    actor_context = actor_context or {}

    run_dir = Path(run_ref.run_dir)
    snapshot = _read_snapshot(run_dir)
    template = load_mission_template(snapshot.template_path or snapshot.mission_key, context=context)

    if snapshot.issued_step_id:
        completed_steps = list(snapshot.completed_steps)
        blocked_reason = snapshot.blocked_reason
        step_index = snapshot.step_index

        if result == "success":
            if snapshot.issued_step_id not in completed_steps:
                completed_steps.append(snapshot.issued_step_id)
            step_index += 1
        elif result == "failed":
            blocked_reason = f"Previous step '{snapshot.issued_step_id}' failed; manual intervention required."
        elif result == "blocked":
            blocked_reason = f"Previous step '{snapshot.issued_step_id}' reported blocked state."

        snapshot = MissionRunSnapshot(
            run_id=snapshot.run_id,
            mission_key=snapshot.mission_key,
            template_path=snapshot.template_path,
            step_index=step_index,
            issued_step_id=None,
            completed_steps=completed_steps,
            inputs=snapshot.inputs,
            decisions=snapshot.decisions,
            blocked_reason=blocked_reason,
        )
        _append_event(
            run_dir,
            "NextStepAutoCompleted",
            {
                "agent_id": agent_id,
                "result": result,
            },
        )

    decision = plan_next(snapshot, template, policy_snapshot, actor_context={**actor_context, "agent_id": agent_id})

    issued_step_id = snapshot.issued_step_id
    if decision.kind == "step" and decision.step_id:
        issued_step_id = decision.step_id
        _append_event(
            run_dir,
            "NextStepIssued",
            {
                "agent_id": agent_id,
                "step_id": decision.step_id,
            },
        )
    elif decision.kind == "decision_required":
        _append_event(
            run_dir,
            "DecisionInputRequested",
            {
                "agent_id": agent_id,
                "question": decision.question,
            },
        )

    snapshot = MissionRunSnapshot(
        run_id=snapshot.run_id,
        mission_key=snapshot.mission_key,
        template_path=snapshot.template_path,
        step_index=snapshot.step_index,
        issued_step_id=issued_step_id,
        completed_steps=snapshot.completed_steps,
        inputs=snapshot.inputs,
        decisions=snapshot.decisions,
        blocked_reason=snapshot.blocked_reason,
    )
    _write_snapshot(run_dir, snapshot)

    return decision

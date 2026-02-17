"""Mission run engine for deterministic `next()` progression."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

import yaml
from pydantic import BaseModel, ConfigDict

from spec_kitty_runtime.discovery import DiscoveryContext, discover_missions, load_mission_template
from spec_kitty_events.mission_next import (
    DecisionInputAnsweredPayload,
    DecisionInputRequestedPayload,
    MissionRunCompletedPayload,
    MissionRunStartedPayload,
    NextStepAutoCompletedPayload,
    NextStepIssuedPayload,
    RuntimeActorIdentity,
)
from spec_kitty_runtime.events import (
    DECISION_INPUT_ANSWERED,
    DECISION_INPUT_REQUESTED,
    MISSION_RUN_COMPLETED,
    MISSION_RUN_STARTED,
    NEXT_STEP_AUTO_COMPLETED,
    NEXT_STEP_ISSUED,
    NullEmitter,
    RuntimeEventEmitter,
)
from spec_kitty_runtime.planner import plan_next
from spec_kitty_runtime.schema import (
    ActorIdentity,
    DecisionAnswer,
    DecisionRequest,
    MissionPolicySnapshot,
    MissionRunSnapshot,
    MissionRuntimeError,
    MissionTemplate,
    NextDecision,
    load_mission_template_file,
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
        json.dump(snapshot.model_dump(mode="json"), handle, indent=2, sort_keys=True, default=str)


def _freeze_template(run_dir: Path, template: MissionTemplate, template_path: str) -> str:
    """Freeze the template into the run directory and return its SHA-256 hash.

    The frozen copy is the verbatim YAML bytes from disk if the path exists,
    otherwise a canonical YAML dump of the loaded template.
    """
    source_path = Path(template_path)
    if source_path.exists() and source_path.is_file():
        yaml_bytes = source_path.read_bytes()
    else:
        yaml_bytes = yaml.dump(
            template.model_dump(), default_flow_style=False, sort_keys=True
        ).encode("utf-8")

    frozen_path = run_dir / "mission_template_frozen.yaml"
    frozen_path.write_bytes(yaml_bytes)

    return hashlib.sha256(yaml_bytes).hexdigest()


def _load_frozen_template(run_dir: Path) -> MissionTemplate:
    """Load the frozen template from the run directory."""
    frozen_path = run_dir / "mission_template_frozen.yaml"
    if not frozen_path.exists():
        raise MissionRuntimeError(f"Frozen template not found: {frozen_path}")
    return load_mission_template_file(frozen_path)


def _resolve_template_path(template_key: str, context: DiscoveryContext | None) -> str:
    """Resolve the actual filesystem path for a template key.

    For explicit file paths, resolve directly.
    For discovery-based keys, find the selected mission's resolved path.
    This ensures template_path always points to a real file for drift detection.
    """
    candidate = Path(template_key)
    if candidate.exists():
        if candidate.is_dir():
            candidate = candidate / "mission.yaml"
        return str(candidate.resolve())

    # Key-based: look up via discovery (use default context if None,
    # matching load_mission_template behavior).
    effective_context = context if context is not None else DiscoveryContext()
    discovered = discover_missions(effective_context)
    for item in discovered:
        if item.key == template_key and item.selected:
            return item.path  # already resolved by discovery

    return template_key  # last resort (shouldn't happen if template loaded OK)


def start_mission_run(
    template_key: str,
    inputs: dict[str, Any] | None,
    policy_snapshot: MissionPolicySnapshot,
    context: DiscoveryContext | None = None,
    run_store: Path | None = None,
    emitter: RuntimeEventEmitter | None = None,
) -> MissionRunRef:
    """Start and persist a new mission run with template freezing."""
    emitter = emitter or NullEmitter()
    template = load_mission_template(template_key, context=context)

    runs_dir = _runtime_runs_dir(run_store)
    run_id = uuid4().hex
    run_dir = runs_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=False)

    # Always resolve to a real filesystem path for drift detection.
    template_path = _resolve_template_path(template_key, context)

    # Freeze template and compute hash.
    template_hash = _freeze_template(run_dir, template, template_path)

    snapshot = MissionRunSnapshot(
        run_id=run_id,
        mission_key=template.mission.key,
        template_path=template_path,
        template_hash=template_hash,
        policy_snapshot=policy_snapshot,
        issued_step_id=None,
        completed_steps=[],
        inputs=inputs or {},
        decisions={},
        pending_decisions={},
        blocked_reason=None,
    )
    _write_snapshot(run_dir, snapshot)
    actor = RuntimeActorIdentity(actor_id="system", actor_type="service")
    payload = MissionRunStartedPayload(run_id=run_id, mission_key=template.mission.key, actor=actor)
    _append_event(run_dir, MISSION_RUN_STARTED, payload.model_dump(mode="json"))
    emitter.emit_mission_run_started(payload)

    return MissionRunRef(run_id=run_id, run_dir=str(run_dir), mission_key=template.mission.key)


def next_step(
    run_ref: MissionRunRef,
    agent_id: str,
    result: ResultType = "success",
    policy_snapshot: MissionPolicySnapshot | None = None,
    actor_context: dict[str, Any] | None = None,
    context: DiscoveryContext | None = None,
    emitter: RuntimeEventEmitter | None = None,
) -> NextDecision:
    """Advance current issued step and compute the next deterministic decision.

    Plans from the frozen template, not the live file.
    Passes live template path for drift detection.
    Uses persisted policy_snapshot from run state; caller override takes precedence.
    """
    emitter = emitter or NullEmitter()
    actor_context = actor_context or {}

    run_dir = Path(run_ref.run_dir)
    snapshot = _read_snapshot(run_dir)

    # Use caller-provided policy, else fall back to persisted policy from run start.
    effective_policy = policy_snapshot or snapshot.policy_snapshot

    # Load from frozen template for determinism.
    template = _load_frozen_template(run_dir)

    # Resolve live template path for drift detection.
    live_template_path: Path | None = None
    if snapshot.template_path:
        candidate = Path(snapshot.template_path)
        if candidate.exists():
            live_template_path = candidate

    # Track whether this call actually transitions state (completes a step).
    # Used to gate one-shot events like MissionRunCompleted.
    did_complete_step = snapshot.issued_step_id is not None

    if snapshot.issued_step_id:
        completed_steps = list(snapshot.completed_steps)
        blocked_reason = snapshot.blocked_reason
        completed_step_id = snapshot.issued_step_id

        if result == "success":
            if snapshot.issued_step_id not in completed_steps:
                completed_steps.append(snapshot.issued_step_id)
        elif result == "failed":
            blocked_reason = f"Previous step '{snapshot.issued_step_id}' failed; manual intervention required."
        elif result == "blocked":
            blocked_reason = f"Previous step '{snapshot.issued_step_id}' reported blocked state."

        snapshot = MissionRunSnapshot(
            run_id=snapshot.run_id,
            mission_key=snapshot.mission_key,
            template_path=snapshot.template_path,
            template_hash=snapshot.template_hash,
            policy_snapshot=snapshot.policy_snapshot,
            issued_step_id=None,
            completed_steps=completed_steps,
            inputs=snapshot.inputs,
            decisions=snapshot.decisions,
            pending_decisions=snapshot.pending_decisions,
            blocked_reason=blocked_reason,
        )
        ac_actor = RuntimeActorIdentity(actor_id=agent_id, actor_type="llm")
        ac_payload = NextStepAutoCompletedPayload(
            run_id=snapshot.run_id, step_id=completed_step_id,
            agent_id=agent_id, result=result, actor=ac_actor,
        )
        _append_event(run_dir, NEXT_STEP_AUTO_COMPLETED, ac_payload.model_dump(mode="json"))
        emitter.emit_next_step_auto_completed(ac_payload)

    decision = plan_next(
        snapshot,
        template,
        effective_policy,
        actor_context={**actor_context, "agent_id": agent_id},
        live_template_path=live_template_path,
    )

    issued_step_id = snapshot.issued_step_id
    pending_decisions = dict(snapshot.pending_decisions)
    inputs = dict(snapshot.inputs)

    if decision.kind == "step" and decision.step_id:
        issued_step_id = decision.step_id
        si_actor = RuntimeActorIdentity(actor_id=agent_id, actor_type="llm")
        si_payload = NextStepIssuedPayload(
            run_id=snapshot.run_id, step_id=decision.step_id,
            agent_id=agent_id, actor=si_actor,
        )
        _append_event(run_dir, NEXT_STEP_ISSUED, si_payload.model_dump(mode="json"))
        emitter.emit_next_step_issued(si_payload)
    elif decision.kind == "decision_required" and decision.decision_id:
        # Persist input-keyed decisions in pending_decisions so they're answerable.
        # Only emit event + persist on first occurrence to avoid duplicates on re-poll.
        if decision.decision_id not in pending_decisions:
            dr_actor = RuntimeActorIdentity(actor_id=agent_id, actor_type="llm")
            req = DecisionRequest(
                decision_id=decision.decision_id,
                step_id=decision.step_id or "",
                question=decision.question or "",
                options=decision.options or [],
                requested_by=dr_actor,
                requested_at=datetime.now(timezone.utc),
            )
            pending_decisions[decision.decision_id] = req.model_dump(mode="json")

            dr_payload = DecisionInputRequestedPayload(
                run_id=snapshot.run_id,
                decision_id=decision.decision_id,
                step_id=decision.step_id or "",
                question=decision.question or "",
                options=tuple(decision.options or []),
                input_key=decision.input_key,
                actor=dr_actor,
            )
            _append_event(run_dir, DECISION_INPUT_REQUESTED, dr_payload.model_dump(mode="json"))
            emitter.emit_decision_input_requested(dr_payload)
    elif decision.kind == "terminal" and did_complete_step:
        # Only emit on the transition into terminal (last step just completed),
        # not on re-polls of an already-terminal run.
        mc_actor = RuntimeActorIdentity(actor_id=agent_id, actor_type="llm")
        mc_payload = MissionRunCompletedPayload(
            run_id=snapshot.run_id, mission_key=snapshot.mission_key, actor=mc_actor,
        )
        _append_event(run_dir, MISSION_RUN_COMPLETED, mc_payload.model_dump(mode="json"))
        emitter.emit_mission_run_completed(mc_payload)

    snapshot = MissionRunSnapshot(
        run_id=snapshot.run_id,
        mission_key=snapshot.mission_key,
        template_path=snapshot.template_path,
        template_hash=snapshot.template_hash,
        policy_snapshot=snapshot.policy_snapshot,
        issued_step_id=issued_step_id,
        completed_steps=snapshot.completed_steps,
        inputs=inputs,
        decisions=snapshot.decisions,
        pending_decisions=pending_decisions,
        blocked_reason=snapshot.blocked_reason,
    )
    _write_snapshot(run_dir, snapshot)

    return decision


def provide_decision_answer(
    run_ref: MissionRunRef,
    decision_id: str,
    answer: str,
    actor: ActorIdentity,
    emitter: RuntimeEventEmitter | None = None,
) -> None:
    """Answer a pending decision. For input-keyed decisions (input:X), writes into inputs."""
    emitter = emitter or NullEmitter()
    run_dir = Path(run_ref.run_dir)
    snapshot = _read_snapshot(run_dir)

    pending = dict(snapshot.pending_decisions)
    if decision_id not in pending:
        raise MissionRuntimeError(
            f"Decision '{decision_id}' not found in pending_decisions for run '{snapshot.run_id}'"
        )

    decisions = dict(snapshot.decisions)
    inputs = dict(snapshot.inputs)

    answer_data = DecisionAnswer(
        decision_id=decision_id,
        answer=answer,
        answered_by=actor,
        answered_at=datetime.now(timezone.utc),
    )
    decisions[decision_id] = answer_data.model_dump(mode="json")
    del pending[decision_id]

    # For input-keyed decisions, write the answer into inputs so requires_inputs is satisfied.
    if decision_id.startswith("input:"):
        input_key = decision_id[len("input:"):]
        inputs[input_key] = answer

    snapshot = MissionRunSnapshot(
        run_id=snapshot.run_id,
        mission_key=snapshot.mission_key,
        template_path=snapshot.template_path,
        template_hash=snapshot.template_hash,
        policy_snapshot=snapshot.policy_snapshot,
        issued_step_id=snapshot.issued_step_id,
        completed_steps=snapshot.completed_steps,
        inputs=inputs,
        decisions=decisions,
        pending_decisions=pending,
        blocked_reason=snapshot.blocked_reason,
    )
    _write_snapshot(run_dir, snapshot)
    da_payload = DecisionInputAnsweredPayload(
        run_id=snapshot.run_id, decision_id=decision_id, answer=answer, actor=actor,
    )
    _append_event(run_dir, DECISION_INPUT_ANSWERED, da_payload.model_dump(mode="json"))
    emitter.emit_decision_input_answered(da_payload)

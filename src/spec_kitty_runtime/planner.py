"""Deterministic mission planner with DAG-based step resolution."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from spec_kitty_runtime.schema import (
    DecisionRequest,
    MissionPolicySnapshot,
    MissionRunSnapshot,
    MissionTemplate,
    NextDecision,
    PromptStep,
    StepContextBundle,
)


def _resolve_next_step(
    template: MissionTemplate,
    snapshot: MissionRunSnapshot,
) -> PromptStep | None:
    """Find the next runnable step via deterministic DAG traversal.

    1. Skip completed steps (in snapshot.completed_steps)
    2. Skip the currently issued step (snapshot.issued_step_id)
    3. For each remaining step, verify all depends_on are in completed_steps
    4. Among eligible steps, return the first by template definition order
    5. Return None if no step is eligible (all done or all blocked)
    """
    for step in template.steps:
        if step.id in snapshot.completed_steps:
            continue
        if step.id == snapshot.issued_step_id:
            continue
        unmet = [dep for dep in step.depends_on if dep not in snapshot.completed_steps]
        if unmet:
            continue
        return step
    return None


def _has_remaining_steps(
    template: MissionTemplate,
    snapshot: MissionRunSnapshot,
) -> bool:
    """Return True if there are uncompleted steps (excluding issued)."""
    for step in template.steps:
        if step.id in snapshot.completed_steps:
            continue
        if step.id == snapshot.issued_step_id:
            continue
        return True
    return False


def _check_template_drift(
    snapshot: MissionRunSnapshot,
    live_template_path: Path,
) -> str | None:
    """Return drift reason if live template hash differs from frozen hash.
    Returns None if no drift or if live template doesn't exist."""
    if not live_template_path.exists():
        return None
    live_bytes = live_template_path.read_bytes()
    live_hash = hashlib.sha256(live_bytes).hexdigest()
    if live_hash != snapshot.template_hash:
        return "Template changed during active run. Migration required."
    return None


def serialize_decision(decision: NextDecision) -> str:
    """Canonical JSON serialization for determinism verification."""
    return json.dumps(
        decision.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def plan_next(
    snapshot: MissionRunSnapshot,
    mission_template: MissionTemplate,
    policy_snapshot: MissionPolicySnapshot,
    actor_context: dict[str, Any] | None = None,
    live_template_path: Path | None = None,
) -> NextDecision:
    """Compute the next deterministic decision for a mission run.

    Uses DAG-based resolution instead of linear step_index.
    Checks pending decisions before DAG traversal.
    Detects template drift if live_template_path is provided.
    """
    actor_context = actor_context or {}

    # Blocked reason takes priority over everything.
    if snapshot.blocked_reason:
        return NextDecision(
            kind="blocked",
            run_id=snapshot.run_id,
            mission_key=snapshot.mission_key,
            reason=snapshot.blocked_reason,
        )

    # Template drift detection.
    if live_template_path is not None:
        drift_reason = _check_template_drift(snapshot, live_template_path)
        if drift_reason:
            return NextDecision(
                kind="blocked",
                run_id=snapshot.run_id,
                mission_key=snapshot.mission_key,
                reason=drift_reason,
            )

    # Pending decisions block before DAG traversal.
    if snapshot.pending_decisions:
        first_key = sorted(snapshot.pending_decisions.keys())[0]  # deterministic
        req = DecisionRequest.model_validate(snapshot.pending_decisions[first_key])
        # Derive input_key from decision_id prefix for input-keyed decisions.
        input_key: str | None = None
        if req.decision_id.startswith("input:"):
            input_key = req.decision_id[len("input:"):]
        return NextDecision(
            kind="decision_required",
            run_id=snapshot.run_id,
            mission_key=snapshot.mission_key,
            step_id=req.step_id,
            decision_id=req.decision_id,
            input_key=input_key,
            question=req.question,
            options=req.options if req.options else None,
            reason="pending_decision",
        )

    # DAG-based step resolution.
    step = _resolve_next_step(mission_template, snapshot)

    if step is None:
        # Distinguish true completion from unschedulable DAG.
        if _has_remaining_steps(mission_template, snapshot):
            return NextDecision(
                kind="blocked",
                run_id=snapshot.run_id,
                mission_key=snapshot.mission_key,
                reason="No eligible steps: remaining steps have unmet dependencies.",
            )
        return NextDecision(
            kind="terminal",
            run_id=snapshot.run_id,
            mission_key=snapshot.mission_key,
            reason="All mission steps completed",
        )

    # Check for missing required inputs -> emit input-keyed decision.
    missing_inputs = [
        required
        for required in step.requires_inputs
        if required not in snapshot.inputs and required not in snapshot.decisions
    ]
    if missing_inputs:
        missing = missing_inputs[0]
        decision_id = f"input:{missing}"
        return NextDecision(
            kind="decision_required",
            run_id=snapshot.run_id,
            mission_key=snapshot.mission_key,
            step_id=step.id,
            decision_id=decision_id,
            input_key=missing,
            question=f"Input required before step '{step.id}': provide value for '{missing}'.",
            reason="missing_required_input",
        )

    context = StepContextBundle(
        run_id=snapshot.run_id,
        mission_key=snapshot.mission_key,
        step_id=step.id,
        step_title=step.title,
        step_description=step.description,
        expected_output=step.expected_output,
        policy_snapshot=policy_snapshot,
        actor_context=actor_context,
    )

    prompt = step.prompt or f"Execute step '{step.id}': {step.title}"

    return NextDecision(
        kind="step",
        run_id=snapshot.run_id,
        mission_key=snapshot.mission_key,
        step_id=step.id,
        step_title=step.title,
        prompt=prompt,
        context=context,
    )

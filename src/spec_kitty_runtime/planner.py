"""Deterministic mission planner."""

from __future__ import annotations

from typing import Any

from spec_kitty_runtime.schema import (
    MissionPolicySnapshot,
    MissionRunSnapshot,
    MissionTemplate,
    NextDecision,
    StepContextBundle,
)


def plan_next(
    snapshot: MissionRunSnapshot,
    mission_template: MissionTemplate,
    policy_snapshot: MissionPolicySnapshot,
    actor_context: dict[str, Any] | None = None,
) -> NextDecision:
    """Compute the next deterministic decision for a mission run."""
    actor_context = actor_context or {}

    if snapshot.blocked_reason:
        return NextDecision(
            kind="blocked",
            run_id=snapshot.run_id,
            mission_key=snapshot.mission_key,
            reason=snapshot.blocked_reason,
        )

    if snapshot.step_index >= len(mission_template.steps):
        return NextDecision(
            kind="terminal",
            run_id=snapshot.run_id,
            mission_key=snapshot.mission_key,
            reason="All mission steps completed",
        )

    step = mission_template.steps[snapshot.step_index]

    missing_inputs = [
        required
        for required in step.requires_inputs
        if required not in snapshot.inputs and required not in snapshot.decisions
    ]
    if missing_inputs:
        missing = missing_inputs[0]
        return NextDecision(
            kind="decision_required",
            run_id=snapshot.run_id,
            mission_key=snapshot.mission_key,
            question=f"Input required before step '{step.id}': provide value for '{missing}'.",
            reason="missing_required_input",
        )

    unmet_dependencies = [dep for dep in step.depends_on if dep not in snapshot.completed_steps]
    if unmet_dependencies:
        dep = unmet_dependencies[0]
        return NextDecision(
            kind="blocked",
            run_id=snapshot.run_id,
            mission_key=snapshot.mission_key,
            reason=f"Step '{step.id}' is blocked until dependency '{dep}' is complete.",
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

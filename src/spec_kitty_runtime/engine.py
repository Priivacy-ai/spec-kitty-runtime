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


# ============================================================================
# WP02: Transition-Gate Engine - Deterministic Context Resolution
# ============================================================================


import re
from spec_kitty_runtime.contracts import RemediationPayload
from spec_kitty_runtime.schema import ContextType, ContextTypeRegistry, StepContextContract


class TransitionGate:
    """Core gate evaluation logic that validates context bindings before step entry.

    The TransitionGate evaluates whether a step can be entered by checking:
    1. All required contexts can be resolved
    2. Resolved contexts are not ambiguous (multiple equally valid candidates)
    3. Resolved contexts pass validation rules

    If all checks pass, the gate returns 'ready'. Otherwise, it returns a
    RemediationPayload with structured error information and actionable hints.
    """

    def __init__(
        self,
        contract: StepContextContract,
        available_bindings: dict[str, Any],
        context_registry: ContextTypeRegistry | None = None,
        local_discovery_root: Path | None = None,
    ):
        """Initialize TransitionGate.

        Args:
            contract: The StepContextContract defining required/optional contexts
            available_bindings: Dict of available context bindings from all sources
            context_registry: ContextTypeRegistry for type validation (optional)
            local_discovery_root: Root path for local filesystem discovery (optional)
        """
        self.contract = contract
        self.available_bindings = available_bindings
        self.registry = context_registry or ContextTypeRegistry()
        self.local_discovery_root = local_discovery_root or Path.cwd()

    def evaluate(self) -> str | RemediationPayload:
        """Evaluate the transition gate.

        Returns:
            'ready' if all required contexts are resolved and valid
            RemediationPayload if any required context fails resolution or validation
        """
        # Evaluate all required contexts
        for context_type in self.contract.requires:
            result = self._evaluate_context(context_type, required=True)
            if isinstance(result, RemediationPayload):
                return result

        return "ready"

    def _evaluate_context(
        self,
        context_type: ContextType,
        required: bool = True
    ) -> str | RemediationPayload:
        """Evaluate a single context.

        Args:
            context_type: The ContextType to evaluate
            required: Whether this context is required (blocking) or optional

        Returns:
            'ready' if context resolved and valid
            RemediationPayload if context failed resolution or validation
        """
        # Attempt context resolution using precedence chain
        resolution_result = resolve_context(
            context_type.type,
            context_type,
            self.available_bindings,
            self.registry,
            self.local_discovery_root
        )

        if isinstance(resolution_result, RemediationPayload):
            # Resolution failed
            if required:
                return resolution_result
            else:
                # Optional context failed; log but don't block
                return "ready"

        resolved_value = resolution_result

        # Validate the resolved binding against declared rules
        is_valid, validation_error = validate_binding(resolved_value, context_type)
        if not is_valid:
            payload = RemediationPayload.invalid(
                context_name=context_type.type,
                candidates=[{"value": resolved_value}],
                validation_failures=[validation_error] if validation_error else None,
                resolver_metadata={
                    "context_type": context_type.type,
                    "validation_rule_failed": True
                }
            )
            return payload

        return "ready"


def resolve_context(
    context_name: str,
    context_type: ContextType,
    available_bindings: dict[str, Any],
    registry: ContextTypeRegistry,
    local_discovery_root: Path | None = None
) -> Any | RemediationPayload:
    """Resolve a context using the 5-point precedence chain.

    Resolver precedence (local-first, offline):
    1. Explicit step/run inputs (operator overrides)
    2. Prior ContextLedger bindings (from earlier steps)
    3. Mission run metadata (project context, branch, etc.)
    4. Deterministic local discovery (filesystem, branch state, cwd)
    5. Step-specific LOCAL fallback resolvers (only with explicit policy)

    Multiple candidates from the same resolver level = ambiguous (error).
    Try next resolver only if current returns nothing.
    No "best guess" auto-selection.

    Args:
        context_name: The name of the context to resolve
        context_type: The ContextType definition with validation rules
        available_bindings: All available bindings from all sources
        registry: ContextTypeRegistry for type info
        local_discovery_root: Root path for local discovery operations

    Returns:
        Resolved value if found and unambiguous
        RemediationPayload if resolution fails or ambiguous
    """
    if local_discovery_root is None:
        local_discovery_root = Path.cwd()

    resolver_metadata = {
        "context_name": context_name,
        "deterministic": context_type.deterministic,
    }

    # 1. Explicit step/run inputs (highest precedence)
    candidates = _resolve_explicit_inputs(context_name, available_bindings)
    if candidates:
        if len(candidates) > 1:
            return RemediationPayload.ambiguous(
                context_name=context_name,
                candidates=candidates,
                resolver_metadata={
                    **resolver_metadata,
                    "resolver": "explicit_inputs",
                    "precedence": 1,
                    "ambiguous_count": len(candidates)
                }
            )
        return candidates[0]["value"]

    # 2. Prior ContextLedger bindings
    candidates = _resolve_ledger_bindings(context_name, available_bindings)
    if candidates:
        if len(candidates) > 1:
            return RemediationPayload.ambiguous(
                context_name=context_name,
                candidates=candidates,
                resolver_metadata={
                    **resolver_metadata,
                    "resolver": "context_ledger",
                    "precedence": 2,
                    "ambiguous_count": len(candidates)
                }
            )
        return candidates[0]["value"]

    # 3. Mission run metadata
    candidates = _resolve_mission_metadata(context_name, available_bindings)
    if candidates:
        if len(candidates) > 1:
            return RemediationPayload.ambiguous(
                context_name=context_name,
                candidates=candidates,
                resolver_metadata={
                    **resolver_metadata,
                    "resolver": "mission_metadata",
                    "precedence": 3,
                    "ambiguous_count": len(candidates)
                }
            )
        return candidates[0]["value"]

    # 4. Deterministic local discovery
    candidates = _resolve_local_discovery(
        context_name,
        context_type,
        available_bindings,
        local_discovery_root
    )
    if candidates:
        if len(candidates) > 1:
            return RemediationPayload.ambiguous(
                context_name=context_name,
                candidates=candidates,
                resolver_metadata={
                    **resolver_metadata,
                    "resolver": "local_discovery",
                    "precedence": 4,
                    "ambiguous_count": len(candidates)
                }
            )
        return candidates[0]["value"]

    # 5. Step-specific LOCAL fallback resolvers (optional, requires explicit policy)
    # Note: Fallback resolvers must be explicitly enabled in mission policy
    # and are LOCAL-ONLY (no network access in V1)
    # Default behavior: fallback resolvers disabled (conservative, offline-first)

    # Check if mission policy explicitly allows fallback resolvers
    mission_metadata = available_bindings.get("mission_metadata", {})
    allow_fallback_resolvers = mission_metadata.get("allow_fallback_resolvers", False)

    if allow_fallback_resolvers:
        candidates = _resolve_fallback_local(context_name, available_bindings)
        if candidates:
            if len(candidates) > 1:
                return RemediationPayload.ambiguous(
                    context_name=context_name,
                    candidates=candidates,
                    resolver_metadata={
                        **resolver_metadata,
                        "resolver": "fallback_local",
                        "precedence": 5,
                        "ambiguous_count": len(candidates),
                        "policy_enabled": True
                    }
                )
            return candidates[0]["value"]

    # No candidates found in any resolver
    return RemediationPayload.missing(
        context_name=context_name,
        resolver_metadata={
            **resolver_metadata,
            "resolver_chain_exhausted": True
        }
    )


def _resolve_explicit_inputs(
    context_name: str,
    available_bindings: dict[str, Any]
) -> list[dict[str, Any]]:
    """Resolver 1: Check for explicit operator overrides.

    Sources:
    - Explicit step inputs
    - Command-line arguments (passed via available_bindings)
    - Environment variables (passed via available_bindings)

    Args:
        context_name: The context to resolve
        available_bindings: Dict with 'explicit_inputs' key

    Returns:
        List of candidate bindings (empty if not found)
        Each candidate: {"value": <value>, "source": <str>, "metadata": <dict>}

    Note: If explicit input value is a list/tuple, it's treated as multiple
    candidates (ambiguous). Each item becomes a separate candidate.
    """
    explicit = available_bindings.get("explicit_inputs", {})
    if not isinstance(explicit, dict):
        return []

    candidates = []
    if context_name in explicit:
        value = explicit[context_name]

        # If explicit input is a list or tuple, treat as multiple candidates (ambiguous)
        if isinstance(value, (list, tuple)):
            for i, item in enumerate(value):
                candidates.append({
                    "value": item,
                    "source": f"explicit_input:{context_name}[{i}]",
                    "metadata": {
                        "resolver": "explicit_inputs",
                        "precedence": 1,
                        "is_list": True,
                        "index": i
                    }
                })
        else:
            # Single value - normal candidate
            candidates.append({
                "value": value,
                "source": f"explicit_input:{context_name}",
                "metadata": {"resolver": "explicit_inputs", "precedence": 1}
            })

    return candidates


def _resolve_ledger_bindings(
    context_name: str,
    available_bindings: dict[str, Any]
) -> list[dict[str, Any]]:
    """Resolver 2: Check prior ContextLedger bindings.

    Sources:
    - ContextLedger from prior steps
    - ContextLedger from prior runs

    Args:
        context_name: The context to resolve
        available_bindings: Dict with 'ledger' key

    Returns:
        List of candidate bindings (empty if not found)
    """
    ledger = available_bindings.get("ledger", {})
    if not isinstance(ledger, dict):
        return []

    candidates = []
    if context_name in ledger:
        binding = ledger[context_name]
        # Handle both dict and non-dict values
        if isinstance(binding, dict):
            value = binding.get("value", binding)
            validation_status = binding.get("validation_status", "unknown")
        else:
            value = binding
            validation_status = "unknown"

        candidates.append({
            "value": value,
            "source": f"ledger:{context_name}",
            "metadata": {
                "resolver": "context_ledger",
                "precedence": 2,
                "validation_status": validation_status
            }
        })

    return candidates


def _resolve_mission_metadata(
    context_name: str,
    available_bindings: dict[str, Any]
) -> list[dict[str, Any]]:
    """Resolver 3: Check mission run metadata.

    Sources:
    - Mission YAML fields (project_uuid, feature_slug, target_branch, mission_key)
    - Mission run context

    Args:
        context_name: The context to resolve
        available_bindings: Dict with 'mission_metadata' key

    Returns:
        List of candidate bindings (empty if not found)
    """
    metadata = available_bindings.get("mission_metadata", {})
    if not isinstance(metadata, dict):
        return []

    candidates = []

    # Map common context names to metadata fields
    mapping = {
        "project_uuid": "project_uuid",
        "feature_slug": "feature_slug",
        "target_branch": "target_branch",
        "mission_key": "mission_key",
        "mission_name": "mission_name",
        "branch": "target_branch",  # Alias
    }

    if context_name in mapping:
        field = mapping[context_name]
        if field in metadata:
            candidates.append({
                "value": metadata[field],
                "source": f"mission_metadata:{field}",
                "metadata": {
                    "resolver": "mission_metadata",
                    "precedence": 3,
                    "field": field
                }
            })

    return candidates


def _resolve_local_discovery(
    context_name: str,
    context_type: ContextType,
    available_bindings: dict[str, Any],
    local_discovery_root: Path
) -> list[dict[str, Any]]:
    """Resolver 4: Deterministic local filesystem discovery.

    Sources:
    - Working directory and mission directory
    - Fixed known paths
    - Branch state (git info)
    - Artifact paths

    Offline-capable by design (no network calls).

    Args:
        context_name: The context to resolve
        context_type: ContextType with validation rules
        available_bindings: Dict with discovery hints
        local_discovery_root: Root path for searching

    Returns:
        List of candidate bindings (empty if not found)
    """
    candidates = []

    # Check discovery hints in available_bindings
    discovery_hints = available_bindings.get("discovery_hints", {})
    if context_name in discovery_hints:
        hint_value = discovery_hints[context_name]
        candidates.append({
            "value": hint_value,
            "source": f"discovery_hint:{context_name}",
            "metadata": {
                "resolver": "local_discovery",
                "precedence": 4,
                "type": "hint"
            }
        })

    # Check for artifact files that match context name pattern
    # E.g., "spec_artifact" -> look for spec.md, spec.yaml
    artifact_patterns = {
        "spec_artifact": ["spec.md", "spec.yaml"],
        "plan_artifact": ["plan.md", "plan.yaml"],
        "tasks_artifact": ["tasks.md", "tasks.yaml"],
        "research_artifact": ["research.md", "research.yaml"],
    }

    if context_name in artifact_patterns:
        for pattern in artifact_patterns[context_name]:
            potential_path = local_discovery_root / pattern
            if potential_path.exists():
                candidates.append({
                    "value": str(potential_path),
                    "source": f"local_discovery:{pattern}",
                    "metadata": {
                        "resolver": "local_discovery",
                        "precedence": 4,
                        "type": "artifact_file"
                    }
                })

    # Check for branch context (requires git state in available_bindings)
    if context_name == "target_branch":
        git_state = available_bindings.get("git_state", {})
        if "branch" in git_state:
            candidates.append({
                "value": git_state["branch"],
                "source": "git_state:branch",
                "metadata": {
                    "resolver": "local_discovery",
                    "precedence": 4,
                    "type": "git_state"
                }
            })

    return candidates


def _resolve_fallback_local(
    context_name: str,
    available_bindings: dict[str, Any]
) -> list[dict[str, Any]]:
    """Resolver 5: Step-specific LOCAL fallback resolvers.

    Fallback resolvers are optional and must be:
    1. Explicitly registered in mission policy
    2. LOCAL-ONLY (no network registries in V1)
    3. Defined by resolver_ref in ContextType

    Args:
        context_name: The context to resolve
        available_bindings: Dict with 'fallback_resolvers' key

    Returns:
        List of candidate bindings (empty if not found or policy not set)
    """
    fallback_resolvers = available_bindings.get("fallback_resolvers", {})
    if not isinstance(fallback_resolvers, dict):
        return []

    candidates = []
    if context_name in fallback_resolvers:
        resolver_data = fallback_resolvers[context_name]
        # Handle both dict and non-dict values
        if isinstance(resolver_data, dict):
            value = resolver_data.get("value", resolver_data)
        else:
            value = resolver_data

        candidates.append({
            "value": value,
            "source": f"fallback_local:{context_name}",
            "metadata": {
                "resolver": "fallback_local",
                "precedence": 5,
                "policy_required": True,
                "local_only": True
            }
        })

    return candidates


def validate_binding(value: Any, context_type: ContextType) -> tuple[bool, str | None]:
    """Validate a resolved binding against declared validation rules.

    Args:
        value: The resolved value to validate
        context_type: ContextType with validation rules

    Returns:
        (is_valid, error_message) tuple
        If valid: (True, None)
        If invalid: (False, human-readable error message)
    """
    if not context_type.validation:
        # No validation rules; binding is valid
        return (True, None)

    # Validate each rule
    for rule_name, rule_value in context_type.validation.items():
        is_valid, error = _validate_rule(value, rule_name, rule_value)
        if not is_valid:
            return (False, error)

    return (True, None)


def _validate_rule(
    value: Any,
    rule_name: str,
    rule_value: Any
) -> tuple[bool, str | None]:
    """Validate a single rule.

    Args:
        value: The value to validate
        rule_name: Name of the validation rule
        rule_value: The rule specification/pattern (optional, depends on rule type)

    Returns:
        (is_valid, error_message) tuple

    Validation rules:
    - artifact_exists: Check if file exists at path (uses bound value as path, or rule_value if provided)
    - path_exists: Check if directory exists (uses bound value as path, or rule_value if provided)
    - slug_format: Check if value matches regex pattern (uses rule_value as pattern)
    """
    if rule_name == "artifact_exists":
        # Check if file exists at the path
        # If rule_value is provided, it specifies the expected path
        # Otherwise use the bound value as the path
        check_path = str(rule_value) if rule_value else str(value)
        path = Path(check_path)
        if not path.exists() or not path.is_file():
            if rule_value:
                return (False, f"artifact_exists rule failed: expected artifact at {rule_value}, got {value}")
            else:
                return (False, f"artifact_exists: Artifact does not exist at {value}")
        return (True, None)

    elif rule_name == "path_exists":
        # Check if directory exists
        # If rule_value is provided, it specifies the expected path
        # Otherwise use the bound value as the path
        check_path = str(rule_value) if rule_value else str(value)
        path = Path(check_path)
        if not path.exists() or not path.is_dir():
            if rule_value:
                return (False, f"path_exists rule failed: expected directory at {rule_value}, got {value}")
            else:
                return (False, f"path_exists: Directory does not exist at {value}")
        return (True, None)

    elif rule_name == "slug_format":
        # Check if value matches regex pattern
        # rule_value MUST be provided for this rule (the regex pattern)
        pattern = str(rule_value)
        if not re.match(f"^{pattern}$", str(value)):
            return (False, f"slug_format rule failed: value '{value}' does not match pattern '{pattern}'")
        return (True, None)

    else:
        # Unknown rule; treat as valid (extensible for custom rules)
        return (True, None)

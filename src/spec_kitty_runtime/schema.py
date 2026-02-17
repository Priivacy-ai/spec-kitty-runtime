"""Core runtime types and YAML mission-template loading."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field


class MissionRuntimeError(RuntimeError):
    """Raised for runtime loading/planning errors."""


# ---------------------------------------------------------------------------
# Domain value objects
# ---------------------------------------------------------------------------

from spec_kitty_events.mission_next import RuntimeActorIdentity

ActorIdentity = RuntimeActorIdentity


class CommitContext(BaseModel):
    model_config = ConfigDict(frozen=True)

    head_sha: str = Field(..., min_length=1)
    branch: str = Field(..., min_length=1)
    dirty: bool = False


class DecisionRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    decision_id: str = Field(..., min_length=1)
    step_id: str = Field(..., min_length=1)
    question: str = Field(..., min_length=1)
    options: list[str] = Field(default_factory=list)
    requested_by: ActorIdentity
    requested_at: datetime


class DecisionAnswer(BaseModel):
    model_config = ConfigDict(frozen=True)

    decision_id: str = Field(..., min_length=1)
    answer: str = Field(..., min_length=1)
    answered_by: ActorIdentity
    answered_at: datetime


# ---------------------------------------------------------------------------
# Mission template types
# ---------------------------------------------------------------------------

class MissionMeta(BaseModel):
    model_config = ConfigDict(frozen=True)

    key: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    version: str = Field(..., min_length=1)
    description: str = Field(default="")


class PromptStep(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    description: str = Field(default="")
    prompt: str | None = None
    prompt_template: str | None = None
    expected_output: str | None = None
    requires_inputs: list[str] = Field(default_factory=list)
    depends_on: list[str] = Field(default_factory=list)


class MissionPolicySnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)

    strictness: Literal["off", "medium", "max"] = "medium"
    default_route: str = "same_llm_context"
    extras: dict[str, Any] = Field(default_factory=dict)


class MissionTemplate(BaseModel):
    model_config = ConfigDict(frozen=True)

    mission: MissionMeta
    steps: list[PromptStep] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Discovery types
# ---------------------------------------------------------------------------

class DiscoveredMission(BaseModel):
    model_config = ConfigDict(frozen=True)

    key: str
    path: str
    origin: str
    precedence_tier: str
    selected: bool = True


# ---------------------------------------------------------------------------
# Mission pack manifest types
# ---------------------------------------------------------------------------

class MissionPackMeta(BaseModel):
    """Pack-level metadata."""
    model_config = ConfigDict(frozen=True)

    name: str = Field(..., min_length=1)
    version: str = Field(..., min_length=1)
    description: str = Field(default="")


class MissionPackEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    key: str = Field(..., min_length=1)
    path: str = Field(..., min_length=1)


class MissionPackManifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    pack: MissionPackMeta
    missions: list[MissionPackEntry] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Runtime context types
# ---------------------------------------------------------------------------

class StepContextBundle(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: str
    mission_key: str
    step_id: str
    step_title: str
    step_description: str
    expected_output: str | None = None
    policy_snapshot: MissionPolicySnapshot
    actor_context: dict[str, Any] = Field(default_factory=dict)


class NextDecision(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: Literal["step", "decision_required", "blocked", "terminal"]
    run_id: str
    mission_key: str
    step_id: str | None = None
    step_title: str | None = None
    prompt: str | None = None
    context: StepContextBundle | None = None
    decision_id: str | None = None      # for decision_required
    input_key: str | None = None        # for input-keyed decisions (requires_inputs)
    question: str | None = None
    options: list[str] | None = None    # suggested answer options
    reason: str | None = None


class MissionRunSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: str
    mission_key: str
    template_path: str                                          # resolved file path for drift detection
    template_hash: str                                          # SHA-256 of frozen YAML
    policy_snapshot: MissionPolicySnapshot = Field(default_factory=MissionPolicySnapshot)
    completed_steps: list[str] = Field(default_factory=list)
    issued_step_id: str | None = None
    inputs: dict[str, Any] = Field(default_factory=dict)
    decisions: dict[str, Any] = Field(default_factory=dict)     # decision_id -> answer data
    pending_decisions: dict[str, Any] = Field(default_factory=dict)  # decision_id -> request data
    blocked_reason: str | None = None


# ---------------------------------------------------------------------------
# Template loading
# ---------------------------------------------------------------------------

def load_mission_template_file(path: Path) -> MissionTemplate:
    """Load a mission template from a mission.yaml file."""
    if not path.exists():
        raise MissionRuntimeError(f"Mission template not found: {path}")

    with open(path, "r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}

    if not isinstance(raw, dict):
        raise MissionRuntimeError(f"Mission template must be a mapping: {path}")

    # Allow lightweight shorthand with top-level key/name/version.
    if "mission" not in raw:
        mission_meta = {
            "key": raw.get("key") or raw.get("name") or path.parent.name,
            "name": raw.get("name") or path.parent.name,
            "version": str(raw.get("version", "1.0.0")),
            "description": raw.get("description", ""),
        }
        raw = {"mission": mission_meta, "steps": raw.get("steps", [])}

    template = MissionTemplate.model_validate(raw)
    if not template.steps:
        raise MissionRuntimeError(f"Mission template has no steps: {path}")
    return template

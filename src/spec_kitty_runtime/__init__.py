"""Public API for spec-kitty-runtime."""

from spec_kitty_runtime.discovery import DiscoveryContext, discover_missions, load_mission_template
from spec_kitty_runtime.engine import MissionRunRef, next_step, start_mission_run
from spec_kitty_runtime.prompting import render_prompt
from spec_kitty_runtime.schema import (
    DiscoveredMission,
    MissionPolicySnapshot,
    MissionRuntimeError,
    MissionTemplate,
    NextDecision,
    PromptStep,
    StepContextBundle,
)

__all__ = [
    "DiscoveryContext",
    "DiscoveredMission",
    "MissionPolicySnapshot",
    "MissionRunRef",
    "MissionRuntimeError",
    "MissionTemplate",
    "NextDecision",
    "PromptStep",
    "StepContextBundle",
    "discover_missions",
    "load_mission_template",
    "next_step",
    "render_prompt",
    "start_mission_run",
]

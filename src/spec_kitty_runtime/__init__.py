"""Public API for spec-kitty-runtime."""

from spec_kitty_runtime.adapters.capabilities import CapabilityAdapter
from spec_kitty_runtime.discovery import (
    DiscoveryContext,
    DiscoveryResult,
    DiscoveryWarning,
    ShadowEntry,
    ShadowingDiagnostics,
    diagnose_shadowing,
    discover_missions,
    discover_missions_with_warnings,
    load_mission_template,
)
from spec_kitty_runtime.engine import MissionRunRef, next_step, provide_decision_answer, start_mission_run
from spec_kitty_runtime.events import JsonlEventLog, NullEmitter, RuntimeEventEmitter
from spec_kitty_runtime.planner import serialize_decision
from spec_kitty_runtime.prompting import render_prompt
from spec_kitty_runtime.schema import (
    ActorIdentity,
    CommitContext,
    DecisionAnswer,
    DecisionRequest,
    DiscoveredMission,
    MissionPackEntry,
    MissionPackManifest,
    MissionPackMeta,
    MissionPolicySnapshot,
    MissionRuntimeError,
    MissionTemplate,
    NextDecision,
    PromptStep,
    StepContextBundle,
)

__all__ = [
    # Domain value objects
    "ActorIdentity",
    "CommitContext",
    "DecisionAnswer",
    "DecisionRequest",
    # Mission template types
    "MissionPolicySnapshot",
    "MissionRuntimeError",
    "MissionTemplate",
    "PromptStep",
    "StepContextBundle",
    # Mission pack manifest types
    "MissionPackEntry",
    "MissionPackManifest",
    "MissionPackMeta",
    # Discovery
    "DiscoveredMission",
    "DiscoveryContext",
    "DiscoveryResult",
    "DiscoveryWarning",
    "ShadowEntry",
    "ShadowingDiagnostics",
    "diagnose_shadowing",
    "discover_missions",
    "discover_missions_with_warnings",
    "load_mission_template",
    # Engine
    "MissionRunRef",
    "NextDecision",
    "next_step",
    "provide_decision_answer",
    "start_mission_run",
    # Events
    "JsonlEventLog",
    "NullEmitter",
    "RuntimeEventEmitter",
    # Planner
    "serialize_decision",
    # Prompting
    "render_prompt",
    # Adapters
    "CapabilityAdapter",
]

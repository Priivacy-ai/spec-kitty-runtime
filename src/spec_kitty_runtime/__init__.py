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
from spec_kitty_runtime.engine import MissionRunRef, next_step, notify_decision_timeout, provide_decision_answer, start_mission_run
from spec_kitty_runtime.events import JsonlEventLog, NullEmitter, RuntimeEventEmitter
from spec_kitty_runtime.planner import serialize_decision
from spec_kitty_runtime.prompting import render_prompt
from spec_kitty_runtime.raci import infer_raci, resolve_raci, validate_raci_assignment
from spec_kitty_events.mission_next import RuntimeActorIdentity
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
    RACIAssignment,
    RACIEscalationPayload,
    RACIRoleBinding,
    ResolvedRACIBinding,
    SignificanceBlock,
    StepContextBundle,
)
from spec_kitty_runtime.significance import (
    # Models
    SignificanceDimension,
    SignificanceScore,
    RoutingBand,
    HardTriggerClass,
    TimeoutPolicy,
    SoftGateDecision,
    DimensionScoreOverride,
    TimeoutEscalationResult,
    SignificanceEvaluatedPayload,
    TimeoutExpiredPayload,
    # Functions
    evaluate_significance,
    compute_escalation_targets,
    validate_band_cutoffs,
    validate_dimension_scores,
    parse_band_cutoffs_from_policy,
    parse_timeout_from_policy,
    resolve_hard_triggers,
    # Constants
    DIMENSION_NAMES,
    HARD_TRIGGER_REGISTRY,
    DEFAULT_BANDS,
)

__all__ = [
    # Domain value objects
    "ActorIdentity",
    "RuntimeActorIdentity",
    "CommitContext",
    "DecisionAnswer",
    "DecisionRequest",
    # RACI types (WP06)
    "RACIAssignment",
    "RACIEscalationPayload",
    "RACIRoleBinding",
    "ResolvedRACIBinding",
    # Mission template types
    "MissionPolicySnapshot",
    "MissionRuntimeError",
    "MissionTemplate",
    "PromptStep",
    "SignificanceBlock",
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
    "notify_decision_timeout",
    "provide_decision_answer",
    "start_mission_run",
    # RACI functions (WP06)
    "infer_raci",
    "resolve_raci",
    "validate_raci_assignment",
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
    # Significance models (WP01-WP04)
    "SignificanceDimension",
    "SignificanceScore",
    "RoutingBand",
    "HardTriggerClass",
    "TimeoutPolicy",
    "SoftGateDecision",
    "DimensionScoreOverride",
    "TimeoutEscalationResult",
    "SignificanceEvaluatedPayload",
    "TimeoutExpiredPayload",
    # Significance functions (WP01-WP02)
    "evaluate_significance",
    "compute_escalation_targets",
    "validate_band_cutoffs",
    "validate_dimension_scores",
    "parse_band_cutoffs_from_policy",
    "parse_timeout_from_policy",
    "resolve_hard_triggers",
    # Significance constants
    "DIMENSION_NAMES",
    "HARD_TRIGGER_REGISTRY",
    "DEFAULT_BANDS",
]

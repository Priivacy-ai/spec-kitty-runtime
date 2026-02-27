---
work_package_id: "WP06"
title: "RACI Inference and Override"
lane: "planned"
dependencies: []
base_branch: main
base_commit: 8bc392f57b62d20ba66b741eb3c92ccb5ca667fd
created_at: '2026-02-27T18:58:00+00:00'
subtasks:
  - "T001-define-raci-models"
  - "T002-implement-raci-inference-engine"
  - "T003-integrate-with-authority-kernel"
  - "T004-add-template-validation"
  - "T005-create-test-suite"
phase: "Phase 2 - Implementation"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
review_feedback: ""
requirement_refs: [FR-006]
history:
  - timestamp: "2026-02-27T00:00:00Z"
    lane: "planned"
    agent: "system"
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP06 – RACI Inference and Override

## Objective

Implement a deterministic RACI (Responsible, Accountable, Consulted, Informed) role model that governs who may act on each mission step and decision. The runtime will infer default RACI bindings from step type and mission policy, allow mission authors to override bindings explicitly in YAML, and escalate when a required role cannot be resolved to a concrete actor.

## Technical Requirements

Based on the specification in `spec.md`, implement the following components:

### Schema Definitions (T001-define-raci-models)
- Define `RACIRoleBinding` model with `actor_type` and optional `actor_id`
- Define `RACIAssignment` model with required R/A and optional C/I roles
- Define `ResolvedRACIBinding` model with provenance metadata
- Define `RACIEscalationPayload` for unresolved role escalation
- Extend `PromptStep` and `AuditStep` with optional `raci` and `raci_override_reason` fields

### RACI Inference Engine (T002-implement-raci-inference-engine)
- Implement `infer_raci(step, mission_policy)` function with deterministic rules:
  - PromptStep → R:llm, A:human (mission_owner)
  - AuditStep (blocking) → R:human, A:human
  - AuditStep (advisory) → R:llm, A:human
- Implement `validate_raci_assignment(assignment, step)` for P0 invariant checks
- Implement `resolve_raci(step, inputs, mission_policy)` for concrete actor resolution

### Authority Kernel Integration (T003-integrate-with-authority-kernel)
- Extend `_authority_metadata()` with `raci_source` and `override_reason` fields
- Add RACI validation in `provide_decision_answer()` before processing answers
- Persist RACI bindings in snapshot decisions under `raci:<step_id>` key

### Template Validation (T004-add-template-validation)
- Extend `validate_mission_template_compatibility()` with RACI checks
- Add validation for P0 invariants (accountable must be human, etc.)
- Add validation for missing `raci_override_reason` when `raci` block is present

### Test Suite (T005-create-test-suite)
- Create comprehensive test suite covering:
  - Schema validation edge cases
  - Inference rule correctness
  - Explicit override precedence
  - Escalation scenarios
  - Authority kernel integration
  - Backward compatibility

## Implementation Constraints

- Maintain P0 invariants (human accountable, LLM advisory-only)
- All operations must be deterministic and local-only
- No network calls or external dependencies
- Fail-closed escalation for unresolved required roles
- Backward compatibility with existing missions
- No fallback mechanisms - explicit failures when configurations are invalid

## Acceptance Criteria

All acceptance criteria from the specification must be met:

1. Schema validation passes for valid configurations and fails for invalid ones
2. YAML loading works correctly with and without RACI blocks
3. Inference produces correct default bindings for all step types
4. Explicit overrides take precedence over inferred defaults
5. Unresolved-role escalation works correctly with proper payloads
6. Authority kernel integration preserves existing behavior while adding RACI validation
7. Audit trails contain complete RACI provenance information
8. Template compatibility diagnostics catch RACI-related issues
9. All operations are deterministic with no randomness
10. Backward compatibility is maintained for missions without RACI blocks

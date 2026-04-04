---
work_package_id: WP04
title: Timeout Escalation & Engine API
dependencies: [WP03]
requirement_refs:
- FR-011
- FR-012
- FR-013
- FR-014
base_branch: main
base_commit: cbf0cc05d0a4d9d9e4f49e1137fbfd13c3f10fa9
created_at: '2026-02-27T21:45:17.519425+00:00'
subtasks:
- T017
- T018
- T019
- T020
phase: Phase 1 - Escalation Layer
history:
- timestamp: '2026-02-27T20:43:12Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: ''
execution_mode: code_change
mission_id: 01KN234FRPZWM9YKQZJY41ANVM
owned_files:
- .agents/skills/spec-kitty-constitution-doctrine/SKILL.md
- .agents/skills/spec-kitty-constitution-doctrine/references/constitution-command-map.md
- .agents/skills/spec-kitty-constitution-doctrine/references/doctrine-artifact-structure.md
- .agents/skills/spec-kitty-glossary-context/SKILL.md
- .agents/skills/spec-kitty-glossary-context/references/glossary-field-guide.md
- .agents/skills/spec-kitty-glossary-context/references/semantic-drift-examples.md
- .agents/skills/spec-kitty-orchestrator-api-operator/SKILL.md
- .agents/skills/spec-kitty-orchestrator-api-operator/references/host-boundary-rules.md
- .agents/skills/spec-kitty-orchestrator-api-operator/references/orchestrator-api-contract.md
- .agents/skills/spec-kitty-runtime-next/SKILL.md
- .agents/skills/spec-kitty-runtime-next/references/blocked-state-recovery.md
- .agents/skills/spec-kitty-runtime-next/references/runtime-result-taxonomy.md
- .agents/skills/spec-kitty-runtime-review/SKILL.md
- .agents/skills/spec-kitty-runtime-review/references/review-checklist.md
- .agents/skills/spec-kitty-setup-doctor/SKILL.md
- .agents/skills/spec-kitty-setup-doctor/references/agent-path-matrix.md
- .agents/skills/spec-kitty-setup-doctor/references/common-failure-signatures.md
- .github/prompts/spec-kitty.clarify.prompt.md
- .github/prompts/spec-kitty.constitution.prompt.md
- .github/workflows/publish-pypi.yml
- .github/workflows/publish-testpypi.yml
- .kittify/AGENTS.md
- .kittify/metadata.yaml
- .kittify/missions/__init__.py
- .kittify/missions/documentation/command-templates/implement.md
- .kittify/missions/documentation/command-templates/plan.md
- .kittify/missions/documentation/command-templates/review.md
- .kittify/missions/documentation/command-templates/specify.md
- .kittify/missions/documentation/command-templates/tasks.md
- .kittify/missions/documentation/expected-artifacts.yaml
- .kittify/missions/documentation/mission.yaml
- .kittify/missions/documentation/templates/divio/explanation-template.md
- .kittify/missions/documentation/templates/divio/howto-template.md
- .kittify/missions/documentation/templates/divio/reference-template.md
- .kittify/missions/documentation/templates/divio/tutorial-template.md
- .kittify/missions/documentation/templates/generators/jsdoc.json.template
- .kittify/missions/documentation/templates/generators/sphinx-conf.py.template
- .kittify/missions/documentation/templates/plan-template.md
- .kittify/missions/documentation/templates/release-template.md
- .kittify/missions/documentation/templates/spec-template.md
- .kittify/missions/documentation/templates/task-prompt-template.md
- .kittify/missions/documentation/templates/tasks-template.md
- .kittify/missions/glossary_hook.py
- .kittify/missions/plan/command-templates/.gitkeep
- .kittify/missions/plan/command-templates/plan.md
- .kittify/missions/plan/command-templates/research.md
- .kittify/missions/plan/command-templates/review.md
- .kittify/missions/plan/command-templates/specify.md
- .kittify/missions/plan/mission-runtime.yaml
- .kittify/missions/plan/mission.yaml
- .kittify/missions/plan/templates/.gitkeep
- .kittify/missions/primitives.py
- .kittify/missions/research/command-templates/implement.md
- .kittify/missions/research/command-templates/merge.md
- .kittify/missions/research/command-templates/plan.md
- .kittify/missions/research/command-templates/review.md
- .kittify/missions/research/command-templates/specify.md
- .kittify/missions/research/command-templates/tasks.md
- .kittify/missions/research/expected-artifacts.yaml
- .kittify/missions/research/mission.yaml
- .kittify/missions/research/templates/data-model-template.md
- .kittify/missions/research/templates/plan-template.md
- .kittify/missions/research/templates/research-template.md
- .kittify/missions/research/templates/research/evidence-log.csv
- .kittify/missions/research/templates/research/source-register.csv
- .kittify/missions/research/templates/spec-template.md
- .kittify/missions/research/templates/task-prompt-template.md
- .kittify/missions/research/templates/tasks-template.md
- .kittify/missions/software-dev/command-templates/accept.md
- .kittify/missions/software-dev/command-templates/analyze.md
- .kittify/missions/software-dev/command-templates/checklist.md
- .kittify/missions/software-dev/command-templates/clarify.md
- .kittify/missions/software-dev/command-templates/constitution.md
- .kittify/missions/software-dev/command-templates/dashboard.md
- .kittify/missions/software-dev/command-templates/implement.md
- .kittify/missions/software-dev/command-templates/merge.md
- .kittify/missions/software-dev/command-templates/plan.md
- .kittify/missions/software-dev/command-templates/review.md
- .kittify/missions/software-dev/command-templates/specify.md
- .kittify/missions/software-dev/command-templates/tasks-finalize.md
- .kittify/missions/software-dev/command-templates/tasks-outline.md
- .kittify/missions/software-dev/command-templates/tasks-packages.md
- .kittify/missions/software-dev/command-templates/tasks.md
- .kittify/missions/software-dev/expected-artifacts.yaml
- .kittify/missions/software-dev/mission-runtime.yaml
- .kittify/missions/software-dev/mission.yaml
- .kittify/missions/software-dev/templates/plan-template.md
- .kittify/missions/software-dev/templates/spec-template.md
- .kittify/missions/software-dev/templates/task-prompt-template.md
- .kittify/missions/software-dev/templates/tasks-template.md
- .kittify/overrides/missions/__pycache__/__init__.cpython-314.pyc
- .kittify/overrides/missions/__pycache__/glossary_hook.cpython-314.pyc
- .kittify/overrides/missions/__pycache__/primitives.cpython-314.pyc
- .kittify/overrides/scripts/tasks/__pycache__/acceptance_support.cpython-314.pyc
- .kittify/overrides/scripts/tasks/__pycache__/task_helpers.cpython-314.pyc
- .kittify/overrides/scripts/tasks/__pycache__/tasks_cli.cpython-314.pyc
- .kittify/scripts/debug-dashboard-scan.py
- .kittify/scripts/tasks/acceptance_support.py
- .kittify/scripts/tasks/task_helpers.py
- .kittify/scripts/tasks/tasks_cli.py
- .kittify/scripts/validate_encoding.py
- .kittify/skills-manifest.json
- CHANGELOG.md
- docs/releases/dependency-compatibility-matrix.toml
- docs/releases/dependency-release-train.md
- kitty-specs/001-audit-primitive-decision-checkpoint/meta.json
- kitty-specs/001-audit-primitive-decision-checkpoint/status.events.jsonl
- kitty-specs/001-audit-primitive-decision-checkpoint/status.json
- kitty-specs/001-audit-primitive-decision-checkpoint/tasks/WP01-audit-config-audit-step-schema.md
- kitty-specs/001-audit-primitive-decision-checkpoint/tasks/WP02-planner-dag-extension-audit-steps.md
- kitty-specs/001-audit-primitive-decision-checkpoint/tasks/WP03-engine-resume-path-audit-decisions.md
- kitty-specs/001-audit-primitive-decision-checkpoint/tasks/WP04-compat-diagnostics-api-fixtures.md
- kitty-specs/002-decision-authority-kernel/status.json
- kitty-specs/002-decision-authority-kernel/tasks/WP05-runtime-decision-authority-kernel.md
- kitty-specs/003-raci-inference-override/status.json
- kitty-specs/003-raci-inference-override/tasks/WP06-raci-inference-override.md
- kitty-specs/004-runtime-significance-threshold-timeout-policy/meta.json
- kitty-specs/004-runtime-significance-threshold-timeout-policy/status.events.jsonl
- kitty-specs/004-runtime-significance-threshold-timeout-policy/status.json
- kitty-specs/004-runtime-significance-threshold-timeout-policy/tasks.md
- kitty-specs/004-runtime-significance-threshold-timeout-policy/tasks/WP01-core-significance-models.md
- kitty-specs/004-runtime-significance-threshold-timeout-policy/tasks/WP02-scoring-engine.md
- kitty-specs/004-runtime-significance-threshold-timeout-policy/tasks/WP03-event-payloads-decision-models.md
- kitty-specs/004-runtime-significance-threshold-timeout-policy/tasks/WP04-timeout-escalation-engine.md
- kitty-specs/004-runtime-significance-threshold-timeout-policy/tasks/WP05-auditstep-engine-integration.md
- kitty-specs/004-runtime-significance-threshold-timeout-policy/tasks/WP06-test-fixtures-scoring-tests.md
- kitty-specs/004-runtime-significance-threshold-timeout-policy/tasks/WP07-integration-tests-edge-cases.md
- pyproject.toml
- scripts/release/validate_dependency_matrix.py
- scripts/release/validate_dependency_policy.py
- scripts/release/validate_distribution_metadata.py
- src/spec_kitty_runtime/__init__.py
- src/spec_kitty_runtime/adapters/capabilities.py
- src/spec_kitty_runtime/engine.py
- src/spec_kitty_runtime/schema.py
- tests/fixtures/mission_hard_trigger.yaml
- tests/fixtures/mission_significance_high.yaml
- tests/fixtures/mission_significance_low.yaml
- tests/fixtures/mission_significance_medium.yaml
- tests/test_scoring_fixtures_wp06.py
- tests/test_significance_integration.py
- tests/test_significance_integration_wp05.py
- tests/test_significance_timeout.py
- uv.lock
wp_code: WP04
---

# Work Package Prompt: WP04 – Timeout Escalation & Engine API

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: Update `review_status: acknowledged` when you begin addressing feedback.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Markdown Formatting
Wrap HTML/XML tags in backticks: `` `<div>` ``, `` `<script>` ``
Use language identifiers in code blocks: ````python`, ````bash`

---

## Implementation Command

Depends on WP03:

```bash
spec-kitty implement WP04 --base WP03
```

---

## Objectives & Success Criteria

- Implement `compute_escalation_targets()` as a pure function in `significance.py`
- Implement `TimeoutEscalationResult` return model
- Implement `notify_decision_timeout()` public API in `engine.py`
- Persist timeout events to `MissionRunSnapshot.decisions`
- Medium-band timeout → escalate to mission owner only
- High-band/hard-trigger timeout → escalate to mission owner + accountable + consulted from RACI
- Run stays blocked after timeout (fail-closed, FR-014)
- Empty consulted set is logged but does not block escalation

## Context & Constraints

- **Spec reference**: FR-011 through FR-014, US3, US4
- **Research**: R-003 (timeout notification architecture — explicit engine API)
- **Engineering Decision ED-3**: Engine exposes `notify_decision_timeout()`, internally calls `compute_escalation_targets()`
- **Constraint C-004**: Runtime caller manages wall-clock timers; runtime defines policy and emits events
- **Integration with Feature 003**: Uses `ResolvedRACIBinding` from `decisions["raci:<step_id>"]` for escalation targeting
- **Engine patterns**: Study `engine.py` for snapshot read/write patterns, event emission via emitter

## Subtasks & Detailed Guidance

### Subtask T017 – Implement compute_escalation_targets() Pure Function

- **Purpose**: Deterministically resolve escalation targets from a RACI binding and the effective significance band.

- **Steps**:
  1. Add to `significance.py`:
     ```python
     def compute_escalation_targets(
         raci_binding: ResolvedRACIBinding,
         effective_band: Literal["medium", "high"],
     ) -> tuple[RACIRoleBinding, ...]:
         """Compute escalation targets for a timed-out decision.

         Pure function: deterministic output from inputs.

         Medium band: escalate to accountable (mission owner) only.
         High band / hard-trigger: escalate to accountable + consulted actors.

         Empty consulted set is allowed — escalation proceeds with accountable only.
         """
         if effective_band == "medium":
             return (raci_binding.accountable,)

         # high band (includes hard-trigger)
         targets = [raci_binding.accountable]
         targets.extend(raci_binding.consulted)
         return tuple(targets)
     ```
  2. Import `ResolvedRACIBinding` and `RACIRoleBinding` from `schema.py`
  3. Note: accountable is always the mission owner (enforced by RACI P0 invariant)

- **Files**: `src/spec_kitty_runtime/significance.py`
- **Parallel?**: Yes — independent of T018
- **Notes**:
  - Medium escalation (FR-012): mission owner only
  - High/hard-trigger escalation (FR-013): mission owner + accountable + consulted
  - When responsible == mission owner for medium: still emit timeout event, no target change (per US3 scenario 2)
  - Empty consulted: `targets.extend([])` is a no-op, just logs and continues

### Subtask T018 – Implement TimeoutEscalationResult Model

- **Purpose**: Return type from `notify_decision_timeout()` — provides the caller with escalation targets and the emitted event payload.

- **Steps**:
  1. Add to `significance.py`:
     ```python
     class TimeoutEscalationResult(BaseModel):
         model_config = ConfigDict(frozen=True, extra="forbid")

         decision_id: str = Field(..., min_length=1)
         escalation_targets: tuple[RACIRoleBinding, ...] = Field(default_factory=tuple)
         band: Literal["medium", "high"]
         timeout_expired_payload: TimeoutExpiredPayload
     ```
  2. The caller (host process) uses `escalation_targets` to deliver notifications (email, Slack, etc.)
  3. The `timeout_expired_payload` is already emitted to the event log — included here for caller convenience

- **Files**: `src/spec_kitty_runtime/significance.py`
- **Parallel?**: Yes — independent of T017
- **Notes**: Keep this model simple. The caller needs: who to notify (targets), what band (for message framing), and the full payload (for debugging).

### Subtask T019 – Implement notify_decision_timeout() in engine.py

- **Purpose**: The public API entry point for timeout notification. Called by the host process when a wall-clock timer expires.

- **Steps**:
  1. Add to `engine.py`:
     ```python
     def notify_decision_timeout(
         run_ref: MissionRunRef,
         decision_id: str,
         actor: RACIRoleBinding,
         emitter: RuntimeEventEmitter | None = None,
     ) -> TimeoutEscalationResult:
         """Notify the runtime that a decision has timed out.

         Called by the host process (caller manages wall-clock timers per C-004).
         The runtime computes escalation targets, emits timeout-expired event,
         and persists the timeout record. The run remains blocked (fail-closed).

         Args:
             run_ref: Reference to the mission run
             decision_id: The decision that timed out (e.g., "audit:deploy-approval")
             actor: System actor identity (typically service/runtime)
             emitter: Optional event emitter (uses NullEmitter if None)

         Returns:
             TimeoutEscalationResult with escalation targets and event payload

         Raises:
             MissionRuntimeError: If decision not found, RACI not resolved, or significance not evaluated
         """
     ```
  2. Implementation flow:
     a. Load snapshot from `run_ref`
     b. Extract `step_id` from `decision_id` (strip "audit:" prefix)
     c. Load RACI binding from `snapshot.decisions[f"raci:{step_id}"]`
        - If not found: raise `MissionRuntimeError("No RACI binding for step '{step_id}'")`
     d. Load significance score from `snapshot.decisions[f"significance:{decision_id}"]`
        - If not found: raise `MissionRuntimeError("No significance evaluation for decision '{decision_id}'")`
     e. Determine effective_band from the stored significance score
     f. Call `compute_escalation_targets(raci_binding, effective_band)`
     g. Build `TimeoutExpiredPayload`:
        ```python
        payload = TimeoutExpiredPayload(
            run_id=snapshot.run_id,
            decision_id=decision_id,
            step_id=step_id,
            significance_score=stored_significance_score,
            effective_band=effective_band,
            timeout_configured_seconds=timeout_seconds,
            escalation_targets=escalation_targets,
            raci_snapshot=stored_raci_binding,
            actor=actor,
        )
        ```
     h. Emit via `emitter.emit_decision_timeout_expired(payload)`
     i. Persist to snapshot: `decisions[f"timeout:{decision_id}"] = payload.model_dump()`
     j. Save updated snapshot
     k. Return `TimeoutEscalationResult`
  3. Import new types from `significance`:
     ```python
     from spec_kitty_runtime.significance import (
         compute_escalation_targets,
         TimeoutEscalationResult,
         TimeoutExpiredPayload,
     )
     ```

- **Files**: `src/spec_kitty_runtime/engine.py`
- **Parallel?**: No — core engine integration
- **Notes**:
  - Follow existing engine.py patterns for snapshot loading and saving (see `next_step()` and `provide_decision_answer()`)
  - The run remains blocked (do NOT modify `blocked_reason` or `completed_steps`)
  - The RACI binding was persisted by `next_step()` during initial step evaluation (line ~286-310)
  - The significance score will be persisted by WP05 integration work
  - For now, this function reads what WP05 will write — implement the reading side; WP05 handles writing

### Subtask T020 – Persist Timeout Events to Decisions Dict

- **Purpose**: Ensure timeout events are captured in the mission run snapshot for audit trail completeness.

- **Steps**:
  1. In `notify_decision_timeout()` (T019), after building the payload:
     ```python
     # Persist timeout event to decisions dict
     updated_decisions = dict(snapshot.decisions)
     updated_decisions[f"timeout:{decision_id}"] = payload.model_dump()

     # Build updated snapshot (frozen model, so create new)
     updated_snapshot = MissionRunSnapshot(
         **{**snapshot.model_dump(), "decisions": updated_decisions}
     )

     # Save to state.json
     _save_snapshot(run_ref, updated_snapshot)
     ```
  2. Follow existing snapshot update pattern from `provide_decision_answer()` in engine.py
  3. The key format `"timeout:{decision_id}"` follows the existing convention (`"raci:{step_id}"`, `"audit:{step_id}"`)

- **Files**: `src/spec_kitty_runtime/engine.py`
- **Parallel?**: No — sequential with T019
- **Notes**: The snapshot is frozen, so updating requires constructing a new MissionRunSnapshot. Follow the pattern already established in engine.py for decision updates.

## Risks & Mitigations

- **Missing RACI binding**: If `next_step()` didn't persist a RACI binding for the step, `notify_decision_timeout()` will fail. This is correct behavior — fail-closed, not fail-open. Clear error message.
- **Missing significance score**: WP05 persists significance scores. If testing this WP before WP05, you'll need to manually seed the significance score in the decisions dict for testing.
- **Snapshot immutability**: All snapshots are frozen. Updating requires constructing a new instance. Follow existing patterns.
- **Event ordering**: The timeout event should be emitted BEFORE the snapshot is saved, consistent with existing event emission patterns in engine.py.

## Review Guidance

- Verify `compute_escalation_targets()` returns correct targets:
  - medium → `(accountable,)` only
  - high → `(accountable, *consulted)`
  - high with empty consulted → `(accountable,)` — no error
- Verify `notify_decision_timeout()` reads RACI and significance from decisions dict correctly
- Verify timeout event is emitted via emitter AND persisted to decisions dict
- Verify error handling: missing RACI binding, missing significance score → `MissionRuntimeError`
- Verify the run remains blocked after timeout (fail-closed, no state changes beyond timeout persistence)
- Verify decision key format: `"timeout:{decision_id}"`

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

- 2026-02-27T20:43:12Z – system – lane=planned – Prompt created.
- 2026-02-27T21:45:17Z – claude-opus – shell_pid=29041 – lane=doing – Assigned agent via workflow command
- 2026-02-27T21:51:47Z – claude-opus – shell_pid=29041 – lane=for_review – Ready for review: Timeout escalation engine API with compute_escalation_targets(), TimeoutEscalationResult, notify_decision_timeout(), and timeout persistence. 30 new tests, 508 total passing.
- 2026-02-27T21:52:38Z – claude-opus-reviewer – shell_pid=32586 – lane=doing – Started review via workflow command
- 2026-02-27T21:55:39Z – claude-opus-reviewer – shell_pid=32586 – lane=done – Review passed: WP04 merged to main. All 4 subtasks (T017-T020) implemented correctly. 30 new tests, 508 total passing, zero regressions.

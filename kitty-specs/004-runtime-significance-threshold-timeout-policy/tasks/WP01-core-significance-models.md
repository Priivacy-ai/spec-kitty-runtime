---
work_package_id: WP01
title: Core Significance Models & Registries
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-008
- FR-015
base_branch: main
base_commit: 15df224ca42e67fc9c8dce338e5675b4f4dba9f7
created_at: '2026-02-27T21:00:20.500268+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
phase: Phase 0 - Foundation
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
- src/spec_kitty_runtime/events.py
- src/spec_kitty_runtime/schema.py
- src/spec_kitty_runtime/significance.py
- tests/fixtures/mission_hard_trigger.yaml
- tests/fixtures/mission_significance_high.yaml
- tests/fixtures/mission_significance_low.yaml
- tests/fixtures/mission_significance_medium.yaml
- tests/test_event_payloads_wp03.py
- tests/test_scoring_engine_wp02.py
- tests/test_scoring_fixtures_wp06.py
- tests/test_significance_integration.py
- tests/test_significance_integration_wp05.py
- tests/test_significance_timeout.py
- tests/test_timeout_escalation_wp04.py
- uv.lock
wp_code: WP01
---

# Work Package Prompt: WP01 – Core Significance Models & Registries

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately (right below this notice).
- **You must address all feedback** before your work is complete. Feedback items are your implementation TODO list.
- **Mark as acknowledged**: When you understand the feedback and begin addressing it, update `review_status: acknowledged` in the frontmatter.
- **Report progress**: As you address each feedback item, update the Activity Log explaining what you changed.

---

## Review Feedback

> **Populated by `/spec-kitty.review`** – Reviewers add detailed feedback here when work needs changes. Implementation must address every item listed below before returning for re-review.

*[This section is empty initially. Reviewers will populate it if the work is returned from review. If you see feedback here, treat each item as a must-do before completion.]*

---

## Markdown Formatting
Wrap HTML/XML tags in backticks: `` `<div>` ``, `` `<script>` ``
Use language identifiers in code blocks: ````python`, ````bash`

---

## Implementation Command

No dependencies — start from the target branch:

```bash
spec-kitty implement WP01
```

---

## Objectives & Success Criteria

- Create `src/spec_kitty_runtime/significance.py` with three foundational frozen Pydantic models: SignificanceDimension, RoutingBand, HardTriggerClass
- Establish fixed registries for the 6 dimension names and 5 hard-trigger classes
- Implement band cutoff validation ensuring contiguous, non-overlapping coverage of 0–18
- All models reject invalid input at construction time with clear error messages
- Models follow existing codebase conventions: `ConfigDict(frozen=True, extra="forbid")`, `@model_validator`, `Field(...)` with constraints

## Context & Constraints

- **Spec reference**: `kitty-specs/004-runtime-significance-threshold-timeout-policy/spec.md` — FR-001 through FR-003, FR-008, FR-015, C-001, C-003
- **Data model reference**: `kitty-specs/004-runtime-significance-threshold-timeout-policy/data-model.md` — SignificanceDimension, RoutingBand, HardTriggerClass sections
- **Contract reference**: `kitty-specs/004-runtime-significance-threshold-timeout-policy/contracts/significance-evaluation.yaml` — field names and enum values
- **Codebase conventions**: Study `src/spec_kitty_runtime/raci.py` and `src/spec_kitty_runtime/schema.py` for frozen Pydantic model patterns
- **Constraint C-001**: Six significance dimensions are FIXED in V1 — no custom dimensions
- **Constraint C-003**: Five hard-trigger classes are FIXED in V1 — no custom triggers
- **NFR-005**: All models MUST use frozen Pydantic schemas

## Subtasks & Detailed Guidance

### Subtask T001 – Create significance.py with SignificanceDimension Model

- **Purpose**: Establish the new module and define the atomic unit of significance scoring — a single dimension with a name and score.

- **Steps**:
  1. Create `src/spec_kitty_runtime/significance.py` with standard imports:
     ```python
     from __future__ import annotations
     from pydantic import BaseModel, ConfigDict, Field, model_validator
     from typing import Literal
     ```
  2. Define `SignificanceDimension` frozen model:
     - `name: str` — one of the 6 fixed dimension names (see below)
     - `score: int` — validated 0–3 inclusive
     - `description: str = ""` — optional human-readable description
  3. Add `@model_validator(mode="after")` to reject:
     - `score` outside 0–3 → `ValueError` with message identifying the dimension name and invalid score
     - `name` not in the fixed set → `ValueError` with message listing valid dimension names

- **Fixed Dimension Names** (from data-model.md):
  ```python
  DIMENSION_NAMES: frozenset[str] = frozenset({
      "user_customer_impact",
      "architectural_system_impact",
      "data_security_compliance_impact",
      "operational_reliability_impact",
      "financial_commercial_impact",
      "cross_team_blast_radius",
  })
  ```

- **Files**: `src/spec_kitty_runtime/significance.py` (new file)
- **Parallel?**: No — this is the first subtask that creates the file
- **Notes**: Follow the pattern from `RACIRoleBinding` in `schema.py` (frozen, extra="forbid", field validation)

### Subtask T002 – Implement RoutingBand Model with Default Bands

- **Purpose**: Define the three significance tiers that determine gating behavior.

- **Steps**:
  1. Define `RoutingBand` frozen model in `significance.py`:
     ```python
     class RoutingBand(BaseModel):
         model_config = ConfigDict(frozen=True, extra="forbid")

         name: Literal["low", "medium", "high"]
         min_score: int = Field(..., ge=0, le=18)
         max_score: int = Field(..., ge=0, le=18)

         @model_validator(mode="after")
         def _validate_range(self) -> RoutingBand:
             if self.min_score > self.max_score:
                 raise ValueError(f"min_score ({self.min_score}) > max_score ({self.max_score})")
             return self
     ```
  2. Define default band constants:
     ```python
     DEFAULT_BANDS: tuple[RoutingBand, ...] = (
         RoutingBand(name="low", min_score=0, max_score=6),
         RoutingBand(name="medium", min_score=7, max_score=11),
         RoutingBand(name="high", min_score=12, max_score=18),
     )
     ```
  3. Create factory function `make_routing_bands(cutoffs: dict[str, list[int]] | None = None) -> tuple[RoutingBand, ...]`:
     - If `cutoffs` is None → return `DEFAULT_BANDS`
     - If provided → construct bands from cutoffs dict (e.g., `{"low": [0, 5], "medium": [6, 10], "high": [11, 18]}`)
     - Validate with `validate_band_cutoffs()` (T004) before constructing

- **Files**: `src/spec_kitty_runtime/significance.py`
- **Parallel?**: Yes — independent model, can develop alongside T001 and T003
- **Notes**: Use `Literal["low", "medium", "high"]` for name to restrict values at type level

### Subtask T003 – Implement HardTriggerClass Model with Fixed Registry

- **Purpose**: Define the five conditions that override numeric scoring and force hard-gate behavior.

- **Steps**:
  1. Define `HardTriggerClass` frozen model:
     ```python
     class HardTriggerClass(BaseModel):
         model_config = ConfigDict(frozen=True, extra="forbid")

         class_id: str = Field(..., min_length=1)
         description: str = Field(..., min_length=1)
     ```
  2. Define the 5 fixed hard-trigger class instances:
     ```python
     HARD_TRIGGER_REGISTRY: dict[str, HardTriggerClass] = {
         "production_data_destructive": HardTriggerClass(
             class_id="production_data_destructive",
             description="Production data-destructive or schema-impacting changes",
         ),
         "security_privacy_access_control": HardTriggerClass(
             class_id="security_privacy_access_control",
             description="Security/privacy/access-control changes",
         ),
         "legal_compliance_regulatory": HardTriggerClass(
             class_id="legal_compliance_regulatory",
             description="Legal/compliance/regulatory impact",
         ),
         "billing_financial_commitment": HardTriggerClass(
             class_id="billing_financial_commitment",
             description="Billing/financial commitment changes",
         ),
         "architecture_foundation": HardTriggerClass(
             class_id="architecture_foundation",
             description="Architecture-foundation changes (language, framework, runtime, datastore, infrastructure)",
         ),
     }
     ```
  3. Add a lookup helper:
     ```python
     def resolve_hard_triggers(class_ids: list[str]) -> tuple[HardTriggerClass, ...]:
         """Resolve hard-trigger class IDs to HardTriggerClass instances.
         Raises ValueError for unknown class_ids."""
         resolved = []
         for cid in class_ids:
             if cid not in HARD_TRIGGER_REGISTRY:
                 raise ValueError(f"Unknown hard-trigger class: {cid!r}. Valid: {sorted(HARD_TRIGGER_REGISTRY.keys())}")
             resolved.append(HARD_TRIGGER_REGISTRY[cid])
         return tuple(resolved)
     ```

- **Files**: `src/spec_kitty_runtime/significance.py`
- **Parallel?**: Yes — independent of T001 and T002
- **Notes**: The `class_id` values match exactly what's in `contracts/significance-evaluation.yaml` → `hard_trigger_classes.items.enum`

### Subtask T004 – Implement Band Cutoff Validation Logic

- **Purpose**: Ensure custom band cutoffs from policy settings are valid before use.

- **Steps**:
  1. Implement `validate_band_cutoffs(cutoffs: dict[str, list[int]]) -> None`:
     - Raises `ValueError` if validation fails (with specific error message)
     - Validation rules (from research.md R-006):
       1. Exactly three bands must be defined (keys: "low", "medium", "high")
       2. Each band value is a `[min, max]` pair
       3. Each band's min <= max (non-degenerate)
       4. Lowest band ("low") must start at 0
       5. Highest band ("high") must end at 18
       6. Bands are contiguous: sorted by min_score, each band's min == previous band's max + 1
       7. No overlaps: bands sorted by min_score have no score belonging to two bands
  2. Error messages should identify the specific problem:
     - `"Expected exactly 3 bands (low, medium, high), got: {keys}"`
     - `"Band 'low' must start at 0, starts at {min}"`
     - `"Band 'high' must end at 18, ends at {max}"`
     - `"Gap between band '{prev_name}' (max={prev_max}) and '{next_name}' (min={next_min})"`
     - `"Overlap between band '{prev_name}' (max={prev_max}) and '{next_name}' (min={next_min})"`

- **Files**: `src/spec_kitty_runtime/significance.py`
- **Parallel?**: No — depends on T002 (uses RoutingBand)
- **Notes**: This validation runs at policy load time (fail-closed), not at evaluation time

### Subtask T005 – Create DIMENSION_NAMES and HARD_TRIGGER_REGISTRY Constants

- **Purpose**: Provide module-level constants that downstream code references for validation and registration.

- **Steps**:
  1. Ensure `DIMENSION_NAMES` frozenset is defined at module level (already done in T001, verify placement)
  2. Ensure `HARD_TRIGGER_REGISTRY` dict is defined at module level (already done in T003, verify placement)
  3. Add a helper function to validate a full set of dimension scores:
     ```python
     def validate_dimension_scores(scores: dict[str, int]) -> None:
         """Validate that dimension scores contain exactly the 6 required dimensions, each scored 0-3."""
         provided = set(scores.keys())
         if provided != DIMENSION_NAMES:
             missing = DIMENSION_NAMES - provided
             extra = provided - DIMENSION_NAMES
             parts = []
             if missing:
                 parts.append(f"missing: {sorted(missing)}")
             if extra:
                 parts.append(f"unexpected: {sorted(extra)}")
             raise ValueError(f"Dimension scores must contain exactly {len(DIMENSION_NAMES)} dimensions. {', '.join(parts)}")
         for name, score in scores.items():
             if not (0 <= score <= 3):
                 raise ValueError(f"Dimension '{name}' score must be 0-3, got {score}")
     ```
  4. Verify module `__all__` export list includes all public symbols

- **Files**: `src/spec_kitty_runtime/significance.py`
- **Parallel?**: No — depends on T001 and T003
- **Notes**: The `validate_dimension_scores()` helper is used by `evaluate_significance()` in WP02

## Risks & Mitigations

- **Naming drift from contracts**: The dimension names and hard-trigger class_ids MUST match exactly what's in `contracts/significance-evaluation.yaml`. Copy-paste from the contract, don't retype.
- **Over-engineering**: These are pure data models. No business logic beyond validation. Keep them simple.
- **Import cycles**: `significance.py` should NOT import from `engine.py`. It may import from `schema.py` if needed (for type references like ActorIdentity), but prefer keeping it self-contained for now.

## Review Guidance

- Verify all 6 dimension names match `contracts/significance-evaluation.yaml` exactly
- Verify all 5 hard-trigger class_ids match the contract exactly
- Verify default bands: low 0–6, medium 7–11, high 12–18
- Verify band cutoff validation catches: overlapping, gaps, wrong range, wrong count
- Verify all models use `ConfigDict(frozen=True, extra="forbid")`
- Verify `@model_validator` rejects invalid dimension scores (outside 0–3) and unknown dimension names

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

- 2026-02-27T20:43:12Z – system – lane=planned – Prompt created.
- 2026-02-27T21:00:20Z – claude-opus – shell_pid=7578 – lane=doing – Assigned agent via workflow command
- 2026-02-27T21:03:42Z – claude-opus – shell_pid=7578 – lane=for_review – Ready for review: All 5 subtasks complete. significance.py with 3 frozen Pydantic models (SignificanceDimension, RoutingBand, HardTriggerClass), fixed registries, band cutoff validation, dimension score validation. 74 new tests, 371 total passing.
- 2026-02-27T21:07:13Z – codex – shell_pid=7578 – lane=planned – Rejected in review: implementation artifacts missing on main branch
- 2026-02-27T21:08:10Z – codex – shell_pid=7578 – lane=in_progress – Reopened: previous rejection was based on main-branch view; WP01 implementation exists in worktree branch
- 2026-02-27T21:08:12Z – claude-opus – shell_pid=7578 – lane=for_review – Ready for proper review: worktree commit 75160c9 has significance.py + test_significance.py; targeted tests passing
- 2026-02-27T21:08:25Z – claude-opus – shell_pid=11868 – lane=doing – Started review via workflow command
- 2026-02-27T21:11:37Z – claude-opus – shell_pid=11868 – lane=done – Review passed: WP01 merged to main. 3 frozen Pydantic models match contracts exactly. 74 new tests, 297 total, zero regressions. WP02 unblocked.

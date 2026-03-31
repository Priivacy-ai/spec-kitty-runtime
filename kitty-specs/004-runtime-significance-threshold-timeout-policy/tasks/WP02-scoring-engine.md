---
work_package_id: WP02
title: Significance Scoring Engine
dependencies: [WP01]
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-010
- FR-016
- FR-017
base_branch: main
base_commit: 10e7ee5310fb9a1d71a47dc15523cdf4c76327e4
created_at: '2026-02-27T21:12:38.319357+00:00'
subtasks:
- T006
- T007
- T008
- T009
- T010
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
- tests/test_scoring_fixtures_wp06.py
- tests/test_significance_integration.py
- tests/test_significance_integration_wp05.py
- tests/test_significance_timeout.py
- tests/test_timeout_escalation_wp04.py
- uv.lock
wp_code: WP02
---

# Work Package Prompt: WP02 – Significance Scoring Engine

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

Depends on WP01:

```bash
spec-kitty implement WP02 --base WP01
```

---

## Objectives & Success Criteria

- Implement `SignificanceScore` model that computes composite score, resolves band, handles hard-trigger override to `effective_band`
- Implement `evaluate_significance()` as a **pure function** — same inputs always produce identical output (NFR-003)
- Implement `TimeoutPolicy` model with default 600s, per-decision override, positive-integer validation
- Implement policy parsing helpers that extract band cutoffs and timeout from `MissionPolicySnapshot.extras`
- All evaluation is offline, local-only, no network calls (NFR-004)
- Evaluation completes in <50ms on commodity hardware (NFR-001)

## Context & Constraints

- **Spec reference**: FR-001 through FR-009, FR-015, FR-016, NFR-001, NFR-003, NFR-004
- **Data model**: SignificanceScore, TimeoutPolicy sections in `data-model.md`
- **Research**: R-008 (determinism guarantees), R-007 (timeout duration as seconds)
- **Contract**: `contracts/significance-evaluation.yaml` — serialized SignificanceScore shape
- **Prerequisite**: WP01 models (SignificanceDimension, RoutingBand, HardTriggerClass, validation helpers)
- **Integration point**: `MissionPolicySnapshot` from `schema.py` — uses `.extras` dict for configuration

## Subtasks & Detailed Guidance

### Subtask T006 – Implement SignificanceScore Model

- **Purpose**: The composite evaluation result that captures the full significance assessment of a decision.

- **Steps**:
  1. Add `SignificanceScore` to `significance.py`:
     ```python
     class SignificanceScore(BaseModel):
         model_config = ConfigDict(frozen=True, extra="forbid")

         dimensions: tuple[SignificanceDimension, ...] = Field(...)
         composite: int = Field(..., ge=0, le=18)
         band: RoutingBand
         hard_trigger_classes: tuple[HardTriggerClass, ...] = Field(default_factory=tuple)
         effective_band: RoutingBand
     ```
  2. Add `@model_validator(mode="after")` to enforce:
     - Exactly 6 dimensions, one per fixed name (no duplicates, no omissions):
       ```python
       dim_names = {d.name for d in self.dimensions}
       if dim_names != DIMENSION_NAMES:
           raise ValueError(...)
       ```
     - `composite` equals sum of dimension scores:
       ```python
       expected = sum(d.score for d in self.dimensions)
       if self.composite != expected:
           raise ValueError(f"composite ({self.composite}) != sum of scores ({expected})")
       ```
     - `effective_band` must be `high` when `hard_trigger_classes` is non-empty:
       ```python
       if self.hard_trigger_classes and self.effective_band.name != "high":
           raise ValueError("effective_band must be 'high' when hard_trigger_classes present")
       ```
     - When no hard triggers, `effective_band` must equal `band`:
       ```python
       if not self.hard_trigger_classes and self.effective_band != self.band:
           raise ValueError("effective_band must equal band when no hard triggers")
       ```

- **Files**: `src/spec_kitty_runtime/significance.py`
- **Parallel?**: No — the core model that T007 depends on
- **Notes**: The `dimensions` field is a tuple (not list) for immutability. Use `tuple[SignificanceDimension, ...]` not `list`.

### Subtask T007 – Implement evaluate_significance() Pure Function

- **Purpose**: The single entry point for significance evaluation — takes raw scores and returns a fully computed SignificanceScore.

- **Steps**:
  1. Define the function signature:
     ```python
     def evaluate_significance(
         dimension_scores: dict[str, int],
         hard_trigger_classes: list[str] | None = None,
         band_cutoffs: dict[str, list[int]] | None = None,
     ) -> SignificanceScore:
         """Evaluate the significance of a decision.

         Pure function: same inputs always produce identical output.
         No side effects, no randomness, no external state.
         """
     ```
  2. Implementation flow:
     a. Validate dimension scores using `validate_dimension_scores()` from WP01
     b. Build `SignificanceDimension` instances for each score
     c. Compute composite: `sum(dimension_scores.values())`
     d. Build routing bands: `make_routing_bands(band_cutoffs)`
     e. Resolve numeric band: find the band where `min_score <= composite <= max_score`
     f. Resolve hard triggers: `resolve_hard_triggers(hard_trigger_classes or [])`
     g. Determine effective_band:
        - If hard triggers present → effective_band = high band (from bands)
        - Else → effective_band = numeric band
     h. Construct and return `SignificanceScore`
  3. Dimension ordering in the tuple should be deterministic — sort by dimension name for canonical order:
     ```python
     dims = tuple(sorted(
         [SignificanceDimension(name=k, score=v) for k, v in dimension_scores.items()],
         key=lambda d: d.name,
     ))
     ```

- **Files**: `src/spec_kitty_runtime/significance.py`
- **Parallel?**: No — depends on T006 (returns SignificanceScore)
- **Notes**:
  - The function must be deterministic (NFR-003): sorted dimensions, deterministic band resolution
  - No `datetime.now()` calls — timestamps are NOT part of evaluation
  - This function is testable in complete isolation (no engine, no persistence)

### Subtask T008 – Implement TimeoutPolicy Model

- **Purpose**: Configuration governing the timeout window for decisions at medium and high bands.

- **Steps**:
  1. Define `TimeoutPolicy` frozen model:
     ```python
     class TimeoutPolicy(BaseModel):
         model_config = ConfigDict(frozen=True, extra="forbid")

         default_timeout_seconds: int = Field(default=600, gt=0)
         per_decision_timeout_seconds: int | None = Field(default=None)

         @property
         def effective_timeout_seconds(self) -> int:
             return self.per_decision_timeout_seconds if self.per_decision_timeout_seconds is not None else self.default_timeout_seconds

         @model_validator(mode="after")
         def _validate_timeouts(self) -> TimeoutPolicy:
             if self.per_decision_timeout_seconds is not None and self.per_decision_timeout_seconds <= 0:
                 raise ValueError(f"per_decision_timeout_seconds must be > 0, got {self.per_decision_timeout_seconds}")
             return self
     ```
  2. Default: 600 seconds (10 minutes) per spec
  3. Per-decision override: set by responsible human at decision time
  4. Validation: both values must be positive integers (FR-016)

- **Files**: `src/spec_kitty_runtime/significance.py`
- **Parallel?**: Yes — independent of T006/T007, can develop alongside
- **Notes**: `effective_timeout_seconds` is a `@property` (computed, not stored), since frozen models can have properties. Alternatively use `@computed_field` from Pydantic v2.

### Subtask T009 – Implement parse_band_cutoffs_from_policy()

- **Purpose**: Extract custom band cutoffs from `MissionPolicySnapshot.extras`, returning None if not configured.

- **Steps**:
  1. Define helper:
     ```python
     def parse_band_cutoffs_from_policy(
         policy: MissionPolicySnapshot,
     ) -> dict[str, list[int]] | None:
         """Extract band cutoffs from policy extras.

         Returns None if not configured (use defaults).
         Raises ValueError if configured but invalid.
         """
         cutoffs = policy.extras.get("significance_band_cutoffs")
         if cutoffs is None:
             return None
         # Validate structure: must be dict with str keys and [int, int] values
         if not isinstance(cutoffs, dict):
             raise ValueError(f"significance_band_cutoffs must be a dict, got {type(cutoffs).__name__}")
         for band_name, bounds in cutoffs.items():
             if not isinstance(bounds, list) or len(bounds) != 2:
                 raise ValueError(f"Band '{band_name}' cutoff must be [min, max], got {bounds}")
             if not all(isinstance(b, int) for b in bounds):
                 raise ValueError(f"Band '{band_name}' cutoff values must be integers")
         # Validate with band cutoff validation from WP01
         validate_band_cutoffs(cutoffs)
         return cutoffs
     ```
  2. Import `MissionPolicySnapshot` from `schema.py`

- **Files**: `src/spec_kitty_runtime/significance.py`
- **Parallel?**: Yes — independent of T006/T007/T008
- **Notes**: The extras dict uses string keys. The cutoffs format matches `contracts/` examples: `{"low": [0, 6], "medium": [7, 11], "high": [12, 18]}`

### Subtask T010 – Implement parse_timeout_from_policy()

- **Purpose**: Extract custom default timeout from `MissionPolicySnapshot.extras`, returning the standard default if not configured.

- **Steps**:
  1. Define helper:
     ```python
     def parse_timeout_from_policy(
         policy: MissionPolicySnapshot,
     ) -> int:
         """Extract default timeout from policy extras.

         Returns 600 (10 minutes) if not configured.
         Raises ValueError if configured but invalid.
         """
         timeout = policy.extras.get("significance_default_timeout_seconds")
         if timeout is None:
             return 600
         if not isinstance(timeout, int):
             raise ValueError(f"significance_default_timeout_seconds must be int, got {type(timeout).__name__}")
         if timeout <= 0:
             raise ValueError(f"significance_default_timeout_seconds must be > 0, got {timeout}")
         return timeout
     ```

- **Files**: `src/spec_kitty_runtime/significance.py`
- **Parallel?**: Yes — independent of all other T009 subtasks
- **Notes**: Default value 600s matches spec (10-minute default, FR-010) and research R-007

## Risks & Mitigations

- **Evaluation correctness at boundaries**: The band routing for boundary scores (6, 7, 11, 12) is critical. Test these explicitly in WP06.
- **Determinism guarantee**: No randomness, no datetime, no external state. Sort dimensions by name for canonical ordering.
- **Policy parsing robustness**: Missing keys return defaults; present-but-invalid keys raise ValueError. Never silently ignore malformed policy.
- **Type safety with extras dict**: `MissionPolicySnapshot.extras` is `dict[str, Any]` — validate types explicitly in parsing helpers.

## Review Guidance

- Verify `evaluate_significance()` is a pure function with no side effects
- Verify boundary scores: 6 → low, 7 → medium, 11 → medium, 12 → high
- Verify hard-trigger override: any hard trigger → effective_band = high regardless of numeric score
- Verify SignificanceScore validator catches: wrong composite sum, wrong dimension count, effective_band mismatch
- Verify TimeoutPolicy rejects zero and negative timeouts
- Verify policy parsing returns None/default for missing keys, raises for invalid keys

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

- 2026-02-27T20:43:12Z – system – lane=planned – Prompt created.
- 2026-02-27T21:12:38Z – claude-opus – shell_pid=14111 – lane=doing – Assigned agent via workflow command
- 2026-02-27T21:16:23Z – claude-opus – shell_pid=14111 – lane=for_review – Ready for review: SignificanceScore model, evaluate_significance() pure function, TimeoutPolicy model, parse_band_cutoffs_from_policy(), parse_timeout_from_policy(). 61 new tests, 432 total passing.
- 2026-02-27T21:17:03Z – claude-opus – shell_pid=16364 – lane=doing – Started review via workflow command
- 2026-02-27T21:20:13Z – claude-opus – shell_pid=16364 – lane=done – Review passed: WP02 merged to main. All acceptance criteria verified, 61 new tests, 432 total passing.

---
work_package_id: WP01
title: AuditConfig + AuditStep Schema
dependencies: '[]'
base_branch: main
base_commit: 35ff370855f7e734b94aac3b630b187f0a98dace
created_at: '2026-03-01T07:47:20.924880+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T007
phase: Phase 1 - Schema Foundation
history:
- timestamp: '2026-02-26T00:00:00Z'
  lane: planned
  agent: system
  action: Prompt generated via /spec-kitty.specify
authoritative_surface: ''
depends_on: []
execution_mode: code_change
feature: 001-audit-primitive-decision-checkpoint
mission_id: 01KN234FRN2DACHD1S4PM2264H
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
- kitty-specs/004-runtime-significance-threshold-timeout-policy/status.json
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
- uv.lock
wp_code: WP01
---

# Work Package Prompt: WP01 – AuditConfig + AuditStep Schema

## Context

This is the foundation WP for feature `001-audit-primitive-decision-checkpoint` in the `spec-kitty-runtime` Python library.

The codebase is at `src/spec_kitty_runtime/`. The main schema file is `src/spec_kitty_runtime/schema.py` which contains all Pydantic models including `MissionTemplate`, `PromptStep`, `MissionPolicySnapshot`, etc. Tests live under `tests/`.

All models use `pydantic>=2.0` with `ConfigDict(frozen=True)`. The project uses `pytest>=8.0`.

**Key constraint**: 2.x only. No 1.x compat. No fallback mechanisms. Code must fail explicitly on invalid config.

## Objective

Add `AuditConfig` and `AuditStep` Pydantic models to `schema.py`, extend `MissionTemplate` to include `audit_steps`, and extend `load_mission_template_file` to parse and validate the new schema.

## Subtasks

- [ ] T001 Add `AuditConfig` Pydantic model with required `trigger_mode: Literal["manual", "post_merge", "both"]` and required `enforcement: Literal["advisory", "blocking"]` — both fields have NO defaults (explicit declaration enforced)
- [ ] T002 Add optional `label: str | None = None` and `metadata: dict[str, Any] | None = None` to `AuditConfig`
- [ ] T003 Add `AuditStep` Pydantic model with `id: str`, `title: str`, `description: str = ""`, `audit: AuditConfig`, `depends_on: list[str] = []` — NO `prompt`, `prompt_template`, or `requires_inputs` fields
- [ ] T004 Extend `MissionTemplate` with `audit_steps: list[AuditStep] = Field(default_factory=list)`
- [ ] T005 Extend `load_mission_template_file` to parse `audit_steps` key from YAML (alongside existing `steps` parsing)
- [ ] T006 Add validation in `load_mission_template_file`: raise `MissionRuntimeError` if both `steps` and `audit_steps` are empty after loading
- [ ] T007 Write `tests/test_audit_schema.py` with deterministic tests (no mocks, no network) covering all acceptance criteria below

## Acceptance Criteria

### AC-1: Schema validation
- `AuditConfig(trigger_mode="manual", enforcement="blocking")` parses without error
- `AuditConfig(trigger_mode="invalid", enforcement="blocking")` raises `pydantic.ValidationError`
- `AuditConfig(trigger_mode="manual", enforcement="invalid")` raises `pydantic.ValidationError`
- `AuditStep` without `audit` field raises `pydantic.ValidationError`
- `AuditConfig` without `trigger_mode` raises `pydantic.ValidationError` (no default)
- `AuditConfig` without `enforcement` raises `pydantic.ValidationError` (no default)

### AC-2: YAML loading
- Mission YAML with `audit_steps` list loads successfully via `load_mission_template_file`
- Mission YAML with only `audit_steps` (no `steps` key) loads successfully
- Mission YAML with neither `steps` nor `audit_steps` (or both empty) raises `MissionRuntimeError`
- Mission YAML with unknown field in `audit:` block must fail validation (Pydantic strict mode or `model_config = ConfigDict(extra="forbid")` on `AuditConfig`)

## Example YAML that must load successfully

```yaml
mission:
  key: test-audit-mission
  name: Test Audit Mission
  version: "1.0.0"
steps:
  - id: step-01
    title: Initial step
audit_steps:
  - id: audit-01
    title: Post-merge policy check
    audit:
      trigger_mode: post_merge
      enforcement: blocking
```

## Implementation Notes

- Use `model_config = ConfigDict(frozen=True, extra="forbid")` on `AuditConfig` to enforce unknown-field rejection
- The `depends_on` field in `AuditStep` follows the same semantics as `PromptStep.depends_on` (list of step IDs that must complete first)
- `AuditStep` is intentionally NOT a subclass of `PromptStep` — it is a distinct schema type
- `MissionTemplate.audit_steps` should default to empty list (compatible with existing missions that have no audit steps)

## Files to Create/Modify

- **Modify**: `src/spec_kitty_runtime/schema.py`
- **Create**: `tests/test_audit_schema.py`

## Test Structure

```python
# tests/test_audit_schema.py
import pytest
from pydantic import ValidationError
from spec_kitty_runtime.schema import AuditConfig, AuditStep, MissionTemplate, MissionRuntimeError, load_mission_template_file

class TestAuditConfig:
    def test_valid_manual_blocking(self): ...
    def test_valid_post_merge_advisory(self): ...
    def test_invalid_trigger_mode(self): ...
    def test_invalid_enforcement(self): ...
    def test_trigger_mode_required(self): ...
    def test_enforcement_required(self): ...
    def test_extra_fields_forbidden(self): ...
    def test_optional_label(self): ...
    def test_optional_metadata(self): ...

class TestAuditStep:
    def test_valid_audit_step(self): ...
    def test_missing_audit_field_raises(self): ...
    def test_no_prompt_field(self): ...
    def test_depends_on_default_empty(self): ...

class TestMissionTemplateWithAuditSteps:
    def test_load_with_audit_steps(self, tmp_path): ...
    def test_load_audit_steps_only(self, tmp_path): ...
    def test_load_neither_raises(self, tmp_path): ...
    def test_load_both_empty_raises(self, tmp_path): ...
```

## Completion Steps

1. Implement all subtasks
2. Run: `python -m pytest tests/test_audit_schema.py -v`
3. Ensure all tests pass
4. Commit: `git add -A && git commit -m "feat(WP01): AuditConfig + AuditStep schema"`
5. Mark subtasks done: `spec-kitty agent tasks mark-status T001 T002 T003 T004 T005 T006 T007 --status done --feature 001-audit-primitive-decision-checkpoint`
6. Move to review: `spec-kitty agent tasks move-task WP01 --to for_review --feature 001-audit-primitive-decision-checkpoint --note "Schema implementation complete, all tests passing"`

## Activity Log

- 2026-02-26T14:12:36Z – coordinator – shell_pid=90317 – lane=doing – Assigned agent via workflow command
- 2026-02-26T14:16:35Z – coordinator – shell_pid=90317 – lane=for_review – Schema implementation complete, 26 tests passing (156 total in suite, zero regressions)
- 2026-02-26T14:17:06Z – claude-reviewer – shell_pid=92818 – lane=doing – Started review via workflow command
- 2026-02-26T14:19:30Z – claude-reviewer – shell_pid=92818 – lane=done – Review passed: All 7 subtasks delivered. 26/26 AC tests pass, 156/156 full suite passes (zero regressions). AuditConfig (extra=forbid, frozen), AuditStep (distinct from PromptStep), MissionTemplate.audit_steps field, and load_mission_template_file extension all correct. Implementation notes fully followed.
- 2026-03-01T07:47:20Z – claude-opus – shell_pid=93343 – lane=doing – Started implementation via workflow command
- 2026-03-01T07:49:37Z – claude-opus – shell_pid=93343 – lane=doing – All deliverables (AuditConfig, AuditStep, MissionTemplate.audit_steps, load_mission_template_file extension, 26 tests) already exist on main from prior implementation cycle. 730/730 full suite passing. No new code changes needed.
- 2026-03-01T07:49:48Z – claude-opus – shell_pid=93343 – lane=for_review – Schema implementation verified complete on main (prior cycle). 26/26 AC tests pass, 730/730 full suite passes. No new code needed - AuditConfig, AuditStep, MissionTemplate.audit_steps, load_mission_template_file all present and correct.
- 2026-03-01T07:50:26Z – claude-opus-reviewer – shell_pid=95001 – lane=doing – Started review via workflow command
- 2026-03-01T07:52:26Z – claude-opus-reviewer – shell_pid=95001 – lane=done – Review passed: All 7 subtasks delivered (on main from prior cycle). 26/26 AC tests pass, 730/730 full suite (zero regressions). AuditConfig (frozen, extra=forbid), AuditStep (distinct from PromptStep), MissionTemplate.audit_steps, load_mission_template_file extension all correct per spec. Dependents WP02 and WP04 unblocked.

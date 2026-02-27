---
work_package_id: WP06
title: Test Fixtures & Scoring Test Suite
lane: "doing"
dependencies: [WP02]
base_branch: main
base_commit: d9f40bd12cd56ca647ad5ed6a73f6a554dca8af9
created_at: '2026-02-27T22:12:36.633791+00:00'
subtasks:
- T026
- T027
- T028
- T029
- T030
- T031
phase: Phase 2 - Validation
assignee: ''
agent: ''
shell_pid: "42199"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-02-27T20:43:12Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-008
- FR-015
---

# Work Package Prompt: WP06 – Test Fixtures & Scoring Test Suite

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

Depends on WP02 (can run in parallel with WP03–WP05):

```bash
spec-kitty implement WP06 --base WP02
```

---

## Objectives & Success Criteria

- Create 4 YAML mission fixtures covering all significance bands and hard-trigger override
- Write comprehensive test suite in `tests/test_significance.py` covering:
  - Dimension validation (valid/invalid names, scores)
  - Composite computation and band routing for all three bands
  - Hard-trigger override (all 5 classes, multiple simultaneous, high score + trigger)
  - Boundary score tests at exact band transitions (0, 6, 7, 11, 12, 18)
  - Band cutoff validation (valid custom, overlapping, gaps, defaults)
- All tests deterministic, offline, no randomness (NFR-003, NFR-004)
- Zero flaky tests

## Context & Constraints

- **Spec reference**: US1 (scoring/routing), US2 (hard-trigger), SC-001 through SC-003, SC-008
- **Contract reference**: All 3 contract YAML files define expected payload shapes
- **Test patterns**: Follow existing test conventions from `tests/test_raci.py` and `tests/test_audit_engine.py`
- **Fixture patterns**: Follow existing YAML fixture format from `tests/fixtures/`
- **No randomness**: Tests use fixed inputs and verify deterministic outputs
- **Prerequisite**: WP01 + WP02 (models and evaluation function must exist)

## Subtasks & Detailed Guidance

### Subtask T026 – Create 4 YAML Mission Fixtures

- **Purpose**: Provide realistic, complete mission templates with significance blocks for each band scenario.

- **Steps**:
  1. Create `tests/fixtures/mission_significance_low.yaml`:
     ```yaml
     mission:
       key: sig-low-test
       name: Low Significance Test Mission
       version: "1.0.0"

     steps:
       - id: prepare
         title: Prepare artifacts
         prompt: "Gather artifacts"

     audit_steps:
       - id: low-review
         title: Low-impact configuration review
         audit:
           trigger_mode: manual
           enforcement: blocking
         significance:
           dimensions:
             user_customer_impact: 1
             architectural_system_impact: 1
             data_security_compliance_impact: 1
             operational_reliability_impact: 1
             financial_commercial_impact: 1
             cross_team_blast_radius: 1
           hard_triggers: []
         depends_on: [prepare]
     ```
     - Composite: 6 (upper boundary of low band)
     - Expected band: low → auto-proceed

  2. Create `tests/fixtures/mission_significance_medium.yaml`:
     ```yaml
     # Same structure as above but with:
     significance:
       dimensions:
         user_customer_impact: 2
         architectural_system_impact: 1
         data_security_compliance_impact: 2
         operational_reliability_impact: 2
         financial_commercial_impact: 1
         cross_team_blast_radius: 1
       hard_triggers: []
     ```
     - Composite: 9 (mid-range of medium band)
     - Expected band: medium → soft gate

  3. Create `tests/fixtures/mission_significance_high.yaml`:
     ```yaml
     significance:
       dimensions:
         user_customer_impact: 3
         architectural_system_impact: 3
         data_security_compliance_impact: 3
         operational_reliability_impact: 2
         financial_commercial_impact: 2
         cross_team_blast_radius: 2
       hard_triggers: []
     ```
     - Composite: 15 (mid-range of high band)
     - Expected band: high → hard gate

  4. Create `tests/fixtures/mission_hard_trigger.yaml`:
     ```yaml
     significance:
       dimensions:
         user_customer_impact: 0
         architectural_system_impact: 0
         data_security_compliance_impact: 1
         operational_reliability_impact: 0
         financial_commercial_impact: 0
         cross_team_blast_radius: 0
       hard_triggers:
         - production_data_destructive
     ```
     - Composite: 1 (low band numerically)
     - Expected: hard-trigger override → effective_band = high

- **Files**: `tests/fixtures/mission_significance_low.yaml`, `tests/fixtures/mission_significance_medium.yaml`, `tests/fixtures/mission_significance_high.yaml`, `tests/fixtures/mission_hard_trigger.yaml`
- **Parallel?**: Yes — fixtures are independent of test code
- **Notes**: Follow the existing fixture structure from `tests/fixtures/` (mission key, steps, audit_steps). Each fixture is a complete, valid mission template.

### Subtask T027 – Write Dimension Validation Tests

- **Purpose**: Verify that `SignificanceDimension` and `validate_dimension_scores()` correctly enforce constraints.

- **Steps**:
  1. Create `tests/test_significance.py` with standard imports:
     ```python
     import pytest
     from spec_kitty_runtime.significance import (
         SignificanceDimension,
         RoutingBand,
         HardTriggerClass,
         SignificanceScore,
         evaluate_significance,
         validate_dimension_scores,
         validate_band_cutoffs,
         DIMENSION_NAMES,
         HARD_TRIGGER_REGISTRY,
         DEFAULT_BANDS,
     )
     ```
  2. Test valid dimension construction:
     ```python
     def test_valid_dimension():
         dim = SignificanceDimension(name="user_customer_impact", score=2)
         assert dim.name == "user_customer_impact"
         assert dim.score == 2
     ```
  3. Test invalid score (outside 0–3):
     ```python
     def test_dimension_score_out_of_range():
         with pytest.raises(ValueError, match="score"):
             SignificanceDimension(name="user_customer_impact", score=4)

     def test_dimension_score_negative():
         with pytest.raises(ValueError, match="score"):
             SignificanceDimension(name="user_customer_impact", score=-1)
     ```
  4. Test invalid dimension name:
     ```python
     def test_dimension_unknown_name():
         with pytest.raises(ValueError, match="dimension"):
             SignificanceDimension(name="made_up_dimension", score=1)
     ```
  5. Test `validate_dimension_scores()`:
     ```python
     def test_validate_scores_valid():
         scores = {name: 1 for name in DIMENSION_NAMES}
         validate_dimension_scores(scores)  # Should not raise

     def test_validate_scores_missing_dimension():
         scores = {name: 1 for name in list(DIMENSION_NAMES)[:5]}
         with pytest.raises(ValueError, match="missing"):
             validate_dimension_scores(scores)

     def test_validate_scores_extra_dimension():
         scores = {name: 1 for name in DIMENSION_NAMES}
         scores["fake_dimension"] = 1
         with pytest.raises(ValueError, match="unexpected"):
             validate_dimension_scores(scores)
     ```

- **Files**: `tests/test_significance.py` (new file)
- **Parallel?**: Yes — independent section of the test file
- **Notes**: Test each dimension name is in the DIMENSION_NAMES set. Test all 6 are required. Test score boundaries (0 valid, 3 valid, 4 invalid, -1 invalid).

### Subtask T028 – Write Composite & Band Routing Tests

- **Purpose**: Verify that `evaluate_significance()` correctly computes composite scores and routes to the right band.

- **Steps**:
  1. Test low band (composite 0–6):
     ```python
     def test_evaluate_low_band():
         scores = {name: 1 for name in DIMENSION_NAMES}  # total 6
         result = evaluate_significance(dimension_scores=scores)
         assert result.composite == 6
         assert result.band.name == "low"
         assert result.effective_band.name == "low"
         assert len(result.hard_trigger_classes) == 0
     ```
  2. Test medium band (composite 7–11):
     ```python
     def test_evaluate_medium_band():
         scores = dict.fromkeys(DIMENSION_NAMES, 1)
         scores["user_customer_impact"] = 2
         scores["data_security_compliance_impact"] = 2
         # total = 2+1+2+1+1+1 = 8
         result = evaluate_significance(dimension_scores=scores)
         assert result.composite == 8
         assert result.band.name == "medium"
         assert result.effective_band.name == "medium"
     ```
  3. Test high band (composite 12–18):
     ```python
     def test_evaluate_high_band():
         scores = {name: 2 for name in DIMENSION_NAMES}  # total 12
         result = evaluate_significance(dimension_scores=scores)
         assert result.composite == 12
         assert result.band.name == "high"
         assert result.effective_band.name == "high"
     ```
  4. Test all-zeros (composite 0) and all-threes (composite 18):
     ```python
     def test_evaluate_all_zeros():
         scores = {name: 0 for name in DIMENSION_NAMES}
         result = evaluate_significance(dimension_scores=scores)
         assert result.composite == 0
         assert result.band.name == "low"

     def test_evaluate_all_threes():
         scores = {name: 3 for name in DIMENSION_NAMES}
         result = evaluate_significance(dimension_scores=scores)
         assert result.composite == 18
         assert result.band.name == "high"
     ```
  5. Verify dimensions are sorted deterministically in the result

- **Files**: `tests/test_significance.py`
- **Parallel?**: Yes — independent section of the test file
- **Notes**: Each test constructs a score dict from DIMENSION_NAMES to ensure all 6 are present.

### Subtask T029 – Write Hard-Trigger Override Tests

- **Purpose**: Verify that hard-trigger classes force `effective_band=high` regardless of numeric score (US2).

- **Steps**:
  1. Test each of the 5 hard-trigger classes independently:
     ```python
     @pytest.mark.parametrize("trigger_id", list(HARD_TRIGGER_REGISTRY.keys()))
     def test_hard_trigger_forces_high(trigger_id):
         scores = {name: 0 for name in DIMENSION_NAMES}  # total 0 (low band)
         result = evaluate_significance(
             dimension_scores=scores,
             hard_trigger_classes=[trigger_id],
         )
         assert result.composite == 0
         assert result.band.name == "low"  # numeric band is still low
         assert result.effective_band.name == "high"  # but effective is high
         assert len(result.hard_trigger_classes) == 1
         assert result.hard_trigger_classes[0].class_id == trigger_id
     ```
  2. Test multiple simultaneous hard-triggers:
     ```python
     def test_multiple_hard_triggers():
         scores = {name: 0 for name in DIMENSION_NAMES}
         result = evaluate_significance(
             dimension_scores=scores,
             hard_trigger_classes=[
                 "production_data_destructive",
                 "security_privacy_access_control",
                 "legal_compliance_regulatory",
             ],
         )
         assert result.effective_band.name == "high"
         assert len(result.hard_trigger_classes) == 3
     ```
  3. Test high numeric score + hard-trigger (both captured):
     ```python
     def test_high_score_with_hard_trigger():
         scores = {name: 3 for name in DIMENSION_NAMES}  # total 18 (high)
         result = evaluate_significance(
             dimension_scores=scores,
             hard_trigger_classes=["architecture_foundation"],
         )
         assert result.composite == 18
         assert result.band.name == "high"
         assert result.effective_band.name == "high"
         assert len(result.hard_trigger_classes) == 1  # trigger recorded alongside score
     ```
  4. Test unknown hard-trigger class ID:
     ```python
     def test_unknown_hard_trigger_rejected():
         scores = {name: 0 for name in DIMENSION_NAMES}
         with pytest.raises(ValueError, match="Unknown hard-trigger"):
             evaluate_significance(
                 dimension_scores=scores,
                 hard_trigger_classes=["not_a_real_trigger"],
             )
     ```

- **Files**: `tests/test_significance.py`
- **Parallel?**: Yes — independent section of the test file
- **Notes**: Use `@pytest.mark.parametrize` for the 5-class test to ensure every class is verified independently (SC-003).

### Subtask T030 – Write Boundary Score Tests

- **Purpose**: Verify correct routing at the exact band transition points (spec acceptance scenarios US1.4, US1.5).

- **Steps**:
  1. Test exact boundaries with parametrize:
     ```python
     @pytest.mark.parametrize("total,expected_band", [
         (0, "low"),
         (6, "low"),       # upper boundary of low
         (7, "medium"),    # lower boundary of medium (US1.4)
         (11, "medium"),   # upper boundary of medium
         (12, "high"),     # lower boundary of high (US1.5)
         (18, "high"),     # maximum possible
     ])
     def test_band_boundaries(total, expected_band):
         # Distribute total across dimensions deterministically
         scores = _make_scores_for_total(total)
         result = evaluate_significance(dimension_scores=scores)
         assert result.composite == total
         assert result.band.name == expected_band
         assert result.effective_band.name == expected_band
     ```
  2. Helper function to create a score dict with a specific total:
     ```python
     def _make_scores_for_total(total: int) -> dict[str, int]:
         """Distribute a total score across the 6 dimensions deterministically."""
         names = sorted(DIMENSION_NAMES)
         scores = {}
         remaining = total
         for i, name in enumerate(names):
             # Distribute evenly, put remainder on last dimensions
             if i < len(names) - 1:
                 score = min(remaining, 3)
                 score = min(score, remaining - (len(names) - i - 1) * 0)  # ensure non-negative for remaining
                 # Simple approach: fill up to 3 per dimension
                 score = min(3, remaining)
                 remaining_dims = len(names) - i - 1
                 # Ensure enough left for remaining dims (0 each minimum)
                 score = min(3, remaining)
                 scores[name] = score
                 remaining -= score
             else:
                 scores[name] = remaining
         return scores
     ```
     A simpler approach: fill dimensions to 3, leave rest at 0:
     ```python
     def _make_scores_for_total(total: int) -> dict[str, int]:
         names = sorted(DIMENSION_NAMES)
         scores = {}
         remaining = total
         for name in names:
             s = min(3, remaining)
             scores[name] = s
             remaining -= s
         return scores
     ```
  3. Also test boundary transitions with one score unit difference:
     ```python
     def test_boundary_low_to_medium():
         """Score 6 is low, score 7 is medium."""
         low = evaluate_significance(_make_scores_for_total(6))
         med = evaluate_significance(_make_scores_for_total(7))
         assert low.band.name == "low"
         assert med.band.name == "medium"

     def test_boundary_medium_to_high():
         """Score 11 is medium, score 12 is high."""
         med = evaluate_significance(_make_scores_for_total(11))
         high = evaluate_significance(_make_scores_for_total(12))
         assert med.band.name == "medium"
         assert high.band.name == "high"
     ```

- **Files**: `tests/test_significance.py`
- **Parallel?**: Yes — independent section of the test file
- **Notes**: These boundary tests directly validate spec acceptance scenarios US1.4 (score 7 → medium) and US1.5 (score 12 → high). Critical for correctness.

### Subtask T031 – Write Band Cutoff Validation Tests

- **Purpose**: Verify that `validate_band_cutoffs()` correctly accepts valid configurations and rejects invalid ones.

- **Steps**:
  1. Test valid default cutoffs:
     ```python
     def test_default_cutoffs_valid():
         validate_band_cutoffs({"low": [0, 6], "medium": [7, 11], "high": [12, 18]})
     ```
  2. Test valid custom cutoffs:
     ```python
     def test_custom_cutoffs_valid():
         validate_band_cutoffs({"low": [0, 5], "medium": [6, 10], "high": [11, 18]})
     ```
  3. Test overlapping ranges:
     ```python
     def test_cutoffs_overlapping_rejected():
         with pytest.raises(ValueError, match="[Oo]verlap"):
             validate_band_cutoffs({"low": [0, 7], "medium": [7, 11], "high": [12, 18]})
     ```
  4. Test gap between bands:
     ```python
     def test_cutoffs_gap_rejected():
         with pytest.raises(ValueError, match="[Gg]ap"):
             validate_band_cutoffs({"low": [0, 5], "medium": [7, 11], "high": [12, 18]})
     ```
  5. Test wrong start (not 0):
     ```python
     def test_cutoffs_not_starting_at_zero():
         with pytest.raises(ValueError, match="start at 0"):
             validate_band_cutoffs({"low": [1, 6], "medium": [7, 11], "high": [12, 18]})
     ```
  6. Test wrong end (not 18):
     ```python
     def test_cutoffs_not_ending_at_18():
         with pytest.raises(ValueError, match="end at 18"):
             validate_band_cutoffs({"low": [0, 6], "medium": [7, 11], "high": [12, 17]})
     ```
  7. Test wrong number of bands:
     ```python
     def test_cutoffs_wrong_band_count():
         with pytest.raises(ValueError, match="3 bands"):
             validate_band_cutoffs({"low": [0, 9], "high": [10, 18]})
     ```
  8. Test with evaluate_significance using custom cutoffs:
     ```python
     def test_evaluate_with_custom_cutoffs():
         scores = {name: 1 for name in DIMENSION_NAMES}  # total 6
         # With custom cutoffs: 6 is in medium band [5-10]
         result = evaluate_significance(
             dimension_scores=scores,
             band_cutoffs={"low": [0, 4], "medium": [5, 10], "high": [11, 18]},
         )
         assert result.band.name == "medium"  # 6 is medium under custom cutoffs
     ```

- **Files**: `tests/test_significance.py`
- **Parallel?**: Yes — independent section of the test file
- **Notes**: Error messages should be specific enough for the parametrized match strings to work.

## Risks & Mitigations

- **Test isolation**: Each test must be fully independent. No shared mutable state. Use function-scoped fixtures if needed.
- **Determinism**: No `datetime.now()`, no randomness, no network calls. All inputs are constants.
- **Fixture validity**: Each YAML fixture must be a complete, valid mission template that the engine can load.
- **Score distribution helper**: The `_make_scores_for_total()` helper must produce exactly 6 dimensions with valid 0–3 scores summing to the target total. Test the helper itself if complex.

## Review Guidance

- Verify all 5 hard-trigger classes are tested independently (parametrize test)
- Verify boundary scores 6→low, 7→medium, 11→medium, 12→high are explicitly tested
- Verify band cutoff validation catches all invalid configurations (overlap, gap, wrong range, wrong count)
- Verify custom cutoffs change routing behavior
- Verify all tests are deterministic (no randomness, no external state)
- Verify fixture YAML files are complete mission templates

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

- 2026-02-27T20:43:12Z – system – lane=planned – Prompt created.

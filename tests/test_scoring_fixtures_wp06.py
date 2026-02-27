"""Tests for WP06: Test Fixtures & Scoring Test Suite.

Tests cover:
- T026: YAML mission fixture validation (4 fixtures, all bands + hard-trigger)
- T027: Dimension validation (valid/invalid names, scores)
- T028: Composite computation and band routing for all three bands
- T029: Hard-trigger override (all 5 classes, multiple simultaneous, high score + trigger)
- T030: Boundary score tests at exact band transitions (0, 6, 7, 11, 12, 18)
- T031: Band cutoff validation (valid custom, overlapping, gaps, defaults)

All tests deterministic, offline, no randomness (NFR-003, NFR-004).
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from spec_kitty_runtime.significance import (
    DEFAULT_BANDS,
    DIMENSION_NAMES,
    HARD_TRIGGER_REGISTRY,
    SignificanceDimension,
    SignificanceScore,
    evaluate_significance,
    validate_band_cutoffs,
    validate_dimension_scores,
)

FIXTURES = Path(__file__).parent / "fixtures"


# ============================================================================
# Helpers
# ============================================================================


def _make_scores_for_total(total: int) -> dict[str, int]:
    """Distribute a total score across the 6 dimensions deterministically.

    Fills dimensions (sorted alphabetically) up to 3 each until the total
    is reached. Remaining dimensions get 0.
    """
    names = sorted(DIMENSION_NAMES)
    scores: dict[str, int] = {}
    remaining = total
    for name in names:
        s = min(3, remaining)
        scores[name] = s
        remaining -= s
    return scores


def _load_fixture(name: str) -> dict:
    """Load a YAML fixture file from the fixtures directory."""
    path = FIXTURES / name
    with open(path) as f:
        return yaml.safe_load(f)


# ============================================================================
# T026: YAML Mission Fixture Validation
# ============================================================================


class TestFixtureFiles:
    """Verify the 4 YAML mission fixtures are valid and complete."""

    def test_fixture_low_exists_and_loads(self) -> None:
        data = _load_fixture("mission_significance_low.yaml")
        assert "mission" in data
        assert "steps" in data
        assert "audit_steps" in data

    def test_fixture_low_dimensions_sum_to_6(self) -> None:
        data = _load_fixture("mission_significance_low.yaml")
        dims = data["audit_steps"][0]["significance"]["dimensions"]
        assert sum(dims.values()) == 6
        assert set(dims.keys()) == set(DIMENSION_NAMES)

    def test_fixture_low_produces_low_band(self) -> None:
        data = _load_fixture("mission_significance_low.yaml")
        dims = data["audit_steps"][0]["significance"]["dimensions"]
        result = evaluate_significance(dimension_scores=dims)
        assert result.composite == 6
        assert result.band.name == "low"
        assert result.effective_band.name == "low"

    def test_fixture_medium_exists_and_loads(self) -> None:
        data = _load_fixture("mission_significance_medium.yaml")
        assert "mission" in data
        assert data["mission"]["key"] == "sig-medium-test"

    def test_fixture_medium_dimensions_sum_to_9(self) -> None:
        data = _load_fixture("mission_significance_medium.yaml")
        dims = data["audit_steps"][0]["significance"]["dimensions"]
        assert sum(dims.values()) == 9
        assert set(dims.keys()) == set(DIMENSION_NAMES)

    def test_fixture_medium_produces_medium_band(self) -> None:
        data = _load_fixture("mission_significance_medium.yaml")
        dims = data["audit_steps"][0]["significance"]["dimensions"]
        result = evaluate_significance(dimension_scores=dims)
        assert result.composite == 9
        assert result.band.name == "medium"
        assert result.effective_band.name == "medium"

    def test_fixture_high_exists_and_loads(self) -> None:
        data = _load_fixture("mission_significance_high.yaml")
        assert "mission" in data
        assert data["mission"]["key"] == "sig-high-test"

    def test_fixture_high_dimensions_sum_to_15(self) -> None:
        data = _load_fixture("mission_significance_high.yaml")
        dims = data["audit_steps"][0]["significance"]["dimensions"]
        assert sum(dims.values()) == 15
        assert set(dims.keys()) == set(DIMENSION_NAMES)

    def test_fixture_high_produces_high_band(self) -> None:
        data = _load_fixture("mission_significance_high.yaml")
        dims = data["audit_steps"][0]["significance"]["dimensions"]
        result = evaluate_significance(dimension_scores=dims)
        assert result.composite == 15
        assert result.band.name == "high"
        assert result.effective_band.name == "high"

    def test_fixture_hard_trigger_exists_and_loads(self) -> None:
        data = _load_fixture("mission_hard_trigger.yaml")
        assert "mission" in data
        assert data["mission"]["key"] == "sig-hard-trigger-test"

    def test_fixture_hard_trigger_low_score_high_effective(self) -> None:
        data = _load_fixture("mission_hard_trigger.yaml")
        sig = data["audit_steps"][0]["significance"]
        dims = sig["dimensions"]
        triggers = sig["hard_triggers"]
        result = evaluate_significance(
            dimension_scores=dims,
            hard_trigger_classes=triggers,
        )
        assert result.composite == 1
        assert result.band.name == "low"
        assert result.effective_band.name == "high"
        assert len(result.hard_trigger_classes) == 1

    def test_fixture_hard_trigger_has_no_empty_triggers(self) -> None:
        data = _load_fixture("mission_hard_trigger.yaml")
        triggers = data["audit_steps"][0]["significance"]["hard_triggers"]
        assert len(triggers) == 1
        assert triggers[0] == "production_data_destructive"

    def test_all_fixtures_have_complete_mission_structure(self) -> None:
        fixture_names = [
            "mission_significance_low.yaml",
            "mission_significance_medium.yaml",
            "mission_significance_high.yaml",
            "mission_hard_trigger.yaml",
        ]
        for name in fixture_names:
            data = _load_fixture(name)
            assert "mission" in data, f"{name}: missing 'mission'"
            assert "key" in data["mission"], f"{name}: missing 'mission.key'"
            assert "name" in data["mission"], f"{name}: missing 'mission.name'"
            assert "version" in data["mission"], f"{name}: missing 'mission.version'"
            assert "steps" in data, f"{name}: missing 'steps'"
            assert len(data["steps"]) > 0, f"{name}: empty 'steps'"
            assert "audit_steps" in data, f"{name}: missing 'audit_steps'"
            assert len(data["audit_steps"]) > 0, f"{name}: empty 'audit_steps'"

    def test_all_fixtures_have_valid_significance_blocks(self) -> None:
        fixture_names = [
            "mission_significance_low.yaml",
            "mission_significance_medium.yaml",
            "mission_significance_high.yaml",
            "mission_hard_trigger.yaml",
        ]
        for name in fixture_names:
            data = _load_fixture(name)
            sig = data["audit_steps"][0]["significance"]
            assert "dimensions" in sig, f"{name}: missing 'dimensions'"
            assert "hard_triggers" in sig, f"{name}: missing 'hard_triggers'"
            dims = sig["dimensions"]
            assert set(dims.keys()) == set(DIMENSION_NAMES), (
                f"{name}: dimension keys mismatch"
            )
            for dim_name, score in dims.items():
                assert 0 <= score <= 3, (
                    f"{name}: {dim_name} score {score} out of range"
                )


# ============================================================================
# T027: Dimension Validation Tests
# ============================================================================


class TestDimensionValidation:
    """Verify SignificanceDimension and validate_dimension_scores constraints."""

    def test_valid_dimension(self) -> None:
        dim = SignificanceDimension(name="user_customer_impact", score=2)
        assert dim.name == "user_customer_impact"
        assert dim.score == 2

    def test_dimension_score_out_of_range(self) -> None:
        with pytest.raises(ValueError, match="score"):
            SignificanceDimension(name="user_customer_impact", score=4)

    def test_dimension_score_negative(self) -> None:
        with pytest.raises(ValueError, match="score"):
            SignificanceDimension(name="user_customer_impact", score=-1)

    def test_dimension_unknown_name(self) -> None:
        with pytest.raises(ValueError, match="dimension"):
            SignificanceDimension(name="made_up_dimension", score=1)

    @pytest.mark.parametrize("score", [0, 1, 2, 3])
    def test_all_valid_scores(self, score: int) -> None:
        dim = SignificanceDimension(name="user_customer_impact", score=score)
        assert dim.score == score

    @pytest.mark.parametrize("name", sorted(DIMENSION_NAMES))
    def test_all_valid_dimension_names(self, name: str) -> None:
        dim = SignificanceDimension(name=name, score=1)
        assert dim.name == name

    def test_validate_scores_valid(self) -> None:
        scores = {name: 1 for name in DIMENSION_NAMES}
        validate_dimension_scores(scores)  # Should not raise

    def test_validate_scores_missing_dimension(self) -> None:
        scores = {name: 1 for name in list(DIMENSION_NAMES)[:5]}
        with pytest.raises(ValueError, match="missing"):
            validate_dimension_scores(scores)

    def test_validate_scores_extra_dimension(self) -> None:
        scores = {name: 1 for name in DIMENSION_NAMES}
        scores["fake_dimension"] = 1
        with pytest.raises(ValueError, match="unexpected"):
            validate_dimension_scores(scores)


# ============================================================================
# T028: Composite & Band Routing Tests
# ============================================================================


class TestCompositeAndBandRouting:
    """Verify evaluate_significance computes composites and routes to correct band."""

    def test_evaluate_low_band(self) -> None:
        scores = {name: 1 for name in DIMENSION_NAMES}  # total 6
        result = evaluate_significance(dimension_scores=scores)
        assert result.composite == 6
        assert result.band.name == "low"
        assert result.effective_band.name == "low"
        assert len(result.hard_trigger_classes) == 0

    def test_evaluate_medium_band(self) -> None:
        scores = dict.fromkeys(DIMENSION_NAMES, 1)
        scores["user_customer_impact"] = 2
        scores["data_security_compliance_impact"] = 2
        # total = 2+1+2+1+1+1 = 8
        result = evaluate_significance(dimension_scores=scores)
        assert result.composite == 8
        assert result.band.name == "medium"
        assert result.effective_band.name == "medium"

    def test_evaluate_high_band(self) -> None:
        scores = {name: 2 for name in DIMENSION_NAMES}  # total 12
        result = evaluate_significance(dimension_scores=scores)
        assert result.composite == 12
        assert result.band.name == "high"
        assert result.effective_band.name == "high"

    def test_evaluate_all_zeros(self) -> None:
        scores = {name: 0 for name in DIMENSION_NAMES}
        result = evaluate_significance(dimension_scores=scores)
        assert result.composite == 0
        assert result.band.name == "low"

    def test_evaluate_all_threes(self) -> None:
        scores = {name: 3 for name in DIMENSION_NAMES}
        result = evaluate_significance(dimension_scores=scores)
        assert result.composite == 18
        assert result.band.name == "high"

    def test_dimensions_sorted_deterministically(self) -> None:
        scores = {name: 1 for name in DIMENSION_NAMES}
        result = evaluate_significance(dimension_scores=scores)
        dim_names = [d.name for d in result.dimensions]
        assert dim_names == sorted(dim_names)

    def test_returns_significance_score_type(self) -> None:
        scores = {name: 1 for name in DIMENSION_NAMES}
        result = evaluate_significance(dimension_scores=scores)
        assert isinstance(result, SignificanceScore)

    def test_determinism_identical_inputs(self) -> None:
        """Same inputs produce identical outputs (NFR-003)."""
        scores = {name: 2 for name in DIMENSION_NAMES}
        r1 = evaluate_significance(dimension_scores=scores)
        r2 = evaluate_significance(dimension_scores=scores)
        assert r1 == r2

    def test_no_hard_triggers_effective_equals_band(self) -> None:
        scores = {name: 1 for name in DIMENSION_NAMES}
        result = evaluate_significance(dimension_scores=scores)
        assert result.effective_band == result.band

    def test_exactly_six_dimensions_in_result(self) -> None:
        scores = {name: 1 for name in DIMENSION_NAMES}
        result = evaluate_significance(dimension_scores=scores)
        assert len(result.dimensions) == 6


# ============================================================================
# T029: Hard-Trigger Override Tests
# ============================================================================


class TestHardTriggerOverride:
    """Verify hard-trigger classes force effective_band=high regardless of score."""

    @pytest.mark.parametrize("trigger_id", sorted(HARD_TRIGGER_REGISTRY.keys()))
    def test_hard_trigger_forces_high(self, trigger_id: str) -> None:
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

    def test_multiple_hard_triggers(self) -> None:
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

    def test_all_five_hard_triggers_simultaneously(self) -> None:
        scores = {name: 0 for name in DIMENSION_NAMES}
        all_trigger_ids = sorted(HARD_TRIGGER_REGISTRY.keys())
        result = evaluate_significance(
            dimension_scores=scores,
            hard_trigger_classes=all_trigger_ids,
        )
        assert result.effective_band.name == "high"
        assert len(result.hard_trigger_classes) == 5

    def test_high_score_with_hard_trigger(self) -> None:
        scores = {name: 3 for name in DIMENSION_NAMES}  # total 18 (high)
        result = evaluate_significance(
            dimension_scores=scores,
            hard_trigger_classes=["architecture_foundation"],
        )
        assert result.composite == 18
        assert result.band.name == "high"
        assert result.effective_band.name == "high"
        assert len(result.hard_trigger_classes) == 1  # trigger recorded alongside score

    def test_medium_score_with_hard_trigger(self) -> None:
        scores = _make_scores_for_total(9)  # medium band
        result = evaluate_significance(
            dimension_scores=scores,
            hard_trigger_classes=["billing_financial_commitment"],
        )
        assert result.composite == 9
        assert result.band.name == "medium"
        assert result.effective_band.name == "high"  # overridden

    def test_unknown_hard_trigger_rejected(self) -> None:
        scores = {name: 0 for name in DIMENSION_NAMES}
        with pytest.raises(ValueError, match="Unknown hard-trigger"):
            evaluate_significance(
                dimension_scores=scores,
                hard_trigger_classes=["not_a_real_trigger"],
            )

    def test_empty_hard_triggers_no_override(self) -> None:
        scores = {name: 0 for name in DIMENSION_NAMES}
        result = evaluate_significance(
            dimension_scores=scores,
            hard_trigger_classes=[],
        )
        assert result.effective_band.name == "low"
        assert len(result.hard_trigger_classes) == 0


# ============================================================================
# T030: Boundary Score Tests
# ============================================================================


class TestBoundaryScores:
    """Verify correct routing at exact band transition points."""

    @pytest.mark.parametrize(
        "total,expected_band",
        [
            (0, "low"),
            (6, "low"),       # upper boundary of low
            (7, "medium"),    # lower boundary of medium (US1.4)
            (11, "medium"),   # upper boundary of medium
            (12, "high"),     # lower boundary of high (US1.5)
            (18, "high"),     # maximum possible
        ],
    )
    def test_band_boundaries(self, total: int, expected_band: str) -> None:
        scores = _make_scores_for_total(total)
        result = evaluate_significance(dimension_scores=scores)
        assert result.composite == total
        assert result.band.name == expected_band
        assert result.effective_band.name == expected_band

    def test_boundary_low_to_medium(self) -> None:
        """Score 6 is low, score 7 is medium."""
        low = evaluate_significance(dimension_scores=_make_scores_for_total(6))
        med = evaluate_significance(dimension_scores=_make_scores_for_total(7))
        assert low.band.name == "low"
        assert med.band.name == "medium"

    def test_boundary_medium_to_high(self) -> None:
        """Score 11 is medium, score 12 is high."""
        med = evaluate_significance(dimension_scores=_make_scores_for_total(11))
        high = evaluate_significance(dimension_scores=_make_scores_for_total(12))
        assert med.band.name == "medium"
        assert high.band.name == "high"

    def test_helper_produces_correct_totals(self) -> None:
        """Verify _make_scores_for_total produces expected sums."""
        for total in range(19):  # 0 through 18
            scores = _make_scores_for_total(total)
            assert sum(scores.values()) == total, f"Expected sum {total}"
            assert len(scores) == 6, f"Expected 6 dims for total {total}"
            for v in scores.values():
                assert 0 <= v <= 3, f"Score {v} out of range for total {total}"

    def test_helper_is_deterministic(self) -> None:
        """Same total always produces same scores."""
        for total in range(19):
            s1 = _make_scores_for_total(total)
            s2 = _make_scores_for_total(total)
            assert s1 == s2

    @pytest.mark.parametrize("total", range(19))
    def test_all_totals_produce_valid_band(self, total: int) -> None:
        """Every possible total (0-18) maps to a valid band."""
        scores = _make_scores_for_total(total)
        result = evaluate_significance(dimension_scores=scores)
        assert result.composite == total
        assert result.band.name in ("low", "medium", "high")


# ============================================================================
# T031: Band Cutoff Validation Tests
# ============================================================================


class TestBandCutoffValidation:
    """Verify validate_band_cutoffs accepts valid and rejects invalid configs."""

    def test_default_cutoffs_valid(self) -> None:
        validate_band_cutoffs({"low": [0, 6], "medium": [7, 11], "high": [12, 18]})

    def test_custom_cutoffs_valid(self) -> None:
        validate_band_cutoffs({"low": [0, 5], "medium": [6, 10], "high": [11, 18]})

    def test_cutoffs_overlapping_rejected(self) -> None:
        with pytest.raises(ValueError, match="[Oo]verlap"):
            validate_band_cutoffs(
                {"low": [0, 7], "medium": [7, 11], "high": [12, 18]}
            )

    def test_cutoffs_gap_rejected(self) -> None:
        with pytest.raises(ValueError, match="[Gg]ap"):
            validate_band_cutoffs(
                {"low": [0, 5], "medium": [7, 11], "high": [12, 18]}
            )

    def test_cutoffs_not_starting_at_zero(self) -> None:
        with pytest.raises(ValueError, match="start at 0"):
            validate_band_cutoffs(
                {"low": [1, 6], "medium": [7, 11], "high": [12, 18]}
            )

    def test_cutoffs_not_ending_at_18(self) -> None:
        with pytest.raises(ValueError, match="end at 18"):
            validate_band_cutoffs(
                {"low": [0, 6], "medium": [7, 11], "high": [12, 17]}
            )

    def test_cutoffs_wrong_band_count(self) -> None:
        with pytest.raises(ValueError, match="3 bands"):
            validate_band_cutoffs({"low": [0, 9], "high": [10, 18]})

    def test_evaluate_with_custom_cutoffs(self) -> None:
        scores = {name: 1 for name in DIMENSION_NAMES}  # total 6
        # With custom cutoffs: 6 is in medium band [5-10]
        result = evaluate_significance(
            dimension_scores=scores,
            band_cutoffs={"low": [0, 4], "medium": [5, 10], "high": [11, 18]},
        )
        assert result.band.name == "medium"  # 6 is medium under custom cutoffs

    def test_evaluate_custom_cutoffs_low(self) -> None:
        scores = {name: 0 for name in DIMENSION_NAMES}  # total 0
        result = evaluate_significance(
            dimension_scores=scores,
            band_cutoffs={"low": [0, 4], "medium": [5, 10], "high": [11, 18]},
        )
        assert result.band.name == "low"

    def test_evaluate_custom_cutoffs_high(self) -> None:
        scores = _make_scores_for_total(11)
        result = evaluate_significance(
            dimension_scores=scores,
            band_cutoffs={"low": [0, 4], "medium": [5, 10], "high": [11, 18]},
        )
        assert result.band.name == "high"  # 11 is high under custom cutoffs

    def test_custom_cutoffs_change_routing(self) -> None:
        """Same score routes differently with default vs custom cutoffs."""
        scores = {name: 1 for name in DIMENSION_NAMES}  # total 6

        default_result = evaluate_significance(dimension_scores=scores)
        assert default_result.band.name == "low"  # 6 is low in defaults

        custom_result = evaluate_significance(
            dimension_scores=scores,
            band_cutoffs={"low": [0, 4], "medium": [5, 10], "high": [11, 18]},
        )
        assert custom_result.band.name == "medium"  # 6 is medium in custom

    def test_custom_cutoffs_with_hard_trigger(self) -> None:
        """Hard trigger still overrides even with custom cutoffs."""
        scores = {name: 0 for name in DIMENSION_NAMES}
        result = evaluate_significance(
            dimension_scores=scores,
            hard_trigger_classes=["production_data_destructive"],
            band_cutoffs={"low": [0, 4], "medium": [5, 10], "high": [11, 18]},
        )
        assert result.band.name == "low"
        assert result.effective_band.name == "high"

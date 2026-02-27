"""Tests for WP02: Significance Scoring Engine.

Tests cover:
- T006: SignificanceScore model validation
- T007: evaluate_significance() pure function
- T008: TimeoutPolicy model
- T009: parse_band_cutoffs_from_policy()
- T010: parse_timeout_from_policy()
"""

from __future__ import annotations

import pytest

from spec_kitty_runtime.schema import MissionPolicySnapshot
from spec_kitty_runtime.significance import (
    DEFAULT_BANDS,
    DIMENSION_NAMES,
    HARD_TRIGGER_REGISTRY,
    HardTriggerClass,
    RoutingBand,
    SignificanceDimension,
    SignificanceScore,
    TimeoutPolicy,
    evaluate_significance,
    parse_band_cutoffs_from_policy,
    parse_timeout_from_policy,
)


# ============================================================================
# Helpers
# ============================================================================


def _all_dims(score: int = 1) -> tuple[SignificanceDimension, ...]:
    """Create all 6 dimensions with the same score, sorted by name."""
    return tuple(sorted(
        [SignificanceDimension(name=n, score=score) for n in DIMENSION_NAMES],
        key=lambda d: d.name,
    ))


def _all_scores(score: int = 1) -> dict[str, int]:
    """Create a dimension_scores dict with all 6 dimensions at the same score."""
    return {name: score for name in DIMENSION_NAMES}


def _make_policy(**extras: object) -> MissionPolicySnapshot:
    """Create a MissionPolicySnapshot with given extras."""
    return MissionPolicySnapshot(extras=extras)


# ============================================================================
# T006: SignificanceScore
# ============================================================================


class TestSignificanceScore:
    """Tests for the SignificanceScore frozen model."""

    def test_valid_low_score(self) -> None:
        dims = _all_dims(score=0)
        band = DEFAULT_BANDS[0]  # low
        score = SignificanceScore(
            dimensions=dims,
            composite=0,
            band=band,
            effective_band=band,
        )
        assert score.composite == 0
        assert score.band.name == "low"
        assert score.effective_band.name == "low"
        assert score.hard_trigger_classes == ()

    def test_valid_medium_score(self) -> None:
        # 6 dims at score 1 + some at 2 to get composite 8
        scores = _all_scores(1)
        scores["user_customer_impact"] = 2
        scores["cross_team_blast_radius"] = 2
        dims = tuple(sorted(
            [SignificanceDimension(name=k, score=v) for k, v in scores.items()],
            key=lambda d: d.name,
        ))
        band = DEFAULT_BANDS[1]  # medium
        score = SignificanceScore(
            dimensions=dims,
            composite=8,
            band=band,
            effective_band=band,
        )
        assert score.composite == 8
        assert score.band.name == "medium"

    def test_valid_high_score(self) -> None:
        dims = _all_dims(score=3)
        band = DEFAULT_BANDS[2]  # high
        score = SignificanceScore(
            dimensions=dims,
            composite=18,
            band=band,
            effective_band=band,
        )
        assert score.composite == 18
        assert score.band.name == "high"

    def test_valid_with_hard_triggers(self) -> None:
        dims = _all_dims(score=0)
        low_band = DEFAULT_BANDS[0]
        high_band = DEFAULT_BANDS[2]
        triggers = (HARD_TRIGGER_REGISTRY["production_data_destructive"],)

        score = SignificanceScore(
            dimensions=dims,
            composite=0,
            band=low_band,
            hard_trigger_classes=triggers,
            effective_band=high_band,
        )
        assert score.effective_band.name == "high"
        assert len(score.hard_trigger_classes) == 1

    def test_wrong_composite_rejected(self) -> None:
        dims = _all_dims(score=1)  # sum = 6
        with pytest.raises(ValueError, match="composite.*!=.*sum"):
            SignificanceScore(
                dimensions=dims,
                composite=5,  # Wrong
                band=DEFAULT_BANDS[0],
                effective_band=DEFAULT_BANDS[0],
            )

    def test_missing_dimension_rejected(self) -> None:
        # Only 5 dimensions
        names = sorted(DIMENSION_NAMES)[:5]
        dims = tuple(SignificanceDimension(name=n, score=1) for n in names)
        with pytest.raises(ValueError, match="missing:"):
            SignificanceScore(
                dimensions=dims,
                composite=5,
                band=DEFAULT_BANDS[0],
                effective_band=DEFAULT_BANDS[0],
            )

    def test_duplicate_dimension_rejected(self) -> None:
        # 6 dims but with a duplicate name
        names = sorted(DIMENSION_NAMES)
        dup_names = list(names[:5]) + [names[0]]  # duplicate first
        dims = tuple(SignificanceDimension(name=n, score=1) for n in dup_names)
        with pytest.raises(ValueError, match="missing:"):
            SignificanceScore(
                dimensions=dims,
                composite=6,
                band=DEFAULT_BANDS[0],
                effective_band=DEFAULT_BANDS[0],
            )

    def test_hard_trigger_but_effective_not_high_rejected(self) -> None:
        dims = _all_dims(score=0)
        triggers = (HARD_TRIGGER_REGISTRY["security_privacy_access_control"],)
        with pytest.raises(ValueError, match="effective_band must be 'high'"):
            SignificanceScore(
                dimensions=dims,
                composite=0,
                band=DEFAULT_BANDS[0],
                hard_trigger_classes=triggers,
                effective_band=DEFAULT_BANDS[0],  # low, should be high
            )

    def test_no_triggers_but_effective_differs_from_band_rejected(self) -> None:
        dims = _all_dims(score=0)
        with pytest.raises(ValueError, match="effective_band must equal band"):
            SignificanceScore(
                dimensions=dims,
                composite=0,
                band=DEFAULT_BANDS[0],
                effective_band=DEFAULT_BANDS[2],  # high, but no triggers
            )

    def test_frozen(self) -> None:
        dims = _all_dims(score=1)
        score = SignificanceScore(
            dimensions=dims,
            composite=6,
            band=DEFAULT_BANDS[0],
            effective_band=DEFAULT_BANDS[0],
        )
        with pytest.raises(Exception):
            score.composite = 5  # type: ignore[misc]

    def test_extra_fields_forbidden(self) -> None:
        dims = _all_dims(score=1)
        with pytest.raises(ValueError):
            SignificanceScore(
                dimensions=dims,
                composite=6,
                band=DEFAULT_BANDS[0],
                effective_band=DEFAULT_BANDS[0],
                extra_field="nope",  # type: ignore[call-arg]
            )

    def test_dimensions_are_tuple(self) -> None:
        dims = _all_dims(score=1)
        score = SignificanceScore(
            dimensions=dims,
            composite=6,
            band=DEFAULT_BANDS[0],
            effective_band=DEFAULT_BANDS[0],
        )
        assert isinstance(score.dimensions, tuple)

    def test_hard_trigger_classes_are_tuple(self) -> None:
        dims = _all_dims(score=0)
        triggers = (HARD_TRIGGER_REGISTRY["legal_compliance_regulatory"],)
        score = SignificanceScore(
            dimensions=dims,
            composite=0,
            band=DEFAULT_BANDS[0],
            hard_trigger_classes=triggers,
            effective_band=DEFAULT_BANDS[2],
        )
        assert isinstance(score.hard_trigger_classes, tuple)


# ============================================================================
# T007: evaluate_significance()
# ============================================================================


class TestEvaluateSignificance:
    """Tests for the evaluate_significance pure function."""

    def test_all_zeros_is_low(self) -> None:
        result = evaluate_significance(_all_scores(0))
        assert result.composite == 0
        assert result.band.name == "low"
        assert result.effective_band.name == "low"

    def test_all_ones_is_low(self) -> None:
        result = evaluate_significance(_all_scores(1))
        assert result.composite == 6
        assert result.band.name == "low"

    def test_boundary_6_is_low(self) -> None:
        result = evaluate_significance(_all_scores(1))
        assert result.composite == 6
        assert result.band.name == "low"

    def test_boundary_7_is_medium(self) -> None:
        scores = _all_scores(1)
        scores["user_customer_impact"] = 2  # 1+1+1+1+1+2 = 7
        result = evaluate_significance(scores)
        assert result.composite == 7
        assert result.band.name == "medium"

    def test_boundary_11_is_medium(self) -> None:
        scores = _all_scores(1)
        # 5 dims at 1, 1 dim at 3 doesn't work (=8). Need to get to 11.
        # Set dims to get composite = 11: 2+2+2+2+2+1 = 11
        for name in sorted(DIMENSION_NAMES)[:5]:
            scores[name] = 2
        scores[sorted(DIMENSION_NAMES)[5]] = 1
        result = evaluate_significance(scores)
        assert result.composite == 11
        assert result.band.name == "medium"

    def test_boundary_12_is_high(self) -> None:
        scores = _all_scores(2)  # 6 * 2 = 12
        result = evaluate_significance(scores)
        assert result.composite == 12
        assert result.band.name == "high"

    def test_all_threes_is_high(self) -> None:
        result = evaluate_significance(_all_scores(3))
        assert result.composite == 18
        assert result.band.name == "high"

    def test_hard_trigger_overrides_to_high(self) -> None:
        result = evaluate_significance(
            _all_scores(0),
            hard_trigger_classes=["production_data_destructive"],
        )
        assert result.composite == 0
        assert result.band.name == "low"
        assert result.effective_band.name == "high"
        assert len(result.hard_trigger_classes) == 1

    def test_multiple_hard_triggers(self) -> None:
        result = evaluate_significance(
            _all_scores(0),
            hard_trigger_classes=[
                "production_data_destructive",
                "security_privacy_access_control",
            ],
        )
        assert result.effective_band.name == "high"
        assert len(result.hard_trigger_classes) == 2

    def test_hard_trigger_with_high_score(self) -> None:
        result = evaluate_significance(
            _all_scores(3),
            hard_trigger_classes=["billing_financial_commitment"],
        )
        assert result.composite == 18
        assert result.band.name == "high"
        assert result.effective_band.name == "high"

    def test_no_hard_triggers_effective_equals_band(self) -> None:
        result = evaluate_significance(_all_scores(1))
        assert result.effective_band == result.band

    def test_custom_band_cutoffs(self) -> None:
        cutoffs = {"low": [0, 5], "medium": [6, 10], "high": [11, 18]}
        result = evaluate_significance(_all_scores(1), band_cutoffs=cutoffs)
        assert result.composite == 6
        assert result.band.name == "medium"  # 6 is now medium with custom cutoffs

    def test_determinism_same_inputs(self) -> None:
        """Same inputs must produce identical outputs (NFR-003)."""
        scores = _all_scores(2)
        triggers = ["architecture_foundation"]
        r1 = evaluate_significance(scores, hard_trigger_classes=triggers)
        r2 = evaluate_significance(scores, hard_trigger_classes=triggers)
        assert r1 == r2

    def test_determinism_dimensions_sorted(self) -> None:
        """Dimensions must be in canonical sorted order."""
        result = evaluate_significance(_all_scores(1))
        dim_names = [d.name for d in result.dimensions]
        assert dim_names == sorted(dim_names)

    def test_invalid_dimension_scores_rejected(self) -> None:
        scores = {"bad_name": 1}
        with pytest.raises(ValueError):
            evaluate_significance(scores)

    def test_unknown_hard_trigger_rejected(self) -> None:
        with pytest.raises(ValueError, match="Unknown hard-trigger class"):
            evaluate_significance(_all_scores(0), hard_trigger_classes=["nonexistent"])

    def test_invalid_band_cutoffs_rejected(self) -> None:
        with pytest.raises(ValueError):
            evaluate_significance(
                _all_scores(0),
                band_cutoffs={"low": [0, 5], "medium": [7, 11], "high": [12, 18]},
            )

    def test_empty_hard_triggers_treated_as_none(self) -> None:
        r1 = evaluate_significance(_all_scores(1), hard_trigger_classes=[])
        r2 = evaluate_significance(_all_scores(1), hard_trigger_classes=None)
        assert r1 == r2

    def test_returns_significance_score_type(self) -> None:
        result = evaluate_significance(_all_scores(1))
        assert isinstance(result, SignificanceScore)


# ============================================================================
# T008: TimeoutPolicy
# ============================================================================


class TestTimeoutPolicy:
    """Tests for the TimeoutPolicy frozen model."""

    def test_default_timeout(self) -> None:
        policy = TimeoutPolicy()
        assert policy.default_timeout_seconds == 600
        assert policy.per_decision_timeout_seconds is None
        assert policy.effective_timeout_seconds == 600

    def test_custom_default(self) -> None:
        policy = TimeoutPolicy(default_timeout_seconds=300)
        assert policy.default_timeout_seconds == 300
        assert policy.effective_timeout_seconds == 300

    def test_per_decision_override(self) -> None:
        policy = TimeoutPolicy(per_decision_timeout_seconds=120)
        assert policy.effective_timeout_seconds == 120

    def test_per_decision_overrides_default(self) -> None:
        policy = TimeoutPolicy(
            default_timeout_seconds=600,
            per_decision_timeout_seconds=120,
        )
        assert policy.effective_timeout_seconds == 120

    def test_zero_default_rejected(self) -> None:
        with pytest.raises(ValueError):
            TimeoutPolicy(default_timeout_seconds=0)

    def test_negative_default_rejected(self) -> None:
        with pytest.raises(ValueError):
            TimeoutPolicy(default_timeout_seconds=-1)

    def test_zero_per_decision_rejected(self) -> None:
        with pytest.raises(ValueError, match="per_decision_timeout_seconds must be > 0"):
            TimeoutPolicy(per_decision_timeout_seconds=0)

    def test_negative_per_decision_rejected(self) -> None:
        with pytest.raises(ValueError, match="per_decision_timeout_seconds must be > 0"):
            TimeoutPolicy(per_decision_timeout_seconds=-10)

    def test_frozen(self) -> None:
        policy = TimeoutPolicy()
        with pytest.raises(Exception):
            policy.default_timeout_seconds = 300  # type: ignore[misc]

    def test_extra_fields_forbidden(self) -> None:
        with pytest.raises(ValueError):
            TimeoutPolicy(extra_field="nope")  # type: ignore[call-arg]

    def test_large_timeout_accepted(self) -> None:
        policy = TimeoutPolicy(default_timeout_seconds=86400)
        assert policy.effective_timeout_seconds == 86400

    def test_one_second_timeout(self) -> None:
        policy = TimeoutPolicy(default_timeout_seconds=1)
        assert policy.effective_timeout_seconds == 1


# ============================================================================
# T009: parse_band_cutoffs_from_policy()
# ============================================================================


class TestParseBandCutoffsFromPolicy:
    """Tests for the parse_band_cutoffs_from_policy helper."""

    def test_missing_returns_none(self) -> None:
        policy = _make_policy()
        assert parse_band_cutoffs_from_policy(policy) is None

    def test_valid_cutoffs(self) -> None:
        cutoffs = {"low": [0, 5], "medium": [6, 10], "high": [11, 18]}
        policy = _make_policy(significance_band_cutoffs=cutoffs)
        result = parse_band_cutoffs_from_policy(policy)
        assert result == cutoffs

    def test_default_cutoffs(self) -> None:
        cutoffs = {"low": [0, 6], "medium": [7, 11], "high": [12, 18]}
        policy = _make_policy(significance_band_cutoffs=cutoffs)
        result = parse_band_cutoffs_from_policy(policy)
        assert result == cutoffs

    def test_non_dict_rejected(self) -> None:
        policy = _make_policy(significance_band_cutoffs="not_a_dict")
        with pytest.raises(ValueError, match="must be a dict"):
            parse_band_cutoffs_from_policy(policy)

    def test_non_list_bounds_rejected(self) -> None:
        policy = _make_policy(significance_band_cutoffs={
            "low": (0, 6), "medium": [7, 11], "high": [12, 18]
        })
        with pytest.raises(ValueError, match="cutoff must be"):
            parse_band_cutoffs_from_policy(policy)

    def test_wrong_length_bounds_rejected(self) -> None:
        policy = _make_policy(significance_band_cutoffs={
            "low": [0], "medium": [7, 11], "high": [12, 18]
        })
        with pytest.raises(ValueError, match="cutoff must be"):
            parse_band_cutoffs_from_policy(policy)

    def test_non_integer_bounds_rejected(self) -> None:
        policy = _make_policy(significance_band_cutoffs={
            "low": [0.0, 6.0], "medium": [7, 11], "high": [12, 18]
        })
        with pytest.raises(ValueError, match="must be integers"):
            parse_band_cutoffs_from_policy(policy)

    def test_invalid_band_structure_rejected(self) -> None:
        policy = _make_policy(significance_band_cutoffs={
            "low": [0, 5], "medium": [7, 11], "high": [12, 18]
        })
        with pytest.raises(ValueError, match="Gap between band"):
            parse_band_cutoffs_from_policy(policy)

    def test_none_value_returns_none(self) -> None:
        policy = _make_policy(significance_band_cutoffs=None)
        assert parse_band_cutoffs_from_policy(policy) is None


# ============================================================================
# T010: parse_timeout_from_policy()
# ============================================================================


class TestParseTimeoutFromPolicy:
    """Tests for the parse_timeout_from_policy helper."""

    def test_missing_returns_default(self) -> None:
        policy = _make_policy()
        assert parse_timeout_from_policy(policy) == 600

    def test_valid_timeout(self) -> None:
        policy = _make_policy(significance_default_timeout_seconds=300)
        assert parse_timeout_from_policy(policy) == 300

    def test_non_int_rejected(self) -> None:
        policy = _make_policy(significance_default_timeout_seconds="300")
        with pytest.raises(ValueError, match="must be int"):
            parse_timeout_from_policy(policy)

    def test_float_rejected(self) -> None:
        policy = _make_policy(significance_default_timeout_seconds=300.0)
        with pytest.raises(ValueError, match="must be int"):
            parse_timeout_from_policy(policy)

    def test_zero_rejected(self) -> None:
        policy = _make_policy(significance_default_timeout_seconds=0)
        with pytest.raises(ValueError, match="must be > 0"):
            parse_timeout_from_policy(policy)

    def test_negative_rejected(self) -> None:
        policy = _make_policy(significance_default_timeout_seconds=-100)
        with pytest.raises(ValueError, match="must be > 0"):
            parse_timeout_from_policy(policy)

    def test_none_value_returns_default(self) -> None:
        policy = _make_policy(significance_default_timeout_seconds=None)
        assert parse_timeout_from_policy(policy) == 600

    def test_large_timeout(self) -> None:
        policy = _make_policy(significance_default_timeout_seconds=86400)
        assert parse_timeout_from_policy(policy) == 86400

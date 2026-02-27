"""Tests for WP01: Core Significance Models & Registries.

Tests cover:
- T001: SignificanceDimension model validation
- T002: RoutingBand model and default bands
- T003: HardTriggerClass model and fixed registry
- T004: Band cutoff validation logic
- T005: Constants, helpers, and validate_dimension_scores
"""

from __future__ import annotations

import pytest

from spec_kitty_runtime.significance import (
    DEFAULT_BANDS,
    DIMENSION_NAMES,
    HARD_TRIGGER_REGISTRY,
    HardTriggerClass,
    RoutingBand,
    SignificanceDimension,
    make_routing_bands,
    resolve_hard_triggers,
    validate_band_cutoffs,
    validate_dimension_scores,
)


# ============================================================================
# T001: SignificanceDimension
# ============================================================================


class TestSignificanceDimension:
    """Tests for the SignificanceDimension frozen model."""

    def test_valid_dimension(self) -> None:
        dim = SignificanceDimension(name="user_customer_impact", score=2)
        assert dim.name == "user_customer_impact"
        assert dim.score == 2
        assert dim.description == ""

    def test_valid_dimension_with_description(self) -> None:
        dim = SignificanceDimension(
            name="cross_team_blast_radius",
            score=3,
            description="Affects multiple teams",
        )
        assert dim.description == "Affects multiple teams"

    def test_all_six_dimensions_valid(self) -> None:
        for name in sorted(DIMENSION_NAMES):
            dim = SignificanceDimension(name=name, score=0)
            assert dim.name == name

    def test_score_boundaries(self) -> None:
        for score in (0, 1, 2, 3):
            dim = SignificanceDimension(name="user_customer_impact", score=score)
            assert dim.score == score

    def test_score_too_low(self) -> None:
        with pytest.raises(ValueError):
            SignificanceDimension(name="user_customer_impact", score=-1)

    def test_score_too_high(self) -> None:
        with pytest.raises(ValueError):
            SignificanceDimension(name="user_customer_impact", score=4)

    def test_unknown_dimension_name(self) -> None:
        with pytest.raises(ValueError, match="Unknown dimension name"):
            SignificanceDimension(name="invented_dimension", score=1)

    def test_empty_dimension_name(self) -> None:
        with pytest.raises(ValueError):
            SignificanceDimension(name="", score=1)

    def test_frozen(self) -> None:
        dim = SignificanceDimension(name="user_customer_impact", score=2)
        with pytest.raises(Exception):
            dim.score = 3  # type: ignore[misc]

    def test_extra_fields_forbidden(self) -> None:
        with pytest.raises(ValueError):
            SignificanceDimension(
                name="user_customer_impact", score=1, extra_field="nope"  # type: ignore[call-arg]
            )

    def test_error_message_includes_valid_names(self) -> None:
        with pytest.raises(ValueError, match="Valid dimensions"):
            SignificanceDimension(name="bad_name", score=1)


# ============================================================================
# T002: RoutingBand
# ============================================================================


class TestRoutingBand:
    """Tests for the RoutingBand frozen model."""

    def test_valid_low_band(self) -> None:
        band = RoutingBand(name="low", min_score=0, max_score=6)
        assert band.name == "low"
        assert band.min_score == 0
        assert band.max_score == 6

    def test_valid_medium_band(self) -> None:
        band = RoutingBand(name="medium", min_score=7, max_score=11)
        assert band.name == "medium"

    def test_valid_high_band(self) -> None:
        band = RoutingBand(name="high", min_score=12, max_score=18)
        assert band.name == "high"

    def test_min_greater_than_max_rejected(self) -> None:
        with pytest.raises(ValueError, match="min_score.*>.*max_score"):
            RoutingBand(name="low", min_score=5, max_score=3)

    def test_equal_min_max_allowed(self) -> None:
        band = RoutingBand(name="low", min_score=3, max_score=3)
        assert band.min_score == band.max_score

    def test_invalid_name(self) -> None:
        with pytest.raises(ValueError):
            RoutingBand(name="ultra", min_score=0, max_score=5)  # type: ignore[arg-type]

    def test_score_below_zero(self) -> None:
        with pytest.raises(ValueError):
            RoutingBand(name="low", min_score=-1, max_score=5)

    def test_score_above_18(self) -> None:
        with pytest.raises(ValueError):
            RoutingBand(name="high", min_score=10, max_score=19)

    def test_frozen(self) -> None:
        band = RoutingBand(name="low", min_score=0, max_score=6)
        with pytest.raises(Exception):
            band.min_score = 1  # type: ignore[misc]

    def test_extra_fields_forbidden(self) -> None:
        with pytest.raises(ValueError):
            RoutingBand(name="low", min_score=0, max_score=6, color="red")  # type: ignore[call-arg]


class TestDefaultBands:
    """Tests for the DEFAULT_BANDS constant."""

    def test_three_default_bands(self) -> None:
        assert len(DEFAULT_BANDS) == 3

    def test_default_band_names(self) -> None:
        names = [b.name for b in DEFAULT_BANDS]
        assert names == ["low", "medium", "high"]

    def test_default_low_range(self) -> None:
        assert DEFAULT_BANDS[0].min_score == 0
        assert DEFAULT_BANDS[0].max_score == 6

    def test_default_medium_range(self) -> None:
        assert DEFAULT_BANDS[1].min_score == 7
        assert DEFAULT_BANDS[1].max_score == 11

    def test_default_high_range(self) -> None:
        assert DEFAULT_BANDS[2].min_score == 12
        assert DEFAULT_BANDS[2].max_score == 18

    def test_default_bands_contiguous(self) -> None:
        for i in range(1, len(DEFAULT_BANDS)):
            assert DEFAULT_BANDS[i].min_score == DEFAULT_BANDS[i - 1].max_score + 1

    def test_default_bands_cover_full_range(self) -> None:
        assert DEFAULT_BANDS[0].min_score == 0
        assert DEFAULT_BANDS[-1].max_score == 18


class TestMakeRoutingBands:
    """Tests for the make_routing_bands factory function."""

    def test_none_returns_defaults(self) -> None:
        bands = make_routing_bands(None)
        assert bands is DEFAULT_BANDS

    def test_custom_cutoffs(self) -> None:
        cutoffs = {"low": [0, 5], "medium": [6, 10], "high": [11, 18]}
        bands = make_routing_bands(cutoffs)
        assert len(bands) == 3
        assert bands[0].name == "low"
        assert bands[0].min_score == 0
        assert bands[0].max_score == 5

    def test_invalid_cutoffs_rejected(self) -> None:
        with pytest.raises(ValueError):
            make_routing_bands({"low": [0, 5], "medium": [6, 10]})  # missing high


# ============================================================================
# T003: HardTriggerClass
# ============================================================================


class TestHardTriggerClass:
    """Tests for the HardTriggerClass frozen model."""

    def test_valid_trigger(self) -> None:
        trigger = HardTriggerClass(class_id="test_trigger", description="A test trigger")
        assert trigger.class_id == "test_trigger"
        assert trigger.description == "A test trigger"

    def test_empty_class_id_rejected(self) -> None:
        with pytest.raises(ValueError):
            HardTriggerClass(class_id="", description="Has a description")

    def test_empty_description_rejected(self) -> None:
        with pytest.raises(ValueError):
            HardTriggerClass(class_id="valid_id", description="")

    def test_frozen(self) -> None:
        trigger = HardTriggerClass(class_id="test", description="test desc")
        with pytest.raises(Exception):
            trigger.class_id = "changed"  # type: ignore[misc]

    def test_extra_fields_forbidden(self) -> None:
        with pytest.raises(ValueError):
            HardTriggerClass(class_id="test", description="test", severity="high")  # type: ignore[call-arg]


class TestHardTriggerRegistry:
    """Tests for the HARD_TRIGGER_REGISTRY constant."""

    def test_five_triggers(self) -> None:
        assert len(HARD_TRIGGER_REGISTRY) == 5

    def test_expected_class_ids(self) -> None:
        expected = {
            "production_data_destructive",
            "security_privacy_access_control",
            "legal_compliance_regulatory",
            "billing_financial_commitment",
            "architecture_foundation",
        }
        assert set(HARD_TRIGGER_REGISTRY.keys()) == expected

    def test_class_id_matches_key(self) -> None:
        for key, trigger in HARD_TRIGGER_REGISTRY.items():
            assert trigger.class_id == key

    def test_all_have_descriptions(self) -> None:
        for trigger in HARD_TRIGGER_REGISTRY.values():
            assert len(trigger.description) > 0


class TestResolveHardTriggers:
    """Tests for the resolve_hard_triggers helper."""

    def test_resolve_single(self) -> None:
        result = resolve_hard_triggers(["production_data_destructive"])
        assert len(result) == 1
        assert result[0].class_id == "production_data_destructive"

    def test_resolve_multiple(self) -> None:
        result = resolve_hard_triggers([
            "security_privacy_access_control",
            "legal_compliance_regulatory",
        ])
        assert len(result) == 2

    def test_resolve_all_five(self) -> None:
        all_ids = sorted(HARD_TRIGGER_REGISTRY.keys())
        result = resolve_hard_triggers(all_ids)
        assert len(result) == 5

    def test_resolve_empty_list(self) -> None:
        result = resolve_hard_triggers([])
        assert result == ()

    def test_unknown_class_id(self) -> None:
        with pytest.raises(ValueError, match="Unknown hard-trigger class"):
            resolve_hard_triggers(["nonexistent_trigger"])

    def test_error_includes_valid_ids(self) -> None:
        with pytest.raises(ValueError, match="Valid:"):
            resolve_hard_triggers(["bad_id"])

    def test_returns_tuple(self) -> None:
        result = resolve_hard_triggers(["architecture_foundation"])
        assert isinstance(result, tuple)


# ============================================================================
# T004: Band cutoff validation
# ============================================================================


class TestValidateBandCutoffs:
    """Tests for the validate_band_cutoffs function."""

    def test_valid_default_cutoffs(self) -> None:
        cutoffs = {"low": [0, 6], "medium": [7, 11], "high": [12, 18]}
        validate_band_cutoffs(cutoffs)  # Should not raise

    def test_valid_custom_cutoffs(self) -> None:
        cutoffs = {"low": [0, 5], "medium": [6, 10], "high": [11, 18]}
        validate_band_cutoffs(cutoffs)

    def test_valid_narrow_bands(self) -> None:
        cutoffs = {"low": [0, 0], "medium": [1, 1], "high": [2, 18]}
        validate_band_cutoffs(cutoffs)

    def test_missing_band(self) -> None:
        with pytest.raises(ValueError, match="Expected exactly 3 bands"):
            validate_band_cutoffs({"low": [0, 6], "medium": [7, 18]})

    def test_extra_band(self) -> None:
        with pytest.raises(ValueError, match="Expected exactly 3 bands"):
            validate_band_cutoffs({
                "low": [0, 4], "medium": [5, 10], "high": [11, 18], "ultra": [19, 20]
            })

    def test_wrong_band_names(self) -> None:
        with pytest.raises(ValueError, match="Expected exactly 3 bands"):
            validate_band_cutoffs({"lo": [0, 6], "med": [7, 11], "hi": [12, 18]})

    def test_low_not_starting_at_zero(self) -> None:
        with pytest.raises(ValueError, match="must start at 0"):
            validate_band_cutoffs({"low": [1, 6], "medium": [7, 11], "high": [12, 18]})

    def test_high_not_ending_at_18(self) -> None:
        with pytest.raises(ValueError, match="must end at 18"):
            validate_band_cutoffs({"low": [0, 6], "medium": [7, 11], "high": [12, 17]})

    def test_gap_between_bands(self) -> None:
        with pytest.raises(ValueError, match="Gap between band"):
            validate_band_cutoffs({"low": [0, 5], "medium": [7, 11], "high": [12, 18]})

    def test_overlap_between_bands(self) -> None:
        with pytest.raises(ValueError, match="Overlap between band"):
            validate_band_cutoffs({"low": [0, 7], "medium": [7, 11], "high": [12, 18]})

    def test_min_greater_than_max(self) -> None:
        with pytest.raises(ValueError, match="min_score.*>.*max_score"):
            validate_band_cutoffs({"low": [6, 0], "medium": [7, 11], "high": [12, 18]})

    def test_invalid_pair_format(self) -> None:
        with pytest.raises(ValueError, match="must be a.*min.*max.*pair"):
            validate_band_cutoffs({"low": [0], "medium": [7, 11], "high": [12, 18]})


# ============================================================================
# T005: Constants and validate_dimension_scores
# ============================================================================


class TestDimensionNames:
    """Tests for the DIMENSION_NAMES constant."""

    def test_six_dimensions(self) -> None:
        assert len(DIMENSION_NAMES) == 6

    def test_is_frozenset(self) -> None:
        assert isinstance(DIMENSION_NAMES, frozenset)

    def test_expected_names(self) -> None:
        expected = {
            "user_customer_impact",
            "architectural_system_impact",
            "data_security_compliance_impact",
            "operational_reliability_impact",
            "financial_commercial_impact",
            "cross_team_blast_radius",
        }
        assert DIMENSION_NAMES == expected


class TestValidateDimensionScores:
    """Tests for the validate_dimension_scores helper."""

    def _make_valid_scores(self) -> dict[str, int]:
        return {name: 1 for name in DIMENSION_NAMES}

    def test_valid_scores(self) -> None:
        validate_dimension_scores(self._make_valid_scores())  # Should not raise

    def test_all_zeros(self) -> None:
        scores = {name: 0 for name in DIMENSION_NAMES}
        validate_dimension_scores(scores)

    def test_all_threes(self) -> None:
        scores = {name: 3 for name in DIMENSION_NAMES}
        validate_dimension_scores(scores)

    def test_missing_dimension(self) -> None:
        scores = self._make_valid_scores()
        del scores["user_customer_impact"]
        with pytest.raises(ValueError, match="missing:"):
            validate_dimension_scores(scores)

    def test_extra_dimension(self) -> None:
        scores = self._make_valid_scores()
        scores["invented"] = 1
        with pytest.raises(ValueError, match="unexpected:"):
            validate_dimension_scores(scores)

    def test_score_too_low(self) -> None:
        scores = self._make_valid_scores()
        scores["user_customer_impact"] = -1
        with pytest.raises(ValueError, match="must be 0-3"):
            validate_dimension_scores(scores)

    def test_score_too_high(self) -> None:
        scores = self._make_valid_scores()
        scores["user_customer_impact"] = 4
        with pytest.raises(ValueError, match="must be 0-3"):
            validate_dimension_scores(scores)

    def test_empty_dict(self) -> None:
        with pytest.raises(ValueError, match="missing:"):
            validate_dimension_scores({})

    def test_both_missing_and_extra(self) -> None:
        scores = self._make_valid_scores()
        del scores["user_customer_impact"]
        scores["invented"] = 1
        with pytest.raises(ValueError, match="missing:.*unexpected:"):
            validate_dimension_scores(scores)


# ============================================================================
# Contract alignment: verify values match significance-evaluation.yaml
# ============================================================================


class TestContractAlignment:
    """Verify model values match the significance-evaluation.yaml contract."""

    def test_dimension_names_match_contract(self) -> None:
        contract_names = {
            "user_customer_impact",
            "architectural_system_impact",
            "data_security_compliance_impact",
            "operational_reliability_impact",
            "financial_commercial_impact",
            "cross_team_blast_radius",
        }
        assert DIMENSION_NAMES == contract_names

    def test_hard_trigger_ids_match_contract(self) -> None:
        contract_ids = {
            "production_data_destructive",
            "security_privacy_access_control",
            "legal_compliance_regulatory",
            "billing_financial_commitment",
            "architecture_foundation",
        }
        assert set(HARD_TRIGGER_REGISTRY.keys()) == contract_ids

    def test_band_names_match_contract(self) -> None:
        band_names = {b.name for b in DEFAULT_BANDS}
        assert band_names == {"low", "medium", "high"}

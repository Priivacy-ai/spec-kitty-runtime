"""Core significance models and registries.

Provides foundational frozen Pydantic models for significance scoring:
- SignificanceDimension: atomic unit of significance scoring (one of 6 fixed dimensions)
- RoutingBand: significance tier determining gating behavior (low/medium/high)
- HardTriggerClass: conditions that override numeric scoring and force hard-gate

All models use ConfigDict(frozen=True, extra="forbid").
All registries are fixed in V1 (no custom dimensions or triggers).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


# ---------------------------------------------------------------------------
# Fixed dimension names (V1, C-001)
# ---------------------------------------------------------------------------

DIMENSION_NAMES: frozenset[str] = frozenset({
    "user_customer_impact",
    "architectural_system_impact",
    "data_security_compliance_impact",
    "operational_reliability_impact",
    "financial_commercial_impact",
    "cross_team_blast_radius",
})


# ---------------------------------------------------------------------------
# T001: SignificanceDimension model
# ---------------------------------------------------------------------------

class SignificanceDimension(BaseModel):
    """A single significance dimension with a name and score.

    Represents one of the six fixed impact dimensions. Score must be 0–3.
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(..., min_length=1)
    score: int = Field(..., ge=0, le=3)
    description: str = ""

    @model_validator(mode="after")
    def _validate_dimension(self) -> SignificanceDimension:
        if self.name not in DIMENSION_NAMES:
            raise ValueError(
                f"Unknown dimension name: {self.name!r}. "
                f"Valid dimensions: {sorted(DIMENSION_NAMES)}"
            )
        return self


# ---------------------------------------------------------------------------
# T002: RoutingBand model with default bands
# ---------------------------------------------------------------------------

class RoutingBand(BaseModel):
    """Significance tier determining gating behavior.

    Three bands partition the 0–18 composite score range:
    - low (0–6): auto-proceed, logged
    - medium (7–11): soft gate
    - high (12–18): hard gate
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: Literal["low", "medium", "high"]
    min_score: int = Field(..., ge=0, le=18)
    max_score: int = Field(..., ge=0, le=18)

    @model_validator(mode="after")
    def _validate_range(self) -> RoutingBand:
        if self.min_score > self.max_score:
            raise ValueError(
                f"min_score ({self.min_score}) > max_score ({self.max_score})"
            )
        return self


DEFAULT_BANDS: tuple[RoutingBand, ...] = (
    RoutingBand(name="low", min_score=0, max_score=6),
    RoutingBand(name="medium", min_score=7, max_score=11),
    RoutingBand(name="high", min_score=12, max_score=18),
)


# ---------------------------------------------------------------------------
# T004: Band cutoff validation logic
# ---------------------------------------------------------------------------

def validate_band_cutoffs(cutoffs: dict[str, list[int]]) -> None:
    """Validate custom band cutoffs for contiguous, non-overlapping coverage of 0–18.

    Args:
        cutoffs: Mapping of band name to [min, max] pair.
            Example: {"low": [0, 5], "medium": [6, 10], "high": [11, 18]}

    Raises:
        ValueError: If validation fails with a specific error message.
    """
    expected_keys = {"low", "medium", "high"}
    provided_keys = set(cutoffs.keys())

    if provided_keys != expected_keys:
        raise ValueError(
            f"Expected exactly 3 bands (low, medium, high), got: {sorted(provided_keys)}"
        )

    for band_name, pair in cutoffs.items():
        if not isinstance(pair, list) or len(pair) != 2:
            raise ValueError(
                f"Band '{band_name}' must be a [min, max] pair, got: {pair!r}"
            )

    # Sort bands by min_score for contiguity checks
    sorted_bands = sorted(cutoffs.items(), key=lambda item: item[1][0])

    for band_name, (lo, hi) in sorted_bands:
        if lo > hi:
            raise ValueError(
                f"Band '{band_name}': min_score ({lo}) > max_score ({hi})"
            )

    # Check boundaries
    first_name, (first_lo, _) = sorted_bands[0]
    if first_lo != 0:
        raise ValueError(
            f"Band '{first_name}' must start at 0, starts at {first_lo}"
        )

    last_name, (_, last_hi) = sorted_bands[-1]
    if last_hi != 18:
        raise ValueError(
            f"Band '{last_name}' must end at 18, ends at {last_hi}"
        )

    # Check contiguity and no overlaps
    for i in range(1, len(sorted_bands)):
        prev_name, (_, prev_hi) = sorted_bands[i - 1]
        next_name, (next_lo, _) = sorted_bands[i]

        if next_lo > prev_hi + 1:
            raise ValueError(
                f"Gap between band '{prev_name}' (max={prev_hi}) "
                f"and '{next_name}' (min={next_lo})"
            )
        if next_lo <= prev_hi:
            raise ValueError(
                f"Overlap between band '{prev_name}' (max={prev_hi}) "
                f"and '{next_name}' (min={next_lo})"
            )


def make_routing_bands(
    cutoffs: dict[str, list[int]] | None = None,
) -> tuple[RoutingBand, ...]:
    """Create routing bands from custom cutoffs or return defaults.

    Args:
        cutoffs: Optional dict mapping band names to [min, max] pairs.
            If None, returns DEFAULT_BANDS.

    Returns:
        Tuple of RoutingBand instances sorted by min_score.

    Raises:
        ValueError: If cutoffs are invalid.
    """
    if cutoffs is None:
        return DEFAULT_BANDS

    validate_band_cutoffs(cutoffs)

    bands = []
    for name in ("low", "medium", "high"):
        lo, hi = cutoffs[name]
        bands.append(RoutingBand(name=name, min_score=lo, max_score=hi))  # type: ignore[arg-type]

    return tuple(sorted(bands, key=lambda b: b.min_score))


# ---------------------------------------------------------------------------
# T003: HardTriggerClass model with fixed registry
# ---------------------------------------------------------------------------

class HardTriggerClass(BaseModel):
    """A predefined condition that overrides numeric scoring and forces hard-gate.

    V1 defines exactly five fixed hard-trigger classes (C-003).
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    class_id: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)


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


def resolve_hard_triggers(class_ids: list[str]) -> tuple[HardTriggerClass, ...]:
    """Resolve hard-trigger class IDs to HardTriggerClass instances.

    Args:
        class_ids: List of hard-trigger class ID strings.

    Returns:
        Tuple of resolved HardTriggerClass instances.

    Raises:
        ValueError: For unknown class_ids.
    """
    resolved = []
    for cid in class_ids:
        if cid not in HARD_TRIGGER_REGISTRY:
            raise ValueError(
                f"Unknown hard-trigger class: {cid!r}. "
                f"Valid: {sorted(HARD_TRIGGER_REGISTRY.keys())}"
            )
        resolved.append(HARD_TRIGGER_REGISTRY[cid])
    return tuple(resolved)


# ---------------------------------------------------------------------------
# T005: Validation helpers and exports
# ---------------------------------------------------------------------------

def validate_dimension_scores(scores: dict[str, int]) -> None:
    """Validate that dimension scores contain exactly the 6 required dimensions, each scored 0–3.

    Args:
        scores: Mapping of dimension name to score (0–3).

    Raises:
        ValueError: If dimensions are missing/extra or scores are out of range.
    """
    provided = set(scores.keys())
    if provided != DIMENSION_NAMES:
        missing = DIMENSION_NAMES - provided
        extra = provided - DIMENSION_NAMES
        parts = []
        if missing:
            parts.append(f"missing: {sorted(missing)}")
        if extra:
            parts.append(f"unexpected: {sorted(extra)}")
        raise ValueError(
            f"Dimension scores must contain exactly {len(DIMENSION_NAMES)} dimensions. "
            f"{', '.join(parts)}"
        )
    for name, score in scores.items():
        if not (0 <= score <= 3):
            raise ValueError(f"Dimension '{name}' score must be 0-3, got {score}")


__all__ = [
    # Constants
    "DIMENSION_NAMES",
    "DEFAULT_BANDS",
    "HARD_TRIGGER_REGISTRY",
    # Models
    "SignificanceDimension",
    "RoutingBand",
    "HardTriggerClass",
    # Functions
    "make_routing_bands",
    "validate_band_cutoffs",
    "resolve_hard_triggers",
    "validate_dimension_scores",
]

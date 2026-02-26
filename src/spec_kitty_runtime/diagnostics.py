"""Compatibility diagnostics API for mission template validation.

Host repos import ``validate_mission_template_compatibility`` to check their
mission YAML files against the 2.x schema without starting a mission run.
The function never raises — it always returns a ``CompatibilityReport``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict


class CompatibilityIssue(BaseModel):
    """A single compatibility issue found during validation."""

    model_config = ConfigDict(frozen=True)

    code: str
    field: str
    message: str
    severity: Literal["error", "warning"]


class CompatibilityReport(BaseModel):
    """Result of running compatibility diagnostics on a mission template."""

    model_config = ConfigDict(frozen=True)

    path: str
    is_compatible: bool
    schema_valid: bool
    audit_steps_valid: bool
    issues: list[CompatibilityIssue]
    warnings: list[str]


_VALID_TRIGGER_MODES = frozenset({"manual", "post_merge", "both"})
_VALID_ENFORCEMENTS = frozenset({"advisory", "blocking"})


def validate_mission_template_compatibility(path: Path | str) -> CompatibilityReport:
    """Validate a mission template YAML file for 2.x compatibility.

    Runs 9 checks in order:
    1. YAML parses without error
    2. ``mission`` block has required ``key``, ``name``, ``version``
    3. At least one of ``steps`` or ``audit_steps`` is non-empty
    4. Each ``audit_steps`` entry has ``id`` and ``title``
    5. Each ``audit_steps`` entry has an ``audit`` block
    6. ``audit.trigger_mode`` is one of ``manual | post_merge | both``
    7. ``audit.enforcement`` is one of ``advisory | blocking``
    8. ``depends_on`` references resolve to known ``step`` or ``audit_step`` IDs
    9. No duplicate step IDs across ``steps`` and ``audit_steps``

    Never raises — all exceptions are caught and converted to issues.

    Args:
        path: Path to the YAML file (``Path`` or ``str``).

    Returns:
        A ``CompatibilityReport`` describing the validation outcome.
    """
    path_str = str(path)
    issues: list[CompatibilityIssue] = []
    warnings: list[str] = []
    schema_valid = True
    audit_steps_valid = True

    # Check 1: YAML parses without error
    try:
        raw = Path(path).read_text(encoding="utf-8")
        data: Any = yaml.safe_load(raw)
        if not isinstance(data, dict):
            issues.append(CompatibilityIssue(
                code="YAML_PARSE_ERROR",
                field="<root>",
                message="YAML root must be a mapping",
                severity="error",
            ))
            schema_valid = False
            return _build_report(path_str, schema_valid, audit_steps_valid, issues, warnings)
    except Exception as exc:
        issues.append(CompatibilityIssue(
            code="YAML_PARSE_ERROR",
            field="<root>",
            message=f"YAML parse failed: {exc}",
            severity="error",
        ))
        schema_valid = False
        return _build_report(path_str, schema_valid, audit_steps_valid, issues, warnings)

    # Check 2: mission block has required key, name, version
    mission_block = data.get("mission")
    if not isinstance(mission_block, dict) or not all(
        mission_block.get(k) for k in ("key", "name", "version")
    ):
        issues.append(CompatibilityIssue(
            code="MISSING_MISSION_META",
            field="mission",
            message="mission block must have non-empty 'key', 'name', and 'version' fields",
            severity="error",
        ))
        schema_valid = False

    # Collect all steps and audit_steps
    steps: list[dict] = data.get("steps") or []
    audit_steps: list[dict] = data.get("audit_steps") or []

    # Ensure lists of dicts
    if not isinstance(steps, list):
        steps = []
    if not isinstance(audit_steps, list):
        audit_steps = []

    steps = [s for s in steps if isinstance(s, dict)]
    audit_steps = [s for s in audit_steps if isinstance(s, dict)]

    # Check 3: at least one of steps or audit_steps is non-empty
    if not steps and not audit_steps:
        issues.append(CompatibilityIssue(
            code="NO_STEPS_DEFINED",
            field="steps",
            message="Mission must define at least one step in 'steps' or 'audit_steps'",
            severity="error",
        ))
        audit_steps_valid = False

    # Build set of all known IDs for dependency resolution
    all_step_ids: set[str] = set()
    for step in steps:
        sid = step.get("id")
        if sid:
            all_step_ids.add(str(sid))
    audit_step_ids: set[str] = set()
    for step in audit_steps:
        sid = step.get("id")
        if sid:
            audit_step_ids.add(str(sid))
    all_known_ids = all_step_ids | audit_step_ids

    # Check 9: no duplicate step IDs across steps and audit_steps
    seen_ids: set[str] = set()
    duplicate_ids: set[str] = set()
    for step in steps + audit_steps:
        sid = step.get("id")
        if sid:
            sid_str = str(sid)
            if sid_str in seen_ids:
                duplicate_ids.add(sid_str)
            seen_ids.add(sid_str)
    for dup_id in sorted(duplicate_ids):
        issues.append(CompatibilityIssue(
            code="DUPLICATE_STEP_ID",
            field="steps",
            message=f"Duplicate step ID '{dup_id}' found across steps and audit_steps",
            severity="error",
        ))

    # Checks 4–8: validate each audit_step entry
    for i, audit_step in enumerate(audit_steps):
        # Check 4: each audit_steps entry has id and title
        if not audit_step.get("id") or not audit_step.get("title"):
            issues.append(CompatibilityIssue(
                code="MISSING_STEP_FIELDS",
                field=f"audit_steps[{i}]",
                message=f"audit_steps[{i}] must have non-empty 'id' and 'title' fields",
                severity="error",
            ))

        # Check 5: each audit_steps entry has an audit block
        audit_block = audit_step.get("audit")
        if not isinstance(audit_block, dict):
            issues.append(CompatibilityIssue(
                code="MISSING_AUDIT_CONFIG",
                field=f"audit_steps[{i}].audit",
                message=f"audit_steps[{i}] must have an 'audit' configuration block",
                severity="error",
            ))
        else:
            # Check 6: trigger_mode is valid
            trigger_mode = audit_block.get("trigger_mode")
            if trigger_mode not in _VALID_TRIGGER_MODES:
                issues.append(CompatibilityIssue(
                    code="UNKNOWN_TRIGGER_MODE",
                    field=f"audit_steps[{i}].audit.trigger_mode",
                    message=(
                        f"audit_steps[{i}].audit.trigger_mode '{trigger_mode}' is not valid; "
                        f"must be one of: {', '.join(sorted(_VALID_TRIGGER_MODES))}"
                    ),
                    severity="error",
                ))

            # Check 7: enforcement is valid
            enforcement = audit_block.get("enforcement")
            if enforcement not in _VALID_ENFORCEMENTS:
                issues.append(CompatibilityIssue(
                    code="UNKNOWN_ENFORCEMENT",
                    field=f"audit_steps[{i}].audit.enforcement",
                    message=(
                        f"audit_steps[{i}].audit.enforcement '{enforcement}' is not valid; "
                        f"must be one of: {', '.join(sorted(_VALID_ENFORCEMENTS))}"
                    ),
                    severity="error",
                ))

        # Check 8: depends_on references resolve to known IDs
        depends_on = audit_step.get("depends_on") or []
        if not isinstance(depends_on, list):
            depends_on = [depends_on]
        for dep in depends_on:
            dep_str = str(dep)
            if dep_str not in all_known_ids:
                issues.append(CompatibilityIssue(
                    code="UNRESOLVED_DEPENDENCY",
                    field=f"audit_steps[{i}].depends_on",
                    message=(
                        f"audit_steps[{i}].depends_on references unknown ID '{dep_str}'"
                    ),
                    severity="error",
                ))

    return _build_report(path_str, schema_valid, audit_steps_valid, issues, warnings)


def _build_report(
    path_str: str,
    schema_valid: bool,
    audit_steps_valid: bool,
    issues: list[CompatibilityIssue],
    warnings: list[str],
) -> CompatibilityReport:
    is_compatible = len(issues) == 0
    return CompatibilityReport(
        path=path_str,
        is_compatible=is_compatible,
        schema_valid=schema_valid,
        audit_steps_valid=audit_steps_valid,
        issues=issues,
        warnings=warnings,
    )

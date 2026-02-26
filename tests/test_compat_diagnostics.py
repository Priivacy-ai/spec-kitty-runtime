"""Tests for the compatibility diagnostics API (WP04).

Covers all AC-8 acceptance criteria: valid fixtures, invalid fixtures, report
structure guarantees, and the never-raise contract.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from spec_kitty_runtime.diagnostics import (
    CompatibilityIssue,
    CompatibilityReport,
    validate_mission_template_compatibility,
)

FIXTURES = Path(__file__).parent / "fixtures"


class TestValidFixtures:
    """AC-8: Valid fixtures must produce is_compatible=True with no issues."""

    def test_valid_blocking_is_compatible(self):
        report = validate_mission_template_compatibility(FIXTURES / "audit_valid_blocking.yaml")
        assert report.is_compatible is True
        assert report.schema_valid is True
        assert report.audit_steps_valid is True
        assert report.issues == []

    def test_valid_advisory_is_compatible(self):
        report = validate_mission_template_compatibility(FIXTURES / "audit_valid_advisory.yaml")
        assert report.is_compatible is True
        assert report.schema_valid is True
        assert report.audit_steps_valid is True
        assert report.issues == []

    def test_mixed_steps_is_compatible(self):
        report = validate_mission_template_compatibility(FIXTURES / "audit_mixed_steps.yaml")
        assert report.is_compatible is True
        assert report.schema_valid is True
        assert report.audit_steps_valid is True
        assert report.issues == []

    def test_audit_only_is_compatible(self):
        report = validate_mission_template_compatibility(FIXTURES / "audit_only_steps.yaml")
        assert report.is_compatible is True
        assert report.schema_valid is True
        assert report.audit_steps_valid is True
        assert report.issues == []


class TestInvalidFixtures:
    """AC-8: Invalid fixtures must produce is_compatible=False with expected issue codes."""

    def test_invalid_trigger_mode(self):
        report = validate_mission_template_compatibility(FIXTURES / "audit_invalid_trigger.yaml")
        assert report.is_compatible is False
        codes = [issue.code for issue in report.issues]
        assert "UNKNOWN_TRIGGER_MODE" in codes

    def test_missing_audit_config(self):
        report = validate_mission_template_compatibility(FIXTURES / "audit_missing_config.yaml")
        assert report.is_compatible is False
        codes = [issue.code for issue in report.issues]
        assert "MISSING_AUDIT_CONFIG" in codes

    def test_bad_dependency(self):
        report = validate_mission_template_compatibility(FIXTURES / "audit_bad_dependency.yaml")
        assert report.is_compatible is False
        codes = [issue.code for issue in report.issues]
        assert "UNRESOLVED_DEPENDENCY" in codes


class TestReportStructure:
    """Validate structural guarantees of CompatibilityReport."""

    def test_returns_compatibility_report_type(self):
        report = validate_mission_template_compatibility(FIXTURES / "audit_valid_blocking.yaml")
        assert isinstance(report, CompatibilityReport)

    def test_never_raises_on_nonexistent_file(self):
        report = validate_mission_template_compatibility("/tmp/does_not_exist_WP04_test.yaml")
        assert isinstance(report, CompatibilityReport)
        assert report.is_compatible is False
        codes = [issue.code for issue in report.issues]
        assert "YAML_PARSE_ERROR" in codes

    def test_never_raises_on_invalid_yaml(self, tmp_path):
        bad_yaml = tmp_path / "bad.yaml"
        bad_yaml.write_text("key: [\nunclosed bracket", encoding="utf-8")
        report = validate_mission_template_compatibility(bad_yaml)
        assert isinstance(report, CompatibilityReport)
        assert report.is_compatible is False
        codes = [issue.code for issue in report.issues]
        assert "YAML_PARSE_ERROR" in codes

    def test_issue_field_uses_dot_notation(self):
        report = validate_mission_template_compatibility(FIXTURES / "audit_invalid_trigger.yaml")
        trigger_issues = [i for i in report.issues if i.code == "UNKNOWN_TRIGGER_MODE"]
        assert trigger_issues, "Expected at least one UNKNOWN_TRIGGER_MODE issue"
        issue = trigger_issues[0]
        # Field must use dot notation like audit_steps[0].audit.trigger_mode
        assert "[" in issue.field or "." in issue.field, (
            f"Expected dot notation in field '{issue.field}'"
        )
        assert "trigger_mode" in issue.field

    def test_path_field_in_report(self):
        fixture_path = FIXTURES / "audit_valid_blocking.yaml"
        report = validate_mission_template_compatibility(fixture_path)
        assert report.path == str(fixture_path)

    def test_path_field_in_report_string_input(self):
        fixture_path = str(FIXTURES / "audit_valid_blocking.yaml")
        report = validate_mission_template_compatibility(fixture_path)
        assert report.path == fixture_path

    def test_report_is_frozen(self):
        report = validate_mission_template_compatibility(FIXTURES / "audit_valid_blocking.yaml")
        with pytest.raises(Exception):
            report.is_compatible = False  # type: ignore[misc]

    def test_issue_is_frozen(self):
        report = validate_mission_template_compatibility(FIXTURES / "audit_invalid_trigger.yaml")
        assert report.issues
        with pytest.raises(Exception):
            report.issues[0].code = "CHANGED"  # type: ignore[misc]


class TestIssueCodesExhaustive:
    """Verify individual issue codes can be triggered."""

    def test_yaml_parse_error_on_bad_content(self, tmp_path):
        f = tmp_path / "broken.yaml"
        f.write_text(": invalid: yaml: [\n", encoding="utf-8")
        report = validate_mission_template_compatibility(f)
        codes = [i.code for i in report.issues]
        assert "YAML_PARSE_ERROR" in codes

    def test_missing_mission_meta(self, tmp_path):
        f = tmp_path / "no_mission.yaml"
        f.write_text(textwrap.dedent("""\
            steps:
              - id: step-01
                title: A step
        """), encoding="utf-8")
        report = validate_mission_template_compatibility(f)
        codes = [i.code for i in report.issues]
        assert "MISSING_MISSION_META" in codes

    def test_no_steps_defined(self, tmp_path):
        f = tmp_path / "no_steps.yaml"
        f.write_text(textwrap.dedent("""\
            mission:
              key: empty
              name: Empty Mission
              version: "1.0.0"
        """), encoding="utf-8")
        report = validate_mission_template_compatibility(f)
        codes = [i.code for i in report.issues]
        assert "NO_STEPS_DEFINED" in codes

    def test_missing_step_fields(self, tmp_path):
        f = tmp_path / "missing_fields.yaml"
        f.write_text(textwrap.dedent("""\
            mission:
              key: test
              name: Test
              version: "1.0.0"
            audit_steps:
              - title: No ID here
                audit:
                  trigger_mode: manual
                  enforcement: advisory
        """), encoding="utf-8")
        report = validate_mission_template_compatibility(f)
        codes = [i.code for i in report.issues]
        assert "MISSING_STEP_FIELDS" in codes

    def test_unknown_enforcement(self, tmp_path):
        f = tmp_path / "bad_enforcement.yaml"
        f.write_text(textwrap.dedent("""\
            mission:
              key: test
              name: Test
              version: "1.0.0"
            audit_steps:
              - id: audit-01
                title: Bad enforcement
                audit:
                  trigger_mode: manual
                  enforcement: strict
        """), encoding="utf-8")
        report = validate_mission_template_compatibility(f)
        codes = [i.code for i in report.issues]
        assert "UNKNOWN_ENFORCEMENT" in codes

    def test_duplicate_step_id(self, tmp_path):
        f = tmp_path / "duplicate.yaml"
        f.write_text(textwrap.dedent("""\
            mission:
              key: test
              name: Test
              version: "1.0.0"
            steps:
              - id: step-01
                title: Step one
            audit_steps:
              - id: step-01
                title: Duplicate ID
                audit:
                  trigger_mode: manual
                  enforcement: advisory
        """), encoding="utf-8")
        report = validate_mission_template_compatibility(f)
        codes = [i.code for i in report.issues]
        assert "DUPLICATE_STEP_ID" in codes

    def test_issue_severity_is_error_for_failures(self):
        report = validate_mission_template_compatibility(FIXTURES / "audit_invalid_trigger.yaml")
        for issue in report.issues:
            assert issue.severity == "error"

    def test_compatible_report_has_empty_issues(self):
        report = validate_mission_template_compatibility(FIXTURES / "audit_valid_blocking.yaml")
        assert report.issues == []
        assert report.warnings == []

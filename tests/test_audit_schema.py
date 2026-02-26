"""Tests for AuditConfig, AuditStep, and MissionTemplate audit_steps (WP01)."""
import textwrap

import pytest
from pydantic import ValidationError

from spec_kitty_runtime.schema import (
    AuditConfig,
    AuditStep,
    MissionRuntimeError,
    MissionTemplate,
    load_mission_template_file,
)


class TestAuditConfig:
    def test_valid_manual_blocking(self):
        cfg = AuditConfig(trigger_mode="manual", enforcement="blocking")
        assert cfg.trigger_mode == "manual"
        assert cfg.enforcement == "blocking"

    def test_valid_post_merge_advisory(self):
        cfg = AuditConfig(trigger_mode="post_merge", enforcement="advisory")
        assert cfg.trigger_mode == "post_merge"
        assert cfg.enforcement == "advisory"

    def test_valid_both_trigger_mode(self):
        cfg = AuditConfig(trigger_mode="both", enforcement="blocking")
        assert cfg.trigger_mode == "both"

    def test_invalid_trigger_mode(self):
        with pytest.raises(ValidationError):
            AuditConfig(trigger_mode="invalid", enforcement="blocking")

    def test_invalid_enforcement(self):
        with pytest.raises(ValidationError):
            AuditConfig(trigger_mode="manual", enforcement="invalid")

    def test_trigger_mode_required(self):
        with pytest.raises(ValidationError):
            AuditConfig(enforcement="blocking")  # type: ignore[call-arg]

    def test_enforcement_required(self):
        with pytest.raises(ValidationError):
            AuditConfig(trigger_mode="manual")  # type: ignore[call-arg]

    def test_extra_fields_forbidden(self):
        with pytest.raises(ValidationError):
            AuditConfig(trigger_mode="manual", enforcement="blocking", unknown_field="x")

    def test_optional_label(self):
        cfg = AuditConfig(trigger_mode="manual", enforcement="blocking", label="My Label")
        assert cfg.label == "My Label"

    def test_optional_label_none_by_default(self):
        cfg = AuditConfig(trigger_mode="manual", enforcement="blocking")
        assert cfg.label is None

    def test_optional_metadata(self):
        cfg = AuditConfig(
            trigger_mode="manual",
            enforcement="blocking",
            metadata={"severity": "high", "owner": "team-a"},
        )
        assert cfg.metadata == {"severity": "high", "owner": "team-a"}

    def test_optional_metadata_none_by_default(self):
        cfg = AuditConfig(trigger_mode="manual", enforcement="blocking")
        assert cfg.metadata is None

    def test_frozen(self):
        cfg = AuditConfig(trigger_mode="manual", enforcement="blocking")
        with pytest.raises(Exception):
            cfg.trigger_mode = "both"  # type: ignore[misc]


class TestAuditStep:
    def test_valid_audit_step(self):
        step = AuditStep(
            id="audit-01",
            title="Post-merge policy check",
            audit=AuditConfig(trigger_mode="post_merge", enforcement="blocking"),
        )
        assert step.id == "audit-01"
        assert step.title == "Post-merge policy check"
        assert step.description == ""
        assert step.depends_on == []

    def test_missing_audit_field_raises(self):
        with pytest.raises(ValidationError):
            AuditStep(id="audit-01", title="Check")  # type: ignore[call-arg]

    def test_no_prompt_field(self):
        step = AuditStep(
            id="audit-01",
            title="Check",
            audit=AuditConfig(trigger_mode="manual", enforcement="advisory"),
        )
        assert not hasattr(step, "prompt")
        assert not hasattr(step, "prompt_template")
        assert not hasattr(step, "requires_inputs")

    def test_depends_on_default_empty(self):
        step = AuditStep(
            id="audit-01",
            title="Check",
            audit=AuditConfig(trigger_mode="manual", enforcement="advisory"),
        )
        assert step.depends_on == []

    def test_depends_on_with_values(self):
        step = AuditStep(
            id="audit-02",
            title="Check after step-01",
            audit=AuditConfig(trigger_mode="manual", enforcement="blocking"),
            depends_on=["audit-01"],
        )
        assert step.depends_on == ["audit-01"]

    def test_description_field(self):
        step = AuditStep(
            id="audit-01",
            title="Check",
            description="Detailed description here",
            audit=AuditConfig(trigger_mode="manual", enforcement="blocking"),
        )
        assert step.description == "Detailed description here"


class TestMissionTemplateWithAuditSteps:
    def test_load_with_audit_steps(self, tmp_path):
        yaml_content = textwrap.dedent("""\
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
        """)
        mission_file = tmp_path / "mission.yaml"
        mission_file.write_text(yaml_content)

        template = load_mission_template_file(mission_file)
        assert template.mission.key == "test-audit-mission"
        assert len(template.steps) == 1
        assert len(template.audit_steps) == 1
        assert template.audit_steps[0].id == "audit-01"
        assert template.audit_steps[0].audit.trigger_mode == "post_merge"
        assert template.audit_steps[0].audit.enforcement == "blocking"

    def test_load_audit_steps_only(self, tmp_path):
        yaml_content = textwrap.dedent("""\
            mission:
              key: audit-only-mission
              name: Audit Only Mission
              version: "1.0.0"
            audit_steps:
              - id: audit-01
                title: Advisory check
                audit:
                  trigger_mode: both
                  enforcement: advisory
        """)
        mission_file = tmp_path / "mission.yaml"
        mission_file.write_text(yaml_content)

        template = load_mission_template_file(mission_file)
        assert template.steps == []
        assert len(template.audit_steps) == 1
        assert template.audit_steps[0].id == "audit-01"

    def test_load_neither_raises(self, tmp_path):
        yaml_content = textwrap.dedent("""\
            mission:
              key: empty-mission
              name: Empty Mission
              version: "1.0.0"
        """)
        mission_file = tmp_path / "mission.yaml"
        mission_file.write_text(yaml_content)

        with pytest.raises(MissionRuntimeError, match="no steps"):
            load_mission_template_file(mission_file)

    def test_load_both_empty_raises(self, tmp_path):
        yaml_content = textwrap.dedent("""\
            mission:
              key: empty-mission
              name: Empty Mission
              version: "1.0.0"
            steps: []
            audit_steps: []
        """)
        mission_file = tmp_path / "mission.yaml"
        mission_file.write_text(yaml_content)

        with pytest.raises(MissionRuntimeError, match="no steps"):
            load_mission_template_file(mission_file)

    def test_audit_step_unknown_field_in_audit_block_fails(self, tmp_path):
        yaml_content = textwrap.dedent("""\
            mission:
              key: bad-audit
              name: Bad Audit
              version: "1.0.0"
            audit_steps:
              - id: audit-01
                title: Bad check
                audit:
                  trigger_mode: manual
                  enforcement: blocking
                  unknown_extra_field: should_fail
        """)
        mission_file = tmp_path / "mission.yaml"
        mission_file.write_text(yaml_content)

        with pytest.raises(Exception):
            load_mission_template_file(mission_file)

    def test_mission_template_audit_steps_default_empty(self):
        from spec_kitty_runtime.schema import MissionMeta
        template = MissionTemplate(
            mission=MissionMeta(key="k", name="n", version="1.0.0"),
            steps=[],
            audit_steps=[],
        )
        assert template.audit_steps == []

    def test_audit_config_with_label_and_metadata_from_yaml(self, tmp_path):
        yaml_content = textwrap.dedent("""\
            mission:
              key: labeled-audit
              name: Labeled Audit Mission
              version: "1.0.0"
            audit_steps:
              - id: audit-01
                title: Labeled check
                description: A check with full config
                audit:
                  trigger_mode: manual
                  enforcement: advisory
                  label: compliance-gate
                  metadata:
                    severity: low
                    team: platform
                depends_on: []
        """)
        mission_file = tmp_path / "mission.yaml"
        mission_file.write_text(yaml_content)

        template = load_mission_template_file(mission_file)
        step = template.audit_steps[0]
        assert step.description == "A check with full config"
        assert step.audit.label == "compliance-gate"
        assert step.audit.metadata == {"severity": "low", "team": "platform"}

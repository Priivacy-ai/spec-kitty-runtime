"""Comprehensive test suite for WP06: RACI Inference and Override.

Tests cover:
- Schema validation edge cases (AC-1)
- YAML loading with/without RACI blocks (AC-2)
- Inference rule correctness (AC-3, AC-4, AC-5)
- Explicit override precedence (AC-6)
- Escalation scenarios (AC-7)
- Authority kernel integration (AC-8, AC-9)
- Template compatibility diagnostics (AC-10)
- Determinism (AC-11)
- Backward compatibility (AC-12)
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from spec_kitty_runtime.schema import (
    AuditConfig,
    AuditStep,
    MissionPolicySnapshot,
    MissionRuntimeError,
    MissionTemplate,
    PromptStep,
    RACIAssignment,
    RACIEscalationPayload,
    RACIRoleBinding,
    ResolvedRACIBinding,
    load_mission_template_file,
)
from spec_kitty_runtime.raci import (
    infer_raci,
    resolve_raci,
    validate_raci_assignment,
)
from spec_kitty_runtime.diagnostics import validate_mission_template_compatibility

FIXTURES = Path(__file__).parent / "fixtures"


# ============================================================================
# AC-1: Schema validation
# ============================================================================


class TestRACISchemaValidation:
    """Schema validation passes for valid configs and fails for invalid ones."""

    def test_valid_role_binding_human(self):
        b = RACIRoleBinding(actor_type="human", actor_id="user1")
        assert b.actor_type == "human"
        assert b.actor_id == "user1"

    def test_valid_role_binding_llm_no_id(self):
        b = RACIRoleBinding(actor_type="llm")
        assert b.actor_type == "llm"
        assert b.actor_id is None

    def test_valid_role_binding_service(self):
        b = RACIRoleBinding(actor_type="service", actor_id="ci-runner")
        assert b.actor_type == "service"

    def test_invalid_actor_type(self):
        with pytest.raises(Exception):
            RACIRoleBinding(actor_type="robot")

    def test_valid_assignment(self):
        a = RACIAssignment(
            responsible=RACIRoleBinding(actor_type="llm"),
            accountable=RACIRoleBinding(actor_type="human"),
        )
        assert a.responsible.actor_type == "llm"
        assert a.accountable.actor_type == "human"

    def test_assignment_with_consulted_informed(self):
        a = RACIAssignment(
            responsible=RACIRoleBinding(actor_type="llm"),
            accountable=RACIRoleBinding(actor_type="human"),
            consulted=[RACIRoleBinding(actor_type="llm", actor_id="reviewer")],
            informed=[RACIRoleBinding(actor_type="service", actor_id="notifier")],
        )
        assert len(a.consulted) == 1
        assert len(a.informed) == 1

    def test_p0_invariant_accountable_must_be_human(self):
        """P0: accountable must always be human."""
        with pytest.raises(Exception, match="P0 invariant"):
            RACIAssignment(
                responsible=RACIRoleBinding(actor_type="llm"),
                accountable=RACIRoleBinding(actor_type="llm"),
            )

    def test_p0_invariant_accountable_service_rejected(self):
        with pytest.raises(Exception, match="P0 invariant"):
            RACIAssignment(
                responsible=RACIRoleBinding(actor_type="llm"),
                accountable=RACIRoleBinding(actor_type="service"),
            )

    def test_resolved_binding_inferred_valid(self):
        r = ResolvedRACIBinding(
            step_id="s1",
            responsible=RACIRoleBinding(actor_type="llm"),
            accountable=RACIRoleBinding(actor_type="human"),
            source="inferred",
            inferred_rule="prompt_default",
        )
        assert r.source == "inferred"
        assert r.inferred_rule == "prompt_default"
        assert r.override_reason is None

    def test_resolved_binding_explicit_valid(self):
        r = ResolvedRACIBinding(
            step_id="s1",
            responsible=RACIRoleBinding(actor_type="llm"),
            accountable=RACIRoleBinding(actor_type="human"),
            source="explicit",
            override_reason="Custom config needed",
        )
        assert r.source == "explicit"
        assert r.override_reason == "Custom config needed"

    def test_resolved_binding_explicit_requires_override_reason(self):
        with pytest.raises(Exception, match="override_reason"):
            ResolvedRACIBinding(
                step_id="s1",
                responsible=RACIRoleBinding(actor_type="llm"),
                accountable=RACIRoleBinding(actor_type="human"),
                source="explicit",
            )

    def test_resolved_binding_inferred_requires_rule(self):
        with pytest.raises(Exception, match="inferred_rule"):
            ResolvedRACIBinding(
                step_id="s1",
                responsible=RACIRoleBinding(actor_type="llm"),
                accountable=RACIRoleBinding(actor_type="human"),
                source="inferred",
            )

    def test_resolved_binding_inferred_rejects_override_reason(self):
        with pytest.raises(Exception, match="override_reason"):
            ResolvedRACIBinding(
                step_id="s1",
                responsible=RACIRoleBinding(actor_type="llm"),
                accountable=RACIRoleBinding(actor_type="human"),
                source="inferred",
                inferred_rule="prompt_default",
                override_reason="should not be here",
            )

    def test_escalation_payload(self):
        e = RACIEscalationPayload(
            run_id="run1",
            step_id="s1",
            unresolved_role="accountable",
            actor_type_expected="human",
            reason="missing owner",
            resolution_hint="Set mission_owner_id",
        )
        assert e.unresolved_role == "accountable"
        assert e.decision_id is None

    def test_assignment_frozen(self):
        a = RACIAssignment(
            responsible=RACIRoleBinding(actor_type="llm"),
            accountable=RACIRoleBinding(actor_type="human"),
        )
        with pytest.raises(Exception):
            a.responsible = RACIRoleBinding(actor_type="human")

    def test_extra_fields_rejected(self):
        with pytest.raises(Exception):
            RACIRoleBinding(actor_type="human", extra_field="bad")


# ============================================================================
# AC-2: YAML loading with/without RACI blocks
# ============================================================================


class TestRACIYAMLLoading:
    """YAML loading works correctly with and without RACI blocks."""

    def test_load_template_without_raci(self):
        """Backward compat: templates without RACI load fine."""
        template = load_mission_template_file(FIXTURES / "audit_valid_blocking.yaml")
        assert template.steps[0].raci is None
        assert template.steps[0].raci_override_reason is None

    def test_load_template_with_explicit_raci(self):
        template = load_mission_template_file(FIXTURES / "raci_explicit_override.yaml")
        step = template.steps[0]
        assert step.raci is not None
        assert step.raci.responsible.actor_type == "llm"
        assert step.raci.responsible.actor_id == "custom-agent"
        assert step.raci.accountable.actor_type == "human"
        assert step.raci_override_reason == "Custom agent required for specialized implementation"

    def test_load_template_mixed_raci_steps(self):
        """Template with some steps having RACI and others not."""
        template = load_mission_template_file(FIXTURES / "raci_explicit_override.yaml")
        assert template.steps[0].raci is not None
        assert template.steps[1].raci is None

    def test_load_template_p0_violation_fails(self):
        """Loading template with P0 violation raises."""
        with pytest.raises(Exception):
            load_mission_template_file(FIXTURES / "raci_p0_violation.yaml")

    def test_load_template_missing_override_reason_fails(self):
        """Loading template with raci but no override_reason raises."""
        with pytest.raises(Exception):
            load_mission_template_file(FIXTURES / "raci_missing_override_reason.yaml")


# ============================================================================
# AC-3, AC-4, AC-5: Inference rule correctness
# ============================================================================


class TestRACIInference:
    """Inference produces correct default bindings for all step types."""

    def test_prompt_step_default(self):
        """AC-3: PromptStep → R:llm, A:human."""
        step = PromptStep(id="s1", title="Step 1")
        policy = MissionPolicySnapshot()
        result = infer_raci(step, policy)

        assert result.step_id == "s1"
        assert result.responsible.actor_type == "llm"
        assert result.accountable.actor_type == "human"
        assert result.source == "inferred"
        assert result.inferred_rule == "prompt_default"
        assert result.override_reason is None
        assert result.consulted == []
        assert result.informed == []

    def test_audit_blocking_default(self):
        """AC-4: AuditStep(blocking) → R:human, A:human."""
        step = AuditStep(
            id="a1", title="Audit 1",
            audit=AuditConfig(trigger_mode="manual", enforcement="blocking"),
        )
        policy = MissionPolicySnapshot()
        result = infer_raci(step, policy)

        assert result.responsible.actor_type == "human"
        assert result.accountable.actor_type == "human"
        assert result.inferred_rule == "audit_blocking"

    def test_audit_advisory_default(self):
        """AC-5: AuditStep(advisory) → R:llm, A:human."""
        step = AuditStep(
            id="a2", title="Audit 2",
            audit=AuditConfig(trigger_mode="manual", enforcement="advisory"),
        )
        policy = MissionPolicySnapshot()
        result = infer_raci(step, policy)

        assert result.responsible.actor_type == "llm"
        assert result.accountable.actor_type == "human"
        assert result.inferred_rule == "audit_advisory"

    def test_inference_with_different_trigger_modes(self):
        """Trigger mode doesn't affect RACI inference — only enforcement matters."""
        for trigger_mode in ("manual", "post_merge", "both"):
            step = AuditStep(
                id="a1", title="Audit",
                audit=AuditConfig(trigger_mode=trigger_mode, enforcement="blocking"),
            )
            result = infer_raci(step, MissionPolicySnapshot())
            assert result.inferred_rule == "audit_blocking"

    def test_inference_with_different_policy_strictness(self):
        """Policy strictness doesn't change inference rules."""
        step = PromptStep(id="s1", title="Step 1")
        for strictness in ("off", "medium", "max"):
            policy = MissionPolicySnapshot(strictness=strictness)
            result = infer_raci(step, policy)
            assert result.inferred_rule == "prompt_default"


# ============================================================================
# AC-6: Explicit override precedence
# ============================================================================


class TestExplicitOverridePrecedence:
    """Explicit overrides take precedence over inferred defaults."""

    def test_explicit_override_on_prompt_step(self):
        step = PromptStep(
            id="s1", title="Step 1",
            raci=RACIAssignment(
                responsible=RACIRoleBinding(actor_type="llm", actor_id="custom-agent"),
                accountable=RACIRoleBinding(actor_type="human", actor_id="owner-1"),
                consulted=[RACIRoleBinding(actor_type="llm", actor_id="reviewer")],
            ),
            raci_override_reason="Custom agent needed",
        )
        inputs = {"mission_owner_id": "owner-1", "agent_id": "default-agent"}
        result = resolve_raci(step, inputs, MissionPolicySnapshot())

        assert result.source == "explicit"
        assert result.override_reason == "Custom agent needed"
        assert result.responsible.actor_id == "custom-agent"
        assert result.accountable.actor_id == "owner-1"
        assert len(result.consulted) == 1
        assert result.consulted[0].actor_id == "reviewer"

    def test_inferred_when_no_explicit_raci(self):
        step = PromptStep(id="s1", title="Step 1")
        inputs = {"mission_owner_id": "owner-1", "agent_id": "agent-1"}
        result = resolve_raci(step, inputs, MissionPolicySnapshot())

        assert result.source == "inferred"
        assert result.inferred_rule == "prompt_default"
        assert result.responsible.actor_id == "agent-1"
        assert result.accountable.actor_id == "owner-1"

    def test_explicit_actor_ids_preserved(self):
        """When explicit raci provides actor_ids, they are used as-is."""
        step = PromptStep(
            id="s1", title="Step 1",
            raci=RACIAssignment(
                responsible=RACIRoleBinding(actor_type="llm", actor_id="specific-agent"),
                accountable=RACIRoleBinding(actor_type="human", actor_id="specific-owner"),
            ),
            raci_override_reason="Named actors",
        )
        # Even with different inputs, explicit IDs win
        inputs = {"mission_owner_id": "different-owner", "agent_id": "different-agent"}
        result = resolve_raci(step, inputs, MissionPolicySnapshot())

        assert result.responsible.actor_id == "specific-agent"
        assert result.accountable.actor_id == "specific-owner"


# ============================================================================
# AC-7: Escalation scenarios
# ============================================================================


class TestEscalationScenarios:
    """Unresolved-role escalation works correctly with proper payloads."""

    def test_escalation_missing_mission_owner(self):
        step = PromptStep(id="s1", title="Step 1")
        with pytest.raises(MissionRuntimeError, match="escalation"):
            resolve_raci(step, {}, MissionPolicySnapshot())

    def test_escalation_missing_agent_id_for_blocking_audit(self):
        """Blocking audit needs human R/A → needs mission_owner_id."""
        step = AuditStep(
            id="a1", title="Audit",
            audit=AuditConfig(trigger_mode="manual", enforcement="blocking"),
        )
        with pytest.raises(MissionRuntimeError, match="escalation"):
            resolve_raci(step, {}, MissionPolicySnapshot())

    def test_escalation_empty_mission_owner(self):
        step = PromptStep(id="s1", title="Step 1")
        with pytest.raises(MissionRuntimeError, match="escalation"):
            resolve_raci(step, {"mission_owner_id": "  "}, MissionPolicySnapshot())

    def test_no_escalation_with_valid_inputs(self):
        step = PromptStep(id="s1", title="Step 1")
        inputs = {"mission_owner_id": "owner", "agent_id": "agent"}
        result = resolve_raci(step, inputs, MissionPolicySnapshot())
        assert result.responsible.actor_id == "agent"
        assert result.accountable.actor_id == "owner"

    def test_optional_roles_dont_escalate(self):
        """C/I roles don't cause escalation when actor_id can't be resolved."""
        step = PromptStep(
            id="s1", title="Step 1",
            raci=RACIAssignment(
                responsible=RACIRoleBinding(actor_type="llm", actor_id="agent-1"),
                accountable=RACIRoleBinding(actor_type="human", actor_id="owner-1"),
                consulted=[RACIRoleBinding(actor_type="service")],  # no actor_id, no service_id in inputs
            ),
            raci_override_reason="Testing optional roles",
        )
        inputs = {"mission_owner_id": "owner-1", "agent_id": "agent-1"}
        result = resolve_raci(step, inputs, MissionPolicySnapshot())
        # Consulted service role is unresolved but not escalated
        assert result.consulted[0].actor_id is None


# ============================================================================
# AC-8: Validate RACI assignment
# ============================================================================


class TestValidateRACIAssignment:
    """validate_raci_assignment catches P0 violations."""

    def test_valid_prompt_step_assignment(self):
        a = RACIAssignment(
            responsible=RACIRoleBinding(actor_type="llm"),
            accountable=RACIRoleBinding(actor_type="human"),
        )
        step = PromptStep(id="s1", title="Step 1")
        ok, errors = validate_raci_assignment(a, step)
        assert ok
        assert errors == []

    def test_valid_blocking_audit_assignment(self):
        a = RACIAssignment(
            responsible=RACIRoleBinding(actor_type="human"),
            accountable=RACIRoleBinding(actor_type="human"),
        )
        step = AuditStep(
            id="a1", title="Audit",
            audit=AuditConfig(trigger_mode="manual", enforcement="blocking"),
        )
        ok, errors = validate_raci_assignment(a, step)
        assert ok

    def test_blocking_audit_llm_responsible_fails(self):
        a = RACIAssignment(
            responsible=RACIRoleBinding(actor_type="llm"),
            accountable=RACIRoleBinding(actor_type="human"),
        )
        step = AuditStep(
            id="a1", title="Audit",
            audit=AuditConfig(trigger_mode="manual", enforcement="blocking"),
        )
        ok, errors = validate_raci_assignment(a, step)
        assert not ok
        assert any("blocking" in e.lower() for e in errors)

    def test_advisory_audit_llm_responsible_ok(self):
        a = RACIAssignment(
            responsible=RACIRoleBinding(actor_type="llm"),
            accountable=RACIRoleBinding(actor_type="human"),
        )
        step = AuditStep(
            id="a1", title="Audit",
            audit=AuditConfig(trigger_mode="manual", enforcement="advisory"),
        )
        ok, errors = validate_raci_assignment(a, step)
        assert ok


# ============================================================================
# AC-9: Authority kernel integration (RACI audit trail)
# ============================================================================


class TestRACIAuthorityKernel:
    """Authority kernel integration preserves behavior while adding RACI."""

    def test_authority_metadata_without_raci(self):
        """Backward compat: _authority_metadata works without RACI params."""
        from spec_kitty_runtime.engine import _authority_metadata
        from spec_kitty_events.mission_next import RuntimeActorIdentity

        actor = RuntimeActorIdentity(actor_id="user1", actor_type="human")
        meta = _authority_metadata(actor, "mission_owner", None)
        assert meta["actor_type"] == "human"
        assert meta["actor_id"] == "user1"
        assert "raci_source" not in meta

    def test_authority_metadata_with_raci(self):
        from spec_kitty_runtime.engine import _authority_metadata
        from spec_kitty_events.mission_next import RuntimeActorIdentity

        actor = RuntimeActorIdentity(actor_id="user1", actor_type="human")
        meta = _authority_metadata(
            actor, "mission_owner", None,
            raci_source="inferred",
            override_reason=None,
        )
        assert meta["raci_source"] == "inferred"
        assert "override_reason" not in meta  # None values excluded

    def test_authority_metadata_with_explicit_raci(self):
        from spec_kitty_runtime.engine import _authority_metadata
        from spec_kitty_events.mission_next import RuntimeActorIdentity

        actor = RuntimeActorIdentity(actor_id="user1", actor_type="human")
        meta = _authority_metadata(
            actor, "mission_owner", None,
            raci_source="explicit",
            override_reason="Custom config",
        )
        assert meta["raci_source"] == "explicit"
        assert meta["override_reason"] == "Custom config"

    def test_find_step_by_id(self):
        from spec_kitty_runtime.engine import _find_step_by_id

        template = load_mission_template_file(FIXTURES / "raci_explicit_override.yaml")
        step = _find_step_by_id(template, "step-01")
        assert step is not None
        assert step.id == "step-01"

        audit = _find_step_by_id(template, "audit-01")
        assert audit is not None
        assert audit.id == "audit-01"

        missing = _find_step_by_id(template, "nonexistent")
        assert missing is None


# ============================================================================
# AC-10: Template compatibility diagnostics
# ============================================================================


class TestRACIDiagnostics:
    """Template compatibility diagnostics catch RACI-related issues."""

    def test_diagnostics_no_raci_is_compatible(self):
        report = validate_mission_template_compatibility(
            FIXTURES / "audit_valid_blocking.yaml"
        )
        assert report.is_compatible

    def test_diagnostics_valid_explicit_raci(self):
        report = validate_mission_template_compatibility(
            FIXTURES / "raci_explicit_override.yaml"
        )
        assert report.is_compatible

    def test_diagnostics_p0_violation(self):
        report = validate_mission_template_compatibility(
            FIXTURES / "raci_p0_violation.yaml"
        )
        assert not report.is_compatible
        codes = {i.code for i in report.issues}
        assert "P0_INVARIANT_VIOLATION" in codes

    def test_diagnostics_missing_override_reason(self):
        report = validate_mission_template_compatibility(
            FIXTURES / "raci_missing_override_reason.yaml"
        )
        assert not report.is_compatible
        codes = {i.code for i in report.issues}
        assert "MISSING_OVERRIDE_REASON" in codes

    def test_diagnostics_blocking_audit_llm_responsible(self):
        report = validate_mission_template_compatibility(
            FIXTURES / "raci_blocking_audit_llm.yaml"
        )
        assert not report.is_compatible
        codes = {i.code for i in report.issues}
        assert "INVALID_RACI_ROLE" in codes

    def test_diagnostics_unknown_actor_type(self, tmp_path):
        yaml_content = """\
mission:
  key: bad-actor
  name: Bad Actor Type
  version: "1.0.0"
steps:
  - id: step-01
    title: Bad step
    raci:
      responsible:
        actor_type: robot
      accountable:
        actor_type: human
    raci_override_reason: "Testing unknown actor type"
"""
        p = tmp_path / "bad_actor.yaml"
        p.write_text(yaml_content)
        report = validate_mission_template_compatibility(p)
        assert not report.is_compatible
        codes = {i.code for i in report.issues}
        assert "UNKNOWN_ACTOR_TYPE" in codes

    def test_diagnostics_missing_required_role(self, tmp_path):
        yaml_content = """\
mission:
  key: missing-role
  name: Missing Role
  version: "1.0.0"
steps:
  - id: step-01
    title: Bad step
    raci:
      responsible:
        actor_type: llm
    raci_override_reason: "Missing accountable role"
"""
        p = tmp_path / "missing_role.yaml"
        p.write_text(yaml_content)
        report = validate_mission_template_compatibility(p)
        assert not report.is_compatible
        codes = {i.code for i in report.issues}
        assert "INVALID_RACI_ROLE" in codes


# ============================================================================
# AC-11: Determinism
# ============================================================================


class TestDeterminism:
    """All operations are deterministic with no randomness."""

    def test_infer_raci_deterministic(self):
        """Same inputs → same output, always."""
        step = PromptStep(id="s1", title="Step 1")
        policy = MissionPolicySnapshot()
        results = [infer_raci(step, policy) for _ in range(10)]
        first = results[0].model_dump()
        for r in results[1:]:
            assert r.model_dump() == first

    def test_resolve_raci_deterministic(self):
        step = PromptStep(id="s1", title="Step 1")
        inputs = {"mission_owner_id": "owner", "agent_id": "agent"}
        policy = MissionPolicySnapshot()
        results = [resolve_raci(step, inputs, policy) for _ in range(10)]
        first = results[0].model_dump()
        for r in results[1:]:
            assert r.model_dump() == first

    def test_validate_raci_deterministic(self):
        a = RACIAssignment(
            responsible=RACIRoleBinding(actor_type="llm"),
            accountable=RACIRoleBinding(actor_type="human"),
        )
        step = PromptStep(id="s1", title="Step 1")
        results = [validate_raci_assignment(a, step) for _ in range(10)]
        for ok, errors in results:
            assert ok
            assert errors == []


# ============================================================================
# AC-12: Backward compatibility
# ============================================================================


class TestBackwardCompatibility:
    """Missions without RACI blocks continue to work."""

    def test_prompt_step_without_raci_fields(self):
        step = PromptStep(id="s1", title="Step 1", prompt="Do something")
        assert step.raci is None
        assert step.raci_override_reason is None

    def test_audit_step_without_raci_fields(self):
        step = AuditStep(
            id="a1", title="Audit",
            audit=AuditConfig(trigger_mode="manual", enforcement="blocking"),
        )
        assert step.raci is None
        assert step.raci_override_reason is None

    def test_load_existing_valid_templates_unmodified(self):
        """Valid existing fixture templates load without error."""
        valid_fixtures = [
            "audit_valid_blocking.yaml",
            "audit_valid_advisory.yaml",
            "audit_mixed_steps.yaml",
            "audit_only_steps.yaml",
        ]
        for name in valid_fixtures:
            fixture = FIXTURES / name
            if fixture.exists():
                template = load_mission_template_file(fixture)
                assert template is not None

    def test_infer_raci_for_legacy_steps(self):
        """Steps without explicit RACI get correct inferred bindings."""
        step = PromptStep(id="s1", title="Legacy Step")
        result = infer_raci(step, MissionPolicySnapshot())
        assert result.source == "inferred"
        assert result.inferred_rule == "prompt_default"

    def test_resolve_raci_for_legacy_steps(self):
        step = PromptStep(id="s1", title="Legacy Step")
        inputs = {"mission_owner_id": "owner", "agent_id": "agent"}
        result = resolve_raci(step, inputs, MissionPolicySnapshot())
        assert result.source == "inferred"
        assert result.responsible.actor_id == "agent"
        assert result.accountable.actor_id == "owner"

    def test_serialization_roundtrip(self):
        """ResolvedRACIBinding serializes and deserializes cleanly."""
        original = ResolvedRACIBinding(
            step_id="s1",
            responsible=RACIRoleBinding(actor_type="llm", actor_id="agent"),
            accountable=RACIRoleBinding(actor_type="human", actor_id="owner"),
            source="inferred",
            inferred_rule="prompt_default",
        )
        data = original.model_dump(mode="json")
        restored = ResolvedRACIBinding.model_validate(data)
        assert restored == original

    def test_json_roundtrip(self):
        """JSON serialization roundtrip preserves all fields."""
        original = ResolvedRACIBinding(
            step_id="s1",
            responsible=RACIRoleBinding(actor_type="llm", actor_id="agent"),
            accountable=RACIRoleBinding(actor_type="human", actor_id="owner"),
            consulted=[RACIRoleBinding(actor_type="llm", actor_id="reviewer")],
            source="explicit",
            override_reason="Custom config",
        )
        json_str = json.dumps(original.model_dump(mode="json"), sort_keys=True)
        restored = ResolvedRACIBinding.model_validate(json.loads(json_str))
        assert restored == original

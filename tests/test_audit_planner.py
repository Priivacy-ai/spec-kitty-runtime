"""Tests for planner DAG extension handling AuditStep entries.

Covers AC-3 (blocking enforcement), AC-4 (advisory enforcement),
AC-7 (DAG ordering), and AC-9 (determinism).
"""

from __future__ import annotations

import pytest

from spec_kitty_runtime.planner import plan_next, serialize_decision
from spec_kitty_runtime.schema import (
    MissionPolicySnapshot,
    MissionRunSnapshot,
    MissionTemplate,
)


HASH_PLACEHOLDER = "0" * 64


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _policy() -> MissionPolicySnapshot:
    return MissionPolicySnapshot()


def _snapshot(**overrides) -> MissionRunSnapshot:
    defaults = dict(
        run_id="run-audit-01",
        mission_key="audit-test",
        template_path="/tmp/audit_mission.yaml",
        template_hash=HASH_PLACEHOLDER,
        issued_step_id=None,
        completed_steps=[],
        inputs={},
        decisions={},
        pending_decisions={},
        blocked_reason=None,
    )
    defaults.update(overrides)
    return MissionRunSnapshot(**defaults)


def _template_blocking(trigger_mode: str = "manual") -> MissionTemplate:
    """Template with one regular step followed by one blocking audit step."""
    return MissionTemplate.model_validate(
        {
            "mission": {"key": "audit-test", "name": "Audit Test", "version": "1.0.0"},
            "steps": [
                {"id": "step-01", "title": "Implement feature", "prompt": "Do it"},
            ],
            "audit_steps": [
                {
                    "id": "audit-01",
                    "title": "Security Review",
                    "description": "Check security posture",
                    "audit": {
                        "trigger_mode": trigger_mode,
                        "enforcement": "blocking",
                        "label": "security",
                    },
                }
            ],
        }
    )


def _template_advisory() -> MissionTemplate:
    """Template with one regular step followed by one advisory audit step."""
    return MissionTemplate.model_validate(
        {
            "mission": {"key": "audit-test", "name": "Audit Test", "version": "1.0.0"},
            "steps": [
                {"id": "step-01", "title": "Implement feature", "prompt": "Do it"},
            ],
            "audit_steps": [
                {
                    "id": "audit-adv-01",
                    "title": "Code Quality Check",
                    "description": "Evaluate code quality",
                    "audit": {
                        "trigger_mode": "manual",
                        "enforcement": "advisory",
                    },
                }
            ],
        }
    )


# ---------------------------------------------------------------------------
# AC-3: Blocking enforcement
# ---------------------------------------------------------------------------

class TestPlannerBlockingAudit:
    def test_blocking_audit_emits_decision_required(self):
        template = _template_blocking()
        snapshot = _snapshot(completed_steps=["step-01"])

        d = plan_next(snapshot, template, _policy())

        assert d.kind == "decision_required"

    def test_decision_id_format(self):
        template = _template_blocking()
        snapshot = _snapshot(completed_steps=["step-01"])

        d = plan_next(snapshot, template, _policy())

        assert d.decision_id == "audit:audit-01"

    def test_question_contains_title(self):
        template = _template_blocking()
        snapshot = _snapshot(completed_steps=["step-01"])

        d = plan_next(snapshot, template, _policy())

        assert d.question is not None
        assert "Security Review" in d.question

    def test_options_are_approve_reject(self):
        template = _template_blocking()
        snapshot = _snapshot(completed_steps=["step-01"])

        d = plan_next(snapshot, template, _policy())

        assert d.options == ["approve", "reject"]

    def test_input_key_is_none(self):
        template = _template_blocking()
        snapshot = _snapshot(completed_steps=["step-01"])

        d = plan_next(snapshot, template, _policy())

        assert d.input_key is None

    @pytest.mark.parametrize("trigger_mode", ["manual", "post_merge", "both"])
    def test_blocking_applies_to_all_trigger_modes(self, trigger_mode: str):
        template = _template_blocking(trigger_mode=trigger_mode)
        snapshot = _snapshot(completed_steps=["step-01"])

        d = plan_next(snapshot, template, _policy())

        assert d.kind == "decision_required"
        assert d.decision_id == "audit:audit-01"
        assert d.options == ["approve", "reject"]
        assert d.input_key is None

    def test_blocking_audit_has_step_id_set(self):
        template = _template_blocking()
        snapshot = _snapshot(completed_steps=["step-01"])

        d = plan_next(snapshot, template, _policy())

        assert d.step_id == "audit-01"

    def test_blocking_audit_has_step_title_set(self):
        template = _template_blocking()
        snapshot = _snapshot(completed_steps=["step-01"])

        d = plan_next(snapshot, template, _policy())

        assert d.step_title == "Security Review"

    def test_blocking_audit_context_is_none(self):
        """Blocking audit decisions do not carry a StepContextBundle."""
        template = _template_blocking()
        snapshot = _snapshot(completed_steps=["step-01"])

        d = plan_next(snapshot, template, _policy())

        assert d.context is None


# ---------------------------------------------------------------------------
# AC-4: Advisory enforcement
# ---------------------------------------------------------------------------

class TestPlannerAdvisoryAudit:
    def test_advisory_audit_emits_step(self):
        template = _template_advisory()
        snapshot = _snapshot(completed_steps=["step-01"])

        d = plan_next(snapshot, template, _policy())

        assert d.kind == "step"

    def test_advisory_step_id_correct(self):
        template = _template_advisory()
        snapshot = _snapshot(completed_steps=["step-01"])

        d = plan_next(snapshot, template, _policy())

        assert d.step_id == "audit-adv-01"

    def test_advisory_step_title_correct(self):
        template = _template_advisory()
        snapshot = _snapshot(completed_steps=["step-01"])

        d = plan_next(snapshot, template, _policy())

        assert d.step_title == "Code Quality Check"

    def test_advisory_step_has_context(self):
        template = _template_advisory()
        snapshot = _snapshot(completed_steps=["step-01"])

        d = plan_next(snapshot, template, _policy())

        assert d.context is not None
        assert d.context.step_id == "audit-adv-01"

    def test_advisory_step_has_prompt(self):
        template = _template_advisory()
        snapshot = _snapshot(completed_steps=["step-01"])

        d = plan_next(snapshot, template, _policy())

        assert d.prompt is not None
        assert len(d.prompt) > 0


# ---------------------------------------------------------------------------
# AC-7: DAG ordering
# ---------------------------------------------------------------------------

class TestPlannerAuditDagOrdering:
    def test_audit_with_depends_on_waits_for_dependency(self):
        """Audit step with depends_on waits until dependency is completed."""
        template = MissionTemplate.model_validate(
            {
                "mission": {"key": "audit-test", "name": "Audit Test", "version": "1.0.0"},
                "steps": [
                    {"id": "step-01", "title": "Step One", "prompt": "Do it"},
                ],
                "audit_steps": [
                    {
                        "id": "audit-dep-01",
                        "title": "Dependent Audit",
                        "audit": {"trigger_mode": "manual", "enforcement": "blocking"},
                        "depends_on": ["step-01"],
                    }
                ],
            }
        )
        # step-01 is NOT yet completed
        snapshot = _snapshot(completed_steps=[])

        d = plan_next(snapshot, template, _policy())

        # Should resolve to step-01 first, not the audit step
        assert d.kind == "step"
        assert d.step_id == "step-01"

    def test_audit_with_depends_on_issued_after_dependency_completed(self):
        """Once dependency is completed, audit step becomes eligible."""
        template = MissionTemplate.model_validate(
            {
                "mission": {"key": "audit-test", "name": "Audit Test", "version": "1.0.0"},
                "steps": [
                    {"id": "step-01", "title": "Step One", "prompt": "Do it"},
                ],
                "audit_steps": [
                    {
                        "id": "audit-dep-01",
                        "title": "Dependent Audit",
                        "audit": {"trigger_mode": "manual", "enforcement": "blocking"},
                        "depends_on": ["step-01"],
                    }
                ],
            }
        )
        snapshot = _snapshot(completed_steps=["step-01"])

        d = plan_next(snapshot, template, _policy())

        assert d.kind == "decision_required"
        assert d.decision_id == "audit:audit-dep-01"

    def test_audit_no_depends_on_after_all_steps(self):
        """Audit step with no depends_on appears after all regular steps complete."""
        template = MissionTemplate.model_validate(
            {
                "mission": {"key": "audit-test", "name": "Audit Test", "version": "1.0.0"},
                "steps": [
                    {"id": "step-01", "title": "Step One", "prompt": "Do it"},
                    {"id": "step-02", "title": "Step Two", "prompt": "Do it two"},
                ],
                "audit_steps": [
                    {
                        "id": "audit-final",
                        "title": "Final Audit",
                        "audit": {"trigger_mode": "manual", "enforcement": "blocking"},
                    }
                ],
            }
        )
        # Only step-01 done, step-02 still pending → audit should NOT appear yet
        snapshot = _snapshot(completed_steps=["step-01"])

        d = plan_next(snapshot, template, _policy())

        assert d.kind == "step"
        assert d.step_id == "step-02"

    def test_audit_no_depends_on_eligible_when_all_regular_done(self):
        """Audit step with no depends_on is eligible after all regular steps complete."""
        template = MissionTemplate.model_validate(
            {
                "mission": {"key": "audit-test", "name": "Audit Test", "version": "1.0.0"},
                "steps": [
                    {"id": "step-01", "title": "Step One", "prompt": "Do it"},
                    {"id": "step-02", "title": "Step Two", "prompt": "Do it two"},
                ],
                "audit_steps": [
                    {
                        "id": "audit-final",
                        "title": "Final Audit",
                        "audit": {"trigger_mode": "manual", "enforcement": "blocking"},
                    }
                ],
            }
        )
        snapshot = _snapshot(completed_steps=["step-01", "step-02"])

        d = plan_next(snapshot, template, _policy())

        assert d.kind == "decision_required"
        assert d.decision_id == "audit:audit-final"

    def test_regular_steps_before_audit_steps(self):
        """Regular steps always come before audit steps in the combined sequence."""
        template = MissionTemplate.model_validate(
            {
                "mission": {"key": "audit-test", "name": "Audit Test", "version": "1.0.0"},
                "steps": [
                    {"id": "regular-01", "title": "Regular Step", "prompt": "Do it"},
                ],
                "audit_steps": [
                    {
                        "id": "audit-01",
                        "title": "First Audit",
                        "audit": {"trigger_mode": "manual", "enforcement": "advisory"},
                    }
                ],
            }
        )
        snapshot = _snapshot(completed_steps=[])

        d = plan_next(snapshot, template, _policy())

        assert d.step_id == "regular-01"

    def test_two_audit_steps_maintain_template_order(self):
        """Two audit steps with same eligibility maintain template definition order."""
        template = MissionTemplate.model_validate(
            {
                "mission": {"key": "audit-test", "name": "Audit Test", "version": "1.0.0"},
                "steps": [
                    {"id": "step-01", "title": "Step One", "prompt": "Do it"},
                ],
                "audit_steps": [
                    {
                        "id": "audit-alpha",
                        "title": "Alpha Audit",
                        "audit": {"trigger_mode": "manual", "enforcement": "advisory"},
                    },
                    {
                        "id": "audit-beta",
                        "title": "Beta Audit",
                        "audit": {"trigger_mode": "manual", "enforcement": "advisory"},
                    },
                ],
            }
        )
        snapshot = _snapshot(completed_steps=["step-01"])

        d = plan_next(snapshot, template, _policy())

        # alpha comes first in template order
        assert d.step_id == "audit-alpha"

    def test_cross_type_dependency_audit_depends_on_audit(self):
        """An audit step can depend on another audit step."""
        template = MissionTemplate.model_validate(
            {
                "mission": {"key": "audit-test", "name": "Audit Test", "version": "1.0.0"},
                "steps": [],
                "audit_steps": [
                    {
                        "id": "audit-01",
                        "title": "First Audit",
                        "audit": {"trigger_mode": "manual", "enforcement": "advisory"},
                    },
                    {
                        "id": "audit-02",
                        "title": "Second Audit",
                        "audit": {"trigger_mode": "manual", "enforcement": "advisory"},
                        "depends_on": ["audit-01"],
                    },
                ],
            }
        )
        # audit-01 not yet completed
        snapshot = _snapshot(completed_steps=[])

        d = plan_next(snapshot, template, _policy())

        # audit-01 should come first; audit-02 is blocked
        assert d.step_id == "audit-01"

    def test_terminal_when_all_steps_and_audits_completed(self):
        """Mission is terminal only when both regular steps and audit steps are done."""
        template = MissionTemplate.model_validate(
            {
                "mission": {"key": "audit-test", "name": "Audit Test", "version": "1.0.0"},
                "steps": [
                    {"id": "step-01", "title": "Step One", "prompt": "Do it"},
                ],
                "audit_steps": [
                    {
                        "id": "audit-01",
                        "title": "Audit One",
                        "audit": {"trigger_mode": "manual", "enforcement": "blocking"},
                    }
                ],
            }
        )
        snapshot = _snapshot(completed_steps=["step-01", "audit-01"])

        d = plan_next(snapshot, template, _policy())

        assert d.kind == "terminal"

    def test_audit_only_mission_no_regular_steps(self):
        """Mission with only audit steps and no regular steps works correctly."""
        template = MissionTemplate.model_validate(
            {
                "mission": {"key": "audit-only", "name": "Audit Only", "version": "1.0.0"},
                "steps": [],
                "audit_steps": [
                    {
                        "id": "audit-01",
                        "title": "Audit One",
                        "audit": {"trigger_mode": "manual", "enforcement": "blocking"},
                    }
                ],
            }
        )
        snapshot = _snapshot(completed_steps=[])

        d = plan_next(snapshot, template, _policy())

        assert d.kind == "decision_required"
        assert d.decision_id == "audit:audit-01"


# ---------------------------------------------------------------------------
# AC-9: Determinism
# ---------------------------------------------------------------------------

class TestPlannerDeterminism:
    def test_same_input_same_output(self):
        """Same MissionRunSnapshot + MissionTemplate → identical NextDecision."""
        template = _template_blocking()
        snapshot = _snapshot(completed_steps=["step-01"])

        d1 = plan_next(snapshot, template, _policy())
        d2 = plan_next(snapshot, template, _policy())

        assert d1.model_dump() == d2.model_dump()

    def test_serialize_decision_stable(self):
        """serialize_decision produces same bytes across calls."""
        template = _template_blocking()
        snapshot = _snapshot(completed_steps=["step-01"])

        d = plan_next(snapshot, template, _policy())
        s1 = serialize_decision(d)
        s2 = serialize_decision(d)

        assert s1 == s2

    def test_audit_only_mission(self):
        """Determinism holds for audit-only missions (no regular steps)."""
        template = MissionTemplate.model_validate(
            {
                "mission": {"key": "audit-only", "name": "Audit Only", "version": "1.0.0"},
                "steps": [],
                "audit_steps": [
                    {
                        "id": "audit-01",
                        "title": "Solo Audit",
                        "audit": {"trigger_mode": "manual", "enforcement": "blocking"},
                    }
                ],
            }
        )
        snapshot = _snapshot(completed_steps=[])

        d1 = plan_next(snapshot, template, _policy())
        d2 = plan_next(snapshot, template, _policy())

        assert d1.model_dump() == d2.model_dump()
        assert d1.kind == "decision_required"

    def test_same_input_advisory_same_output(self):
        """Determinism holds for advisory audit steps."""
        template = _template_advisory()
        snapshot = _snapshot(completed_steps=["step-01"])

        d1 = plan_next(snapshot, template, _policy())
        d2 = plan_next(snapshot, template, _policy())

        assert d1.model_dump() == d2.model_dump()
        assert d1.kind == "step"

    def test_serialize_decision_advisory_stable(self):
        """serialize_decision is stable for advisory (step kind) decisions."""
        template = _template_advisory()
        snapshot = _snapshot(completed_steps=["step-01"])

        d = plan_next(snapshot, template, _policy())
        s1 = serialize_decision(d)
        s2 = serialize_decision(d)

        assert s1 == s2

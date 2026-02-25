"""Tests for the transition-gate engine and context resolution (WP02)."""

import tempfile
from pathlib import Path
from typing import Any, Dict

import pytest

from spec_kitty_runtime.contracts import RemediationPayload
from spec_kitty_runtime.engine import (
    TransitionGate,
    resolve_context,
    validate_binding,
    _resolve_explicit_inputs,
    _resolve_ledger_bindings,
    _resolve_mission_metadata,
    _resolve_local_discovery,
)
from spec_kitty_runtime.schema import ContextType, ContextTypeRegistry, StepContextContract


# ============================================================================
# TransitionGate Tests
# ============================================================================


class TestTransitionGateEvaluation:
    """Tests for TransitionGate evaluation logic."""

    def test_gate_ready_with_all_required_contexts_resolved(self) -> None:
        """Gate returns 'ready' when all required contexts resolve."""
        contract = StepContextContract(
            requires=[
                ContextType(type="feature_binding"),
            ]
        )
        available_bindings = {
            "explicit_inputs": {"feature_binding": "feature-value"}
        }

        gate = TransitionGate(contract, available_bindings)
        result = gate.evaluate()

        assert result == "ready"

    def test_gate_blocks_missing_required_context(self) -> None:
        """Gate blocks when required context cannot be resolved."""
        contract = StepContextContract(
            requires=[
                ContextType(type="missing_context", resolver_ref="test:resolver"),
            ]
        )
        available_bindings = {}

        gate = TransitionGate(contract, available_bindings)
        result = gate.evaluate()

        assert isinstance(result, RemediationPayload)
        assert result.error_code == "CONTEXT_MISSING"

    def test_gate_blocks_ambiguous_context(self) -> None:
        """Gate blocks when context is ambiguous (multiple candidates)."""
        contract = StepContextContract(
            requires=[
                ContextType(type="feature_binding"),
            ]
        )
        available_bindings = {
            "explicit_inputs": {"feature_binding": ["feature-a", "feature-b"]}
        }

        gate = TransitionGate(contract, available_bindings)
        result = gate.evaluate()

        assert isinstance(result, RemediationPayload)
        assert result.error_code == "CONTEXT_AMBIGUOUS"


# ============================================================================
# Resolver Precedence Tests
# ============================================================================


class TestResolverPrecedence:
    """Tests for the 5-point resolver precedence chain."""

    def test_precedence_1_explicit_inputs_highest(self) -> None:
        """Path 1: Explicit inputs have highest precedence."""
        contract_type = ContextType(type="feature_binding")
        available_bindings = {
            "explicit_inputs": {"feature_binding": "explicit-value"},
            "ledger": {"feature_binding": "ledger-value"},
            "mission_metadata": {"feature_binding": "metadata-value"},
            "discovery_hints": {"feature_binding": "discovery-value"},
        }

        result = resolve_context(
            "feature_binding",
            contract_type,
            available_bindings,
            ContextTypeRegistry()
        )

        assert result == "explicit-value"

    def test_precedence_2_ledger_when_no_explicit(self) -> None:
        """Path 2: ContextLedger used when no explicit input."""
        contract_type = ContextType(type="feature_binding")
        available_bindings = {
            "ledger": {"feature_binding": {"value": "ledger-value"}},
            "mission_metadata": {"feature_binding": "metadata-value"},
            "discovery_hints": {"feature_binding": "discovery-value"},
        }

        result = resolve_context(
            "feature_binding",
            contract_type,
            available_bindings,
            ContextTypeRegistry()
        )

        assert result == "ledger-value"

    def test_precedence_3_metadata_when_no_explicit_or_ledger(self) -> None:
        """Path 3: Mission metadata used if no explicit or ledger."""
        contract_type = ContextType(type="target_branch")
        available_bindings = {
            "mission_metadata": {"target_branch": "main"},
            "discovery_hints": {"target_branch": "develop"},
        }

        result = resolve_context(
            "target_branch",
            contract_type,
            available_bindings,
            ContextTypeRegistry()
        )

        assert result == "main"

    def test_precedence_4_discovery_when_no_higher_precedence(self, tmp_path: Path) -> None:
        """Path 4: Local discovery used if no higher precedence."""
        contract_type = ContextType(type="spec_artifact")

        discovery_dir = tmp_path / "discovery"
        discovery_dir.mkdir()

        available_bindings = {
            "discovery_hints": {"spec_artifact": "spec-hint"},
        }

        result = resolve_context(
            "spec_artifact",
            contract_type,
            available_bindings,
            ContextTypeRegistry(),
            local_discovery_root=discovery_dir
        )

        assert result == "spec-hint"

    def test_no_fallback_without_explicit_policy(self) -> None:
        """Fallback resolvers not used without explicit policy (default: disabled)."""
        contract_type = ContextType(type="custom_context")
        available_bindings = {
            "fallback_resolvers": {"custom_context": "fallback-value"}
        }

        result = resolve_context(
            "custom_context",
            contract_type,
            available_bindings,
            ContextTypeRegistry()
        )

        assert isinstance(result, RemediationPayload)
        assert result.error_code == "CONTEXT_MISSING"

    def test_fallback_used_with_explicit_policy(self) -> None:
        """Fallback resolvers used when allow_fallback_resolvers policy enabled."""
        contract_type = ContextType(type="custom_context")
        available_bindings = {
            "mission_metadata": {"allow_fallback_resolvers": True},
            "fallback_resolvers": {"custom_context": "fallback-value"}
        }

        result = resolve_context(
            "custom_context",
            contract_type,
            available_bindings,
            ContextTypeRegistry()
        )

        assert result == "fallback-value"


# ============================================================================
# Ambiguity Detection Tests
# ============================================================================


class TestAmbiguityDetection:
    """Tests for detecting multiple equally valid candidates."""

    def test_ambiguity_detected_from_explicit_list_input(self) -> None:
        """Ambiguity detected when explicit inputs has list value."""
        contract_type = ContextType(type="feature_binding")
        available_bindings = {
            "explicit_inputs": {
                "feature_binding": ["feature-a", "feature-b"]
            }
        }

        result = resolve_context(
            "feature_binding",
            contract_type,
            available_bindings,
            ContextTypeRegistry()
        )

        assert isinstance(result, RemediationPayload)
        assert result.error_code == "CONTEXT_AMBIGUOUS"
        assert len(result.candidates) == 2
        assert result.candidates[0]["value"] == "feature-a"
        assert result.candidates[1]["value"] == "feature-b"
        for candidate in result.candidates:
            assert "source" in candidate
            assert "value" in candidate
            assert "metadata" in candidate
        assert result.remediation_hint is not None

    def test_ambiguity_detected_from_discovery(self, tmp_path: Path) -> None:
        """Ambiguity detected when multiple artifact files match."""
        spec_md = tmp_path / "spec.md"
        spec_yaml = tmp_path / "spec.yaml"
        spec_md.write_text("# Spec MD")
        spec_yaml.write_text("# Spec YAML")

        contract_type = ContextType(type="spec_artifact")
        available_bindings = {}

        result = resolve_context(
            "spec_artifact",
            contract_type,
            available_bindings,
            ContextTypeRegistry(),
            local_discovery_root=tmp_path
        )

        assert isinstance(result, RemediationPayload)
        assert result.error_code == "CONTEXT_AMBIGUOUS"
        assert len(result.candidates) == 2
        for candidate in result.candidates:
            assert "source" in candidate
            assert "value" in candidate
            assert "metadata" in candidate
        assert result.remediation_hint is not None

    def test_ambiguity_payload_includes_all_candidates(self) -> None:
        """RemediationPayload for ambiguous context includes all candidates."""
        contract_type = ContextType(type="feature_binding")
        available_bindings = {
            "explicit_inputs": {
                "feature_binding": ["feature-a", "feature-b"]
            }
        }

        result = resolve_context(
            "feature_binding",
            contract_type,
            available_bindings,
            ContextTypeRegistry()
        )

        assert isinstance(result, RemediationPayload)
        assert result.error_code == "CONTEXT_AMBIGUOUS"
        assert result.context_name == "feature_binding"
        assert len(result.candidates) == 2
        assert result.candidates[0]["value"] == "feature-a"
        assert result.candidates[1]["value"] == "feature-b"
        for candidate in result.candidates:
            assert "source" in candidate
            assert candidate["source"].startswith("explicit_input:")
            assert "value" in candidate
            assert "metadata" in candidate
            assert candidate["metadata"]["resolver"] == "explicit_inputs"


# ============================================================================
# Validation Rule Tests
# ============================================================================


class TestValidationRules:
    """Tests for validation rule enforcement."""

    def test_artifact_exists_rule_valid(self, tmp_path: Path) -> None:
        """artifact_exists rule passes when file exists."""
        artifact_file = tmp_path / "spec.md"
        artifact_file.write_text("# Spec")

        context_type = ContextType(
            type="spec_artifact",
            validation={"artifact_exists": None}
        )

        is_valid, error = validate_binding(str(artifact_file), context_type)

        assert is_valid is True
        assert error is None

    def test_artifact_exists_rule_with_specific_path(self, tmp_path: Path) -> None:
        """artifact_exists rule with specific path in rule_value."""
        expected_file = tmp_path / "expected.md"
        expected_file.write_text("# Expected")

        context_type = ContextType(
            type="spec_artifact",
            validation={"artifact_exists": str(expected_file)}
        )

        is_valid, error = validate_binding("some-value", context_type)

        assert is_valid is True

    def test_artifact_exists_rule_invalid(self) -> None:
        """artifact_exists rule fails when file doesn't exist."""
        context_type = ContextType(
            type="spec_artifact",
            validation={"artifact_exists": None}
        )

        is_valid, error = validate_binding("/nonexistent/path.md", context_type)

        assert is_valid is False
        assert "artifact_exists" in error
        assert "/nonexistent/path.md" in error

    def test_path_exists_rule_valid(self, tmp_path: Path) -> None:
        """path_exists rule passes when directory exists."""
        context_type = ContextType(
            type="work_dir",
            validation={"path_exists": None}
        )

        is_valid, error = validate_binding(str(tmp_path), context_type)

        assert is_valid is True
        assert error is None

    def test_path_exists_rule_invalid(self) -> None:
        """path_exists rule fails when directory doesn't exist."""
        context_type = ContextType(
            type="work_dir",
            validation={"path_exists": None}
        )

        is_valid, error = validate_binding("/nonexistent/directory", context_type)

        assert is_valid is False
        assert "path_exists" in error

    def test_slug_format_rule_valid(self) -> None:
        """slug_format rule passes when value matches pattern."""
        context_type = ContextType(
            type="feature_slug",
            validation={"slug_format": r"[a-z0-9\-]+"}
        )

        is_valid, error = validate_binding("feature-123", context_type)

        assert is_valid is True
        assert error is None

    def test_slug_format_rule_invalid(self) -> None:
        """slug_format rule fails when value doesn't match pattern."""
        context_type = ContextType(
            type="feature_slug",
            validation={"slug_format": r"^[a-z0-9\-]+$"}
        )

        is_valid, error = validate_binding("FEATURE_123", context_type)

        assert is_valid is False
        assert "slug_format" in error
        assert "FEATURE_123" in error

    def test_combined_validation_rules(self, tmp_path: Path) -> None:
        """Multiple rules on single context must all pass."""
        artifact_file = tmp_path / "spec.md"
        artifact_file.write_text("# Spec")

        context_type = ContextType(
            type="spec_artifact",
            validation={
                "artifact_exists": None,
                "slug_format": r".+\.md$"  # Match any path ending in .md
            }
        )

        is_valid, error = validate_binding(str(artifact_file), context_type)

        assert is_valid is True


# ============================================================================
# Independent Resolver Unit Tests (T010 Implementation)
# ============================================================================


class TestExplicitInputResolver:
    """Direct unit tests for ExplicitInputResolver (Resolver 1)."""

    def test_resolve_with_explicit_value(self) -> None:
        """Resolver returns value when explicitly provided."""
        available_bindings = {
            "explicit_inputs": {"feature_binding": "explicit-value"}
        }

        candidates = _resolve_explicit_inputs("feature_binding", available_bindings)

        assert len(candidates) == 1
        assert candidates[0]["value"] == "explicit-value"
        assert candidates[0]["source"] == "explicit_input:feature_binding"
        assert candidates[0]["metadata"]["resolver"] == "explicit_inputs"
        assert candidates[0]["metadata"]["precedence"] == 1

    def test_resolve_with_list_input_creates_multiple_candidates(self) -> None:
        """Resolver treats list input as multiple candidates (ambiguous)."""
        available_bindings = {
            "explicit_inputs": {"feature_binding": ["feature-a", "feature-b"]}
        }

        candidates = _resolve_explicit_inputs("feature_binding", available_bindings)

        assert len(candidates) == 2
        assert candidates[0]["value"] == "feature-a"
        assert candidates[1]["value"] == "feature-b"
        assert candidates[0]["source"] == "explicit_input:feature_binding[0]"
        assert candidates[1]["source"] == "explicit_input:feature_binding[1]"
        assert candidates[0]["metadata"]["is_list"] is True
        assert candidates[0]["metadata"]["index"] == 0

    def test_resolve_with_tuple_input_creates_multiple_candidates(self) -> None:
        """Resolver treats tuple input as multiple candidates (ambiguous)."""
        available_bindings = {
            "explicit_inputs": {"feature_binding": ("feature-a", "feature-b")}
        }

        candidates = _resolve_explicit_inputs("feature_binding", available_bindings)

        assert len(candidates) == 2
        assert candidates[0]["value"] == "feature-a"
        assert candidates[1]["value"] == "feature-b"

    def test_resolve_missing_context_returns_empty(self) -> None:
        """Resolver returns empty list when context not in explicit inputs."""
        available_bindings = {
            "explicit_inputs": {"other_context": "value"}
        }

        candidates = _resolve_explicit_inputs("feature_binding", available_bindings)

        assert len(candidates) == 0

    def test_resolve_with_none_explicit_inputs(self) -> None:
        """Resolver handles missing explicit_inputs key."""
        available_bindings = {}

        candidates = _resolve_explicit_inputs("feature_binding", available_bindings)

        assert len(candidates) == 0

    def test_resolve_with_non_dict_explicit_inputs(self) -> None:
        """Resolver handles non-dict explicit_inputs gracefully."""
        available_bindings = {"explicit_inputs": "not a dict"}

        candidates = _resolve_explicit_inputs("feature_binding", available_bindings)

        assert len(candidates) == 0


class TestContextLedgerResolver:
    """Direct unit tests for ContextLedgerResolver (Resolver 2)."""

    def test_resolve_with_ledger_binding(self) -> None:
        """Resolver returns prior binding from ledger."""
        available_bindings = {
            "ledger": {"feature_binding": {"value": "ledger-value", "validation_status": "valid"}}
        }

        candidates = _resolve_ledger_bindings("feature_binding", available_bindings)

        assert len(candidates) == 1
        assert candidates[0]["value"] == "ledger-value"
        assert candidates[0]["source"] == "ledger:feature_binding"
        assert candidates[0]["metadata"]["resolver"] == "context_ledger"
        assert candidates[0]["metadata"]["precedence"] == 2
        assert candidates[0]["metadata"]["validation_status"] == "valid"

    def test_resolve_with_simple_ledger_value(self) -> None:
        """Resolver handles non-dict ledger values."""
        available_bindings = {
            "ledger": {"feature_binding": "simple-value"}
        }

        candidates = _resolve_ledger_bindings("feature_binding", available_bindings)

        assert len(candidates) == 1
        assert candidates[0]["value"] == "simple-value"
        assert candidates[0]["metadata"]["validation_status"] == "unknown"

    def test_resolve_missing_context_returns_empty(self) -> None:
        """Resolver returns empty list when context not in ledger."""
        available_bindings = {
            "ledger": {"other_context": "value"}
        }

        candidates = _resolve_ledger_bindings("feature_binding", available_bindings)

        assert len(candidates) == 0

    def test_resolve_with_none_ledger(self) -> None:
        """Resolver handles missing ledger key."""
        available_bindings = {}

        candidates = _resolve_ledger_bindings("feature_binding", available_bindings)

        assert len(candidates) == 0

    def test_resolve_with_non_dict_ledger(self) -> None:
        """Resolver handles non-dict ledger gracefully."""
        available_bindings = {"ledger": "not a dict"}

        candidates = _resolve_ledger_bindings("feature_binding", available_bindings)

        assert len(candidates) == 0


class TestMissionMetadataResolver:
    """Direct unit tests for MissionMetadataResolver (Resolver 3)."""

    def test_resolve_project_uuid(self) -> None:
        """Resolver retrieves project_uuid from mission metadata."""
        available_bindings = {
            "mission_metadata": {
                "project_uuid": "proj-123",
                "feature_slug": "feature-x",
                "target_branch": "main"
            }
        }

        candidates = _resolve_mission_metadata("project_uuid", available_bindings)

        assert len(candidates) == 1
        assert candidates[0]["value"] == "proj-123"
        assert candidates[0]["source"] == "mission_metadata:project_uuid"
        assert candidates[0]["metadata"]["field"] == "project_uuid"

    def test_resolve_feature_slug(self) -> None:
        """Resolver retrieves feature_slug from mission metadata."""
        available_bindings = {
            "mission_metadata": {"feature_slug": "feature-x"}
        }

        candidates = _resolve_mission_metadata("feature_slug", available_bindings)

        assert len(candidates) == 1
        assert candidates[0]["value"] == "feature-x"

    def test_resolve_target_branch_alias(self) -> None:
        """Resolver handles 'branch' as alias for 'target_branch'."""
        available_bindings = {
            "mission_metadata": {"target_branch": "develop"}
        }

        candidates = _resolve_mission_metadata("branch", available_bindings)

        assert len(candidates) == 1
        assert candidates[0]["value"] == "develop"

    def test_resolve_missing_context_returns_empty(self) -> None:
        """Resolver returns empty list when context not mapped."""
        available_bindings = {
            "mission_metadata": {"other_field": "value"}
        }

        candidates = _resolve_mission_metadata("unmapped_context", available_bindings)

        assert len(candidates) == 0

    def test_resolve_with_none_metadata(self) -> None:
        """Resolver handles missing mission_metadata key."""
        available_bindings = {}

        candidates = _resolve_mission_metadata("project_uuid", available_bindings)

        assert len(candidates) == 0

    def test_resolve_with_non_dict_metadata(self) -> None:
        """Resolver handles non-dict mission_metadata gracefully."""
        available_bindings = {"mission_metadata": "not a dict"}

        candidates = _resolve_mission_metadata("project_uuid", available_bindings)

        assert len(candidates) == 0


class TestLocalDiscoveryResolver:
    """Direct unit tests for LocalDiscoveryResolver (Resolver 4)."""

    def test_resolve_with_discovery_hint(self) -> None:
        """Resolver finds context from discovery hints."""
        contract_type = ContextType(type="spec_artifact")
        available_bindings = {
            "discovery_hints": {"spec_artifact": "/path/to/spec.md"}
        }

        candidates = _resolve_local_discovery(
            "spec_artifact",
            contract_type,
            available_bindings,
            Path.cwd()
        )

        assert len(candidates) >= 1
        assert any(c["value"] == "/path/to/spec.md" for c in candidates)

    def test_resolve_artifact_file_from_filesystem(self, tmp_path: Path) -> None:
        """Resolver finds artifact files in filesystem."""
        spec_md = tmp_path / "spec.md"
        spec_md.write_text("# Spec")

        contract_type = ContextType(type="spec_artifact")
        available_bindings = {}

        candidates = _resolve_local_discovery(
            "spec_artifact",
            contract_type,
            available_bindings,
            tmp_path
        )

        assert len(candidates) == 1
        assert str(spec_md) in candidates[0]["value"]
        assert candidates[0]["metadata"]["type"] == "artifact_file"

    def test_resolve_multiple_artifacts_ambiguous(self, tmp_path: Path) -> None:
        """Resolver detects multiple matching artifacts (ambiguous)."""
        spec_md = tmp_path / "spec.md"
        spec_yaml = tmp_path / "spec.yaml"
        spec_md.write_text("# Spec")
        spec_yaml.write_text("# Spec YAML")

        contract_type = ContextType(type="spec_artifact")
        available_bindings = {}

        candidates = _resolve_local_discovery(
            "spec_artifact",
            contract_type,
            available_bindings,
            tmp_path
        )

        assert len(candidates) == 2
        values = [c["value"] for c in candidates]
        assert str(spec_md) in values
        assert str(spec_yaml) in values

    def test_resolve_git_branch_from_state(self) -> None:
        """Resolver retrieves git branch from git_state."""
        contract_type = ContextType(type="target_branch")
        available_bindings = {
            "git_state": {"branch": "feature/my-feature"}
        }

        candidates = _resolve_local_discovery(
            "target_branch",
            contract_type,
            available_bindings,
            Path.cwd()
        )

        assert len(candidates) == 1
        assert candidates[0]["value"] == "feature/my-feature"
        assert candidates[0]["metadata"]["type"] == "git_state"

    def test_resolve_missing_context_returns_empty(self, tmp_path: Path) -> None:
        """Resolver returns empty list when context not discoverable."""
        contract_type = ContextType(type="unknown_artifact")
        available_bindings = {}

        candidates = _resolve_local_discovery(
            "unknown_artifact",
            contract_type,
            available_bindings,
            tmp_path
        )

        assert len(candidates) == 0

    def test_resolve_hint_takes_precedence_over_files(self, tmp_path: Path) -> None:
        """Resolver includes both hints and files (multiple candidates)."""
        spec_md = tmp_path / "spec.md"
        spec_md.write_text("# Spec")

        contract_type = ContextType(type="spec_artifact")
        available_bindings = {
            "discovery_hints": {"spec_artifact": "/explicit/hint"}
        }

        candidates = _resolve_local_discovery(
            "spec_artifact",
            contract_type,
            available_bindings,
            tmp_path
        )

        assert len(candidates) >= 2
        values = [c["value"] for c in candidates]
        assert "/explicit/hint" in values


# ============================================================================
# Regression Tests for Validation Bugs
# ============================================================================


class TestValidationBugRegressions:
    """Regression tests for validation and resolver bugs."""

    def test_artifact_exists_rule_with_boolean_true(self, tmp_path: Path) -> None:
        """Bug 1: Boolean True in artifact_exists must validate the bound value, not Path('True')."""
        artifact_file = tmp_path / "spec.md"
        artifact_file.write_text("# Spec")

        context_type = ContextType(
            type="spec_artifact",
            validation={"artifact_exists": True}
        )

        is_valid, error = validate_binding(str(artifact_file), context_type)

        assert is_valid is True, f"Expected valid but got error: {error}"
        assert error is None

    def test_path_exists_rule_with_boolean_true(self, tmp_path: Path) -> None:
        """Bug 1: Boolean True in path_exists must validate the bound value, not Path('True')."""
        contracts_dir = tmp_path / "contracts"
        contracts_dir.mkdir()

        context_type = ContextType(
            type="contracts_dir",
            validation={"path_exists": True}
        )

        is_valid, error = validate_binding(str(contracts_dir), context_type)

        assert is_valid is True, f"Expected valid but got error: {error}"
        assert error is None

    def test_artifact_exists_rule_with_boolean_false(self) -> None:
        """Bug 1: Boolean False in artifact_exists must skip validation entirely."""
        context_type = ContextType(
            type="spec_artifact",
            validation={"artifact_exists": False}
        )

        # Should pass regardless — the rule is disabled
        is_valid, error = validate_binding("/nonexistent/path.md", context_type)

        assert is_valid is True
        assert error is None

    def test_resolve_context_with_malformed_metadata(self) -> None:
        """Bug 2: Non-dict mission_metadata must not crash with AttributeError."""
        contract_type = ContextType(type="custom_ctx", resolver_ref="test:resolver")
        available_bindings = {
            "mission_metadata": "not_a_dict",
            "fallback_resolvers": {"custom_ctx": "fallback-value"}
        }

        # Should not raise AttributeError; returns CONTEXT_MISSING because
        # fallback resolvers are disabled when metadata is malformed
        result = resolve_context(
            "custom_ctx",
            contract_type,
            available_bindings,
            ContextTypeRegistry()
        )

        assert isinstance(result, RemediationPayload)
        assert result.error_code == "CONTEXT_MISSING"

    def test_registry_isolation(self) -> None:
        """Bug 3: Separate registries must not share ContextType instances."""
        registry1 = ContextTypeRegistry()
        registry2 = ContextTypeRegistry()

        type1 = registry1.get_builtin_type("spec_artifact")
        type2 = registry2.get_builtin_type("spec_artifact")

        assert type1 is not type2, "Registries share the same ContextType object"

    def test_unknown_validation_rule_fails(self) -> None:
        """Bug 4: Unknown validation rules must fail with descriptive error."""
        context_type = ContextType(
            type="test_context",
            validation={"typo_rule": True}
        )

        is_valid, error = validate_binding("some-value", context_type)

        assert is_valid is False
        assert "Unknown validation rule" in error
        assert "typo_rule" in error
        assert "artifact_exists" in error
        assert "path_exists" in error
        assert "slug_format" in error

    def test_schema_and_engine_validate_binding_agree(self, tmp_path: Path) -> None:
        """ContextType.validate_binding() must produce identical results to engine validate_binding()."""
        artifact_file = tmp_path / "spec.md"
        artifact_file.write_text("# Spec")

        cases = [
            # (value, context_type) — tests boolean artifact_exists, path_exists, unknown rule
            (str(artifact_file), ContextType(type="spec_artifact", validation={"artifact_exists": True})),
            (str(tmp_path), ContextType(type="contracts_dir", validation={"path_exists": True})),
            ("/nonexistent", ContextType(type="x", validation={"artifact_exists": True})),
            ("some-val", ContextType(type="x", validation={"bogus_rule": True})),
        ]

        for value, ctx_type in cases:
            engine_result = validate_binding(value, ctx_type)
            schema_result = ctx_type.validate_binding(value)
            assert engine_result == schema_result, (
                f"Mismatch for value={value!r}, validation={ctx_type.validation}: "
                f"engine={engine_result}, schema={schema_result}"
            )

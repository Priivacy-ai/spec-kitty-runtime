"""Tests for step context contracts (WP01)."""

import json
from datetime import datetime

import pytest
from spec_kitty_runtime.contracts import RemediationPayload
from spec_kitty_runtime.schema import ContextType, ContextTypeRegistry, StepContextContract


class TestContextType:
    """Tests for ContextType model."""

    def test_context_type_minimal(self) -> None:
        """Create minimal ContextType with only name."""
        ctx = ContextType(type="feature_binding")
        assert ctx.type == "feature_binding"
        assert ctx.deterministic is True
        assert ctx.cardinality == "one"
        assert ctx.validation is None
        assert ctx.resolver_ref is None

    def test_context_type_full(self) -> None:
        """Create ContextType with all fields."""
        ctx = ContextType(
            type="spec_artifact",
            deterministic=True,
            cardinality="one",
            validation={"artifact_exists": True},
            resolver_ref="custom.resolvers:resolve_spec"
        )
        assert ctx.type == "spec_artifact"
        assert ctx.deterministic is True
        assert ctx.cardinality == "one"
        assert ctx.validation == {"artifact_exists": True}
        assert ctx.resolver_ref == "custom.resolvers:resolve_spec"

    def test_context_type_with_many_cardinality(self) -> None:
        """ContextType with cardinality 'many'."""
        ctx = ContextType(type="wp_binding", cardinality="many")
        assert ctx.cardinality == "many"

    def test_context_type_frozen(self) -> None:
        """ContextType is immutable (frozen)."""
        ctx = ContextType(type="test")
        with pytest.raises(Exception):  # Pydantic FrozenModel raises
            ctx.type = "modified"  # type: ignore


class TestContextTypeRegistry:
    """Tests for ContextTypeRegistry."""

    def test_registry_has_8_builtin_types(self) -> None:
        """Registry initializes with 8 V1 baseline types."""
        registry = ContextTypeRegistry()
        all_types = registry.get_all_types()
        assert len(all_types) == 8
        assert "feature_binding" in all_types
        assert "spec_artifact" in all_types
        assert "plan_artifact" in all_types
        assert "tasks_artifact" in all_types
        assert "wp_binding" in all_types
        assert "target_branch" in all_types
        assert "contracts_dir" in all_types
        assert "research_artifact" in all_types

    def test_get_builtin_type(self) -> None:
        """Retrieve a built-in type by name."""
        registry = ContextTypeRegistry()
        ctx = registry.get_builtin_type("feature_binding")
        assert ctx.type == "feature_binding"
        assert ctx.deterministic is True

    def test_get_builtin_type_unknown(self) -> None:
        """Requesting unknown type raises ValueError."""
        registry = ContextTypeRegistry()
        with pytest.raises(ValueError, match="Unknown context type"):
            registry.get_builtin_type("unknown_type")

    def test_is_registered(self) -> None:
        """Check if type is registered."""
        registry = ContextTypeRegistry()
        assert registry.is_registered("feature_binding")
        assert registry.is_registered("spec_artifact")
        assert not registry.is_registered("unknown_type")

    def test_register_custom_type(self) -> None:
        """Register and retrieve custom type."""
        registry = ContextTypeRegistry()
        custom = ContextType(type="custom_analysis", deterministic=False)
        registry.register_custom_type(custom)
        assert registry.is_registered("custom_analysis")
        assert registry.get_builtin_type("custom_analysis") == custom

    def test_registry_baseline_types_have_correct_cardinality(self) -> None:
        """V1 baseline types have correct cardinality settings."""
        registry = ContextTypeRegistry()

        # Most types have cardinality "one"
        assert registry.get_builtin_type("feature_binding").cardinality == "one"
        assert registry.get_builtin_type("spec_artifact").cardinality == "one"
        assert registry.get_builtin_type("plan_artifact").cardinality == "one"

        # wp_binding has cardinality "many"
        assert registry.get_builtin_type("wp_binding").cardinality == "many"

    def test_registry_baseline_types_have_validation_rules(self) -> None:
        """V1 baseline artifact types have validation rules."""
        registry = ContextTypeRegistry()

        # Artifact types have artifact_exists validation
        spec = registry.get_builtin_type("spec_artifact")
        assert spec.validation == {"artifact_exists": True}

        # target_branch has slug_format validation
        branch = registry.get_builtin_type("target_branch")
        assert "slug_format" in branch.validation


class TestStepContextContract:
    """Tests for StepContextContract model."""

    def test_contract_minimal(self) -> None:
        """Create minimal contract with only requires."""
        contract = StepContextContract(
            requires=[ContextType(type="feature_binding")]
        )
        assert len(contract.requires) == 1
        assert len(contract.optional) == 0
        assert len(contract.emits) == 0

    def test_contract_full(self) -> None:
        """Create full contract with requires, optional, and emits."""
        contract = StepContextContract(
            requires=[ContextType(type="feature_binding")],
            optional=[ContextType(type="research_artifact")],
            emits=[ContextType(type="plan_artifact")]
        )
        assert len(contract.requires) == 1
        assert len(contract.optional) == 1
        assert len(contract.emits) == 1

    def test_contract_validate_unknown_type(self) -> None:
        """Contract validation rejects unknown types without resolver_ref."""
        from pydantic import ValidationError
        with pytest.raises(ValidationError) as exc_info:
            contract = StepContextContract(
                requires=[ContextType(type="unknown_type")]
            )
        assert "Unknown context type" in str(exc_info.value)

    def test_contract_validate_unknown_type_with_resolver(self) -> None:
        """Contract accepts unknown type with resolver_ref."""
        contract = StepContextContract(
            requires=[
                ContextType(
                    type="custom_type",
                    resolver_ref="resolvers:custom_resolver"
                )
            ]
        )
        is_valid, errors = contract.validate_contract()
        assert is_valid
        assert len(errors) == 0

    def test_contract_validate_circular_dependency(self) -> None:
        """Contract validation detects circular dependencies (requires + emits same)."""
        contract = StepContextContract(
            requires=[ContextType(type="my_artifact", resolver_ref="test:resolver")],
            emits=[ContextType(type="my_artifact", resolver_ref="test:resolver")]
        )
        is_valid, errors = contract.validate_contract()
        assert not is_valid
        assert any("requires and emits same context" in err for err in errors)

    def test_contract_validate_with_registry(self) -> None:
        """Contract validation uses provided registry."""
        registry = ContextTypeRegistry()
        contract = StepContextContract(
            requires=[ContextType(type="feature_binding")]
        )
        is_valid, errors = contract.validate_contract(registry)
        assert is_valid
        assert len(errors) == 0

    def test_contract_frozen(self) -> None:
        """StepContextContract is immutable."""
        contract = StepContextContract()
        with pytest.raises(Exception):
            contract.requires = [ContextType(type="test")]  # type: ignore


class TestRemediationPayload:
    """Tests for RemediationPayload model."""

    def test_remediation_payload_missing(self) -> None:
        """Factory creates CONTEXT_MISSING payload."""
        payload = RemediationPayload.missing("feature_binding")
        assert payload.error_code == "CONTEXT_MISSING"
        assert payload.context_name == "feature_binding"
        assert payload.candidates == []
        assert "feature_binding" in payload.remediation_hint
        assert isinstance(payload.timestamp, datetime)

    def test_remediation_payload_ambiguous(self) -> None:
        """Factory creates CONTEXT_AMBIGUOUS payload."""
        candidates = [
            {"source": "config.yaml", "value": "admin"},
            {"source": "env:ROLE", "value": "user"}
        ]
        payload = RemediationPayload.ambiguous("user_role", candidates)
        assert payload.error_code == "CONTEXT_AMBIGUOUS"
        assert payload.context_name == "user_role"
        assert len(payload.candidates) == 2
        assert "Select one" in payload.remediation_hint
        assert "config.yaml" in payload.remediation_hint

    def test_remediation_payload_invalid(self) -> None:
        """Factory creates CONTEXT_INVALID payload."""
        candidates = [{"path": "/missing/spec.md"}]
        failures = ["artifact_exists at /missing/spec.md"]
        payload = RemediationPayload.invalid(
            "spec_artifact",
            candidates,
            failures
        )
        assert payload.error_code == "CONTEXT_INVALID"
        assert payload.context_name == "spec_artifact"
        assert len(payload.candidates) == 1
        assert all(fail in payload.remediation_hint for fail in failures)

    def test_remediation_payload_with_metadata(self) -> None:
        """Payloads include resolver metadata."""
        metadata = {
            "resolver": "offline_resolver",
            "checked_locations": [".spec-kitty/context.yaml"]
        }
        payload = RemediationPayload.missing(
            "feature_binding",
            metadata
        )
        assert payload.resolver_metadata == metadata

    def test_remediation_payload_serializable(self) -> None:
        """Payloads serialize to JSON deterministically."""
        payload = RemediationPayload.missing(
            "feature_binding",
            {"key": "value"}
        )
        # Should be JSON serializable
        json_str = payload.model_dump_json()
        assert isinstance(json_str, str)
        # And deserializable
        data = json.loads(json_str)
        assert data["error_code"] == "CONTEXT_MISSING"
        assert data["context_name"] == "feature_binding"

    def test_remediation_payload_frozen(self) -> None:
        """RemediationPayload is immutable."""
        payload = RemediationPayload.missing("test")
        with pytest.raises(Exception):
            payload.error_code = "CONTEXT_INVALID"  # type: ignore


class TestContractIntegration:
    """Integration tests for contracts with real patterns."""

    def test_software_dev_mission_contracts(self) -> None:
        """Real software-dev mission contracts validate."""
        registry = ContextTypeRegistry()

        # Research step
        research_contract = StepContextContract(
            requires=[ContextType(type="feature_binding")],
            emits=[ContextType(type="research_artifact")]
        )
        is_valid, errors = research_contract.validate_contract(registry)
        assert is_valid, f"Research contract validation failed: {errors}"

        # Design step (uses research output)
        design_contract = StepContextContract(
            requires=[
                ContextType(type="feature_binding"),
                ContextType(
                    type="research_artifact",
                    validation={"artifact_exists": True}
                )
            ],
            emits=[
                ContextType(type="plan_artifact"),
                ContextType(type="spec_artifact")
            ]
        )
        is_valid, errors = design_contract.validate_contract(registry)
        assert is_valid, f"Design contract validation failed: {errors}"

    def test_error_scenario_missing_context(self) -> None:
        """Error scenario: missing required context."""
        payload = RemediationPayload.missing("plan_artifact")
        assert payload.error_code == "CONTEXT_MISSING"
        assert payload.candidates == []
        assert "plan_artifact" in payload.remediation_hint

    def test_error_scenario_ambiguous_context(self) -> None:
        """Error scenario: ambiguous context resolution."""
        candidates = [
            {"source": "mission_spec.yaml", "branch": "main"},
            {"source": "runtime_input", "branch": "feature-x"}
        ]
        payload = RemediationPayload.ambiguous("target_branch", candidates)
        assert payload.error_code == "CONTEXT_AMBIGUOUS"
        assert len(payload.candidates) == 2
        # Hint should guide operator to select one
        assert "Select one" in payload.remediation_hint

    def test_error_scenario_invalid_context(self) -> None:
        """Error scenario: context fails validation."""
        payload = RemediationPayload.invalid(
            "spec_artifact",
            [{"path": "/designs/missing.md"}],
            ["artifact_exists at /designs/missing.md"]
        )
        assert payload.error_code == "CONTEXT_INVALID"
        assert "artifact_exists" in payload.remediation_hint
        assert "/designs/missing.md" in payload.remediation_hint


class TestYAMLExamples:
    """Tests for YAML example files."""

    def test_example_contracts_yaml_exists(self) -> None:
        """Example contracts YAML file exists."""
        from pathlib import Path
        path = Path(__file__).parent / "fixtures" / "example_contracts.yaml"
        assert path.exists(), f"Example contracts YAML not found at {path}"

    def test_example_missions_yaml_exists(self) -> None:
        """Example missions YAML file exists."""
        from pathlib import Path
        path = Path(__file__).parent / "fixtures" / "example_missions.yaml"
        assert path.exists(), f"Example missions YAML not found at {path}"

    def test_example_contracts_yaml_parseable(self) -> None:
        """Example contracts YAML parses without errors."""
        import yaml
        from pathlib import Path
        path = Path(__file__).parent / "fixtures" / "example_contracts.yaml"
        with open(path) as f:
            data = yaml.safe_load(f)
        assert isinstance(data, dict)

    def test_example_missions_yaml_parseable(self) -> None:
        """Example missions YAML parses without errors (supports multiple documents)."""
        import yaml
        from pathlib import Path
        path = Path(__file__).parent / "fixtures" / "example_missions.yaml"
        with open(path) as f:
            # safe_load_all to handle multiple documents separated by ---
            documents = list(yaml.safe_load_all(f))
        # Should contain multiple mission documents
        assert len(documents) > 0
        # Each should be a dict
        for doc in documents:
            assert isinstance(doc, dict)

# Step Context Contracts (V1)

## Overview

Step context contracts define the context bindings required, optional, and emitted by mission steps. They enable deterministic evaluation of step preconditions and allow the runtime to provide structured remediation when context is missing, ambiguous, or invalid.

This document is the authoritative reference for spec-kitty 2.x and other consumers building on top of spec-kitty-runtime.

## Why Context Contracts?

Mission steps often depend on context from prior steps (e.g., research findings, design documents) or from the execution environment (feature branch, project settings). Without explicit contracts:

- **Ambiguity**: Unclear what each step needs to run
- **Silent failures**: Missing context silently skipped rather than reported
- **Unfixable errors**: No guidance on how to resolve issues
- **Non-determinism**: Context resolution depends on implementation details

Contracts solve these problems by:

1. **Explicit declaration**: Each step declares what it needs
2. **Structured validation**: Context is validated against declared rules
3. **Deterministic resolution**: Local-first, offline context resolution (no network)
4. **Actionable remediation**: Specific, executable guidance when resolution fails

## Quick Start

Here's a minimal example:

```yaml
mission:
  key: example-mission
  name: Example Mission

steps:
  - id: research
    title: "Research Phase"
    context:
      requires:
        - type: feature_binding
          deterministic: true
          cardinality: one
      emits:
        - type: research_artifact
          cardinality: one

  - id: implement
    title: "Implementation Phase"
    context:
      requires:
        - type: feature_binding
          deterministic: true
        - type: research_artifact
          deterministic: true
          validation:
            artifact_exists: true
```

## Full Reference

### StepContextContract

A contract attached to a mission step with three sections:

```python
class StepContextContract(BaseModel):
    requires: list[ContextType]   # MUST resolve before execution
    optional: list[ContextType]   # May enrich but not blocking
    emits: list[ContextType]      # Produced on completion
```

### ContextType

Describes a single context requirement:

```python
class ContextType(BaseModel):
    name: str                           # Required: context type name
    deterministic: bool = True          # Is resolution deterministic (local)?
    cardinality: Literal["one", "many"] = "one"  # Expected binding count
    validation: dict[str, Any] | None   # Validation rules (type-specific)
    resolver_ref: str | None            # Custom resolver for unknown types
```

**Fields**:

- **name**: Identifier for the context type. Must be registered in `ContextTypeRegistry` or have `resolver_ref`.
- **deterministic**: Whether this context can be resolved deterministically (local filesystem, environment, etc.). Non-deterministic contexts require custom resolvers.
- **cardinality**:
  - `"one"`: Exactly one binding expected
  - `"many"`: Multiple bindings expected (e.g., work packages)
- **validation**: Type-specific validation rules:
  - `artifact_exists: bool` – Check if artifact file exists
  - `path_exists: bool` – Check if filesystem path exists
  - `slug_format: str` – Regex pattern for slug validation (e.g., `"[a-z0-9-]+"`)
  - Custom key-value pairs for custom validators
- **resolver_ref**: Reference to custom resolver for unknown types. Format: `"module:function"` or `"class:method"`.

## V1 Baseline Context Types

The runtime includes 8 built-in context types (V1 baseline):

### 1. feature_binding
Identifies the feature being worked on.

- **Cardinality**: `one`
- **Deterministic**: `true`
- **Validation**: None
- **Use case**: Entry point for most missions; identifies the feature key

### 2. spec_artifact
Specification or requirements document for the feature.

- **Cardinality**: `one`
- **Deterministic**: `true`
- **Validation**: `artifact_exists: true`
- **Use case**: Design and planning steps that reference formal specs

### 3. plan_artifact
Design plan or architecture document.

- **Cardinality**: `one`
- **Deterministic**: `true`
- **Validation**: `artifact_exists: true`
- **Use case**: Implementation steps that follow a design plan

### 4. tasks_artifact
List of implementation tasks or work breakdown.

- **Cardinality**: `one`
- **Deterministic**: `true`
- **Validation**: `artifact_exists: true`
- **Use case**: Task decomposition and work package generation

### 5. wp_binding
Work package identifier(s).

- **Cardinality**: `many` (multiple bindings)
- **Deterministic**: `true`
- **Validation**: None
- **Use case**: Tracks multiple work packages from task generation

### 6. target_branch
Git branch target for the feature.

- **Cardinality**: `one`
- **Deterministic**: `true`
- **Validation**: `slug_format: "[a-z0-9-]+"`
- **Use case**: Branch-specific logic and validation

### 7. contracts_dir
Directory containing mission contracts.

- **Cardinality**: `one`
- **Deterministic**: `true`
- **Validation**: `path_exists: true`
- **Use case**: Access to shared contract definitions or templates

### 8. research_artifact
Research findings or investigation results.

- **Cardinality**: `one`
- **Deterministic**: `true`
- **Validation**: `artifact_exists: true`
- **Use case**: Evidence-based decision making and knowledge capture

## How to Declare Contracts in Mission YAML

Add a `context` section to each step:

```yaml
steps:
  - id: my_step
    title: "Step Title"
    context:
      requires:
        - type: feature_binding
          deterministic: true
      optional:
        - type: research_artifact
          validation:
            artifact_exists: true
      emits:
        - type: plan_artifact
          cardinality: one
```

## Resolver Precedence (Local-First, Offline)

Context resolution follows this precedence chain (in order):

1. **Explicit step/run inputs**: Values provided directly to mission run
2. **Prior ContextLedger bindings**: From completed prior steps
3. **Mission run metadata**: From run snapshot (branch, commit, etc.)
4. **Deterministic local discovery**: Filesystem scanning, environment variables, git state
5. **Step-specific fallbacks** (only with explicit policy): Hardcoded defaults

**Important**: Network/remote registries are explicitly OUT of the default chain. Custom resolvers can add network-based resolution, but they must be explicitly registered.

## RemediationPayload Structure

When context resolution fails, the runtime emits a structured remediation payload:

```python
class RemediationPayload(BaseModel):
    error_code: Literal["CONTEXT_MISSING", "CONTEXT_AMBIGUOUS", "CONTEXT_INVALID"]
    context_name: str
    candidates: list[dict[str, Any]]          # Possible bindings
    remediation_hint: str                      # Actionable suggestion
    resolver_metadata: dict[str, Any]          # Debug info
    timestamp: datetime
```

### Error Codes

#### CONTEXT_MISSING

**When**: No bindings found for a required context.

**Example**:
```json
{
  "error_code": "CONTEXT_MISSING",
  "context_name": "feature_binding",
  "candidates": [],
  "remediation_hint": "Resolve missing context: --context=feature_binding --source=/path/to/spec",
  "resolver_metadata": {
    "resolver": "offline_resolver",
    "checked_locations": [".spec-kitty/context.yaml", "env:FEATURE_KEY"]
  }
}
```

**Operator action**: Provide the missing context using the suggested command.

#### CONTEXT_AMBIGUOUS

**When**: Multiple equally valid bindings found.

**Example**:
```json
{
  "error_code": "CONTEXT_AMBIGUOUS",
  "context_name": "user_role",
  "candidates": [
    {"source": "config.yaml", "value": "reviewer"},
    {"source": "env:USER_ROLE", "value": "admin"}
  ],
  "remediation_hint": "Select one: --context=user_role --source=config.yaml or --context=user_role --source=env:USER_ROLE",
  "resolver_metadata": {}
}
```

**Operator action**: Select one of the candidates or provide explicit override.

#### CONTEXT_INVALID

**When**: Binding(s) found but fail declared validation rules.

**Example**:
```json
{
  "error_code": "CONTEXT_INVALID",
  "context_name": "spec_artifact",
  "candidates": [
    {"path": "/missing/spec.md"}
  ],
  "remediation_hint": "Context value must pass validation: artifact_exists at /missing/spec.md",
  "resolver_metadata": {
    "validation_rule": "artifact_exists",
    "validation_target": "/missing/spec.md"
  }
}
```

**Operator action**: Fix the underlying issue (create the artifact, check file path) or provide an alternative context source.

## Integration Guide: spec-kitty 2.x Parser

This section guides spec-kitty 2.x teams on integrating step context contracts.

### 1. Parse Contracts from Mission YAML

```python
import yaml
from spec_kitty_runtime.schema import StepContextContract

with open("missions/software-dev/mission.yaml") as f:
    mission_data = yaml.safe_load(f)

for step in mission_data["steps"]:
    if "context" in step:
        contract = StepContextContract.model_validate(step["context"])
        # Use contract for validation and planning
```

### 2. Evaluate Transition Gates

Before transitioning to a step, check if all required contexts can be resolved:

```python
from spec_kitty_runtime.contracts import RemediationPayload

def can_transition_to_step(step_id: str, available_contexts: dict) -> tuple[bool, RemediationPayload | None]:
    contract = get_contract_for_step(step_id)

    for required_ctx in contract.requires:
        if required_ctx.name not in available_contexts:
            return False, RemediationPayload.missing(required_ctx.name)

    return True, None
```

### 3. Handle Remediation Payloads

```python
def handle_remediation(payload: RemediationPayload, operator_input: str):
    if payload.error_code == "CONTEXT_MISSING":
        # Prompt operator to provide the missing context
        print(f"Missing: {payload.remediation_hint}")

    elif payload.error_code == "CONTEXT_AMBIGUOUS":
        # Show candidates and ask operator to select
        print(f"Ambiguous: {payload.remediation_hint}")
        for i, candidate in enumerate(payload.candidates, 1):
            print(f"  {i}. {candidate['source']}")

    elif payload.error_code == "CONTEXT_INVALID":
        # Suggest fixing the validation error
        print(f"Invalid: {payload.remediation_hint}")
        print(f"Metadata: {payload.resolver_metadata}")
```

### 4. Use Remediation Hints for Operator Guidance

Remediation hints are designed to be:

- **Actionable**: Specific steps to resolve the issue
- **Executable**: Commands or suggestions operators can immediately use
- **Contextual**: Include specific paths, values, or choices relevant to the failure

Example hints:
- Missing: `resolve --context=feature_binding --source=/path/to/spec.md`
- Ambiguous: `select one: --context=user_role --source=config.yaml or --context=user_role --source=env`
- Invalid: `context value must pass validation: artifact_exists at /path/to/artifact`

## Edge Cases and Advanced Topics

### Circular Dependencies

A step cannot require and emit the same context in the same step:

```yaml
# ❌ INVALID: Circular in same step
steps:
  - id: bad_step
    context:
      requires:
        - type: my_artifact
      emits:
        - type: my_artifact  # ERROR: can't require and emit same context
```

The contract validator will reject this.

### Multi-Step Flows

Contexts emitted by one step typically feed into requirements of the next:

```yaml
# ✓ VALID: Linear flow
steps:
  - id: step1
    context:
      emits:
        - type: research_artifact

  - id: step2
    context:
      requires:
        - type: research_artifact  # Consumes step1's emit
      emits:
        - type: plan_artifact

  - id: step3
    context:
      requires:
        - type: plan_artifact      # Consumes step2's emit
```

### Custom Context Types

To use a context type not in the V1 baseline, provide a resolver reference:

```yaml
steps:
  - id: custom_step
    context:
      requires:
        - type: custom_analysis
          deterministic: false
          resolver_ref: "my_project.resolvers:resolve_analysis"
```

The resolver function must be registered with the runtime and handle context discovery/validation.

### Validation Rules

Validation rules are type-specific and extensible:

```yaml
context:
  requires:
    - type: feature_binding
      validation:
        slug_format: "^[a-z][a-z0-9-]*$"  # Custom regex
        max_length: 50                       # Custom rule

    - type: spec_artifact
      validation:
        artifact_exists: true
        file_extension: ".md"  # Can add custom rules
```

## Examples

### Example 1: Minimal Software Dev Mission

See `tests/fixtures/example_missions.yaml` (software-dev mission).

**Key patterns**:
- Linear progression: research → design → implement → test → review
- Emits flow into requires of downstream steps
- All contexts deterministically resolvable

### Example 2: Research Investigation Mission

See `tests/fixtures/example_missions.yaml` (research-investigation mission).

**Key patterns**:
- Multiple steps produce research_artifact
- Optional contexts enrich but don't block (contracts_dir)
- Simple cardinality (all "one")

### Example 3: Error Scenarios

See `tests/fixtures/example_missions.yaml` (failure scenario missions).

**Key patterns**:
- Missing context (plan_artifact not available)
- Ambiguous context (feature_binding from multiple sources)
- Invalid context (artifact path doesn't exist)

## Testing and Validation

### Unit Testing Context Contracts

```python
from spec_kitty_runtime.schema import StepContextContract, ContextTypeRegistry

def test_valid_contract():
    contract_data = {
        "requires": [
            {"type": "feature_binding", "deterministic": true}
        ],
        "emits": [
            {"type": "research_artifact", "cardinality": "one"}
        ]
    }
    contract = StepContextContract.model_validate(contract_data)
    is_valid, errors = contract.validate_contract()
    assert is_valid
    assert len(errors) == 0
```

### Integration Testing Context Resolution

```python
from spec_kitty_runtime.contracts import RemediationPayload

def test_missing_context_remediation():
    payload = RemediationPayload.missing("feature_binding")
    assert payload.error_code == "CONTEXT_MISSING"
    assert "feature_binding" in payload.remediation_hint
```

## Version and Compatibility

This document specifies V1 of the context contracts system.

- **Version**: 0.4.0-rc1 (contract-freeze pre-release)
- **Python**: 3.11+
- **Dependencies**: Pydantic 2.0+, PyYAML 6.0+
- **Stability**: Contracts are frozen for V1. Breaking changes require major version bump.

## Related Documentation

- `README.md`: Overall runtime architecture
- `tests/fixtures/example_contracts.yaml`: All contract patterns
- `tests/fixtures/example_missions.yaml`: Real mission examples
- `CHANGELOG.md`: Version history and release notes

## Contact & Questions

For questions or issues with context contracts, open an issue in the spec-kitty-runtime repository or contact the Spec Kitty team.

# WP06: RACI Inference and Override

## Feature ID
`003-raci-inference-override`

## Version
0.4.x (no legacy compat)

## Status
specified

---

## 1. Objective

Extend the runtime with a deterministic RACI (Responsible, Accountable, Consulted, Informed) role model that governs who may act on each mission step and decision. The runtime infers default RACI bindings from step type and mission policy, allows mission authors to override bindings explicitly in YAML, and escalates when a required role cannot be resolved to a concrete actor.

This builds directly on the WP05 decision authority kernel (`engine.py:332-493`), which enforces human-only audit closure and delegation audit trails. WP06 generalises that enforcement into a structured RACI framework that covers all step types, not only audit checkpoints.

The mission owner remains the human final authority in P0. LLMs participate in advisory capacity only (C/I roles). All RACI-governed actions produce auditable records with actor provenance, role justification, and override reasoning when applicable.

---

## 2. Scope

### In scope
- `RACIRoleBinding` and `RACIAssignment` schema for declaring per-step RACI
- `ResolvedRACIBinding` model capturing fully-resolved bindings with provenance
- Deterministic inference engine: step type + mission policy → default RACI assignment
- Explicit override mechanism via `raci:` block in mission YAML step definitions
- P0 invariant validation (A is always human; LLM restricted to C/I)
- Unresolved-role escalation with structured `RACIEscalationPayload`
- Audit record extension: `raci_source`, `override_reason` fields alongside existing `actor_type`, `actor_id`, `authority_role`, `rationale_linkage`
- Integration with WP05 authority kernel (extend, not replace)
- Deterministic test suite (no mocks, no randomness, no network)

### Out of scope
- Auth0 / SAML / SCIM identity provider integration (post-MVP)
- `LLM-as-A` mode (LLM as Accountable actor — post-MVP)
- LLM-as-R for audit decisions (WP05 invariant preserved)
- Remote role registries or network-based actor resolution
- SaaS UI / projection work
- CLI wiring
- New event types in `spec-kitty-events` (reuse existing contracts)

## 2.1 Functional Requirements

- `FR-006`: Runtime MUST resolve a deterministic per-step RACI binding (inferred or explicit), enforce P0 authority invariants (human accountable, LLM advisory-only), and fail closed with auditable escalation when required roles cannot be resolved.

---

## 3. Requirements

### 3.1 Schema

#### `RACIRoleBinding`

A single actor-role binding within a RACI assignment.

```python
class RACIRoleBinding(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    actor_type: Literal["human", "llm", "service"]
    actor_id: str | None = None  # Resolved at runtime; None = resolve from inputs
```

**Validation rules:**
- `actor_type` must be one of `"human"`, `"llm"`, `"service"`
- `actor_id` is optional at declaration time; resolved at runtime from `inputs` dict
- Unknown `actor_type` values raise `ValidationError` (Pydantic strict, no passthrough)

#### `RACIAssignment`

Per-step RACI role assignment, declarable in mission YAML or inferred at runtime.

```python
class RACIAssignment(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    responsible: RACIRoleBinding
    accountable: RACIRoleBinding
    consulted: list[RACIRoleBinding] = Field(default_factory=list)
    informed: list[RACIRoleBinding] = Field(default_factory=list)
```

**Validation rules:**
- `responsible` and `accountable` are required (no defaults)
- `accountable.actor_type` must be `"human"` — enforced at validation time (P0 invariant)
- `consulted` and `informed` are optional lists; LLM actors are permitted in these roles
- If `accountable.actor_type != "human"`, raise `MissionRuntimeError` with message: `"P0 invariant: accountable role must be human"`

#### `ResolvedRACIBinding`

Fully-resolved RACI binding with provenance metadata, produced at step evaluation time.

```python
class ResolvedRACIBinding(BaseModel):
    model_config = ConfigDict(frozen=True)

    step_id: str
    responsible: RACIRoleBinding
    accountable: RACIRoleBinding
    consulted: list[RACIRoleBinding] = Field(default_factory=list)
    informed: list[RACIRoleBinding] = Field(default_factory=list)
    source: Literal["inferred", "explicit"]
    inferred_rule: str | None = None         # Rule name when source="inferred"
    override_reason: str | None = None       # Required when source="explicit"
```

**Validation rules:**
- `source` is required; no default
- When `source="explicit"`, `override_reason` must be a non-empty string
- When `source="inferred"`, `inferred_rule` must be a non-empty string identifying the inference rule applied
- `override_reason` must be `None` when `source="inferred"`

#### `RACIEscalationPayload`

Structured escalation when a required RACI role cannot be resolved to a concrete actor.

```python
class RACIEscalationPayload(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: str
    step_id: str
    decision_id: str | None = None
    unresolved_role: Literal["responsible", "accountable"]
    actor_type_expected: str
    resolution_candidates: list[dict[str, Any]] = Field(default_factory=list)
    reason: str
    resolution_hint: str
```

**Validation rules:**
- Only `responsible` and `accountable` trigger escalation (C/I are optional by nature)
- `reason` and `resolution_hint` are required non-empty strings
- `resolution_candidates` lists any partially-matched actors discovered during resolution

#### YAML declaration in `PromptStep` and `AuditStep`

Extend both step types with an optional `raci:` block:

```yaml
steps:
  - id: implement-feature
    title: Implement the feature
    prompt_template: implement.md
    raci:
      responsible:
        actor_type: llm
      accountable:
        actor_type: human
        actor_id: "{{mission_owner_id}}"
      consulted:
        - actor_type: llm
          actor_id: reviewer-agent
      informed: []
    raci_override_reason: "Feature requires named LLM reviewer in consulted role"

audit_steps:
  - id: post-merge-review
    title: Post-merge policy check
    audit:
      trigger_mode: post_merge
      enforcement: blocking
    raci:
      responsible:
        actor_type: human
        actor_id: "{{mission_owner_id}}"
      accountable:
        actor_type: human
        actor_id: "{{mission_owner_id}}"
    raci_override_reason: "Explicit mission owner binding for security audit"
```

- The `raci:` block is optional on both `PromptStep` and `AuditStep`
- When absent, RACI is inferred from the step type (see §3.3)
- When present, `raci_override_reason` must also be present as a sibling field

### 3.2 Schema Extension for Step Types

Extend `PromptStep` and `AuditStep` in `schema.py`:

```python
class PromptStep(BaseModel):
    # ... existing fields ...
    raci: RACIAssignment | None = None
    raci_override_reason: str | None = None

class AuditStep(BaseModel):
    # ... existing fields ...
    raci: RACIAssignment | None = None
    raci_override_reason: str | None = None
```

**Validation rules:**
- If `raci` is not `None`, then `raci_override_reason` must be a non-empty string
- If `raci` is `None`, then `raci_override_reason` must be `None`
- Cross-field validation enforced via Pydantic `model_validator`

### 3.3 RACI Inference Engine

New module: `raci.py` in `src/spec_kitty_runtime/`.

#### `infer_raci(step, mission_policy) -> ResolvedRACIBinding`

Pure function. Given a step (PromptStep or AuditStep) and a MissionPolicySnapshot, returns the inferred RACI binding. No side effects, no I/O.

**Default inference rules (P0):**

| Rule Name | Step Type | Condition | R | A | C | I |
|-----------|-----------|-----------|---|---|---|---|
| `prompt_default` | PromptStep | — | `llm` | `human` (mission_owner) | — | — |
| `audit_blocking` | AuditStep | `enforcement=blocking` | `human` (mission_owner) | `human` (mission_owner) | — | — |
| `audit_advisory` | AuditStep | `enforcement=advisory` | `llm` | `human` (mission_owner) | — | — |

**Rule selection is deterministic**: step type checked first, then enforcement level for audit steps. No ambiguity, no fallthrough.

**Inference resolution for `actor_id`:**
- `accountable.actor_id` → resolved from `inputs["mission_owner_id"]` at evaluation time
- `responsible.actor_id` → for human-R rules, resolved from `inputs["mission_owner_id"]`; for llm-R rules, resolved from `inputs.get("agent_id", "default-agent")`
- Resolution happens in `resolve_raci()` (§3.4), not in `infer_raci()`

#### `validate_raci_assignment(assignment, step) -> tuple[bool, list[str]]`

Validates a RACI assignment (explicit or inferred) against P0 invariants.

**P0 invariants (must not be violated):**

1. `accountable.actor_type` must be `"human"` — no exceptions in P0
2. For `AuditStep` with `enforcement=blocking`: `responsible.actor_type` must be `"human"`
3. LLM actors must not appear in `responsible` or `accountable` for audit decisions
4. Every `RACIAssignment` must have exactly one `responsible` and exactly one `accountable`

Returns `(True, [])` on success, `(False, [error_messages])` on violation.

### 3.4 RACI Resolution

#### `resolve_raci(step, inputs, mission_policy) -> ResolvedRACIBinding`

Resolves a step's RACI binding to concrete actors using runtime inputs.

**Resolution order:**
1. If step has explicit `raci:` block → validate, resolve `actor_id` placeholders, return with `source="explicit"`
2. If step has no `raci:` block → call `infer_raci()`, resolve `actor_id`, return with `source="inferred"`

**`actor_id` placeholder resolution:**
- `"{{mission_owner_id}}"` → `inputs["mission_owner_id"]`
- Literal string values → used as-is
- `None` → resolved from inputs by actor_type convention:
  - `actor_type=human` → `inputs["mission_owner_id"]`
  - `actor_type=llm` → `inputs.get("agent_id", "default-agent")`
  - `actor_type=service` → `inputs.get("service_id")` (must be present)

**Unresolved-role escalation:**
- If `accountable.actor_id` cannot be resolved → emit `RACIEscalationPayload` and raise `MissionRuntimeError` (fail-closed, consistent with WP05 behavior for missing `mission_owner_id`)
- If `responsible.actor_id` cannot be resolved → emit `RACIEscalationPayload` and raise `MissionRuntimeError`
- `consulted` and `informed` with unresolvable `actor_id` are silently dropped (non-blocking roles)

### 3.5 Authority Kernel Integration

WP06 extends — does not replace — the WP05 authority kernel in `engine.py:provide_decision_answer()`.

#### Extended authority metadata

The `_authority_metadata()` helper is extended with two new fields:

```python
def _authority_metadata(
    actor: ActorIdentity,
    authority_role: str,
    rationale_linkage: str | None,
    raci_source: str | None = None,
    override_reason: str | None = None,
) -> dict[str, Any]:
    return {
        "actor_type": actor.actor_type,
        "actor_id": actor.actor_id,
        "authority_role": authority_role,
        "rationale_linkage": rationale_linkage,
        "raci_source": raci_source,          # "inferred" | "explicit" | None
        "override_reason": override_reason,   # Non-None only when raci_source="explicit"
    }
```

#### Pre-answer RACI validation

Before `provide_decision_answer()` processes an answer, it resolves the step's RACI binding and validates the acting actor against the resolved binding:

1. Resolve RACI for the step associated with the decision
2. Determine which RACI role the actor is filling (R for answering, A for audit closure)
3. Validate actor against the resolved binding
4. On mismatch → emit `DecisionAuthorityDenied` with RACI context and raise `MissionRuntimeError`

This validation is additive to WP05 checks (human-only audit, mission_owner_id match, delegation records). WP05 checks execute first; RACI validation runs after WP05 passes.

#### Step-level RACI recording

When `next_step()` issues a step, the resolved RACI binding is persisted in the snapshot's `decisions` dict under key `raci:<step_id>`:

```python
snapshot.decisions[f"raci:{step_id}"] = resolved_binding.model_dump(mode="json")
```

This ensures every step execution has a queryable RACI audit record.

### 3.6 Events

No new event types are introduced. WP06 reuses existing event contracts:

| Event | Usage in WP06 |
|-------|---------------|
| `DecisionAuthorityDenied` | Extended payload includes `raci_source` and `override_reason` |
| `DECISION_INPUT_ANSWERED` | Unchanged; authority metadata now includes RACI fields |
| `NEXT_STEP_ISSUED` | Unchanged; RACI binding persisted to snapshot separately |

The `DecisionAuthorityDenied` payload gains two optional fields:

```python
{
    "run_id": str,
    "decision_id": str,
    "actor_type": str,
    "actor_id": str,
    "authority_role": str,
    "rationale_linkage": str | None,
    "reason": str,
    # WP06 extensions:
    "raci_source": str | None,        # "inferred" | "explicit"
    "override_reason": str | None,
}
```

These are additive (new optional fields on existing payload shape). No breaking change to existing consumers.

### 3.7 Mission Template Validation

Extend `validate_mission_template_compatibility()` in `diagnostics.py` with RACI checks:

1. If `raci:` block is present, validate against `RACIAssignment` schema
2. If `raci:` block sets `accountable.actor_type != "human"`, report `P0_INVARIANT_VIOLATION`
3. If `raci:` block is present without `raci_override_reason`, report `MISSING_OVERRIDE_REASON`
4. If `raci:` block sets LLM as R for a blocking audit step, report `INVALID_RACI_ROLE`

New issue codes:

| Code | Severity | Condition |
|------|----------|-----------|
| `P0_INVARIANT_VIOLATION` | error | `accountable.actor_type` is not `"human"` |
| `INVALID_RACI_ROLE` | error | LLM as R for blocking audit step |
| `MISSING_OVERRIDE_REASON` | error | Explicit `raci:` without `raci_override_reason` |
| `UNKNOWN_ACTOR_TYPE` | error | `actor_type` not in `{"human", "llm", "service"}` |

---

## 4. Acceptance Criteria

### AC-1: Schema validation
- `RACIRoleBinding` with valid `actor_type` parses without error
- `RACIRoleBinding` with unknown `actor_type` raises `ValidationError`
- `RACIAssignment` with `accountable.actor_type="llm"` raises `MissionRuntimeError`
- `RACIAssignment` with `accountable.actor_type="human"` parses without error
- `ResolvedRACIBinding` with `source="explicit"` and empty `override_reason` raises `ValidationError`

### AC-2: YAML loading
- Mission YAML with `raci:` block on a `PromptStep` loads via `load_mission_template_file`
- Mission YAML with `raci:` block on an `AuditStep` loads via `load_mission_template_file`
- Mission YAML with `raci:` block but no `raci_override_reason` raises `MissionRuntimeError`
- Mission YAML without `raci:` block loads normally (backward compatible)

### AC-3: Inference — PromptStep
- `infer_raci(prompt_step, policy)` returns `responsible.actor_type="llm"`, `accountable.actor_type="human"`
- `inferred_rule` is `"prompt_default"`
- `source` is `"inferred"`

### AC-4: Inference — AuditStep (blocking)
- `infer_raci(audit_step_blocking, policy)` returns `responsible.actor_type="human"`, `accountable.actor_type="human"`
- `inferred_rule` is `"audit_blocking"`

### AC-5: Inference — AuditStep (advisory)
- `infer_raci(audit_step_advisory, policy)` returns `responsible.actor_type="llm"`, `accountable.actor_type="human"`
- `inferred_rule` is `"audit_advisory"`

### AC-6: Explicit override
- Step with `raci:` block → `resolve_raci()` returns `source="explicit"` with `override_reason` populated
- Explicit RACI override takes precedence over inferred default
- Override that violates P0 invariant is rejected at load time

### AC-7: Unresolved-role escalation
- `resolve_raci()` with missing `mission_owner_id` for A role → `RACIEscalationPayload` emitted + `MissionRuntimeError` raised
- `resolve_raci()` with missing `agent_id` for R role (llm) → `RACIEscalationPayload` emitted + `MissionRuntimeError` raised
- Escalation payload includes `resolution_hint` with actionable guidance
- Unresolvable C/I roles are silently dropped (non-blocking)

### AC-8: Authority kernel integration
- `provide_decision_answer()` persists `raci_source` and `override_reason` in authority metadata
- `DecisionAuthorityDenied` event payload includes `raci_source` when RACI validation triggers denial
- RACI validation runs after WP05 checks (additive, not replacing)
- WP05 test suite continues to pass unmodified

### AC-9: RACI audit trail
- Every step issued by `next_step()` has a `raci:<step_id>` entry in `snapshot.decisions`
- The audit record contains `step_id`, `source`, `responsible`, `accountable`, `consulted`, `informed`
- Inferred bindings include `inferred_rule`; explicit bindings include `override_reason`

### AC-10: Template compatibility diagnostics
- `validate_mission_template_compatibility()` reports `P0_INVARIANT_VIOLATION` for LLM-as-A
- `validate_mission_template_compatibility()` reports `MISSING_OVERRIDE_REASON` for raci without reason
- `validate_mission_template_compatibility()` reports `INVALID_RACI_ROLE` for LLM-as-R on blocking audit

### AC-11: Determinism
- Same step + same inputs + same policy → identical `ResolvedRACIBinding` output
- No randomness, no time-dependent branching in inference or resolution
- All RACI operations are offline and local-only

### AC-12: Backward compatibility
- Missions without `raci:` blocks continue to work identically to pre-WP06 behavior
- WP05 authority kernel tests pass without modification
- Existing `_authority_metadata()` callers receive backward-compatible dicts (new fields are additive)

---

## 5. Architecture Notes

### Where code lives

| Module | Change |
|--------|--------|
| `schema.py` | Add `RACIRoleBinding`, `RACIAssignment`, `ResolvedRACIBinding`, `RACIEscalationPayload`; extend `PromptStep` and `AuditStep` with optional `raci` field |
| `raci.py` (new) | `infer_raci()`, `resolve_raci()`, `validate_raci_assignment()` — pure functions, no I/O |
| `engine.py` | Extend `_authority_metadata()` with `raci_source` / `override_reason`; add RACI resolution call in `next_step()` and `provide_decision_answer()` |
| `diagnostics.py` | Extend `validate_mission_template_compatibility()` with RACI validation checks |
| `tests/test_raci.py` (new) | Inference, resolution, validation, escalation tests |
| `tests/test_raci_engine.py` (new) | Authority kernel integration, audit trail, backward compat tests |
| `tests/fixtures/` | New fixture YAML files with RACI blocks for test harness |

### Design invariants (must not be violated)

1. **P0 human authority**: `accountable.actor_type` is always `"human"` — enforced at schema validation, inference, resolution, and template compatibility layers (defense in depth)
2. **LLM advisory only**: LLM actors restricted to `consulted` and `informed` roles for decisions; LLM-as-R permitted only for prompt step execution (not decision closure)
3. **Deterministic inference**: `infer_raci()` is a pure function with no I/O, no randomness, no time dependency
4. **Fail-closed escalation**: Unresolvable `responsible` or `accountable` roles always raise `MissionRuntimeError` — no silent degradation, no inference guessing
5. **Additive extension**: WP05 authority kernel behavior is preserved; RACI is layered on top, not replacing existing checks
6. **Audit completeness**: Every step execution records a `ResolvedRACIBinding` with full provenance — no step runs without a RACI audit record
7. **No network calls**: All resolution is local, offline, deterministic
8. **No fallback mechanisms**: Invalid RACI configurations fail explicitly at load time or resolution time

---

## 6. Non-Goals (Explicitly Excluded)

- Auth0 / SAML / SCIM identity provider integration
- `LLM-as-A` authority mode (LLM as Accountable — future/post-MVP)
- Remote actor registries or network-based role resolution
- Role hierarchy or inheritance (P0 uses flat RACI, no nesting)
- SaaS UI or projection work
- CLI wiring for RACI management
- New event types in `spec-kitty-events` package
- 1.x compatibility shims or legacy field aliases
- Dynamic RACI renegotiation during a run (bindings are resolved per-step, not mutable mid-step)

---

## 7. Assumptions

1. **WP05 authority kernel is stable and merged** — WP06 extends `_authority_metadata()` and the `provide_decision_answer()` path without modifying WP05 invariants. Confirmed: commit `8bc392f` is on `main`.

2. **`spec-kitty-events==2.3.1` event contract is frozen** — No new event types are introduced. WP06 adds optional fields to existing payloads (`DecisionAuthorityDenied`), which is a non-breaking additive change.

3. **`inputs["mission_owner_id"]` is the canonical human authority identifier** — WP05 established this convention (`_resolve_mission_owner_id()` at `engine.py:465`). WP06 reuses it for `accountable.actor_id` resolution.

4. **`inputs["agent_id"]` convention for LLM actor identification** — WP06 assumes LLM actors are identified via `inputs.get("agent_id", "default-agent")`. This is a new convention introduced by WP06; no existing code uses `agent_id` in inputs.

5. **Mission YAML is the single control entity** — RACI declarations in YAML override inference. No external RACI policy sources exist in P0.

6. **`actor_type` enum is `{"human", "llm", "service"}`** — Matches the existing `RuntimeActorIdentity` from `spec_kitty_events.mission_next`. The `"service"` type is supported in schema but has no P0 inference rules (service actors must be explicitly declared).

7. **RACI audit records use the `decisions` dict namespace** — Records are keyed as `raci:<step_id>` in `MissionRunSnapshot.decisions`. This co-locates RACI provenance with decision records without requiring a schema change to `MissionRunSnapshot`.

8. **Backward compatibility is structural, not semantic** — Missions without `raci:` blocks behave identically to pre-WP06. The runtime does not retroactively infer RACI for steps that have already completed in an in-progress run; RACI inference applies only to steps evaluated after WP06 deployment.

9. **P0 means "Priority 0 / MVP release"** — The P0 invariants (human-only-A, LLM advisory-only) are hard constraints for this release. Post-MVP work may relax these under a separate feature flag and spec.

10. **`raci_override_reason` is a human-authored justification string** — It is not validated for content beyond non-emptiness. It exists for audit trail purposes, not for machine interpretation.

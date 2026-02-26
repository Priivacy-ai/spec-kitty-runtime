# Runtime Audit Primitive Contracts

This directory documents the serialized payload shapes and runtime contracts produced and consumed by `spec-kitty-runtime`.

## Overview

The audit primitive layer is responsible for deterministic evaluation of mission steps, structured failure reporting, and context persistence for replay. The contracts below describe the stable shapes that downstream consumers (e.g. `spec-kitty` SaaS) may pin against.

## Key Contract Sources

| Module | Location | Description |
|--------|----------|-------------|
| **Schema** | `src/spec_kitty_runtime/schema.py` | Core data models — `ContextType`, `StepContextContract`, `RemediationPayload`, `ContextLedgerEntry`, and related Pydantic schemas that form the serialization contract. |
| **Planner** | `src/spec_kitty_runtime/planner.py` | Mission planning primitives — resolves step ordering, dependency graphs, and emits planning-phase artifacts. |
| **Engine** | `src/spec_kitty_runtime/engine.py` | Transition-gate engine — evaluates `StepContextContract` blocks, runs the 5-point resolver chain, and returns `ready` or a structured `RemediationPayload`. |
| **Diagnostics** | `src/spec_kitty_runtime/diagnostics.py` | Diagnostic helpers — introspects ledger state, reports context gaps, and formats audit output for human and machine consumers. |

## Payload Shapes (Summary)

### Mission Manifest
Produced by the planner. Describes all steps, their context requirements (`StepContextContract`), and expected artifact lists.

### StepContextContract
Frozen in `schema.py`. Required fields: `type`, `deterministic`, `cardinality`, `validation`, `resolver_ref`. Unknown `ContextType` values fail validation at mission-pack load time.

### Resolved Context
Produced by the engine after a successful transition-gate evaluation. Contains the resolved value, source resolver, and ledger binding key.

### RemediationPayload
Emitted on gate failure. Error codes: `CONTEXT_MISSING`, `CONTEXT_AMBIGUOUS`, `CONTEXT_INVALID`. Includes candidate list for ambiguous cases.

### ContextLedger Entry
Persisted by the ledger layer. Canonical JSON serialization with deterministic key ordering. Supports bit-for-bit replay across independent runs.

## Resolver Precedence

The engine resolves contexts in this fixed order (local-first, offline):

1. Explicit step/run inputs
2. Prior `ContextLedger` bindings
3. Mission run metadata
4. Deterministic local discovery (filesystem, branch state, cwd)
5. Step-specific fallbacks (only with explicit policy)

Network or remote registries are explicitly **out of scope** for the default chain.

## Version

These contracts are targeted for the **v0.4.0** release of `spec-kitty-runtime`.
See `CHANGELOG.md` for the full history and breaking-change log.

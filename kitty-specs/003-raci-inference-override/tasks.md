---
feature: 003-raci-inference-override
total_wps: 1
---

# Tasks: RACI Inference and Override (WP06)

## Work Package Index
- [x] [WP06 RACI Inference and Override](tasks/WP06-raci-inference-override.md)

## WP06: RACI Inference and Override

- **Dependencies**: none
- **Requirement Refs**: FR-006
- Deliverable: deterministic runtime RACI inference/override enforcement with audit-safe escalation and WP05-compatible authority integration.

## Global Done Criteria
- [x] Mission owner remains human final authority in P0.
- [x] LLM role remains advisory-only in P0 (`C/I`, may also be informed).
- [x] Explicit RACI overrides require auditable override reason.
- [x] Unresolved required roles fail closed with escalation payload.
- [x] WP05 authority behavior remains intact and additive.
- [x] Out-of-scope (`LLM-as-A`, Auth0/SAML/SCIM) remains excluded.

## Validation Commands
- [x] `pytest -k "raci or authority or audit"`
- [x] `ruff check .`

## Required Assertions
- [x] RACI inference is deterministic for prompt and audit steps.
- [x] Explicit RACI override takes precedence over inferred binding.
- [x] `DecisionAuthorityDenied` payload remains backward compatible with additive fields.
- [x] Step-level RACI provenance is persisted in snapshot decisions.

<!-- status-model:start -->
## Canonical Status (Generated)
- WP06: done
<!-- status-model:end -->

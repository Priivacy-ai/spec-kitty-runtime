---
feature: 003-raci-inference-override
total_wps: 1
---

# Tasks: RACI Inference and Override (WP06)

## Work Package Index
- [ ] [WP06 RACI Inference and Override](tasks/WP06-raci-inference-override.md)

## WP06: RACI Inference and Override

- **Dependencies**: none
- **Requirement Refs**: FR-006
- Deliverable: deterministic runtime RACI inference/override enforcement with audit-safe escalation and WP05-compatible authority integration.

## Global Done Criteria
- [ ] Mission owner remains human final authority in P0.
- [ ] LLM role remains advisory-only in P0 (`C/I`, may also be informed).
- [ ] Explicit RACI overrides require auditable override reason.
- [ ] Unresolved required roles fail closed with escalation payload.
- [ ] WP05 authority behavior remains intact and additive.
- [ ] Out-of-scope (`LLM-as-A`, Auth0/SAML/SCIM) remains excluded.

## Validation Commands
- [ ] `pytest -k "raci or authority or audit"`
- [ ] `ruff check .`

## Required Assertions
- [ ] RACI inference is deterministic for prompt and audit steps.
- [ ] Explicit RACI override takes precedence over inferred binding.
- [ ] `DecisionAuthorityDenied` payload remains backward compatible with additive fields.
- [ ] Step-level RACI provenance is persisted in snapshot decisions.

<!-- status-model:start -->
## Canonical Status (Generated)
- WP06: for_review
<!-- status-model:end -->

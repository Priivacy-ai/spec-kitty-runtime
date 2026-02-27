---
feature: 002-decision-authority-kernel
total_wps: 1
---

# Tasks: Decision Authority Kernel (WP05)

## Work Package Index
- [ ] [WP05 Runtime Decision Authority Kernel](tasks/WP05-runtime-decision-authority-kernel.md)

## Global Done Criteria
- [ ] P0 final closure authority is human mission owner only.
- [ ] LLM role is advisory-only in P0 (`C/I`, may be informed).
- [ ] LLM delegation requires explicit audit record.
- [ ] Runtime denies non-human final closure and emits audit event.
- [ ] WP03 decision contracts are used as dependency in `events/runtime`.
- [ ] Out-of-scope (`LLM-as-A`) remains excluded from MVP behavior.

## Validation Commands
- [ ] `pytest -k "authority or decision"`
- [ ] `pytest -k "audit or policy"`
- [ ] `ruff check .`

## Required Assertions
- [ ] Denial path for non-human final closure exists.
- [ ] Audit payload includes `actor_type`, `actor_id`, `authority_role`, `rationale_linkage`.

<!-- status-model:start -->
## Canonical Status (Generated)
- WP05: in_progress
<!-- status-model:end -->

---
work_package_id: WP05
title: Runtime Decision Authority Kernel
lane: "in_progress"
dependencies: []
requirement_refs: [FR-005]
assignee: "claude-opus-4.6"
agent: "codex"
---

# WP05: Runtime Decision Authority Kernel

## Objective
Establish a runtime authority kernel for P0 so final closure is strictly human-owned (mission owner), while LLM participation remains advisory and auditable.

## Policy Constraints (Must Hold)
- Mission owner is always human final authority in P0.
- LLMs are advisory-only in P0 (`C/I`; may also be informed), never final closure actor.
- Delegation to LLM is allowed only with explicit audit record.
- Non-human final closure attempts must be denied and audited.
- Implementation depends on WP03 decision contracts from `events/runtime`.
- `LLM-as-A` final authority is out of scope (future/post-MVP).

## Implementation Tasks
- [ ] Integrate authority guard into P0 final closure runtime path.
- [ ] Enforce actor-type + authority-role checks against WP03 contract fields.
- [ ] Implement deterministic denial response for non-human final closure attempts.
- [ ] Emit denial audit event on policy violation.
- [ ] Ensure delegation-to-LLM path requires explicit audit record.
- [ ] Ensure audit payload carries required authority metadata fields.

## Test Tasks
- [ ] Add/validate tests for human mission-owner success path.
- [ ] Add/validate tests for non-human final closure denial path.
- [ ] Add/validate tests for missing delegation audit record behavior.
- [ ] Verify audit payload schema in authority events.

## Acceptance Checks
- [ ] `pytest -k "authority or decision"`
- [ ] `pytest -k "audit or policy"`
- [ ] `ruff check .`

## Assertion Checklist
- [ ] Denial path for non-human final closure exists.
- [ ] Audit payload includes `actor_type`, `actor_id`, `authority_role`, `rationale_linkage`.

## Deliverables
- Updated runtime authority logic bound to WP03 contracts.
- Test coverage for authority and policy audit behavior.
- Traceable audit events for allow/deny authority decisions.

## Activity Log

- 2026-02-27T13:47:44Z – codex – lane=in_progress – Starting WP05 implementation orchestration

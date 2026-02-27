# Plan: WP05 Runtime Decision Authority Kernel

## Goal
Implement P0 decision authority enforcement so only human mission owners can perform final closure, with deterministic denial + audit for non-human attempts.

## Dependency
- Consume WP03 decision contracts in `events/runtime` as source of truth for actor, role, decision state, and audit envelope semantics.

## Workstreams
1. Policy Kernel Definition
- Encode policy invariants for P0 final closure authority.
- Mark LLM participation as advisory-only (`C/I`; optionally informed).
- Define explicit delegation record precondition for LLM delegation.

2. Runtime Enforcement
- Add authority gate in final closure path.
- Reject non-human final closure attempts.
- Emit standardized denial audit event on rejection.

3. Audit Contract Alignment
- Ensure authority events include: `actor_type`, `actor_id`, `authority_role`, `rationale_linkage`.
- Preserve linkage to WP03 decision identifiers.

4. Test and Lint Validation
- Execute:
  - `pytest -k "authority or decision"`
  - `pytest -k "audit or policy"`
  - `ruff check .`
- Add/verify assertions:
  - Denial path for non-human final closure exists.
  - Audit payload includes `actor_type`, `actor_id`, `authority_role`, `rationale_linkage`.

## Sequencing
1. Lock policy constraints and non-goals.
2. Implement runtime gate using WP03 contracts.
3. Add denial/audit emission behavior.
4. Verify contract-level payload fields.
5. Run acceptance checks.

## Risks and Mitigations
- Risk: Contract drift with WP03 payload shape.
  - Mitigation: Reference WP03 contract definitions directly in tests.
- Risk: Silent policy bypasses in alternate closure flows.
  - Mitigation: enforce a shared authority guard used by all final closure entry points.

## Out of Scope
- `LLM-as-A` final authority pathway (future/post-MVP).

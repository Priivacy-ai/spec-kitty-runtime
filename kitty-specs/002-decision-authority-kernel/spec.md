# WP05: Runtime Decision Authority Kernel (P0)

## Status
Draft for implementation.

## Problem
P0 runtime flows currently risk ambiguous decision closure authority across human and non-human actors. This creates a safety and accountability gap for mission-critical closures.

## Objective
Define and enforce a runtime authority kernel so final closure in P0 is always human-owned, auditable, and denial-enforced for non-human closure attempts.

## Normative Policy Facts
1. Mission owner is always human final authority in P0.
2. LLMs are advisory-only in P0 (`C/I`; may also be informed), never the final closure actor.
3. Delegation to an LLM is allowed only with an explicit audit record.
4. If a non-human actor attempts final closure, runtime must deny and emit an audit event.
5. WP05 depends on WP03 decision contracts from `events/runtime` as the enforcement and payload baseline.
6. Out of scope for MVP: `LLM-as-A` final authority mode (future/post-MVP).

## Scope
- Authoritative role policy for P0 closure actions.
- Runtime enforcement behavior for actor-role mismatches.
- Audit event requirements for both allowed and denied paths.
- Contract-aligned payload fields required for traceability.

## Non-Goals
- Enabling non-human final closure in P0.
- Introducing new authority roles outside WP03 contract model.
- Shipping future `LLM-as-A` authority behavior.

## Required Runtime Behavior
- On P0 final closure request:
  - Validate actor identity and actor type.
  - Confirm authority role is `mission_owner` and actor is human.
  - If check fails: deny closure, preserve open state, emit denial audit event.
- On LLM delegation:
  - Allow advisory delegation only when explicit audit record exists.
  - Missing audit record is policy violation.

## Required Audit Payload Fields
Audit payloads for authority decisions (allow/deny) must include:
- `actor_type`
- `actor_id`
- `authority_role`
- `rationale_linkage`

## Acceptance Criteria
- Tests executed:
  - `pytest -k "authority or decision"`
  - `pytest -k "audit or policy"`
  - `ruff check .`
- Assertions:
  - Denial path for non-human final closure exists.
  - Audit payload includes `actor_type`, `actor_id`, `authority_role`, `rationale_linkage`.

# Changelog

## 0.2.0a0 - 2026-02-17

**Breaking API change** — emitter protocol and event constants canonicalized
against `spec-kitty-events` v2.3.1.

### Breaking changes

- **Emitter method renames** (old -> new):
  - `emit_mission_started()` -> `emit_mission_run_started(payload)`
  - `emit_mission_completed()` -> `emit_mission_run_completed(payload)`
  - `emit_decision_requested()` -> `emit_decision_input_requested(payload)`
  - `emit_decision_answered()` -> `emit_decision_input_answered(payload)`
- **All emitter methods** now accept a single canonical payload model
  (e.g. `MissionRunStartedPayload`) instead of positional arguments.
- **Event constant `MISSION_COMPLETED` removed**, replaced by
  `MISSION_RUN_COMPLETED` (value: `"MissionRunCompleted"`).
- **Constants `DECISION_RESOLVED` and `TEMPLATE_MIGRATION_REQUIRED` removed** —
  not part of canonical contracts.
- **JSONL event payloads** now contain full canonical model fields
  (`run_id`, `actor`, `agent_id`, etc.) instead of ad-hoc dicts.

### Migration guide

1. Replace all emitter implementations with payload-based method signatures.
2. Import event constants from `spec_kitty_runtime.events` (re-exported from
   `spec_kitty_events.mission_next`).
3. Replace `ActorIdentity` construction with `RuntimeActorIdentity` (or use
   the `ActorIdentity` alias which now points to the canonical class).
4. Update any event-type string comparisons:
   `"MissionCompleted"` -> `"MissionRunCompleted"`.

### Other changes

- `ActorIdentity` is now an alias for `spec_kitty_events.mission_next.RuntimeActorIdentity`.
- `RuntimeActorIdentity` added to public exports.
- Dependency pinned to `spec-kitty-events==2.3.1`.
- New `tests/test_contract_parity.py` validates payload/JSONL round-trip
  against canonical models.

## 0.1.0a0 - 2026-02-17

1. Initial scaffold for canonical mission runtime package.
2. Added deterministic discovery, planner, engine, and prompt renderer modules.
3. Added example YAML mission pack and baseline tests.

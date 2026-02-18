# spec-kitty-runtime

Canonical mission runtime for Spec Kitty.

## Scope (V1)

1. YAML mission template loading.
2. Deterministic mission discovery with precedence tiers.
3. Deterministic step planner and mission `next()` execution loop.
4. Prompt rendering for agent runtimes.

## Public API

1. `load_mission_template(path_or_key, context=None)`
2. `discover_missions(context)`
3. `start_mission_run(template_key, inputs, policy_snapshot, context=None, run_store=None)`
4. `next_step(run_ref, agent_id, result="success", policy_snapshot=None, actor_context=None, context=None)`
5. `render_prompt(decision, format="markdown")`

## Runtime Event Emitter API (v0.2.0a0)

`RuntimeEventEmitter` uses canonical payload-object methods aligned to
`spec-kitty-events` mission-next contracts:

1. `emit_mission_run_started(payload)`
2. `emit_next_step_issued(payload)`
3. `emit_next_step_auto_completed(payload)`
4. `emit_decision_input_requested(payload)`
5. `emit_decision_input_answered(payload)`
6. `emit_mission_run_completed(payload)`

`NullEmitter` is the default no-op implementation for local-first/offline flows.

## Mission Pack Layout (YAML-only)

```text
mission-pack.yaml
missions/<mission_key>/mission.yaml
missions/<mission_key>/templates/*.md
missions/<mission_key>/steps/*.yaml  # optional
```

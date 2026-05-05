# TeamSpace Migration Runtime Log Boundary

For the public TeamSpace launch migration, `spec-kitty-runtime` logs are **local-only side logs**.

`run.events.jsonl` rows are useful audit evidence for mission-next execution, but they are not WP lane authority and they are not full TeamSpace event envelopes. Launch migration tooling should report them with disposition `local_only_side_log` / `deferred_not_launch_import`.

In scope for classification:

- `MissionNextInvoked`
- `MissionRunStarted`
- `NextStepIssued`
- `MissionRunCompleted`

Out of scope for launch import:

- adapting runtime rows into TeamSpace events
- reducing runtime rows into `status.json`
- treating runtime event types as `WPStatusChanged`

The CLI migration doctor owns repository-wide discovery of `.kittify/runtime/**/run.events.jsonl`; this package owns the event-type boundary and fixture coverage.

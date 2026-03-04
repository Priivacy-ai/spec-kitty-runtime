# Runtime Dependency Release Train

`spec-kitty-runtime` must only release after compatible, MIT-clearly-labeled `spec-kitty-events` versions are published.

## Order

1. Release `spec-kitty-events`.
2. Update runtime pin in `pyproject.toml`.
3. Update `docs/releases/dependency-compatibility-matrix.toml`.
4. Release `spec-kitty-runtime`.
5. Release `spec-kitty-cli` only after runtime/events are available and pinned.

## Required Checks

- `python scripts/release/validate_dependency_matrix.py`
- `python scripts/release/validate_dependency_policy.py`
- `python scripts/release/validate_distribution_metadata.py`

## Exception Policy

Prerelease/direct-reference dependency pins are blocked unless explicitly approved in release workflow inputs.

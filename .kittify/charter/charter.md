# Project Charter

<!-- Generated charter location; manually established for runtime boundary governance. -->

Generated: 2026-04-25T09:07:59Z

## Purpose

Define the governance boundary for mission runtime code during the migration away from a standalone shared runtime package.

## Policy Summary

- Intent: Retire `spec-kitty-runtime` as a production shared dependency and move mission runtime behavior into the owning product boundary.
- Owning Product Boundary: Runtime behavior used by `spec-kitty next` and mission execution belongs inside the `spec-kitty` CLI repository.
- SaaS Boundary: Spec Kitty SaaS must not consume this package as a production dependency without a reviewed architecture decision.
- External Contracts: Runtime code may consume `spec-kitty-events` and `spec-kitty-tracker` as external package contracts after migration, but those packages must not depend on runtime.
- Release Policy: Do not create runtime package releases solely to unblock sibling package release order. New releases require a documented migration, compatibility, or archival reason.

## Project Directives

1. Do not add new public API surface intended for long-term consumption by CLI or SaaS.
2. Keep changes focused on migration support, compatibility preservation, or archival cleanup.
3. Do not introduce dependencies from events or tracker back into runtime.
4. Do not require CLI or SaaS to install this package for production execution after the migration is complete.

## Migration Direction

- Move runtime implementation needed by CLI into the `spec-kitty` repository.
- Remove stale nested runtime source from `spec-kitty-saas` import paths.
- Replace cross-package release gates with direct consumer tests in CLI and SaaS.
- Preserve any still-needed runtime concepts as internal product code or as narrow, versioned contracts in the appropriate external package.

## Amendment Process

Update this charter through maintainer-reviewed changes when the runtime migration direction or archival policy changes.

## Exception Policy

Exceptions require explicit maintainer approval plus a follow-up issue that restores the internal-runtime boundary or documents a replacement architecture.

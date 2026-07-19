# Coverage Manifests

This directory holds concrete declared coverage for the simulator.

## Files

- `rules.initial.yaml`: initial rules support declaration
- `cards.initial.yaml`: initial card support declaration
- `slices/*.yaml`: named support-slice manifests

## Manifest Relationship

- Named support-slice manifests are the declared playable scope on top of the card and rules coverage manifests.
- `docs/coverage/slices/portal.initial.yaml` is the active support-slice manifest for the current narrow `Portal`-led slice.
- `rules.initial.yaml` and `cards.initial.yaml` remain the canonical declarations of implemented card and rule coverage inside that slice.

## Companion Planning Docs

- `docs/contracts/engine-test-trace-mapping.md`: planned future engine tests and replay-trace assertions for current rule families

These manifests are declarations of claimed support, not implementation.

## Canonical Format Rule

- YAML manifests are the canonical coverage declaration for the current repository phase.
- Matching narrative markdown is optional and should be added only when the supported rule surface becomes too large for the manifests alone to stay legible.

## Current Declared Slice

The current declared playable scope is the active support-slice manifest:

- `docs/coverage/slices/portal.initial.yaml`

Use that manifest as the complete card and rule list. The companion manifests remain the status authority for individual entries:

- `docs/coverage/cards.initial.yaml`
- `docs/coverage/rules.initial.yaml`

At the time of this README update, the active slice includes a narrow
`Portal`-led card set covering vanilla creatures, basic lands, minimal
`Flying`, `Reach`, `Swampwalk`, `Forestwalk`, `Islandwalk`, `Mountainwalk`,
`Defender`, `Vigilance`, and `Haste`, plus the bounded flying-only blocker restriction and name-scoped
Alabaster Dragon dies-trigger shuffle. Waves 5–7 additionally provide the
documented, name-scoped hidden-zone choices and deterministic RNG, X-cost and
damage effects, turn markers and extra turn, constrained instants, registered
triggers, activated abilities, and creature-or-sorcery countering. Generic
versions of those rule families remain unsupported; use the manifests and
bounded contracts for the exact surface.

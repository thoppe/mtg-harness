# Coverage Manifests

This directory holds concrete declared coverage for the simulator.

## Files

- `rules.initial.yaml`: initial rules support declaration
- `cards.initial.yaml`: initial card support declaration
- `slices/*.yaml`: named support-slice manifests

## Planned Next Layer

- Named support-slice manifests should become the declared playable scope on top of the card and rules coverage manifests.
- `docs/coverage/slices/portal.initial.yaml` is the first active support-slice manifest for the current narrow `Portal` slice.
- `rules.initial.yaml` and `cards.initial.yaml` remain the canonical declarations of implemented card and rule coverage inside that slice.

## Companion Planning Docs

- `docs/contracts/engine-test-trace-mapping.md`: planned future engine tests and replay-trace assertions for current rule families

These manifests are declarations of claimed support, not implementation.

## Canonical Format Rule

- YAML manifests are the canonical coverage declaration for the current repository phase.
- Matching narrative markdown is optional and should be added only when the supported rule surface becomes too large for the manifests alone to stay legible.

Current declared slice contents:

- `Border Guard`
- `Foot Soldiers`
- `Muck Rats`
- `Vengeance`
- `Path of Peace`
- `Touch of Brilliance`
- `Time Ebb`
- `Swamp`
- `Forest`
- `Island`
- `Mountain`
- `Plains`

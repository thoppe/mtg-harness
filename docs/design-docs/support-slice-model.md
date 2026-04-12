# Support Slice Model

## Problem

The repository currently relies on a fixed "micro-universe" concept that is doing too much at once:

- source acquisition scope
- declared playable scope
- implemented engine loading scope
- test fixture universe

That was a good bootstrap choice, but it is starting to create friction:

- every card expansion requires touching multiple hardcoded lists
- the engine and ingestion layers are coupled more tightly than they should be
- the term "micro-universe" does not scale well once we want multiple narrow `Portal` expansions
- the repository risks drifting toward an ever-growing special case instead of a controlled support model

## Decision

Move from a fixed repo-wide micro-universe toward manifest-driven named support slices.

The current initial slice should remain narrow, but it should be treated as one declared slice among future slices, not as a permanent global model.

## Model

Use three explicit layers:

1. Raw source artifacts
2. Coverage manifests for cards and rules
3. Support slice manifests

Responsibilities:

- raw source artifacts state what data has been fetched
- coverage manifests state what cards and rules are implemented, deferred, or not started
- support slices state which implemented subset is grouped together as a declared playable or engine-loadable slice

## Why This Is Better

- Expansions become manifest edits first, not code-first list edits.
- The repository can support multiple narrow `Portal` increments without pretending to support all of `Portal`.
- Tests can target named slices instead of inheriting one implicit global universe.
- Engine loading can become data-driven without collapsing source ingestion and gameplay support into the same concept.

## Near-Term Shape

In the near term, keep one active slice and one engine-loading path, but define it by manifest:

- one active support slice under `docs/coverage/`
- card repository loading keyed off the active slice manifest
- tests asserting that the repository and coverage declarations align with that manifest

This keeps v0 simple while removing the current hardcoded-growth trap.

## Deferred Complexity

Do not add these yet:

- runtime slice switching in user-facing interfaces
- multiple active slices at once
- cross-set slice composition unless a concrete use case appears
- a generalized plugin or package-discovery system for slices

## Migration Plan

1. Define a support-slice manifest contract.
2. Add an initial manifest representing the current `portal_initial_micro_universe`.
3. Update coverage docs to describe slices as the declared playable scope.
4. Refactor engine card loading to derive the active slice from manifest data instead of a hardcoded oracle ID set.
5. Update tests so slice membership and repository loading are validated through manifest-driven expectations.

## Guardrails

- Do not use support slices to hide unsupported cards inside a broadly named set claim.
- Do not replace the existing card and rule coverage manifests; slices compose them.
- Do not let raw source presence imply slice membership.
- Do not widen beyond one active slice in code until a real use case exists.

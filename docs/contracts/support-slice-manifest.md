# Contract: Support Slice Manifest

## Purpose

Define the manifest shape for named implementation slices that replace reliance on a hardcoded micro-universe.

## Why This Exists

- Raw source scope, declared playable scope, and implemented rules scope are different concerns.
- The current manifest-backed micro-universe provides bootstrap honesty without hardcoding its membership in the engine.
- Named support slices let the repository expand in controlled increments without implying full-set support.

## Required Fields

- `slice_key`: stable machine-readable identifier for the slice
- `display_name`: short human-readable label
- `status`: one of `draft`, `active`, `superseded`, `archived`
- `set_code`: primary source set for the slice, when applicable
- `card_keys`: canonical card identities included in the slice
- `rule_keys`: rules coverage entries required by the slice
- `source_artifacts`: references to the raw source scope the slice depends on
- `notes`: optional explanation of simplifications, exclusions, or migration intent

## Optional Fields

- `card_entries`: explicit per-card source declarations, each containing:
  - `oracle_id`: canonical card identity
  - `set_code`: source set used to fetch and provenance that card's raw artifact
  - `deck_eligible`: optional boolean; defaults to true for a declared slice
    card and must be false for a scenario-only engine testbed

## Guarantees

- A support slice is a declared gameplay scope, not merely a source-ingestion scope.
- Slice membership must be discoverable from repo-local manifests rather than only from hardcoded engine constants.
- A card may exist in local source artifacts without belonging to any active support slice.
- A rule family may exist in coverage manifests without belonging to every slice.
- The active slice must not imply broader set support than the manifest explicitly names.
- When `card_entries` exists, raw-source provenance should come from those per-card set declarations rather than assuming the slice-level `set_code` applies to every card.
- Deck eligibility is narrower than engine support: a supported scenario-only
  card may be loadable for a rules harness while excluded from legal decks.

## Freshness Rule

- Treat the active support-slice manifest as the canonical current playable card list.
- Prefer references to the active support-slice manifest over copied card lists in contracts, README files, and execution plans.
- When a support-slice card entry changes, update card coverage, rules coverage, relevant product specs, and active-plan progress or resume notes in the same change.
- If an execution plan names a specific "next card," replace or re-affirm that statement when the named card is implemented.

## Separation Rule

- Raw source artifacts answer: "what external data is locally available?"
- Support slices answer: "what card and rule subset is currently declared as a playable/implemented scope?"
- Coverage manifests answer: "what individual cards and rule families are implemented, deferred, or not started?"

## Current Implementation Direction

- The current `portal_initial_micro_universe` is the named active support slice and is loaded from its manifest rather than a hardcoded engine card list.
- Early slices may remain small and `Portal`-only.
- Later slices may stay Portal-led while incorporating a small number of off-set oracle identities when their source provenance is explicit in `card_entries`.
- Engine loading uses the one active manifest-backed slice in v0; future work may extend this only when multiple simultaneous runtime formats are explicitly contracted.

## Non-Goals

- This contract does not require immediate support for multiple simultaneous runtime formats.
- This contract does not replace the card or rules coverage manifests.
- This contract does not imply full normalization of all raw source artifacts into engine-ready objects.

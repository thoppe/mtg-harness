# Contract: Card Implementation Lifecycle

## Purpose

Define how raw card data becomes simulator-supported gameplay objects.

## Lifecycle States

- `raw`: card metadata, oracle text, and optional images have been fetched with provenance.
- `normalized`: raw data has been transformed into the project's canonical card model.
- `set-declared`: the card's set belongs to a declared implementation wave.
- `implemented`: the engine supports the card within the currently stated mechanic envelope.
- `deferred`: the card is present in data but intentionally unsupported.

## Guarantees

- Cards are planned and reported by set first, not by ad hoc one-off card additions.
- A set can be partially implemented only if the unsupported portion is explicitly marked.
- Image availability does not imply gameplay support.
- Card support status must be traceable to both a source snapshot and an implementation declaration.
- Once a new card from an actively targeted set is identified, the repository should pull and retain its raw source artifacts instead of deferring the data pull until the implementation session that uses it.
- Newly pulled cards that are not yet engine-supported should be marked `deferred` in coverage until a later change implements them.

## Workflow Requirements

- Card-support changes must follow the collaboration and autonomous staging
  requirements in [Agent Workflow And Change Staging](agent-workflow.md).
- A verified card-support increment is a coherent commit stage when it includes
  every artifact required by the active plan's card-expansion freshness check.

## Contract Boundary

- Scryfall provides raw source data and image references.
- The repository's canonical card model defines normalized internal shape.
- Engine support is declared separately from source ingestion.
- Set planning should use set code as the first implementation grouping, starting with `Portal` (`por`).

## Open Questions

- How should reprints and multi-set membership be reported in set-based implementation plans?
- Should support manifests be keyed by set code, oracle ID, or internal card ID?

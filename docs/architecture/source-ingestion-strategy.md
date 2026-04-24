# Source Ingestion Strategy

## Selected Authorities

- Card data authority: Scryfall
- Rules authority: Wizards of the Coast Comprehensive Rules

## Rules Strategy

- Fetch the official plain-text Comprehensive Rules snapshot from the Wizards rules page.
- Preserve each fetched rules snapshot with an effective date and source URL.
- Store rules text as `information/rules/raw/comprehensive_rules_<effective-date>.txt`.
- Store a sidecar provenance file next to each rules snapshot.
- Treat the raw rules corpus as reference material, not as directly executable logic.
- Build explicit mappings from comprehensive-rules sections to internal contracts and implementation status.
- Store pulled rules artifacts under `information/rules/`.

Current verified official entry points as of April 12, 2026:

- Wizards rules page: `https://magic.wizards.com/en/rules`
- Current text snapshot linked there: effective February 27, 2026

## Card Data Strategy

- Use Scryfall as the canonical external source for card metadata and oracle text.
- Prefer bulk-data acquisition patterns for large-scale syncs.
- Download card images as a separate concern from metadata normalization.
- Keep provenance linking normalized card records back to the source snapshot.
- Store pulled card artifacts under `information/cards/`.
- Store one card-data file per card and one image file per card in separate subdirectories.
- Use Scryfall `oracle_id` as the canonical internal identity for a card concept.
- Treat Scryfall `id` as the printing-level/source-record identity.
- Persist canonical card metadata files as `information/cards/data/<oracle_id>.json`.
- Persist card images as `information/cards/images/<oracle_id>.<ext>`.
- Persist JPG images by default for the current plan.
- Persist image provenance as `information/cards/images/<oracle_id>.jpg.provenance.json`.
- Persist card metadata as a provenance wrapper around the fetched Scryfall source record, not as an engine-normalized card object.
- When a new card from an actively tracked set becomes known, pull and commit its raw artifacts immediately, then let coverage mark it as future implementation work.
- This keeps future implementation sessions from having to repeat source acquisition just to widen support by one declared card.

## Initial Coverage Target

- First implementation set: `Portal` (`por`)
- Reason for selection: reduced rules complexity relative to later expansions, which makes it a better first vertical slice for engine and coverage-manifest design.

## Image Strategy

- Images are supporting assets, not the authority for rules text.
- Image download workflows should be rate-aware and cache-aware.
- Image fetching policy should minimize repeated downloads and avoid unnecessary API pressure.
- Persist the Scryfall `normal` JPG variant by default for the initial micro-universe.

## Initial Card Universe

- First implementation set remains `Portal` (`por`).
- The active playable universe is declared in `docs/coverage/slices/portal.initial.yaml`.
- This support slice exists to constrain the first engine slice before broader `Portal` support.

## Raw Vs Implemented Separation

- Raw source archives answer: "what does the official source say?"
- Contracts answer: "what semantics does this simulator claim to support?"
- Coverage manifests answer: "what has been implemented, deferred, or not started?"

This separation is necessary because official rules and card data are much broader than the initial simulator scope.

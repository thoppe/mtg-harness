# Contract: Knowledge Sources

## Purpose

Define how external card and rules information enters the repository.

## Guarantees

- Every external source used by the project must be named and documented in-repo.
- Imported information must identify origin, version or snapshot date, and normalization assumptions.
- Derived internal artifacts must be reproducible from documented inputs.
- Raw source snapshots must remain distinguishable from engine-implemented interpretations.
- Implemented support must be declared explicitly; raw source presence does not imply simulator support.

## Selected Sources

- Canonical card database source: Scryfall
- Canonical rules source: Wizards of the Coast Comprehensive Rules
- Preferred rules artifact format: plain text snapshot downloaded from the official rules page

## Operational Constraints

- Scryfall API access must follow published traffic guidance.
- Large card-data pulls should prefer bulk data workflows rather than high-volume per-card API traffic.
- Card-image downloads should avoid unnecessary API load and must respect the distinction between API-hosted metadata and image/file hosting.
- Requests to Scryfall should send a meaningful `User-Agent` and `Accept` header.

## Raw Vs Implemented Model

- `raw` means an external source snapshot is archived and available for reference.
- `implemented` means the engine and contracts explicitly support the corresponding semantics or card/set slice.
- `not implemented` means the source material may exist locally, but the simulator must not claim behavior support.

## Unknowns

- Licensing and redistribution implications are not evaluated yet.
- Exact local storage policy for downloaded images is not chosen yet.
- Exact raw/implemented directory and manifest layout is not chosen yet.

## Decisions Needed

- Define snapshot/versioning policy for imported knowledge.
- Define manifests that track raw coverage versus implemented coverage.
- Define how set-based implementation status is declared for cards.

# Execution Plan: Source Strategy And Coverage

## Goal

Turn the selected external authorities into a durable repository strategy for ingestion, provenance, and incremental implementation coverage.

## Status

- Phase: active
- Acquisition scaffold: in place for the initial micro-universe and current rules snapshot
- Remaining blocker type: engine-facing contract refinement before package scaffolding

## Why This Plan Exists

The project now has chosen sources:

- Scryfall for card data
- Wizards of the Coast Comprehensive Rules for game logic

That choice creates a second problem: raw source material is much broader than implemented simulator behavior. We need a plan that prevents the repository from implying false coverage.

## Core Design Principle

Maintain three distinct layers:

1. Raw source snapshots
2. Internal contracts and normalized models
3. Declared implementation coverage

The simulator should only claim support based on layer 3, never merely because layers 1 or 2 exist.

## Progress Notes

- Source artifact provenance contract now exists for card metadata, card images, and rules snapshots.
- The repository now has a repeatable pull script under `information/` for:
  - `Border Guard`
  - `Foot Soldiers`
  - `Muck Rats`
  - `Swamp`
  - `Forest`
  - `Island`
  - `Mountain`
  - `Plains`
  - the current official Wizards plain-text Comprehensive Rules snapshot
- Pulled artifacts now exist in-repo with stable filenames and sidecar provenance.
- Coverage manifests remain YAML as the canonical support declaration for the current micro-universe.
- Narrative companion markdown should be added only when the supported rule surface grows beyond the current small slice.
- Engine implementation now covers deterministic setup, turn progression through cleanup and next-turn handoff, precombat-main legal-action enumeration, combat declaration action windows, priority passing across the currently supported forced-pass branch, land play, five-basic-land mana production, creature spell casting, and minimal combat with multi-block support.
- The first targeted-sorcery increment is now in place via `Vengeance`, the next destruction expansion was `Path of Peace`, and the next narrow sorcery expansion is `Touch of Brilliance` to add simple spell-driven card draw without introducing keywords, triggers, or multi-targeting.
- The fixed micro-universe model is now showing strain; the next structural improvement should be a manifest-driven support-slice model rather than continued growth of hardcoded scope lists.

## Workstreams

### 1. Source Acquisition

- Define how Scryfall metadata syncs will work.
- Define how and when card images are downloaded.
- Define how Wizards rules text snapshots are stored.
- Record provenance fields required for all imported artifacts.
- Enforce repository layout under `information/`, `information/cards/`, and `information/rules/`.

### 2. Rules Coverage Model

- Segment raw comprehensive-rules text into addressable rules or rule families.
- Define a coverage manifest that marks rule areas as `implemented`, `deferred`, or `not started`.
- Link implemented rule areas to specific engine contracts and tests.

### 3. Card Coverage Model

- Normalize Scryfall data into a canonical internal card model.
- Declare implementation waves by set.
- Track per-set status and any explicitly deferred cards or mechanics within those sets.
- Start with `Portal` (`por`) as the first implementation wave.

### 4. Contract Interaction

- Decide which parts of the raw rules corpus are referenced directly by contracts.
- Decide when a contract may intentionally simplify or collapse multiple official rules.
- Define how those simplifications are recorded so the repo stays honest.

## Proposed Raw-To-Implemented Pipeline

For rules:

1. Archive official text snapshot.
2. Index by section/rule number.
3. Group into engine-relevant rule families.
4. Write or update contracts for those families.
5. Mark coverage status.
6. Only then implement engine behavior.

For cards:

1. Archive Scryfall source snapshot.
2. Normalize into canonical card records.
3. Declare a target set for implementation.
4. Identify mechanics required by that set.
5. Map cards in that set to supported versus deferred behavior.
6. Only then implement engine behavior.

## Decisions Needed

- The initial rules envelope tied to that set

## Suggested Next Deliverables

1. A provenance and snapshot policy for external sources
2. Concrete coverage manifests for the initial micro-universe
3. A `Portal`-specific first rules envelope

## Immediate Next Actions

1. Draft the support-slice model that separates source scope, coverage declarations, and declared playable scope.
2. Add a support-slice manifest contract and plan the migration away from hardcoded micro-universe lists.
3. Keep card and rules coverage manifests canonical while support slices are introduced as the grouping layer above them.
4. Only continue widening the `Portal` engine slice after that structural migration is at least planned in repo-local docs.

## Resume Here

The next session should continue the engine-facing plan, but the immediate prerequisite is structural cleanup around support-scope declaration.

1. Add the first support-slice manifest representing the current `portal_initial_micro_universe`.
2. Refactor repository and engine-loading assumptions so the active slice comes from manifest data instead of hardcoded oracle ID sets.
3. Update tests and coverage docs to validate slice membership explicitly.
4. After that migration lands, inspect `Portal` again for the next smallest non-keyword card group, with direct-damage or card-draw sorceries as likely next candidates.

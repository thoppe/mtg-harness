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

1. Choose the next text-bearing, non-keyword `Portal` card or small card group that expands the engine without forcing keywords or broad triggered-ability support.
2. Update the rules envelope and coverage manifests for that next rule family before implementation code claims support.
3. Extend the engine through simple noncreature spell casting and resolution before widening into more complex combat variants, replacement effects, or triggered abilities.
4. Keep coverage declarations canonical in YAML until the supported rule surface grows enough to justify narrative companion docs.

## Resume Here

The next session should continue engine work, not return to ingestion scaffolding.

1. Inspect `Portal` for the next low-complexity text-bearing card group and choose one that adds the smallest new rule family.
2. Record that choice in the rules envelope and coverage manifests before implementing it.
3. Add the smallest missing engine capability for that card group, with simple sorcery or other noncreature spell resolution preferred over more complex mechanic families.
4. Add replay-trace assertions and keep the rules and coverage declarations honest as new turn windows or card mechanics are introduced.

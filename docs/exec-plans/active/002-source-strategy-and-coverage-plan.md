# Execution Plan: Source Strategy And Coverage

## Goal

Turn the selected external authorities into a durable repository strategy for ingestion, provenance, and incremental implementation coverage.

## Status

- Phase: active
- Acquisition scaffold: in place for the initial micro-universe and current rules snapshot
- Remaining blocker type: continue narrow Portal engine widening without outrunning declared coverage

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
- The first targeted-sorcery increment is now in place via `Vengeance`, the next destruction expansion was `Path of Peace`, the next narrow sorcery expansion was `Touch of Brilliance`, `Time Ebb` now covers targeted battlefield-to-library-top movement, `Armored Pegasus` established the first minimal flying-keyword card, and `Wall of Granite` now establishes the first strict `Defender` card.
- The manifest-driven support-slice model is now in place and the active slice is loaded from `docs/coverage/slices/portal.initial.yaml` instead of a hardcoded card universe list.
- `Rain of Salt` and `Wrath of God` now cover fixed multi-target land destruction and global creature destruction, while `Sacred Nectar` covers the smallest no-target life-gain sorcery family.
- `Keen-Eyed Archers` now covers the minimal `Reach` combat-blocking exception required to block flying attackers.
- The next requested expansion is `Hand of Death`, which should add only the minimal target-color restriction required for `Destroy target nonblack creature.`

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

## Deferred Next Candidate

- After `Wall of Granite`, the next candidate should return to the smallest nonkeyword `Portal` expansion rather than widening further keyword support.
- Favor direct-damage or similarly narrow sorcery patterns before adding broader static-ability, replacement-effect, or triggered-ability families.

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

1. Keep the support-slice manifest canonical as the engine-loadable source of active card scope.
2. Continue widening the `Portal` engine slice in narrow increments, preferring sorceries by default but allowing isolated keyword cards when a human explicitly selects the next target.
3. Update coverage manifests, contracts, and source artifacts in the same change that widens support.
4. Keep any keyword expansion name-scoped and minimal rather than introducing a general keyword framework prematurely.

## Resume Here

The next session should continue from the manifest-backed slice now that the structural cleanup is complete.

1. Keep `docs/coverage/slices/portal.initial.yaml` aligned with the declared active card universe and source pull scope.
2. Widen the next `Portal` increment through the smallest requested rule family expansion, keeping the implementation explicitly name-scoped when a human picks the target card.
3. `Hand of Death` is the current next card, and it should introduce only the minimal nonblack-creature target restriction needed by its printed sorcery text.
4. Update contracts and coverage first, then pull source artifacts, then implement engine behavior and tests.

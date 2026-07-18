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
- The repository now has a repeatable pull script under `information/` for active support-slice Scryfall card artifacts and the current official Wizards plain-text Comprehensive Rules snapshot.
- Pulled artifacts now exist in-repo with stable filenames and sidecar provenance.
- Coverage manifests remain YAML as the canonical support declaration for the current micro-universe.
- Narrative companion markdown should be added only when the supported rule surface grows beyond the current small slice.
- Engine implementation now covers deterministic setup, turn progression through cleanup and next-turn handoff, precombat-main legal-action enumeration, combat declaration action windows, priority passing across the currently supported forced-pass branch, land play, five-basic-land mana production, creature spell casting, and minimal combat with multi-block support.
- The first targeted-sorcery increment is now in place via `Vengeance`, the next destruction expansion was `Path of Peace`, the next narrow sorcery expansion was `Touch of Brilliance`, `Time Ebb` now covers targeted battlefield-to-library-top movement, `Armored Pegasus` established the first minimal flying-keyword card, and `Wall of Granite` now establishes the first strict `Defender` card.
- The manifest-driven support-slice model is now in place and the active slice is loaded from `docs/coverage/slices/portal.initial.yaml` instead of a hardcoded card universe list.
- `Rain of Salt` and `Wrath of God` now cover fixed multi-target land destruction and global creature destruction, while `Sacred Nectar` covers the smallest no-target life-gain sorcery family.
- `Keen-Eyed Archers` now covers the minimal `Reach` combat-blocking exception required to block flying attackers.
- `Hand of Death` now covers the minimal target-color restriction required for `Destroy target nonblack creature.`
- `Anaconda` now covers the minimal `Swampwalk` attack-evasion restriction required when the defending player controls a `Swamp`, and combat legality now flows through the shared keyword-aware validation surface.
- `Tidal Surge` now covers the minimal targeted creature-tapping sorcery path required for `Tap up to three target creatures without flying.`
- Wave 2 now covers its eight temporary-characteristic/evasion spells and twelve
  simple combat-restriction creatures. Targeted Wave 2 spells participate in
  legal-action enumeration, Valorous Charge affects every white creature as its
  oracle text requires, and focused coverage lives in
  `engine/tests/test_wave2.py`.
- Wave 3 now covers its 26 non-Alabaster creature promotions plus Alabaster
  Dragon's separately contracted, name-scoped death trigger. The latter
  captures last-known identity, resolves through the existing priority stack,
  and uses deterministic owner-library shuffling only on a successful
  resolution.
- Wave 4 now covers its 21 combat-card promotions, including the bounded
  `Mountainwalk` -> `Mountain` mapping and Haste exception. Wave 5 has a
  dependency-ordered contract sequence for its nineteen draw/discard,
  hidden-zone, search, ordering, additional-cost, and X-cost candidates; it is
  not active support until its source, coverage, implementation, and tests
  land together.

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

- The next candidate should return to the smallest nonkeyword `Portal` expansion rather than widening further keyword support.
- Favor sorceries that fit or minimally extend the current supported effect families before adding broader static-ability, replacement-effect, or triggered-ability families.

## Selected Next Increment

- **Rain of Tears** (`72cecab3-519e-4a23-9623-b423a5c5a251`, `Portal`):
  `Destroy target land.`
- It is a nonkeyword sorcery and fits the already implemented targeted-land
  destruction family (`Winter's Grasp`) while deliberately exercising a new
  black mana cost. It introduces no new target category, event family,
  replacement effect, trigger, or keyword.
- This selection is implemented and active; its fifteen-card completion note
  below is the canonical record of the widened support boundary.

## Expansion Completion Note

The selected `Rain of Tears` increment was completed as part of a fifteen-card
Portal sorcery wave. The active manifest, source artifacts, coverage,
implementation registry, and regression tests now cover all fifteen selected
cards.

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

## Card-Expansion Freshness Check

Every change that adds, removes, or promotes a card must update or deliberately re-affirm these surfaces in the same change:

1. Source artifacts under `information/cards/` and their provenance sidecars.
2. The active support-slice manifest in `docs/coverage/slices/`.
3. `docs/coverage/cards.initial.yaml` and `docs/coverage/rules.initial.yaml`.
4. The relevant product spec and rules envelope under `docs/product-specs/`.
5. Any contract whose expected scope would otherwise contain a copied card list or stale rule-family statement.
6. This active execution plan's progress notes and `Resume Here` section.
7. Root routing text in `AGENTS.md` only if its next-step guidance would otherwise name a completed card.

Prefer links to canonical manifests over duplicated card lists. If a copied list is necessary, update it in the same change and run a text search for the old card name or old "next card" wording before finishing.

## Resume Here

The next session should continue from the manifest-backed slice after the
completed Wave 4 creature, Mountainwalk, and Haste batch, using Wave 5's
dependency-ordered contracts rather than promoting its raw sources as a group.

1. Treat the active support-slice manifest as the only playable card-universe
   declaration; source artifacts alone do not imply support.
2. Preserve the completed Wave 4 boundary: Mountain Goat extends only the
   explicit landwalk mapping with `Mountainwalk` -> `Mountain`; Raging Cougar,
   Raging Goblin, Raging Minotaur, and Volcanic Dragon have only the printed
   Haste exception to entered-this-turn attacker legality. The other Wave 4
   cards reuse the declared creature and combat predicates. Do not infer
   generic static or triggered-ability support from this batch.
3. Preserve Alabaster Dragon's trigger boundary: it is limited to oracle ID
   `2392a41a-59d3-4749-be94-4d9df0af9c4c`, records last-known identity when it
   dies, and shuffles only that card instance from its owner's graveyard on
   successful trigger resolution.
4. Do not use the Alabaster implementation to claim generic triggered
   abilities, generic shuffle effects, replacement effects, or ordering logic.
5. Before each implementation subwave, update source artifacts, manifest,
   coverage, rules envelope, registry, and edge-case tests together; before
   finishing, run the card-expansion freshness check above.
6. Start Wave 5A only with its three fixed/public-derived cards, then advance
   through Wave 5B–5I in `docs/contracts/portal-expansion-order.md`. Preserve
   `docs/contracts/wave5-hidden-zone-expansion.md` as the authority for hidden
   visibility, decision sequencing, and RNG cursor use.

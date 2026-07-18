# Contract: Portal Expansion Order

## Purpose

Declare the implementation order for every Portal card outside the active support slice. This is a planning contract, not an implementation claim: a card is supported only after source, manifest, coverage, code, and tests land together.

## Ordering Rule

Within a numbered wave, implement cards in the printed order. Finish the wave's rule family and edge cases before entering the next wave.

The final four entries of the next twenty are gated by shared foundations:
choices/RNG before the tutors, a per-turn land-play allowance before Summer
Bloom, and combat requirements before Alluring Scent. They must not be
special-cased in the sorcery resolver.

## Next Twenty

1. **Burning Cloak** — combines target damage with temporary power.
2. **Monstrous Growth** — extends temporary power to toughness.
3. **Nature's Ruin** — global creature destruction filtered by color.
4. **Virtue's Ruin** — confirms that color-filtered destruction family.
5. **Boiling Seas** — global land destruction filtered by land subtype.
6. **Flashfires** — confirms subtype filtering for Plains.
7. **Dry Spell** — fixed damage to every creature and player.
8. **Fire Tempest** — larger batch damage and terminal player outcomes.
9. **Hurricane** — flying-filtered creature damage plus player damage.
10. **Spitting Earth** — target damage derived from controlled-land count.
11. **Fruition** — life gain derived from battlefield count.
12. **Renewing Dawn** — opponent-targeted, filtered battlefield-count gain.
13. **Theft of Dreams** — card draw derived from tapped-creature count.
14. **Vampiric Feast** — any-target damage plus life gain.
15. **Breath of Life** — graveyard creature card to battlefield movement.
16. **Déjà Vu** — graveyard sorcery-card type restriction.
17. **Personal Tutor** — search, reveal, shuffle, and library-top placement.
18. **Sylvan Tutor** — reusable tutor path with creature filtering.
19. **Summer Bloom** — additional land-play allowance in turn state.
20. **Alluring Scent** — forced-blocking constraint in blocker enumeration.

## Remaining Ordered Waves

### Wave 2: Temporary-stat and simple combat surface

Reason: reuse temporary P/T state before triggers or choices. Angelic Blessing, Cloak of Feathers, Steadfastness, Warrior's Charge, Valorous Charge, Nature's Cloak, Dread Charge, Treetop Defense, Sacred Knight, Fleet-Footed Monk, Charging Rhino, Stalking Tiger, Phantom Warrior, Craven Giant, Craven Knight, Hulking Cyclops, Hulking Goblin, Jungle Lion, Deep-Sea Serpent, Cloud Dragon.

### Wave 3: Dependency-ordered creature expansion

Wave 3 supersedes the within-wave printed-order rule. Its cards are grouped by
the smallest shared rule increment instead. A card is not supported merely
because its source artifact exists or a superficially similar card is in the
active slice.

#### Wave 3A: Existing casting and combat behavior

Reason: promote only cards whose behavior is already represented by the active
slice: vanilla creatures, Flying, Reach, Swampwalk, or Forestwalk. Coral Eel,
Elvish Ranger, Giant Octopus, Goblin Bully, Gorilla Warrior, Grizzly Bears,
Highland Giant, Hill Giant, Horned Turtle, Knight Errant, Lizard Warrior,
Merfolk of the Pearl Trident, Devoted Hero, Arrogant Vampire, Desert Drake,
Djinn of the Lamp, Feral Shadow, Giant Spider, Bog Raiders, Bog Wraith, Elite
Cat Warrior.

#### Wave 3B: Shared flying-only blocker restriction

Reason: Cloud Pirates and Cloud Spirit each have Flying and can block only
creatures with Flying. Generalize the existing Cloud Dragon behavior into one
bounded combat predicate shared by those three named cards; do not leave a
card-name special case in blocker validation.

#### Wave 3C: Islandwalk

Reason: Bull Hippo requires the existing landwalk check to use an explicit
supported-keyword-to-land-subtype mapping that includes Islandwalk alongside
the currently supported Swampwalk and Forestwalk. This is not a general
land-type-changing or arbitrary-landwalk framework.

#### Wave 3D: Vigilance

Reason: Archangel and Ardent Militia require the attacker-declaration rule to
leave a creature with Vigilance untapped. The increment is limited to that
exception; it must preserve the creature's ability to block later in combat.

#### Wave 3E: Alabaster Dragon's bounded triggered death ability

Alabaster Dragon (`2392a41a-59d3-4749-be94-4d9df0af9c4c`) adds the one
name-scoped trigger foundation required by its oracle text: detect its death
after the destruction or state-based-action operation completes, capture last-known source identity and owner, put a
trigger entry on the stack, then resolve it through the ordinary deterministic
priority cycle. A successful resolution moves the same card instance from its
owner's graveyard into that library and shuffles it; if it left the graveyard,
the trigger has no effect and consumes no RNG cursor. This does not create a
generic trigger dispatcher or special-case zone movement.

### Wave 4: Combat exceptions and haste

Reason: extend shared combat-legality checks before triggered combat text. Minotaur Warrior, Moon Sprite, Mountain Goat, Panther Warriors, Python, Raging Cougar, Raging Goblin, Raging Minotaur, Redwood Treefolk, Regal Unicorn, Rowan Treefolk, Skeletal Crocodile, Skeletal Snake, Snapping Drake, Spined Wurm, Spotted Griffin, Starlit Angel, Volcanic Dragon, Wall of Swords, Whiptail Wurm, Willow Dryad.

### Wave 5: Draw, discard, hidden zones, and deterministic ordering

Reason: add explicit hidden-zone view and choice policies before search/randomness. Ancestral Memories, Balance of Power, Baleful Stare, Cruel Bargain, Cruel Fate, Mind Knives, Omen, Prosperity, Sorcerous Sight, Temporary Truce, Withering Gaze, Flux, Winds of Change, Gift of Estates, Nature's Lore, Untamed Wilds, Cruel Tutor, Natural Order, Starlight.

### Wave 6: Variable damage, multi-targeting, costs, and delayed turn rules

Reason: require target allocation, X-cost payment, sacrifice costs, or derived values. Blaze, Earthquake, Forked Lightning, Wicked Pact, Final Strike, Devastation, Exhaustion, False Peace, Taunt, Last Chance.

### Wave 7: Triggers, activated abilities, instants, and prevention

Reason: require a trigger/ability queue, response windows, prevention/replacement, or mandatory additional-cost model. Assassin's Blade, Blessed Reversal, Capricious Sorcerer, Charging Bandits, Charging Paladin, Command of Unsummoning, Deep Wood, Defiant Stand, Dread Reaper, Ebon Dragon, Endless Cockroaches, Fire Dragon, Fire Imp, Fire Snake, Gravedigger, Harsh Justice, Ingenious Thief, King's Assassin, Man-o'-War, Mercenary Knight, Mystic Denial, Noxious Toad, Owl Familiar, Pillaging Horde, Plant Elemental, Primeval Force, Scorching Winds, Seasoned Marshal, Serpent Assassin, Serpent Warrior, Spiritual Guardian, Stern Marshal, Thing from the Deep, Thundering Wurm, Thundermare, Undying Beast, Venerable Monk, Wood Elves.

## Deliberate Deferrals

- Random selection needs a replayable RNG contract.
- Search/shuffle needs explicit hidden-zone and shuffle semantics.
- Instants need response priority beyond the sorcery-only surface.
- Triggered and activated creature text needs a general event/ability model; do not special-case it.

## Source of Truth

The candidate universe is Scryfall `set:por` compared against `docs/coverage/slices/portal.initial.yaml`. Re-evaluate this contract when the active manifest changes; raw artifacts alone do not change support status.

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

Wave 4 is dependency-ordered, rather than printed-order, so every card is
promoted only through an existing combat predicate or one of its two narrow
increments. It introduces no triggered text, general static-ability framework,
or effect parsing.

#### Wave 4A: Existing creature and combat behavior

Minotaur Warrior, Moon Sprite, Panther Warriors, Python, Redwood Treefolk,
Regal Unicorn, Rowan Treefolk, Skeletal Crocodile, Skeletal Snake, Snapping
Drake, Spined Wurm, Spotted Griffin, Starlit Angel, and Whiptail Wurm reuse
vanilla, Flying, and existing casting/combat behavior. Wall of Swords reuses
the existing Defender plus Flying predicates; Willow Dryad reuses Forestwalk.

#### Wave 4B: Mountainwalk

Mountain Goat adds `Mountainwalk` -> `Mountain` to the explicit supported
landwalk mapping. This is a narrow extension of the existing landwalk
predicate, not support for land-type changes or arbitrary landwalk names.

#### Wave 4C: Haste

Raging Cougar, Raging Goblin, Raging Minotaur, and Volcanic Dragon add only
the printed Haste exception to the entered-this-turn attack restriction.
Volcanic Dragon combines that exception with existing Flying. This does not
add triggered abilities, alternate combat timing, or a generic static-ability
framework.

### Wave 5: Draw, discard, hidden zones, and deterministic ordering

Wave 5 supersedes the within-wave printed-order rule. It is dependency ordered:
each subwave establishes one explicitly bounded decision, visibility, random,
or zone-ordering surface before a card relies on it. Source artifacts alone do
not make any of these cards supported.

#### Wave 5A: Fixed and public derived effects

`Cruel Bargain`, `Balance of Power`, and `Starlight` add fixed multi-card draw
with rounded life loss, target-opponent hand-size comparison, and counted
life gain for target opponent's black creatures. These effects use public
zone/battlefield counts and existing life/draw movement; they create neither a
hidden-zone decision nor a general arithmetic expression evaluator.

#### Wave 5B: Opponent-hand inspection and card-property counting

`Sorcerous Sight`, `Baleful Stare`, and `Withering Gaze` add only the
controller-visible inspection/reveal outputs their text requires, followed by
the printed fixed or counted draw. `Baleful Stare` and `Withering Gaze` count
each revealed card once when it is respectively red-or-a-Mountain or
green-or-a-Forest. This is not persistent hand visibility, generalized
information sharing, or arbitrary card-text predicates.

#### Wave 5C: Deterministic random hand discard

`Mind Knives` adds one deterministic uniform selection from a nonempty target
opponent hand, then moves that chosen card to its owner's graveyard. It uses
the versioned RNG cursor exactly once on successful selection; an empty hand
does not consume RNG. It does not let a player choose the discarded card.

#### Wave 5D: Sequential optional and multi-card decisions

`Temporary Truce` and `Flux` extend the pending-decision contract with
ordered resolver continuations: each affected player chooses in active-player
then nonactive-player order. Temporary Truce permits a count from zero through
two for each player, then grants that player two life for every forgone draw.
Flux lets each player choose any subset of that player's hand to discard,
draws the recorded count, then draws one card for its caster. These are
name-scoped choice schemas, not a general modal or simultaneous-choice engine.

#### Wave 5E: Hand-to-library shuffle and replacement draws

`Winds of Change` records each player's pre-resolution hand count, moves that
entire hand into its owner's library, shuffles that library once per affected
player in active-player then nonactive-player order, and draws the recorded
count. Empty hands still shuffle and consume one cursor under the ordinary
``shuffle`` instruction. This does not introduce generic hand replacement or
mass-zone-change parsing.

#### Wave 5F: Search with bounded cardinality and destinations

`Gift of Estates`, `Nature's Lore`, `Untamed Wilds`, and `Cruel Tutor` extend
the existing private-library chooser path. Gift conditionally chooses zero to
three Plains cards, reveals them, moves them to hand, then shuffles; Nature's
Lore and Untamed Wilds choose one Forest or basic-land card respectively and
put it onto the battlefield before shuffling; Cruel Tutor chooses one card,
shuffles, places that same card on top, then loses two life. Every search
shuffles even after an explicit no-selection. The scope excludes arbitrary
search predicates, replacement effects, and library-wide public disclosure.

#### Wave 5G: Look, select, and order a bounded library prefix

`Ancestral Memories`, `Omen`, and `Cruel Fate` add chooser-visible top-prefix
decisions. Ancestral Memories selects exactly the available minimum of two
cards from the top seven for hand and moves the rest to its owner's graveyard;
Omen orders the top available minimum of three, optionally shuffles, then
draws; Cruel Fate's controller selects one card from the target opponent's top
available minimum of five for that player's graveyard and orders the remainder
on top. The recorded order is authoritative and does not reveal looked-at
identities unless the oracle text says to reveal them.

#### Wave 5H: Green-creature sacrifice cost plus search

`Natural Order` adds only its name-scoped additional casting cost: choose and
sacrifice one green creature controlled by the caster while casting. On
resolution, privately choose a green creature card in that library, put it
onto the battlefield, then shuffle. This reuses the Wave 5F search decision
and introduces neither a general additional-cost framework nor generic
sacrifice-cost support.

#### Wave 5I: Variable-cost all-player draw

`Prosperity` is last because it needs an explicit nonnegative X declaration,
colored-plus-generic payment validation, and sequential each-player draw.
This increment is limited to Prosperity's X value; it is not a general
variable-cost or multi-targeting framework.

### Wave 6: Variable damage, multi-targeting, costs, and delayed turn rules

Wave 6 is dependency ordered. Its effects are bounded by
`docs/contracts/wave6-damage-and-turn-effects.md`; source artifacts alone do
not make any of these cards supported.

#### Wave 6A: X damage and immutable divided allocations

`Blaze`, `Earthquake`, and `Forked Lightning` extend the existing X snapshot
only through X damage, a nonflying global-damage filter, and a one-to-three
distinct-target positive allocation totaling four. A target becoming illegal
does not redistribute declared Forked Lightning damage.

#### Wave 6B: Snapshot sacrifice value and reuse-only destruction

`Wicked Pact`, `Final Strike`, and `Devastation` add exactly two nonblack
creature targets, Final Strike's required creature sacrifice and captured
power, and combined global creature/land destruction. This is not generic
additional-cost or multi-target support.

#### Wave 6C: One-next-turn restriction markers

`Exhaustion`, `False Peace`, and `Taunt` add serializable, consumable markers
for one target player's next untap step, next turn's combat phases, and next
attacker declaration respectively. They reuse current turn and combat
validation rather than introduce generic continuous effects.

#### Wave 6D: One queued extra turn with a terminal outcome

`Last Chance` adds one caster-owned queued turn immediately after the current
turn and a name-scoped loss at the beginning of that extra turn's end step.
It must not be represented as generic triggered-ability or extra-turn support.

### Wave 7: Triggers, activated abilities, instants, and prevention

Reason: require a trigger/ability queue, response windows, prevention/replacement, or mandatory additional-cost model. Assassin's Blade, Blessed Reversal, Capricious Sorcerer, Charging Bandits, Charging Paladin, Command of Unsummoning, Deep Wood, Defiant Stand, Dread Reaper, Ebon Dragon, Endless Cockroaches, Fire Dragon, Fire Imp, Fire Snake, Gravedigger, Harsh Justice, Ingenious Thief, King's Assassin, Man-o'-War, Mercenary Knight, Mystic Denial, Noxious Toad, Owl Familiar, Pillaging Horde, Plant Elemental, Primeval Force, Scorching Winds, Seasoned Marshal, Serpent Assassin, Serpent Warrior, Spiritual Guardian, Stern Marshal, Thing from the Deep, Thundering Wurm, Thundermare, Undying Beast, Venerable Monk, Wood Elves.

## Deliberate Deferrals

- Random selection needs a replayable RNG contract.
- Search/shuffle needs explicit hidden-zone and shuffle semantics.
- Instants need response priority beyond the sorcery-only surface.
- Triggered and activated creature text needs a general event/ability model; do not special-case it.

## Source of Truth

The candidate universe is Scryfall `set:por` compared against `docs/coverage/slices/portal.initial.yaml`. Re-evaluate this contract when the active manifest changes; raw artifacts alone do not change support status.

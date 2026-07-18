# Contract: Portal Expansion Order

## Purpose

Declare the implementation order for every Portal card outside the active support slice. This is a planning contract, not an implementation claim: a card is supported only after source, manifest, coverage, code, and tests land together.

## Ordering Rule

Within a numbered wave, implement cards in the printed order. Finish the wave's rule family and edge cases before entering the next wave.

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

### Wave 3: Vanilla creatures and existing keyword reuse

Reason: casting/combat coverage only, or existing Flying, Reach, Defender, Swampwalk, and landwalk. Alabaster Dragon, Archangel, Ardent Militia, Arrogant Vampire, Bog Raiders, Bog Wraith, Bull Hippo, Coral Eel, Desert Drake, Djinn of the Lamp, Elvish Ranger, Feral Shadow, Giant Octopus, Giant Spider, Goblin Bully, Gorilla Warrior, Grizzly Bears, Highland Giant, Hill Giant, Horned Turtle, Knight Errant, Lizard Warrior, Merfolk of the Pearl Trident, Cloud Pirates, Cloud Spirit, Devoted Hero, Elite Cat Warrior.

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

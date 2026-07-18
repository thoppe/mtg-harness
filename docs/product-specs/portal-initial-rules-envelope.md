# Portal Initial Rules Envelope

## Purpose

Define the smallest believable rules subset for the active card universe
declared by `docs/coverage/slices/portal.initial.yaml`.

## In Scope

- Two-player game setup
- Minimal turn and phase progression
- Basic zones: library, hand, battlefield, stack, graveyard
- Playing the five `Portal` basic lands
- Producing basic colored mana from those lands
- Casting and resolving simple sorcery-speed spells
- Basic creature combat
- Flying keyword support limited to the combat and blocking behavior required by `Armored Pegasus`, `Wind Drake`, `Bog Imp`, and `Storm Crow`
- Reach keyword support limited to the blocking behavior required by `Keen-Eyed Archers`
- Swampwalk keyword support limited to the unblockability condition required by `Anaconda`
- Defender keyword support limited to preventing `Wall of Granite` from attacking
- Wave 3A creature promotion limited to vanilla creatures and reuse of the
  existing Flying, Reach, Swampwalk, and Forestwalk combat behavior
- Islandwalk keyword support limited to the unblockability condition required
  by `Bull Hippo`
- Vigilance keyword support limited to leaving `Archangel` and `Ardent
  Militia` untapped when declared as attackers
- Flying-only blocker restriction limited to `Cloud Dragon`, `Cloud Pirates`,
  and `Cloud Spirit`
- Lethal damage and creature death as minimal state-based handling
- Sorcery-speed targeted destruction limited to `Destroy target tapped creature.` and `Destroy target creature. Its owner gains 4 life.`
- Sorcery-speed targeted destruction limited to the printed nonblack-creature restriction required by `Hand of Death`
- Sorcery-speed card draw limited to `Draw two cards.`
- Sorcery-speed targeted creature repositioning limited to `Put target creature on top of its owner's library.`
- Sorcery-speed targeted creature bounce limited to `Return target creature to its owner's hand.` plus draw-one follow-up for `Symbol of Unsummoning`
- Sorcery-speed targeted creature tapping limited to `Tap up to three target creatures without flying.`
- Sorcery-speed direct damage limited to `Volcanic Hammer deals 3 damage to any target.` and `Lava Axe deals 5 damage to target player or planeswalker.` with planeswalker targeting omitted in the current slice
- Sorcery-speed no-target life gain limited to `You gain 4 life.`
- Sorcery-speed targeted discard limited to `Target player discards two cards.` using deterministic hand-order selection in the current slice
- Sorcery-speed targeted land destruction limited to `Destroy target land.`
- Sorcery-speed fixed multi-target land destruction limited to `Destroy two target lands.`
- Sorcery-speed global land destruction limited to `Destroy all lands.`
- Sorcery-speed global creature destruction limited to `Destroy all creatures. They can't be regenerated.` with regeneration text ignored in the current slice
- Sorcery-speed opponent-targeted mass creature destruction limited to `Destroy all creatures target opponent controls. You lose 2 life for each creature destroyed this way.` in the current two-player slice
- Wave 2 temporary power/toughness and keyword effects represented by
  object-bound records that expire at cleanup or zone change
- The attacked-player instant response window required by `Treetop Defense`
- Shared, name-scoped attack and block restrictions for the Wave 2 creatures
- Deterministic setup inputs and replay traces for the above behaviors

## Engine-Facing Interpretation

- Setup must be reproducible from explicit player order, library order, opening-hand data, and RNG seed.
- Turn progression must move through named transition points rather than implicit control flow.
- Accepted actions and automatic rules outcomes must emit replay events in execution order.
- State-based actions for lethal damage must run at explicit checkpoints.
- Combat legality should flow through shared helper functions so attacker and blocker validation, as well as action enumeration, use the same keyword-aware rules surface.
- The first noncreature spell path may stay sorcery-speed only and may validate targets only against battlefield creatures in the declared micro-universe.
- `Vengeance` may reuse the existing tapped-state model from combat and mana activation rather than introducing a broader effect framework.
- `Path of Peace` may reuse the same targeted-destruction path while adding only owner life gain, without introducing damage prevention, regeneration, or broader effect layering.
- `Hand of Death` may reuse the existing targeted-destruction path while adding only the minimal printed-color target check needed to reject black creatures, without introducing color-changing effects, continuous color layers, or generalized protection-style filtering.
- `Touch of Brilliance` may reuse existing library-to-hand zone movement from turn draws while resolving as a no-target sorcery for exactly two cards.
- `Time Ebb` may reuse targeted sorcery selection while adding only battlefield-to-library-top movement for creatures, without introducing shuffle, reveal, or replacement-effect support.
- `Volcanic Hammer` and `Lava Axe` may introduce only the minimal direct-damage path required to mark damage on creatures, reduce player life totals, and run the existing lethal-damage SBA check, without introducing prevention, redirection, or planeswalker support.
- `Sacred Nectar` may introduce only the minimal no-target life-gain path required to increase the caster's life total by 4 and emit the corresponding life-total-change event, without introducing prevention, replacement effects, or generalized life-setting support.
- `Mind Rot` may introduce only the minimal targeted-discard path required for a player to discard exactly two cards, with the current deterministic implementation using the target player's hand order rather than a separate choice action.
- `Winter's Grasp` may introduce only the minimal targeted land-destruction path required to choose a land on the battlefield, move it to its owner's graveyard, and emit the matching destruction and zone-move events, without introducing mana burn, land animation, or broader permanent-destruction generalization.
- `Rain of Salt` may introduce only the minimal fixed multi-target land-destruction path required to choose exactly two distinct land targets on the battlefield, destroy those lands on resolution, and emit the matching destruction and zone-move events, without introducing generalized arbitrary target counts or retargeting support.
- `Symbol of Unsummoning` may introduce only the minimal targeted battlefield-to-hand path required to return a creature to its owner's hand and then draw one card for the caster, without introducing instant timing, save effects, or broader hand-size rules.
- `Tidal Surge` may introduce only the minimal targeted creature-tapping path required to choose zero to three distinct nonflying creature targets and tap those creatures on resolution, without introducing tap triggers, untap prevention, or broader status-effect support.
- `Armageddon` may introduce only the minimal global land-destruction path required to destroy all lands on the battlefield and emit the corresponding destruction and zone-move events, without introducing regeneration, replacement effects, or broader mass-destruction generalization.
- `Wrath of God` may introduce only the minimal global creature-destruction path required to destroy all creatures on the battlefield and emit the corresponding destruction and zone-move events, with the printed regeneration rider explicitly ignored in the current slice because regeneration is otherwise unsupported.
- `Rain of Daggers` may introduce only the minimal opponent-targeted mass creature-destruction path required to target the opposing player in a two-player game, destroy all creatures that player controls, count how many were destroyed this way, and reduce the caster's life total by 2 for each, without introducing broader multiplayer opponent selection, regeneration, or generalized linked delayed accounting.
- The fifteen-card sorcery expansion wave is limited to the named rule families in `docs/contracts/portal-sorcery-expansion-wave.md`: fixed reuse effects, player and graveyard targeting, mass status and damage, combined damage/life effects, and Howling Fury's explicit +4 power modifier through cleanup. It does not introduce generic effect parsing, prevention, choices, X costs, or broader continuous-effect layering.
- Wave 2 is limited to the temporary characteristics, attacked-player instant
  window, and shared combat legality described by
  `docs/contracts/characteristics-and-continuous-effects.md`,
  `docs/contracts/stack-and-priority.md`, and
  `docs/contracts/combat-requirements-and-evasion.md`. Valorous Charge applies
  to white creatures on both battlefields; the other controller-qualified mass
  effects remain limited to the caster's creatures.
- `Armored Pegasus`, `Wind Drake`, `Bog Imp`, and `Storm Crow` may introduce only the minimal flying restriction that nonflying creatures cannot block them; broader keyword handling remains out of scope until another card requires it.
- `Keen-Eyed Archers` may introduce only the minimal reach exception that it can block creatures with flying, without introducing broader anti-air combat text, continuous-effect layering, or generalized keyword interaction beyond the currently supported flying cards.
- `Anaconda` may introduce only the minimal swampwalk restriction that it cannot be blocked while the defending player controls a `Swamp`, without introducing generalized landwalk handling beyond the printed `Swampwalk` keyword or continuous land-type modification.
- `Wall of Granite` may introduce only the minimal defender restriction that it cannot be declared as an attacker; broader static-ability handling remains out of scope until another card requires it.
- Wave 3B may replace Cloud Dragon's name-only blocker check with one bounded
  predicate for Cloud Dragon, Cloud Pirates, and Cloud Spirit: each can block
  only creatures with Flying. Both action enumeration and submitted blockers
  must use that predicate.
- Wave 3C may extend the explicit landwalk mapping only with `Islandwalk` ->
  `Island` for Bull Hippo, preserving the existing Swampwalk and Forestwalk
  behavior and excluding land-type changes.
- Wave 3D may add only the Vigilance exception that an attacking Archangel or
  Ardent Militia does not tap. It introduces no broader static-ability or
  untap-effect system.

## Out Of Scope

- Keyword abilities beyond those declared by the active manifest and bounded
  contracts
- Triggered abilities not required by the initial cards
- Alabaster Dragon's death trigger, library shuffle, and all triggered-ability
  queue behavior pending a separate contract increment
- Replacement effects
- Continuous effects beyond the object-bound additive and keyword-granting
  Wave 2 model
- Color-changing effects or generalized color-layer recalculation
- Instants beyond the name-scoped `Treetop Defense` response window, and modal
  spells
- Multiplayer rules
- Format-legality enforcement
- Any card text not present in the declared micro-universe


## Envelope Rule

If a new card requires a new rule family outside this envelope, the manifests and contracts must be updated before engine code claims support.

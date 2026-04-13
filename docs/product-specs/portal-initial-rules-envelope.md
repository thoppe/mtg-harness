# Portal Initial Rules Envelope

## Purpose

Define the smallest believable rules subset for the initial `Portal` support slice built from `Border Guard`, `Foot Soldiers`, `Muck Rats`, `Vengeance`, `Path of Peace`, `Touch of Brilliance`, `Time Ebb`, and the five `Portal` basic lands.

## In Scope

- Two-player game setup
- Minimal turn and phase progression
- Basic zones: library, hand, battlefield, stack, graveyard
- Playing the five `Portal` basic lands
- Producing basic colored mana from those lands
- Casting and resolving simple sorcery-speed spells
- Basic creature combat
- Lethal damage and creature death as minimal state-based handling
- Sorcery-speed targeted destruction limited to `Destroy target tapped creature.` and `Destroy target creature. Its owner gains 4 life.`
- Sorcery-speed card draw limited to `Draw two cards.`
- Sorcery-speed targeted creature repositioning limited to `Put target creature on top of its owner's library.`
- Deterministic setup inputs and replay traces for the above behaviors

## Engine-Facing Interpretation

- Setup must be reproducible from explicit player order, library order, opening-hand data, and RNG seed.
- Turn progression must move through named transition points rather than implicit control flow.
- Accepted actions and automatic rules outcomes must emit replay events in execution order.
- State-based actions for lethal damage must run at explicit checkpoints.
- The first noncreature spell path may stay sorcery-speed only and may validate targets only against battlefield creatures in the declared micro-universe.
- `Vengeance` may reuse the existing tapped-state model from combat and mana activation rather than introducing a broader effect framework.
- `Path of Peace` may reuse the same targeted-destruction path while adding only owner life gain, without introducing damage prevention, regeneration, or broader effect layering.
- `Touch of Brilliance` may reuse existing library-to-hand zone movement from turn draws while resolving as a no-target sorcery for exactly two cards.
- `Time Ebb` may reuse targeted sorcery selection while adding only battlefield-to-library-top movement for creatures, without introducing shuffle, reveal, or replacement-effect support.

## Out Of Scope

- Keyword abilities
- Triggered abilities not required by the initial cards
- Replacement effects
- Continuous effects beyond what the initial cards require
- Instants, modal spells, and multi-target spells
- Multiplayer rules
- Format-legality enforcement
- Any card text not present in the declared micro-universe


## Envelope Rule

If a new card requires a new rule family outside this envelope, the manifests and contracts must be updated before engine code claims support.

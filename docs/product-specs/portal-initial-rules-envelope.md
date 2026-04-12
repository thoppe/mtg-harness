# Portal Initial Rules Envelope

## Purpose

Define the smallest believable rules subset for the initial three-card `Portal` micro-universe.

## In Scope

- Two-player game setup
- Minimal turn and phase progression
- Basic zones: library, hand, battlefield, stack, graveyard
- Playing `Plains`
- Producing white mana from `Plains`
- Casting `Border Guard`
- Casting `Foot Soldiers`
- Basic creature combat
- Lethal damage and creature death as minimal state-based handling
- Deterministic setup inputs and replay traces for the above behaviors

## Engine-Facing Interpretation

- Setup must be reproducible from explicit player order, library order, opening-hand data, and RNG seed.
- Turn progression must move through named transition points rather than implicit control flow.
- Accepted actions and automatic rules outcomes must emit replay events in execution order.
- State-based actions for lethal damage must run at explicit checkpoints.

## Out Of Scope

- Keyword abilities
- Triggered abilities not required by the initial cards
- Replacement effects
- Continuous effects beyond what the initial cards require
- Multiplayer rules
- Format-legality enforcement
- Any card text not present in the declared micro-universe

## Envelope Rule

If a new card requires a new rule family outside this envelope, the manifests and contracts must be updated before engine code claims support.

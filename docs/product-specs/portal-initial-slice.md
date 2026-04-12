# Portal Initial Slice

## Purpose

Define the first actually playable subset before broader `Portal` support.

## Card Universe

The initial playable universe contains only these legal card identities:

- `Border Guard` from `Portal`
- `Foot Soldiers` from `Portal`
- `Muck Rats` from `Portal`
- `Swamp` from `Portal`
- `Forest` from `Portal`
- `Island` from `Portal`
- `Mountain` from `Portal`
- `Plains` from `Portal`

This slice uses vanilla `Portal` creatures plus all five `Portal` basic lands to minimize the first rules envelope while still enabling colored mana tests and a real lethal-damage path.
Multiplicity is allowed as normal so long as no card identity outside this universe is introduced.

## Play Mode

- Two-player only
- Normal gameplay structure only
- No multiplayer support
- No format-legality enforcement beyond the explicitly chosen card universe

## Card Text Authority

- Use Scryfall oracle text only for gameplay behavior.
- Ignore flavor text for implementation decisions.

## Initial Constraints

- No keyword support is required in the first slice.
- The first slice should implement only the rule families actually needed by this universe.
- Any new card added beyond this universe should trigger a rules-gap review before implementation.

## Current Implementation Note

- The currently implemented slice supports deterministic setup, first-turn progression, land play, and basic-land mana generation.
- Additional setup scenarios may use multiple copies of the declared basic lands and vanilla creatures without widening the universe.

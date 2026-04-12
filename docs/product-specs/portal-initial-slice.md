# Portal Initial Slice

## Purpose

Define the first actually playable subset before broader `Portal` support.

## Card Universe

The initial playable universe contains only these legal card identities:

- `Border Guard` from `Portal`
- `Foot Soldiers` from `Portal`
- `Muck Rats` from `Portal`
- `Vengeance` from `Portal`
- `Path of Peace` from `Portal`
- `Swamp` from `Portal`
- `Forest` from `Portal`
- `Island` from `Portal`
- `Mountain` from `Portal`
- `Plains` from `Portal`

This slice uses vanilla `Portal` creatures, the sorceries `Vengeance` and `Path of Peace`, and all five `Portal` basic lands to widen the engine through a narrow targeted noncreature-spell path before broader mechanics are introduced.
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

- The currently implemented slice supports deterministic setup, first-turn progression, land play, basic-land mana generation, vanilla creature spell resolution, and the narrow targeted-sorcery path required for `Vengeance` and `Path of Peace`.
- Additional setup scenarios may use multiple copies of the declared basic lands and vanilla creatures without widening the universe.

# Portal Initial Slice

## Purpose

Define the first actually playable subset before broader `Portal` support.

## Card Universe

The initial playable universe contains only these legal card identities:

- `Border Guard` from `Portal`
- `Foot Soldiers` from `Portal`
- `Muck Rats` from `Portal`
- `Wind Drake` from `Portal`
- `Bog Imp` from `Portal`
- `Storm Crow` from `Portal`
- `Vengeance` from `Portal`
- `Path of Peace` from `Portal`
- `Touch of Brilliance` from `Portal`
- `Time Ebb` from `Portal`
- `Armored Pegasus` from `Portal`
- `Wall of Granite` from `Portal`
- `Swamp` from `Portal`
- `Forest` from `Portal`
- `Island` from `Portal`
- `Mountain` from `Portal`
- `Plains` from `Portal`

This slice uses mostly vanilla `Portal` creatures plus the simple flyers `Armored Pegasus`, `Wind Drake`, `Bog Imp`, and `Storm Crow`, the strict defender creature `Wall of Granite`, the sorceries `Vengeance`, `Path of Peace`, `Touch of Brilliance`, and `Time Ebb`, and all five `Portal` basic lands to widen the engine through a narrow keyword and sorcery-speed noncreature-spell path before broader mechanics are introduced.
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

- Keyword support stays minimal and only covers the printed `Flying` and `Defender` abilities required by the declared slice.
- The first slice should implement only the rule families actually needed by this universe.
- Any new card added beyond this universe should trigger a rules-gap review before implementation.

## Current Implementation Note

- The currently implemented slice supports deterministic setup, first-turn progression, land play, basic-land mana generation, creature spell resolution including minimal flying for `Armored Pegasus`, `Wind Drake`, `Bog Imp`, and `Storm Crow`, minimal defender for `Wall of Granite`, the narrow targeted-sorcery path required for `Vengeance` and `Path of Peace`, simple sorcery-driven card draw for `Touch of Brilliance`, and targeted battlefield-to-top-of-library movement for `Time Ebb`.
- Additional setup scenarios may use multiple copies of the declared basic lands and vanilla creatures without widening the universe.

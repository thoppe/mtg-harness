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
- `Volcanic Hammer` from `Portal`
- `Lava Axe` from `Portal`
- `Mind Rot` from `Portal`
- `Winter's Grasp` from `Portal`
- `Symbol of Unsummoning` from `Portal`
- `Armageddon` from `Portal`
- `Rain of Salt` from `Portal`
- `Armored Pegasus` from `Portal`
- `Wrath of God` from `Portal`
- `Wall of Granite` from `Portal`
- `Rain of Daggers` from `Masters Edition IV`
- `Swamp` from `Portal`
- `Forest` from `Portal`
- `Island` from `Portal`
- `Mountain` from `Portal`
- `Plains` from `Portal`

This slice uses mostly vanilla `Portal` creatures plus the simple flyers `Armored Pegasus`, `Wind Drake`, `Bog Imp`, and `Storm Crow`, the strict defender creature `Wall of Granite`, the sorceries `Vengeance`, `Path of Peace`, `Touch of Brilliance`, `Time Ebb`, `Volcanic Hammer`, `Lava Axe`, `Mind Rot`, `Winter's Grasp`, `Symbol of Unsummoning`, `Armageddon`, `Rain of Salt`, and `Wrath of God`, the off-Portal testbed sorcery `Rain of Daggers`, and all five `Portal` basic lands to widen the engine through narrow keyword and sorcery-speed noncreature-spell rule families before broader mechanics are introduced.
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

- The currently implemented slice supports deterministic setup, first-turn progression, land play, basic-land mana generation, creature spell resolution including minimal flying for `Armored Pegasus`, `Wind Drake`, `Bog Imp`, and `Storm Crow`, minimal defender for `Wall of Granite`, the narrow targeted-sorcery path required for `Vengeance`, `Path of Peace`, `Volcanic Hammer`, `Lava Axe`, `Winter's Grasp`, and `Rain of Salt`, simple sorcery-driven card draw for `Touch of Brilliance`, targeted battlefield-to-top-of-library movement for `Time Ebb`, targeted battlefield-to-hand movement plus draw for `Symbol of Unsummoning`, deterministic targeted discard for `Mind Rot`, and global/per-opponent mass destruction for `Armageddon`, `Wrath of God`, and `Rain of Daggers`.
- Additional setup scenarios may use multiple copies of the declared basic lands and vanilla creatures without widening the universe.

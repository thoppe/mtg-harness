# Portal Initial Slice

## Purpose

Define the first actually playable subset before broader `Portal` support.

## Card Universe

The legal card identities are declared exclusively by
`docs/coverage/slices/portal.initial.yaml`. The current slice includes the
bootstrap creatures, lands, and sorcery waves plus the completed Wave 2
temporary-characteristic, instant-response, evasion, and combat-restriction
batch described by `docs/contracts/portal-expansion-order.md`.

Multiplicity is allowed as normal so long as no card identity outside the
canonical manifest is introduced.

## Play Mode

- Two-player only
- Normal gameplay structure only
- No multiplayer support
- No format-legality enforcement beyond the explicitly chosen card universe

## Card Text Authority

- Use Scryfall oracle text only for gameplay behavior.
- Ignore flavor text for implementation decisions.

## Initial Constraints

- Keyword and combat-text support stays bounded to the families declared by the
  active manifest and rules envelope, including Wave 2's temporary `Forestwalk`
  and name-scoped attack/block restrictions. Wave 3 planning further bounds
  the next promotion sequence to existing behavior (3A), Cloud Dragon's shared
  flying-only blocker predicate (3B), Islandwalk (3C), and Vigilance (3D).
- Alabaster Dragon remains outside the active universe until a triggered-
  ability and deterministic-shuffle increment is explicitly contracted and
  implemented.
- The first slice should implement only the rule families actually needed by this universe.
- Any new card added beyond this universe should trigger a rules-gap review before implementation.

## Current Implementation Note

- The implemented slice supports every card declared by the active manifest.
  Coverage details and test links live in `docs/coverage/cards.initial.yaml`;
  Wave 2's focused effect, priority, and combat checks live in
  `engine/tests/test_wave2.py`, `engine/tests/test_priority.py`, and
  `engine/tests/test_portal_expansion_wave.py`.
- Additional setup scenarios may use multiple copies of the declared basic lands and vanilla creatures without widening the universe.

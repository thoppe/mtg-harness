# Contract: Game State

## Purpose

Define the core state boundaries for simulation.

## Minimum State Areas

- Players
- Turn and phase structure
- Zones
- Objects on the stack
- Battlefield objects and attachments
- Life totals, counters, and status markers
- Randomness source / seed state

## Guarantees

- Game state transitions must be inspectable.
- The engine must be able to explain why a legal action was accepted or rejected.
- Deterministic replay must be possible from explicit setup inputs plus the append-only event log.

## v0 Required State Partitions

- `players`: identifiers, life totals, and ownership relations
- `turn_state`: active player, step, and priority holder
- `zones`: library, hand, battlefield, graveyard, and stack
- `objects`: card-instance records keyed by stable `card_instance_id`, each
  carrying a monotonic zone-change counter and derived `object_id`
- `mana_pools`: at minimum the five basic colors needed for the current active support slice
- `rng_state`: deterministic seed and any derived RNG cursor state
- `pending_decision`: an optional, serializable chooser-owned continuation for
  an unresolved hidden-zone or modal choice; Wave 5 extends its payload only
  with the selected tuple/order/count/boolean and resolver-continuation forms
  declared in `wave5-hidden-zone-expansion.md`
- `damage_marks`: creature damage marked on objects until cleared by later turn handling
- `temporary_power_modifiers`: explicit, turn-bounded power and toughness
  changes on objects when a supported card grants them
- `land_play_limit_this_turn`: each player begins at one permitted land play;
  temporary effects may raise it and cleanup resets it to one
- `outcome`: in-progress or completed game status, winner/loser IDs, and terminal reason
- `next_turn_effects`: optional serializable, name-scoped markers for a named
  player's next untap step, next combat, or next attacker declaration; Wave 6
  defines Exhaustion, False Peace, and Taunt as the only permitted markers
- `turn_queue`: the normal next-player turn plus an optional name-scoped queued
  extra turn; Wave 6 permits only Last Chance's one caster-owned queued turn
  and its terminal end-step marker
- `pending_triggers`: serializable registered Wave 7 trigger records awaiting
  APNAP placement, each with source/event snapshots and any required expected
  zone identity
- `turn_damage_effects`: current-turn, caster-bound Wave 7 prevention and
  retaliation records; they expire at cleanup

## v0 State Rules

- Hidden-zone ordering must be stable and replayable.
- Zone movement must preserve the persistent card instance while creating a
  fresh object identity by incrementing its zone-change counter.
- The engine may derive convenience views, but replay cannot depend on untracked derived state.
- A pending decision is authoritative state: only its chooser and matching
  decision action may progress the game until it is consumed.
- The first slice may omit counters, attachments, and status markers not required by the active support slice.
- Damage marked on creatures must be represented explicitly rather than inferred only from event history.
- Trigger records and activated-ability stack entries must be explicit state;
  replay cannot infer their targets, source snapshots, or ordering from later
  zone contents.
- A player at zero or less life, or attempting to draw from an empty library,
  completes the game and emits a `game_ended` event with a deterministic reason.

## Open Questions

- What state should be persisted for debugging versus recomputed on demand?
- Should hidden information be modeled directly or through player-relative views?

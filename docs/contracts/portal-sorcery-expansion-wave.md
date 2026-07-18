# Contract: Portal Sorcery Expansion Wave

## Purpose

Define the bounded rule families for the next fifteen `Portal` sorceries. Each
card remains name-scoped through its canonical oracle ID; shared effect keys are
an implementation convenience, not a claim of general rules coverage.

## Included Families

- Exact reuse: `Rain of Tears` and `Stone Rain` destroy one target land;
  `Scorching Spear` and `Bee Sting` deal fixed damage to any target.
- Player targeting: `Natural Spring` gains life for one target player.
- Union target: `Lava Flow` destroys one target creature or land.
- Graveyard return: `Raise Dead` returns one target creature card and `Elven
  Cache` one target card from its owner's graveyard to their hand.
- Mass status: `Mobilize` untaps creatures its controller controls; `Blinding
  Light` taps all nonwhite creatures.
- Mass damage: `Pyroclasm` damages all creatures; `Needle Storm` damages all
  creatures with flying.
- Combined effects: `Soul Shred` damages a target nonblack creature and gains
  life; `Vampiric Touch` damages a target opponent and gains life.
- Temporary modification: `Howling Fury` grants a target creature +4/+0 until
  cleanup of the current turn.

## Required Boundaries

- Each targeted spell validates targets on cast and resolution; an invalid sole
  target counters the spell under the stack contract.
- Fixed damage must run state-based actions for both creature and player
  targets, including a terminal zero-life result.
- Graveyard returns use the target card's owner, reset object identity on every
  zone change, and do not return cards from another zone.
- Temporary power modifications are explicit state and are removed during
  cleanup; they must not survive a zone change.
- This wave excludes choices, X costs, search/shuffle, random discard,
  replacement/prevention effects, planeswalkers, and keyword expansion beyond
  the existing `Flying` predicate used by `Needle Storm`.

## Related Contracts

- `docs/contracts/stack-and-priority.md`
- `docs/contracts/object-identity-and-zone-changes.md`
- `docs/contracts/game-state.md`
- `docs/contracts/replay-event-log.md`

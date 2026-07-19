# Execution Plan: Legal Actions API And Long Traces

## Goal

Make the frozen Portal game engine consumable as a player-scoped legal-action
and valid-target surface, prove it through longer deterministic games, and
present those actions through a player-safe Rich terminal game surface.

## Ordered Work

1. Contract state revision, player scope, visibility, and rejection behavior.
2. Add versioned descriptor models for legal actions and parameter slots.
3. Derive valid-target candidates from the existing action enumeration path.
4. Keep target predicates and transition validation single-sourced.
5. Describe partial multi-target, ordered, allocation, X, sacrifice, and
   private-choice parameters.
6. Add session query and descriptor-submission methods with stale protection.
7. Apply role-based public/private redaction.
8. Add 10–30 turn Portal starter-deck trace scenarios.
9. Add seeded long-trace generation with action/replay/invariant assertions.
10. Route the CLI and JSON serialization through the descriptor surface and
    expose structured rejection results.
11. Contract a Rich-capable, player-safe terminal layout, including action
    completeness, event timeline, scenario boundary, and semantic snapshots.
12. Route the descriptor CLI through the Rich terminal surface without reading
    raw hidden state or changing action behavior.
13. Add deterministic named mid-game Portal scenarios for interesting action
    points, keeping legal decks separate from rules-harness scenarios.
14. Add terminal end-to-end and plain/Rich semantic-snapshot evidence for
    privacy, target collection, rejection refresh, and scenario flow.

## Verification

- API descriptor/target/rejection/redaction tests.
- Long scripted and generated trace tests across multiple seeds.
- Full engine and information suites, coverage parsing, and `git diff --check`.

## Status

- Phase: active
- Steps 1–7 are complete: revision-bound, player-scoped descriptors, valid
  target candidates, partial selection, structured rejections, and redaction
  all derive from the reducer's enumerated action variants.
- Steps 8–9 are complete: seeded white-versus-blue starter-deck traces now run
  for ten or more turns and assert legal-action use, deterministic traces,
  replay equivalence, and zone/object/stack invariants.
- Step 10 is complete: the CLI uses descriptor-driven parameter collection,
  including target candidates, multi-targets, ordered choices, X values,
  allocations, additional costs, and structured rejection refresh.
- Step 11 is complete: `docs/contracts/terminal-play-surface.md` defines the
  player-safe Rich terminal boundary, live action/event presentation, scenario
  launcher, and semantic-snapshot obligations.
- Steps 12–14 are complete: the descriptor CLI defaults to a player-safe Rich
  layout with a no-color path, named deterministic rules-harness scenarios,
  and semantic render/CLI/scenario coverage for privacy and action behavior.
- Follow-up hardening: declaring blockers now hands the bounded combat-damage
  continuation to the active player, so the player-scoped terminal cannot
  stop at a legal combat state with an action owned by another player.

## Resume Here

The legal-action, long-trace, and terminal-play work is complete. Keep future
terminal work descriptor-only and player-safe; new scenarios must remain
deterministic, declare their category, and never present a rules-harness state
as a legal Portal deck game.

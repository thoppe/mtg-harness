# Execution Plan: Legal Actions API And Long Traces

## Goal

Make the frozen Portal game engine consumable as a player-scoped legal-action
and valid-target surface, then prove it through longer deterministic games.

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
- Step 10 is complete for the versioned JSON/session surface. The existing
  numeric CLI remains a direct exact-action picker until a multi-parameter
  descriptor interaction flow is deliberately designed; it must not fake a
  descriptor-only UI by guessing targets.
- Descriptor-driven CLI parameter collection: active.

## Resume Here

Complete the descriptor-driven CLI parameter flow, including target candidates,
multi-targets, ordered choices, X values, allocations, additional costs, and
structured rejection refresh. Do not duplicate targeting rules, guess hidden
choices, or reveal hidden option IDs.

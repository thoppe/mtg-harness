# Execution Plan: Portal Decks And Playable Game

## Goal

Turn the frozen Portal card roster into a reproducible, legal-deck, two-player
playable game surface without weakening the explicit rules-harness path.

## Ordered Work

1. Add explicit deck eligibility to the support slice and exclude Rain of
   Daggers from Portal decks.
2. Implement the Portal Constructed v0 profile: exact 60-card decks, four-copy
   nonbasic limit, unrestricted basics, 20 life, seven-card opening hands,
   London mulligan, and no sideboards.
3. Add serializable deck-list and deck-profile models.
4. Validate eligibility, deck size, copy limits, and malformed deck entries.
5. Provide deterministic Portal deck fixtures and a deck-to-library builder.
6. Implement deterministic initial shuffle, opening draw, and private London
   mulligan decisions while retaining explicit harness setup.
7. Add a session facade that starts a legal game from decks and accepts only
   enumerated legal actions.
8. Route replay through the same action dispatch as the session facade.
9. Add a minimal numeric-action CLI that starts deck games, shows state/actions,
   writes replay input, and never exposes hidden identities.
10. Add bounded generated-game and end-to-end tests for valid decks, rejected
    decks, deterministic traces, replay equivalence, invariants, and terminal
    outcomes.

## Verification

- Focused deck, setup/mulligan, session, CLI, and generated-game tests.
- Full engine and information suites, coverage YAML parsing, and `git diff --check`.
- Assert every Portal deck excludes `Rain of Daggers`.

## Status

- Phase: complete
- All ten ordered steps are implemented: eligibility, profile, models,
  validation, starter decks, deterministic startup and London mulligans,
  deck-session facade, shared action dispatch/replay, numeric CLI, and bounded
  generated-game verification.

## Resume Here

Return to `026-adversarial-engine-verification.md` for the next bounded
hardening increment. Preserve the legal-deck/rules-harness boundary and do not
onboard cards or sets unless a human explicitly reopens expansion work.

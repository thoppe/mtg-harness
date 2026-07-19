# Execution Plan: Adversarial Engine Verification

## Goal

Increase confidence in the frozen 201-card Portal-led slice by trying to break
supported rules interactions before onboarding any additional card or set.

## Scope

- Preserve the active support-slice manifest, coverage manifests, and bounded
  Waves 1–7 contracts without adding cards, sets, or generic rule frameworks.
- Use Portal cards in hardening scenarios. `Rain of Daggers` remains available
  only to its dedicated opponent-mass-destruction rules harness and must not
  appear in a Portal deck fixture.
- Add small, explicit adversarial scenarios that combine already-supported
  actions, choices, resolution, replay, and state transitions.
- For each scenario, assert both the resulting state and the relevant public
  event trace; include replay reduction when the path is replayable.
- Repair an engine defect only after the failing scenario and relevant contract
  boundary are recorded.

## Ordered Work

1. Establish reusable invariant assertions for zone uniqueness, object
   identity, owner/controller preservation, stack/priority coherence, and
   expired temporary state.
2. Exercise rejected and stale actions at every supported priority, combat,
   and chooser-owned decision window; rejected actions must not mutate state
   or consume deterministic RNG.
3. Exercise resolution-time invalidation: changed targets, missing sources,
   stale choices, empty hands/libraries, and no-longer-payable mandatory
   costs.
4. Build multi-feature scenarios combining combat, triggers, instants,
   prevention, damage-order choices, cleanup, and turn handoff.
5. Add replay-equivalence and public-event redaction checks for every complex
   path added above.
6. Add deterministic metamorphic tests for independent orderings and legal
   action encodings when the contract specifies their equivalence.

## Verification

- Run the focused adversarial regression for the increment.
- Run all engine and information tests.
- Run `git diff --check` and parse every coverage YAML document.
- Confirm the active manifest's card roster is unchanged.

## Status

- Phase: active
- The roster is frozen at all 200 Portal oracle identities plus the explicit
  ME4 `Rain of Daggers` mass-destruction testbed.
- Initial ten-scenario hardening increment: complete. It proves combat-choice
  barriers; priority reset after mana and instant responses; prevention,
  retaliation, and marker expiry; stale/foreign choice rejection; stale tutor
  and trigger-object identity rejection; deterministic RNG continuity;
  replay equivalence; and APNAP trigger ordering.
- Corrections made by that increment: tutor choices retain expected library
  object identities; skip-combat effects are scoped to their designated turn;
  bounded prevention, retaliation, and forced-attack records expire at the
  correct cleanup boundary.

## Resume Here

Continue with the next smallest scenario not covered by the initial ten:
prefer reusable state-invariant helpers, then metamorphic action-order tests
and longer replay-equivalence paths. Do not onboard a card or set; make the
scenario fail first, then record the narrow contract clarification or engine
correction required to pass it.

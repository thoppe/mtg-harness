# AGENTS.md

This repository follows a harness-engineering approach.

`AGENTS.md` is the entry point, not the encyclopedia. Keep this file short and use it to route work into the source-of-truth docs in `docs/`.

## Working Rules

- Do not add implementation code until the active execution plan and relevant contracts are in place.
- Treat repository-local markdown as the system of record. If a decision exists only in chat, it does not exist.
- Prefer small, explicit contracts over vague architecture prose.
- When assumptions are needed, write them into `HUMAN_INPUT.md` or the relevant plan before building on them.
- Update plans and contracts as part of the same change that depends on them.
- When adding cards, run the active plan's card-expansion freshness check so routing docs, manifests, contracts, and resume notes do not drift.
- Follow `docs/contracts/agent-workflow.md` for collaboration and verified
  rule/card change staging.

## First Stops

- Project overview: `README.md`
- Human-owned constraints and decisions: `HUMAN_INPUT.md`
- Docs index: `docs/index.md`
- Active execution plans: `docs/exec-plans/active/`

## Source Of Truth Map

- Scope and roadmap: `docs/product-specs/`
- System structure and package boundaries: `docs/architecture/`
- Formal interfaces and invariants: `docs/contracts/`
- Design principles and agent operating norms: `docs/design-docs/`
- External references to encode into repo-local docs: `docs/references/`
- Long-running work plans and decision logs: `docs/exec-plans/`

## Expected Workflow

1. Read `README.md`, `HUMAN_INPUT.md`, and the relevant active execution plan.
2. Read the specific contract(s) and architecture docs for the area you are touching.
3. If information is missing, update docs first.
4. Only then propose or implement code changes.

## Current Focus

The project has moved past scaffold planning into a manifest-backed, narrow v0 engine slice. The active Portal-led slice has completed Waves 1–7 and is backed by in-repo source artifacts, contracts, coverage declarations, implementation, and regression tests.

Initial major domains:

- Card and rules knowledge ingestion
- Core play engine
- CLI interaction surface
- Browser-facing API surface for a later viewer/player

No frontend implementation should be introduced yet.

## Immediate Next Steps

The ingestion scaffold and the current Portal Waves 1–7 are complete. The active 201-card roster is frozen; the next agent should improve the legal-deck game surface and engine confidence rather than onboarding cards.

1. Read `docs/exec-plans/active/028-legal-actions-api-and-long-traces.md` first and follow its `Resume Here` section.
2. Treat the active support-slice manifest and coverage manifests as the current playable scope; do not infer support from source artifacts alone.
3. Keep the rules envelope, coverage manifests, and source artifacts aligned with the frozen roster; do not infer support from source artifacts alone.
4. Keep legal Portal deck games separate from the explicit rules harness, and stage further session/CLI/generator hardening as explicit evidence. Do not onboard cards or sets unless a human explicitly reopens expansion work.

# AGENTS.md

This repository follows a harness-engineering approach.

`AGENTS.md` is the entry point, not the encyclopedia. Keep this file short and use it to route work into the source-of-truth docs in `docs/`.

## Working Rules

- Do not add implementation code until the active execution plan and relevant contracts are in place.
- Treat repository-local markdown as the system of record. If a decision exists only in chat, it does not exist.
- Prefer small, explicit contracts over vague architecture prose.
- When assumptions are needed, write them into `HUMAN_INPUT.md` or the relevant plan before building on them.
- Update plans and contracts as part of the same change that depends on them.

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

The project has moved past pure scaffold planning into a narrow v0 engine slice backed by in-repo source artifacts and contracts.

Initial major domains:

- Card and rules knowledge ingestion
- Core play engine
- CLI interaction surface
- Browser-facing API surface for a later viewer/player

No frontend implementation should be introduced yet.

## Immediate Next Steps

The ingestion scaffold already exists under `information/`, so the next agent should continue the active engine plan.

1. Read `docs/exec-plans/active/002-source-strategy-and-coverage-plan.md` first and follow its `Resume Here` section.
2. Treat `Path of Peace` as the current next low-complexity `Portal` expansion on top of the existing `Vengeance` slice.
3. Keep the rules envelope, coverage manifests, and source artifacts aligned with that declared micro-universe before implementation code.
4. After `Path of Peace`, continue widening the engine through similarly narrow nonkeyword sorceries before adding keywords, replacement effects, or broader triggered-ability support.

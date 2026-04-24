# Contract: Rules Coverage Manifest

## Purpose

Define the machine-readable inventory of rules support claimed by the simulator.

## Required Fields

- `rule_key`: stable internal key for a rule family or specific rule
- `source_rules`: comprehensive-rules sections or rule numbers covered
- `status`: one of `implemented`, `deferred`, `not_started`
- `scope`: description of the supported subset
- `engine_contracts`: links to relevant engine contracts or docs
- `tests`: references to verifying tests or examples when implemented
- `notes`: optional explanation of simplifications or omissions

## Granularity Rule

- The manifest may track rule families instead of every individual rule number when that is more practical.
- If a broad rule family is partially implemented, the manifest must state the supported subset explicitly.

## Freshness Rule

- Do not keep copied card lists in this contract as the active scope expands.
- The active support-slice manifest is the canonical current card list; this contract defines the manifest shape and rule-support expectations.
- When a card adds or promotes a rule family, update `docs/coverage/rules.initial.yaml`, the relevant rules envelope, and any active-plan resume notes in the same change.

## Initial Expectation

- The first manifest was seeded from the initial narrow `Portal` slice.
- Current expected card membership must be read from `docs/coverage/slices/portal.initial.yaml`, not from this contract.

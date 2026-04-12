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

## Initial Expectation

- The first manifest should cover only the rules needed for the initial `Portal` micro-universe currently built from:
  - `Border Guard`
  - `Foot Soldiers`
  - `Muck Rats`
  - `Swamp`
  - `Forest`
  - `Island`
  - `Mountain`
  - `Plains`

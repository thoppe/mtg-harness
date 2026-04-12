# Contract: Card Coverage Manifest

## Purpose

Define the machine-readable inventory of card and set support claimed by the simulator.

## Required Fields

- `set_code`: source set code
- `card_key`: canonical card key, based on `oracle_id`
- `status`: one of `implemented`, `deferred`, `not_started`
- `engine_scope`: what gameplay support exists for this card
- `required_rules`: rule families needed for this card
- `tests`: references to verifying tests or examples when implemented
- `notes`: optional explanation of omissions or simplifications

## Grouping Rule

- Planning remains set-first, but support can be declared per card within a set.
- A set-level summary may exist, but the manifest must still make card-level support explicit when only part of a set is implemented.

## Initial Expectation

- The first manifest should include only:
  - `Border Guard`
  - `Border Guard`
  - `Plains`

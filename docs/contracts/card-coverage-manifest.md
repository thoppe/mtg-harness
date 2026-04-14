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
- When raw artifacts are pulled for newly discovered cards from a set the project is actively tracking, those cards should usually appear in the manifest immediately as `deferred` or `not_started` rather than waiting for engine work.

## Separation Rule

- Presence in `information/cards/` means the repository has source knowledge for that card.
- Presence in the coverage manifest means the repository has declared an implementation posture for that card.
- Newly pulled cards from an interested set should default to `deferred` until a narrower implementation change promotes them.
- Raw source data may be committed ahead of implementation; that commit must not claim engine support.

## Initial Expectation

- The first manifest should include only:
  - `Border Guard`
  - `Foot Soldiers`
  - `Muck Rats`
  - `Wind Drake`
  - `Bog Imp`
  - `Storm Crow`
  - `Vengeance`
  - `Path of Peace`
  - `Touch of Brilliance`
  - `Time Ebb`
  - `Armored Pegasus`
  - `Swamp`
  - `Forest`
  - `Island`
  - `Mountain`
  - `Plains`

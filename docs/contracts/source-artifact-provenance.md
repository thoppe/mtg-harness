# Contract: Source Artifact Provenance

## Purpose

Define the on-disk shape and minimum provenance fields for downloaded external source artifacts.

## Artifact Classes

### Scryfall card metadata

- Path: `information/cards/data/<oracle_id>.json`
- Format: JSON object with top-level `artifact_type`, `schema_version`, `canonical_card_id`, `name`, `source_record`, and `provenance`
- `artifact_type` must be `scryfall_card_snapshot`
- `canonical_card_id` must equal Scryfall `oracle_id`
- `source_record` must preserve the fetched Scryfall card payload
- `provenance` must include:
  - `source_name`
  - `source_url`
  - `fetched_at`
  - `request_url`
  - `requested_set_code`
  - `scryfall_id`
  - `oracle_id`
  - `set_code`
  - `collector_number`
  - `image_uri_normal`

### Scryfall card image

- Path: `information/cards/images/<oracle_id>.jpg`
- Companion provenance path: `information/cards/images/<oracle_id>.jpg.provenance.json`
- Image provenance must include:
  - `artifact_type`
  - `schema_version`
  - `canonical_card_id`
  - `image_format`
  - `image_variant`
  - `source_name`
  - `source_url`
  - `fetched_at`
  - `scryfall_id`
  - `oracle_id`
  - `set_code`

### Wizards Comprehensive Rules snapshot

- Text path: `information/rules/raw/comprehensive_rules_<effective-date>.txt`
- Companion provenance path: `information/rules/raw/comprehensive_rules_<effective-date>.txt.provenance.json`
- Rules provenance must include:
  - `artifact_type`
  - `schema_version`
  - `source_name`
  - `source_page_url`
  - `source_download_url`
  - `fetched_at`
  - `effective_date`
  - `filename`

## Invariants

- Provenance must be written in the same operation as the artifact it describes.
- Raw artifact storage must preserve enough information to reproduce the pull without relying on chat history.
- File naming must remain stable across reruns for the same canonical card identity and rules effective date.
- Raw source artifacts must remain separate from any later normalized engine-facing model.

## Initial Scope

- The first card pull scope is the currently declared narrow `Portal` slice, aligned with the active support slice:
  - `Border Guard`
  - `Foot Soldiers`
  - `Muck Rats`
  - `Vengeance`
  - `Path of Peace`
  - `Swamp`
  - `Forest`
  - `Island`
  - `Mountain`
  - `Plains`
- The first rules pull scope is the current official plain-text Comprehensive Rules snapshot linked from the Wizards rules page.

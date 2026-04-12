# Card Information Layout

## Planned Subdirectories

- `data/`: one metadata file per card
- `images/`: one image file per card

## Indexing Rule

- Canonical card identity should use Scryfall `oracle_id`.
- Printing-level provenance should retain Scryfall `id`, set code, and collector number.
- Canonical card metadata files must be named `data/<oracle_id>.json`.
- Card image files must be named `images/<oracle_id>.<ext>`.
- JPG is the default persisted image asset type for the current plan.

# Contract: Canonical Card Model

## Purpose

Define the minimum internal representation of a card object before engine implementation begins.

## Required Fields

- Stable internal card identifier
- Source printing identifier
- Card name
- Mana cost representation
- Type line
- Oracle text
- Power/toughness or loyalty when applicable
- Color identity
- Legal set or printing references as needed by chosen scope

## Guarantees

- The canonical model must distinguish external raw data from normalized internal data.
- Rule-relevant text used by the engine must be traceable back to a source snapshot.
- The model must support future derived annotations without mutating source provenance away.
- The stable internal card identifier must be based on Scryfall `oracle_id`.
- Printing-level provenance must retain Scryfall `id`, set code, and collector number when present.

## Open Questions

- How much printing-level detail belongs in the canonical model?
- Should parsed abilities be stored alongside raw oracle text or as a separate derived layer?

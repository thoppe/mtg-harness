from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CardDefinition:
    oracle_id: str
    name: str
    mana_cost: str
    type_line: str
    oracle_text: str
    power: str | None
    toughness: str | None
    set_code: str

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .models import CardDefinition

MICRO_UNIVERSE_ORACLE_IDS = {
    "1d001145-5d14-43a9-bf3b-3ce5c20b2a46",
    "1ef5003c-f540-4cdc-913f-7d5280ad9f62",
    "b7593cf8-4dcb-473b-a2ef-180fffe66738",
    "a768ba13-4d1c-4dce-a4a6-86a39c069c3f",
    "a3fb7228-e76b-4e96-a40e-20b5fed75685",
    "b2c6aa39-2d2a-459c-a555-fb48ba993373",
    "b34bb2dc-c1af-4d77-b0b3-a0fb342a5fc6",
    "bca13a12-6723-4a5e-8f1b-21646a8b3e7e",
    "bc71ebf6-2056-41f7-be35-b2e5c34afa99",
    "56719f6a-1a6c-4c0a-8d21-18f7d7350b68",
}


@dataclass(frozen=True)
class CardRepository:
    cards_by_oracle_id: dict[str, CardDefinition]

    @classmethod
    def from_information_directory(cls, information_dir: Path) -> "CardRepository":
        data_dir = information_dir / "cards" / "data"
        cards_by_oracle_id: dict[str, CardDefinition] = {}

        for oracle_id in MICRO_UNIVERSE_ORACLE_IDS:
            path = data_dir / f"{oracle_id}.json"
            payload = json.loads(path.read_text(encoding="utf-8"))
            source = payload["source_record"]
            cards_by_oracle_id[oracle_id] = CardDefinition(
                oracle_id=oracle_id,
                name=source["name"],
                mana_cost=source.get("mana_cost", ""),
                type_line=source["type_line"],
                oracle_text=source.get("oracle_text", ""),
                power=source.get("power"),
                toughness=source.get("toughness"),
                set_code=source["set"],
                produced_mana=tuple(source.get("produced_mana", ())),
            )

        return cls(cards_by_oracle_id=cards_by_oracle_id)

    def get(self, oracle_id: str) -> CardDefinition:
        return self.cards_by_oracle_id[oracle_id]

    def has(self, oracle_id: str) -> bool:
        return oracle_id in self.cards_by_oracle_id

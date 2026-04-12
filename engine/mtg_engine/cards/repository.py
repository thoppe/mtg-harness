from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .models import CardDefinition

MICRO_UNIVERSE_ORACLE_IDS = {
    "1ef5003c-f540-4cdc-913f-7d5280ad9f62",
    "a768ba13-4d1c-4dce-a4a6-86a39c069c3f",
    "bc71ebf6-2056-41f7-be35-b2e5c34afa99",
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
            )

        return cls(cards_by_oracle_id=cards_by_oracle_id)

    def get(self, oracle_id: str) -> CardDefinition:
        return self.cards_by_oracle_id[oracle_id]

    def has(self, oracle_id: str) -> bool:
        return oracle_id in self.cards_by_oracle_id

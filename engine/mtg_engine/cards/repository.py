from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .models import CardDefinition
from .support_slices import load_active_support_slice


@dataclass(frozen=True)
class CardRepository:
    support_slice_key: str
    cards_by_oracle_id: dict[str, CardDefinition]

    @classmethod
    def from_information_directory(cls, information_dir: Path) -> "CardRepository":
        repo_root = information_dir.parent
        data_dir = information_dir / "cards" / "data"
        support_slice = load_active_support_slice(repo_root)
        cards_by_oracle_id: dict[str, CardDefinition] = {}

        for oracle_id in support_slice.card_keys:
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
                keywords=tuple(source.get("keywords", ())),
            )

        return cls(
            support_slice_key=support_slice.slice_key,
            cards_by_oracle_id=cards_by_oracle_id,
        )

    def get(self, oracle_id: str) -> CardDefinition:
        return self.cards_by_oracle_id[oracle_id]

    def has(self, oracle_id: str) -> bool:
        return oracle_id in self.cards_by_oracle_id

    @property
    def allowed_oracle_ids(self) -> frozenset[str]:
        return frozenset(self.cards_by_oracle_id)

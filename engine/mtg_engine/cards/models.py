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
    colors: tuple[str, ...] = ()
    produced_mana: tuple[str, ...] = ()
    keywords: tuple[str, ...] = ()

    @property
    def is_land(self) -> bool:
        return "Land" in self.type_line

    @property
    def is_creature(self) -> bool:
        return "Creature" in self.type_line

    @property
    def is_sorcery(self) -> bool:
        return "Sorcery" in self.type_line

    def has_keyword(self, keyword: str) -> bool:
        return keyword in self.keywords

    def has_color(self, color: str) -> bool:
        return color in self.colors

    @property
    def is_black(self) -> bool:
        return self.has_color("B")

    @property
    def has_flying(self) -> bool:
        return self.has_keyword("Flying")

    @property
    def has_reach(self) -> bool:
        return self.has_keyword("Reach")

    @property
    def has_defender(self) -> bool:
        return self.has_keyword("Defender")

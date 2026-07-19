from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class DeckList:
    """A persistent, ordered multiset of card oracle identities."""

    oracle_ids: tuple[str, ...]

    @property
    def cards(self) -> tuple[str, ...]:
        """Compatibility-oriented name for the ordered card identities."""
        return self.oracle_ids

    def to_payload(self) -> dict[str, object]:
        return {"oracle_ids": list(self.oracle_ids)}

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "DeckList":
        oracle_ids = payload.get("oracle_ids")
        if not isinstance(oracle_ids, list):
            raise ValueError("deck payload oracle_ids must be a list")
        return cls(oracle_ids=tuple(oracle_ids))


@dataclass(frozen=True)
class DeckProfile:
    """Declared rules for one legal main-deck format."""

    key: str
    deck_size: int
    max_nonbasic_copies: int
    starting_life_total: int = 20
    opening_hand_size: int = 7
    mulligan_policy: str = "london"
    sideboards_supported: bool = False

    def to_payload(self) -> dict[str, object]:
        return {
            "key": self.key,
            "deck_size": self.deck_size,
            "max_nonbasic_copies": self.max_nonbasic_copies,
            "starting_life_total": self.starting_life_total,
            "opening_hand_size": self.opening_hand_size,
            "mulligan_policy": self.mulligan_policy,
            "sideboards_supported": self.sideboards_supported,
        }


PORTAL_CONSTRUCTED_V0 = DeckProfile(
    key="portal_constructed_v0",
    deck_size=60,
    max_nonbasic_copies=4,
)

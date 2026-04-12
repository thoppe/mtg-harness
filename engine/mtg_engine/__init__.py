"""Minimal MTG engine package for the initial deterministic slice."""

from .cards.repository import CardRepository
from .flow.setup import SetupInput, initialize_game
from .flow.turns import (
    activate_mana_ability,
    advance_to_begin_combat,
    advance_to_cleanup,
    cast_creature_spell,
    declare_attackers,
    declare_blockers,
    play_land,
    resolve_combat_damage,
    start_next_turn,
    start_first_turn,
)

__all__ = [
    "CardRepository",
    "SetupInput",
    "activate_mana_ability",
    "advance_to_begin_combat",
    "advance_to_cleanup",
    "cast_creature_spell",
    "declare_attackers",
    "declare_blockers",
    "initialize_game",
    "play_land",
    "resolve_combat_damage",
    "start_next_turn",
    "start_first_turn",
]

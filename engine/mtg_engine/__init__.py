"""Minimal MTG engine package for the initial deterministic slice."""

from .cards.repository import CardRepository
from .flow.setup import SetupInput, initialize_game
from .flow.deck_start import DeckGameInput, initialize_deck_game, keep_london_hand, take_london_mulligan
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
from .output import print_action_plan, print_game_snapshot, print_recent_events

__all__ = [
    "CardRepository",
    "DeckGameInput",
    "SetupInput",
    "activate_mana_ability",
    "advance_to_begin_combat",
    "advance_to_cleanup",
    "cast_creature_spell",
    "declare_attackers",
    "declare_blockers",
    "initialize_game",
    "initialize_deck_game",
    "keep_london_hand",
    "print_action_plan",
    "print_game_snapshot",
    "print_recent_events",
    "play_land",
    "resolve_combat_damage",
    "start_next_turn",
    "start_first_turn",
    "take_london_mulligan",
]

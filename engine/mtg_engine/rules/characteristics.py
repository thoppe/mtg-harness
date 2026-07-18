from __future__ import annotations

from mtg_engine.cards.repository import CardRepository
from mtg_engine.state.models import GameState, TemporaryEffect


def effects_for(state: GameState, instance_id: str) -> tuple[TemporaryEffect, ...]:
    object_id = state.objects[instance_id].object_id
    return tuple(effect for effect in state.temporary_effects if object_id in effect.target_object_ids)


def effective_power(state: GameState, card_repository: CardRepository, instance_id: str) -> int:
    card = state.objects[instance_id]
    definition = card_repository.get(card.oracle_id)
    return int(definition.power or "0") + sum(effect.power_delta for effect in effects_for(state, instance_id))


def effective_toughness(state: GameState, card_repository: CardRepository, instance_id: str) -> int:
    card = state.objects[instance_id]
    definition = card_repository.get(card.oracle_id)
    return int(definition.toughness or "0") + sum(effect.toughness_delta for effect in effects_for(state, instance_id))


def effective_keywords(state: GameState, card_repository: CardRepository, instance_id: str) -> frozenset[str]:
    definition = card_repository.get(state.objects[instance_id].oracle_id)
    keywords = set(definition.keywords)
    for effect in effects_for(state, instance_id):
        keywords.update(effect.granted_keywords)
    return frozenset(keywords)


def has_keyword(state: GameState, card_repository: CardRepository, instance_id: str, keyword: str) -> bool:
    return keyword in effective_keywords(state, card_repository, instance_id)


def only_blockable_by_colors(state: GameState, instance_id: str) -> tuple[str, ...]:
    colors: set[str] = set()
    for effect in effects_for(state, instance_id):
        colors.update(effect.only_blockable_by_colors)
    return tuple(sorted(colors))

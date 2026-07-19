from __future__ import annotations

from collections import Counter

from mtg_engine.cards.repository import CardRepository

from .models import DeckList, DeckProfile


class DeckValidationError(ValueError):
    """A deck violates the declared legal-deck profile."""


def validate_deck(
    deck_list: DeckList,
    profile: DeckProfile,
    card_repository: CardRepository,
) -> None:
    """Raise a clear error unless a deck is legal under ``profile``."""
    _validate_profile(profile)
    if not isinstance(deck_list, DeckList):
        raise DeckValidationError("deck must be a DeckList")
    if not isinstance(deck_list.oracle_ids, tuple):
        raise DeckValidationError("deck oracle_ids must be a tuple")
    if len(deck_list.oracle_ids) != profile.deck_size:
        raise DeckValidationError(
            f"deck must contain exactly {profile.deck_size} cards; got {len(deck_list.oracle_ids)}"
        )

    definitions_by_oracle_id = {}
    for index, oracle_id in enumerate(deck_list.oracle_ids):
        if not isinstance(oracle_id, str) or not oracle_id:
            raise DeckValidationError(f"deck entry {index} must be a non-empty oracle_id string")
        if not card_repository.has(oracle_id):
            raise DeckValidationError(f"deck entry {index} is not in the active support slice: {oracle_id}")
        if oracle_id not in card_repository.deck_eligible_oracle_ids:
            raise DeckValidationError(f"deck entry {index} is not deck eligible: {oracle_id}")
        definitions_by_oracle_id[oracle_id] = card_repository.get(oracle_id)

    names = Counter(
        definitions_by_oracle_id[oracle_id].name for oracle_id in deck_list.oracle_ids
    )
    for name, count in names.items():
        definition = next(
            definition
            for definition in definitions_by_oracle_id.values()
            if definition.name == name
        )
        if not definition.is_basic_land and count > profile.max_nonbasic_copies:
            raise DeckValidationError(
                f"deck contains {count} copies of nonbasic {name}; maximum is {profile.max_nonbasic_copies}"
            )


def _validate_profile(profile: DeckProfile) -> None:
    if not isinstance(profile, DeckProfile):
        raise DeckValidationError("deck profile must be a DeckProfile")
    if not profile.key:
        raise DeckValidationError("deck profile key must be non-empty")
    if profile.deck_size <= 0:
        raise DeckValidationError("deck profile deck_size must be positive")
    if profile.max_nonbasic_copies <= 0:
        raise DeckValidationError("deck profile max_nonbasic_copies must be positive")
    if profile.starting_life_total <= 0:
        raise DeckValidationError("deck profile starting_life_total must be positive")
    if profile.opening_hand_size <= 0:
        raise DeckValidationError("deck profile opening_hand_size must be positive")
    if profile.mulligan_policy != "london":
        raise DeckValidationError("deck profile mulligan_policy must be london")
    if profile.sideboards_supported:
        raise DeckValidationError("sideboards are not supported by this engine surface")

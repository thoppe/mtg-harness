from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mtg_engine.cards.repository import CardRepository
from mtg_engine.cards.support_slices import load_active_support_slice
from mtg_engine.decks import (
    DeckList,
    DeckValidationError,
    PORTAL_CONSTRUCTED_V0,
    validate_deck,
)
from mtg_engine.decks.fixtures import portal_blue_starter, portal_white_starter


REPO_ROOT = Path(__file__).resolve().parents[2]
INFORMATION_DIR = REPO_ROOT / "information"
PLAINS = "bc71ebf6-2056-41f7-be35-b2e5c34afa99"
MUCK_RATS = "bca13a12-6723-4a5e-8f1b-21646a8b3e7e"
RAIN_OF_DAGGERS = "e2048201-6dc9-4cf5-916f-1d867ae8dbdd"


class DeckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repository = CardRepository.from_information_directory(INFORMATION_DIR)

    def test_manifest_defaults_portal_cards_to_deck_eligible_and_excludes_rain(self) -> None:
        support_slice = load_active_support_slice(REPO_ROOT)

        self.assertEqual(len(support_slice.card_keys), 201)
        self.assertEqual(len(support_slice.deck_eligible_card_keys), 200)
        self.assertIn(MUCK_RATS, support_slice.deck_eligible_card_keys)
        self.assertNotIn(RAIN_OF_DAGGERS, support_slice.deck_eligible_card_keys)
        self.assertNotIn(RAIN_OF_DAGGERS, self.repository.deck_eligible_oracle_ids)

    def test_basic_land_predicate_uses_basic_supertype(self) -> None:
        self.assertTrue(self.repository.get(PLAINS).is_basic_land)
        self.assertFalse(self.repository.get(MUCK_RATS).is_basic_land)

    def test_legal_sixty_card_deck_allows_unlimited_basic_lands(self) -> None:
        deck = DeckList(oracle_ids=(PLAINS,) * 56 + (MUCK_RATS,) * 4)

        validate_deck(deck, PORTAL_CONSTRUCTED_V0, self.repository)
        self.assertEqual(DeckList.from_payload(deck.to_payload()), deck)

    def test_rejects_incorrect_size_before_game_setup(self) -> None:
        deck = DeckList(oracle_ids=(PLAINS,) * 59)

        with self.assertRaisesRegex(DeckValidationError, "exactly 60"):
            validate_deck(deck, PORTAL_CONSTRUCTED_V0, self.repository)

    def test_rejects_more_than_four_copies_of_nonbasic_by_name(self) -> None:
        deck = DeckList(oracle_ids=(PLAINS,) * 55 + (MUCK_RATS,) * 5)

        with self.assertRaisesRegex(DeckValidationError, "5 copies of nonbasic Muck Rats"):
            validate_deck(deck, PORTAL_CONSTRUCTED_V0, self.repository)

    def test_rejects_scenario_only_rain_of_daggers(self) -> None:
        deck = DeckList(oracle_ids=(PLAINS,) * 59 + (RAIN_OF_DAGGERS,))

        with self.assertRaisesRegex(DeckValidationError, "not deck eligible"):
            validate_deck(deck, PORTAL_CONSTRUCTED_V0, self.repository)

    def test_rejects_unknown_and_malformed_entries(self) -> None:
        unknown = DeckList(oracle_ids=(PLAINS,) * 59 + ("not-a-real-card",))
        malformed = DeckList(oracle_ids=(PLAINS,) * 59 + (123,))  # type: ignore[arg-type]

        with self.assertRaisesRegex(DeckValidationError, "not in the active support slice"):
            validate_deck(unknown, PORTAL_CONSTRUCTED_V0, self.repository)
        with self.assertRaisesRegex(DeckValidationError, "non-empty oracle_id string"):
            validate_deck(malformed, PORTAL_CONSTRUCTED_V0, self.repository)

    def test_portal_starter_decks_are_legal_and_exclude_scenario_testbed(self) -> None:
        for deck in (portal_white_starter(), portal_blue_starter()):
            validate_deck(deck, PORTAL_CONSTRUCTED_V0, self.repository)
            self.assertNotIn(RAIN_OF_DAGGERS, deck.oracle_ids)


if __name__ == "__main__":
    unittest.main()

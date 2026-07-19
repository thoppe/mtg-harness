from __future__ import annotations

import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mtg_engine.cards.repository import CardRepository
from mtg_engine.decks.models import DeckList
from mtg_engine.flow.deck_start import DeckGameInput, initialize_deck_game, keep_london_hand, take_london_mulligan
from mtg_engine.flow.setup import SetupInput, initialize_game
from mtg_engine.services import DeckGameSession


INFORMATION_DIR = Path(__file__).resolve().parents[2] / "information"
PLAINS = "bc71ebf6-2056-41f7-be35-b2e5c34afa99"


class DeckStartTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repository = CardRepository.from_information_directory(INFORMATION_DIR)
        legal_deck = DeckList((PLAINS,) * 60)
        self.input = DeckGameInput(
            game_id="legal-deck-game", players=("alice", "bob"), starting_player="alice",
            decks={"alice": legal_deck, "bob": legal_deck}, rng_seed=37,
        )

    def test_legal_decks_shuffle_draw_seven_deterministically_without_identity_events(self) -> None:
        first = initialize_deck_game(self.input, self.repository)
        second = initialize_deck_game(self.input, self.repository)

        self.assertEqual(first, second)
        self.assertEqual(first.state.rng_cursor, 2)
        self.assertEqual(first.state.turn.step, "mulligan_decision")
        self.assertEqual(first.state.players["alice"].life_total, 20)
        self.assertEqual(len(first.state.players["alice"].hand), 7)
        self.assertEqual(len(first.state.players["alice"].library), 53)
        self.assertEqual([event.event_type for event in first.event_log].count("library_shuffled"), 2)
        self.assertNotIn(PLAINS, str([event.payload for event in first.event_log]))

    def test_london_mulligan_redraws_seven_then_requires_exact_ordered_bottom(self) -> None:
        initial = initialize_deck_game(self.input, self.repository)
        redrawn = take_london_mulligan(initial, "alice")

        self.assertEqual(redrawn.state.rng_cursor, 3)
        self.assertEqual(len(redrawn.state.players["alice"].hand), 7)
        self.assertEqual(redrawn.state.mulligan.count_for("alice"), 1)
        with self.assertRaisesRegex(ValueError, "exactly the mulligan count"):
            keep_london_hand(redrawn, "alice")

        bottom = redrawn.state.players["alice"].hand[-1:]
        kept = keep_london_hand(redrawn, "alice", bottom)
        self.assertEqual(len(kept.state.players["alice"].hand), 6)
        self.assertEqual(kept.state.players["alice"].library[-1:], bottom)
        self.assertEqual(kept.state.objects[bottom[0]].zone, "library")
        self.assertEqual(kept.state.objects[bottom[0]].zone_change_counter, 1)
        self.assertNotIn(bottom[0], str(kept.event_log[-1].payload))
        self.assertEqual(kept.state.turn.priority_player, "bob")

    def test_both_kept_hands_finish_opening_procedure_and_harness_remains_explicit(self) -> None:
        session = initialize_deck_game(self.input, self.repository)
        session = keep_london_hand(session, "alice")
        session = keep_london_hand(session, "bob")

        self.assertIsNone(session.state.mulligan)
        self.assertEqual(session.state.turn.step, "opening_hand_ready")
        self.assertEqual(session.state.turn.priority_player, "alice")
        self.assertIn("opening_hands_ready", [event.event_type for event in session.event_log])

        harness = initialize_game(
            SetupInput("harness", ("alice", "bob"), "alice", {"alice": (PLAINS,), "bob": (PLAINS,)}, {"alice": (PLAINS,), "bob": (PLAINS,)}, 1),
            self.repository,
        )
        self.assertEqual(harness.state.turn.step, "opening_hand_ready")
        self.assertIsNone(harness.state.mulligan)

    def test_only_current_mulligan_chooser_can_act(self) -> None:
        session = initialize_deck_game(self.input, self.repository)
        with self.assertRaisesRegex(ValueError, "current London mulligan chooser"):
            take_london_mulligan(session, "bob")
        self.assertEqual(session.state.rng_cursor, 2)

    def test_deck_session_requires_kept_hands_then_exposes_ordinary_legal_actions(self) -> None:
        deck_session = DeckGameSession.from_decks(self.input, self.repository)
        with self.assertRaisesRegex(ValueError, "must keep"):
            deck_session.start()
        deck_session.keep_hand("alice")
        deck_session.keep_hand("bob")
        session = deck_session.start()

        self.assertEqual(session.state.turn.step, "precombat_main_step")
        self.assertTrue(session.legal_actions())
        self.assertTrue(
            all(
                card.oracle_id != "e2048201-6dc9-4cf5-916f-1d867ae8dbdd"
                for card in session.state.objects.values()
            )
        )


if __name__ == "__main__":
    unittest.main()

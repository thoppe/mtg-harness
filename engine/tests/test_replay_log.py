from __future__ import annotations

import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mtg_engine.cards.repository import CardRepository
from mtg_engine.flow.setup import SetupInput, initialize_game


INFORMATION_DIR = Path(__file__).resolve().parents[2] / "information"


class ReplayLogTests(unittest.TestCase):
    def test_setup_emits_expected_append_only_events(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        setup = SetupInput(
            game_id="game-003",
            players=("alice", "bob"),
            starting_player="alice",
            libraries={
                "alice": (
                    "bc71ebf6-2056-41f7-be35-b2e5c34afa99",
                    "1ef5003c-f540-4cdc-913f-7d5280ad9f62",
                ),
                "bob": ("a768ba13-4d1c-4dce-a4a6-86a39c069c3f",),
            },
            opening_hands={
                "alice": ("bc71ebf6-2056-41f7-be35-b2e5c34afa99",),
                "bob": ("a768ba13-4d1c-4dce-a4a6-86a39c069c3f",),
            },
            rng_seed=13,
        )

        bootstrap = initialize_game(setup, repository)

        self.assertEqual(
            [event.event_type for event in bootstrap.event_log],
            ["game_initialized", "opening_hand_assigned", "opening_hand_assigned"],
        )
        self.assertEqual([event.sequence for event in bootstrap.event_log], [1, 2, 3])
        self.assertEqual(bootstrap.event_log[0].payload["rng_seed"], 13)
        self.assertEqual(bootstrap.event_log[1].payload["player_id"], "alice")
        self.assertEqual(bootstrap.event_log[2].payload["player_id"], "bob")


if __name__ == "__main__":
    unittest.main()

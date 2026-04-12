from __future__ import annotations

import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mtg_engine.cards.repository import CardRepository
from mtg_engine.flow.setup import SetupInput, initialize_game


INFORMATION_DIR = Path(__file__).resolve().parents[2] / "information"


class SetupTests(unittest.TestCase):
    def test_repository_loads_declared_micro_universe(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)

        self.assertEqual(set(repository.cards_by_oracle_id.keys()), {
            "1ef5003c-f540-4cdc-913f-7d5280ad9f62",
            "a768ba13-4d1c-4dce-a4a6-86a39c069c3f",
            "bc71ebf6-2056-41f7-be35-b2e5c34afa99",
        })
        self.assertEqual(repository.get("bc71ebf6-2056-41f7-be35-b2e5c34afa99").name, "Plains")

    def test_initialize_game_builds_reproducible_opening_state(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        setup = SetupInput(
            game_id="game-001",
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
            rng_seed=7,
        )

        bootstrap = initialize_game(setup, repository)

        self.assertEqual(bootstrap.state.turn.step, "opening_hand_ready")
        self.assertEqual(bootstrap.state.turn.active_player, "alice")
        self.assertEqual(bootstrap.state.players["alice"].hand, ("alice:1",))
        self.assertEqual(bootstrap.state.players["alice"].library, ("alice:2",))
        self.assertEqual(bootstrap.state.players["bob"].hand, ("bob:1",))
        self.assertEqual(bootstrap.state.players["bob"].library, ())
        self.assertEqual(bootstrap.state.objects["alice:2"].oracle_id, "1ef5003c-f540-4cdc-913f-7d5280ad9f62")

    def test_initialize_game_rejects_cards_outside_micro_universe(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        setup = SetupInput(
            game_id="game-002",
            players=("alice", "bob"),
            starting_player="alice",
            libraries={
                "alice": ("not-a-real-card", "1ef5003c-f540-4cdc-913f-7d5280ad9f62"),
                "bob": ("a768ba13-4d1c-4dce-a4a6-86a39c069c3f",),
            },
            opening_hands={
                "alice": ("not-a-real-card",),
                "bob": ("a768ba13-4d1c-4dce-a4a6-86a39c069c3f",),
            },
            rng_seed=7,
        )

        with self.assertRaises(ValueError):
            initialize_game(setup, repository)


if __name__ == "__main__":
    unittest.main()

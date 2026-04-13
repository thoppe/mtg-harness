from __future__ import annotations

import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mtg_engine.cards.repository import CardRepository
from mtg_engine.cards.support_slices import load_active_support_slice
from mtg_engine.flow.setup import SetupInput, initialize_game


INFORMATION_DIR = Path(__file__).resolve().parents[2] / "information"
REPO_ROOT = Path(__file__).resolve().parents[2]
ARMORED_PEGASUS = "f097a059-5505-4c3c-b879-7853ab6972ed"
WIND_DRAKE = "d6ffdaf0-ac08-4de9-bbce-2eab2f86bcca"
BOG_IMP = "45b94e3c-a905-435b-aee5-bec9239fd24c"
STORM_CROW = "000d5588-5a4c-434e-988d-396632ade42c"


class SetupTests(unittest.TestCase):
    def test_repository_loads_active_support_slice(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        support_slice = load_active_support_slice(REPO_ROOT)

        self.assertEqual(repository.support_slice_key, "portal_initial_micro_universe")
        self.assertEqual(set(repository.cards_by_oracle_id.keys()), set(support_slice.card_keys))
        self.assertEqual(set(repository.cards_by_oracle_id.keys()), {
            "1d001145-5d14-43a9-bf3b-3ce5c20b2a46",
            "1ef5003c-f540-4cdc-913f-7d5280ad9f62",
            "b7593cf8-4dcb-473b-a2ef-180fffe66738",
            "6365aba1-78d3-416c-89cd-9449578eedbf",
            "30cc8f7b-3c28-40f5-8f8f-157e8212280b",
            "f097a059-5505-4c3c-b879-7853ab6972ed",
            "d6ffdaf0-ac08-4de9-bbce-2eab2f86bcca",
            "45b94e3c-a905-435b-aee5-bec9239fd24c",
            "000d5588-5a4c-434e-988d-396632ade42c",
            "a768ba13-4d1c-4dce-a4a6-86a39c069c3f",
            "a3fb7228-e76b-4e96-a40e-20b5fed75685",
            "b2c6aa39-2d2a-459c-a555-fb48ba993373",
            "b34bb2dc-c1af-4d77-b0b3-a0fb342a5fc6",
            "bca13a12-6723-4a5e-8f1b-21646a8b3e7e",
            "bc71ebf6-2056-41f7-be35-b2e5c34afa99",
            "56719f6a-1a6c-4c0a-8d21-18f7d7350b68",
        })
        self.assertEqual(repository.get("bc71ebf6-2056-41f7-be35-b2e5c34afa99").name, "Plains")
        self.assertEqual(repository.get("bca13a12-6723-4a5e-8f1b-21646a8b3e7e").name, "Muck Rats")
        self.assertTrue(repository.get(ARMORED_PEGASUS).has_flying)
        self.assertTrue(repository.get(WIND_DRAKE).has_flying)
        self.assertTrue(repository.get(BOG_IMP).has_flying)
        self.assertTrue(repository.get(STORM_CROW).has_flying)

    def test_active_support_slice_manifest_is_unique_and_loadable(self) -> None:
        support_slice = load_active_support_slice(REPO_ROOT)

        self.assertEqual(support_slice.slice_key, "portal_initial_micro_universe")
        self.assertEqual(support_slice.status, "active")
        self.assertEqual(support_slice.set_code, "por")
        self.assertIn("targeted_sorcery_spells_minimal", support_slice.rule_keys)
        self.assertIn("flying_keyword_minimal", support_slice.rule_keys)
        self.assertIn("b7593cf8-4dcb-473b-a2ef-180fffe66738", support_slice.card_keys)
        self.assertIn(ARMORED_PEGASUS, support_slice.card_keys)
        self.assertIn(WIND_DRAKE, support_slice.card_keys)
        self.assertIn(BOG_IMP, support_slice.card_keys)
        self.assertIn(STORM_CROW, support_slice.card_keys)

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

    def test_initialize_game_rejects_cards_outside_active_support_slice(self) -> None:
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

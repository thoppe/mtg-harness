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
WALL_OF_GRANITE = "8445094f-008b-491a-977c-e8582d5ab72c"
VOLCANIC_HAMMER = "98fa5a06-0553-40fd-999c-bc31c9b3f4db"
LAVA_AXE = "387b6b07-a283-412d-94c3-f7f1dc76e858"
MIND_ROT = "ad44cf74-b717-48fb-9fa2-77512024d76a"
WINTERS_GRASP = "e9b8679d-52a9-4f0f-9365-f3e4b7a69805"
SYMBOL_OF_UNSUMMONING = "c44f1a81-269b-4f05-8ff2-e7ce19a93937"


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
            "98fa5a06-0553-40fd-999c-bc31c9b3f4db",
            "387b6b07-a283-412d-94c3-f7f1dc76e858",
            "ad44cf74-b717-48fb-9fa2-77512024d76a",
            "e9b8679d-52a9-4f0f-9365-f3e4b7a69805",
            "c44f1a81-269b-4f05-8ff2-e7ce19a93937",
            "f097a059-5505-4c3c-b879-7853ab6972ed",
            "8445094f-008b-491a-977c-e8582d5ab72c",
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
        self.assertTrue(repository.get(WALL_OF_GRANITE).has_defender)

    def test_active_support_slice_manifest_is_unique_and_loadable(self) -> None:
        support_slice = load_active_support_slice(REPO_ROOT)

        self.assertEqual(support_slice.slice_key, "portal_initial_micro_universe")
        self.assertEqual(support_slice.status, "active")
        self.assertEqual(support_slice.set_code, "por")
        self.assertIn("targeted_sorcery_spells_minimal", support_slice.rule_keys)
        self.assertIn("targeted_damage_sorceries_minimal", support_slice.rule_keys)
        self.assertIn("targeted_discard_sorceries_minimal", support_slice.rule_keys)
        self.assertIn("targeted_land_destruction_sorceries_minimal", support_slice.rule_keys)
        self.assertIn("targeted_battlefield_to_hand_sorceries_minimal", support_slice.rule_keys)
        self.assertIn("flying_keyword_minimal", support_slice.rule_keys)
        self.assertIn("defender_keyword_minimal", support_slice.rule_keys)
        self.assertIn("b7593cf8-4dcb-473b-a2ef-180fffe66738", support_slice.card_keys)
        self.assertIn(ARMORED_PEGASUS, support_slice.card_keys)
        self.assertIn(WIND_DRAKE, support_slice.card_keys)
        self.assertIn(BOG_IMP, support_slice.card_keys)
        self.assertIn(STORM_CROW, support_slice.card_keys)
        self.assertIn(WALL_OF_GRANITE, support_slice.card_keys)
        self.assertIn(VOLCANIC_HAMMER, support_slice.card_keys)
        self.assertIn(LAVA_AXE, support_slice.card_keys)
        self.assertIn(MIND_ROT, support_slice.card_keys)
        self.assertIn(WINTERS_GRASP, support_slice.card_keys)
        self.assertIn(SYMBOL_OF_UNSUMMONING, support_slice.card_keys)

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

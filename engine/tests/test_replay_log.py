from __future__ import annotations

import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mtg_engine.cards.repository import CardRepository
from mtg_engine.flow.setup import SetupInput, initialize_game
from mtg_engine.actions.models import ActivateManaAbilityAction, CastNonCreatureSpellAction
from mtg_engine.flow.turns import activate_mana_ability, cast_noncreature_spell, start_first_turn
from mtg_engine.state.zones import move_object


INFORMATION_DIR = Path(__file__).resolve().parents[2] / "information"
PLAINS = "bc71ebf6-2056-41f7-be35-b2e5c34afa99"
MUCK_RATS = "bca13a12-6723-4a5e-8f1b-21646a8b3e7e"
PATH_OF_PEACE = "b7593cf8-4dcb-473b-a2ef-180fffe66738"


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

    def test_path_of_peace_replay_trace_includes_life_total_change(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        setup = SetupInput(
            game_id="replay-path-of-peace",
            players=("alice", "bob"),
            starting_player="alice",
            libraries={
                "alice": (PLAINS, PLAINS, PLAINS, PLAINS, PATH_OF_PEACE),
                "bob": (MUCK_RATS,),
            },
            opening_hands={
                "alice": (PLAINS, PLAINS, PLAINS, PLAINS, PATH_OF_PEACE),
                "bob": (MUCK_RATS,),
            },
            rng_seed=47,
        )

        session = start_first_turn(initialize_game(setup, repository))
        current_state = session.state
        for land_id in ("alice:1", "alice:2", "alice:3", "alice:4"):
            current_state = move_object(
                current_state,
                instance_id=land_id,
                from_zone="hand",
                to_zone="battlefield",
                player_id="alice",
            )
        current_state = move_object(
            current_state,
            instance_id="bob:1",
            from_zone="hand",
            to_zone="battlefield",
            player_id="bob",
        )
        session = type(session)(state=current_state, event_log=session.event_log)

        for source_instance_id in session.state.players["alice"].battlefield:
            session = activate_mana_ability(
                session,
                ActivateManaAbilityAction(player_id="alice", source_instance_id=source_instance_id),
                repository,
            )

        result = cast_noncreature_spell(
            session,
            CastNonCreatureSpellAction(
                player_id="alice",
                card_instance_id="alice:5",
                target_instance_id="bob:1",
            ),
            repository,
        )

        self.assertEqual(
            [event.event_type for event in result.event_log[-7:]],
            [
                "spell_cast",
                "object_moved_between_zones",
                "spell_resolved",
                "permanent_destroyed",
                "object_moved_between_zones",
                "life_total_changed",
                "object_moved_between_zones",
            ],
        )
        self.assertEqual(result.event_log[-2].payload["player_id"], "bob")
        self.assertEqual(result.event_log[-2].payload["life_total"], 24)


if __name__ == "__main__":
    unittest.main()

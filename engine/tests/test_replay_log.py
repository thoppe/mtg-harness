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
ISLAND = "b2c6aa39-2d2a-459c-a555-fb48ba993373"
MUCK_RATS = "bca13a12-6723-4a5e-8f1b-21646a8b3e7e"
PATH_OF_PEACE = "b7593cf8-4dcb-473b-a2ef-180fffe66738"
HAND_OF_DEATH = "dc45b2e3-272b-479b-8e3b-36eead606a3a"
TIME_EBB = "30cc8f7b-3c28-40f5-8f8f-157e8212280b"
TIDAL_SURGE = "be738992-77fe-498d-b219-e5da4ce5bf07"
MOUNTAIN = "a3fb7228-e76b-4e96-a40e-20b5fed75685"
SWAMP = "56719f6a-1a6c-4c0a-8d21-18f7d7350b68"
BORDER_GUARD = "1ef5003c-f540-4cdc-913f-7d5280ad9f62"
VOLCANIC_HAMMER = "98fa5a06-0553-40fd-999c-bc31c9b3f4db"
MIND_ROT = "ad44cf74-b717-48fb-9fa2-77512024d76a"
FOREST = "b34bb2dc-c1af-4d77-b0b3-a0fb342a5fc6"
WINTERS_GRASP = "e9b8679d-52a9-4f0f-9365-f3e4b7a69805"
SYMBOL_OF_UNSUMMONING = "c44f1a81-269b-4f05-8ff2-e7ce19a93937"
ARMAGEDDON = "c9ed8b01-959a-47d6-891e-0abbdccf6e4f"
RAIN_OF_SALT = "1219e330-01ac-405a-b75a-dd4298598167"
SACRED_NECTAR = "30870ee5-6ad7-48a9-983e-d3b018f2344f"
WRATH_OF_GOD = "34515b16-c9a4-4f98-8c77-416a7a523407"
RAIN_OF_DAGGERS = "e2048201-6dc9-4cf5-916f-1d867ae8dbdd"


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

    def test_time_ebb_replay_trace_includes_battlefield_to_library_move(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        setup = SetupInput(
            game_id="replay-time-ebb",
            players=("alice", "bob"),
            starting_player="alice",
            libraries={
                "alice": (PLAINS, PLAINS, "b2c6aa39-2d2a-459c-a555-fb48ba993373", TIME_EBB),
                "bob": (MUCK_RATS, PLAINS),
            },
            opening_hands={
                "alice": (PLAINS, PLAINS, "b2c6aa39-2d2a-459c-a555-fb48ba993373", TIME_EBB),
                "bob": (MUCK_RATS,),
            },
            rng_seed=51,
        )

        session = start_first_turn(initialize_game(setup, repository))
        current_state = session.state
        for land_id in ("alice:1", "alice:2", "alice:3"):
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
                card_instance_id="alice:4",
                target_instance_id="bob:1",
            ),
            repository,
        )

        self.assertEqual(
            [event.event_type for event in result.event_log[-5:]],
            [
                "spell_cast",
                "object_moved_between_zones",
                "spell_resolved",
                "object_moved_between_zones",
                "object_moved_between_zones",
            ],
        )
        self.assertEqual(result.event_log[-2].payload["from_zone"], "battlefield")
        self.assertEqual(result.event_log[-2].payload["to_zone"], "library")
        self.assertEqual(result.event_log[-2].payload["library_position"], "top")

    def test_hand_of_death_replay_trace_includes_target_destruction_events(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        setup = SetupInput(
            game_id="replay-hand-of-death",
            players=("alice", "bob"),
            starting_player="alice",
            libraries={
                "alice": (SWAMP, SWAMP, SWAMP, HAND_OF_DEATH),
                "bob": (BORDER_GUARD, MUCK_RATS),
            },
            opening_hands={
                "alice": (SWAMP, SWAMP, SWAMP, HAND_OF_DEATH),
                "bob": (BORDER_GUARD, MUCK_RATS),
            },
            rng_seed=63,
        )

        session = start_first_turn(initialize_game(setup, repository))
        current_state = session.state
        for land_id in ("alice:1", "alice:2", "alice:3"):
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
        current_state = move_object(
            current_state,
            instance_id="bob:2",
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
                card_instance_id="alice:4",
                target_instance_id="bob:1",
            ),
            repository,
        )

        self.assertEqual(
            [event.event_type for event in result.event_log[-6:]],
            [
                "spell_cast",
                "object_moved_between_zones",
                "spell_resolved",
                "permanent_destroyed",
                "object_moved_between_zones",
                "object_moved_between_zones",
            ],
        )
        self.assertEqual(result.event_log[-3].payload["card_instance_id"], "bob:1")

    def test_volcanic_hammer_replay_trace_includes_damage_and_sba_events(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        setup = SetupInput(
            game_id="replay-volcanic-hammer",
            players=("alice", "bob"),
            starting_player="alice",
            libraries={
                "alice": (MOUNTAIN, MOUNTAIN, VOLCANIC_HAMMER),
                "bob": (MUCK_RATS,),
            },
            opening_hands={
                "alice": (MOUNTAIN, MOUNTAIN, VOLCANIC_HAMMER),
                "bob": (MUCK_RATS,),
            },
            rng_seed=57,
        )

        session = start_first_turn(initialize_game(setup, repository))
        current_state = session.state
        for land_id in ("alice:1", "alice:2"):
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
                card_instance_id="alice:3",
                target_instance_id="bob:1",
            ),
            repository,
        )

        self.assertEqual(
            [event.event_type for event in result.event_log[-8:]],
            [
                "spell_cast",
                "object_moved_between_zones",
                "spell_resolved",
                "damage_applied",
                "state_based_actions_checked",
                "permanent_destroyed",
                "object_moved_between_zones",
                "object_moved_between_zones",
            ],
        )

    def test_mind_rot_replay_trace_includes_hand_to_graveyard_discards(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        setup = SetupInput(
            game_id="replay-mind-rot",
            players=("alice", "bob"),
            starting_player="alice",
            libraries={
                "alice": (SWAMP, SWAMP, SWAMP, MIND_ROT),
                "bob": (PLAINS, MUCK_RATS, BORDER_GUARD),
            },
            opening_hands={
                "alice": (SWAMP, SWAMP, SWAMP, MIND_ROT),
                "bob": (PLAINS, MUCK_RATS, BORDER_GUARD),
            },
            rng_seed=58,
        )

        session = start_first_turn(initialize_game(setup, repository))
        current_state = session.state
        for land_id in ("alice:1", "alice:2", "alice:3"):
            current_state = move_object(
                current_state,
                instance_id=land_id,
                from_zone="hand",
                to_zone="battlefield",
                player_id="alice",
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
                card_instance_id="alice:4",
                target_instance_id="bob",
            ),
            repository,
        )

        non_mana_events = [event.event_type for event in result.event_log if event.event_type != "mana_added"]
        spell_cast_index = max(index for index, event_type in enumerate(non_mana_events) if event_type == "spell_cast")
        self.assertEqual(
            non_mana_events[spell_cast_index:],
            [
                "spell_cast",
                "object_moved_between_zones",
                "spell_resolved",
                "object_moved_between_zones",
                "object_moved_between_zones",
                "object_moved_between_zones",
            ],
        )
        self.assertEqual(result.event_log[-3].payload["from_zone"], "hand")
        self.assertEqual(result.event_log[-2].payload["from_zone"], "hand")

    def test_winters_grasp_replay_trace_includes_land_destruction(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        setup = SetupInput(
            game_id="replay-winters-grasp",
            players=("alice", "bob"),
            starting_player="alice",
            libraries={
                "alice": (FOREST, FOREST, FOREST, WINTERS_GRASP),
                "bob": (PLAINS,),
            },
            opening_hands={
                "alice": (FOREST, FOREST, FOREST, WINTERS_GRASP),
                "bob": (PLAINS,),
            },
            rng_seed=59,
        )

        session = start_first_turn(initialize_game(setup, repository))
        current_state = session.state
        for land_id in ("alice:1", "alice:2", "alice:3"):
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
                card_instance_id="alice:4",
                target_instance_id="bob:1",
            ),
            repository,
        )

        self.assertEqual(
            [event.event_type for event in result.event_log[-6:]],
            [
                "spell_cast",
                "object_moved_between_zones",
                "spell_resolved",
                "permanent_destroyed",
                "object_moved_between_zones",
                "object_moved_between_zones",
            ],
        )

    def test_armageddon_replay_trace_includes_repeated_land_destruction(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        setup = SetupInput(
            game_id="replay-armageddon",
            players=("alice", "bob"),
            starting_player="alice",
            libraries={
                "alice": (PLAINS, PLAINS, PLAINS, PLAINS, ARMAGEDDON),
                "bob": (PLAINS, SWAMP),
            },
            opening_hands={
                "alice": (PLAINS, PLAINS, PLAINS, PLAINS, ARMAGEDDON),
                "bob": (PLAINS, SWAMP),
            },
            rng_seed=61,
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
        for land_id in ("bob:1", "bob:2"):
            current_state = move_object(
                current_state,
                instance_id=land_id,
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
                target_instance_id=None,
            ),
            repository,
        )

        self.assertEqual(
            [event.event_type for event in result.event_log[-16:]],
            [
                "spell_cast",
                "object_moved_between_zones",
                "spell_resolved",
                "permanent_destroyed",
                "object_moved_between_zones",
                "permanent_destroyed",
                "object_moved_between_zones",
                "permanent_destroyed",
                "object_moved_between_zones",
                "permanent_destroyed",
                "object_moved_between_zones",
                "permanent_destroyed",
                "object_moved_between_zones",
                "permanent_destroyed",
                "object_moved_between_zones",
                "object_moved_between_zones",
            ],
        )
        self.assertEqual(result.event_log[-1].payload["to_zone"], "graveyard")

    def test_rain_of_salt_replay_trace_includes_two_target_land_destruction(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        setup = SetupInput(
            game_id="replay-rain-of-salt",
            players=("alice", "bob"),
            starting_player="alice",
            libraries={
                "alice": (MOUNTAIN, MOUNTAIN, MOUNTAIN, MOUNTAIN, MOUNTAIN, MOUNTAIN, RAIN_OF_SALT),
                "bob": (PLAINS, SWAMP),
            },
            opening_hands={
                "alice": (MOUNTAIN, MOUNTAIN, MOUNTAIN, MOUNTAIN, MOUNTAIN, MOUNTAIN, RAIN_OF_SALT),
                "bob": (PLAINS, SWAMP),
            },
            rng_seed=62,
        )

        session = start_first_turn(initialize_game(setup, repository))
        current_state = session.state
        for land_id in ("alice:1", "alice:2", "alice:3", "alice:4", "alice:5", "alice:6"):
            current_state = move_object(
                current_state,
                instance_id=land_id,
                from_zone="hand",
                to_zone="battlefield",
                player_id="alice",
            )
        for land_id in ("bob:1", "bob:2"):
            current_state = move_object(
                current_state,
                instance_id=land_id,
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
                card_instance_id="alice:7",
                target_instance_ids=("bob:1", "bob:2"),
            ),
            repository,
        )

        self.assertEqual(
            [event.event_type for event in result.event_log[-8:]],
            [
                "spell_cast",
                "object_moved_between_zones",
                "spell_resolved",
                "permanent_destroyed",
                "object_moved_between_zones",
                "permanent_destroyed",
                "object_moved_between_zones",
                "object_moved_between_zones",
            ],
        )

    def test_wrath_of_god_replay_trace_includes_global_creature_destruction(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        setup = SetupInput(
            game_id="replay-wrath-of-god",
            players=("alice", "bob"),
            starting_player="alice",
            libraries={
                "alice": (PLAINS, PLAINS, PLAINS, PLAINS, WRATH_OF_GOD),
                "bob": (MUCK_RATS, BORDER_GUARD),
            },
            opening_hands={
                "alice": (PLAINS, PLAINS, PLAINS, PLAINS, WRATH_OF_GOD),
                "bob": (MUCK_RATS, BORDER_GUARD),
            },
            rng_seed=63,
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
        current_state = move_object(
            current_state,
            instance_id="bob:2",
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
                target_instance_ids=(),
            ),
            repository,
        )

        self.assertEqual(
            [event.event_type for event in result.event_log[-8:]],
            [
                "spell_cast",
                "object_moved_between_zones",
                "spell_resolved",
                "permanent_destroyed",
                "object_moved_between_zones",
                "permanent_destroyed",
                "object_moved_between_zones",
                "object_moved_between_zones",
            ],
        )

    def test_sacred_nectar_replay_trace_includes_life_gain(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        setup = SetupInput(
            game_id="replay-sacred-nectar",
            players=("alice", "bob"),
            starting_player="alice",
            libraries={
                "alice": (PLAINS, PLAINS, SACRED_NECTAR),
                "bob": (PLAINS,),
            },
            opening_hands={
                "alice": (PLAINS, PLAINS, SACRED_NECTAR),
                "bob": (PLAINS,),
            },
            rng_seed=65,
        )

        session = start_first_turn(initialize_game(setup, repository))
        current_state = session.state
        for land_id in ("alice:1", "alice:2"):
            current_state = move_object(
                current_state,
                instance_id=land_id,
                from_zone="hand",
                to_zone="battlefield",
                player_id="alice",
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
                card_instance_id="alice:3",
                target_instance_ids=(),
            ),
            repository,
        )

        self.assertEqual(
            [event.event_type for event in result.event_log[-5:]],
            [
                "spell_cast",
                "object_moved_between_zones",
                "spell_resolved",
                "life_total_changed",
                "object_moved_between_zones",
            ],
        )

    def test_rain_of_daggers_replay_trace_includes_mass_creature_destruction_and_life_loss(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        setup = SetupInput(
            game_id="replay-rain-of-daggers",
            players=("alice", "bob"),
            starting_player="alice",
            libraries={
                "alice": (SWAMP, SWAMP, SWAMP, SWAMP, SWAMP, SWAMP, RAIN_OF_DAGGERS),
                "bob": (MUCK_RATS, BORDER_GUARD),
            },
            opening_hands={
                "alice": (SWAMP, SWAMP, SWAMP, SWAMP, SWAMP, SWAMP, RAIN_OF_DAGGERS),
                "bob": (MUCK_RATS, BORDER_GUARD),
            },
            rng_seed=62,
        )

        session = start_first_turn(initialize_game(setup, repository))
        current_state = session.state
        for land_id in ("alice:1", "alice:2", "alice:3", "alice:4", "alice:5", "alice:6"):
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
        current_state = move_object(
            current_state,
            instance_id="bob:2",
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
                card_instance_id="alice:7",
                target_instance_id="bob",
            ),
            repository,
        )

        self.assertEqual(
            [event.event_type for event in result.event_log[-9:]],
            [
                "spell_cast",
                "object_moved_between_zones",
                "spell_resolved",
                "permanent_destroyed",
                "object_moved_between_zones",
                "permanent_destroyed",
                "object_moved_between_zones",
                "life_total_changed",
                "object_moved_between_zones",
            ],
        )
        self.assertEqual(result.event_log[-2].payload["player_id"], "alice")
        self.assertEqual(result.event_log[-2].payload["life_total"], 16)

    def test_symbol_of_unsummoning_replay_trace_includes_bounce_and_draw(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        setup = SetupInput(
            game_id="replay-symbol-of-unsummoning",
            players=("alice", "bob"),
            starting_player="alice",
            libraries={
                "alice": (ISLAND, ISLAND, ISLAND, SYMBOL_OF_UNSUMMONING, PLAINS),
                "bob": (MUCK_RATS,),
            },
            opening_hands={
                "alice": (ISLAND, ISLAND, ISLAND, SYMBOL_OF_UNSUMMONING),
                "bob": (MUCK_RATS,),
            },
            rng_seed=60,
        )

        session = start_first_turn(initialize_game(setup, repository))
        current_state = session.state
        for land_id in ("alice:1", "alice:2", "alice:3"):
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
                card_instance_id="alice:4",
                target_instance_id="bob:1",
            ),
            repository,
        )

        non_mana_events = [event.event_type for event in result.event_log if event.event_type != "mana_added"]
        spell_cast_index = max(index for index, event_type in enumerate(non_mana_events) if event_type == "spell_cast")
        self.assertEqual(
            non_mana_events[spell_cast_index:],
            [
                "spell_cast",
                "object_moved_between_zones",
                "spell_resolved",
                "object_moved_between_zones",
                "object_moved_between_zones",
                "object_moved_between_zones",
            ],
        )

    def test_tidal_surge_replay_trace_includes_permanent_tapped_events(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        setup = SetupInput(
            game_id="replay-tidal-surge",
            players=("alice", "bob"),
            starting_player="alice",
            libraries={
                "alice": (ISLAND, PLAINS, TIDAL_SURGE),
                "bob": (MUCK_RATS, BORDER_GUARD),
            },
            opening_hands={
                "alice": (ISLAND, PLAINS, TIDAL_SURGE),
                "bob": (MUCK_RATS, BORDER_GUARD),
            },
            rng_seed=70,
        )

        session = start_first_turn(initialize_game(setup, repository))
        current_state = session.state
        for land_id in ("alice:1", "alice:2"):
            current_state = move_object(
                current_state,
                instance_id=land_id,
                from_zone="hand",
                to_zone="battlefield",
                player_id="alice",
            )
        for creature_id in ("bob:1", "bob:2"):
            current_state = move_object(
                current_state,
                instance_id=creature_id,
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
                card_instance_id="alice:3",
                target_instance_ids=("bob:1", "bob:2"),
            ),
            repository,
        )

        self.assertEqual(
            [event.event_type for event in result.event_log[-6:]],
            [
                "spell_cast",
                "object_moved_between_zones",
                "spell_resolved",
                "permanent_tapped",
                "permanent_tapped",
                "object_moved_between_zones",
            ],
        )
        self.assertEqual(result.event_log[-3].payload["card_instance_id"], "bob:1")
        self.assertEqual(result.event_log[-2].payload["card_instance_id"], "bob:2")


if __name__ == "__main__":
    unittest.main()

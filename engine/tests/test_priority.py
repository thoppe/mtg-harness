from __future__ import annotations

from dataclasses import replace
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mtg_engine.actions.models import (
    ActivateManaAbilityAction,
    AdvanceStepAction,
    CastCreatureSpellAction,
    CastNonCreatureSpellAction,
    DeclareAttackersAction,
    DeclareBlockersAction,
    PassPriorityAction,
    PlayLandAction,
)
from mtg_engine.cards.repository import CardRepository
from mtg_engine.flow.priority import enumerate_legal_actions
from mtg_engine.flow.setup import SetupInput, initialize_game
from mtg_engine.flow.turns import (
    activate_mana_ability,
    advance_to_begin_combat,
    advance_to_cleanup,
    cast_creature_spell,
    declare_attackers,
    declare_blockers,
    pass_priority,
    play_land,
    resolve_combat_damage,
    start_first_turn,
    start_next_turn,
)
from mtg_engine.state.zones import move_object, update_object


INFORMATION_DIR = Path(__file__).resolve().parents[2] / "information"
SWAMP = "56719f6a-1a6c-4c0a-8d21-18f7d7350b68"
ISLAND = "b2c6aa39-2d2a-459c-a555-fb48ba993373"
PLAINS = "bc71ebf6-2056-41f7-be35-b2e5c34afa99"
MOUNTAIN = "a3fb7228-e76b-4e96-a40e-20b5fed75685"
BORDER_GUARD = "1ef5003c-f540-4cdc-913f-7d5280ad9f62"
FOOT_SOLDIERS = "a768ba13-4d1c-4dce-a4a6-86a39c069c3f"
MUCK_RATS = "bca13a12-6723-4a5e-8f1b-21646a8b3e7e"
VENGEANCE = "1d001145-5d14-43a9-bf3b-3ce5c20b2a46"
PATH_OF_PEACE = "b7593cf8-4dcb-473b-a2ef-180fffe66738"
HAND_OF_DEATH = "dc45b2e3-272b-479b-8e3b-36eead606a3a"
TOUCH_OF_BRILLIANCE = "6365aba1-78d3-416c-89cd-9449578eedbf"
TIME_EBB = "30cc8f7b-3c28-40f5-8f8f-157e8212280b"
TIDAL_SURGE = "be738992-77fe-498d-b219-e5da4ce5bf07"
VOLCANIC_HAMMER = "98fa5a06-0553-40fd-999c-bc31c9b3f4db"
LAVA_AXE = "387b6b07-a283-412d-94c3-f7f1dc76e858"
MIND_ROT = "ad44cf74-b717-48fb-9fa2-77512024d76a"
FOREST = "b34bb2dc-c1af-4d77-b0b3-a0fb342a5fc6"
WINTERS_GRASP = "e9b8679d-52a9-4f0f-9365-f3e4b7a69805"
SYMBOL_OF_UNSUMMONING = "c44f1a81-269b-4f05-8ff2-e7ce19a93937"
ARMAGEDDON = "c9ed8b01-959a-47d6-891e-0abbdccf6e4f"
RAIN_OF_SALT = "1219e330-01ac-405a-b75a-dd4298598167"
SACRED_NECTAR = "30870ee5-6ad7-48a9-983e-d3b018f2344f"
ARMORED_PEGASUS = "f097a059-5505-4c3c-b879-7853ab6972ed"
STORM_CROW = "000d5588-5a4c-434e-988d-396632ade42c"
KEEN_EYED_ARCHERS = "0ace32d6-7261-447c-9ee2-e03febaab91b"
ANACONDA = "3eff03f1-2c5f-4c59-b465-a8c4cd05e1ba"
WRATH_OF_GOD = "34515b16-c9a4-4f98-8c77-416a7a523407"
WALL_OF_GRANITE = "8445094f-008b-491a-977c-e8582d5ab72c"
RAIN_OF_DAGGERS = "e2048201-6dc9-4cf5-916f-1d867ae8dbdd"


class PriorityTests(unittest.TestCase):
    def test_precombat_main_enumerates_land_then_step_controls(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _build_main_phase_session(repository)

        actions = enumerate_legal_actions(session.state, repository)

        self.assertEqual(
            actions,
            (
                PlayLandAction(player_id="alice", card_instance_id="alice:1"),
                AdvanceStepAction(player_id="alice", to_step="begin_combat_step"),
                PassPriorityAction(player_id="alice"),
            ),
        )

    def test_played_land_exposes_mana_ability_and_step_controls(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _build_main_phase_session(repository)
        session = play_land(session, PlayLandAction(player_id="alice", card_instance_id="alice:1"), repository)

        actions = enumerate_legal_actions(session.state, repository)

        self.assertEqual(
            actions,
            (
                ActivateManaAbilityAction(player_id="alice", source_instance_id="alice:1"),
                AdvanceStepAction(player_id="alice", to_step="begin_combat_step"),
                PassPriorityAction(player_id="alice"),
            ),
        )

    def test_pass_priority_auto_advances_when_opponent_has_no_supported_actions(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _build_main_phase_session(repository)

        result = pass_priority(session, PassPriorityAction(player_id="alice"), repository)

        self.assertEqual(result.state.turn.step, "declare_attackers_step")
        self.assertEqual(result.state.turn.priority_player, "alice")
        self.assertEqual(
            [event.event_type for event in result.event_log[-4:]],
            ["priority_passed", "priority_passed", "step_changed", "step_changed"],
        )

    def test_declare_attackers_window_enumerates_attack_subsets(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _build_attack_ready_session(repository)
        session = advance_to_begin_combat(session)

        actions = enumerate_legal_actions(session.state, repository)

        self.assertEqual(
            actions,
            (
                DeclareAttackersAction(player_id="alice", attacker_ids=()),
                DeclareAttackersAction(player_id="alice", attacker_ids=("alice:4",)),
            ),
        )

    def test_declare_blockers_window_enumerates_multi_block_assignments(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _build_multi_block_ready_session(repository)
        session = advance_to_begin_combat(session)
        session = declare_attackers(
            session,
            DeclareAttackersAction(player_id="alice", attacker_ids=("alice:4",)),
            repository,
        )

        actions = enumerate_legal_actions(session.state, repository)

        self.assertIn(DeclareBlockersAction(player_id="bob", blockers={}), actions)
        self.assertIn(DeclareBlockersAction(player_id="bob", blockers={"alice:4": ("bob:4",)}), actions)
        self.assertIn(DeclareBlockersAction(player_id="bob", blockers={"alice:4": ("bob:6",)}), actions)
        self.assertIn(DeclareBlockersAction(player_id="bob", blockers={"alice:4": ("bob:4", "bob:6")}), actions)

    def test_precombat_main_enumerates_vengeance_when_tapped_target_and_mana_exist(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _build_vengeance_ready_session(repository)

        actions = enumerate_legal_actions(session.state, repository)

        self.assertIn(
            CastNonCreatureSpellAction(
                player_id="alice",
                card_instance_id="alice:5",
                target_instance_id="bob:1",
            ),
            actions,
        )

    def test_precombat_main_enumerates_path_of_peace_for_untapped_creature_target(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _build_path_of_peace_ready_session(repository)

        actions = enumerate_legal_actions(session.state, repository)

        self.assertIn(
            CastNonCreatureSpellAction(
                player_id="alice",
                card_instance_id="alice:5",
                target_instance_id="bob:1",
            ),
            actions,
        )

    def test_precombat_main_enumerates_hand_of_death_for_nonblack_creature_only(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _build_hand_of_death_ready_session(repository)

        actions = enumerate_legal_actions(session.state, repository)

        self.assertIn(
            CastNonCreatureSpellAction(
                player_id="alice",
                card_instance_id="alice:4",
                target_instance_id="bob:1",
            ),
            actions,
        )
        self.assertNotIn(
            CastNonCreatureSpellAction(
                player_id="alice",
                card_instance_id="alice:4",
                target_instance_id="bob:2",
            ),
            actions,
        )

    def test_precombat_main_enumerates_touch_of_brilliance_without_target(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _build_touch_of_brilliance_ready_session(repository)

        actions = enumerate_legal_actions(session.state, repository)

        self.assertIn(
            CastNonCreatureSpellAction(
                player_id="alice",
                card_instance_id="alice:5",
                target_instance_id=None,
            ),
            actions,
        )

    def test_precombat_main_enumerates_time_ebb_for_creature_target(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _build_time_ebb_ready_session(repository)

        actions = enumerate_legal_actions(session.state, repository)

        self.assertIn(
            CastNonCreatureSpellAction(
                player_id="alice",
                card_instance_id="alice:4",
                target_instance_id="bob:1",
            ),
            actions,
        )

    def test_precombat_main_enumerates_tidal_surge_for_up_to_three_nonflying_creatures(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _build_tidal_surge_ready_session(repository)

        actions = enumerate_legal_actions(session.state, repository)

        self.assertIn(
            CastNonCreatureSpellAction(
                player_id="alice",
                card_instance_id="alice:3",
                target_instance_ids=(),
            ),
            actions,
        )
        self.assertIn(
            CastNonCreatureSpellAction(
                player_id="alice",
                card_instance_id="alice:3",
                target_instance_ids=("bob:1",),
            ),
            actions,
        )
        self.assertIn(
            CastNonCreatureSpellAction(
                player_id="alice",
                card_instance_id="alice:3",
                target_instance_ids=("bob:1", "bob:2"),
            ),
            actions,
        )
        self.assertNotIn(
            CastNonCreatureSpellAction(
                player_id="alice",
                card_instance_id="alice:3",
                target_instance_ids=("bob:3",),
            ),
            actions,
        )

    def test_precombat_main_enumerates_volcanic_hammer_for_creature_and_player_targets(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _build_volcanic_hammer_ready_session(repository)

        actions = enumerate_legal_actions(session.state, repository)

        self.assertIn(
            CastNonCreatureSpellAction(
                player_id="alice",
                card_instance_id="alice:3",
                target_instance_id="bob:1",
            ),
            actions,
        )
        self.assertIn(
            CastNonCreatureSpellAction(
                player_id="alice",
                card_instance_id="alice:3",
                target_instance_id="bob",
            ),
            actions,
        )

    def test_precombat_main_enumerates_lava_axe_for_player_target(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _build_lava_axe_ready_session(repository)

        actions = enumerate_legal_actions(session.state, repository)

        self.assertIn(
            CastNonCreatureSpellAction(
                player_id="alice",
                card_instance_id="alice:6",
                target_instance_id="bob",
            ),
            actions,
        )

    def test_precombat_main_enumerates_mind_rot_for_player_target(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _build_mind_rot_ready_session(repository)

        actions = enumerate_legal_actions(session.state, repository)

        self.assertIn(
            CastNonCreatureSpellAction(
                player_id="alice",
                card_instance_id="alice:4",
                target_instance_id="bob",
            ),
            actions,
        )

    def test_precombat_main_enumerates_winters_grasp_for_land_target(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _build_winters_grasp_ready_session(repository)

        actions = enumerate_legal_actions(session.state, repository)

        self.assertIn(
            CastNonCreatureSpellAction(
                player_id="alice",
                card_instance_id="alice:4",
                target_instance_id="bob:1",
            ),
            actions,
        )

    def test_precombat_main_enumerates_symbol_of_unsummoning_for_creature_target(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _build_symbol_of_unsummoning_ready_session(repository)

        actions = enumerate_legal_actions(session.state, repository)

        self.assertIn(
            CastNonCreatureSpellAction(
                player_id="alice",
                card_instance_id="alice:4",
                target_instance_id="bob:1",
            ),
            actions,
        )

    def test_precombat_main_enumerates_armageddon_without_target(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _build_armageddon_ready_session(repository)

        actions = enumerate_legal_actions(session.state, repository)

        self.assertIn(
            CastNonCreatureSpellAction(
                player_id="alice",
                card_instance_id="alice:5",
                target_instance_id=None,
            ),
            actions,
        )

    def test_precombat_main_enumerates_rain_of_salt_for_two_distinct_land_targets(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _build_rain_of_salt_ready_session(repository)

        actions = enumerate_legal_actions(session.state, repository)

        self.assertIn(
            CastNonCreatureSpellAction(
                player_id="alice",
                card_instance_id="alice:7",
                target_instance_ids=("bob:1", "bob:2"),
            ),
            actions,
        )
        self.assertNotIn(
            CastNonCreatureSpellAction(
                player_id="alice",
                card_instance_id="alice:7",
                target_instance_ids=("bob:1", "bob:1"),
            ),
            actions,
        )

    def test_precombat_main_enumerates_wrath_of_god_without_target(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _build_wrath_of_god_ready_session(repository)

        actions = enumerate_legal_actions(session.state, repository)

        self.assertIn(
            CastNonCreatureSpellAction(
                player_id="alice",
                card_instance_id="alice:5",
                target_instance_ids=(),
            ),
            actions,
        )

    def test_precombat_main_enumerates_sacred_nectar_without_target(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _build_sacred_nectar_ready_session(repository)

        actions = enumerate_legal_actions(session.state, repository)

        self.assertIn(
            CastNonCreatureSpellAction(
                player_id="alice",
                card_instance_id="alice:3",
                target_instance_ids=(),
            ),
            actions,
        )

    def test_precombat_main_enumerates_rain_of_daggers_for_opponent_target_only(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _build_rain_of_daggers_ready_session(repository)

        actions = enumerate_legal_actions(session.state, repository)

        self.assertIn(
            CastNonCreatureSpellAction(
                player_id="alice",
                card_instance_id="alice:7",
                target_instance_id="bob",
            ),
            actions,
        )
        self.assertNotIn(
            CastNonCreatureSpellAction(
                player_id="alice",
                card_instance_id="alice:7",
                target_instance_id="alice",
            ),
            actions,
        )

    def test_declare_blockers_window_excludes_nonflying_blockers_against_armored_pegasus(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _build_flying_block_ready_session(repository)
        session = advance_to_begin_combat(session)
        session = declare_attackers(
            session,
            DeclareAttackersAction(player_id="alice", attacker_ids=("alice:3",)),
            repository,
        )

        actions = enumerate_legal_actions(session.state, repository)

        self.assertEqual(
            actions,
            (DeclareBlockersAction(player_id="bob", blockers={}),),
        )

    def test_declare_blockers_window_allows_reach_blocker_against_armored_pegasus(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _build_reach_block_ready_session(repository)
        session = advance_to_begin_combat(session)
        session = declare_attackers(
            session,
            DeclareAttackersAction(player_id="alice", attacker_ids=("alice:3",)),
            repository,
        )

        actions = enumerate_legal_actions(session.state, repository)

        self.assertIn(
            DeclareBlockersAction(player_id="bob", blockers={"alice:3": ("bob:4",)}),
            actions,
        )

    def test_declare_blockers_window_excludes_blockers_against_anaconda_when_defender_controls_swamp(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _build_swampwalk_block_locked_session(repository)
        session = advance_to_begin_combat(session)
        session = declare_attackers(
            session,
            DeclareAttackersAction(player_id="alice", attacker_ids=("alice:5",)),
            repository,
        )

        actions = enumerate_legal_actions(session.state, repository)

        self.assertEqual(actions, (DeclareBlockersAction(player_id="bob", blockers={}),))

    def test_declare_blockers_window_allows_blocker_against_anaconda_without_swamp(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _build_swampwalk_blockable_session(repository)
        session = advance_to_begin_combat(session)
        session = declare_attackers(
            session,
            DeclareAttackersAction(player_id="alice", attacker_ids=("alice:5",)),
            repository,
        )

        actions = enumerate_legal_actions(session.state, repository)

        self.assertIn(
            DeclareBlockersAction(player_id="bob", blockers={"alice:5": ("bob:2",)}),
            actions,
        )

    def test_declare_attackers_window_excludes_wall_of_granite_from_attack_subsets(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _build_defender_attack_ready_session(repository)
        session = advance_to_begin_combat(session)

        actions = enumerate_legal_actions(session.state, repository)

        self.assertEqual(
            actions,
            (DeclareAttackersAction(player_id="alice", attacker_ids=()),),
        )


def _build_main_phase_session(repository: CardRepository):
    setup = SetupInput(
        game_id="priority-001",
        players=("alice", "bob"),
        starting_player="alice",
        libraries={
            "alice": (PLAINS, FOOT_SOLDIERS),
            "bob": (PLAINS,),
        },
        opening_hands={
            "alice": (PLAINS,),
            "bob": (PLAINS,),
        },
        rng_seed=13,
    )
    return start_first_turn(initialize_game(setup, repository))


def _build_attack_ready_session(repository: CardRepository):
    setup = SetupInput(
        game_id="priority-attackers",
        players=("alice", "bob"),
        starting_player="alice",
        libraries={
            "alice": (PLAINS, PLAINS, PLAINS, BORDER_GUARD),
            "bob": (PLAINS,),
        },
        opening_hands={
            "alice": (PLAINS, PLAINS, PLAINS, BORDER_GUARD),
            "bob": (PLAINS,),
        },
        rng_seed=31,
    )
    session = start_first_turn(initialize_game(setup, repository))
    session = _cast_creature_from_normal_turns(session, repository, "alice", "alice:4")
    return _advance_to_player_main_phase(_advance_to_next_turn(session, repository), repository, "alice")


def _build_multi_block_ready_session(repository: CardRepository):
    setup = SetupInput(
        game_id="priority-blockers",
        players=("alice", "bob"),
        starting_player="alice",
        libraries={
            "alice": (PLAINS, PLAINS, PLAINS, BORDER_GUARD),
            "bob": (PLAINS, PLAINS, PLAINS, BORDER_GUARD, SWAMP, MUCK_RATS),
        },
        opening_hands={
            "alice": (PLAINS, PLAINS, PLAINS, BORDER_GUARD),
            "bob": (PLAINS, PLAINS, PLAINS, BORDER_GUARD, SWAMP, MUCK_RATS),
        },
        rng_seed=37,
    )
    session = start_first_turn(initialize_game(setup, repository))
    session = _cast_creature_from_normal_turns(session, repository, "alice", "alice:4")
    session = _advance_to_player_main_phase(_advance_to_next_turn(session, repository), repository, "bob")
    session = _cast_creature_from_normal_turns(session, repository, "bob", "bob:4")
    session = _advance_to_player_main_phase(_advance_to_next_turn(session, repository), repository, "bob")
    session = _cast_creature_from_normal_turns(session, repository, "bob", "bob:6")
    return _advance_to_player_main_phase(_advance_to_next_turn(session, repository), repository, "alice")


def _build_vengeance_ready_session(repository: CardRepository):
    setup = SetupInput(
        game_id="priority-vengeance",
        players=("alice", "bob"),
        starting_player="alice",
        libraries={
            "alice": (PLAINS, PLAINS, PLAINS, PLAINS, VENGEANCE),
            "bob": (MUCK_RATS,),
        },
        opening_hands={
            "alice": (PLAINS, PLAINS, PLAINS, PLAINS, VENGEANCE),
            "bob": (MUCK_RATS,),
        },
        rng_seed=41,
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
    current_state = update_object(
        current_state,
        replace(current_state.objects["bob:1"], tapped=True),
    )
    session = replace(session, state=current_state)

    for source_instance_id in session.state.players["alice"].battlefield:
        session = activate_mana_ability(
            session,
            ActivateManaAbilityAction(player_id="alice", source_instance_id=source_instance_id),
            repository,
        )
    return session


def _build_path_of_peace_ready_session(repository: CardRepository):
    setup = SetupInput(
        game_id="priority-path-of-peace",
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
        rng_seed=43,
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
    session = replace(session, state=current_state)

    for source_instance_id in session.state.players["alice"].battlefield:
        session = activate_mana_ability(
            session,
            ActivateManaAbilityAction(player_id="alice", source_instance_id=source_instance_id),
            repository,
        )
    return session


def _build_hand_of_death_ready_session(repository: CardRepository):
    setup = SetupInput(
        game_id="priority-hand-of-death",
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
        rng_seed=68,
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

    for creature_id in ("bob:1", "bob:2"):
        current_state = move_object(
            current_state,
            instance_id=creature_id,
            from_zone="hand",
            to_zone="battlefield",
            player_id="bob",
        )
    session = replace(session, state=current_state)

    for source_instance_id in session.state.players["alice"].battlefield:
        session = activate_mana_ability(
            session,
            ActivateManaAbilityAction(player_id="alice", source_instance_id=source_instance_id),
            repository,
        )
    return session


def _build_touch_of_brilliance_ready_session(repository: CardRepository):
    setup = SetupInput(
        game_id="priority-touch-of-brilliance",
        players=("alice", "bob"),
        starting_player="alice",
        libraries={
            "alice": (PLAINS, PLAINS, PLAINS, ISLAND, TOUCH_OF_BRILLIANCE, PLAINS, PLAINS),
            "bob": (PLAINS,),
        },
        opening_hands={
            "alice": (PLAINS, PLAINS, PLAINS, ISLAND, TOUCH_OF_BRILLIANCE),
            "bob": (PLAINS,),
        },
        rng_seed=45,
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
    session = replace(session, state=current_state)

    for source_instance_id in session.state.players["alice"].battlefield:
        session = activate_mana_ability(
            session,
            ActivateManaAbilityAction(player_id="alice", source_instance_id=source_instance_id),
            repository,
        )
    return session


def _build_time_ebb_ready_session(repository: CardRepository):
    setup = SetupInput(
        game_id="priority-time-ebb",
        players=("alice", "bob"),
        starting_player="alice",
        libraries={
            "alice": (PLAINS, PLAINS, ISLAND, TIME_EBB),
            "bob": (MUCK_RATS, PLAINS),
        },
        opening_hands={
            "alice": (PLAINS, PLAINS, ISLAND, TIME_EBB),
            "bob": (MUCK_RATS,),
        },
        rng_seed=49,
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
    session = replace(session, state=current_state)

    for source_instance_id in session.state.players["alice"].battlefield:
        session = activate_mana_ability(
            session,
            ActivateManaAbilityAction(player_id="alice", source_instance_id=source_instance_id),
            repository,
        )
    return session


def _build_tidal_surge_ready_session(repository: CardRepository):
    setup = SetupInput(
        game_id="priority-tidal-surge",
        players=("alice", "bob"),
        starting_player="alice",
        libraries={
            "alice": (ISLAND, PLAINS, TIDAL_SURGE),
            "bob": (MUCK_RATS, BORDER_GUARD, STORM_CROW),
        },
        opening_hands={
            "alice": (ISLAND, PLAINS, TIDAL_SURGE),
            "bob": (MUCK_RATS, BORDER_GUARD, STORM_CROW),
        },
        rng_seed=69,
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
    for creature_id in ("bob:1", "bob:2", "bob:3"):
        current_state = move_object(
            current_state,
            instance_id=creature_id,
            from_zone="hand",
            to_zone="battlefield",
            player_id="bob",
        )
    session = replace(session, state=current_state)

    for source_instance_id in session.state.players["alice"].battlefield:
        session = activate_mana_ability(
            session,
            ActivateManaAbilityAction(player_id="alice", source_instance_id=source_instance_id),
            repository,
        )
    return session


def _build_volcanic_hammer_ready_session(repository: CardRepository):
    setup = SetupInput(
        game_id="priority-volcanic-hammer",
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
        rng_seed=54,
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
    session = replace(session, state=current_state)

    for source_instance_id in session.state.players["alice"].battlefield:
        session = activate_mana_ability(
            session,
            ActivateManaAbilityAction(player_id="alice", source_instance_id=source_instance_id),
            repository,
        )
    return session


def _build_lava_axe_ready_session(repository: CardRepository):
    setup = SetupInput(
        game_id="priority-lava-axe",
        players=("alice", "bob"),
        starting_player="alice",
        libraries={
            "alice": (MOUNTAIN, MOUNTAIN, MOUNTAIN, MOUNTAIN, MOUNTAIN, LAVA_AXE),
            "bob": (PLAINS,),
        },
        opening_hands={
            "alice": (MOUNTAIN, MOUNTAIN, MOUNTAIN, MOUNTAIN, MOUNTAIN, LAVA_AXE),
            "bob": (PLAINS,),
        },
        rng_seed=55,
    )
    session = start_first_turn(initialize_game(setup, repository))
    current_state = session.state

    for land_id in ("alice:1", "alice:2", "alice:3", "alice:4", "alice:5"):
        current_state = move_object(
            current_state,
            instance_id=land_id,
            from_zone="hand",
            to_zone="battlefield",
            player_id="alice",
        )
    session = replace(session, state=current_state)

    for source_instance_id in session.state.players["alice"].battlefield:
        session = activate_mana_ability(
            session,
            ActivateManaAbilityAction(player_id="alice", source_instance_id=source_instance_id),
            repository,
        )
    return session


def _build_mind_rot_ready_session(repository: CardRepository):
    setup = SetupInput(
        game_id="priority-mind-rot",
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
        rng_seed=56,
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
    session = replace(session, state=current_state)

    for source_instance_id in session.state.players["alice"].battlefield:
        session = activate_mana_ability(
            session,
            ActivateManaAbilityAction(player_id="alice", source_instance_id=source_instance_id),
            repository,
        )
    return session


def _build_winters_grasp_ready_session(repository: CardRepository):
    setup = SetupInput(
        game_id="priority-winters-grasp",
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
        rng_seed=57,
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
    session = replace(session, state=current_state)

    for source_instance_id in session.state.players["alice"].battlefield:
        session = activate_mana_ability(
            session,
            ActivateManaAbilityAction(player_id="alice", source_instance_id=source_instance_id),
            repository,
        )
    return session


def _build_symbol_of_unsummoning_ready_session(repository: CardRepository):
    setup = SetupInput(
        game_id="priority-symbol-of-unsummoning",
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
    current_state = move_object(
        current_state,
        instance_id="bob:1",
        from_zone="hand",
        to_zone="battlefield",
        player_id="bob",
    )
    session = replace(session, state=current_state)

    for source_instance_id in session.state.players["alice"].battlefield:
        session = activate_mana_ability(
            session,
            ActivateManaAbilityAction(player_id="alice", source_instance_id=source_instance_id),
            repository,
        )
    return session


def _build_armageddon_ready_session(repository: CardRepository):
    setup = SetupInput(
        game_id="priority-armageddon",
        players=("alice", "bob"),
        starting_player="alice",
        libraries={
            "alice": (PLAINS, PLAINS, PLAINS, PLAINS, ARMAGEDDON),
            "bob": (PLAINS,),
        },
        opening_hands={
            "alice": (PLAINS, PLAINS, PLAINS, PLAINS, ARMAGEDDON),
            "bob": (PLAINS,),
        },
        rng_seed=59,
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
    session = replace(session, state=current_state)

    for source_instance_id in session.state.players["alice"].battlefield:
        session = activate_mana_ability(
            session,
            ActivateManaAbilityAction(player_id="alice", source_instance_id=source_instance_id),
            repository,
        )
    return session


def _build_rain_of_salt_ready_session(repository: CardRepository):
    setup = SetupInput(
        game_id="priority-rain-of-salt",
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
        rng_seed=60,
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
    session = replace(session, state=current_state)

    for source_instance_id in session.state.players["alice"].battlefield:
        session = activate_mana_ability(
            session,
            ActivateManaAbilityAction(player_id="alice", source_instance_id=source_instance_id),
            repository,
        )
    return session


def _build_wrath_of_god_ready_session(repository: CardRepository):
    setup = SetupInput(
        game_id="priority-wrath-of-god",
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
    session = replace(session, state=current_state)

    for source_instance_id in session.state.players["alice"].battlefield:
        session = activate_mana_ability(
            session,
            ActivateManaAbilityAction(player_id="alice", source_instance_id=source_instance_id),
            repository,
        )
    return session


def _build_sacred_nectar_ready_session(repository: CardRepository):
    setup = SetupInput(
        game_id="priority-sacred-nectar",
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
        rng_seed=64,
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
    session = replace(session, state=current_state)

    for source_instance_id in session.state.players["alice"].battlefield:
        session = activate_mana_ability(
            session,
            ActivateManaAbilityAction(player_id="alice", source_instance_id=source_instance_id),
            repository,
        )
    return session


def _build_reach_block_ready_session(repository: CardRepository):
    setup = SetupInput(
        game_id="priority-reach-block",
        players=("alice", "bob"),
        starting_player="alice",
        libraries={
            "alice": (PLAINS, PLAINS, ARMORED_PEGASUS),
            "bob": (PLAINS, PLAINS, ISLAND, KEEN_EYED_ARCHERS),
        },
        opening_hands={
            "alice": (PLAINS, PLAINS, ARMORED_PEGASUS),
            "bob": (PLAINS, PLAINS, ISLAND, KEEN_EYED_ARCHERS),
        },
        rng_seed=66,
    )
    session = start_first_turn(initialize_game(setup, repository))
    session = _cast_creature_from_normal_turns(session, repository, "alice", "alice:3")
    session = _advance_to_player_main_phase(_advance_to_next_turn(session, repository), repository, "bob")
    session = _cast_creature_from_normal_turns(session, repository, "bob", "bob:4")
    return _advance_to_player_main_phase(_advance_to_next_turn(session, repository), repository, "alice")


def _build_swampwalk_block_locked_session(repository: CardRepository):
    setup = SetupInput(
        game_id="priority-anaconda-swampwalk-locked",
        players=("alice", "bob"),
        starting_player="alice",
        libraries={
            "alice": (FOREST, PLAINS, PLAINS, PLAINS, ANACONDA),
            "bob": (SWAMP, BORDER_GUARD),
        },
        opening_hands={
            "alice": (FOREST, PLAINS, PLAINS, PLAINS, ANACONDA),
            "bob": (SWAMP, BORDER_GUARD),
        },
        rng_seed=69,
    )
    session = start_first_turn(initialize_game(setup, repository))
    session = _cast_creature_from_normal_turns(session, repository, "alice", "alice:5")
    session = _advance_to_player_main_phase(_advance_to_next_turn(session, repository), repository, "bob")
    session = play_land(session, PlayLandAction(player_id="bob", card_instance_id="bob:1"), repository)
    session = _advance_to_next_turn(session, repository)
    current_state = move_object(
        session.state,
        instance_id="bob:2",
        from_zone="hand",
        to_zone="battlefield",
        player_id="bob",
    )
    session = replace(session, state=current_state)
    return _advance_to_player_main_phase(_advance_to_next_turn(session, repository), repository, "alice")


def _build_swampwalk_blockable_session(repository: CardRepository):
    setup = SetupInput(
        game_id="priority-anaconda-swampwalk-open",
        players=("alice", "bob"),
        starting_player="alice",
        libraries={
            "alice": (FOREST, PLAINS, PLAINS, PLAINS, ANACONDA),
            "bob": (PLAINS, BORDER_GUARD),
        },
        opening_hands={
            "alice": (FOREST, PLAINS, PLAINS, PLAINS, ANACONDA),
            "bob": (PLAINS, BORDER_GUARD),
        },
        rng_seed=70,
    )
    session = start_first_turn(initialize_game(setup, repository))
    session = _cast_creature_from_normal_turns(session, repository, "alice", "alice:5")
    session = _advance_to_player_main_phase(_advance_to_next_turn(session, repository), repository, "bob")
    session = play_land(session, PlayLandAction(player_id="bob", card_instance_id="bob:1"), repository)
    session = _advance_to_next_turn(session, repository)
    current_state = move_object(
        session.state,
        instance_id="bob:2",
        from_zone="hand",
        to_zone="battlefield",
        player_id="bob",
    )
    session = replace(session, state=current_state)
    return _advance_to_player_main_phase(_advance_to_next_turn(session, repository), repository, "alice")


def _build_rain_of_daggers_ready_session(repository: CardRepository):
    setup = SetupInput(
        game_id="priority-rain-of-daggers",
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
        rng_seed=60,
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
    session = replace(session, state=current_state)

    for source_instance_id in session.state.players["alice"].battlefield:
        session = activate_mana_ability(
            session,
            ActivateManaAbilityAction(player_id="alice", source_instance_id=source_instance_id),
            repository,
        )
    return session


def _build_flying_block_ready_session(repository: CardRepository):
    setup = SetupInput(
        game_id="priority-flying-blockers",
        players=("alice", "bob"),
        starting_player="alice",
        libraries={
            "alice": (PLAINS, PLAINS, ARMORED_PEGASUS),
            "bob": (SWAMP, MUCK_RATS),
        },
        opening_hands={
            "alice": (PLAINS, PLAINS, ARMORED_PEGASUS),
            "bob": (SWAMP, MUCK_RATS),
        },
        rng_seed=51,
    )
    session = start_first_turn(initialize_game(setup, repository))
    session = _cast_creature_from_normal_turns(session, repository, "alice", "alice:3")
    session = _advance_to_player_main_phase(_advance_to_next_turn(session, repository), repository, "bob")
    session = _cast_creature_from_normal_turns(session, repository, "bob", "bob:2")
    return _advance_to_player_main_phase(_advance_to_next_turn(session, repository), repository, "alice")


def _build_defender_attack_ready_session(repository: CardRepository):
    setup = SetupInput(
        game_id="priority-defender-attackers",
        players=("alice", "bob"),
        starting_player="alice",
        libraries={
            "alice": (MOUNTAIN, MOUNTAIN, PLAINS, WALL_OF_GRANITE),
            "bob": (PLAINS,),
        },
        opening_hands={
            "alice": (MOUNTAIN, MOUNTAIN, PLAINS, WALL_OF_GRANITE),
            "bob": (PLAINS,),
        },
        rng_seed=53,
    )
    session = start_first_turn(initialize_game(setup, repository))
    session = _cast_creature_from_normal_turns(session, repository, "alice", "alice:4")
    return _advance_to_player_main_phase(_advance_to_next_turn(session, repository), repository, "alice")


def _cast_creature_from_normal_turns(session, repository: CardRepository, player_id: str, creature_id: str):
    current_session = _advance_to_player_main_phase(session, repository, player_id)
    land_ids = [instance_id for instance_id in current_session.state.players[player_id].hand if instance_id != creature_id]
    chosen_land_ids = _select_land_ids_for_spell(current_session, repository, land_ids, creature_id)

    for index, land_id in enumerate(chosen_land_ids, start=1):
        current_session = play_land(
            current_session,
            PlayLandAction(player_id=player_id, card_instance_id=land_id),
            repository,
        )
        if index != len(chosen_land_ids):
            current_session = _advance_to_player_main_phase(
                _advance_to_next_turn(current_session, repository),
                repository,
                player_id,
            )

    for source_instance_id in current_session.state.players[player_id].battlefield:
        if len(repository.get(current_session.state.objects[source_instance_id].oracle_id).produced_mana) != 1:
            continue
        current_session = activate_mana_ability(
            current_session,
            ActivateManaAbilityAction(player_id=player_id, source_instance_id=source_instance_id),
            repository,
        )

    return cast_creature_spell(
        current_session,
        CastCreatureSpellAction(player_id=player_id, card_instance_id=creature_id),
        repository,
    )


def _advance_to_next_turn(session, repository: CardRepository):
    active_player = session.state.turn.active_player
    defending_player = "bob" if active_player == "alice" else "alice"
    session = pass_priority(session, PassPriorityAction(player_id=active_player), repository)
    session = declare_attackers(
        session,
        DeclareAttackersAction(player_id=active_player, attacker_ids=()),
        repository,
    )
    session = declare_blockers(
        session,
        DeclareBlockersAction(player_id=defending_player, blockers={}),
        repository,
    )
    session = resolve_combat_damage(session, repository)
    session = advance_to_cleanup(session)
    return start_next_turn(session)


def _advance_to_player_main_phase(session, repository: CardRepository, player_id: str):
    current_session = session
    while current_session.state.turn.active_player != player_id:
        current_session = _advance_to_next_turn(current_session, repository)
    return current_session


def _select_land_ids_for_spell(session, repository: CardRepository, land_ids: list[str], creature_id: str) -> list[str]:
    mana_cost = repository.get(session.state.objects[creature_id].oracle_id).mana_cost
    requirements = _mana_requirements(mana_cost)
    chosen_ids: list[str] = []
    remaining_ids = list(land_ids)

    for symbol in ("W", "U", "B", "R", "G"):
        for _ in range(requirements[symbol]):
            match_id = next(
                instance_id
                for instance_id in remaining_ids
                if repository.get(session.state.objects[instance_id].oracle_id).produced_mana == (symbol,)
            )
            chosen_ids.append(match_id)
            remaining_ids.remove(match_id)

    chosen_ids.extend(remaining_ids[: requirements["generic"]])
    return chosen_ids


def _mana_requirements(mana_cost: str) -> dict[str, int]:
    requirements = {"W": 0, "U": 0, "B": 0, "R": 0, "G": 0, "generic": 0}
    for symbol in mana_cost.replace("{", " ").replace("}", " ").split():
        if symbol in requirements:
            requirements[symbol] += 1
        elif symbol.isdigit():
            requirements["generic"] += int(symbol)
    return requirements


if __name__ == "__main__":
    unittest.main()

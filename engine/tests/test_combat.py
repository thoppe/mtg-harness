from __future__ import annotations

from dataclasses import replace
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mtg_engine.actions.models import (
    ActivateManaAbilityAction,
    CastCreatureSpellAction,
    DeclareAttackersAction,
    DeclareBlockersAction,
    PassPriorityAction,
    PlayLandAction,
)
from mtg_engine.cards.repository import CardRepository
from mtg_engine.flow.setup import SetupInput, initialize_game
from mtg_engine.flow.turns import (
    activate_mana_ability,
    advance_to_cleanup,
    advance_to_begin_combat,
    cast_creature_spell,
    declare_attackers,
    declare_blockers,
    pass_priority,
    play_land,
    resolve_combat_damage,
    start_first_turn,
    start_next_turn,
)
from mtg_engine.state.zones import move_object
from mtg_engine.state.models import GameOutcome


INFORMATION_DIR = Path(__file__).resolve().parents[2] / "information"
SWAMP = "56719f6a-1a6c-4c0a-8d21-18f7d7350b68"
FOREST = "b34bb2dc-c1af-4d77-b0b3-a0fb342a5fc6"
PLAINS = "bc71ebf6-2056-41f7-be35-b2e5c34afa99"
ISLAND = "b2c6aa39-2d2a-459c-a555-fb48ba993373"
MOUNTAIN = "a3fb7228-e76b-4e96-a40e-20b5fed75685"
BORDER_GUARD = "1ef5003c-f540-4cdc-913f-7d5280ad9f62"
FOOT_SOLDIERS = "a768ba13-4d1c-4dce-a4a6-86a39c069c3f"
MUCK_RATS = "bca13a12-6723-4a5e-8f1b-21646a8b3e7e"
ARMORED_PEGASUS = "f097a059-5505-4c3c-b879-7853ab6972ed"
WIND_DRAKE = "d6ffdaf0-ac08-4de9-bbce-2eab2f86bcca"
KEEN_EYED_ARCHERS = "0ace32d6-7261-447c-9ee2-e03febaab91b"
ANACONDA = "3eff03f1-2c5f-4c59-b465-a8c4cd05e1ba"
WALL_OF_GRANITE = "8445094f-008b-491a-977c-e8582d5ab72c"


class CombatTests(unittest.TestCase):
    def test_life_zero_state_based_action_ends_game(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _state_with_creatures_ready_to_fight(repository, include_blocker=False)
        low_life_state = replace(
            session.state,
            outcome=GameOutcome(),
            players={
                **session.state.players,
                "bob": replace(session.state.players["bob"], life_total=1),
            },
        )
        session = replace(session, state=low_life_state)
        session = advance_to_begin_combat(session)
        session = declare_attackers(
            session,
            DeclareAttackersAction(player_id="alice", attacker_ids=("alice:4",)),
            repository,
        )
        session = _pass_attackers_window(session, repository)
        session = declare_blockers(
            session,
            DeclareBlockersAction(player_id="bob", blockers={}),
            repository,
        )
        result = resolve_combat_damage(session, repository)

        self.assertEqual(result.state.outcome.status, "completed")
        self.assertEqual(result.state.outcome.winner_id, "alice")
        self.assertEqual(result.state.outcome.loser_ids, ("bob",))
        self.assertEqual(result.state.outcome.reason, "life_total_zero_or_less")
        self.assertIn("game_ended", [event.event_type for event in result.event_log])

    def test_unblocked_border_guard_deals_life_damage(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _state_with_creatures_ready_to_fight(repository, include_blocker=False)

        session = advance_to_begin_combat(session)
        session = declare_attackers(
            session,
            DeclareAttackersAction(player_id="alice", attacker_ids=("alice:4",)),
            repository,
        )
        session = _pass_attackers_window(session, repository)
        session = declare_blockers(
            session,
            DeclareBlockersAction(player_id="bob", blockers={}),
            repository,
        )
        result = resolve_combat_damage(session, repository)

        self.assertEqual(result.state.players["bob"].life_total, 19)
        self.assertEqual(result.state.turn.step, "end_combat_step")
        self.assertEqual(result.event_log[-4].event_type, "combat_damage_applied")
        self.assertEqual(result.event_log[-3].event_type, "life_total_changed")
        self.assertEqual(result.event_log[-2].event_type, "state_based_actions_checked")

    def test_blocked_combat_records_assignment_and_keeps_creatures_alive(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _state_with_creatures_ready_to_fight(repository, include_blocker=True)

        session = advance_to_begin_combat(session)
        session = declare_attackers(
            session,
            DeclareAttackersAction(player_id="alice", attacker_ids=("alice:4",)),
            repository,
        )
        session = _pass_attackers_window(session, repository)
        session = declare_blockers(
            session,
            DeclareBlockersAction(player_id="bob", blockers={"alice:4": ("bob:4",)}),
            repository,
        )
        result = resolve_combat_damage(session, repository)

        self.assertEqual(result.state.objects["alice:4"].zone, "battlefield")
        self.assertEqual(result.state.objects["bob:4"].zone, "battlefield")
        self.assertEqual(
            [event.event_type for event in result.event_log[-6:]],
            [
                "blockers_declared",
                "step_changed",
                "combat_damage_assigned",
                "combat_damage_applied",
                "state_based_actions_checked",
                "step_changed",
            ],
        )

    def test_multiple_blockers_on_one_attacker_are_supported(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _state_with_multiple_blockers_ready(repository)

        session = advance_to_begin_combat(session)
        session = declare_attackers(
            session,
            DeclareAttackersAction(player_id="alice", attacker_ids=("alice:4",)),
            repository,
        )
        session = _pass_attackers_window(session, repository)
        session = declare_blockers(
            session,
            DeclareBlockersAction(player_id="bob", blockers={"alice:4": ("bob:4", "bob:6")}),
            repository,
        )
        result = resolve_combat_damage(session, repository)

        self.assertEqual(result.state.objects["alice:4"].damage_marked, 2)
        self.assertEqual(result.state.objects["bob:4"].damage_marked, 1)
        self.assertEqual(result.state.objects["bob:6"].damage_marked, 0)
        self.assertEqual(result.state.turn.step, "end_combat_step")
        combat_assignment = next(
            event for event in result.event_log if event.event_type == "combat_damage_assigned"
        )
        self.assertEqual(
            combat_assignment.payload["assignments"],
            [
                {"blocker_id": "bob:4", "attacker_damage": 1, "blocker_damage": 1},
                {"blocker_id": "bob:6", "attacker_damage": 0, "blocker_damage": 1},
            ],
        )

    def test_multiple_blockers_receive_lethal_damage_in_declared_order(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _state_with_anaconda_blockable(repository)
        state_with_second_blocker = move_object(
            session.state,
            instance_id="bob:3",
            from_zone="hand",
            to_zone="battlefield",
            player_id="bob",
        )
        muck_rat_blockers = {
            **state_with_second_blocker.objects,
            "bob:2": replace(state_with_second_blocker.objects["bob:2"], oracle_id=MUCK_RATS),
            "bob:3": replace(state_with_second_blocker.objects["bob:3"], oracle_id=MUCK_RATS),
        }
        session = replace(session, state=replace(state_with_second_blocker, objects=muck_rat_blockers))
        session = advance_to_begin_combat(session)
        session = declare_attackers(
            session,
            DeclareAttackersAction(player_id="alice", attacker_ids=("alice:5",)),
            repository,
        )
        session = _pass_attackers_window(session, repository)
        session = declare_blockers(
            session,
            DeclareBlockersAction(player_id="bob", blockers={"alice:5": ("bob:2", "bob:3")}),
            repository,
        )
        result = resolve_combat_damage(session, repository)

        combat_assignment = next(
            event for event in result.event_log if event.event_type == "combat_damage_assigned"
        )
        self.assertEqual(
            combat_assignment.payload["assignments"],
            [
                {"blocker_id": "bob:2", "attacker_damage": 1, "blocker_damage": 1},
                {"blocker_id": "bob:3", "attacker_damage": 1, "blocker_damage": 1},
            ],
        )

    def test_state_based_actions_destroy_muck_rats_after_lethal_combat_damage(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _state_with_muck_rats_blocker_ready(repository)

        session = advance_to_begin_combat(session)
        session = declare_attackers(
            session,
            DeclareAttackersAction(player_id="alice", attacker_ids=("alice:4",)),
            repository,
        )
        session = _pass_attackers_window(session, repository)
        session = declare_blockers(
            session,
            DeclareBlockersAction(player_id="bob", blockers={"alice:4": ("bob:2",)}),
            repository,
        )
        result = resolve_combat_damage(session, repository)

        self.assertEqual(result.state.objects["bob:2"].zone, "graveyard")
        self.assertIn("bob:2", result.state.players["bob"].graveyard)
        self.assertEqual(result.event_log[-4].event_type, "state_based_actions_checked")
        self.assertEqual(result.event_log[-3].event_type, "permanent_destroyed")
        self.assertEqual(result.event_log[-2].event_type, "object_moved_between_zones")

    def test_armored_pegasus_cannot_be_blocked_by_nonflying_creature(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _state_with_armored_pegasus_ready(repository)

        session = advance_to_begin_combat(session)
        session = declare_attackers(
            session,
            DeclareAttackersAction(player_id="alice", attacker_ids=("alice:3",)),
            repository,
        )
        session = _pass_attackers_window(session, repository)

        with self.assertRaises(ValueError):
            declare_blockers(
                session,
                DeclareBlockersAction(player_id="bob", blockers={"alice:3": ("bob:2",)}),
                repository,
            )

        session = declare_blockers(
            session,
            DeclareBlockersAction(player_id="bob", blockers={}),
            repository,
        )
        result = resolve_combat_damage(session, repository)

        self.assertEqual(result.state.players["bob"].life_total, 19)
        self.assertEqual(result.state.objects["alice:3"].zone, "battlefield")
        self.assertEqual(result.state.objects["bob:2"].zone, "battlefield")

    def test_wind_drake_cannot_be_blocked_by_nonflying_creature(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _state_with_wind_drake_ready(repository)

        session = advance_to_begin_combat(session)
        session = declare_attackers(
            session,
            DeclareAttackersAction(player_id="alice", attacker_ids=("alice:4",)),
            repository,
        )
        session = _pass_attackers_window(session, repository)

        with self.assertRaises(ValueError):
            declare_blockers(
                session,
                DeclareBlockersAction(player_id="bob", blockers={"alice:4": ("bob:2",)}),
                repository,
            )

        session = declare_blockers(
            session,
            DeclareBlockersAction(player_id="bob", blockers={}),
            repository,
        )
        result = resolve_combat_damage(session, repository)

        self.assertEqual(result.state.players["bob"].life_total, 18)
        self.assertEqual(result.state.objects["alice:4"].zone, "battlefield")
        self.assertEqual(result.state.objects["bob:2"].zone, "battlefield")

    def test_keen_eyed_archers_can_block_armored_pegasus(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _state_with_reach_block_ready(repository)

        session = advance_to_begin_combat(session)
        session = declare_attackers(
            session,
            DeclareAttackersAction(player_id="alice", attacker_ids=("alice:3",)),
            repository,
        )
        session = _pass_attackers_window(session, repository)
        session = declare_blockers(
            session,
            DeclareBlockersAction(player_id="bob", blockers={"alice:3": ("bob:4",)}),
            repository,
        )
        result = resolve_combat_damage(session, repository)

        self.assertEqual(result.state.players["bob"].life_total, 20)
        self.assertEqual(result.state.objects["alice:3"].zone, "graveyard")
        self.assertEqual(result.state.objects["bob:4"].zone, "battlefield")
        self.assertEqual(result.state.objects["bob:4"].damage_marked, 1)

    def test_anaconda_cannot_be_blocked_when_defending_player_controls_swamp(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _state_with_anaconda_swampwalk_locked(repository)

        session = advance_to_begin_combat(session)
        session = declare_attackers(
            session,
            DeclareAttackersAction(player_id="alice", attacker_ids=("alice:5",)),
            repository,
        )
        session = _pass_attackers_window(session, repository)
        session = declare_blockers(
            session,
            DeclareBlockersAction(player_id="bob", blockers={}),
            repository,
        )
        result = resolve_combat_damage(session, repository)

        self.assertEqual(result.state.players["bob"].life_total, 17)
        self.assertEqual(result.state.objects["alice:5"].zone, "battlefield")
        self.assertEqual(result.state.objects["bob:2"].zone, "battlefield")

    def test_anaconda_can_be_blocked_when_defending_player_lacks_swamp(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _state_with_anaconda_blockable(repository)

        session = advance_to_begin_combat(session)
        session = declare_attackers(
            session,
            DeclareAttackersAction(player_id="alice", attacker_ids=("alice:5",)),
            repository,
        )
        session = _pass_attackers_window(session, repository)
        session = declare_blockers(
            session,
            DeclareBlockersAction(player_id="bob", blockers={"alice:5": ("bob:2",)}),
            repository,
        )
        result = resolve_combat_damage(session, repository)

        self.assertEqual(result.state.players["bob"].life_total, 20)
        self.assertEqual(result.state.objects["alice:5"].zone, "battlefield")
        self.assertEqual(result.state.objects["bob:2"].zone, "battlefield")
        self.assertEqual(result.state.objects["bob:2"].damage_marked, 3)

    def test_wall_of_granite_cannot_attack(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _state_with_wall_of_granite_ready(repository)

        session = advance_to_begin_combat(session)

        with self.assertRaises(ValueError):
            declare_attackers(
                session,
                DeclareAttackersAction(player_id="alice", attacker_ids=("alice:4",)),
                repository,
            )

    def test_wall_of_granite_can_block_and_survive_combat(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _state_with_wall_of_granite_block_ready(repository)

        session = advance_to_begin_combat(session)
        session = declare_attackers(
            session,
            DeclareAttackersAction(player_id="alice", attacker_ids=("alice:4",)),
            repository,
        )
        session = _pass_attackers_window(session, repository)
        session = declare_blockers(
            session,
            DeclareBlockersAction(player_id="bob", blockers={"alice:4": ("bob:4",)}),
            repository,
        )
        result = resolve_combat_damage(session, repository)

        self.assertEqual(result.state.players["bob"].life_total, 20)
        self.assertEqual(result.state.objects["alice:4"].zone, "battlefield")
        self.assertEqual(result.state.objects["bob:4"].zone, "battlefield")
        self.assertEqual(result.state.objects["bob:4"].damage_marked, 1)
        self.assertEqual(
            [event.event_type for event in result.event_log[-4:]],
            [
                "combat_damage_assigned",
                "combat_damage_applied",
                "state_based_actions_checked",
                "step_changed",
            ],
        )


def _state_with_creatures_ready_to_fight(repository: CardRepository, *, include_blocker: bool):
    setup = SetupInput(
        game_id="combat-001",
        players=("alice", "bob"),
        starting_player="alice",
        libraries={
            "alice": (PLAINS, PLAINS, PLAINS, BORDER_GUARD),
            "bob": (PLAINS, PLAINS, PLAINS, BORDER_GUARD) if include_blocker else (PLAINS,),
        },
        opening_hands={
            "alice": (PLAINS, PLAINS, PLAINS, BORDER_GUARD),
            "bob": (PLAINS, PLAINS, PLAINS, BORDER_GUARD) if include_blocker else (PLAINS,),
        },
        rng_seed=23,
    )
    session = start_first_turn(initialize_game(setup, repository))
    session = _develop_creature_through_normal_turns(session, repository, "alice", "alice:4")
    if include_blocker:
        session = _advance_to_player_main_phase(_advance_to_next_turn(session, repository), repository, "bob")
        session = _develop_creature_through_normal_turns(session, repository, "bob", "bob:4")
    return _advance_to_player_main_phase(_advance_to_next_turn(session, repository), repository, "alice")


def _state_with_multiple_blockers_ready(repository: CardRepository):
    setup = SetupInput(
        game_id="combat-multi-block",
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
        rng_seed=41,
    )
    session = start_first_turn(initialize_game(setup, repository))
    session = _develop_creature_through_normal_turns(session, repository, "alice", "alice:4")
    session = _advance_to_player_main_phase(_advance_to_next_turn(session, repository), repository, "bob")
    session = _develop_creature_through_normal_turns(session, repository, "bob", "bob:4")
    session = _advance_to_player_main_phase(_advance_to_next_turn(session, repository), repository, "bob")
    session = _develop_creature_through_normal_turns(session, repository, "bob", "bob:6")
    return _advance_to_player_main_phase(_advance_to_next_turn(session, repository), repository, "alice")


def _state_with_muck_rats_blocker_ready(repository: CardRepository):
    setup = SetupInput(
        game_id="combat-lethal-muck-rats",
        players=("alice", "bob"),
        starting_player="alice",
        libraries={
            "alice": (PLAINS, PLAINS, PLAINS, BORDER_GUARD),
            "bob": (SWAMP, MUCK_RATS),
        },
        opening_hands={
            "alice": (PLAINS, PLAINS, PLAINS, BORDER_GUARD),
            "bob": (SWAMP, MUCK_RATS),
        },
        rng_seed=43,
    )
    session = start_first_turn(initialize_game(setup, repository))
    session = _develop_creature_through_normal_turns(session, repository, "alice", "alice:4")
    session = _advance_to_player_main_phase(_advance_to_next_turn(session, repository), repository, "bob")
    session = _develop_creature_through_normal_turns(session, repository, "bob", "bob:2")
    return _advance_to_player_main_phase(_advance_to_next_turn(session, repository), repository, "alice")


def _state_with_armored_pegasus_ready(repository: CardRepository):
    setup = SetupInput(
        game_id="combat-armored-pegasus",
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
        rng_seed=47,
    )
    session = start_first_turn(initialize_game(setup, repository))
    session = _develop_creature_through_normal_turns(session, repository, "alice", "alice:3")
    session = _advance_to_player_main_phase(_advance_to_next_turn(session, repository), repository, "bob")
    session = _develop_creature_through_normal_turns(session, repository, "bob", "bob:2")
    return _advance_to_player_main_phase(_advance_to_next_turn(session, repository), repository, "alice")


def _state_with_wind_drake_ready(repository: CardRepository):
    setup = SetupInput(
        game_id="combat-wind-drake",
        players=("alice", "bob"),
        starting_player="alice",
        libraries={
            "alice": (ISLAND, ISLAND, PLAINS, WIND_DRAKE),
            "bob": (SWAMP, MUCK_RATS),
        },
        opening_hands={
            "alice": (ISLAND, ISLAND, PLAINS, WIND_DRAKE),
            "bob": (SWAMP, MUCK_RATS),
        },
        rng_seed=48,
    )
    session = start_first_turn(initialize_game(setup, repository))
    session = _develop_creature_through_normal_turns(session, repository, "alice", "alice:4")
    session = _advance_to_player_main_phase(_advance_to_next_turn(session, repository), repository, "bob")
    session = _develop_creature_through_normal_turns(session, repository, "bob", "bob:2")
    return _advance_to_player_main_phase(_advance_to_next_turn(session, repository), repository, "alice")


def _state_with_reach_block_ready(repository: CardRepository):
    setup = SetupInput(
        game_id="combat-reach-block",
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
        rng_seed=52,
    )
    session = start_first_turn(initialize_game(setup, repository))
    session = _develop_creature_through_normal_turns(session, repository, "alice", "alice:3")
    session = _advance_to_player_main_phase(_advance_to_next_turn(session, repository), repository, "bob")
    session = _develop_creature_through_normal_turns(session, repository, "bob", "bob:4")
    return _advance_to_player_main_phase(_advance_to_next_turn(session, repository), repository, "alice")


def _state_with_anaconda_swampwalk_locked(repository: CardRepository):
    setup = SetupInput(
        game_id="combat-anaconda-swampwalk-locked",
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
        rng_seed=53,
    )
    session = start_first_turn(initialize_game(setup, repository))
    session = _develop_creature_through_normal_turns(session, repository, "alice", "alice:5")
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


def _state_with_anaconda_blockable(repository: CardRepository):
    setup = SetupInput(
        game_id="combat-anaconda-swampwalk-open",
        players=("alice", "bob"),
        starting_player="alice",
        libraries={
            "alice": (FOREST, PLAINS, PLAINS, PLAINS, ANACONDA),
            "bob": (PLAINS, BORDER_GUARD, BORDER_GUARD),
        },
        opening_hands={
            "alice": (FOREST, PLAINS, PLAINS, PLAINS, ANACONDA),
            "bob": (PLAINS, BORDER_GUARD, BORDER_GUARD),
        },
        rng_seed=54,
    )
    session = start_first_turn(initialize_game(setup, repository))
    session = _develop_creature_through_normal_turns(session, repository, "alice", "alice:5")
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


def _state_with_wall_of_granite_ready(repository: CardRepository):
    setup = SetupInput(
        game_id="combat-wall-of-granite-attack",
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
        rng_seed=49,
    )
    session = start_first_turn(initialize_game(setup, repository))
    session = _develop_creature_through_normal_turns(session, repository, "alice", "alice:4")
    return _advance_to_player_main_phase(_advance_to_next_turn(session, repository), repository, "alice")


def _state_with_wall_of_granite_block_ready(repository: CardRepository):
    setup = SetupInput(
        game_id="combat-wall-of-granite-block",
        players=("alice", "bob"),
        starting_player="alice",
        libraries={
            "alice": (PLAINS, PLAINS, PLAINS, BORDER_GUARD),
            "bob": (MOUNTAIN, MOUNTAIN, PLAINS, WALL_OF_GRANITE),
        },
        opening_hands={
            "alice": (PLAINS, PLAINS, PLAINS, BORDER_GUARD),
            "bob": (MOUNTAIN, MOUNTAIN, PLAINS, WALL_OF_GRANITE),
        },
        rng_seed=50,
    )
    session = start_first_turn(initialize_game(setup, repository))
    session = _develop_creature_through_normal_turns(session, repository, "alice", "alice:4")
    session = _advance_to_player_main_phase(_advance_to_next_turn(session, repository), repository, "bob")
    session = _develop_creature_through_normal_turns(session, repository, "bob", "bob:4")
    return _advance_to_player_main_phase(_advance_to_next_turn(session, repository), repository, "alice")


def _develop_creature_through_normal_turns(session, repository: CardRepository, player_id: str, creature_id: str):
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

    current_session = cast_creature_spell(
        current_session,
        CastCreatureSpellAction(player_id=player_id, card_instance_id=creature_id),
        repository,
    )
    current_session = pass_priority(current_session, PassPriorityAction(player_id=player_id), repository)
    opponent_id = "bob" if player_id == "alice" else "alice"
    return pass_priority(current_session, PassPriorityAction(player_id=opponent_id), repository)


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


def _advance_to_next_turn(session, repository: CardRepository):
    active_player = session.state.turn.active_player
    defending_player = "bob" if active_player == "alice" else "alice"
    session = pass_priority(session, PassPriorityAction(player_id=active_player), repository)
    session = declare_attackers(
        session,
        DeclareAttackersAction(player_id=active_player, attacker_ids=()),
        repository,
    )
    session = pass_priority(session, PassPriorityAction(player_id=active_player), repository)
    session = pass_priority(session, PassPriorityAction(player_id=defending_player), repository)
    session = declare_blockers(
        session,
        DeclareBlockersAction(player_id=defending_player, blockers={}),
        repository,
    )
    session = resolve_combat_damage(session, repository)
    session = advance_to_cleanup(session)
    return start_next_turn(session)


def _pass_attackers_window(session, repository: CardRepository):
    active = session.state.turn.active_player
    defender = "bob" if active == "alice" else "alice"
    session = pass_priority(session, PassPriorityAction(player_id=active), repository)
    return pass_priority(session, PassPriorityAction(player_id=defender), repository)


def _advance_to_player_main_phase(session, repository: CardRepository, player_id: str):
    current_session = session
    while current_session.state.turn.active_player != player_id:
        current_session = _advance_to_next_turn(current_session, repository)
    return current_session


if __name__ == "__main__":
    unittest.main()

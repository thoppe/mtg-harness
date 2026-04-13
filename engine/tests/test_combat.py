from __future__ import annotations

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


INFORMATION_DIR = Path(__file__).resolve().parents[2] / "information"
SWAMP = "56719f6a-1a6c-4c0a-8d21-18f7d7350b68"
PLAINS = "bc71ebf6-2056-41f7-be35-b2e5c34afa99"
ISLAND = "b2c6aa39-2d2a-459c-a555-fb48ba993373"
BORDER_GUARD = "1ef5003c-f540-4cdc-913f-7d5280ad9f62"
FOOT_SOLDIERS = "a768ba13-4d1c-4dce-a4a6-86a39c069c3f"
MUCK_RATS = "bca13a12-6723-4a5e-8f1b-21646a8b3e7e"
ARMORED_PEGASUS = "f097a059-5505-4c3c-b879-7853ab6972ed"
WIND_DRAKE = "d6ffdaf0-ac08-4de9-bbce-2eab2f86bcca"


class CombatTests(unittest.TestCase):
    def test_unblocked_border_guard_deals_life_damage(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _state_with_creatures_ready_to_fight(repository, include_blocker=False)

        session = advance_to_begin_combat(session)
        session = declare_attackers(
            session,
            DeclareAttackersAction(player_id="alice", attacker_ids=("alice:4",)),
            repository,
        )
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
        self.assertEqual(
            result.event_log[-3].payload["assignments"],
            [
                {"blocker_id": "bob:4", "attacker_damage": 1, "blocker_damage": 1},
                {"blocker_id": "bob:6", "attacker_damage": 0, "blocker_damage": 1},
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

    return cast_creature_spell(
        current_session,
        CastCreatureSpellAction(player_id=player_id, card_instance_id=creature_id),
        repository,
    )


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


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import unittest
from dataclasses import replace
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
PLAINS = "bc71ebf6-2056-41f7-be35-b2e5c34afa99"
BORDER_GUARD = "1ef5003c-f540-4cdc-913f-7d5280ad9f62"
FOOT_SOLDIERS = "a768ba13-4d1c-4dce-a4a6-86a39c069c3f"


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

    def test_state_based_actions_destroy_premarked_creature_after_combat_damage(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _state_with_creatures_ready_to_fight(repository, include_blocker=True)

        state = session.state
        updated_objects = dict(state.objects)
        updated_objects["bob:4"] = replace(updated_objects["bob:4"], damage_marked=3)
        session = session.__class__(state=replace(state, objects=updated_objects), event_log=session.event_log)

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

        self.assertEqual(result.state.objects["bob:4"].zone, "graveyard")
        self.assertIn("bob:4", result.state.players["bob"].graveyard)
        self.assertEqual(result.event_log[-4].event_type, "state_based_actions_checked")
        self.assertEqual(result.event_log[-3].event_type, "permanent_destroyed")
        self.assertEqual(result.event_log[-2].event_type, "object_moved_between_zones")


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


def _develop_creature_through_normal_turns(session, repository: CardRepository, player_id: str, creature_id: str):
    current_session = _advance_to_player_main_phase(session, repository, player_id)
    plains_ids = [instance_id for instance_id in current_session.state.players[player_id].hand if instance_id != creature_id]
    required_land_count = _required_white_mana(repository, current_session.state.objects[creature_id].oracle_id)

    for index, plains_id in enumerate(plains_ids[:required_land_count], start=1):
        current_session = play_land(
            current_session,
            PlayLandAction(player_id=player_id, card_instance_id=plains_id),
            repository,
        )
        if index != required_land_count:
            current_session = _advance_to_player_main_phase(
                _advance_to_next_turn(current_session, repository),
                repository,
                player_id,
            )

    for source_instance_id in current_session.state.players[player_id].battlefield:
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


def _required_white_mana(repository: CardRepository, oracle_id: str) -> int:
    mana_cost = repository.get(oracle_id).mana_cost
    return sum(int(symbol) if symbol.isdigit() else 1 for symbol in mana_cost.replace("{", " ").replace("}", " ").split())


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

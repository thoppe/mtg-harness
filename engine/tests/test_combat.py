from __future__ import annotations

import unittest
from dataclasses import replace
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mtg_engine.actions.models import CastCreatureSpellAction, DeclareAttackersAction, DeclareBlockersAction
from mtg_engine.cards.repository import CardRepository
from mtg_engine.flow.setup import SetupInput, initialize_game
from mtg_engine.flow.turns import (
    advance_to_begin_combat,
    cast_creature_spell,
    declare_attackers,
    declare_blockers,
    resolve_combat_damage,
    start_first_turn,
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
        self.assertEqual(result.event_log[-3].event_type, "combat_damage_applied")
        self.assertEqual(result.event_log[-2].event_type, "life_total_changed")

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
            DeclareBlockersAction(player_id="bob", blockers={"alice:4": ("bob:3",)}),
            repository,
        )
        result = resolve_combat_damage(session, repository)

        self.assertEqual(result.state.objects["alice:4"].zone, "battlefield")
        self.assertEqual(result.state.objects["bob:3"].zone, "battlefield")
        self.assertEqual(
            [event.event_type for event in result.event_log[-5:]],
            [
                "blockers_declared",
                "step_changed",
                "combat_damage_assigned",
                "combat_damage_applied",
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
            "bob": (PLAINS, PLAINS, BORDER_GUARD) if include_blocker else (PLAINS,),
        },
        opening_hands={
            "alice": (PLAINS, PLAINS, PLAINS, BORDER_GUARD),
            "bob": (PLAINS, PLAINS, BORDER_GUARD) if include_blocker else (PLAINS,),
        },
        rng_seed=23,
    )
    session = start_first_turn(initialize_game(setup, repository))
    session = _cast_creature_for_test(session, repository, "alice", "alice:4")
    if include_blocker:
        session = session.__class__(
            state=replace(
                session.state,
                turn=replace(
                    session.state.turn,
                    turn_number=session.state.turn.turn_number + 1,
                    active_player="bob",
                    priority_player="bob",
                    step="precombat_main_step",
                ),
            ),
            event_log=session.event_log,
        )
        session = _cast_creature_for_test(session, repository, "bob", "bob:3")
        session = session.__class__(
            state=replace(
                session.state,
                turn=replace(
                    session.state.turn,
                    turn_number=session.state.turn.turn_number + 1,
                    active_player="alice",
                    priority_player="alice",
                    step="precombat_main_step",
                ),
            ),
            event_log=session.event_log,
        )

    state = session.state
    updated_objects = dict(state.objects)
    updated_objects["alice:4"] = replace(
        updated_objects["alice:4"],
        entered_battlefield_turn=state.turn.turn_number - 1,
        tapped=False,
    )
    if include_blocker:
            updated_objects["bob:3"] = replace(
                updated_objects["bob:3"],
                entered_battlefield_turn=state.turn.turn_number - 1,
                tapped=False,
            )
    updated_players = dict(state.players)
    updated_players["alice"] = replace(updated_players["alice"], mana_pool=(), lands_played_this_turn=0)
    updated_players["bob"] = replace(updated_players["bob"], mana_pool=(), lands_played_this_turn=0)
    next_state = replace(state, objects=updated_objects, players=updated_players)
    return session.__class__(state=next_state, event_log=session.event_log)


def _cast_creature_for_test(session, repository: CardRepository, player_id: str, creature_id: str):
    state = session.state
    player = state.players[player_id]
    next_state = replace(
        state,
        players={
            **state.players,
            player_id: replace(player, mana_pool=("W", "W", "W")),
        },
    )
    session = session.__class__(state=next_state, event_log=session.event_log)
    return cast_creature_spell(
        session,
        CastCreatureSpellAction(player_id=player_id, card_instance_id=creature_id),
        repository,
    )


if __name__ == "__main__":
    unittest.main()

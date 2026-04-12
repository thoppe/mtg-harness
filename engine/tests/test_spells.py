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


class SpellTests(unittest.TestCase):
    def test_setup_allows_multiple_copies_from_declared_universe(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        setup = SetupInput(
            game_id="spell-setup",
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
            rng_seed=11,
        )

        bootstrap = initialize_game(setup, repository)
        self.assertEqual(len(bootstrap.state.players["alice"].hand), 4)

    def test_cast_border_guard_with_three_plains(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _build_castable_main_phase_session(repository)
        session = _advance_to_player_main_phase(session, repository, "alice")
        session = play_land(session, PlayLandAction(player_id="alice", card_instance_id="alice:1"), repository)
        session = _advance_to_player_main_phase(_advance_to_next_turn(session, repository), repository, "alice")
        session = play_land(session, PlayLandAction(player_id="alice", card_instance_id="alice:2"), repository)
        session = _advance_to_player_main_phase(_advance_to_next_turn(session, repository), repository, "alice")
        session = play_land(session, PlayLandAction(player_id="alice", card_instance_id="alice:3"), repository)
        session = activate_mana_ability(
            session,
            ActivateManaAbilityAction(player_id="alice", source_instance_id="alice:1"),
            repository,
        )
        session = activate_mana_ability(
            session,
            ActivateManaAbilityAction(player_id="alice", source_instance_id="alice:2"),
            repository,
        )
        session = activate_mana_ability(
            session,
            ActivateManaAbilityAction(player_id="alice", source_instance_id="alice:3"),
            repository,
        )

        result = cast_creature_spell(
            session,
            CastCreatureSpellAction(player_id="alice", card_instance_id="alice:4"),
            repository,
        )

        self.assertEqual(result.state.players["alice"].battlefield, ("alice:1", "alice:2", "alice:3", "alice:4"))
        self.assertEqual(result.state.players["alice"].hand, ())
        self.assertEqual(result.state.stack, ())
        self.assertEqual(result.state.players["alice"].mana_pool, ())
        self.assertEqual(result.state.objects["alice:4"].zone, "battlefield")
        self.assertEqual(
            [event.event_type for event in result.event_log[-4:]],
            ["spell_cast", "object_moved_between_zones", "spell_resolved", "object_moved_between_zones"],
        )


def _build_castable_main_phase_session(repository: CardRepository):
    setup = SetupInput(
        game_id="spell-cast",
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
        rng_seed=17,
    )
    return start_first_turn(initialize_game(setup, repository))


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

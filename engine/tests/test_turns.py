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
PLAINS = "bc71ebf6-2056-41f7-be35-b2e5c34afa99"
BORDER_GUARD = "1ef5003c-f540-4cdc-913f-7d5280ad9f62"


class TurnTests(unittest.TestCase):
    def test_start_first_turn_reaches_precombat_main_and_draws_card(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        setup = SetupInput(
            game_id="turn-001",
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
            rng_seed=5,
        )

        bootstrap = initialize_game(setup, repository)
        turn_state = start_first_turn(bootstrap)

        self.assertEqual(turn_state.state.turn.step, "precombat_main_step")
        self.assertEqual(turn_state.state.players["alice"].hand, ("alice:1", "alice:2"))
        self.assertEqual(turn_state.state.players["alice"].library, ())
        self.assertEqual(
            [event.event_type for event in turn_state.event_log],
            [
                "game_initialized",
                "opening_hand_assigned",
                "opening_hand_assigned",
                "turn_started",
                "step_changed",
                "step_changed",
                "step_changed",
                "step_changed",
                "object_moved_between_zones",
                "step_changed",
            ],
        )

    def test_play_land_moves_plains_to_battlefield(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _build_main_phase_session(repository)

        result = play_land(session, PlayLandAction(player_id="alice", card_instance_id="alice:1"), repository)

        self.assertEqual(result.state.players["alice"].hand, ("alice:2",))
        self.assertEqual(result.state.players["alice"].battlefield, ("alice:1",))
        self.assertEqual(result.state.objects["alice:1"].zone, "battlefield")
        self.assertEqual(result.state.players["alice"].lands_played_this_turn, 1)
        self.assertEqual([event.event_type for event in result.event_log[-2:]], ["land_played", "object_moved_between_zones"])

    def test_activate_plains_adds_white_mana(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _build_main_phase_session(repository)
        session = play_land(session, PlayLandAction(player_id="alice", card_instance_id="alice:1"), repository)

        result = activate_mana_ability(
            session,
            ActivateManaAbilityAction(player_id="alice", source_instance_id="alice:1"),
            repository,
        )

        self.assertEqual(result.state.players["alice"].mana_pool, ("W",))
        self.assertEqual(result.event_log[-1].event_type, "mana_added")
        self.assertEqual(result.event_log[-1].payload["mana"], ["W"])

    def test_cleanup_clears_damage_and_mana_and_ends_turn(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _build_end_combat_session_with_marked_damage(repository)

        result = advance_to_cleanup(session)

        self.assertEqual(result.state.turn.step, "cleanup_step")
        self.assertEqual(result.state.players["alice"].mana_pool, ())
        self.assertEqual(result.state.players["alice"].lands_played_this_turn, 0)
        self.assertEqual(result.state.objects["alice:4"].damage_marked, 0)
        self.assertEqual(result.state.objects["bob:4"].damage_marked, 0)
        self.assertEqual(result.event_log[-1].event_type, "turn_ended")

    def test_start_next_turn_hands_off_to_other_player(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _build_main_phase_session(repository)
        cleanup_session = advance_to_cleanup(_advance_to_end_combat_step(session, repository))

        result = start_next_turn(cleanup_session)

        self.assertEqual(result.state.turn.turn_number, 2)
        self.assertEqual(result.state.turn.active_player, "bob")
        self.assertEqual(result.state.turn.step, "precombat_main_step")
        self.assertEqual(result.event_log[-5].event_type, "turn_started")
        self.assertEqual(result.event_log[-1].event_type, "step_changed")


def _build_main_phase_session(repository: CardRepository):
    setup = SetupInput(
        game_id="turn-main",
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
        rng_seed=9,
    )
    bootstrap = initialize_game(setup, repository)
    return start_first_turn(bootstrap)


def _build_end_combat_session_with_marked_damage(repository: CardRepository):
    setup = SetupInput(
        game_id="turn-cleanup-damage",
        players=("alice", "bob"),
        starting_player="alice",
        libraries={
            "alice": (PLAINS, PLAINS, PLAINS, BORDER_GUARD),
            "bob": (PLAINS, PLAINS, PLAINS, BORDER_GUARD),
        },
        opening_hands={
            "alice": (PLAINS, PLAINS, PLAINS, BORDER_GUARD),
            "bob": (PLAINS, PLAINS, PLAINS, BORDER_GUARD),
        },
        rng_seed=29,
    )
    session = start_first_turn(initialize_game(setup, repository))
    session = _cast_creature_from_normal_turns(session, repository, "alice", "alice:4")
    session = _advance_to_player_main_phase(_advance_to_next_turn(session, repository), repository, "bob")
    session = _cast_creature_from_normal_turns(session, repository, "bob", "bob:4")
    session = _advance_to_player_main_phase(_advance_to_next_turn(session, repository), repository, "alice")
    session = activate_mana_ability(
        session,
        ActivateManaAbilityAction(player_id="alice", source_instance_id="alice:1"),
        repository,
    )
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
    return resolve_combat_damage(session, repository)


def _cast_creature_from_normal_turns(session, repository: CardRepository, player_id: str, creature_id: str):
    current_session = _advance_to_player_main_phase(session, repository, player_id)
    plains_ids = [instance_id for instance_id in current_session.state.players[player_id].hand if instance_id != creature_id]

    for index, plains_id in enumerate(plains_ids[:3], start=1):
        current_session = play_land(
            current_session,
            PlayLandAction(player_id=player_id, card_instance_id=plains_id),
            repository,
        )
        if index != 3:
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


def _advance_to_end_combat_step(session, repository: CardRepository):
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
    return resolve_combat_damage(session, repository)


def _advance_to_next_turn(session, repository: CardRepository):
    session = _advance_to_end_combat_step(session, repository)
    session = advance_to_cleanup(session)
    return start_next_turn(session)


def _advance_to_player_main_phase(session, repository: CardRepository, player_id: str):
    current_session = session
    while current_session.state.turn.active_player != player_id:
        current_session = _advance_to_next_turn(current_session, repository)
    return current_session


if __name__ == "__main__":
    unittest.main()

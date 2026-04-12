from __future__ import annotations

import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mtg_engine.actions.models import ActivateManaAbilityAction, PlayLandAction
from mtg_engine.cards.repository import CardRepository
from mtg_engine.flow.setup import SetupInput, initialize_game
from mtg_engine.flow.turns import activate_mana_ability, advance_to_cleanup, play_land, start_first_turn, start_next_turn


INFORMATION_DIR = Path(__file__).resolve().parents[2] / "information"


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
        session = _build_main_phase_session(repository)
        session = play_land(session, PlayLandAction(player_id="alice", card_instance_id="alice:1"), repository)
        session = activate_mana_ability(
            session,
            ActivateManaAbilityAction(player_id="alice", source_instance_id="alice:1"),
            repository,
        )
        damaged_state = session.state
        damaged_objects = dict(damaged_state.objects)
        damaged_objects["alice:1"] = damaged_objects["alice:1"].__class__(
            instance_id=damaged_objects["alice:1"].instance_id,
            oracle_id=damaged_objects["alice:1"].oracle_id,
            owner_id=damaged_objects["alice:1"].owner_id,
            controller_id=damaged_objects["alice:1"].controller_id,
            zone=damaged_objects["alice:1"].zone,
            tapped=damaged_objects["alice:1"].tapped,
            entered_battlefield_turn=damaged_objects["alice:1"].entered_battlefield_turn,
            damage_marked=2,
        )
        session = session.__class__(state=damaged_state.__class__(
            game_id=damaged_state.game_id,
            rng_seed=damaged_state.rng_seed,
            players=damaged_state.players,
            objects=damaged_objects,
            stack=damaged_state.stack,
            turn=damaged_state.turn.__class__(
                turn_number=damaged_state.turn.turn_number,
                active_player=damaged_state.turn.active_player,
                priority_player=damaged_state.turn.priority_player,
                step="end_combat_step",
            ),
            combat=damaged_state.combat,
        ), event_log=session.event_log)

        result = advance_to_cleanup(session)

        self.assertEqual(result.state.turn.step, "cleanup_step")
        self.assertEqual(result.state.players["alice"].mana_pool, ())
        self.assertEqual(result.state.players["alice"].lands_played_this_turn, 0)
        self.assertEqual(result.state.objects["alice:1"].damage_marked, 0)
        self.assertEqual(result.event_log[-1].event_type, "turn_ended")

    def test_start_next_turn_hands_off_to_other_player(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _build_main_phase_session(repository)
        session = play_land(session, PlayLandAction(player_id="alice", card_instance_id="alice:1"), repository)
        session = activate_mana_ability(
            session,
            ActivateManaAbilityAction(player_id="alice", source_instance_id="alice:1"),
            repository,
        )
        cleanup_session = session.__class__(
            state=session.state.__class__(
                game_id=session.state.game_id,
                rng_seed=session.state.rng_seed,
                players=session.state.players,
                objects=session.state.objects,
                stack=session.state.stack,
                turn=session.state.turn.__class__(
                    turn_number=session.state.turn.turn_number,
                    active_player="alice",
                    priority_player="alice",
                    step="cleanup_step",
                ),
                combat=session.state.combat,
            ),
            event_log=session.event_log + (
                session.event_log[-1].__class__(
                    event_id="synthetic",
                    game_id=session.state.game_id,
                    sequence=len(session.event_log) + 1,
                    event_type="turn_ended",
                    active_player="alice",
                    payload={"turn_number": 1, "active_player": "alice"},
                ),
            ),
        )

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


if __name__ == "__main__":
    unittest.main()

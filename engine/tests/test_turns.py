from __future__ import annotations

from dataclasses import replace
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mtg_engine.actions.models import (
    ActivateManaAbilityAction,
    CastNonCreatureSpellAction,
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
    cast_noncreature_spell,
    declare_attackers,
    declare_blockers,
    pass_priority,
    play_land,
    resolve_combat_damage,
    start_first_turn,
    start_next_turn,
)
from mtg_engine.state.zones import move_object


INFORMATION_DIR = Path(__file__).resolve().parents[2] / "information"
SWAMP = "56719f6a-1a6c-4c0a-8d21-18f7d7350b68"
FOREST = "b34bb2dc-c1af-4d77-b0b3-a0fb342a5fc6"
ISLAND = "b2c6aa39-2d2a-459c-a555-fb48ba993373"
MOUNTAIN = "a3fb7228-e76b-4e96-a40e-20b5fed75685"
PLAINS = "bc71ebf6-2056-41f7-be35-b2e5c34afa99"
BORDER_GUARD = "1ef5003c-f540-4cdc-913f-7d5280ad9f62"
MUCK_RATS = "bca13a12-6723-4a5e-8f1b-21646a8b3e7e"
TOUCH_OF_BRILLIANCE = "6365aba1-78d3-416c-89cd-9449578eedbf"


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

    def test_basic_lands_add_their_expected_mana_colors(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        for oracle_id, expected_mana in (
            (PLAINS, "W"),
            (ISLAND, "U"),
            (SWAMP, "B"),
            (MOUNTAIN, "R"),
            (FOREST, "G"),
        ):
            session = _build_single_land_main_phase_session(repository, oracle_id)
            session = play_land(session, PlayLandAction(player_id="alice", card_instance_id="alice:1"), repository)
            result = activate_mana_ability(
                session,
                ActivateManaAbilityAction(player_id="alice", source_instance_id="alice:1"),
                repository,
            )

            self.assertEqual(result.state.players["alice"].mana_pool, (expected_mana,))
            self.assertEqual(result.event_log[-1].payload["mana"], [expected_mana])

    def test_cleanup_clears_damage_and_mana_and_ends_turn(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _build_end_combat_session_with_marked_damage(repository)

        result = advance_to_cleanup(session)

        self.assertEqual(result.state.turn.step, "cleanup_step")
        self.assertEqual(result.state.players["alice"].mana_pool, ())
        self.assertEqual(result.state.players["alice"].lands_played_this_turn, 0)
        self.assertEqual(result.state.objects["alice:4"].damage_marked, 0)
        self.assertEqual(result.state.objects["bob:2"].damage_marked, 0)
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

    def test_touch_of_brilliance_reuses_library_to_hand_draw_path(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _build_touch_of_brilliance_main_phase_session(repository)

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

        self.assertEqual(result.state.players["alice"].hand, ("alice:6", "alice:7", "alice:8"))
        self.assertEqual(result.state.players["alice"].library, ())
        move_events = [event for event in result.event_log if event.event_type == "object_moved_between_zones"]
        self.assertEqual(
            [event.payload["from_zone"] for event in move_events[-3:]],
            ["library", "library", "stack"],
        )


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


def _build_single_land_main_phase_session(repository: CardRepository, land_oracle_id: str):
    setup = SetupInput(
        game_id=f"turn-land-{land_oracle_id}",
        players=("alice", "bob"),
        starting_player="alice",
        libraries={
            "alice": (land_oracle_id,),
            "bob": (PLAINS,),
        },
        opening_hands={
            "alice": (land_oracle_id,),
            "bob": (PLAINS,),
        },
        rng_seed=12,
    )
    return start_first_turn(initialize_game(setup, repository))


def _build_touch_of_brilliance_main_phase_session(repository: CardRepository):
    setup = SetupInput(
        game_id="turn-touch-of-brilliance",
        players=("alice", "bob"),
        starting_player="alice",
        libraries={
            "alice": (PLAINS, PLAINS, PLAINS, ISLAND, TOUCH_OF_BRILLIANCE, PLAINS, PLAINS, PLAINS),
            "bob": (PLAINS,),
        },
        opening_hands={
            "alice": (PLAINS, PLAINS, PLAINS, ISLAND, TOUCH_OF_BRILLIANCE),
            "bob": (PLAINS,),
        },
        rng_seed=15,
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
    return replace(session, state=current_state)


def _build_end_combat_session_with_marked_damage(repository: CardRepository):
    setup = SetupInput(
        game_id="turn-cleanup-damage",
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
        rng_seed=29,
    )
    session = start_first_turn(initialize_game(setup, repository))
    session = _cast_creature_from_normal_turns(session, repository, "alice", "alice:4")
    session = _advance_to_player_main_phase(_advance_to_next_turn(session, repository), repository, "bob")
    session = _cast_creature_from_normal_turns(session, repository, "bob", "bob:2")
    session = _advance_to_player_main_phase(_advance_to_next_turn(session, repository), repository, "alice")
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
    return resolve_combat_damage(session, repository)


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

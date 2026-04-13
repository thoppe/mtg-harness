from __future__ import annotations

from dataclasses import replace
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mtg_engine.actions.models import (
    ActivateManaAbilityAction,
    CastCreatureSpellAction,
    CastNonCreatureSpellAction,
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
    cast_noncreature_spell,
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
PLAINS = "bc71ebf6-2056-41f7-be35-b2e5c34afa99"
SWAMP = "56719f6a-1a6c-4c0a-8d21-18f7d7350b68"
BORDER_GUARD = "1ef5003c-f540-4cdc-913f-7d5280ad9f62"
FOOT_SOLDIERS = "a768ba13-4d1c-4dce-a4a6-86a39c069c3f"
MUCK_RATS = "bca13a12-6723-4a5e-8f1b-21646a8b3e7e"
VENGEANCE = "1d001145-5d14-43a9-bf3b-3ce5c20b2a46"
PATH_OF_PEACE = "b7593cf8-4dcb-473b-a2ef-180fffe66738"
ISLAND = "b2c6aa39-2d2a-459c-a555-fb48ba993373"
TOUCH_OF_BRILLIANCE = "6365aba1-78d3-416c-89cd-9449578eedbf"


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
        result = _cast_creature_from_normal_turns(session, repository, "alice", "alice:4")

        self.assertEqual(result.state.players["alice"].battlefield, ("alice:1", "alice:2", "alice:3", "alice:4"))
        self.assertEqual(result.state.players["alice"].hand, ())
        self.assertEqual(result.state.stack, ())
        self.assertEqual(result.state.players["alice"].mana_pool, ())
        self.assertEqual(result.state.objects["alice:4"].zone, "battlefield")
        self.assertEqual(
            [event.event_type for event in result.event_log[-4:]],
            ["spell_cast", "object_moved_between_zones", "spell_resolved", "object_moved_between_zones"],
        )

    def test_cast_foot_soldiers_with_four_plains(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _build_foot_soldiers_session(repository)

        result = _cast_creature_from_normal_turns(session, repository, "alice", "alice:5")

        self.assertEqual(result.state.players["alice"].battlefield, ("alice:1", "alice:2", "alice:3", "alice:4", "alice:5"))
        self.assertEqual(result.state.players["alice"].hand, ())
        self.assertEqual(result.state.stack, ())
        self.assertEqual(result.state.players["alice"].mana_pool, ())
        self.assertEqual(result.state.objects["alice:5"].zone, "battlefield")
        self.assertEqual(result.state.objects["alice:5"].oracle_id, FOOT_SOLDIERS)
        self.assertEqual(
            [event.event_type for event in result.event_log[-4:]],
            ["spell_cast", "object_moved_between_zones", "spell_resolved", "object_moved_between_zones"],
        )

    def test_cast_muck_rats_with_swamp(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _build_muck_rats_session(repository)

        result = _cast_creature_from_normal_turns(session, repository, "alice", "alice:2")

        self.assertEqual(result.state.players["alice"].battlefield, ("alice:1", "alice:2"))
        self.assertEqual(result.state.players["alice"].hand, ())
        self.assertEqual(result.state.players["alice"].mana_pool, ())
        self.assertEqual(result.state.objects["alice:2"].zone, "battlefield")
        self.assertEqual(result.state.objects["alice:2"].oracle_id, MUCK_RATS)

    def test_cast_vengeance_destroys_tapped_creature_and_moves_spell_to_graveyard(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _build_vengeance_session(repository)

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

        self.assertEqual(result.state.players["alice"].hand, ())
        self.assertEqual(result.state.players["alice"].graveyard, ("alice:5",))
        self.assertEqual(result.state.players["bob"].graveyard, ("bob:1",))
        self.assertEqual(result.state.players["alice"].mana_pool, ())
        self.assertEqual(result.state.stack, ())
        self.assertEqual(result.state.objects["alice:5"].zone, "graveyard")
        self.assertEqual(result.state.objects["alice:5"].oracle_id, VENGEANCE)
        self.assertEqual(result.state.objects["bob:1"].zone, "graveyard")
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

    def test_cast_path_of_peace_destroys_creature_and_grants_owner_life(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _build_path_of_peace_session(repository)

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

        self.assertEqual(result.state.players["alice"].hand, ())
        self.assertEqual(result.state.players["alice"].graveyard, ("alice:5",))
        self.assertEqual(result.state.players["bob"].graveyard, ("bob:1",))
        self.assertEqual(result.state.players["bob"].life_total, 24)
        self.assertEqual(result.state.players["alice"].mana_pool, ())
        self.assertEqual(result.state.stack, ())
        self.assertEqual(result.state.objects["alice:5"].zone, "graveyard")
        self.assertEqual(result.state.objects["alice:5"].oracle_id, PATH_OF_PEACE)
        self.assertEqual(result.state.objects["bob:1"].zone, "graveyard")
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

    def test_cast_touch_of_brilliance_draws_two_cards_and_moves_spell_to_graveyard(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _build_touch_of_brilliance_session(repository)

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
        self.assertEqual(result.state.players["alice"].graveyard, ("alice:5",))
        self.assertEqual(result.state.players["alice"].mana_pool, ())
        self.assertEqual(result.state.stack, ())
        self.assertEqual(result.state.objects["alice:5"].zone, "graveyard")
        self.assertEqual(result.state.objects["alice:5"].oracle_id, TOUCH_OF_BRILLIANCE)
        non_mana_events = [event.event_type for event in result.event_log if event.event_type != "mana_added"]
        spell_cast_index = non_mana_events.index("spell_cast")
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


def _build_foot_soldiers_session(repository: CardRepository):
    setup = SetupInput(
        game_id="spell-cast-foot-soldiers",
        players=("alice", "bob"),
        starting_player="alice",
        libraries={
            "alice": (PLAINS, PLAINS, PLAINS, PLAINS, FOOT_SOLDIERS),
            "bob": (PLAINS,),
        },
        opening_hands={
            "alice": (PLAINS, PLAINS, PLAINS, PLAINS, FOOT_SOLDIERS),
            "bob": (PLAINS,),
        },
        rng_seed=19,
    )
    return start_first_turn(initialize_game(setup, repository))


def _build_muck_rats_session(repository: CardRepository):
    setup = SetupInput(
        game_id="spell-cast-muck-rats",
        players=("alice", "bob"),
        starting_player="alice",
        libraries={
            "alice": (SWAMP, MUCK_RATS),
            "bob": (PLAINS,),
        },
        opening_hands={
            "alice": (SWAMP, MUCK_RATS),
            "bob": (PLAINS,),
        },
        rng_seed=23,
    )
    return start_first_turn(initialize_game(setup, repository))


def _build_vengeance_session(repository: CardRepository):
    setup = SetupInput(
        game_id="spell-cast-vengeance",
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
        rng_seed=29,
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
    return replace(session, state=current_state)


def _build_path_of_peace_session(repository: CardRepository):
    setup = SetupInput(
        game_id="spell-cast-path-of-peace",
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
        rng_seed=31,
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
    return replace(session, state=current_state)


def _build_touch_of_brilliance_session(repository: CardRepository):
    setup = SetupInput(
        game_id="spell-cast-touch-of-brilliance",
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
        rng_seed=33,
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


def _cast_creature_from_normal_turns(session, repository: CardRepository, player_id: str, creature_id: str):
    current_session = _advance_to_player_main_phase(session, repository, player_id)
    player = current_session.state.players[player_id]
    land_ids = [instance_id for instance_id in player.hand if instance_id != creature_id]
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


def _required_mana_value(repository: CardRepository, oracle_id: str) -> int:
    mana_cost = repository.get(oracle_id).mana_cost
    return sum(int(symbol) if symbol.isdigit() else 1 for symbol in mana_cost.replace("{", " ").replace("}", " ").split())


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

from __future__ import annotations

import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mtg_engine.actions.models import ActivateManaAbilityAction, CastCreatureSpellAction, PlayLandAction
from mtg_engine.cards.repository import CardRepository
from mtg_engine.flow.setup import SetupInput, initialize_game
from mtg_engine.flow.turns import activate_mana_ability, cast_creature_spell, play_land, start_first_turn


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
        session = play_land(session, PlayLandAction(player_id="alice", card_instance_id="alice:1"), repository)
        session = _next_turn_main_phase_with_reset(session)
        session = play_land(session, PlayLandAction(player_id="alice", card_instance_id="alice:2"), repository)
        session = _next_turn_main_phase_with_reset(session)
        session = play_land(session, PlayLandAction(player_id="alice", card_instance_id="alice:3"), repository)
        session = activate_mana_ability(session, ActivateManaAbilityAction(player_id="alice", source_instance_id="alice:1"), repository)
        session = activate_mana_ability(session, ActivateManaAbilityAction(player_id="alice", source_instance_id="alice:2"), repository)
        session = activate_mana_ability(session, ActivateManaAbilityAction(player_id="alice", source_instance_id="alice:3"), repository)

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


def _next_turn_main_phase_with_reset(session):
    state = session.state
    alice = state.players["alice"]
    reset_player = alice.__class__(
        player_id=alice.player_id,
        life_total=alice.life_total,
        library=alice.library,
        hand=alice.hand,
        battlefield=alice.battlefield,
        graveyard=alice.graveyard,
        mana_pool=(),
        lands_played_this_turn=0,
    )
    updated_players = dict(state.players)
    updated_players["alice"] = reset_player
    reset_objects = {
        key: value.__class__(
            instance_id=value.instance_id,
            oracle_id=value.oracle_id,
            owner_id=value.owner_id,
            controller_id=value.controller_id,
            zone=value.zone,
            tapped=False,
        )
        for key, value in state.objects.items()
    }
    next_state = state.__class__(
        game_id=state.game_id,
        rng_seed=state.rng_seed,
        players=updated_players,
        objects=reset_objects,
        stack=state.stack,
        turn=state.turn.__class__(
            turn_number=state.turn.turn_number + 1,
            active_player="alice",
            priority_player="alice",
            step="precombat_main_step",
        ),
    )
    return session.__class__(state=next_state, event_log=session.event_log)


if __name__ == "__main__":
    unittest.main()

"""Bounded legal-deck game generation regressions.

These deliberately drive only actions enumerated by the engine.  They use a
legal, Portal-only deck rather than the rules-harness setup path so that deck
construction, shuffle, opening hands, turn flow, and zone accounting meet at
one boundary.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mtg_engine.actions.dispatch import dispatch_action
from mtg_engine.actions.models import (
    ActivateManaAbilityAction,
    AdvanceStepAction,
    AdvanceTurnAction,
    CastCreatureSpellAction,
    CastNonCreatureSpellAction,
    DeclareAttackersAction,
    DeclareBlockersAction,
    PassPriorityAction,
    PlayLandAction,
)
from mtg_engine.cards.repository import CardRepository
from mtg_engine.decks import DeckList, DeckValidationError, PORTAL_CONSTRUCTED_V0, validate_deck
from mtg_engine.decks.fixtures import portal_blue_starter, portal_white_starter
from mtg_engine.flow.deck_start import DeckGameInput, initialize_deck_game, keep_london_hand
from mtg_engine.flow.priority import enumerate_legal_actions
from mtg_engine.flow.setup import SetupInput
from mtg_engine.flow.turns import TurnResult, start_first_turn
from mtg_engine.replay.reducer import ReplayInput, replay
from mtg_engine.services import GameSession


REPO_ROOT = Path(__file__).resolve().parents[2]
INFORMATION_DIR = REPO_ROOT / "information"
PLAINS = "bc71ebf6-2056-41f7-be35-b2e5c34afa99"
RAIN_OF_DAGGERS = "e2048201-6dc9-4cf5-916f-1d867ae8dbdd"
PLAYERS = ("alice", "bob")


class GeneratedLegalDeckGameTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repository = CardRepository.from_information_directory(INFORMATION_DIR)

    def _deck_input(self, seed: int = 71, *, starter_decks: bool = False) -> DeckGameInput:
        """Build either the tiny outcome fixture or two real Portal starters.

        The all-Plains form remains useful for the bounded deck-out outcome.
        Long traces deliberately use the public starter fixtures so they cover
        land development, mana, creatures, stack resolution, and combat.
        """
        decks = (
            {"alice": portal_white_starter(), "bob": portal_blue_starter()}
            if starter_decks
            else {player_id: DeckList((PLAINS,) * 60) for player_id in PLAYERS}
        )
        return DeckGameInput(
            game_id="generated-portal-game",
            players=PLAYERS,
            starting_player="alice",
            decks=decks,
            rng_seed=seed,
        )

    def _kept_bootstrap(self, seed: int = 71, *, starter_decks: bool = False):
        bootstrap = initialize_deck_game(
            self._deck_input(seed, starter_decks=starter_decks), self.repository
        )
        bootstrap = keep_london_hand(bootstrap, "alice")
        return keep_london_hand(bootstrap, "bob")

    @staticmethod
    def _choose_action(actions: tuple[object, ...]) -> object:
        """Choose a deterministic legal action that develops a real game."""
        has_cast = any(
            isinstance(action, (CastCreatureSpellAction, CastNonCreatureSpellAction))
            for action in actions
        )
        preferred_types = (
            PlayLandAction,
            *((ActivateManaAbilityAction,) if has_cast else ()),
            CastCreatureSpellAction,
            CastNonCreatureSpellAction,
            AdvanceStepAction,
            AdvanceTurnAction,
            PassPriorityAction,
        )
        # Attack with everything and decline blocks.  These are both chosen
        # from legal action instances, not reconstructed from battlefield IDs.
        attacker_actions = [action for action in actions if isinstance(action, DeclareAttackersAction)]
        if attacker_actions:
            return max(attacker_actions, key=lambda action: len(action.attacker_ids))
        blocker_actions = [action for action in actions if isinstance(action, DeclareBlockersAction)]
        if blocker_actions:
            return min(blocker_actions, key=lambda action: sum(len(ids) for ids in action.blockers.values()))
        for action_type in preferred_types:
            for action in actions:
                if isinstance(action, action_type):
                    return action
        raise AssertionError(f"bounded generator has no policy for {actions!r}")

    def _assert_zone_invariants(self, result: TurnResult) -> None:
        state = result.state
        locations: dict[str, tuple[str, str]] = {}
        for player_id, player in state.players.items():
            for zone_name in ("library", "hand", "battlefield", "graveyard"):
                for instance_id in getattr(player, zone_name):
                    self.assertNotIn(instance_id, locations, f"{instance_id} appears in two zones")
                    locations[instance_id] = (player_id, zone_name)

        for instance_id in state.stack:
            self.assertNotIn(instance_id, locations, f"{instance_id} is both stacked and zoned")
            locations[instance_id] = (state.objects[instance_id].owner_id, "stack")

        self.assertEqual(set(locations), set(state.objects), "every object has exactly one zone or stack location")
        for instance_id, (player_id, zone_name) in locations.items():
            card = state.objects[instance_id]
            self.assertEqual(card.owner_id, player_id)
            self.assertEqual(card.zone, zone_name)
            self.assertNotEqual(card.oracle_id, RAIN_OF_DAGGERS)
        self.assertEqual(len(locations), 120)

    def _drive(
        self, seed: int, maximum_actions: int, *, starter_decks: bool = False
    ) -> tuple[TurnResult, tuple[object, ...]]:
        result = start_first_turn(self._kept_bootstrap(seed, starter_decks=starter_decks))
        actions_taken: list[object] = []
        self._assert_zone_invariants(result)
        while len(actions_taken) < maximum_actions and result.state.outcome.status == "in_progress":
            legal_actions = enumerate_legal_actions(result.state, self.repository)
            self.assertTrue(legal_actions, f"no legal action at {result.state.turn}")
            action = self._choose_action(legal_actions)
            self.assertIn(action, legal_actions)
            result = dispatch_action(result, action, self.repository)
            actions_taken.append(action)
            self._assert_zone_invariants(result)
        return result, tuple(actions_taken)

    def test_same_seed_legal_games_have_identical_bounded_trace_and_invariants(self) -> None:
        first, first_actions = self._drive(seed=71, maximum_actions=30)
        second, second_actions = self._drive(seed=71, maximum_actions=30)

        self.assertEqual(first_actions, second_actions)
        self.assertEqual(first, second)
        self.assertEqual(first.state.outcome.status, "in_progress")
        self.assertTrue(first_actions)

    def test_portal_starter_decks_produce_a_deterministic_trace_past_ten_turns(self) -> None:
        """A long legal-deck trace exercises actual Portal starter cards.

        Every transition is selected from current enumeration, including
        generated target choices.  The bounded result is permitted to end
        early only if ordinary game rules produce a terminal outcome.
        """
        first, first_actions = self._drive(
            seed=202, maximum_actions=360, starter_decks=True
        )
        second, second_actions = self._drive(
            seed=202, maximum_actions=360, starter_decks=True
        )

        self.assertGreaterEqual(first.state.turn.turn_number, 10)
        self.assertGreaterEqual(len(first_actions), 80)
        self.assertEqual(first_actions, second_actions)
        self.assertEqual(first, second)
        self.assertIn(first.state.outcome.status, {"in_progress", "completed"})
        for player in first.state.players.values():
            self.assertNotIn(RAIN_OF_DAGGERS, (
                first.state.objects[instance_id].oracle_id
                for instance_id in player.library + player.hand + player.battlefield + player.graveyard
            ))

    def test_legal_deck_start_can_project_to_compatible_session_replay(self) -> None:
        """Deck shuffle is private setup; normal action replay remains setup-compatible."""
        bootstrap = self._kept_bootstrap(seed=91, starter_decks=True)
        setup = SetupInput(
            game_id=bootstrap.state.game_id,
            players=PLAYERS,
            starting_player="alice",
            libraries={
                player_id: tuple(
                    bootstrap.state.objects[instance_id].oracle_id
                    for instance_id in (
                        bootstrap.state.players[player_id].hand
                        + bootstrap.state.players[player_id].library
                    )
                )
                for player_id in PLAYERS
            },
            opening_hands={
                player_id: tuple(
                    bootstrap.state.objects[instance_id].oracle_id
                    for instance_id in bootstrap.state.players[player_id].hand
                )
                for player_id in PLAYERS
            },
            rng_seed=91,
        )
        session = GameSession.from_setup(setup, self.repository)
        for _ in range(180):
            if session.state.outcome.status == "completed":
                break
            action = self._choose_action(session.legal_actions())
            self.assertIn(action, session.legal_actions())
            session.submit(action)  # type: ignore[arg-type]
            self._assert_zone_invariants(session.result)

        replayed = replay(session.replay_input(), self.repository)
        self.assertEqual(replayed.state, session.state)
        self.assertEqual(replayed.event_log, session.result.event_log)
        self.assertGreaterEqual(session.state.turn.turn_number, 10)

    def test_generated_legal_game_reaches_a_deterministic_empty_library_outcome(self) -> None:
        result, actions = self._drive(seed=113, maximum_actions=800)

        self.assertLess(len(actions), 800)
        self.assertEqual(result.state.outcome.status, "completed")
        self.assertEqual(result.state.outcome.reason, "draw_from_empty_library")
        self.assertIn(result.state.outcome.loser_ids[0], PLAYERS)
        self.assertIn(result.state.outcome.winner_id, PLAYERS)

    def test_legal_generator_rejects_scenario_only_card_before_start(self) -> None:
        invalid_deck = DeckList((PLAINS,) * 59 + (RAIN_OF_DAGGERS,))
        with self.assertRaisesRegex(DeckValidationError, "not deck eligible"):
            validate_deck(invalid_deck, PORTAL_CONSTRUCTED_V0, self.repository)
        with self.assertRaisesRegex(DeckValidationError, "not deck eligible"):
            initialize_deck_game(
                replace(self._deck_input(), decks={"alice": invalid_deck, "bob": DeckList((PLAINS,) * 60)}),
                self.repository,
            )


if __name__ == "__main__":
    unittest.main()

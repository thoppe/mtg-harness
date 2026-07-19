"""Cross-wave game-flow and replay determinism regressions.

These tests intentionally exercise the public transition functions rather
than calling a card-effect branch directly.  They cover the seams where a
correct individual card implementation can still produce a non-replayable or
non-terminating game.
"""

from __future__ import annotations

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mtg_engine.actions.models import (
    ActivateAbilityAction,
    ActivateManaAbilityAction,
    CastNonCreatureSpellAction,
    DeclareAttackersAction,
    DeclareBlockersAction,
    PassPriorityAction,
    PlayLandAction,
)
from mtg_engine.cards.repository import CardRepository
from mtg_engine.flow.setup import SetupInput, initialize_game
from mtg_engine.flow.turns import (
    TurnResult,
    _resolve_noncreature_spell,
    advance_to_begin_combat,
    advance_to_cleanup,
    declare_attackers,
    declare_blockers,
    pass_priority,
    play_land,
    resolve_combat_damage,
    start_first_turn,
    start_next_turn,
)
from mtg_engine.replay.reducer import ReplayInput, replay
from mtg_engine.state.models import StackEntry
from mtg_engine.state.zones import move_object


INFO = Path(__file__).resolve().parents[2] / "information"
MOUNTAIN = "a3fb7228-e76b-4e96-a40e-20b5fed75685"
WINDS_OF_CHANGE = "f525cf10-e24c-4c46-9a13-6f8579d09d50"
LAST_CHANCE = "360039a5-1cbd-4ee3-8f94-21b5348e106a"
RAIN_OF_TEARS = "72cecab3-519e-4a23-9623-b423a5c5a251"
CAPRICIOUS_SORCERER = "09fe624f-c66a-46e4-a9af-7e3c3ca1a4e3"


class EndToEndScenarioTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = CardRepository.from_information_directory(INFO)

    def _winds_setup(self, seed: int) -> SetupInput:
        # The opening hand contains a land, Winds, and one card to recycle;
        # the remaining cards make the shuffle/draw outcome observable.
        alice_cards = (MOUNTAIN, WINDS_OF_CHANGE, RAIN_OF_TEARS, RAIN_OF_TEARS, RAIN_OF_TEARS)
        bob_cards = (RAIN_OF_TEARS, RAIN_OF_TEARS)
        return SetupInput(
            game_id=f"e2e-winds-{seed}",
            players=("alice", "bob"),
            starting_player="alice",
            libraries={"alice": alice_cards, "bob": bob_cards},
            opening_hands={"alice": alice_cards[:3], "bob": bob_cards[:1]},
            rng_seed=seed,
        )

    def _winds_actions(self) -> tuple[object, ...]:
        return (
            PlayLandAction(player_id="alice", card_instance_id="alice:1"),
            ActivateManaAbilityAction(player_id="alice", source_instance_id="alice:1"),
            CastNonCreatureSpellAction(player_id="alice", card_instance_id="alice:2"),
            PassPriorityAction(player_id="alice"),
            PassPriorityAction(player_id="bob"),
        )

    def _play_winds_directly(self, setup: SetupInput) -> TurnResult:
        actions = self._winds_actions()
        session = start_first_turn(initialize_game(setup, self.repo))
        session = play_land(session, actions[0], self.repo)
        from mtg_engine.flow.turns import activate_mana_ability, cast_noncreature_spell

        session = activate_mana_ability(session, actions[1], self.repo)
        session = cast_noncreature_spell(session, actions[2], self.repo)
        session = pass_priority(session, actions[3], self.repo)
        return pass_priority(session, actions[4], self.repo)

    def test_seeded_hidden_zone_spell_replays_byte_for_byte_across_seeds(self) -> None:
        """A shuffle-bearing Wave 5 spell must replay its full public trace."""
        for seed in range(1, 13):
            with self.subTest(seed=seed):
                setup = self._winds_setup(seed)
                direct = self._play_winds_directly(setup)
                reduced = replay(ReplayInput(setup=setup, actions=self._winds_actions()), self.repo)

                self.assertEqual(reduced.state, direct.state)
                self.assertEqual(reduced.event_log, direct.event_log)
                shuffle_events = [event for event in direct.event_log if event.event_type == "library_shuffled"]
                self.assertEqual(len(shuffle_events), 2)
                self.assertEqual(
                    [(event.payload["rng_cursor_before"], event.payload["rng_cursor_after"]) for event in shuffle_events],
                    [(0, 1), (1, 2)],
                )

    def test_last_chance_extra_turn_reaches_terminal_outcome_without_next_turn(self) -> None:
        """A scheduled losing extra turn is a complete two-turn scenario."""
        setup = SetupInput(
            game_id="e2e-last-chance",
            players=("alice", "bob"),
            starting_player="alice",
            libraries={"alice": (LAST_CHANCE,), "bob": (RAIN_OF_TEARS,)},
            opening_hands={"alice": (LAST_CHANCE,), "bob": (RAIN_OF_TEARS,)},
            rng_seed=44,
        )
        started = start_first_turn(initialize_game(setup, self.repo))
        state = move_object(started.state, instance_id="alice:1", from_zone="hand", to_zone="stack", player_id="alice")
        initial = TurnResult(state=state, event_log=started.event_log)
        first_turn = _resolve_noncreature_spell(initial, StackEntry(card_instance_id="alice:1", controller_id="alice"), self.repo)

        # Complete Alice's ordinary turn, then the extra turn.  Empty combat
        # declarations keep this a genuine multi-turn flow without relying on
        # a private step mutation.
        normal_combat = advance_to_begin_combat(first_turn)
        normal_combat = declare_attackers(normal_combat, DeclareAttackersAction("alice", ()), self.repo)
        normal_combat = pass_priority(normal_combat, PassPriorityAction("alice"), self.repo)
        normal_combat = pass_priority(normal_combat, PassPriorityAction("bob"), self.repo)
        normal_combat = declare_blockers(normal_combat, DeclareBlockersAction("bob", {}), self.repo)
        normal_combat = resolve_combat_damage(normal_combat, self.repo)
        extra_turn = start_next_turn(advance_to_cleanup(normal_combat))
        self.assertEqual((extra_turn.state.turn.turn_number, extra_turn.state.turn.active_player), (2, "alice"))

        extra_combat = advance_to_begin_combat(extra_turn)
        extra_combat = declare_attackers(extra_combat, DeclareAttackersAction("alice", ()), self.repo)
        extra_combat = pass_priority(extra_combat, PassPriorityAction("alice"), self.repo)
        extra_combat = pass_priority(extra_combat, PassPriorityAction("bob"), self.repo)
        extra_combat = declare_blockers(extra_combat, DeclareBlockersAction("bob", {}), self.repo)
        extra_combat = resolve_combat_damage(extra_combat, self.repo)
        terminal = advance_to_cleanup(extra_combat)

        self.assertEqual(terminal.state.outcome.status, "completed")
        self.assertEqual(terminal.state.outcome.winner_id, "bob")
        self.assertEqual(terminal.state.outcome.reason, "last_chance")
        self.assertEqual(terminal.state.turn.step, "end_step")
        self.assertFalse(any(event.event_type == "turn_ended" for event in terminal.event_log[-3:]))

    def test_replay_routes_activated_abilities_to_normal_validation(self) -> None:
        """Replay must not silently omit the Wave 7 accepted-action family."""
        setup = SetupInput(
            game_id="e2e-replay-activation-routing",
            players=("alice", "bob"),
            starting_player="alice",
            libraries={"alice": (CAPRICIOUS_SORCERER,), "bob": (RAIN_OF_TEARS,)},
            opening_hands={"alice": (CAPRICIOUS_SORCERER,), "bob": (RAIN_OF_TEARS,)},
            rng_seed=55,
        )
        with self.assertRaisesRegex(ValueError, "ability source must be controlled on the battlefield"):
            replay(
                ReplayInput(
                    setup=setup,
                    actions=(ActivateAbilityAction("alice", "alice:1", target_instance_id="bob"),),
                ),
                self.repo,
            )

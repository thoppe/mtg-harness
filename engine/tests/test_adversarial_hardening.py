from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mtg_engine.actions.models import ActivateAbilityAction, PassPriorityAction
from mtg_engine.cards.repository import CardRepository
from mtg_engine.flow.setup import SetupInput, initialize_game
from mtg_engine.flow.turns import TurnResult, activate_ability, pass_priority
from mtg_engine.rules.combat import apply_state_based_actions
from mtg_engine.state.zones import move_object


INFO = Path(__file__).resolve().parents[2] / "information"
CAPRICIOUS_SORCERER = "09fe624f-c66a-46e4-a9af-7e3c3ca1a4e3"
ENDLESS_COCKROACHES = "9f31dbb1-c350-46f8-bd1d-9f23a073d2f1"
UNDYING_BEAST = "5ae03181-a436-4bad-be3a-6c9f6c0ed4d6"


class AdversarialIdentityHardeningTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = CardRepository.from_information_directory(INFO)

    def test_activated_ability_survives_source_departure_and_reentry(self) -> None:
        """An activated ability is independent, but its returned source is fresh."""
        setup = SetupInput(
            "adversarial-activated-source-reentry",
            ("alice", "bob"),
            "alice",
            {"alice": (CAPRICIOUS_SORCERER,), "bob": (ENDLESS_COCKROACHES,)},
            {"alice": (CAPRICIOUS_SORCERER,), "bob": (ENDLESS_COCKROACHES,)},
            101,
        )
        state = initialize_game(setup, self.repo).state
        state = move_object(
            state, instance_id="alice:1", from_zone="hand", to_zone="battlefield",
            player_id="alice",
        )
        # Make the source old enough to activate without bypassing the actual
        # activation validation; its re-entry below is deliberately this turn.
        state = replace(
            state,
            objects={
                **state.objects,
                "alice:1": replace(state.objects["alice:1"], entered_battlefield_turn=0),
            },
            turn=replace(state.turn, step="precombat_main_step"),
        )

        activated = activate_ability(
            TurnResult(state, ()),
            ActivateAbilityAction("alice", "alice:1", target_instance_id="bob"),
            self.repo,
        )
        old_object_id = activated.state.stack_entries[-1].source_object_id
        self.assertTrue(activated.state.objects["alice:1"].tapped)

        departed = move_object(
            activated.state, instance_id="alice:1", from_zone="battlefield",
            to_zone="graveyard", player_id="alice",
        )
        returned = move_object(
            departed, instance_id="alice:1", from_zone="graveyard",
            to_zone="battlefield", player_id="alice",
        )
        new_source = returned.objects["alice:1"]
        self.assertNotEqual(new_source.object_id, old_object_id)
        self.assertFalse(new_source.tapped)
        self.assertEqual(new_source.entered_battlefield_turn, returned.turn.turn_number)

        pending = TurnResult(returned, activated.event_log)
        pending = pass_priority(pending, PassPriorityAction("alice"), self.repo)
        resolved = pass_priority(pending, PassPriorityAction("bob"), self.repo)

        self.assertEqual(resolved.state.players["bob"].life_total, 19)
        self.assertEqual(resolved.state.objects["alice:1"].zone, "battlefield")
        self.assertFalse(resolved.state.objects["alice:1"].tapped)
        self.assertEqual(
            resolved.event_log[-1].event_type, "activated_ability_resolved"
        )

    def test_simultaneous_dies_triggers_keep_apnap_order_and_reject_stale_identity(self) -> None:
        """One stale dies trigger neither touches its new object nor consumes RNG."""
        setup = SetupInput(
            "adversarial-simultaneous-dies",
            ("alice", "bob"),
            "alice",
            {"alice": (UNDYING_BEAST,), "bob": (ENDLESS_COCKROACHES,)},
            {"alice": (UNDYING_BEAST,), "bob": (ENDLESS_COCKROACHES,)},
            103,
        )
        state = initialize_game(setup, self.repo).state
        for player_id in ("alice", "bob"):
            state = move_object(
                state, instance_id=f"{player_id}:1", from_zone="hand",
                to_zone="battlefield", player_id=player_id,
            )
        state = replace(
            state,
            objects={
                **state.objects,
                "alice:1": replace(state.objects["alice:1"], damage_marked=99),
                "bob:1": replace(state.objects["bob:1"], damage_marked=99),
            },
            turn=replace(state.turn, step="precombat_main_step"),
        )

        destroyed, _ = apply_state_based_actions(state, self.repo, active_player="alice")
        self.assertEqual(
            [entry.controller_id for entry in destroyed.stack_entries], ["alice", "bob"]
        )
        expected_alice_graveyard_object = destroyed.stack_entries[0].expected_graveyard_object_id

        # The Undying Beast returns to the same zone as a new object before its
        # trigger reaches the top of the APNAP stack.
        stale = move_object(
            destroyed, instance_id="alice:1", from_zone="graveyard",
            to_zone="hand", player_id="alice",
        )
        stale = move_object(
            stale, instance_id="alice:1", from_zone="hand", to_zone="graveyard",
            player_id="alice",
        )
        self.assertNotEqual(stale.objects["alice:1"].object_id, expected_alice_graveyard_object)

        # Bob's (nonactive player's) trigger resolves first, then Alice's stale
        # trigger resolves exactly once with no effect.
        session = TurnResult(stale, ())
        session = pass_priority(session, PassPriorityAction("alice"), self.repo)
        after_bob = pass_priority(session, PassPriorityAction("bob"), self.repo)
        self.assertEqual(after_bob.state.objects["bob:1"].zone, "hand")
        self.assertEqual(len(after_bob.state.stack_entries), 1)
        session = pass_priority(after_bob, PassPriorityAction("alice"), self.repo)
        resolved = pass_priority(session, PassPriorityAction("bob"), self.repo)

        self.assertEqual(resolved.state.objects["alice:1"].zone, "graveyard")
        self.assertEqual(resolved.state.rng_cursor, 0)
        resolved_triggers = [
            event for event in resolved.event_log
            if event.event_type == "triggered_ability_resolved"
        ]
        self.assertEqual(
            [event.payload["ability_key"] for event in resolved_triggers],
            ["endless_cockroaches_death", "undying_beast_death"],
        )

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mtg_engine.actions.models import ResolveChoiceAction
from mtg_engine.cards.repository import CardRepository
from mtg_engine.flow.setup import SetupInput, initialize_game
from mtg_engine.flow.priority import enumerate_legal_actions
from mtg_engine.flow.turns import (
    TurnResult,
    _resolve_wave7_trigger,
    resolve_pending_choice,
)
from mtg_engine.state.models import StackEntry
from mtg_engine.state.zones import move_object


INFO = Path(__file__).resolve().parents[2] / "information"
FOREST = "b34bb2dc-c1af-4d77-b0b3-a0fb342a5fc6"
ISLAND = "b2c6aa39-2d2a-459c-a555-fb48ba993373"
GRIZZLY_BEARS = "14c8f55d-d177-4c25-a931-ebeb9e6062a0"
MUCK_RATS = "bca13a12-6723-4a5e-8f1b-21646a8b3e7e"
EBON_DRAGON = "12e4d2bd-83e9-4120-a2e8-0645c0ed2387"
FIRE_IMP = "5bd806e7-3f9b-4bb4-9708-f87a578f531e"
FIRE_DRAGON = "349d8ef9-e07a-416f-a5b1-2c2be6bb322d"
FIRE_SNAKE = "e96542ed-1931-4da1-9d9e-d10878c4ae6b"
GRAVEDIGGER = "1a2030cc-d7ee-4059-b2d7-fb95ea8e267b"
INGENIOUS_THIEF = "73ea2949-5812-478d-8f09-00743ce4d40f"
MAN_O_WAR = "67a3541c-8408-40c8-b44f-90035b860f57"
MERCENARY_KNIGHT = "ed5429bb-233a-4528-bf7d-df5f6b192b1c"
NOXIOUS_TOAD = "2fdc484e-b3c3-4f4e-99a1-26a1134aa1cd"
OWL_FAMILIAR = "099a5835-da6c-4e03-ad3e-aeb448897fed"
PLANT_ELEMENTAL = "e822bf3d-3a29-4a02-9ae8-e2830ce70f15"
PRIMEVAL_FORCE = "f4170db0-3adf-4744-b0ec-e889c713bb93"
SEASONED_MARSHAL = "0c7239bf-dc8a-4d79-867e-7a4225568c49"
SERPENT_ASSASSIN = "3bc7d3a7-ddb4-4eaa-882e-404d8f2926fb"
THING_FROM_THE_DEEP = "9542bd7f-bb99-4b59-a4e3-b88ed9f798bf"
THUNDERING_WURM = "cdab50a8-1e02-4ba5-8c09-e2837e7652f7"
WOOD_ELVES = "8973bd99-20f8-4867-90ef-50392147ee1b"


class WaveSevenTriggerChoiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = CardRepository.from_information_directory(INFO)

    def _state(
        self,
        source_oracle_id: str,
        *,
        alice_cards: tuple[str, ...] = (),
        bob_cards: tuple[str, ...] = (),
        alice_opening: int | None = None,
        bob_opening: int | None = None,
    ):
        alice = (source_oracle_id,) + alice_cards
        setup = SetupInput(
            "wave7-choice",
            ("alice", "bob"),
            "alice",
            {"alice": alice, "bob": bob_cards},
            {
                "alice": alice[:len(alice) if alice_opening is None else alice_opening],
                "bob": bob_cards[:len(bob_cards) if bob_opening is None else bob_opening],
            },
            17,
        )
        state = initialize_game(setup, self.repo).state
        return move_object(
            state, instance_id="alice:1", from_zone="hand",
            to_zone="battlefield", player_id="alice",
        )

    def _request(self, state, source_oracle_id: str):
        source = state.objects["alice:1"]
        entry = StackEntry(
            card_instance_id="alice:1",
            controller_id="alice",
            entry_kind="wave7_trigger",
            source_object_id=source.object_id,
            source_oracle_id=source_oracle_id,
        )
        return _resolve_wave7_trigger(TurnResult(state, ()), entry, self.repo)

    def _choose(self, pending, *selected):
        decision = pending.state.pending_decision
        return resolve_pending_choice(
            pending,
            ResolveChoiceAction(
                "alice", decision.decision_id,
                selected_instance_ids=tuple(selected),
            ),
            self.repo,
        )

    def _choose_as(self, pending, player_id, *selected):
        decision = pending.state.pending_decision
        return resolve_pending_choice(
            pending,
            ResolveChoiceAction(
                player_id,
                decision.decision_id,
                selected_instance_ids=tuple(selected),
            ),
            self.repo,
        )

    def test_optional_gravedigger_choice_can_be_declined(self) -> None:
        state = self._state(GRAVEDIGGER, alice_cards=(GRIZZLY_BEARS,))
        state = move_object(
            state, instance_id="alice:2", from_zone="hand",
            to_zone="graveyard", player_id="alice",
        )
        pending = self._request(state, GRAVEDIGGER)

        self.assertEqual(pending.state.pending_decision.option_ids, ("alice:2",))
        self.assertNotIn("triggered_ability_resolved", [e.event_type for e in pending.event_log])
        resolved = self._choose(pending)

        self.assertEqual(resolved.state.objects["alice:2"].zone, "graveyard")
        self.assertEqual(resolved.event_log[-1].event_type, "triggered_ability_resolved")

    def test_fire_imp_uses_non_first_mandatory_target(self) -> None:
        state = self._state(FIRE_IMP, bob_cards=(GRIZZLY_BEARS, MUCK_RATS))
        for instance_id in ("bob:1", "bob:2"):
            state = move_object(
                state, instance_id=instance_id, from_zone="hand",
                to_zone="battlefield", player_id="bob",
            )
        pending = self._request(state, FIRE_IMP)
        resolved = self._choose(pending, "bob:2")

        self.assertEqual(resolved.state.objects["bob:1"].zone, "battlefield")
        self.assertEqual(resolved.state.objects["bob:2"].zone, "graveyard")

    def test_owl_familiar_draws_before_chosen_discard(self) -> None:
        state = self._state(
            OWL_FAMILIAR,
            alice_cards=(GRIZZLY_BEARS, MUCK_RATS),
            alice_opening=2,
        )
        pending = self._request(state, OWL_FAMILIAR)

        self.assertEqual(set(pending.state.pending_decision.option_ids), {"alice:2", "alice:3"})
        resolved = self._choose(pending, "alice:2")
        self.assertEqual(resolved.state.objects["alice:2"].zone, "graveyard")
        self.assertEqual(resolved.state.objects["alice:3"].zone, "hand")

    def test_player_scope_choices_are_explicit_and_redacted(self) -> None:
        ebon = self._request(
            self._state(EBON_DRAGON, bob_cards=(GRIZZLY_BEARS,)),
            EBON_DRAGON,
        )
        self.assertEqual(ebon.state.pending_decision.option_scope, "player")
        self.assertEqual(ebon.state.pending_decision.option_ids, ("bob",))
        declined = self._choose(ebon)
        self.assertEqual(declined.state.objects["bob:1"].zone, "hand")

        thief = self._request(
            self._state(INGENIOUS_THIEF, bob_cards=(GRIZZLY_BEARS,)),
            INGENIOUS_THIEF,
        )
        inspected = self._choose(thief, "bob")
        event = next(e for e in inspected.event_log if e.event_type == "hand_looked_at")
        self.assertEqual(event.payload["target_player_id"], "bob")
        self.assertNotIn("card_instance_ids", event.payload)

    def test_ebon_dragon_opponent_chooses_non_first_discard(self) -> None:
        pending_target = self._request(
            self._state(
                EBON_DRAGON,
                bob_cards=(GRIZZLY_BEARS, MUCK_RATS),
            ),
            EBON_DRAGON,
        )
        pending_discard = self._choose(pending_target, "bob")

        decision = pending_discard.state.pending_decision
        self.assertEqual(decision.chooser_id, "bob")
        self.assertEqual(decision.option_ids, ("bob:1", "bob:2"))
        self.assertEqual(
            {
                action.selected_instance_ids
                for action in enumerate_legal_actions(
                    pending_discard.state, self.repo
                )
            },
            {("bob:1",), ("bob:2",)},
        )

        resolved = self._choose_as(pending_discard, "bob", "bob:2")
        self.assertEqual(resolved.state.objects["bob:1"].zone, "hand")
        self.assertEqual(resolved.state.objects["bob:2"].zone, "graveyard")
        choice_event = [
            event for event in resolved.event_log
            if event.event_type == "choice_resolved"
        ][-1]
        self.assertNotIn("selected_instance_id", choice_event.payload)
        self.assertEqual(
            resolved.event_log[-1].event_type,
            "triggered_ability_resolved",
        )

    def test_noxious_toad_opponent_chooses_discard(self) -> None:
        pending = self._request(
            self._state(
                NOXIOUS_TOAD,
                bob_cards=(GRIZZLY_BEARS, MUCK_RATS),
            ),
            NOXIOUS_TOAD,
        )

        self.assertEqual(pending.state.pending_decision.chooser_id, "bob")
        resolved = self._choose_as(pending, "bob", "bob:2")
        self.assertEqual(resolved.state.objects["bob:1"].zone, "hand")
        self.assertEqual(resolved.state.objects["bob:2"].zone, "graveyard")

    def test_trigger_discard_rejects_reentered_hand_object(self) -> None:
        pending = self._request(
            self._state(NOXIOUS_TOAD, bob_cards=(GRIZZLY_BEARS,)),
            NOXIOUS_TOAD,
        )
        stale = move_object(
            pending.state,
            instance_id="bob:1",
            from_zone="hand",
            to_zone="graveyard",
            player_id="bob",
        )
        stale = move_object(
            stale,
            instance_id="bob:1",
            from_zone="graveyard",
            to_zone="hand",
            player_id="bob",
        )

        with self.assertRaisesRegex(ValueError, "expected hand object"):
            self._choose_as(replace(pending, state=stale), "bob", "bob:1")

    def test_wave7_trigger_discards_skip_empty_hands(self) -> None:
        ebon_target = self._request(self._state(EBON_DRAGON), EBON_DRAGON)
        ebon_resolved = self._choose(ebon_target, "bob")
        self.assertIsNone(ebon_resolved.state.pending_decision)
        self.assertEqual(
            ebon_resolved.event_log[-1].event_type,
            "triggered_ability_resolved",
        )

        toad_resolved = self._request(
            self._state(NOXIOUS_TOAD),
            NOXIOUS_TOAD,
        )
        self.assertIsNone(toad_resolved.state.pending_decision)
        self.assertEqual(
            toad_resolved.event_log[-1].event_type,
            "triggered_ability_resolved",
        )

    def test_primeval_force_requires_exactly_three_distinct_forests(self) -> None:
        state = self._state(PRIMEVAL_FORCE, alice_cards=(FOREST,) * 4)
        for instance_id in ("alice:2", "alice:3", "alice:4", "alice:5"):
            state = move_object(
                state, instance_id=instance_id, from_zone="hand",
                to_zone="battlefield", player_id="alice",
            )
        pending = self._request(state, PRIMEVAL_FORCE)
        actions = {
            len(action.selected_instance_ids)
            for action in enumerate_legal_actions(pending.state, self.repo)
        }
        self.assertEqual(actions, {0, 3})

        resolved = self._choose(pending, "alice:3", "alice:4", "alice:5")
        self.assertEqual(resolved.state.objects["alice:2"].zone, "battlefield")
        self.assertTrue(all(resolved.state.objects[i].zone == "graveyard" for i in ("alice:3", "alice:4", "alice:5")))
        self.assertEqual(resolved.state.objects["alice:1"].zone, "battlefield")

    def test_declined_and_unavailable_payment_sacrifices_source(self) -> None:
        declined_state = self._state(PLANT_ELEMENTAL, alice_cards=(FOREST,))
        declined_state = move_object(
            declined_state, instance_id="alice:2", from_zone="hand",
            to_zone="battlefield", player_id="alice",
        )
        declined = self._choose(self._request(declined_state, PLANT_ELEMENTAL))
        self.assertEqual(declined.state.objects["alice:1"].zone, "graveyard")
        self.assertEqual(declined.state.objects["alice:2"].zone, "battlefield")

        unavailable = self._choose(
            self._request(self._state(PLANT_ELEMENTAL), PLANT_ELEMENTAL)
        )
        self.assertEqual(unavailable.state.objects["alice:1"].zone, "graveyard")

    def test_stale_target_does_not_affect_reentered_object(self) -> None:
        state = self._state(FIRE_IMP, bob_cards=(GRIZZLY_BEARS,))
        state = move_object(
            state, instance_id="bob:1", from_zone="hand",
            to_zone="battlefield", player_id="bob",
        )
        pending = self._request(state, FIRE_IMP)
        stale = move_object(
            pending.state, instance_id="bob:1", from_zone="battlefield",
            to_zone="hand", player_id="bob",
        )
        stale = move_object(
            stale, instance_id="bob:1", from_zone="hand",
            to_zone="battlefield", player_id="bob",
        )
        resolved = self._choose(replace(pending, state=stale), "bob:1")
        self.assertEqual(resolved.state.objects["bob:1"].zone, "battlefield")
        self.assertEqual(resolved.state.objects["bob:1"].damage_marked, 0)

    def test_each_remaining_target_family_requests_an_explicit_choice(self) -> None:
        for source_id, extra, target_id, optional in (
            (FIRE_DRAGON, GRIZZLY_BEARS, "bob:1", False),
            (MAN_O_WAR, GRIZZLY_BEARS, "bob:1", False),
            (FIRE_SNAKE, FOREST, "bob:1", False),
            (SEASONED_MARSHAL, GRIZZLY_BEARS, "bob:1", True),
            (SERPENT_ASSASSIN, GRIZZLY_BEARS, "bob:1", True),
        ):
            with self.subTest(source_id=source_id):
                state = self._state(source_id, bob_cards=(extra,))
                state = move_object(
                    state, instance_id=target_id, from_zone="hand",
                    to_zone="battlefield", player_id="bob",
                )
                pending = self._request(state, source_id)
                decision = pending.state.pending_decision
                self.assertIn(target_id, decision.option_ids)
                self.assertEqual(decision.min_selections, 0 if optional else 1)

    def test_each_single_payment_family_can_pay_a_non_first_option(self) -> None:
        cases = (
            (MERCENARY_KNIGHT, GRIZZLY_BEARS, "hand"),
            (THUNDERING_WURM, FOREST, "hand"),
            (PLANT_ELEMENTAL, FOREST, "battlefield"),
            (THING_FROM_THE_DEEP, ISLAND, "battlefield"),
        )
        for source_id, payment_id, payment_zone in cases:
            with self.subTest(source_id=source_id):
                state = self._state(source_id, alice_cards=(payment_id, payment_id))
                if payment_zone == "battlefield":
                    for instance_id in ("alice:2", "alice:3"):
                        state = move_object(
                            state, instance_id=instance_id, from_zone="hand",
                            to_zone="battlefield", player_id="alice",
                        )
                pending = self._request(state, source_id)
                resolved = self._choose(pending, "alice:3")
                self.assertEqual(resolved.state.objects["alice:1"].zone, "battlefield")
                self.assertEqual(resolved.state.objects["alice:2"].zone, payment_zone)
                self.assertEqual(resolved.state.objects["alice:3"].zone, "graveyard")

    def test_stale_payment_is_unpaid_without_sacrificing_partial_options(self) -> None:
        state = self._state(PLANT_ELEMENTAL, alice_cards=(FOREST,))
        state = move_object(
            state, instance_id="alice:2", from_zone="hand",
            to_zone="battlefield", player_id="alice",
        )
        pending = self._request(state, PLANT_ELEMENTAL)
        stale = move_object(
            pending.state, instance_id="alice:2", from_zone="battlefield",
            to_zone="hand", player_id="alice",
        )
        stale = move_object(
            stale, instance_id="alice:2", from_zone="hand",
            to_zone="battlefield", player_id="alice",
        )
        resolved = self._choose(replace(pending, state=stale), "alice:2")
        self.assertEqual(resolved.state.objects["alice:1"].zone, "graveyard")
        self.assertEqual(resolved.state.objects["alice:2"].zone, "battlefield")

    def test_wood_elves_non_first_search_and_decline_both_shuffle(self) -> None:
        state = self._state(
            WOOD_ELVES,
            alice_cards=(FOREST, GRIZZLY_BEARS, FOREST),
            alice_opening=1,
        )
        selected = self._choose(self._request(state, WOOD_ELVES), "alice:4")
        self.assertEqual(selected.state.objects["alice:4"].zone, "battlefield")
        self.assertEqual(selected.state.rng_cursor, 1)

        repeated = self._state(
            WOOD_ELVES,
            alice_cards=(FOREST, GRIZZLY_BEARS, FOREST),
            alice_opening=1,
        )
        declined = self._choose(self._request(repeated, WOOD_ELVES))
        self.assertEqual(declined.state.rng_cursor, 1)
        self.assertTrue(all(declined.state.objects[i].zone == "library" for i in ("alice:2", "alice:4")))

    def test_same_setup_and_accepted_choice_reproduce_state_and_events(self) -> None:
        results = []
        for _ in range(2):
            state = self._state(
                WOOD_ELVES,
                alice_cards=(FOREST, GRIZZLY_BEARS, FOREST),
                alice_opening=1,
            )
            pending = self._request(state, WOOD_ELVES)
            results.append(self._choose(pending, "alice:4"))

        self.assertEqual(results[0].state, results[1].state)
        self.assertEqual(results[0].event_log, results[1].event_log)


if __name__ == "__main__":
    unittest.main()

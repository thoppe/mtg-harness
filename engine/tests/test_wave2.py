from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mtg_engine.actions.models import (
    ActivateManaAbilityAction,
    CastNonCreatureSpellAction,
)
from mtg_engine.cards.repository import CardRepository
from mtg_engine.flow.priority import enumerate_legal_actions
from mtg_engine.flow.setup import SetupInput, initialize_game
from mtg_engine.flow.turns import (
    TurnResult,
    _resolve_noncreature_spell,
    activate_mana_ability,
    start_first_turn,
)
from mtg_engine.rules.characteristics import (
    effective_power,
    effective_toughness,
    has_keyword,
    only_blockable_by_colors,
)
from mtg_engine.state.models import StackEntry
from mtg_engine.state.zones import move_object


INFORMATION_DIR = Path(__file__).resolve().parents[2] / "information"
PLAINS = "bc71ebf6-2056-41f7-be35-b2e5c34afa99"
ISLAND = "b2c6aa39-2d2a-459c-a555-fb48ba993373"
FOREST = "b34bb2dc-c1af-4d77-b0b3-a0fb342a5fc6"
FOOT_SOLDIERS = "a768ba13-4d1c-4dce-a4a6-86a39c069c3f"
MUCK_RATS = "bca13a12-6723-4a5e-8f1b-21646a8b3e7e"
ANACONDA = "3eff03f1-2c5f-4c59-b465-a8c4cd05e1ba"
ALLURING_SCENT = "ad218276-a44b-4a61-8e42-26a27929bbbb"
ANGELIC_BLESSING = "d3758fca-0522-4b5a-a1cc-3b2b3ab299ba"
CLOAK_OF_FEATHERS = "cb4baf53-51ed-468b-a468-5d7d45a6dc26"
STEADFASTNESS = "8f8dfc24-f466-4607-8991-acbcbb415db3"
WARRIORS_CHARGE = "5cf28c04-76af-4eb8-9969-366dc8e04690"
VALOROUS_CHARGE = "1f51fea2-ce19-44ef-a330-65cc0fafcd64"
NATURES_CLOAK = "bb493c95-5f6d-405b-aac6-c56fe6b6f42f"
DREAD_CHARGE = "6b7933b3-821a-4d64-9a10-af8a69fa008e"


class Wave2Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.repository = CardRepository.from_information_directory(INFORMATION_DIR)

    def test_targeted_wave_two_sorceries_are_enumerated_for_creatures(self) -> None:
        spells = (ANGELIC_BLESSING, CLOAK_OF_FEATHERS, ALLURING_SCENT)
        mana_sources = (PLAINS, PLAINS, ISLAND, FOREST, FOREST)
        state = initialize_game(
            SetupInput(
                "wave2-target-enumeration",
                ("alice", "bob"),
                "alice",
                {
                    "alice": spells + (MUCK_RATS,) + mana_sources,
                    "bob": (PLAINS,),
                },
                {
                    "alice": spells + (MUCK_RATS,) + mana_sources,
                    "bob": (PLAINS,),
                },
                21,
            ),
            self.repository,
        ).state
        state = move_object(
            state,
            instance_id="alice:4",
            from_zone="hand",
            to_zone="battlefield",
            player_id="alice",
        )
        for source_instance_id in ("alice:5", "alice:6", "alice:7", "alice:8", "alice:9"):
            state = move_object(
                state,
                instance_id=source_instance_id,
                from_zone="hand",
                to_zone="battlefield",
                player_id="alice",
            )
        session = start_first_turn(TurnResult(state, ()))
        for source_instance_id in ("alice:5", "alice:6", "alice:7", "alice:8", "alice:9"):
            session = activate_mana_ability(
                session,
                ActivateManaAbilityAction(
                    player_id="alice",
                    source_instance_id=source_instance_id,
                ),
                self.repository,
            )

        actions = enumerate_legal_actions(session.state, self.repository)

        for spell_instance_id in ("alice:1", "alice:2", "alice:3"):
            self.assertIn(
                CastNonCreatureSpellAction(
                    player_id="alice",
                    card_instance_id=spell_instance_id,
                    target_instance_id="alice:4",
                ),
                actions,
            )

    def test_targeted_wave_two_effects_resolve(self) -> None:
        state = self._stacked_targeted_spell(
            ANGELIC_BLESSING,
            library_tail=(),
        )
        power_before = effective_power(state, self.repository, "alice:2")
        toughness_before = effective_toughness(state, self.repository, "alice:2")

        blessing = _resolve_noncreature_spell(
            TurnResult(state, ()),
            StackEntry("alice:1", "alice", ("alice:2",)),
            self.repository,
        )

        self.assertEqual(
            effective_power(blessing.state, self.repository, "alice:2"),
            power_before + 3,
        )
        self.assertEqual(
            effective_toughness(blessing.state, self.repository, "alice:2"),
            toughness_before + 3,
        )
        self.assertTrue(
            has_keyword(blessing.state, self.repository, "alice:2", "Flying")
        )

        state = self._stacked_targeted_spell(
            CLOAK_OF_FEATHERS,
            library_tail=(PLAINS,),
        )
        cloak = _resolve_noncreature_spell(
            TurnResult(state, ()),
            StackEntry("alice:1", "alice", ("alice:2",)),
            self.repository,
        )

        self.assertTrue(
            has_keyword(cloak.state, self.repository, "alice:2", "Flying")
        )
        self.assertEqual(cloak.state.players["alice"].hand, ("alice:3",))

    def test_controlled_mass_modifiers_do_not_affect_opponents(self) -> None:
        for spell_id, power_delta, toughness_delta in (
            (STEADFASTNESS, 0, 3),
            (WARRIORS_CHARGE, 1, 1),
        ):
            with self.subTest(spell_id=spell_id):
                state = self._stacked_mass_spell(
                    spell_id,
                    friendly_creature=MUCK_RATS,
                    opposing_creature=MUCK_RATS,
                )
                friendly_before = (
                    effective_power(state, self.repository, "alice:2"),
                    effective_toughness(state, self.repository, "alice:2"),
                )
                opposing_before = (
                    effective_power(state, self.repository, "bob:1"),
                    effective_toughness(state, self.repository, "bob:1"),
                )

                resolved = _resolve_noncreature_spell(
                    TurnResult(state, ()),
                    StackEntry("alice:1", "alice"),
                    self.repository,
                ).state

                self.assertEqual(
                    (
                        effective_power(resolved, self.repository, "alice:2"),
                        effective_toughness(resolved, self.repository, "alice:2"),
                    ),
                    (
                        friendly_before[0] + power_delta,
                        friendly_before[1] + toughness_delta,
                    ),
                )
                self.assertEqual(
                    (
                        effective_power(resolved, self.repository, "bob:1"),
                        effective_toughness(resolved, self.repository, "bob:1"),
                    ),
                    opposing_before,
                )

    def test_valorous_charge_affects_white_creatures_on_both_sides(self) -> None:
        state = self._stacked_mass_spell(
            VALOROUS_CHARGE,
            friendly_creature=FOOT_SOLDIERS,
            opposing_creature=FOOT_SOLDIERS,
        )
        friendly_before = effective_power(state, self.repository, "alice:2")
        opposing_before = effective_power(state, self.repository, "bob:1")

        resolved = _resolve_noncreature_spell(
            TurnResult(state, ()),
            StackEntry("alice:1", "alice"),
            self.repository,
        ).state

        self.assertEqual(
            effective_power(resolved, self.repository, "alice:2"),
            friendly_before + 2,
        )
        self.assertEqual(
            effective_power(resolved, self.repository, "bob:1"),
            opposing_before + 2,
        )

    def test_color_filtered_evasion_modifiers_affect_only_controlled_creatures(
        self,
    ) -> None:
        state = self._stacked_mass_spell(
            NATURES_CLOAK,
            friendly_creature=ANACONDA,
            opposing_creature=ANACONDA,
        )
        forestwalk = _resolve_noncreature_spell(
            TurnResult(state, ()),
            StackEntry("alice:1", "alice"),
            self.repository,
        ).state
        self.assertTrue(
            has_keyword(forestwalk, self.repository, "alice:2", "Forestwalk")
        )
        self.assertFalse(
            has_keyword(forestwalk, self.repository, "bob:1", "Forestwalk")
        )

        state = self._stacked_mass_spell(
            DREAD_CHARGE,
            friendly_creature=MUCK_RATS,
            opposing_creature=MUCK_RATS,
        )
        dread = _resolve_noncreature_spell(
            TurnResult(state, ()),
            StackEntry("alice:1", "alice"),
            self.repository,
        ).state
        self.assertEqual(only_blockable_by_colors(dread, "alice:2"), ("B",))
        self.assertEqual(only_blockable_by_colors(dread, "bob:1"), ())

    def _stacked_targeted_spell(
        self,
        spell_id: str,
        *,
        library_tail: tuple[str, ...],
    ):
        library = (spell_id, MUCK_RATS) + library_tail
        state = initialize_game(
            SetupInput(
                f"wave2-target-{spell_id}",
                ("alice", "bob"),
                "alice",
                {"alice": library, "bob": (PLAINS,)},
                {"alice": (spell_id, MUCK_RATS), "bob": (PLAINS,)},
                22,
            ),
            self.repository,
        ).state
        state = move_object(
            state,
            instance_id="alice:2",
            from_zone="hand",
            to_zone="battlefield",
            player_id="alice",
        )
        return move_object(
            state,
            instance_id="alice:1",
            from_zone="hand",
            to_zone="stack",
            player_id="alice",
        )

    def _stacked_mass_spell(
        self,
        spell_id: str,
        *,
        friendly_creature: str,
        opposing_creature: str,
    ):
        state = initialize_game(
            SetupInput(
                f"wave2-mass-{spell_id}",
                ("alice", "bob"),
                "alice",
                {
                    "alice": (spell_id, friendly_creature),
                    "bob": (opposing_creature,),
                },
                {
                    "alice": (spell_id, friendly_creature),
                    "bob": (opposing_creature,),
                },
                23,
            ),
            self.repository,
        ).state
        state = move_object(
            state,
            instance_id="alice:2",
            from_zone="hand",
            to_zone="battlefield",
            player_id="alice",
        )
        state = move_object(
            state,
            instance_id="bob:1",
            from_zone="hand",
            to_zone="battlefield",
            player_id="bob",
        )
        return move_object(
            state,
            instance_id="alice:1",
            from_zone="hand",
            to_zone="stack",
            player_id="alice",
        )


if __name__ == "__main__":
    unittest.main()

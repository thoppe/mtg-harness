"""Named, deterministic rules-harness states for interactive terminal play.

These are deliberately *not* deck fixtures.  They begin at a compact,
interesting decision point so a CLI can demonstrate the same player-scoped
legal-actions surface used by a full game.  In particular, the Rain of
Daggers entry is explicitly a rules-harness-only scenario and must never be
used to construct a Portal deck.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Literal

from mtg_engine.cards.repository import CardRepository
from mtg_engine.flow.setup import SetupInput
from mtg_engine.services.session import GameSession
from mtg_engine.state.models import (
    CombatState,
    DelayedTurnEffect,
    PendingDecision,
    StackEntry,
    TemporaryEffect,
    TurnState,
)
from mtg_engine.state.zones import move_object


# Keep card references local to this rules-harness catalog.  The support-slice
# manifest remains the authority for what is supported and deck eligible.
ASSASSINS_BLADE = "76da2150-34b9-4483-99df-131e1c5468d5"
CHARGING_RHINO = "26966ecb-15d3-47e5-ab63-e38510c87ecc"
FORKED_LIGHTNING = "66107cfd-4bdb-4266-a650-940743555ea4"
GRIZZLY_BEARS = "14c8f55d-d177-4c25-a931-ebeb9e6062a0"
MYSTIC_DENIAL = "d2bd23a6-4f77-4d6e-bf8f-339cb7a4184d"
MUCK_RATS = "bca13a12-6723-4a5e-8f1b-21646a8b3e7e"
RAIN_OF_DAGGERS = "e2048201-6dc9-4cf5-916f-1d867ae8dbdd"
VOLCANIC_HAMMER = "98fa5a06-0553-40fd-999c-bc31c9b3f4db"
PLAINS = "bc71ebf6-2056-41f7-be35-b2e5c34afa99"

# Scenarios begin at a specific decision point, but remain live games rather
# than one-action demonstrations.  This deterministic tail keeps a player
# from losing their very next turn solely because the fixture's opening hand
# consumed its entire library.
SCENARIO_LIBRARY_TAIL = (
    PLAINS,
    GRIZZLY_BEARS,
    PLAINS,
    GRIZZLY_BEARS,
    PLAINS,
    GRIZZLY_BEARS,
    PLAINS,
    GRIZZLY_BEARS,
)


@dataclass(frozen=True)
class MidgameScenario:
    """A compact starting point for a live, player-facing action exercise."""

    name: str
    description: str
    # Every entry intentionally uses exact setup rather than a validated deck
    # game.  A launcher must label it as a rules harness, never a legal-deck
    # start, even when it contains Portal-eligible cards only.
    category: Literal["legal_deck", "rules_harness"] = "rules_harness"
    rules_harness_only: bool = False


_SCENARIOS = (
    MidgameScenario(
        "combat-attackers",
        "Alice chooses attackers while Bob has creatures ready to block.",
    ),
    MidgameScenario(
        "combat-blockers",
        "Bob assigns two blockers after Alice attacks with a Charging Rhino.",
    ),
    MidgameScenario(
        "forked-lightning-targets",
        "Alice chooses one or more creature targets and divides four damage.",
    ),
    MidgameScenario(
        "mystic-denial-response",
        "Bob receives priority with a sorcery on the stack and may counter it.",
    ),
    MidgameScenario(
        "private-choice",
        "Only Alice can resolve a bounded private card-selection decision.",
    ),
    MidgameScenario(
        "cleanup-expiry",
        "Alice advances a completed combat so temporary and turn effects expire at cleanup.",
    ),
    MidgameScenario(
        "rain-of-daggers-harness",
        "Rules-harness-only mass-destruction testbed; it is not a Portal deck scenario.",
        rules_harness_only=True,
    ),
)


def list_midgame_scenarios() -> tuple[MidgameScenario, ...]:
    """Return stable scenario metadata suitable for a launcher or help screen."""
    return _SCENARIOS


def create_midgame_session(card_repository: CardRepository, name: str) -> GameSession:
    """Build a fresh session positioned at named scenario's first decision.

    ``name`` must be one returned by :func:`list_midgame_scenarios`; an
    unknown name fails loudly at the launcher boundary rather than selecting a
    surprising fallback state.
    """
    builders = {
        "combat-attackers": _combat_attackers,
        "combat-blockers": _combat_blockers,
        "forked-lightning-targets": _forked_lightning_targets,
        "mystic-denial-response": _mystic_denial_response,
        "private-choice": _private_choice,
        "cleanup-expiry": _cleanup_expiry,
        "rain-of-daggers-harness": _rain_of_daggers_harness,
    }
    try:
        return builders[name](card_repository)
    except KeyError as error:
        known = ", ".join(scenario.name for scenario in _SCENARIOS)
        raise ValueError(f"unknown mid-game scenario {name!r}; choose one of: {known}") from error


def _session(card_repository: CardRepository, game_id: str, alice: tuple[str, ...], bob: tuple[str, ...]) -> GameSession:
    setup = SetupInput(
        game_id=game_id,
        players=("alice", "bob"),
        starting_player="alice",
        libraries={
            "alice": alice + SCENARIO_LIBRARY_TAIL,
            "bob": bob + SCENARIO_LIBRARY_TAIL,
        },
        opening_hands={"alice": alice, "bob": bob},
        rng_seed=501,
    )
    return GameSession.from_setup(setup, card_repository)


def _to_battlefield(state, player_id: str, *instance_ids: str):
    for instance_id in instance_ids:
        state = move_object(
            state, instance_id=instance_id, from_zone="hand", to_zone="battlefield", player_id=player_id,
        )
    return state


def _midgame_turn(state, *, active_player: str = "alice", priority_player: str | None = None, step: str = "precombat_main_step"):
    return replace(
        state,
        turn=TurnState(5, active_player, priority_player or active_player, step),
        objects={
            instance_id: replace(card, entered_battlefield_turn=3)
            if card.zone == "battlefield" else card
            for instance_id, card in state.objects.items()
        },
    )


def _with_state(session: GameSession, state) -> GameSession:
    session.result = replace(session.result, state=state)
    return session


def _combat_attackers(card_repository: CardRepository) -> GameSession:
    session = _session(
        card_repository, "scenario-combat-attackers",
        (CHARGING_RHINO, GRIZZLY_BEARS), (GRIZZLY_BEARS, MUCK_RATS),
    )
    state = _to_battlefield(session.state, "alice", "alice:1", "alice:2")
    state = _to_battlefield(state, "bob", "bob:1", "bob:2")
    state = _midgame_turn(state, step="declare_attackers_step")
    return _with_state(session, state)


def _combat_blockers(card_repository: CardRepository) -> GameSession:
    session = _combat_attackers(card_repository)
    state = replace(
        session.state,
        combat=CombatState("alice", "bob", ("alice:1",), {}, was_attacked=True),
        turn=TurnState(5, "alice", "bob", "declare_blockers_step"),
    )
    return _with_state(session, state)


def _forked_lightning_targets(card_repository: CardRepository) -> GameSession:
    session = _session(
        card_repository, "scenario-forked-lightning",
        (FORKED_LIGHTNING, MUCK_RATS), (GRIZZLY_BEARS, MUCK_RATS),
    )
    state = _to_battlefield(session.state, "bob", "bob:1", "bob:2")
    state = _midgame_turn(state)
    state = replace(state, players={
        **state.players,
        "alice": replace(state.players["alice"], mana_pool=("R", "R", "R", "R")),
    })
    return _with_state(session, state)


def _mystic_denial_response(card_repository: CardRepository) -> GameSession:
    session = _session(
        card_repository, "scenario-mystic-denial",
        (VOLCANIC_HAMMER,), (MYSTIC_DENIAL,),
    )
    state = move_object(
        session.state, instance_id="alice:1", from_zone="hand", to_zone="stack", player_id="alice",
    )
    hammer = state.objects["alice:1"]
    state = _midgame_turn(state, priority_player="bob")
    state = replace(
        state,
        stack_entries=(StackEntry(
            card_instance_id="alice:1", controller_id="alice", target_ids=("bob",),
            source_object_id=hammer.object_id, source_oracle_id=VOLCANIC_HAMMER,
        ),),
        players={
            **state.players,
            "bob": replace(state.players["bob"], mana_pool=("U", "U", "U")),
        },
    )
    return _with_state(session, state)


def _private_choice(card_repository: CardRepository) -> GameSession:
    session = _session(
        card_repository, "scenario-private-choice",
        (GRIZZLY_BEARS, MUCK_RATS, VOLCANIC_HAMMER), (GRIZZLY_BEARS,),
    )
    state = _midgame_turn(session.state)
    state = replace(state, pending_decision=PendingDecision(
        decision_id="scenario:private-choice",
        chooser_id="alice",
        kind="any_number",
        source_object_id=state.objects["alice:1"].object_id,
        option_ids=("alice:2", "alice:3"),
        min_selections=0,
        max_selections=2,
    ))
    return _with_state(session, state)


def _cleanup_expiry(card_repository: CardRepository) -> GameSession:
    session = _session(
        card_repository, "scenario-cleanup-expiry",
        (GRIZZLY_BEARS,), (MUCK_RATS,),
    )
    state = _to_battlefield(session.state, "alice", "alice:1")
    state = _to_battlefield(state, "bob", "bob:1")
    state = _midgame_turn(state, step="combat_damage_step")
    alice = state.objects["alice:1"]
    state = replace(
        state,
        combat=CombatState("alice", "bob", ("alice:1",), {"alice:1": ("bob:1",)}, was_attacked=True),
        delayed_turn_effects=(DelayedTurnEffect(
            kind="prevent_attacking_damage", player_id="alice", turn_number=5, source_player_id="alice",
        ),),
        temporary_effects=(TemporaryEffect(
            source_object_id=alice.object_id, target_object_ids=(alice.object_id,), power_delta=3, toughness_delta=3,
        ),),
    )
    return _with_state(session, state)


def _rain_of_daggers_harness(card_repository: CardRepository) -> GameSession:
    session = _session(
        card_repository, "scenario-rain-of-daggers-harness",
        (RAIN_OF_DAGGERS,), (GRIZZLY_BEARS, MUCK_RATS),
    )
    state = _to_battlefield(session.state, "bob", "bob:1", "bob:2")
    state = _midgame_turn(state)
    state = replace(state, players={
        **state.players,
        "alice": replace(state.players["alice"], mana_pool=("B", "B", "B", "B", "B", "B")),
    })
    return _with_state(session, state)

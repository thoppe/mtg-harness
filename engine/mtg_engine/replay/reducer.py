"""Executable reducer for the v0 accepted-action surface."""

from __future__ import annotations

from dataclasses import dataclass

from mtg_engine.actions.dispatch import AcceptedAction, dispatch_action
from mtg_engine.cards.repository import CardRepository
from mtg_engine.flow.setup import SetupInput, initialize_game
from mtg_engine.flow.turns import TurnResult, start_first_turn


@dataclass(frozen=True)
class ReplayInput:
    setup: SetupInput
    actions: tuple[AcceptedAction, ...]
    start_first_turn: bool = True


def replay(input: ReplayInput, card_repository: CardRepository) -> TurnResult:
    """Recompute a game from setup and its ordered, accepted actions.

    Validation is delegated to the same transition functions that accepted the
    original actions, so malformed or out-of-order logs fail instead of being
    interpreted permissively.
    """
    session: TurnResult | object = initialize_game(input.setup, card_repository)
    if input.start_first_turn:
        session = start_first_turn(session)  # type: ignore[arg-type]

    for action in input.actions:
        if isinstance(session, TurnResult) and session.state.outcome.status == "completed":
            raise ValueError("cannot replay an action after the game has completed")
        session = dispatch_action(session, action, card_repository)

    if not isinstance(session, TurnResult):
        raise ValueError("replay did not enter a turn")
    return session

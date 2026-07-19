"""Executable reducer for the v0 accepted-action surface."""

from __future__ import annotations

from dataclasses import dataclass

from mtg_engine.actions.models import (
    ActivateManaAbilityAction,
    ActivateAbilityAction,
    AdvanceStepAction,
    CastCreatureSpellAction,
    CastNonCreatureSpellAction,
    DeclareAttackersAction,
    DeclareBlockersAction,
    PassPriorityAction,
    PlayLandAction,
    ResolveChoiceAction,
)
from mtg_engine.cards.repository import CardRepository
from mtg_engine.flow.setup import SetupInput, initialize_game
from mtg_engine.flow.turns import (
    TurnResult,
    activate_mana_ability,
    activate_ability,
    advance_step,
    cast_creature_spell,
    cast_noncreature_spell,
    declare_attackers,
    declare_blockers,
    pass_priority,
    play_land,
    resolve_pending_choice,
    start_first_turn,
)

AcceptedAction = (
    PlayLandAction
    | ActivateManaAbilityAction
    | ActivateAbilityAction
    | CastCreatureSpellAction
    | CastNonCreatureSpellAction
    | PassPriorityAction
    | AdvanceStepAction
    | DeclareAttackersAction
    | DeclareBlockersAction
    | ResolveChoiceAction
)


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
        if isinstance(action, PlayLandAction):
            session = play_land(session, action, card_repository)
        elif isinstance(action, ActivateManaAbilityAction):
            session = activate_mana_ability(session, action, card_repository)
        elif isinstance(action, ActivateAbilityAction):
            session = activate_ability(session, action, card_repository)
        elif isinstance(action, CastCreatureSpellAction):
            session = cast_creature_spell(session, action, card_repository)
        elif isinstance(action, CastNonCreatureSpellAction):
            session = cast_noncreature_spell(session, action, card_repository)
        elif isinstance(action, PassPriorityAction):
            session = pass_priority(session, action, card_repository)
        elif isinstance(action, AdvanceStepAction):
            session = advance_step(session, action)
        elif isinstance(action, DeclareAttackersAction):
            session = declare_attackers(session, action, card_repository)
        elif isinstance(action, DeclareBlockersAction):
            session = declare_blockers(session, action, card_repository)
        elif isinstance(action, ResolveChoiceAction):
            session = resolve_pending_choice(session, action, card_repository)
        else:
            raise ValueError(f"unsupported replay action: {type(action).__name__}")

    if not isinstance(session, TurnResult):
        raise ValueError("replay did not enter a turn")
    return session

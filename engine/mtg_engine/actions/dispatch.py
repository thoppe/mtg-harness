"""The single transition dispatch used by live sessions and replay."""

from __future__ import annotations

from mtg_engine.actions.models import (ActivateAbilityAction, ActivateManaAbilityAction, AdvanceStepAction, AdvanceTurnAction, CastCreatureSpellAction, CastNonCreatureSpellAction, DeclareAttackersAction, DeclareBlockersAction, PassPriorityAction, PlayLandAction, ResolveChoiceAction)
from mtg_engine.cards.repository import CardRepository
from mtg_engine.flow.turns import (TurnResult, activate_ability, activate_mana_ability, advance_step, advance_turn, cast_creature_spell, cast_noncreature_spell, declare_attackers, declare_blockers, pass_priority, play_land, resolve_pending_choice)

AcceptedAction = PlayLandAction | ActivateManaAbilityAction | ActivateAbilityAction | CastCreatureSpellAction | CastNonCreatureSpellAction | PassPriorityAction | AdvanceStepAction | AdvanceTurnAction | DeclareAttackersAction | DeclareBlockersAction | ResolveChoiceAction


def dispatch_action(session: TurnResult, action: AcceptedAction, card_repository: CardRepository) -> TurnResult:
    """Apply one already-typed action through the authoritative transition."""
    if isinstance(action, PlayLandAction):
        return play_land(session, action, card_repository)
    if isinstance(action, ActivateManaAbilityAction):
        return activate_mana_ability(session, action, card_repository)
    if isinstance(action, ActivateAbilityAction):
        return activate_ability(session, action, card_repository)
    if isinstance(action, CastCreatureSpellAction):
        return cast_creature_spell(session, action, card_repository)
    if isinstance(action, CastNonCreatureSpellAction):
        return cast_noncreature_spell(session, action, card_repository)
    if isinstance(action, PassPriorityAction):
        return pass_priority(session, action, card_repository)
    if isinstance(action, AdvanceStepAction):
        return advance_step(session, action)
    if isinstance(action, AdvanceTurnAction):
        return advance_turn(session, action, card_repository)
    if isinstance(action, DeclareAttackersAction):
        return declare_attackers(session, action, card_repository)
    if isinstance(action, DeclareBlockersAction):
        return declare_blockers(session, action, card_repository)
    if isinstance(action, ResolveChoiceAction):
        return resolve_pending_choice(session, action, card_repository)
    raise ValueError(f"unsupported action: {type(action).__name__}")

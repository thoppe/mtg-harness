from __future__ import annotations

from typing import Iterable

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from mtg_engine.cards.repository import CardRepository
from mtg_engine.events.models import GameEvent
from mtg_engine.state.models import CardInstance, GameState


MANA_SYMBOLS = {
    "W": "W",
    "U": "U",
    "B": "B",
    "R": "R",
    "G": "G",
}


def print_game_snapshot(
    console: Console,
    state: GameState,
    card_repository: CardRepository,
    *,
    title: str,
) -> None:
    console.print(
        Panel(
            _build_turn_summary(state),
            title=title,
            border_style="blue",
        )
    )
    console.print(_build_player_summary_table(state))

    for player_id in state.players:
        console.print(_build_zone_table(state, card_repository, player_id, zone_name="battlefield"))
        console.print(_build_zone_table(state, card_repository, player_id, zone_name="hand"))
        console.print(_build_zone_table(state, card_repository, player_id, zone_name="graveyard"))

    if state.combat is not None:
        console.print(_build_combat_table(state, card_repository))


def print_action_plan(console: Console, title: str, steps: Iterable[str]) -> None:
    lines = [f"[bold cyan]{index}.[/bold cyan] {step}" for index, step in enumerate(steps, start=1)]
    console.print(Panel("\n".join(lines), title=title, border_style="green"))


def print_recent_events(
    console: Console,
    events: Iterable[GameEvent],
    card_repository: CardRepository,
    *,
    title: str,
    state: GameState | None = None,
) -> None:
    table = Table(title=title, header_style="bold magenta")
    table.add_column("#", justify="right")
    table.add_column("Event")
    table.add_column("Summary")

    for event in events:
        table.add_row(str(event.sequence), event.event_type, _summarize_event(event, card_repository, state))

    console.print(table)


def _build_turn_summary(state: GameState) -> str:
    return (
        f"Turn {state.turn.turn_number} | "
        f"Active player: {state.turn.active_player} | "
        f"Priority: {state.turn.priority_player} | "
        f"Step: {state.turn.step}"
    )


def _build_player_summary_table(state: GameState) -> Table:
    table = Table(title="Players", header_style="bold magenta")
    table.add_column("Player")
    table.add_column("Life", justify="right")
    table.add_column("Mana Pool")
    table.add_column("Library", justify="right")
    table.add_column("Hand", justify="right")
    table.add_column("Battlefield", justify="right")
    table.add_column("Graveyard", justify="right")

    for player_id, player in state.players.items():
        table.add_row(
            player_id,
            str(player.life_total),
            " ".join(MANA_SYMBOLS[symbol] for symbol in player.mana_pool) or "-",
            str(len(player.library)),
            str(len(player.hand)),
            str(len(player.battlefield)),
            str(len(player.graveyard)),
        )
    return table


def _build_zone_table(
    state: GameState,
    card_repository: CardRepository,
    player_id: str,
    *,
    zone_name: str,
) -> Table:
    player = state.players[player_id]
    zone_values = getattr(player, zone_name)
    table = Table(
        title=f"{player_id} {zone_name.replace('_', ' ').title()}",
        header_style="bold magenta",
    )
    table.add_column("Instance")
    table.add_column("Card")
    table.add_column("Status")

    if not zone_values:
        table.add_row("-", "-", "-")
        return table

    for instance_id in zone_values:
        table.add_row(
            instance_id,
            _card_title(state.objects[instance_id], card_repository),
            _card_status(state.objects[instance_id], card_repository),
        )
    return table


def _build_combat_table(state: GameState, card_repository: CardRepository) -> Table:
    combat = state.combat
    assert combat is not None

    table = Table(title="Combat", header_style="bold magenta")
    table.add_column("Attacker")
    table.add_column("Blockers")

    for attacker_id in combat.attackers:
        blocker_ids = combat.blockers.get(attacker_id, ())
        blockers = ", ".join(_card_title(state.objects[blocker_id], card_repository) for blocker_id in blocker_ids) or "-"
        table.add_row(_card_title(state.objects[attacker_id], card_repository), blockers)
    return table


def _card_title(card: CardInstance, card_repository: CardRepository) -> str:
    definition = card_repository.get(card.oracle_id)
    power_toughness = ""
    if definition.is_creature:
        power_toughness = f" ({definition.power}/{definition.toughness})"
    return f"{definition.name}{power_toughness}"


def _card_status(card: CardInstance, card_repository: CardRepository) -> str:
    definition = card_repository.get(card.oracle_id)
    parts = [card.zone]
    if card.tapped:
        parts.append("tapped")
    if definition.is_creature and card.damage_marked:
        parts.append(f"damage {card.damage_marked}")
    return ", ".join(parts)


def _summarize_event(
    event: GameEvent,
    card_repository: CardRepository,
    state: GameState | None,
) -> str:
    payload = event.payload
    if event.event_type == "attackers_declared":
        names = ", ".join(
            _event_card_name(card_repository, state, attacker_id, payload) for attacker_id in payload["attacker_ids"]
        )
        return f"{payload['player_id']} attacks with {names or 'no attackers'}"
    if event.event_type == "blockers_declared":
        if not payload["blockers"]:
            return f"{payload['player_id']} declares no blockers"
        assignments = []
        for attacker_id, blocker_ids in payload["blockers"].items():
            attacker_name = _event_card_name(card_repository, state, attacker_id, payload)
            blocker_names = ", ".join(
                _event_card_name(card_repository, state, blocker_id, payload) for blocker_id in blocker_ids
            )
            assignments.append(f"{blocker_names} blocks {attacker_name}")
        return "; ".join(assignments)
    if event.event_type == "combat_damage_assigned":
        attacker_name = _event_card_name(card_repository, state, payload["attacker_id"], payload)
        assignments = ", ".join(
            f"{assignment['attacker_damage']} to "
            f"{_event_card_name(card_repository, state, assignment['blocker_id'], payload)}"
            for assignment in payload["assignments"]
        )
        return f"{attacker_name} assigns {assignments}"
    if event.event_type == "combat_damage_applied":
        if "target_player_id" in payload:
            source_name = _event_card_name(card_repository, state, payload["source_instance_id"], payload)
            return f"{source_name} deals {payload['damage']} damage to {payload['target_player_id']}"
        attacker_name = _event_card_name(card_repository, state, payload["attacker_id"], payload)
        assignments = ", ".join(
            f"{assignment['attacker_damage']} to "
            f"{_event_card_name(card_repository, state, assignment['blocker_id'], payload)}"
            for assignment in payload["assignments"]
        )
        return f"{attacker_name} deals combat damage: {assignments}"
    if event.event_type == "state_based_actions_checked":
        destroyed_items = payload.get("destroyed", ())
        if not destroyed_items:
            return "SBA check destroys nothing"
        destroyed = ", ".join(
            _destroyed_summary(card_repository, state, item)
            for item in destroyed_items
        )
        return f"SBA check destroys {destroyed}"
    if event.event_type == "mana_added":
        mana = " ".join(payload.get("mana", ())) or "no mana"
        source_name = _event_card_name(card_repository, state, payload["source_instance_id"], payload)
        return f"{source_name} adds {mana}"
    if event.event_type == "spell_cast":
        spell_name = _event_card_name(card_repository, state, payload["card_instance_id"], payload)
        target_ids = payload.get("target_instance_ids", ())
        if not target_ids:
            return f"{spell_name} is cast"
        targets = ", ".join(_event_card_name(card_repository, state, target_id, payload) for target_id in target_ids)
        return f"{spell_name} is cast targeting {targets}"
    if event.event_type == "spell_resolved":
        spell_name = _event_card_name(card_repository, state, payload["card_instance_id"], payload)
        return f"{spell_name} resolves"
    if event.event_type == "permanent_destroyed":
        card_name = _card_name_from_oracle(card_repository, payload["oracle_id"])
        return f"{card_name} is destroyed for {_reason_text(payload)}"
    if event.event_type == "object_moved_between_zones":
        return f"{payload['card_instance_id']} moves {payload['from_zone']} -> {payload['to_zone']}"
    if event.event_type == "step_changed":
        return f"{payload['from_step']} -> {payload['to_step']}"
    if event.event_type == "life_total_changed":
        return f"{payload['player_id']} goes to {payload['life_total']} life"
    if event.event_type == "damage_applied":
        if "target_player_id" in payload:
            return f"{payload['target_player_id']} takes {payload['damage']} damage"
        target_name = _event_card_name(card_repository, state, payload["target_instance_id"], payload)
        return f"{target_name} takes {payload['damage']} damage"
    return str(payload)


def _event_card_name(
    card_repository: CardRepository,
    state: GameState | None,
    instance_id: str,
    payload: dict,
) -> str:
    if state is not None and instance_id in state.objects:
        oracle_id = state.objects[instance_id].oracle_id
        return f"{_card_name_from_oracle(card_repository, oracle_id)} [{instance_id}]"
    oracle_id = payload.get("oracle_id")
    if oracle_id is not None:
        return _card_name_from_oracle(card_repository, oracle_id)
    return instance_id


def _card_name_from_oracle(card_repository: CardRepository, oracle_id: str) -> str:
    return card_repository.get(oracle_id).name


def _destroyed_summary(card_repository: CardRepository, state: GameState | None, item: dict) -> str:
    card_name = _event_card_name(card_repository, state, item["card_instance_id"], item)
    return f"{card_name} for {_reason_text(item)}"


def _reason_text(payload: dict) -> str:
    if payload.get("reason") == "lethal_damage":
        return f"lethal damage ({payload['damage_marked']} >= {payload['toughness']})"
    if isinstance(payload.get("reason"), str) and payload["reason"].startswith("spell_effect:"):
        spell_name = payload["reason"].split(":", 1)[1]
        return f"{spell_name} resolving"
    return payload.get("reason", "an unspecified reason")

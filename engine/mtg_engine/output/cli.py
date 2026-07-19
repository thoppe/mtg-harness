"""Player-safe Rich presentation for the descriptor-driven terminal CLI.

This module is deliberately a renderer, not a second rules interface.  The
CLI hands it only the current player-scoped action and target projections.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Iterable

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from mtg_engine.services.legal_actions_api import LegalActionDescriptor, TargetCandidate

if TYPE_CHECKING:  # pragma: no cover - imported only for type checking
    from mtg_engine.services.legal_actions_api import LegalActionsResponse
    from mtg_engine.services.session import GameSession


class RichCliRenderer:
    """Render public state plus the priority player's own private hand."""

    def __init__(self, console: Console | None = None) -> None:
        self.console = console or Console()

    def message(self, value: str) -> None:
        self.console.print(value)

    def game_state(self, session: "GameSession", viewer_id: str) -> None:
        state = session.state
        turn = state.turn
        self.console.print(
            Panel(
                f"[bold]Turn {turn.turn_number}[/bold]  •  [cyan]{turn.step}[/cyan]\n"
                f"Active: [green]{turn.active_player}[/green]  •  "
                f"Priority: [bold yellow]{turn.priority_player}[/bold yellow]",
                title="[bold blue]Portal game[/bold blue]",
                border_style="blue",
            )
        )
        players = Table(title="Game status", header_style="bold magenta", expand=True)
        players.add_column("Player", style="bold")
        players.add_column("Life", justify="right")
        players.add_column("Mana")
        players.add_column("Library", justify="right")
        players.add_column("Hand")
        players.add_column("Graveyard", justify="right")
        players.add_column("Battlefield", justify="right")
        for player_id, player in state.players.items():
            mana = " ".join(player.mana_pool) or "-"
            hand = str(len(player.hand))
            if player_id != viewer_id:
                hand += " cards"
            players.add_row(
                player_id,
                str(player.life_total),
                mana,
                str(len(player.library)),
                hand,
                str(len(player.graveyard)),
                str(len(player.battlefield)),
            )
        self.console.print(players)
        self._battlefield(session)
        self._stack_and_combat(session)
        self._own_hand(session, viewer_id)
        self._recent_events(session)

    def actions(self, response: "LegalActionsResponse") -> None:
        table = Table(title="Your legal actions", header_style="bold green", expand=True)
        table.add_column("#", justify="right", style="bold cyan")
        table.add_column("Action", style="bold")
        table.add_column("Source")
        table.add_column("Needs")
        for index, action in enumerate(response.actions, start=1):
            table.add_row(
                str(index),
                action.kind,
                action.source.label if action.source is not None else "-",
                ", ".join(slot.name for slot in action.parameters) or "-",
            )
        self.console.print(table)

    def candidates(self, candidates: tuple[TargetCandidate, ...]) -> None:
        table = Table(title="Valid choices", header_style="bold yellow")
        table.add_column("#", justify="right", style="bold cyan")
        table.add_column("Candidate")
        for index, candidate in enumerate(candidates, start=1):
            # Candidate labels are the API's player-scoped display surface;
            # opaque candidate values and ids are intentionally never rendered.
            table.add_row(str(index), candidate.label)
        self.console.print(table)

    def _battlefield(self, session: "GameSession") -> None:
        state = session.state
        table = Table(title="Battlefield", header_style="bold green", expand=True)
        table.add_column("Controller", style="bold")
        table.add_column("Permanents")
        for player_id, player in state.players.items():
            permanents: list[str] = []
            for instance_id in player.battlefield:
                card = state.objects[instance_id]
                definition = session.card_repository.get(card.oracle_id)
                status: list[str] = []
                if card.tapped:
                    status.append("tapped")
                if card.damage_marked:
                    status.append(f"{card.damage_marked} damage")
                suffix = f" [dim]({', '.join(status)})[/dim]" if status else ""
                permanents.append(f"{definition.name}{suffix}")
            table.add_row(player_id, ", ".join(permanents) or "[dim]-[/dim]")
        self.console.print(table)

    def _own_hand(self, session: "GameSession", viewer_id: str) -> None:
        player = session.state.players[viewer_id]
        cards = [
            session.card_repository.get(session.state.objects[instance_id].oracle_id).name
            for instance_id in player.hand
        ]
        self.console.print(
            Panel(
                "  •  ".join(cards) or "[dim]Empty[/dim]",
                title=f"[bold cyan]{viewer_id}'s hand[/bold cyan]",
                border_style="cyan",
            )
        )

    def _stack_and_combat(self, session: "GameSession") -> None:
        """Render only public stack and combat facts when they are present."""
        state = session.state
        if state.stack_entries:
            entries = []
            for entry in state.stack_entries:
                card = state.objects[entry.card_instance_id]
                name = session.card_repository.get(card.oracle_id).name
                entries.append(f"{entry.controller_id}: {name}")
            self.console.print(Panel("\n".join(entries), title="Stack", border_style="yellow"))
        if state.combat is not None:
            assignments = []
            for attacker_id in state.combat.attackers:
                attacker = session.card_repository.get(state.objects[attacker_id].oracle_id).name
                blockers = state.combat.blockers.get(attacker_id, ())
                blocker_names = ", ".join(
                    session.card_repository.get(state.objects[blocker_id].oracle_id).name
                    for blocker_id in blockers
                ) or "unblocked"
                assignments.append(f"{attacker} → {blocker_names}")
            self.console.print(Panel("\n".join(assignments) or "No attackers", title="Combat", border_style="red"))

    def _recent_events(self, session: "GameSession") -> None:
        events: Iterable[object] = getattr(session.result, "event_log", ())[-6:]
        labels = [getattr(event, "event_type", "game event").replace("_", " ") for event in events]
        if labels:
            self.console.print(Panel("\n".join(f"• {label}" for label in labels), title="Recent events", border_style="magenta"))

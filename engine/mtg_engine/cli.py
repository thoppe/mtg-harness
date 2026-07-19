"""Small terminal loop for an already-created two-player game session.

This intentionally has no deck parsing policy.  Callers create a session from
validated decks (or explicit harness setup) and the CLI presents only the
current enumerated action list.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Callable

from mtg_engine.cards.repository import CardRepository
from mtg_engine.decks.models import DeckList
from mtg_engine.flow.deck_start import DeckGameInput
from mtg_engine.replay.serialization import write_replay_input
from mtg_engine.services.session import DeckGameSession, GameSession


Input = Callable[[str], str]
Output = Callable[[str], None]


def run_cli(
    session: GameSession,
    *,
    input_fn: Input = input,
    output: Output = print,
    replay_path: str | Path | None = None,
) -> None:
    """Run a numeric action loop without rendering either player's hand/library.

    Replay files contain the private setup required for deterministic replay;
    the terminal itself prints public counts, battlefield cards, and opaque
    instance identifiers only.
    """
    while session.state.outcome.status != "completed":
        _print_public_state(session, output)
        actions = session.legal_actions()
        if not actions:
            output("No enumerated legal actions; session stopped.")
            break
        for index, action in enumerate(actions, start=1):
            output(f"{index}. {_describe_action(action)}")
        raw = input_fn("Choose action number (q to quit): ").strip().lower()
        if raw in {"q", "quit", "exit"}:
            break
        try:
            choice = int(raw)
            if not 1 <= choice <= len(actions):
                raise ValueError
        except ValueError:
            output("Please enter one displayed action number or q.")
            continue
        session.submit(actions[choice - 1])

    if replay_path is not None:
        write_replay_input(replay_path, session.replay_input())
        output(f"Replay saved to {replay_path}")


def _print_public_state(session: GameSession, output: Output) -> None:
    state = session.state
    output(
        f"Turn {state.turn.turn_number}; {state.turn.step}; "
        f"active={state.turn.active_player}; priority={state.turn.priority_player}"
    )
    for player_id, player in state.players.items():
        battlefield = ", ".join(
            session.card_repository.get(state.objects[card_id].oracle_id).name
            for card_id in player.battlefield
        ) or "-"
        output(
            f"{player_id}: life={player.life_total}, library={len(player.library)}, "
            f"hand={len(player.hand)}, battlefield={battlefield}, graveyard={len(player.graveyard)}"
        )


def _describe_action(action: object) -> str:
    """Show opaque object identifiers, never card names from private zones."""
    fields = ", ".join(f"{name}={value}" for name, value in vars(action).items())
    return f"{type(action).__name__}({fields})"


def main(argv: list[str] | None = None) -> int:
    """Start a local Portal game from two JSON deck-list files.

    Sideboards are intentionally absent. During the opening procedure the
    current player sees that player's own hand in order to make a London
    mulligan choice; ordinary game rendering returns to public information.
    """
    parser = argparse.ArgumentParser(description="Play a local Portal deck game")
    parser.add_argument("--deck-a", required=True, help="JSON DeckList for player one")
    parser.add_argument("--deck-b", required=True, help="JSON DeckList for player two")
    parser.add_argument("--player-a", default="alice")
    parser.add_argument("--player-b", default="bob")
    parser.add_argument("--starting-player", default=None)
    parser.add_argument("--seed", required=True, type=int)
    parser.add_argument("--save", default=None, help="write private replay input after play")
    args = parser.parse_args(argv)

    def load_deck(path: str) -> DeckList:
        with Path(path).open(encoding="utf-8") as handle:
            return DeckList.from_payload(json.load(handle))

    repo_root = Path(__file__).resolve().parents[2]
    repository = CardRepository.from_information_directory(repo_root / "information")
    players = (args.player_a, args.player_b)
    starting_player = args.starting_player or args.player_a
    pregame = DeckGameSession.from_decks(
        DeckGameInput(
            game_id=f"cli-{args.seed}",
            players=players,
            starting_player=starting_player,
            decks={args.player_a: load_deck(args.deck_a), args.player_b: load_deck(args.deck_b)},
            rng_seed=args.seed,
        ),
        repository,
    )
    while pregame.state.mulligan is not None:
        player_id = pregame.state.mulligan.remaining_player_ids[0]
        player = pregame.state.players[player_id]
        print(f"{player_id}'s opening hand:")
        for index, instance_id in enumerate(player.hand, start=1):
            print(f"{index}. {repository.get(pregame.state.objects[instance_id].oracle_id).name}")
        choice = input("Keep or mulligan? [k/m] ").strip().lower()
        if choice == "m":
            pregame.take_mulligan(player_id)
            continue
        if choice not in {"", "k", "keep"}:
            print("Please enter k or m.")
            continue
        bottom_count = pregame.state.mulligan.count_for(player_id)
        bottom_ids: tuple[str, ...] = ()
        if bottom_count:
            raw = input(f"Choose {bottom_count} hand positions to bottom, in order: ").strip()
            try:
                positions = tuple(int(value) for value in raw.split())
                if len(positions) != bottom_count or len(set(positions)) != bottom_count:
                    raise ValueError
                bottom_ids = tuple(player.hand[position - 1] for position in positions)
            except (ValueError, IndexError):
                print("Use distinct displayed positions in the requested count.")
                continue
        pregame.keep_hand(player_id, bottom_ids)
    run_cli(pregame.start(), replay_path=args.save)
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised through installed script
    raise SystemExit(main())

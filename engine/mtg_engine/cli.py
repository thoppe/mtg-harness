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
from mtg_engine.flow.midgame_scenarios import create_midgame_session, list_midgame_scenarios
from mtg_engine.output.cli import RichCliRenderer
from mtg_engine.replay.serialization import write_replay_input
from mtg_engine.services.legal_actions_api import (
    LegalActionDescriptor,
    ParameterSlot,
    TargetCandidate,
)
from mtg_engine.services.session import DeckGameSession, GameSession, SessionRejection


Input = Callable[[str], str]
Output = Callable[[str], None]
CandidateOutput = Callable[[tuple[TargetCandidate, ...]], None]


def run_cli(
    session: GameSession,
    *,
    input_fn: Input = input,
    output: Output | None = None,
    replay_path: str | Path | None = None,
) -> None:
    """Run a descriptor-driven action loop without rendering hidden zones.

    Replay files contain the private setup required for deterministic replay;
    the terminal itself renders public state plus only the priority player's
    own hand; opaque instance identifiers are never used for selection.
    """
    renderer = RichCliRenderer() if output is None else None
    output = output or renderer.message
    candidate_output: CandidateOutput | None = renderer.candidates if renderer is not None else None
    while session.state.outcome.status != "completed":
        player_id = session.state.turn.priority_player
        if renderer is None:
            _print_public_state(session, output)
        else:
            renderer.game_state(session, player_id)
        response = session.legal_actions_api(player_id)
        if isinstance(response, SessionRejection):
            output(f"Could not load actions: {response.code}")
            break
        if not response.actions:
            output("No enumerated legal actions; session stopped.")
            break
        if renderer is None:
            for index, action in enumerate(response.actions, start=1):
                output(f"{index}. {_describe_action(action)}")
        else:
            renderer.actions(response)
        raw = input_fn("Choose action number (q to quit): ").strip().lower()
        if raw in {"q", "quit", "exit"}:
            break
        try:
            choice = int(raw)
            if not 1 <= choice <= len(response.actions):
                raise ValueError
        except ValueError:
            output("Please enter one displayed action number or q.")
            continue
        descriptor = response.actions[choice - 1]
        parameters = _collect_parameters(
            session, player_id, descriptor, output, input_fn, candidate_output=candidate_output
        )
        if parameters is None:
            # Do not submit a partial descriptor.  The next loop obtains a
            # fresh revision and gives the player an opportunity to choose
            # another visible action.
            continue
        submission = session.submit_descriptor(
            player_id, descriptor.action_id, parameters, response.state_revision
        )
        if not submission.accepted:
            assert submission.rejection is not None
            output(f"Action rejected: {submission.rejection.code}; refreshing actions.")

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


def _describe_action(action: LegalActionDescriptor) -> str:
    """Describe a public descriptor, not an internal reducer action."""
    source = f" from {action.source.label}" if action.source is not None else ""
    slots = ", ".join(slot.name for slot in action.parameters)
    suffix = f" (requires: {slots})" if slots else ""
    return f"{action.kind}{source}{suffix}"


def _collect_parameters(
    session: GameSession,
    player_id: str,
    descriptor: LegalActionDescriptor,
    output: Output,
    input_fn: Input,
    *,
    candidate_output: CandidateOutput | None = None,
) -> dict[str, object] | None:
    """Collect precisely the descriptor slots using API-projected candidates.

    There is deliberately no card-text parsing or target inference here.  A
    value can enter this mapping only after it has appeared in the current
    ``valid_targets_api`` response for the selected action and partial input.
    """
    selected: dict[str, object] = {}
    for slot in descriptor.parameters:
        value = _collect_slot(
            session, player_id, descriptor, slot, selected, output, input_fn, candidate_output=candidate_output
        )
        if value is None:
            return None
        selected[slot.name] = value
    return selected


def _collect_slot(
    session: GameSession,
    player_id: str,
    descriptor: LegalActionDescriptor,
    slot: ParameterSlot,
    selected: dict[str, object],
    output: Output,
    input_fn: Input,
    *,
    candidate_output: CandidateOutput | None = None,
) -> object | None:
    """Collect one declared parameter slot, preserving ordered selections."""
    if slot.kind in {"targets", "choice"}:
        return _collect_many(
            session, player_id, descriptor, slot, selected, output, input_fn, candidate_output=candidate_output
        )

    candidates = _slot_candidates(session, player_id, descriptor, slot, selected)
    if candidates is None:
        return None
    return _choose_candidate(candidates, slot, output, input_fn, candidate_output=candidate_output)


def _collect_many(
    session: GameSession,
    player_id: str,
    descriptor: LegalActionDescriptor,
    slot: ParameterSlot,
    selected: dict[str, object],
    output: Output,
    input_fn: Input,
    *,
    candidate_output: CandidateOutput | None = None,
) -> tuple[object, ...] | None:
    """Choose zero or more API candidates, in API-confirmed order when needed."""
    values: list[object] = []
    while slot.maximum is None or len(values) < slot.maximum:
        partial = dict(selected)
        partial[slot.name] = tuple(values)
        candidates = _slot_candidates(session, player_id, descriptor, slot, partial)
        if candidates is None:
            return None
        _print_candidates(candidates, output, candidate_output=candidate_output)
        raw = input_fn(f"Select {slot.name} number (d when done, q to cancel): ").strip().lower()
        if raw in {"q", "quit", "cancel"}:
            return None
        if raw in {"d", "done"}:
            if slot.minimum is not None and len(values) < slot.minimum:
                output(f"Select at least {slot.minimum} value(s).")
                continue
            return tuple(values)
        candidate = _candidate_from_input(raw, candidates, output)
        if candidate is None:
            continue
        # A distinct slot cannot accept the same candidate twice even if a
        # future API implementation happens to return it again.
        if slot.distinct and candidate.value in values:
            output("That value is already selected.")
            continue
        values.append(candidate.value)
    return tuple(values)


def _slot_candidates(
    session: GameSession,
    player_id: str,
    descriptor: LegalActionDescriptor,
    slot: ParameterSlot,
    partial: dict[str, object],
) -> tuple[TargetCandidate, ...] | None:
    response = session.valid_targets_api(player_id, descriptor.action_id, slot.name, partial)
    if isinstance(response, SessionRejection):
        return None
    return response.candidates


def _choose_candidate(
    candidates: tuple[TargetCandidate, ...],
    slot: ParameterSlot,
    output: Output,
    input_fn: Input,
    *,
    candidate_output: CandidateOutput | None = None,
) -> object | None:
    """Choose the single concrete candidate for scalar and composite slots."""
    while True:
        _print_candidates(candidates, output, candidate_output=candidate_output)
        raw = input_fn(f"Select {slot.name} number (q to cancel): ").strip().lower()
        if raw in {"q", "quit", "cancel"}:
            return None
        candidate = _candidate_from_input(raw, candidates, output)
        if candidate is not None:
            return candidate.value


def _print_candidates(
    candidates: tuple[TargetCandidate, ...],
    output: Output,
    *,
    candidate_output: CandidateOutput | None = None,
) -> None:
    if candidate_output is not None:
        candidate_output(candidates)
        return
    for index, candidate in enumerate(candidates, start=1):
        output(f"  {index}. {candidate.label}")


def _candidate_from_input(
    raw: str, candidates: tuple[TargetCandidate, ...], output: Output) -> TargetCandidate | None:
    try:
        index = int(raw)
        if not 1 <= index <= len(candidates):
            raise ValueError
    except ValueError:
        output("Please enter one displayed number.")
        return None
    return candidates[index - 1]


def main(argv: list[str] | None = None) -> int:
    """Start a local Portal game from two JSON deck-list files.

    Sideboards are intentionally absent. During the opening procedure the
    current player sees that player's own hand in order to make a London
    mulligan choice; ordinary game rendering returns to public information.
    """
    parser = argparse.ArgumentParser(description="Play a local Portal deck game or a named mid-game scenario")
    parser.add_argument("--deck-a", help="JSON DeckList for player one")
    parser.add_argument("--deck-b", help="JSON DeckList for player two")
    parser.add_argument("--scenario", help="start a named deterministic mid-game scenario")
    parser.add_argument("--list-scenarios", action="store_true", help="list available mid-game scenarios")
    parser.add_argument("--player-a", default="alice")
    parser.add_argument("--player-b", default="bob")
    parser.add_argument("--starting-player", default=None)
    parser.add_argument("--seed", type=int, help="deterministic shuffle seed for a deck game")
    parser.add_argument("--save", default=None, help="write private replay input after play")
    args = parser.parse_args(argv)

    if args.list_scenarios:
        for scenario in list_midgame_scenarios():
            category = scenario.category.replace("_", " ")
            print(f"{scenario.name} [{category}]: {scenario.description}")
        return 0

    if args.scenario is not None:
        if args.deck_a is not None or args.deck_b is not None:
            parser.error("--scenario cannot be combined with --deck-a or --deck-b")
        repo_root = Path(__file__).resolve().parents[2]
        repository = CardRepository.from_information_directory(repo_root / "information")
        try:
            session = create_midgame_session(repository, args.scenario)
        except ValueError as error:
            parser.error(str(error))
        scenario = next(item for item in list_midgame_scenarios() if item.name == args.scenario)
        category = f"{scenario.category.replace('_', '-')} scenario"
        print(f"Starting {category}: {scenario.name} — {scenario.description}")
        run_cli(session, replay_path=args.save)
        return 0

    if args.deck_a is None or args.deck_b is None or args.seed is None:
        parser.error("a deck game requires --deck-a, --deck-b, and --seed; use --list-scenarios to explore scenarios")

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

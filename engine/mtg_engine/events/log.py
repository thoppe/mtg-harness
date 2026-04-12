from __future__ import annotations

from dataclasses import dataclass, field

from .models import GameEvent


@dataclass
class EventLog:
    game_id: str
    _events: list[GameEvent] = field(default_factory=list)

    def append(self, *, event_type: str, active_player: str, payload: dict) -> GameEvent:
        sequence = len(self._events) + 1
        event = GameEvent(
            event_id=f"{self.game_id}:{sequence}",
            game_id=self.game_id,
            sequence=sequence,
            event_type=event_type,
            active_player=active_player,
            payload=payload,
        )
        self._events.append(event)
        return event

    @property
    def events(self) -> tuple[GameEvent, ...]:
        return tuple(self._events)

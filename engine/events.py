"""Event dataclass and an append-only EventLog that rejects duplicates."""
from __future__ import annotations

import copy
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Iterator

ARRIVAL = "ARRIVAL"
VITALS = "VITALS"
REASSESSED = "REASSESSED"
RESOURCE_REQUESTED = "RESOURCE_REQUESTED"
RESOURCE_COMPLETED = "RESOURCE_COMPLETED"
CLINICIAN_LEVEL = "CLINICIAN_LEVEL"
FLAG_DISMISSED = "FLAG_DISMISSED"
FLAG_ACCEPTED = "FLAG_ACCEPTED"

EVENT_TYPES = {
    ARRIVAL, VITALS, REASSESSED, RESOURCE_REQUESTED, RESOURCE_COMPLETED,
    CLINICIAN_LEVEL, FLAG_DISMISSED, FLAG_ACCEPTED,
}


@dataclass
class Event:
    """One immutable fact about a patient. Identity is event_id."""
    type: str
    patient_id: str
    ts: datetime
    payload: dict[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex)

    def __post_init__(self) -> None:
        if self.type not in EVENT_TYPES:
            raise ValueError(f"Unknown event type: {self.type}")


class EventLog:
    """Append-only log. An event whose event_id was already seen is ignored."""

    def __init__(self, events: list[Event] | None = None) -> None:
        self._events: list[Event] = []
        self._ids: set[str] = set()
        for e in events or []:
            self.append(e)

    def append(self, event: Event) -> bool:
        """Add an event. Returns False (and does nothing) for a duplicate event_id."""
        if event.event_id in self._ids:
            return False
        self._ids.add(event.event_id)
        self._events.append(event)
        return True

    def extend(self, events: list[Event]) -> int:
        """Add many events; returns how many were actually new."""
        return sum(self.append(e) for e in events)

    def for_patient(self, patient_id: str) -> list[Event]:
        return [e for e in self._events if e.patient_id == patient_id]

    @property
    def events(self) -> tuple[Event, ...]:
        return tuple(self._events)

    def copy(self) -> "EventLog":
        """Deep, independent copy (safe for what-if replays)."""
        return EventLog(copy.deepcopy(self._events))

    def __len__(self) -> int:
        return len(self._events)

    def __iter__(self) -> Iterator[Event]:
        return iter(self._events)

    def __contains__(self, event_id: object) -> bool:
        return event_id in self._ids
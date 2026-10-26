"""The only ways the UI may change things: append events.
Level changes ONLY through set_level (CLINICIAN_LEVEL). Dismiss/accept never touch level."""
from __future__ import annotations

from datetime import datetime

from .config import CONFIG
from .events import CLINICIAN_LEVEL, FLAG_ACCEPTED, FLAG_DISMISSED, Event, EventLog


def set_level(log: EventLog, patient_id: str, level: int, ts: datetime, by: str) -> Event:
    if not 1 <= int(level) <= 5:
        raise ValueError("Level must be 1-5")
    e = Event(CLINICIAN_LEVEL, patient_id, ts, {"level": int(level), "by": by})
    log.append(e)
    return e


def dismiss_flag(log: EventLog, patient_id: str, flag_key: str, ts: datetime,
                 by: str, minutes: int | None = None, config: dict | None = None) -> Event:
    """Hide a flag until ts + minutes. Minutes are stored in the event so
    later config changes don't rewrite past dismissals."""
    cfg = config or CONFIG
    mins = cfg["DISMISS_MIN"] if minutes is None else minutes
    e = Event(FLAG_DISMISSED, patient_id, ts, {"flag_key": flag_key, "minutes": mins, "by": by})
    log.append(e)
    return e


def accept_flag(log: EventLog, patient_id: str, flag_key: str, ts: datetime, by: str) -> Event:
    """Acknowledge a flag. If the clinician also wants a new level,
    the UI must call set_level separately."""
    e = Event(FLAG_ACCEPTED, patient_id, ts, {"flag_key": flag_key, "by": by})
    log.append(e)
    return e
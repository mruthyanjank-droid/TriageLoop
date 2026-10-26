"""Rebuild patient state by replaying events in timestamp order."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from .config import CONFIG
from .events import (
    ARRIVAL, CLINICIAN_LEVEL, FLAG_ACCEPTED, FLAG_DISMISSED, REASSESSED,
    RESOURCE_COMPLETED, RESOURCE_REQUESTED, VITALS, Event, EventLog,
)


@dataclass
class PatientState:
    patient_id: str
    arrival_ts: datetime | None = None
    level: int | None = None                                   # only set by CLINICIAN_LEVEL
    level_history: list[tuple[datetime, int, str]] = field(default_factory=list)
    vitals: list[tuple[datetime, dict]] = field(default_factory=list)
    last_assessed_ts: datetime | None = None
    pending_resources: dict[str, tuple[str, datetime]] = field(default_factory=dict)
    completed_resources: dict[str, tuple[str, datetime | None, datetime]] = field(default_factory=dict)
    dismissed: dict[str, datetime] = field(default_factory=dict)   # flag_key -> hidden until
    accepted: dict[str, datetime] = field(default_factory=dict)    # flag_key -> accepted at


def _sort_key(e: Event) -> tuple:
    # event_id breaks ties so equal timestamps still replay deterministically
    return (e.ts, e.event_id)


def rebuild(log: EventLog, as_of: datetime | None = None,
            config: dict | None = None) -> dict[str, PatientState]:
    """Replay all events (optionally only those up to `as_of`) sorted by ts.
    Arrival order of events never matters, only their timestamps."""
    cfg = config or CONFIG
    states: dict[str, PatientState] = {}
    for e in sorted(log, key=_sort_key):
        if as_of is not None and e.ts > as_of:
            continue
        st = states.setdefault(e.patient_id, PatientState(e.patient_id))
        _apply(st, e, cfg)
    return states


def _apply(st: PatientState, e: Event, cfg: dict) -> None:
    p = e.payload
    if e.type == ARRIVAL:
        if st.arrival_ts is None or e.ts < st.arrival_ts:
            st.arrival_ts = e.ts

    elif e.type == VITALS:
        st.vitals.append((e.ts, dict(p)))
        st.last_assessed_ts = e.ts

    elif e.type == REASSESSED:
        st.last_assessed_ts = e.ts

    elif e.type == RESOURCE_REQUESTED:
        rid = p["resource_id"]
        if rid not in st.completed_resources:
            st.pending_resources[rid] = (p.get("name", rid), e.ts)

    elif e.type == RESOURCE_COMPLETED:
        rid = p["resource_id"]
        name, requested = st.pending_resources.pop(rid, (p.get("name", rid), None))
        st.completed_resources[rid] = (name, requested, e.ts)

    elif e.type == CLINICIAN_LEVEL:
        level = int(p["level"])
        if not 1 <= level <= 5:
            raise ValueError(f"Level must be 1-5, got {level}")
        st.level = level
        st.level_history.append((e.ts, level, p.get("by", "")))

    elif e.type == FLAG_DISMISSED:
        minutes = p.get("minutes", cfg["DISMISS_MIN"])
        until = e.ts + timedelta(minutes=minutes)
        key = p["flag_key"]
        st.dismissed[key] = max(until, st.dismissed.get(key, until))

    elif e.type == FLAG_ACCEPTED:
        # Acknowledgement only. Deliberately does NOT touch st.level.
        st.accepted[p["flag_key"]] = e.ts
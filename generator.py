
"""Repeatable demo scenarios for TriageLoop."""
import random
import uuid
from datetime import datetime, timedelta

from engine.events import (
    Event,
    ARRIVAL,
    VITALS,
    RESOURCE_REQUESTED,
    RESOURCE_COMPLETED,
)

START = datetime(2026, 1, 1, 10, 0)

COMPLAINTS = [
    ("Chest pain", "CT", 2),
    ("Head injury", "CT", 3),
    ("Abdominal pain", "LAB", 3),
    ("Fracture", "BED", 4),
    ("Fever", "LAB", 4),
    ("Sprain", "BED", 5),
]

PINNED = {
    "P03": ("Chest pain", "CT", 2),
    "P05": ("Head injury", "CT", 3),
    "P07": ("Abdominal pain", "LAB", 3),
}
DETERIORATING = {"P03", "P07"}

SICK = {
    "hr": [110, 115, 120, 125],
    "rr": [20, 22, 24, 26],
    "spo2": [97, 94, 91, 89],
}


def _eid(rng):
    return str(uuid.UUID(int=rng.getrandbits(128), version=4))


def _event(event_type, patient_id, ts, payload, rng):
    return Event(
        type=event_type,
        patient_id=patient_id,
        ts=ts,
        payload=payload,
        event_id=_eid(rng),
    )


def _healthy_vitals(rng):
    return {
        "hr": rng.randint(70, 95),
        "rr": rng.randint(14, 18),
        "spo2": rng.randint(96, 99),
        "sbp": rng.randint(110, 135),
        "temp": round(rng.uniform(36.4, 37.4), 1),
    }


def _sick_vitals(rng, k):
    return {
        "hr": SICK["hr"][k],
        "rr": SICK["rr"][k],
        "spo2": SICK["spo2"][k],
        "sbp": rng.randint(100, 115),
        "temp": round(rng.uniform(37.0, 38.0), 1),
    }


def _base_events(rng, n=14, start=START, gap=9, prefix="P", sick=True):
    events = []

    for i in range(n):
        pid = f"{prefix}{i + 1:02d}"
        comp, need, level = (
            (PINNED.get(pid) if sick else None)
            or rng.choice(COMPLAINTS)
        )
        arrival_ts = start + timedelta(minutes=i * gap)

        events.append(_event(
            ARRIVAL, pid, arrival_ts,
            {"level": level, "complaint": comp, "needs": need}, rng
        ))

        # Record four sets of vitals, 20 minutes apart.
        for k in range(4):
            ts = arrival_ts + timedelta(minutes=(k + 1) * 20)
            vitals = (
                _sick_vitals(rng, k)
                if sick and pid in DETERIORATING
                else _healthy_vitals(rng)
            )
            events.append(_event(VITALS, pid, ts, vitals, rng))

    return events


def make_scenario(seed=42):
    """Create a repeatable scenario with deterioration and duplicate delivery."""
    rng = random.Random(seed)
    events = _base_events(rng)

    # Simulate a CT request that remains pending during the outage.
    # The engine has no RESOURCE_STATUS event, so use supported events.
    ct_start = START + timedelta(minutes=30)
    events.append(_event(
        RESOURCE_REQUESTED, "P05", ct_start,
        {"resource_id": "CT-P05", "name": "CT"}, rng
    ))

    # Deliver some events out of timestamp order without changing timestamps.
    for _ in range(4):
        i, j = rng.sample(range(len(events)), 2)
        events[i], events[j] = events[j], events[i]

    # Append the same event again to exercise duplicate-ID handling.
    events.append(events[10])
    return events


def make_surge(seed=42):
    """Create 20 arrivals within a 30-minute window."""
    rng = random.Random(seed)
    return _base_events(rng, n=20, gap=30 / 19)


def make_quiet(seed=42):
    """Create four arrivals spaced 30 minutes apart."""
    rng = random.Random(seed)
    return _base_events(rng, n=4, gap=30, sick=False)

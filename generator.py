"""Repeatable demo scenario for TriageLoop.

make_scenario(seed=42) always returns the same events for the same seed.
Event(event_id, type, ts, patient_id, payload)  # ASSUMPTION: confirm with engine/events.py
"""
import random
import uuid
from datetime import datetime, timedelta

from engine.events import Event

START = datetime(2026, 1, 1, 10, 0)

COMPLAINTS = [
    ("Chest pain", "CT", 2),
    ("Head injury", "CT", 3),
    ("Abdominal pain", "LAB", 3),
    ("Fracture", "BED", 4),
    ("Fever", "LAB", 4),
    ("Sprain", "BED", 5),
]

# Pinned patients so the drama is guaranteed on every run
PINNED = {
    "P03": ("Chest pain", "CT", 2),       # deteriorates
    "P05": ("Head injury", "CT", 3),      # level 3 that needs CT (hit by outage)
    "P07": ("Abdominal pain", "LAB", 3),  # deteriorates
}
DETERIORATING = {"P03", "P07"}

# Falling spo2, rising hr and rr, for the four vitals readings
SICK = {
    "hr":   [110, 115, 120, 125],
    "rr":   [20, 22, 24, 26],
    "spo2": [97, 94, 91, 89],
}


def _eid(rng):
    """Repeatable UUID: same seed gives same IDs (uuid4() would not)."""
    return str(uuid.UUID(int=rng.getrandbits(128), version=4))


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
        comp, need, lvl = (PINNED.get(pid) if sick else None) or rng.choice(COMPLAINTS)
        t0 = start + timedelta(minutes=i * gap)
        events.append(Event(_eid(rng), "ARRIVAL", t0, pid,
                            {"level": lvl, "complaint": comp, "needs": need}))
        for k in range(4):  # vitals every 20 min
            ts = t0 + timedelta(minutes=(k + 1) * 20)
            if sick and pid in DETERIORATING:
                v = _sick_vitals(rng, k)
            else:
                v = _healthy_vitals(rng)
            events.append(Event(_eid(rng), "VITALS", ts, pid, v))
    return events


def make_scenario(seed=42):
    rng = random.Random(seed)  # local RNG, no global state touched
    events = _base_events(rng)

    # Scripted drama: CT busy until 2.5 hours after the outage starts
    ct_start = START + timedelta(minutes=30)
    events.append(Event(
        _eid(rng), "RESOURCE_STATUS", ct_start, None,  # ASSUMPTION: patient_id None allowed
        {"resource": "CT", "status": "BUSY",
         "until": (ct_start + timedelta(hours=2, minutes=30)).isoformat()}))

    # Messy delivery: swap a few events so they arrive out of ts order (ts untouched)
    for _ in range(4):
        i, j = rng.sample(range(len(events)), 2)
        events[i], events[j] = events[j], events[i]

    # Duplicate: same event_id appended a second time
    events.append(events[10])
    return events

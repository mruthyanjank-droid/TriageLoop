"""Append-only event log.

Every change in the system is recorded as an event. Nothing is ever edited
or deleted; current state is always rebuilt by replaying events in order.
"""
import json
import os
import threading
from datetime import datetime, timedelta

# Simulation clock: minutes are counted from this moment.
SIM_START = datetime(2025, 9, 26, 9, 30)

EVENT_TYPES = {
    "patient_arrived",     # pid, esi, complaint, news2, needs[]
    "vitals_updated",      # pid, news2, note
    "resource_changed",    # resource, status, minutes
    "lab_result",          # pid, note
    "clock_advanced",      # minutes
    "clinician_reviewed",  # pid, note
}


def sim_time(minute: int) -> datetime:
    return SIM_START + timedelta(minutes=minute)


class EventLog:
    def __init__(self, path: str):
        self.path = path
        self._lock = threading.Lock()
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        if not os.path.exists(path):
            open(path, "w", encoding="utf-8").close()

    def read_all(self) -> list[dict]:
        with self._lock, open(self.path, encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]

    def append(self, etype: str, minute: int, **data) -> dict:
        if etype not in EVENT_TYPES:
            raise ValueError(f"Unknown event type: {etype}")
        with self._lock:
            seq = sum(1 for _ in open(self.path, encoding="utf-8")) + 1
            event = {"seq": seq, "type": etype, "minute": minute, **data}
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(json.dumps(event) + "\n")
        return event

    def clear(self):
        with self._lock:
            open(self.path, "w", encoding="utf-8").close()

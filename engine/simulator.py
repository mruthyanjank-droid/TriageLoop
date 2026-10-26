"""Simulation controls: seed a scenario, advance time, add arrivals, CT outage.

All actions only append events — they never change state directly.
"""
import random
from .events import EventLog
from .state import rebuild

COMPLAINTS = [
    ("Chest pain", 2, ["CT", "Lab"]), ("Abdominal pain", 3, ["CT"]),
    ("Minor injury", 4, []), ("Shortness of breath", 2, ["CT"]),
    ("Fever", 3, ["Lab"]), ("Headache", 3, ["CT"]),
    ("Laceration", 4, ["Beds"]), ("Dizziness", 3, ["Lab"]),
    ("Back pain", 4, []), ("Allergic reaction", 2, ["Beds"]),
]

SCENARIOS = ["Normal", "Surge"]


def seed_normal(log: EventLog):
    """Deterministic starting scenario matching the dashboard design (now = 10:42)."""
    e = log.append
    e("resource_changed", 0, resource="Beds", status="Busy", minutes=200, utilisation=67)
    e("resource_changed", 0, resource="Lab", status="Free", utilisation=33)
    # minute 0 = 09:30
    e("patient_arrived", 7,  pid="P11", esi=2, complaint="Shortness of breath", news2=3, needs=["CT"])
    e("patient_arrived", 12, pid="P01", esi=3, complaint="Headache", news2=1, needs=["CT"])
    e("patient_arrived", 24, pid="P03", esi=3, complaint="Chest pain", news2=2, needs=["CT", "Lab"])
    e("patient_arrived", 30, pid="P14", esi=3, complaint="Fever", news2=2, needs=["Lab"])
    e("patient_arrived", 36, pid="P02", esi=4, complaint="Back pain", news2=0, needs=[])
    e("patient_arrived", 40, pid="P05", esi=2, complaint="Abdominal pain", news2=1, needs=["CT"])
    e("patient_arrived", 46, pid="P06", esi=4, complaint="Laceration", news2=0, needs=["Beds"])
    e("patient_arrived", 54, pid="P08", esi=4, complaint="Minor injury", news2=1, needs=[])
    e("patient_arrived", 58, pid="P09", esi=5, complaint="Prescription refill", news2=0, needs=[])
    e("lab_result",      65, pid="P05", note="Troponin negative")
    e("vitals_updated",  50, pid="P11", news2=7, note="RR 26, SpO₂ 91")
    e("vitals_updated",  60, pid="P14", news2=5, note="Temp 39.1 °C")
    e("vitals_updated",  62, pid="P05", news2=4, note="HR 112")
    e("resource_changed", 60, resource="Lab", status="Busy", minutes=60, utilisation=33)
    e("patient_arrived", 68, pid="P07", esi=3, complaint="Abdominal pain", news2=1, needs=["CT"])
    e("resource_changed", 70, resource="CT", status="Offline", minutes=120, note="CT set to offline")
    e("vitals_updated",  72, pid="P03", news2=6, spo2=92, note="SpO₂ dropped from 97 → 92")


def seed_surge(log: EventLog):
    seed_normal(log)
    add_arrivals(log, 8, rng=random.Random(7))


def reset(log: EventLog, scenario: str = "Normal"):
    log.clear()
    (seed_surge if scenario == "Surge" else seed_normal)(log)


def _next_pid(state) -> str:
    nums = [int(p[1:]) for p in state.patients] or [0]
    return f"P{max(nums) + 1:02d}"


def add_arrivals(log: EventLog, n: int = 5, rng: random.Random | None = None):
    rng = rng or random.Random()
    for _ in range(n):
        st = rebuild(log.read_all())
        complaint, esi, needs = rng.choice(COMPLAINTS)
        log.append("patient_arrived", st.now, pid=_next_pid(st), esi=esi,
                   complaint=complaint, news2=rng.randint(0, 3), needs=needs)


def advance(log: EventLog, minutes: int = 10, rng: random.Random | None = None):
    rng = rng or random.Random()
    st = rebuild(log.read_all())
    new_now = st.now + minutes
    log.append("clock_advanced", new_now, minutes=minutes)
    # Vitals drift for a few patients
    for p in rng.sample(list(st.patients.values()), k=min(3, len(st.patients))):
        drift = rng.choice([-1, 0, 1, 1, 2])
        if drift:
            log.append("vitals_updated", new_now, pid=p.pid,
                       news2=max(0, min(20, p.news2 + drift)),
                       note=f"NEWS2 {p.news2} → {max(0, p.news2 + drift)}")


def ct_down(log: EventLog, minutes: int = 60):
    st = rebuild(log.read_all())
    log.append("resource_changed", st.now, resource="CT", status="Offline",
               minutes=minutes, note=f"CT offline for {minutes} min")


def clinician_review(log: EventLog, pid: str, note: str = "Reviewed by clinician"):
    st = rebuild(log.read_all())
    if pid not in st.patients:
        raise KeyError(pid)
    log.append("clinician_reviewed", st.now, pid=pid, note=note)

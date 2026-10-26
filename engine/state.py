"""Rebuild current state by replaying the event log (sorted by timestamp)."""
from dataclasses import dataclass, field

RESOURCES = ("CT", "Beds", "Lab")


@dataclass
class Patient:
    pid: str
    esi: int
    complaint: str
    arrival: int
    news2: int
    baseline_news2: int          # value at arrival or at last clinician review
    needs: list
    last_review: int | None = None
    spo2: int | None = None
    history: list = field(default_factory=list)


@dataclass
class Resource:
    name: str
    status: str = "Free"         # Free | Busy | Offline
    until: int | None = None     # minute when status ends (Offline/Busy)
    utilisation: int = 0


@dataclass
class State:
    now: int = 0
    patients: dict = field(default_factory=dict)
    resources: dict = field(default_factory=lambda: {r: Resource(r) for r in RESOURCES})
    events: list = field(default_factory=list)


def rebuild(events: list[dict]) -> State:
    st = State()
    for ev in sorted(events, key=lambda e: (e["minute"], e["seq"])):
        st.now = max(st.now, ev["minute"])
        st.events.append(ev)
        t = ev["type"]

        if t == "patient_arrived":
            st.patients[ev["pid"]] = Patient(
                pid=ev["pid"], esi=ev["esi"], complaint=ev["complaint"],
                arrival=ev["minute"], news2=ev["news2"],
                baseline_news2=ev["news2"], needs=ev.get("needs", []),
            )
        elif t == "vitals_updated" and ev["pid"] in st.patients:
            p = st.patients[ev["pid"]]
            p.news2 = ev["news2"]
            p.spo2 = ev.get("spo2", p.spo2)
        elif t == "clinician_reviewed" and ev["pid"] in st.patients:
            p = st.patients[ev["pid"]]
            p.baseline_news2 = p.news2
            p.last_review = ev["minute"]
        elif t == "resource_changed":
            r = st.resources[ev["resource"]]
            r.status = ev["status"]
            mins = ev.get("minutes")
            r.until = ev["minute"] + mins if mins else None
            if "utilisation" in ev:
                r.utilisation = ev["utilisation"]

        if "pid" in ev and ev["pid"] in st.patients:
            st.patients[ev["pid"]].history.append(ev)

    # Expire timed resource states
    for r in st.resources.values():
        if r.until is not None and st.now >= r.until:
            r.status, r.until = "Free", None
        if r.status == "Offline":
            r.utilisation = 0
    return st

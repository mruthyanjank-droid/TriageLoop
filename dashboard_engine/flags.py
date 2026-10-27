"""Flag rules. The system suggests; the clinician decides.

Rules are deliberately simple and explainable so every flag has a reason.
"""
from .state import State, Patient

# Minutes before reassessment is due, by ESI level
REASSESS_TARGET = {1: 0, 2: 30, 3: 60, 4: 120, 5: 240}
MINUTES_PER_SCAN = 30   # rough CT throughput, per patient ahead in queue
MINUTES_PER_LAB = 20


def wait_minutes(p: Patient, now: int) -> int:
    return now - (p.last_review if p.last_review is not None else p.arrival)


def resource_delay(state: State, p: Patient, need: str) -> int | None:
    """Estimated minutes until patient can get the resource, or None if no delay."""
    r = state.resources[need]
    remaining = (r.until - state.now) if r.until is not None else 0
    queue = sorted((q for q in state.patients.values() if need in q.needs),
                   key=lambda q: (q.esi, q.arrival))
    ahead = [q.pid for q in queue].index(p.pid)
    per = MINUTES_PER_SCAN if need == "CT" else MINUTES_PER_LAB
    if r.status == "Offline":
        return remaining + (ahead + 1) * per
    if r.status == "Busy":
        return max(remaining, 0) + ahead * per or None
    return None


def evaluate(state: State, p: Patient) -> dict:
    reasons = []
    rise = p.news2 - p.baseline_news2
    if rise >= 2:
        reasons.append({"kind": "danger",
                        "text": f"NEWS2 rose {p.baseline_news2} → {p.news2}",
                        "why": f"NEWS2 increased from {p.baseline_news2} to {p.news2}."})

    for need in p.needs:
        d = resource_delay(state, p, need)
        if d:
            r = state.resources[need]
            word = "unavailable" if r.status == "Offline" else "delayed"
            reasons.append({"kind": "warn",
                            "text": f"{need} {word} ~{d} min",
                            "why": f"{need} availability is delayed."})

    wait = wait_minutes(p, state.now)
    target = REASSESS_TARGET.get(p.esi, 60)
    if wait > target:
        reasons.append({"kind": "warn",
                        "text": f"Reassessment overdue ({wait - target} min)",
                        "why": "Reassessment target may be overdue."})

    if (rise >= 2 and p.news2 >= 5) or p.news2 >= 7:
        level = "urgent"
    elif reasons:
        level = "reassess"
    else:
        level = "stable"

    return {"level": level, "reasons": reasons, "wait": wait, "rise": rise}


LEVEL_RANK = {"urgent": 0, "reassess": 1, "stable": 2}


def ranked_queue(state: State) -> list[tuple[Patient, dict]]:
    rows = [(p, evaluate(state, p)) for p in state.patients.values()]
    rows.sort(key=lambda r: (LEVEL_RANK[r[1]["level"]], r[0].esi,
                             -r[0].news2, -r[1]["wait"]))
    return rows

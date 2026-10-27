import random
from datetime import datetime, timedelta

import pytest

from engine.actions import accept_flag, dismiss_flag, set_level
from engine.config import make_config
from engine.events import (
    ARRIVAL, CLINICIAN_LEVEL, REASSESSED, RESOURCE_COMPLETED, RESOURCE_REQUESTED,
    VITALS, Event, EventLog,
)
from engine.flags import REASSESS_OVERDUE, VITALS_TREND, flags_for
from engine.scoring import score_param, score_vitals
from engine.state import rebuild

T0 = datetime(2026, 1, 1, 10, 0)
P = "p1"
NORMAL = dict(rr=16, spo2=97, on_oxygen=False, sbp=120, hr=70, avpu="A", temp=37.0)
BAD = dict(rr=30, spo2=88, on_oxygen=True, sbp=85, hr=140, avpu="V", temp=34.5)


def at(m):
    return T0 + timedelta(minutes=m)


def ev(type_, m, payload=None, eid=None, pid=P):
    kw = {"event_id": eid} if eid else {}
    return Event(type_, pid, at(m), payload or {}, **kw)


def admitted(level=3):
    log = EventLog()
    log.append(ev(ARRIVAL, 0))
    set_level(log, P, level, at(0), by="nurse")
    return log


# ---------- A1: duplicates ----------
def test_duplicate_event_ignored():
    log = EventLog()
    e = ev(ARRIVAL, 0, eid="x1")
    assert log.append(e) is True
    assert log.append(e) is False
    assert log.append(ev(VITALS, 5, NORMAL, eid="x1")) is False   # same id, other content
    assert len(log) == 1


def test_copy_is_independent():
    log = admitted()
    c = log.copy()
    c.append(ev(REASSESSED, 10))
    assert len(c) == len(log) + 1


# ---------- A2: out-of-order ----------
def test_out_of_order_gives_same_state():
    events = [
        ev(ARRIVAL, 0), ev(CLINICIAN_LEVEL, 1, {"level": 3, "by": "n"}),
        ev(VITALS, 5, NORMAL), ev(RESOURCE_REQUESTED, 6, {"resource_id": "ct", "name": "CT"}),
        ev(VITALS, 20, BAD), ev(RESOURCE_COMPLETED, 40, {"resource_id": "ct"}),
        ev(REASSESSED, 45), ev(CLINICIAN_LEVEL, 46, {"level": 2, "by": "dr"}),
    ]
    expected = rebuild(EventLog(events))
    for seed in range(5):
        shuffled = events[:]
        random.Random(seed).shuffle(shuffled)
        assert rebuild(EventLog(shuffled)) == expected
    assert rebuild(EventLog(list(reversed(events)))) == expected


# ---------- A3: scoring ----------
def test_known_vitals_scores():
    assert score_vitals(NORMAL).total == 0 and score_vitals(NORMAL).band == "low"
    assert score_vitals(BAD).total == 20 and score_vitals(BAD).band == "high"
    mid = dict(rr=22, spo2=95, on_oxygen=False, sbp=105, hr=115, avpu="A", temp=38.5)
    assert score_vitals(mid).total == 7
    single3 = {**NORMAL, "rr": 8}
    assert score_vitals(single3).total == 3 and score_vitals(single3).band == "low-medium"


@pytest.mark.parametrize("name,value,expected", [
    ("rr", 8, 3), ("rr", 9, 1), ("rr", 11, 1), ("rr", 12, 0), ("rr", 20, 0),
    ("rr", 21, 2), ("rr", 24, 2), ("rr", 25, 3),
    ("spo2", 91, 3), ("spo2", 92, 2), ("spo2", 93, 2), ("spo2", 94, 1), ("spo2", 95, 1), ("spo2", 96, 0),
    ("sbp", 90, 3), ("sbp", 91, 2), ("sbp", 100, 2), ("sbp", 101, 1), ("sbp", 110, 1),
    ("sbp", 111, 0), ("sbp", 219, 0), ("sbp", 220, 3),
    ("hr", 40, 3), ("hr", 41, 1), ("hr", 50, 1), ("hr", 51, 0), ("hr", 90, 0), ("hr", 91, 1),
    ("hr", 110, 1), ("hr", 111, 2), ("hr", 130, 2), ("hr", 131, 3),
    ("temp", 35.0, 3), ("temp", 35.1, 1), ("temp", 36.0, 1), ("temp", 36.1, 0),
    ("temp", 38.0, 0), ("temp", 38.1, 1), ("temp", 39.0, 1), ("temp", 39.1, 2),
    ("avpu", "A", 0), ("avpu", "C", 3), ("avpu", "U", 3),
    ("on_oxygen", True, 2), ("on_oxygen", False, 0),
])
def test_news2_boundaries(name, value, expected):
    assert score_param(name, value) == expected


# ---------- A4: every flag has color + reason ----------
def test_every_flag_has_color_and_reason():
    log = admitted(level=3)
    log.append(ev(VITALS, 0, NORMAL))
    log.append(ev(VITALS, 5, BAD))
    log.append(ev(RESOURCE_REQUESTED, 5, {"resource_id": "lab", "name": "Bloods"}))
    st = rebuild(log)[P]
    flags = flags_for(st, at(200))
    kinds = {f.kind for f in flags}
    assert {"vitals_trend", "resource_delay", "reassess_overdue"} <= kinds
    for f in flags:
        assert f.color in ("amber", "red")
        assert isinstance(f.why, str) and f.why


def test_completed_resource_clears_flag():
    log = admitted()
    log.append(ev(RESOURCE_REQUESTED, 1, {"resource_id": "ct", "name": "CT"}))
    log.append(ev(RESOURCE_COMPLETED, 30, {"resource_id": "ct"}))
    st = rebuild(log)[P]
    assert not [f for f in flags_for(st, at(500)) if f.kind == "resource_delay"]


# ---------- A5: level immutability ----------
def test_flags_never_change_level():
    log = admitted(level=4)
    log.append(ev(VITALS, 1, BAD))
    st = rebuild(log)[P]
    flag = next(f for f in flags_for(st, at(2)) if f.kind == VITALS_TREND)
    assert flag.color == "red"

    accept_flag(log, P, flag.key, at(3), by="dr")
    dismiss_flag(log, P, flag.key, at(4), by="dr")
    st = rebuild(log)[P]
    assert st.level == 4
    assert len(st.level_history) == 1

    set_level(log, P, 2, at(5), by="dr")
    assert rebuild(log)[P].level == 2


def test_invalid_level_rejected():
    with pytest.raises(ValueError):
        set_level(EventLog(), P, 9, at(0), by="x")


# ---------- A5: dismissal expiry ----------
def test_dismissal_hides_until_expiry():
    log = admitted(level=3)                       # target 60 min
    st = rebuild(log)[P]
    assert any(f.kind == REASSESS_OVERDUE for f in flags_for(st, at(70)))

    dismiss_flag(log, P, REASSESS_OVERDUE, at(70), by="n", minutes=30)
    st = rebuild(log)[P]
    assert not any(f.kind == REASSESS_OVERDUE for f in flags_for(st, at(99)))
    assert any(f.kind == REASSESS_OVERDUE for f in flags_for(st, at(101)))


def test_accepted_flag_still_visible_but_marked():
    log = admitted(level=3)
    accept_flag(log, P, REASSESS_OVERDUE, at(70), by="n")
    f = next(f for f in flags_for(rebuild(log)[P], at(75)) if f.kind == REASSESS_OVERDUE)
    assert f.accepted


# ---------- A7: config ----------
def test_config_override_changes_target():
    log = admitted(level=3)
    st = rebuild(log)[P]
    cfg = make_config({"TARGET_MIN": {3: 120}})
    assert not any(f.kind == REASSESS_OVERDUE for f in flags_for(st, at(70), cfg))
    with pytest.raises(KeyError):
        make_config({"NOPE": 1})
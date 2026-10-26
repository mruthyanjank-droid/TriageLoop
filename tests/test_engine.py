import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine import EventLog, rebuild, ranked_queue, simulator  # noqa: E402


def make_log(tmp_path):
    log = EventLog(str(tmp_path / "events.jsonl"))
    simulator.reset(log, "Normal")
    return log


def test_rebuild_is_deterministic(tmp_path):
    log = make_log(tmp_path)
    a, b = rebuild(log.read_all()), rebuild(log.read_all())
    assert a.now == b.now and set(a.patients) == set(b.patients)


def test_news2_rise_flags_urgent(tmp_path):
    log = make_log(tmp_path)
    flags = {p.pid: f for p, f in ranked_queue(rebuild(log.read_all()))}
    assert flags["P03"]["level"] == "urgent"
    assert flags["P11"]["level"] == "urgent"


def test_clinician_review_resets_baseline(tmp_path):
    log = make_log(tmp_path)
    simulator.clinician_review(log, "P03")
    st = rebuild(log.read_all())
    assert st.patients["P03"].baseline_news2 == st.patients["P03"].news2


def test_ct_down_adds_delay_reason(tmp_path):
    log = make_log(tmp_path)
    simulator.ct_down(log, 60)
    flags = {p.pid: f for p, f in ranked_queue(rebuild(log.read_all()))}
    assert any("CT unavailable" in r["text"] for r in flags["P05"]["reasons"])


def test_log_is_append_only(tmp_path):
    log = make_log(tmp_path)
    before = log.read_all()
    simulator.add_arrivals(log, 5)
    after = log.read_all()
    assert after[:len(before)] == before and len(after) == len(before) + 5

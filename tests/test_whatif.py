
from datetime import timedelta

import sim.whatif as whatif_module
from generator import make_scenario, START
from engine.events import EventLog


def test_whatif_does_not_modify_original_log(monkeypatch):
    log = EventLog(make_scenario())
    original_count = len(log)

    # Isolate the test from flag calculations.
    monkeypatch.setattr(
        whatif_module,
        "rebuild",
        lambda simulated_log, as_of=None: {},
    )

    result = whatif_module.whatif(
        log,
        "add 5 arrivals",
        START + timedelta(hours=4),
    )

    assert len(log) == original_count
    assert result == []


def test_whatif_adds_five_hypothetical_arrivals(monkeypatch):
    log = EventLog(make_scenario())
    original_count = len(log)
    captured = {}

    def fake_rebuild(simulated_log, as_of=None):
        captured["event_count"] = len(simulated_log)
        return {}

    monkeypatch.setattr(whatif_module, "rebuild", fake_rebuild)

    whatif_module.whatif(
        log,
        "add 5 arrivals",
        START + timedelta(hours=4),
    )

    assert captured["event_count"] == original_count + 5
    assert len(log) == original_count

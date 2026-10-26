
from generator import make_scenario
from engine.events import EventLog


def test_scenario_has_events():
    events = make_scenario()
    assert len(events) > 0


def test_event_log_rejects_duplicate_ids():
    events = make_scenario()
    log = EventLog(events)

    # The scenario contains a duplicate event ID.
    assert len(log) == len(events) - 1

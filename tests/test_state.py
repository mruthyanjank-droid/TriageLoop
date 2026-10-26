
from datetime import timedelta

from generator import make_scenario, START
from engine.events import EventLog
from engine.state import rebuild


def test_rebuild_creates_patient_states():
    log = EventLog(make_scenario())
    now = START + timedelta(hours=2)

    states = rebuild(log, as_of=now)

    assert len(states) > 0


def test_state_dictionary_keys_match_patient_ids():
    log = EventLog(make_scenario())
    now = START + timedelta(hours=2)

    states = rebuild(log, as_of=now)

    for patient_id, state in states.items():
        assert patient_id == state.patient_id


import pytest
from datetime import datetime

from engine.actions import set_level, dismiss_flag, accept_flag
from engine.events import EventLog, CLINICIAN_LEVEL, FLAG_DISMISSED, FLAG_ACCEPTED


def test_set_level_appends_level_change_event():
    log = EventLog()
    now = datetime(2026, 1, 1, 12, 0)

    event = set_level(log, "P1", 3, now, "clinician")

    assert event.type == CLINICIAN_LEVEL
    assert event.patient_id == "P1"
    assert event.payload["level"] == 3
    assert len(log) == 1


@pytest.mark.parametrize("level", [0, 6, -1])
def test_set_level_rejects_invalid_levels(level):
    log = EventLog()
    now = datetime(2026, 1, 1, 12, 0)

    with pytest.raises(ValueError, match="Level must be 1-5"):
        set_level(log, "P1", level, now, "clinician")

    assert len(log) == 0


def test_dismiss_flag_appends_dismissal_event():
    log = EventLog()
    now = datetime(2026, 1, 1, 12, 0)

    event = dismiss_flag(
        log, "P1", "resource_delay", now, "clinician", minutes=15
    )

    assert event.type == FLAG_DISMISSED
    assert event.payload["flag_key"] == "resource_delay"
    assert event.payload["minutes"] == 15
    assert len(log) == 1


def test_accept_flag_appends_acceptance_event():
    log = EventLog()
    now = datetime(2026, 1, 1, 12, 0)

    event = accept_flag(log, "P1", "reassessment", now, "clinician")

    assert event.type == FLAG_ACCEPTED
    assert event.payload["flag_key"] == "reassessment"
    assert len(log) == 1


from datetime import datetime, timedelta

from engine.state import PatientState
from engine.flags import flags_for


def test_flags_for_normal_empty_patient_returns_list():
    patient = PatientState("P1")
    now = datetime(2026, 1, 1, 12, 0)

    result = flags_for(patient, now)

    assert isinstance(result, list)


def test_resource_delay_flag_appears_after_threshold():
    now = datetime(2026, 1, 1, 12, 0)
    patient = PatientState(
        "P1",
        pending_resources={
            "CT1": ("CT", now - timedelta(hours=2)),
        },
    )

    result = flags_for(patient, now)

    assert any(flag.kind == "resource_delay" for flag in result)


def test_recent_resource_request_does_not_trigger_delay_flag():
    now = datetime(2026, 1, 1, 12, 0)
    patient = PatientState(
        "P1",
        pending_resources={
            "CT1": ("CT", now - timedelta(seconds=1)),
        },
    )

    result = flags_for(patient, now)

    assert not any(flag.kind == "resource_delay" for flag in result)

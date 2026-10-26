
from datetime import datetime, timedelta

from engine.state import PatientState
from sim.bottleneck import find_bottlenecks


def test_empty_states_return_empty_list():
    now = datetime(2026, 1, 1, 12, 0)

    result = find_bottlenecks({}, now)

    assert result == []


def test_bottlenecks_count_pending_resources():
    now = datetime(2026, 1, 1, 12, 0)

    patient1 = PatientState(
        "P1",
        pending_resources={
            "CT1": ("CT", now - timedelta(minutes=90)),
            "LAB1": ("LAB", now - timedelta(minutes=10)),
        },
    )
    patient2 = PatientState(
        "P2",
        pending_resources={
            "CT2": ("CT", now - timedelta(minutes=90)),
        },
    )

    states = {"P1": patient1, "P2": patient2}
    result = find_bottlenecks(states, now)

    counts = {item["resource"]: item["waiting"] for item in result}

    assert counts["CT"] == 2
    assert counts["LAB"] == 1

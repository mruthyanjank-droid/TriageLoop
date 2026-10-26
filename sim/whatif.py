
from datetime import timedelta

from engine.events import Event, EventLog, ARRIVAL
from engine.state import rebuild
from engine.flags import flags_for


def whatif(log, scenario_name, now):
    """Run a hypothetical scenario without modifying the original log."""
    simulated_log = log.copy() if isinstance(log, EventLog) else EventLog(list(log))

    if scenario_name == "add 5 arrivals":
        for i in range(5):
            patient_id = f"WHATIF_P{i + 1}"
            simulated_log.append(
                Event(
                    type=ARRIVAL,
                    patient_id=patient_id,
                    ts=now,
                    payload={
                        "level": 3,
                        "complaint": "Simulated arrival",
                        "needs": "CT",
                    },
                )
            )

    elif scenario_name == "CT down 60 min":
        raise NotImplementedError(
            "CT outage simulation needs resource-allocation rules "
            "that are not currently implemented in the event engine."
        )

    else:
        raise ValueError(f"Unknown scenario: {scenario_name}")

    states = rebuild(simulated_log, as_of=now)

    newly_flagged = []
    for patient_id, state in states.items():
        flags = flags_for(state, now)
        if flags:
            newly_flagged.append({
                "patient_id": patient_id,
                "reasons": [flag.why for flag in flags],
            })

    return newly_flagged

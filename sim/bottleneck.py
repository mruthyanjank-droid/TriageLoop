
from engine.flags import flags_for


def find_bottlenecks(states, now):
    """
    Summarize pending resource requests using the real engine states.

    states: dictionary of patient IDs to PatientState objects
    now: current simulation time (datetime)
    """
    summary = {}

    for patient in states.values():
        patient_is_flagged = bool(flags_for(patient, now))

        for resource_id, (name, requested_ts) in patient.pending_resources.items():
            resource = name

            if resource not in summary:
                summary[resource] = {
                    "waiting": 0,
                    "flagged": 0,
                }

            summary[resource]["waiting"] += 1

            if patient_is_flagged:
                summary[resource]["flagged"] += 1

    return sorted(
        [
            {
                "resource": resource,
                "waiting": counts["waiting"],
                "flagged": counts["flagged"],
            }
            for resource, counts in summary.items()
        ],
        key=lambda item: item["flagged"],
        reverse=True,
    )

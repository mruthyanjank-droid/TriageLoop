"""All tunable numbers in one dict, so the UI sidebar can expose them."""
from copy import deepcopy

CONFIG = {
    # Reassessment interval in minutes per clinician-assigned level (1 = most urgent)
    "TARGET_MIN": {1: 15, 2: 30, 3: 60, 4: 120, 5: 240},
    "OVERDUE_RED_FACTOR": 2.0,      # red once elapsed >= target * factor
    "RESOURCE_DELAY_MIN": 60,       # amber once a resource is pending longer than this
    "RESOURCE_RED_FACTOR": 2.0,     # red once pending >= delay * factor
    "TREND_WINDOW": 3,              # number of recent vitals sets to compare
    "TREND_SCORE_RISE": 2,          # score rise across the window that triggers amber
    "SCORE_AMBER": 5,               # NEWS2 total for amber
    "SCORE_RED": 7,                 # NEWS2 total for red
    "DISMISS_MIN": 30,              # default dismissal duration
}


def make_config(overrides: dict | None = None) -> dict:
    """Return a fresh config with overrides applied. Nested dicts (TARGET_MIN) are merged."""
    cfg = deepcopy(CONFIG)
    for key, value in (overrides or {}).items():
        if key not in cfg:
            raise KeyError(f"Unknown config key: {key}")
        if isinstance(cfg[key], dict) and isinstance(value, dict):
            cfg[key].update({int(k): v for k, v in value.items()})
        else:
            cfg[key] = value
    return cfg
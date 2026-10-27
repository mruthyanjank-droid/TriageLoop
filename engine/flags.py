"""Flags computed from PatientState. Every flag has a color and a 'why'.
Flags are advisory only; they never change a patient's level."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .config import CONFIG
from .scoring import score_vitals
from .state import PatientState

VITALS_TREND = "vitals_trend"
RESOURCE_DELAY = "resource_delay"
REASSESS_OVERDUE = "reassess_overdue"


@dataclass(frozen=True)
class Flag:
    key: str          # stable id used for dismiss/accept
    kind: str
    color: str        # "amber" | "red"
    why: str
    accepted: bool = False


def _minutes(a: datetime, b: datetime) -> float:
    return (b - a).total_seconds() / 60


def _vitals_trend_flag(st: PatientState, cfg: dict) -> Flag | None:
    if not st.vitals:
        return None
    window = st.vitals[-cfg["TREND_WINDOW"]:]
    results = [score_vitals(v) for _, v in window]
    first, latest = results[0], results[-1]
    reasons, color = [], None

    if latest.total >= cfg["SCORE_RED"]:
        color = "red"
        reasons.append(f"NEWS2 {latest.total} (red threshold {cfg['SCORE_RED']})")
    elif latest.total >= cfg["SCORE_AMBER"]:
        color = "amber"
        reasons.append(f"NEWS2 {latest.total} (amber threshold {cfg['SCORE_AMBER']})")
    elif latest.any_three:
        color = "amber"
        reasons.append("a single parameter scored 3")

    rise = latest.total - first.total
    if len(results) > 1 and rise >= cfg["TREND_SCORE_RISE"]:
        color = color or "amber"
        reasons.append(f"score rose {first.total} -> {latest.total} over last {len(results)} obs")

    if color is None:
        return None
    vitals_now = window[-1][1]
    drivers = ", ".join(f"{k}={vitals_now[k]} (+{s})" for k, s in latest.parts.items() if s > 0)
    why = "; ".join(reasons) + (f". Drivers: {drivers}" if drivers else "")
    if latest.missing:
        why += f". Partial score, missing: {', '.join(latest.missing)}"
    return Flag(VITALS_TREND, VITALS_TREND, color, why)


def _resource_delay_flags(st: PatientState, now: datetime, cfg: dict) -> list[Flag]:
    limit = cfg["RESOURCE_DELAY_MIN"]
    out = []
    for rid, (name, requested_ts) in st.pending_resources.items():
        waited = _minutes(requested_ts, now)
        if waited <= limit:
            continue
        color = "red" if waited >= limit * cfg["RESOURCE_RED_FACTOR"] else "amber"
        why = f"{name} requested {waited:.0f} min ago, still not done (limit {limit} min)"
        out.append(Flag(f"{RESOURCE_DELAY}:{rid}", RESOURCE_DELAY, color, why))
    return out


def _reassess_overdue_flag(st: PatientState, now: datetime, cfg: dict) -> Flag | None:
    if st.level is None:
        return None
    since = st.last_assessed_ts or st.arrival_ts
    if since is None:
        return None
    target = cfg["TARGET_MIN"][st.level]
    elapsed = _minutes(since, now)
    if elapsed <= target:
        return None
    color = "red" if elapsed >= target * cfg["OVERDUE_RED_FACTOR"] else "amber"
    why = (f"Level {st.level} needs reassessment every {target} min; "
           f"last assessed {elapsed:.0f} min ago ({elapsed - target:.0f} min overdue)")
    return Flag(REASSESS_OVERDUE, REASSESS_OVERDUE, color, why)


def all_flags(st: PatientState, now: datetime, config: dict | None = None) -> list[Flag]:
    """Every currently-true flag, ignoring dismissals."""
    cfg = config or CONFIG
    flags = [_vitals_trend_flag(st, cfg), _reassess_overdue_flag(st, now, cfg)]
    flags = [f for f in flags if f] + _resource_delay_flags(st, now, cfg)
    return sorted(flags, key=lambda f: (f.color != "red", f.key))


def flags_for(st: PatientState, now: datetime, config: dict | None = None) -> list[Flag]:
    """Flags to show: dismissed ones are hidden until their expiry;
    accepted ones are still shown but marked accepted."""
    visible = []
    for f in all_flags(st, now, config):
        until = st.dismissed.get(f.key)
        if until is not None and now < until:
            continue
        if f.key in st.accepted:
            f = Flag(f.key, f.kind, f.color, f.why, accepted=True)
        visible.append(f)
    return visible
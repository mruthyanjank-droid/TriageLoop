"""TriageLoop — Emergency Care Intelligence (simulation dashboard).

Run:  python app.py   then open http://127.0.0.1:5000
"""
import os
import threading

from flask import Flask, jsonify, render_template, request

from dashboard_engine import EventLog, rebuild, ranked_queue, sim_time, simulator

BASE = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__)
app.config["SCENARIO"] = "Normal"
log = EventLog(os.path.join(BASE, "data", "events.jsonl"))

if not log.read_all():
    simulator.reset(log, "Normal")


def describe(ev: dict) -> dict:
    """Turn a raw event into a dashboard-friendly line."""
    t = ev["type"]
    title, sub, tag, color = t.replace("_", " ").capitalize(), ev.get("note", ""), ev.get("pid", ""), "blue"
    if t == "patient_arrived":
        title, sub, color = "New patient arrival", f"ESI Level {ev['esi']} · {ev['complaint']}", "blue"
    elif t == "vitals_updated":
        title, color = "Vitals updated", "red"
        sub = sub or f"NEWS2 now {ev['news2']}"
    elif t == "resource_changed":
        title, tag, color = "Resource status changed", ev["resource"], "orange"
        sub = sub or f"{ev['resource']} set to {ev['status'].lower()}"
    elif t == "lab_result":
        title, color = "Lab result recorded", "green"
    elif t == "clinician_reviewed":
        title, color = "Clinician review", "green"
    elif t == "clock_advanced":
        title, sub, color = "Clock advanced", f"+{ev['minutes']} min", "grey"
    return {"seq": ev["seq"], "time": sim_time(ev["minute"]).strftime("%H:%M"),
            "title": title, "sub": sub, "tag": tag, "color": color, "type": t}


def snapshot() -> dict:
    st = rebuild(log.read_all())
    queue = ranked_queue(st)

    patients = []
    for p, f in queue:
        patients.append({
            "pid": p.pid, "esi": p.esi, "complaint": p.complaint,
            "news2": p.news2, "baseline": p.baseline_news2, "needs": p.needs,
            "wait": f["wait"], "level": f["level"], "reasons": f["reasons"],
            "reviewed": p.last_review is not None,
        })

    resources = []
    for name, r in st.resources.items():
        waiting = sum(1 for p in st.patients.values() if name in p.needs)
        resources.append({"name": name, "status": r.status, "waiting": waiting,
                          "utilisation": r.utilisation,
                          "remaining": (r.until - st.now) if r.until else None})

    flagged = [p for p in patients if p["level"] == "urgent"]
    waits = [p["wait"] for p in patients]
    offline = [r["name"] for r in resources if r["status"] == "Offline"]

    return {
        "clock": {"date": sim_time(st.now).strftime("%d %b %Y"),
                  "time": sim_time(st.now).strftime("%H:%M")},
        "scenario": app.config["SCENARIO"],
        "kpis": {
            "waiting": len(patients),
            "flags": len(flagged),
            "avg_wait": round(sum(waits) / len(waits)) if waits else 0,
            "resources_free": sum(1 for r in resources if r["status"] != "Offline"),
            "resources_total": len(resources),
        },
        "patients": patients,
        "resources": resources,
        "impact": (f"{', '.join(offline)} outage may increase waiting time for "
                   f"patients requiring imaging." if offline else
                   "All resources operational."),
        "events": [describe(e) for e in reversed(st.events)],
    }


@app.route("/")
def index():
    return render_template("index.html")


@app.get("/api/state")
def api_state():
    return jsonify(snapshot())


@app.get("/api/patient/<pid>")
def api_patient(pid):
    st = rebuild(log.read_all())
    p = st.patients.get(pid)
    if not p:
        return jsonify({"error": "not found"}), 404
    return jsonify({"pid": pid, "history": [describe(e) for e in p.history]})


LOCK = threading.Lock()
MAX_MINUTES, MAX_ARRIVALS = 240, 20


class ApiError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.message, self.status = message, status


@app.errorhandler(ApiError)
def handle_api_error(e):
    return jsonify({"error": e.message}), e.status


def get_int(body, key, default, lo, hi):
    try:
        n = int(body.get(key, default))
    except (TypeError, ValueError):
        raise ApiError(f"{key} must be a whole number")
    if not lo <= n <= hi:
        raise ApiError(f"{key} must be between {lo} and {hi}")
    return n


@app.before_request
def require_json():
    if request.method == "POST" and request.path.startswith("/api/action/"):
        if not request.is_json:
            raise ApiError("Content-Type must be application/json", 415)
        if not isinstance(request.get_json(silent=True), dict):
            raise ApiError("Body must be a JSON object")


@app.post("/api/action/<name>")
def api_action(name):
    with LOCK:
        return _do_action(name)


def _do_action(name):
    body = request.get_json(silent=True) or {}
    if name == "advance":
        simulator.advance(log, get_int(body, "minutes", 10, 1, MAX_MINUTES))
    elif name == "ct_down":
        simulator.ct_down(log, get_int(body, "minutes", 60, 1, MAX_MINUTES))
    elif name == "arrivals":
        simulator.add_arrivals(log, get_int(body, "count", 5, 1, MAX_ARRIVALS))
    elif name == "scenario":
        cur = simulator.SCENARIOS.index(app.config["SCENARIO"])
        app.config["SCENARIO"] = simulator.SCENARIOS[(cur + 1) % len(simulator.SCENARIOS)]
        simulator.reset(log, app.config["SCENARIO"])
    elif name == "reset":
        simulator.reset(log, app.config["SCENARIO"])
    elif name == "review":
        pid = body.get("pid")
        if not isinstance(pid, str) or not pid.strip():
            raise ApiError("pid is required")
        note = str(body.get("note", "Reviewed by clinician"))[:200]
        try:
            simulator.clinician_review(log, pid, note)
        except KeyError:
            raise ApiError("unknown patient", 404)
    else:
        raise ApiError(f"unknown action {name}")
    return jsonify(snapshot())


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1", use_reloader=False)
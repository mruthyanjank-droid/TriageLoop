# TriageLoop — Emergency Care Intelligence (simulation)

A Flask dashboard that simulates an emergency-department triage queue.
Built on an **event-sourced** design: the system suggests, the clinician decides.

```
Event sources ─► Append-only event log ─► Rebuild state ─► Flags ─► Dashboard
                         ▲                                              │
                         └──────────── Clinician decision ◄─────────────┘
```

## Project layout

```
TriageLoop-Repo/
├── app.py               Flask server + JSON API
├── engine/
│   ├── events.py        Append-only event log (data/events.jsonl)
│   ├── state.py         Rebuild state by replaying events in time order
│   ├── flags.py         Explainable flag rules (NEWS2 rise, resource delay, overdue)
│   └── simulator.py     Seed scenarios, advance clock, arrivals, CT outage
├── templates/index.html Dashboard layout
├── static/style.css     Styling (matches the Figma design)
├── static/app.js        Fetches /api/state and renders the UI
├── tests/test_engine.py pytest tests
└── data/                Event log lives here (git-ignored)
```

## Run it (Git Bash on Windows)

```bash
cd ~/OneDrive/Desktop/TriageLoop-Repo
python -m venv .venv
source .venv/Scripts/activate        # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000

Run tests: `python -m pytest -q`

## Flag rules

| Rule | Trigger |
|---|---|
| NEWS2 rise | NEWS2 ≥ 2 above baseline (arrival or last clinician review) |
| Urgent review | NEWS2 rise with NEWS2 ≥ 5, or NEWS2 ≥ 7 |
| Resource delay | Needed CT/Lab/Bed is Offline or Busy (estimate = remaining time + queue position) |
| Reassessment overdue | Wait exceeds ESI target (ESI2 30, ESI3 60, ESI4 120 min) |

"Review patient" appends a `clinician_reviewed` event, which resets that patient's
NEWS2 baseline and wait timer. Nothing is ever edited or deleted in the log.

> Simulation only — not for clinical use.

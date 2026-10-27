// TriageLoop front end — fetches state from Flask and renders the dashboard.
let STATE = null;
let selectedPid = null;

const $ = (s) => document.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const LABEL = { urgent: "URGENT REVIEW", reassess: "REASSESS SOON", stable: "STABLE" };

async function api(path, body) {
  const res = await fetch(path, body === undefined ? {} : {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
  });
  return res.json();
}

async function load() { render(await api("/api/state")); }

function render(s) {
  STATE = s;
  $("#clock-date").textContent = "▣ " + s.clock.date;
  $("#clock-time").textContent = s.clock.time;
  $("#scenario-btn").textContent = "☷ Scenario: " + s.scenario;
  $("#k-waiting").textContent = s.kpis.waiting;
  $("#k-flags").textContent = s.kpis.flags;
  $("#k-wait").textContent = s.kpis.avg_wait + " min";
  $("#k-res").textContent = `${s.kpis.resources_free}/${s.kpis.resources_total}`;
  renderQueue(); renderResources(); renderWhy(); renderEvents();
}

function renderQueue() {
  const q = $("#search").value.trim().toLowerCase();
  const f = $("#filter").value;
  const rows = STATE.patients.filter((p) =>
    (f === "all" || p.level === f) &&
    (!q || p.pid.toLowerCase().includes(q) || p.complaint.toLowerCase().includes(q)));

  $("#queue").innerHTML = rows.length ? rows.map((p) => {
    const reasons = p.reasons.length
      ? p.reasons.map((r) => `<div class="reason ${r.kind}">${esc(r.text)}</div>`).join("")
      : `<div class="reason ok">No flags</div><div class="reason note">Vitals stable · Routine monitoring</div>`;
    return `
    <div class="prow ${p.level}">
      <div>
        <div class="ptitle"><span class="sev"></span>${esc(p.pid)} · ESI Level ${p.esi} · ${esc(p.complaint)}
          <span class="pill ${p.level}">${LABEL[p.level]}</span></div>
        <div class="reasons">${reasons}</div>
      </div>
      <div class="news">NEWS2: ${p.news2}</div>
      <div class="waitbox">
        <small>◷ Wait time</small><div class="w">${p.wait} min</div>
        <div class="btns">
          <button class="btn primary" onclick="review('${p.pid}')">Review patient</button>
          <button class="btn" onclick="details('${p.pid}')">View details</button>
        </div>
      </div>
    </div>`;
  }).join("") : `<div class="empty">No patients match.</div>`;
}

function renderResources() {
  const color = { Offline: "var(--red)", Busy: "var(--orange)", Free: "var(--green)" };
  const icon = { CT: "◉", Beds: "▤", Lab: "♧" };
  $("#resources").innerHTML = STATE.resources.map((r) => `
    <div class="res">
      <div style="font-size:22px;color:var(--blue)">${icon[r.name] || "■"}</div>
      <div class="rname">${r.name}</div>
      <div class="rstat ${r.status}">● ${r.status}${r.remaining ? ` (${r.remaining}m)` : ""}</div>
      <div class="rwait">${r.waiting} waiting</div>
      <div class="bar-row"><div class="bar"><div style="width:${r.utilisation}%;background:${color[r.status]}"></div></div>${r.utilisation}%</div>
    </div>`).join("");
  $("#impact").textContent = STATE.impact;
}

function renderWhy() {
  const flagged = STATE.patients.filter((p) => p.level !== "stable");
  let p = flagged.find((x) => x.pid === selectedPid) || flagged[0];
  if (!p) {
    $("#why").innerHTML = `<h3>✓ No patients flagged</h3><p class="muted">All patients within targets.</p>`;
    return;
  }
  const seen = new Set();
  const items = p.reasons.filter((r) => !seen.has(r.why) && seen.add(r.why))
    .map((r) => `<li class="${r.kind}">${esc(r.why)}</li>`).join("");
  $("#why").innerHTML = `
    <div class="card-head"><h3><span style="color:var(--red)">▲</span>&nbsp; Why is ${esc(p.pid)} flagged?</h3>
      <a href="#" onclick="details('${p.pid}');return false">View details</a></div>
    <ul>${items}</ul>
    <div class="note">The system suggests; the clinician decides.</div>
    <div class="btns">
      <button class="btn primary" onclick="review('${p.pid}')">Review details</button>
      <button class="btn outline" onclick="details('${p.pid}')">View event history</button>
    </div>`;
}

function evRow(e) {
  return `<div class="ev"><span class="edot ${e.color}"></span><span class="etime">${e.time}</span>
    <div><div class="etitle">${esc(e.title)}</div><div class="esub">${esc(e.sub)}</div></div>
    <span class="etag">${esc(e.tag)}</span></div>`;
}

function renderEvents() {
  $("#recent").innerHTML = STATE.events.filter((e) => e.type !== "clock_advanced").slice(0, 4).map(evRow).join("");
  $("#log-body").innerHTML = STATE.events.map((e) =>
    `<tr><td>${e.seq}</td><td>${e.time}</td><td>${e.type}</td><td>${esc(e.title)}</td><td>${esc(e.sub)}</td><td>${esc(e.tag)}</td></tr>`).join("");
}

async function review(pid) {
  const p = STATE.patients.find((x) => x.pid === pid);
  if (!confirm(`Record clinician review for ${pid} (${p.complaint})?\nThis resets its NEWS2 baseline and wait timer.`)) return;
  render(await api("/api/action/review", { pid }));
}

async function details(pid) {
  selectedPid = pid; renderWhy();
  const d = await api(`/api/patient/${pid}`);
  const p = STATE.patients.find((x) => x.pid === pid);
  $("#modal-title").textContent = `${pid} · ESI ${p.esi} · ${p.complaint}`;
  $("#modal-body").innerHTML = `
    <p class="muted">NEWS2 ${p.news2} (baseline ${p.baseline}) · Waiting ${p.wait} min · Needs: ${p.needs.join(", ") || "none"}</p>
    <h3 style="margin:12px 0 4px">Event history</h3>${d.history.slice().reverse().map(evRow).join("")}`;
  $("#modal").classList.remove("hidden");
}

function showView(view) {
  document.querySelectorAll("nav a").forEach((a) => a.classList.toggle("active", a.dataset.view === view));
  $("#view-dashboard").classList.toggle("hidden", !["dashboard", "queue", "resources"].includes(view));
  $("#view-eventlog").classList.toggle("hidden", view !== "eventlog");
  $("#view-settings").classList.toggle("hidden", view !== "settings");
  const target = { queue: "#queue-card", resources: "#resources-card" }[view];
  if (target) $(target).scrollIntoView({ behavior: "smooth" });
}

document.querySelectorAll("[data-action]").forEach((b) =>
  b.addEventListener("click", async () => {
    b.disabled = true;
    try { render(await api(`/api/action/${b.dataset.action}`, {})); }
    finally { b.disabled = false; }
  }));
document.querySelectorAll("[data-view]").forEach((a) =>
  a.addEventListener("click", (e) => { e.preventDefault(); showView(a.dataset.view); }));
$("#search").addEventListener("input", renderQueue);
$("#filter").addEventListener("change", renderQueue);
$("#modal-close").onclick = () => $("#modal").classList.add("hidden");
$("#modal").onclick = (e) => { if (e.target.id === "modal") $("#modal").classList.add("hidden"); };

load();

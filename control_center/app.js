"use strict";

const $ = (selector, root = document) => root.querySelector(selector);
let dashboard = null;
let authenticated = false;
let apiAvailable = true;

function toast(message, type = "success") {
  const item = document.createElement("div");
  item.className = `toast ${type}`;
  item.textContent = message;
  $("#toastRegion").append(item);
  setTimeout(() => item.remove(), 4200);
}

function setBusy(button, busy, label = "Working…") {
  if (!button) return;
  if (busy) {
    button.dataset.label = button.textContent;
    button.textContent = label;
    button.disabled = true;
  } else {
    button.textContent = button.dataset.label || button.textContent;
    button.disabled = false;
  }
}

function humanStatus(value) {
  return String(value || "unknown").replaceAll("_", " ").replace(/\b\w/g, char => char.toUpperCase());
}

function formatTime(value, options = {}) {
  if (!value) return "Not yet";
  const date = new Date(value);
  if (Number.isNaN(date.valueOf())) return value;
  return new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric", hour: "numeric", minute: "2-digit", ...options }).format(date);
}

function relativeTime(value) {
  if (!value) return "Not synced";
  const seconds = Math.round((new Date(value) - new Date()) / 1000);
  const formatter = new Intl.RelativeTimeFormat(undefined, { numeric: "auto" });
  for (const [unit, size] of [["day", 86400], ["hour", 3600], ["minute", 60]]) {
    if (Math.abs(seconds) >= size) return formatter.format(Math.round(seconds / size), unit);
  }
  return "just now";
}

function setText(id, value) {
  const element = document.getElementById(id);
  if (element) element.textContent = value;
}

function setHealth(id, dotId, value) {
  setText(id, humanStatus(value));
  const dot = document.getElementById(dotId);
  dot.className = ["ready", "connected", "configured", "complete", "pass", "online", "healthy", "local"].includes(value) ? "good" :
    ["failed", "offline", "not_connected"].includes(value) ? "bad" : "";
}

async function api(path, options = {}) {
  const response = await fetch(`/api${path}`, {
    ...options,
    credentials: "same-origin",
    headers: { "content-type": "application/json", ...(options.headers || {}) },
  });
  let data = null;
  try { data = await response.json(); } catch (_) { /* non-json response */ }
  if (!response.ok) {
    const error = new Error(data?.error || `${response.status} ${response.statusText}`);
    error.status = response.status;
    throw error;
  }
  return data;
}

function renderSession() {
  setText("connectionLabel", authenticated ? "Secure session active" : apiAvailable ? "Sign in" : "Read-only preview");
  $("#openConnection").classList.toggle("authenticated", authenticated);
  const notice = $("#setupNotice");
  if (!authenticated) {
    notice.classList.remove("hidden");
    setText("noticeTitle", apiAvailable ? "Owner sign-in required" : "Cloud control plane not deployed");
    setText("noticeCopy", apiAvailable ? "Sign in to load private studio state and use production controls." : "This is the static preview. Deploy the Cloudflare Worker to activate controls.");
  }
  document.querySelectorAll("#runCycle, #runAiAudit, #addQueueItem, #pauseAutomation, #buildOnly, #uploadNow").forEach(button => {
    button.disabled = !authenticated;
  });
}

async function checkSession() {
  try {
    const health = await api("/health", { headers: {} });
    apiAvailable = true;
    authenticated = Boolean(health.authenticated);
  } catch (_) {
    apiAvailable = false;
    authenticated = false;
  }
  renderSession();
  return authenticated;
}

function renderWeek(days) {
  const container = $("#weekStrip");
  container.replaceChildren();
  const active = new Set((days || []).map(day => day.toLowerCase()));
  ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].forEach(day => {
    const node = document.createElement("div");
    node.className = `week-day ${active.has({ Tue: "tuesday", Thu: "thursday", Sat: "saturday" }[day]) ? "active" : ""}`;
    const label = document.createElement("strong");
    label.textContent = day;
    node.append(label);
    container.append(node);
  });
}

function renderQueue(items) {
  const container = $("#queueList");
  container.replaceChildren();
  if (!items?.length) {
    const empty = document.createElement("div");
    empty.className = "queue-empty";
    empty.textContent = "The queue is empty. Add a validated project to keep the schedule covered.";
    container.append(empty);
    return;
  }
  items.slice(0, 8).forEach((item, index) => {
    const row = document.createElement("div");
    row.className = "queue-row";
    const order = document.createElement("span");
    order.className = "queue-index";
    order.textContent = String(index + 1).padStart(2, "0");
    const copy = document.createElement("div");
    copy.className = "queue-copy";
    const title = document.createElement("strong");
    title.textContent = item.title;
    const meta = document.createElement("small");
    meta.textContent = item.last_error || `Attempt ${item.attempts || 0} · evidence-gated`;
    copy.append(title, meta);
    const when = document.createElement("span");
    when.className = "queue-when";
    when.textContent = item.scheduled_publish_at ? formatTime(item.scheduled_publish_at) : "Next slot";
    const status = document.createElement(item.youtube_url ? "a" : "span");
    status.className = `status-pill ${item.status}`;
    status.textContent = item.status.toUpperCase();
    if (item.youtube_url) Object.assign(status, { href: item.youtube_url, target: "_blank", rel: "noreferrer" });
    const hold = document.createElement("button");
    hold.className = "row-action";
    hold.type = "button";
    hold.textContent = item.status === "held" ? "Release" : "Hold";
    hold.disabled = !authenticated || !["ready", "held"].includes(item.status);
    hold.addEventListener("click", () => setQueueStatus(item, item.status === "held" ? "ready" : "held", hold));
    row.append(order, copy, when, status, hold);
    container.append(row);
  });
}

function renderEvents(events) {
  const container = $("#activityList");
  container.replaceChildren();
  (events || []).slice(0, 7).forEach(event => {
    const item = document.createElement("div");
    item.className = `activity-item ${event.level || "info"}`;
    const message = document.createElement("p");
    message.textContent = event.message;
    const time = document.createElement("time");
    time.textContent = event.at ? formatTime(event.at) : "Setup";
    item.append(message, time);
    container.append(item);
  });
}

function renderAi(ai) {
  const verdict = String(ai.verdict || "pending").toLowerCase();
  setText("aiModel", ai.model || "Not configured");
  setText("aiVerdict", verdict.toUpperCase());
  setText("aiSummary", ai.summary || "Waiting for the first evidence-bound audit.");
  $("#aiVerdictOrb").className = `verdict-orb ${verdict}`;
  setText("aiRisk", ai.risks?.[0] || ai.recommended_edits?.[0] || "No material risk reported.");
  const scores = ai.scores || {};
  ["hook", "clarity", "payoff", "evidence", "voice"].forEach(name => {
    const value = Number(scores[name]);
    const suffix = name[0].toUpperCase() + name.slice(1);
    setText(`score${suffix}`, Number.isFinite(value) ? `${value}/10` : "—");
    const bar = document.getElementById(`bar${suffix}`);
    if (bar) bar.style.width = Number.isFinite(value) ? `${Math.max(0, Math.min(10, value)) * 10}%` : "0%";
  });
}

function render(data) {
  dashboard = data;
  const system = data.system || {};
  const health = data.health || {};
  const metrics = data.metrics || {};
  const queue = data.queue || [];
  const schedule = data.schedule || {};
  const current = queue.find(item => item.id === system.current_item_id) || queue.find(item => ["building", "qc", "uploading"].includes(item.status)) || queue[0];

  $("#liveState").className = `live-state ${system.status === "healthy" ? "healthy" : system.status === "failed" ? "failed" : ""}`;
  $("#liveState b").textContent = humanStatus(system.status);
  setText("currentStage", system.current_stage || "Idle");
  const progressMap = { setup_required: 8, ready: 14, building: 62, qc: 78, uploading: 91, scheduled: 100, healthy: 100, failed: 50, held: 6 };
  const stage = current?.status || system.status;
  $("#pipelineProgress").style.width = `${progressMap[stage] || progressMap[system.status] || 8}%`;
  setText("stageNumber", String(Math.max(0, ["ready", "building", "qc", "uploading", "scheduled"].indexOf(stage) + 1)).padStart(2, "0"));
  if (current) {
    setText("currentTitle", current.title);
    setText("currentStatus", current.status.toUpperCase());
    $("#currentStatus").className = `status-pill ${current.status}`;
    setText("currentMeta", `${data.channel.genre} · ${current.scheduled_publish_at ? formatTime(current.scheduled_publish_at) : "awaiting slot"}`);
  }

  const next = schedule.next_publish_at ? new Date(schedule.next_publish_at) : null;
  setText("nextDay", next && !Number.isNaN(next.valueOf()) ? String(next.getDate()).padStart(2, "0") : "—");
  setText("nextMonth", next && !Number.isNaN(next.valueOf()) ? new Intl.DateTimeFormat(undefined, { month: "short" }).format(next) : "—");
  setText("nextTime", schedule.time || "19:30");
  setText("nextTimezone", schedule.timezone || "Asia/Kolkata");
  setText("cadence", (schedule.days || []).map(day => day.slice(0, 3)).join(" · "));
  setText("queueCoverage", `${metrics.queued || 0} release${metrics.queued === 1 ? "" : "s"}`);
  for (const [id, value] of Object.entries({ metricQueued: metrics.queued || 0, metricBuilding: metrics.building || 0, metricScheduled: metrics.scheduled || 0, metricPublished: metrics.published || 0, navQueueCount: metrics.queued || 0 })) setText(id, value);
  setText("queueSignal", metrics.queued >= 3 ? "Schedule covered" : `Needs ${Math.max(0, 3 - (metrics.queued || 0))} more`);
  setText("genreShort", data.channel.genre);
  setText("lastUpdated", relativeTime(data.generated_at));
  setHealth("runnerHealth", "runnerDot", health.runner);
  setHealth("youtubeHealth", "youtubeDot", health.youtube);
  setHealth("pipelineHealth", "pipelineDot", health.pipeline);
  setHealth("aiHealth", "aiDot", health.ai);
  setHealth("queueHealth", "queueDot", health.queue);
  setText("pauseAutomation", system.automation_enabled ? "Pause automation" : "Resume automation");
  if (authenticated) $("#setupNotice").classList.toggle("hidden", system.status !== "setup_required" && health.youtube === "connected");
  renderQueue(queue);
  renderEvents(data.events);
  renderWeek(schedule.days);
  renderAi(data.ai || {});
  updateClock();
}

function runIcon(run) {
  if (run.status !== "completed") return "live";
  return run.conclusion === "success" ? "success" : run.conclusion === "cancelled" ? "muted" : "failed";
}

function renderRuns(runs) {
  const list = $("#runList");
  list.replaceChildren();
  if (!runs.length) {
    const empty = document.createElement("p");
    empty.className = "runs-empty";
    empty.textContent = authenticated ? "No workflow activity yet." : "Sign in to view workflow activity.";
    list.append(empty);
    return;
  }
  runs.slice(0, 6).forEach(run => {
    const row = document.createElement("a");
    row.className = "run-row";
    Object.assign(row, { href: run.html_url, target: "_blank", rel: "noreferrer" });
    const dot = document.createElement("i"); dot.className = runIcon(run);
    const copy = document.createElement("span");
    const title = document.createElement("strong"); title.textContent = run.name;
    const meta = document.createElement("small"); meta.textContent = `${humanStatus(run.status === "completed" ? run.conclusion : run.status)} · ${relativeTime(run.created_at)}`;
    copy.append(title, meta);
    const arrow = document.createElement("b"); arrow.textContent = "↗";
    row.append(dot, copy, arrow);
    list.append(row);
  });
}

async function loadState({ quiet = false } = {}) {
  if (!authenticated) return;
  try {
    const [state, runs] = await Promise.all([api("/state"), api("/runs")]);
    render(state);
    renderRuns(runs.runs || []);
    if (!quiet) toast("Studio state refreshed.");
  } catch (error) {
    if (error.status === 401) {
      authenticated = false;
      renderSession();
      $("#connectionDialog").showModal();
    } else if (!quiet) toast(error.message, "error");
  }
}

async function performAction(action, values = {}, button) {
  setBusy(button, true);
  try {
    const result = await api("/action", { method: "POST", body: JSON.stringify({ action, ...values }) });
    toast(result.message || "Action accepted.");
    setTimeout(() => loadState({ quiet: true }), 2500);
  } catch (error) {
    toast(error.message, "error");
  } finally {
    setBusy(button, false);
  }
}

async function setQueueStatus(item, status, button) {
  setBusy(button, true);
  try {
    await api(`/queue/${encodeURIComponent(item.id)}`, { method: "PATCH", body: JSON.stringify({ status }) });
    toast(status === "held" ? "Project held. It cannot be selected for production." : "Project released back to the ready queue.");
    await performAction("refresh");
  } catch (error) {
    toast(error.message, "error");
  } finally {
    setBusy(button, false);
  }
}

async function commitQueueItem(form) {
  const values = Object.fromEntries(new FormData(form));
  if (values.requested_publish_at) values.requested_publish_at = new Date(values.requested_publish_at).toISOString();
  const result = await api("/queue", { method: "POST", body: JSON.stringify(values) });
  toast(`Queued: ${result.item.title}`);
  await performAction("refresh");
}

function updateClock() {
  const now = new Date();
  setText("liveClock", new Intl.DateTimeFormat("en-GB", { timeZone: "Asia/Kolkata", hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false }).format(now));
  const next = dashboard?.schedule?.next_publish_at ? new Date(dashboard.schedule.next_publish_at) : null;
  if (!next || Number.isNaN(next.valueOf())) return setText("nextCountdown", "Awaiting slot");
  const remaining = Math.max(0, next - now);
  const days = Math.floor(remaining / 86_400_000);
  const hours = Math.floor((remaining % 86_400_000) / 3_600_000);
  const minutes = Math.floor((remaining % 3_600_000) / 60_000);
  setText("nextCountdown", `${days ? `${days}d ` : ""}${hours}h ${minutes}m`);
}

function requireOwner() {
  if (authenticated) return true;
  if (apiAvailable) $("#connectionDialog").showModal();
  toast(apiAvailable ? "Unlock the owner console first." : "Deploy the Cloudflare control plane first.", "error");
  return false;
}

function bindEvents() {
  $("#openConnection").addEventListener("click", async () => {
    if (!authenticated) return $("#connectionDialog").showModal();
    if (!confirm("End this secure owner session?")) return;
    await api("/auth/logout", { method: "POST", body: "{}" });
    authenticated = false;
    dashboard = null;
    renderSession();
    renderRuns([]);
  });
  $("#setupButton").addEventListener("click", () => apiAvailable && $("#connectionDialog").showModal());
  $("#refreshState").addEventListener("click", () => requireOwner() && loadState());
  $("#openProduction").addEventListener("click", () => location.hash = "production");
  $("#addQueueItem").addEventListener("click", () => requireOwner() && $("#queueDialog").showModal());
  $("#connectionForm").addEventListener("submit", async event => {
    event.preventDefault();
    const button = $("#saveConnection");
    setBusy(button, true, "Unlocking…");
    try {
      const password = $("#controlPassword").value;
      await api("/auth/login", { method: "POST", body: JSON.stringify({ password }) });
      authenticated = true;
      $("#controlPassword").value = "";
      $("#connectionDialog").close();
      renderSession();
      await loadState({ quiet: true });
      toast("Owner controls unlocked for 12 hours.");
    } catch (error) { toast(error.message, "error"); }
    finally { setBusy(button, false); }
  });
  $("#queueForm").addEventListener("submit", async event => {
    event.preventDefault();
    const button = $("#submitQueueItem");
    setBusy(button, true, "Queuing…");
    try {
      await commitQueueItem(event.currentTarget);
      event.currentTarget.reset();
      $("#queueDialog").close();
    } catch (error) { toast(error.message, "error"); }
    finally { setBusy(button, false); }
  });
  $("#runCycle").addEventListener("click", event => requireOwner() && performAction("dry_run", { item_id: dashboard?.queue?.[0]?.id || "" }, event.currentTarget));
  $("#buildOnly").addEventListener("click", event => requireOwner() && performAction("build", { item_id: dashboard?.queue?.[0]?.id || "" }, event.currentTarget));
  $("#runAiAudit").addEventListener("click", event => requireOwner() && performAction("audit", { project_path: dashboard?.queue?.[0]?.project_path || "" }, event.currentTarget));
  $("#pauseAutomation").addEventListener("click", event => requireOwner() && performAction(dashboard?.system?.automation_enabled ? "pause" : "resume", {}, event.currentTarget));
  $("#uploadNow").addEventListener("click", event => {
    if (!requireOwner()) return;
    const item = dashboard?.queue?.[0];
    const passed = dashboard?.ai?.verdict === "pass";
    if (!item) return toast("No queue item is ready.", "error");
    if (!passed) return toast("Upload blocked: AI editorial verdict is not PASS.", "error");
    if (confirm(`Upload the approved item “${item.title}” privately to YouTube?`)) performAction("upload", { item_id: item.id }, event.currentTarget);
  });
  document.querySelectorAll(".nav-item").forEach(link => link.addEventListener("click", () => {
    document.querySelectorAll(".nav-item").forEach(item => item.classList.remove("active"));
    link.classList.add("active");
  }));
}

bindEvents();
updateClock();
checkSession().then(ok => ok ? loadState({ quiet: true }) : renderRuns([]));
setInterval(() => authenticated && loadState({ quiet: true }), 20_000);
setInterval(updateClock, 1_000);

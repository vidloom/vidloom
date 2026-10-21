"use strict";

const $ = (selector, root = document) => root.querySelector(selector);
const stateUrl = `data/dashboard.json?ts=${Date.now()}`;
const workflowFiles = {
  production: "production-cycle.yml",
  control: "control.yml",
  deploy: "deploy-dashboard.yml",
};

let dashboard = null;
let connection = readConnection();

function readConnection() {
  try {
    return JSON.parse(sessionStorage.getItem("vidloom-owner-connection")) || inferConnection();
  } catch (_) {
    return inferConnection();
  }
}

function inferConnection() {
  if (!location.hostname.endsWith("github.io")) return { owner: "", repo: "", branch: "main", token: "" };
  const owner = location.hostname.split(".")[0];
  const firstPath = location.pathname.split("/").filter(Boolean)[0] || "";
  return { owner, repo: firstPath, branch: "main", token: "" };
}

function saveConnection(next) {
  connection = next;
  sessionStorage.setItem("vidloom-owner-connection", JSON.stringify(next));
  renderConnection();
}

function toast(message, type = "success") {
  const item = document.createElement("div");
  item.className = `toast ${type}`;
  item.textContent = message;
  $("#toastRegion").append(item);
  setTimeout(() => item.remove(), 4200);
}

function humanStatus(value) {
  return String(value || "unknown").replaceAll("_", " ").replace(/\b\w/g, char => char.toUpperCase());
}

function formatTime(value, options = {}) {
  if (!value) return "Not yet";
  const date = new Date(value);
  if (Number.isNaN(date.valueOf())) return value;
  return new Intl.DateTimeFormat(undefined, {
    month: "short", day: "numeric", hour: "numeric", minute: "2-digit", ...options,
  }).format(date);
}

function relativeTime(value) {
  if (!value) return "Not synced";
  const seconds = Math.round((new Date(value) - new Date()) / 1000);
  const formatter = new Intl.RelativeTimeFormat(undefined, { numeric: "auto" });
  const units = [["day", 86400], ["hour", 3600], ["minute", 60]];
  for (const [unit, size] of units) {
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
  dot.className = ["ready", "connected", "online", "healthy", "local"].includes(value) ? "good" :
    ["failed", "offline", "not_connected"].includes(value) ? "bad" : "";
}

function renderConnection() {
  const connected = Boolean(connection.owner && connection.repo);
  setText("connectionLabel", connected ? `${connection.owner}/${connection.repo}` : "Connect GitHub");
  $("#repoOwner").value = connection.owner || "";
  $("#repoName").value = connection.repo || "";
  $("#repoBranch").value = connection.branch || "main";
  $("#repoToken").value = connection.token || "";
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
  items.slice(0, 6).forEach((item, index) => {
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
    meta.textContent = item.last_error || `Attempt ${item.attempts || 0} · locked genre`;
    copy.append(title, meta);
    const when = document.createElement("span");
    when.className = "queue-when";
    when.textContent = item.scheduled_publish_at ? formatTime(item.scheduled_publish_at) : "Next slot";
    const status = document.createElement(item.youtube_url ? "a" : "span");
    status.className = `status-pill ${item.status}`;
    status.textContent = item.status.toUpperCase();
    if (item.youtube_url) {
      status.href = item.youtube_url;
      status.target = "_blank";
      status.rel = "noreferrer";
    }
    row.append(order, copy, when, status);
    container.append(row);
  });
}

function renderEvents(events) {
  const container = $("#activityList");
  container.replaceChildren();
  (events || []).slice(0, 6).forEach(event => {
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

function render(data) {
  dashboard = data;
  const system = data.system || {};
  const health = data.health || {};
  const metrics = data.metrics || {};
  const queue = data.queue || [];
  const schedule = data.schedule || {};
  const current = queue.find(item => item.id === system.current_item_id) || queue.find(item => ["building", "qc", "uploading"].includes(item.status)) || queue[0];

  const live = $("#liveState");
  live.className = `live-state ${system.status === "healthy" ? "healthy" : system.status === "failed" ? "failed" : ""}`;
  $("#liveState b").textContent = humanStatus(system.status);
  setText("currentStage", system.current_stage || "Idle");
  const progressMap = { setup_required: 8, ready: 14, building: 62, qc: 78, uploading: 91, healthy: 100, failed: 50 };
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
  setText("metricQueued", metrics.queued || 0);
  setText("metricBuilding", metrics.building || 0);
  setText("metricScheduled", metrics.scheduled || 0);
  setText("metricPublished", metrics.published || 0);
  setText("navQueueCount", metrics.queued || 0);
  setText("queueSignal", metrics.queued >= 3 ? "Schedule covered" : `Needs ${Math.max(0, 3 - (metrics.queued || 0))} more`);
  setText("genreShort", data.channel.genre);
  setText("lastUpdated", relativeTime(data.generated_at));
  setHealth("runnerHealth", "runnerDot", health.runner);
  setHealth("youtubeHealth", "youtubeDot", health.youtube);
  setHealth("pipelineHealth", "pipelineDot", health.pipeline);
  setHealth("queueHealth", "queueDot", health.queue);
  setText("pauseAutomation", system.automation_enabled ? "Pause automation" : "Resume automation");
  $("#setupNotice").classList.toggle("hidden", system.status !== "setup_required" && health.youtube === "connected");
  renderQueue(queue);
  renderEvents(data.events);
  renderWeek(schedule.days);
}

async function loadState() {
  try {
    const response = await fetch(`${stateUrl}&refresh=${Date.now()}`, { cache: "no-store" });
    if (!response.ok) throw new Error(`Dashboard state returned ${response.status}`);
    render(await response.json());
  } catch (error) {
    toast(error.message, "error");
  }
}

function requireConnection({ token = false } = {}) {
  if (!connection.owner || !connection.repo || (token && !connection.token)) {
    $("#connectionDialog").showModal();
    throw new Error(token ? "Connect a session-only GitHub token first." : "Connect the GitHub repository first.");
  }
}

async function github(path, options = {}) {
  requireConnection({ token: true });
  const response = await fetch(`https://api.github.com${path}`, {
    ...options,
    headers: {
      Accept: "application/vnd.github+json",
      Authorization: `Bearer ${connection.token}`,
      "X-GitHub-Api-Version": "2022-11-28",
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  });
  if (!response.ok) {
    let message = `${response.status} ${response.statusText}`;
    try { message = (await response.json()).message || message; } catch (_) { /* response was not JSON */ }
    throw new Error(message);
  }
  if (response.status === 204) return null;
  return response.json();
}

async function dispatch(workflow, inputs = {}) {
  if (connection.owner && connection.repo && !connection.token) {
    window.open(`https://github.com/${encodeURIComponent(connection.owner)}/${encodeURIComponent(connection.repo)}/actions/workflows/${workflow}`, "_blank", "noopener,noreferrer");
    toast("Opened the authenticated GitHub workflow controls.");
    return;
  }
  await github(`/repos/${encodeURIComponent(connection.owner)}/${encodeURIComponent(connection.repo)}/actions/workflows/${workflow}/dispatches`, {
    method: "POST",
    body: JSON.stringify({ ref: connection.branch || "main", inputs }),
  });
  toast("Workflow accepted by GitHub Actions.");
}

function decodeBase64(value) {
  const bytes = Uint8Array.from(atob(value.replaceAll("\n", "")), char => char.charCodeAt(0));
  return new TextDecoder().decode(bytes);
}

function encodeBase64(value) {
  const bytes = new TextEncoder().encode(value);
  let binary = "";
  bytes.forEach(byte => { binary += String.fromCharCode(byte); });
  return btoa(binary);
}

async function commitQueueItem(form) {
  const base = `/repos/${encodeURIComponent(connection.owner)}/${encodeURIComponent(connection.repo)}/contents/automation/queue.json`;
  const current = await github(`${base}?ref=${encodeURIComponent(connection.branch || "main")}`);
  const document = JSON.parse(decodeBase64(current.content));
  const values = Object.fromEntries(new FormData(form));
  const slug = values.title.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 50);
  const id = `${slug}-${Date.now().toString(36)}`;
  let requested = null;
  if (values.requested_publish_at) {
    const localDate = new Date(values.requested_publish_at);
    if (Number.isNaN(localDate.valueOf())) throw new Error("Invalid requested publish time");
    requested = localDate.toISOString();
  }
  document.items.push({
    id,
    project_path: values.project_path,
    genre: "cinema_scene_breakdown",
    title: values.title,
    description: values.description,
    tags: String(values.tags || "").split(",").map(tag => tag.trim()).filter(Boolean),
    status: "ready",
    requested_publish_at: requested,
    scheduled_publish_at: null,
    youtube_id: null,
    youtube_url: null,
    attempts: 0,
    last_error: null,
  });
  await github(base, {
    method: "PUT",
    body: JSON.stringify({
      message: `queue: add ${id}`,
      content: encodeBase64(`${JSON.stringify(document, null, 2)}\n`),
      sha: current.sha,
      branch: connection.branch || "main",
    }),
  });
  toast("Project committed to the production queue.");
}

function bindEvents() {
  $("#openConnection").addEventListener("click", () => $("#connectionDialog").showModal());
  $("#setupButton").addEventListener("click", () => $("#connectionDialog").showModal());
  $("#refreshState").addEventListener("click", loadState);
  $("#openProduction").addEventListener("click", () => location.hash = "production");
  $("#addQueueItem").addEventListener("click", () => {
    try { requireConnection({ token: true }); $("#queueDialog").showModal(); } catch (error) { toast(error.message, "error"); }
  });
  $("#connectionForm").addEventListener("submit", event => {
    event.preventDefault();
    const values = Object.fromEntries(new FormData(event.currentTarget));
    saveConnection({ owner: values.owner.trim(), repo: values.repo.trim(), branch: values.branch.trim() || "main", token: values.token.trim() });
    $("#connectionDialog").close();
    toast(values.token ? "Direct controls connected for this tab." : "Repository connected in read-only mode.");
  });
  $("#queueForm").addEventListener("submit", async event => {
    event.preventDefault();
    try {
      await commitQueueItem(event.currentTarget);
      event.currentTarget.reset();
      $("#queueDialog").close();
    } catch (error) { toast(error.message, "error"); }
  });
  $("#runCycle").addEventListener("click", async () => {
    try { await dispatch(workflowFiles.production, { mode: "full", item_id: "", dry_run: "false" }); }
    catch (error) { toast(error.message, "error"); }
  });
  $("#pauseAutomation").addEventListener("click", async () => {
    try {
      const action = dashboard?.system?.automation_enabled ? "pause" : "resume";
      await dispatch(workflowFiles.control, { action });
    } catch (error) { toast(error.message, "error"); }
  });
  document.querySelectorAll(".nav-item").forEach(link => link.addEventListener("click", () => {
    document.querySelectorAll(".nav-item").forEach(item => item.classList.remove("active"));
    link.classList.add("active");
  }));
}

renderConnection();
bindEvents();
loadState();
setInterval(loadState, 60_000);

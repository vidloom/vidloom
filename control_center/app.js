"use strict";

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
let dashboard = null;
let authenticated = false;
let apiAvailable = true;
let settingsHydrated = false;

const PAGE_COPY = {
  overview: ["COMMAND CENTER", "Your channel, on autopilot.", "A five-minute view of production, releases, performance, and risk."],
  autopilot: ["AUTOPILOT", "Set it once. Let it run.", "Control production pace, backlog, publishing, recovery, and spending."],
  queue: ["QUEUE & SCHEDULE", "Everything Vidloom is making.", "Inspect active work, finished inventory, failures, and assigned release slots."],
  analytics: ["ANALYTICS", "Learn without chasing noise.", "Channel outcomes and evidence-based feedback for future videos."],
  activity: ["ACTIVITY & COSTS", "Know what ran and what it cost.", "Workflow history, operating events, infrastructure health, and budget protection."],
  settings: ["SETTINGS", "The channel's permanent rules.", "Content memory, production standards, integrations, and alerts."],
};

function setText(id, value) { const node = document.getElementById(id); if (node) node.textContent = value ?? "—"; }
function human(value) { return String(value || "unknown").replaceAll("_", " ").replace(/\b\w/g, c => c.toUpperCase()); }
function number(value) { return value === null || value === undefined ? "—" : new Intl.NumberFormat().format(value); }
function money(value) { return `$${Number(value || 0).toFixed(2)}`; }
function formatDate(value, options = {}) { const date = new Date(value); return !value || Number.isNaN(date.valueOf()) ? "Not yet" : new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric", hour: "numeric", minute: "2-digit", ...options }).format(date); }
function relative(value) {
  if (!value) return "Not synced";
  const seconds = Math.round((new Date(value) - new Date()) / 1000);
  const formatter = new Intl.RelativeTimeFormat(undefined, { numeric: "auto" });
  for (const [unit, size] of [["day", 86400], ["hour", 3600], ["minute", 60]]) if (Math.abs(seconds) >= size) return formatter.format(Math.round(seconds / size), unit);
  return "just now";
}
function toast(message, type = "success") { const node = document.createElement("div"); node.className = `toast ${type}`; node.textContent = message; $("#toastRegion").append(node); setTimeout(() => node.remove(), 4500); }
function setBusy(button, busy, label = "Working…") { if (!button) return; if (busy) { button.dataset.label = button.textContent; button.textContent = label; button.disabled = true; } else { button.textContent = button.dataset.label || button.textContent; button.disabled = false; } }

async function api(path, options = {}) {
  const response = await fetch(`/api${path}`, { ...options, credentials: "same-origin", headers: { "content-type": "application/json", ...(options.headers || {}) } });
  let payload = null;
  try { payload = await response.json(); } catch (_) { /* empty */ }
  if (!response.ok) { const error = new Error(payload?.error || `${response.status} ${response.statusText}`); error.status = response.status; throw error; }
  return payload;
}

function showPage(name) {
  const page = PAGE_COPY[name] ? name : "overview";
  $$(".page-view").forEach(node => node.classList.toggle("active", node.dataset.page === page));
  $$(".nav-item").forEach(node => node.classList.toggle("active", node.dataset.pageLink === page));
  const [kicker, title, description] = PAGE_COPY[page];
  setText("pageKicker", kicker); setText("pageTitle", title); setText("pageDescription", description);
  if (location.hash !== `#${page}`) history.replaceState(null, "", `#${page}`);
  window.scrollTo({ top: 0, behavior: "instant" });
}

function renderSession() {
  setText("connectionLabel", authenticated ? "Secure session active" : apiAvailable ? "Sign in" : "Static preview");
  $("#openConnection").classList.toggle("authenticated", authenticated);
  const notice = $("#setupNotice");
  if (!authenticated) {
    notice.classList.remove("hidden");
    setText("noticeTitle", apiAvailable ? "Owner sign-in required" : "Cloud control plane unavailable");
    setText("noticeCopy", apiAvailable ? "Sign in to load private channel state and use controls." : "The static interface loaded, but live API controls are unavailable.");
  }
  $$("button, input, select, textarea", $("#main")).forEach(node => { if (!["refreshState", "setupButton"].includes(node.id)) node.disabled = !authenticated; });
}

async function checkSession() {
  try { const health = await api("/health", { headers: {} }); apiAvailable = true; authenticated = Boolean(health.authenticated); }
  catch (_) { apiAvailable = false; authenticated = false; }
  renderSession(); return authenticated;
}

function setHealth(id, dotId, value) {
  setText(id, human(value));
  const dot = document.getElementById(dotId);
  if (!dot) return;
  dot.className = ["ready", "connected", "configured", "complete", "pass", "online", "healthy", "local", "active", "standing_by"].includes(value) ? "good" : ["failed", "offline", "not_connected", "blocked"].includes(value) ? "bad" : "";
}

function currentCreation(data) {
  const active = new Set(["planned", "analyzing", "scripting", "voicing", "editing", "build_ready", "building", "qc", "uploading"]);
  return data.queue?.find(item => active.has(item.status)) || data.ideas?.find(item => active.has(item.status)) || null;
}

function renderPipeline(data) {
  const item = currentCreation(data);
  const auto = data.autopilot || {};
  const system = data.system || {};
  const running = system.creator_enabled || system.publishing_enabled;
  setText("automationHeadline", running ? "Running automatically" : "Autopilot paused");
  setText("automationDetail", auto.next_action || "Waiting for the next inventory decision.");
  setText("creatorStateLabel", system.creator_enabled ? "On" : "Paused");
  setText("publishingStateLabel", system.publishing_enabled ? "On" : "Paused");
  setText("lastUpdated", relative(data.generated_at));
  setText("masterToggle", running ? "Pause autopilot" : "Resume autopilot");
  $("#masterToggle").classList.toggle("button-danger", running);

  if (item) {
    setText("currentStage", item.stage || human(item.status));
    setText("currentStatus", human(item.status).toUpperCase());
    $("#currentStatus").className = `status-pill ${item.status}`;
    setText("currentTitle", item.title || "Untitled production");
    setText("currentMeta", `${item.origin === "manual" ? "Owner request" : "Autopilot"} · ${Number(item.progress || 0)}% complete`);
    setText("stageNumber", String(Math.max(1, Math.ceil(Number(item.progress || 0) / 15))).padStart(2, "0"));
    $("#pipelineProgress").style.width = `${Math.max(2, Math.min(100, Number(item.progress || 0)))}%`;
  } else {
    setText("currentStage", auto.mode === "standing_by" ? "Release vault is full" : auto.mode === "paused" ? "Creator paused" : "Researching the next scene");
    setText("currentStatus", human(auto.mode || "idle").toUpperCase());
    $("#currentStatus").className = `status-pill ${auto.mode || "held"}`;
    setText("currentTitle", auto.next_action || "No active creation");
    setText("currentMeta", `Inventory is checked every ${auto.interval_hours || 2} hours.`);
    setText("stageNumber", "00"); $("#pipelineProgress").style.width = "0%";
  }
}

function renderOverview(data) {
  const metrics = data.metrics || {}; const auto = data.autopilot || {}; const analytics = data.analytics || {}; const weekly = analytics.weekly || {};
  setText("metricPublished", metrics.published || 0); setText("metricScheduled", metrics.scheduled || 0); setText("metricFailures", metrics.needs_attention || 0); setText("metricFinished", auto.finished || 0);
  setText("failureSignal", metrics.needs_attention ? "Open the attention queue" : "No open failures");
  setText("bufferSignal", `Target: ${auto.target || 0} videos`);
  const scheduled = [...(data.scheduled_videos || [])].sort((a, b) => String(a.scheduled_publish_at).localeCompare(String(b.scheduled_publish_at)));
  const nextItem = scheduled[0]; const nextValue = nextItem?.scheduled_publish_at || data.schedule?.next_publish_at; const next = nextValue ? new Date(nextValue) : null;
  setText("nextDay", next && !Number.isNaN(next.valueOf()) ? String(next.getDate()).padStart(2, "0") : "—");
  setText("nextMonth", next && !Number.isNaN(next.valueOf()) ? new Intl.DateTimeFormat(undefined, { month: "short" }).format(next) : "—");
  setText("nextTime", next && !Number.isNaN(next.valueOf()) ? new Intl.DateTimeFormat(undefined, { hour: "numeric", minute: "2-digit" }).format(next) : "—");
  setText("nextTimezone", data.schedule?.timezone || "Asia/Kolkata"); setText("nextVideoTitle", nextItem?.title || "Open slot — awaiting finished video");
  setText("weeklyViews", number(weekly.views)); setText("weeklySubscribers", weekly.subscribers_gained === null || weekly.subscribers_gained === undefined ? "—" : `${weekly.subscribers_gained >= 0 ? "+" : ""}${weekly.subscribers_gained}`); setText("weeklyViewed", weekly.average_percentage_viewed === null || weekly.average_percentage_viewed === undefined ? "—" : `${weekly.average_percentage_viewed.toFixed(1)}%`);
  setText("analyticsMessage", analytics.message || "Analytics will appear after channel sync.");
  renderAttention(data.attention_videos || [], data.costs || {}); renderReleases("releasePreview", data.finished_videos || [], auto, 4);
}

function renderAttention(items, costs) {
  const container = $("#attentionList"); container.replaceChildren();
  const alerts = items.map(item => ({ title: item.title, detail: item.last_error || item.stage || human(item.status) }));
  if (costs.creation_allowed === false) alerts.push({ title: "Creation budget stopped", detail: "The monthly safety threshold has been reached." });
  setText("attentionCount", alerts.length); setText("attentionTitle", alerts.length ? `${alerts.length} item${alerts.length === 1 ? "" : "s"} need review` : "No urgent problems");
  if (!alerts.length) { const p = document.createElement("p"); p.textContent = "Builds, release automation, and budget protection report healthy."; container.append(p); return; }
  alerts.slice(0, 4).forEach(alert => { const row = document.createElement("div"); const strong = document.createElement("strong"); strong.textContent = alert.title; const small = document.createElement("small"); small.textContent = alert.detail; row.append(strong, small); container.append(row); });
}

function renderReleases(targetId, items, auto, limit = 20) {
  const container = document.getElementById(targetId); if (!container) return; container.replaceChildren();
  const videos = items.filter(item => ["ready", "scheduled", "published"].includes(item.status));
  if (!videos.length) { const empty = document.createElement("div"); empty.className = "vault-empty"; const title = document.createElement("strong"); title.textContent = "No finished videos yet"; const copy = document.createElement("span"); copy.textContent = `Autopilot has ${auto.gap || 0} open buffer slots and will keep creating until the target is full.`; empty.append(title, copy); container.append(empty); return; }
  videos.slice(0, limit).forEach((item, index) => {
    const card = document.createElement("article"); card.className = "release-card";
    const art = document.createElement("div"); art.className = `release-art art-${index % 4}`; const tag = document.createElement("span"); tag.textContent = item.status.toUpperCase(); const play = document.createElement("b"); play.textContent = "▶"; art.append(tag, play);
    const body = document.createElement("div"); body.className = "release-body"; const title = document.createElement("strong"); title.textContent = item.title; const meta = document.createElement("span"); meta.textContent = item.scheduled_publish_at ? formatDate(item.scheduled_publish_at) : human(item.status); body.append(title, meta);
    if (item.youtube_url) { const link = document.createElement("a"); Object.assign(link, { href: item.youtube_url, target: "_blank", rel: "noreferrer", textContent: "Open on YouTube ↗" }); body.append(link); }
    card.append(art, body); container.append(card);
  });
}

function renderWeek(days = []) {
  const active = new Set(days.map(day => day.slice(0, 3).toLowerCase())); const container = $("#weekStrip"); container.replaceChildren();
  ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].forEach(day => { const node = document.createElement("div"); node.className = `week-day ${active.has(day.toLowerCase()) ? "active" : ""}`; const label = document.createElement("strong"); label.textContent = day; node.append(label); container.append(node); });
}

function renderSchedule(items = []) {
  const container = $("#scheduleList"); container.replaceChildren();
  if (!items.length) { const p = document.createElement("p"); p.className = "empty-note"; p.textContent = "No upload is scheduled yet. Finished videos will be assigned to the next free slot."; container.append(p); return; }
  items.slice(0, 8).forEach(item => { const row = document.createElement("div"); const title = document.createElement("strong"); title.textContent = item.title; const time = document.createElement("span"); time.textContent = formatDate(item.scheduled_publish_at); row.append(title, time); container.append(row); });
}

function renderQueue(data) {
  const metrics = data.metrics || {}; const auto = data.autopilot || {};
  setText("metricBuilding", auto.active || 0); setText("metricReady", metrics.ready || 0); setText("queueScheduled", metrics.scheduled || 0); setText("queueAttention", metrics.needs_attention || 0); setText("navQueueCount", (auto.active || 0) + (metrics.needs_attention || 0));
  setText("fullVaultSummary", `${auto.finished || 0} finished · ${auto.target || 0} target`); setText("vaultSummary", `${auto.finished || 0}/${auto.target || 0} finished · Open queue →`);
  renderReleases("releaseGrid", data.finished_videos || [], auto); renderWeek(data.schedule?.days || []); renderSchedule(data.scheduled_videos || []);
  const container = $("#queueList"); container.replaceChildren(); const queueIds = new Set((data.queue || []).map(item => item.id)); const rows = [...(data.ideas || []).filter(item => !queueIds.has(item.id)), ...(data.queue || []).filter(item => !["ready", "scheduled", "published"].includes(item.status))];
  if (!rows.length) { const p = document.createElement("div"); p.className = "queue-empty"; p.textContent = auto.mode === "standing_by" ? "The release vault is full. Vidloom is correctly standing by." : "No active production is visible yet; the next creator cycle will fill the backlog."; container.append(p); return; }
  rows.slice(0, 12).forEach((item, index) => { const row = document.createElement("div"); row.className = "queue-row"; const order = document.createElement("span"); order.className = "queue-index"; order.textContent = String(index + 1).padStart(2, "0"); const copy = document.createElement("div"); copy.className = "queue-copy"; const title = document.createElement("strong"); title.textContent = item.title || "Untitled idea"; const meta = document.createElement("small"); meta.textContent = item.last_error || `${item.stage || human(item.status)} · ${item.origin === "manual" ? "Owner request" : "Autopilot"}`; copy.append(title, meta); const progress = document.createElement("span"); progress.className = "queue-when"; progress.textContent = `${Number(item.progress || 0)}%`; const status = document.createElement("span"); status.className = `status-pill ${item.status}`; status.textContent = human(item.status).toUpperCase(); row.append(order, copy, progress, status); container.append(row); });
}

function hydrateForms(settings) {
  if (settingsHydrated || !settings) return; settingsHydrated = true;
  const auto = settings.autopilot || {}; $("#creatorEnabled").checked = Boolean(auto.creator_enabled); $("#publishingEnabled").checked = Boolean(auto.publishing_enabled); $("#automaticRetries").checked = Boolean(auto.automatic_retries); $("#videosPerDay").value = String(auto.videos_per_day || 1); $("#firstPublishTime").value = auto.first_publish_time || "20:00"; $("#timezone").value = auto.timezone || "Asia/Kolkata"; $("#bufferTarget").value = auto.finished_buffer_target || 6; $("#monthlyBudget").value = auto.monthly_modal_budget_usd || 10; const mode = $(`input[name="publishing_mode"][value="${auto.publishing_mode || "fully_automatic"}"]`); if (mode) mode.checked = true;
  const brain = settings.content_brain || {}; $("#moviePreferences").value = (brain.movie_preferences || []).join("\n"); $("#excludedMovies").value = (brain.excluded_movies || []).join("\n"); $("#preventDuplicateScenes").checked = Boolean(brain.prevent_duplicate_scenes); $("#preventDuplicateHooks").checked = Boolean(brain.prevent_duplicate_hooks);
  const rules = settings.production_rules || {}; $("#durationMin").value = rules.duration_min_seconds || 24; $("#durationMax").value = rules.duration_max_seconds || 34; $("#narrationStyle").value = rules.narration_style || ""; $("#subtitlePreset").value = rules.subtitle_preset || ""; $("#musicMix").value = rules.music_mix || ""; $("#cropTracking").value = rules.crop_tracking || "";
  const note = settings.notifications || {}; $("#notifyWeekly").checked = Boolean(note.weekly_summary); $("#notifyFailures").checked = Boolean(note.upload_failures); $("#notifyCopyright").checked = Boolean(note.copyright_claims); $("#notifyCredits").checked = Boolean(note.credit_warnings); $("#notificationEmail").value = note.email || "";
}

function autopilotPayload() {
  return { creator_enabled: $("#creatorEnabled").checked, publishing_enabled: $("#publishingEnabled").checked, videos_per_day: Number($("#videosPerDay").value), first_publish_time: $("#firstPublishTime").value, timezone: $("#timezone").value.trim(), publishing_mode: $('input[name="publishing_mode"]:checked')?.value || "fully_automatic", automatic_retries: $("#automaticRetries").checked, finished_buffer_target: Number($("#bufferTarget").value), monthly_modal_budget_usd: Number($("#monthlyBudget").value) };
}

function renderAutopilot(data) {
  const auto = data.autopilot || {}; const costs = data.costs || {}; hydrateForms(data.settings);
  setText("autopilotDecision", human(auto.mode)); setText("autopilotReason", auto.next_action || "Inventory is evaluated every two hours."); setText("autoFinished", auto.finished || 0); setText("autoActive", auto.active || 0); setText("autoGap", auto.gap || 0); setText("autopilotSpend", money(costs.estimated_spend_usd));
  const pct = Math.min(100, Number(costs.estimated_spend_usd || 0) / Math.max(1, Number(costs.budget_limit_usd || 1)) * 100); $("#autopilotBudgetBar").style.width = `${pct}%`;
}

function renderAnalytics(data) {
  const analytics = data.analytics || {}; const channel = analytics.channel || {}; const weekly = analytics.weekly || {};
  setText("analyticsViews", number(channel.views)); setText("analyticsSubscribers", number(channel.subscribers)); setText("analyticsWeeklyViews", number(weekly.views)); setText("analyticsApv", weekly.average_percentage_viewed === null || weekly.average_percentage_viewed === undefined ? "—" : `${weekly.average_percentage_viewed.toFixed(1)}%`); setText("analyticsGenerated", relative(analytics.generated_at)); setText("retentionStatus", analytics.retention_scope_connected ? "Audience-retention scope connected." : analytics.message || "Retention scope is not connected yet.");
  const container = $("#videoAnalytics"); container.replaceChildren(); const videos = analytics.videos || [];
  if (!videos.length) { const p = document.createElement("p"); p.className = "empty-note"; p.textContent = "Published-video statistics will appear after the first successful YouTube sync."; container.append(p); return; }
  const header = document.createElement("div"); header.className = "table-row table-head"; ["Video", "Views", "Likes", "Comments"].forEach(text => { const span = document.createElement("span"); span.textContent = text; header.append(span); }); container.append(header);
  videos.slice(0, 20).forEach(video => { const row = document.createElement("div"); row.className = "table-row"; [video.title || video.id, number(video.views), number(video.likes), number(video.comments)].forEach(text => { const span = document.createElement("span"); span.textContent = text; row.append(span); }); container.append(row); });
}

function renderEvents(events = []) {
  const container = $("#activityList"); container.replaceChildren();
  if (!events.length) { const p = document.createElement("p"); p.className = "empty-note"; p.textContent = "No system events recorded."; container.append(p); return; }
  events.slice(0, 12).forEach(event => { const row = document.createElement("div"); row.className = `activity-item ${event.level || "info"}`; const p = document.createElement("p"); p.textContent = event.message; const time = document.createElement("time"); time.textContent = event.at ? formatDate(event.at) : "Setup"; row.append(p, time); container.append(row); });
}

function renderCosts(data) {
  const costs = data.costs || {}; setText("costSpent", money(costs.estimated_spend_usd)); setText("costLimit", money(costs.budget_limit_usd)); setText("costRemaining", money(costs.remaining_usd)); setText("costSource", costs.source || "Cost estimate unavailable."); const pct = Math.min(100, Number(costs.estimated_spend_usd || 0) / Math.max(1, Number(costs.budget_limit_usd || 1)) * 100); $("#budgetRing").style.setProperty("--budget", `${pct * 3.6}deg`);
  const health = data.health || {}; setHealth("creatorHealth", "creatorDot", health.creator); setHealth("runnerHealth", "runnerDot", health.runner); setHealth("youtubeHealth", "youtubeDot", health.youtube); setHealth("pipelineHealth", "pipelineDot", health.pipeline); setHealth("aiHealth", "aiDot", health.ai); setHealth("queueHealth", "queueDot", health.queue); renderEvents(data.events || []);
  setText("settingsYoutube", human(health.youtube)); setText("settingsGroq", human(health.ai)); setText("settingsRunner", human(health.runner));
}

function render(data) {
  dashboard = data; setText("genreShort", data.channel?.genre || "Cinema breakdowns"); renderPipeline(data); renderOverview(data); renderQueue(data); renderAutopilot(data); renderAnalytics(data); renderCosts(data); updateClock();
  if (authenticated) $("#setupNotice").classList.toggle("hidden", data.health?.youtube === "connected");
}

function renderRuns(runs = []) {
  const container = $("#runList"); container.replaceChildren();
  if (!runs.length) { const p = document.createElement("p"); p.className = "empty-note"; p.textContent = authenticated ? "No workflow activity yet." : "Sign in to view workflow activity."; container.append(p); return; }
  runs.slice(0, 10).forEach(run => { const row = document.createElement("a"); row.className = "run-row"; Object.assign(row, { href: run.html_url, target: "_blank", rel: "noreferrer" }); const dot = document.createElement("i"); dot.className = run.status !== "completed" ? "live" : run.conclusion === "success" ? "success" : run.conclusion === "cancelled" ? "muted" : "failed"; const copy = document.createElement("span"); const title = document.createElement("strong"); title.textContent = run.name; const meta = document.createElement("small"); meta.textContent = `${human(run.status === "completed" ? run.conclusion : run.status)} · ${relative(run.created_at)}`; copy.append(title, meta); const arrow = document.createElement("b"); arrow.textContent = "↗"; row.append(dot, copy, arrow); container.append(row); });
}

async function loadState({ quiet = false } = {}) {
  if (!authenticated) return;
  try { const [state, runs] = await Promise.all([api("/state"), api("/runs")]); render(state); renderRuns(runs.runs || []); if (!quiet) toast("Live channel state refreshed."); }
  catch (error) { if (error.status === 401) { authenticated = false; renderSession(); $("#connectionDialog").showModal(); } else if (!quiet) toast(error.message, "error"); }
}

async function performAction(action, button) {
  setBusy(button, true);
  try { const result = await api("/action", { method: "POST", body: JSON.stringify({ action }) }); toast(result.message || "Action accepted."); setTimeout(() => loadState({ quiet: true }), 2500); }
  catch (error) { toast(error.message, "error"); }
  finally { setBusy(button, false); }
}

async function saveSettings(payload, button, stateId) {
  setBusy(button, true, "Saving…");
  try { const result = await api("/settings", { method: "PATCH", body: JSON.stringify(payload) }); toast(result.message || "Settings saved."); settingsHydrated = false; setText(stateId, "Saved. Dashboard state is refreshing."); setTimeout(() => loadState({ quiet: true }), 2200); }
  catch (error) { toast(error.message, "error"); setText(stateId, error.message); }
  finally { setBusy(button, false); }
}

function updateClock() {
  const now = new Date(); setText("liveClock", new Intl.DateTimeFormat("en-GB", { timeZone: dashboard?.schedule?.timezone || "Asia/Kolkata", hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false }).format(now));
  const nextItem = dashboard?.scheduled_videos?.[0]; const value = nextItem?.scheduled_publish_at || dashboard?.schedule?.next_publish_at; if (!value) return setText("nextCountdown", "Awaiting slot"); const next = new Date(value); const remaining = Math.max(0, next - now); const days = Math.floor(remaining / 86400000); const hours = Math.floor((remaining % 86400000) / 3600000); const minutes = Math.floor((remaining % 3600000) / 60000); setText("nextCountdown", `${days ? `${days}d ` : ""}${hours}h ${minutes}m`);
}

function requireOwner() { if (authenticated) return true; if (apiAvailable) $("#connectionDialog").showModal(); toast("Unlock the owner console first.", "error"); return false; }

function bindEvents() {
  $$('[data-page-link]').forEach(link => link.addEventListener("click", event => { event.preventDefault(); showPage(link.dataset.pageLink); })); window.addEventListener("hashchange", () => showPage(location.hash.slice(1)));
  $("#openConnection").addEventListener("click", async () => { if (!authenticated) return $("#connectionDialog").showModal(); if (!confirm("End this secure owner session?")) return; await api("/auth/logout", { method: "POST", body: "{}" }); authenticated = false; dashboard = null; renderSession(); renderRuns([]); });
  $("#setupButton").addEventListener("click", () => apiAvailable && $("#connectionDialog").showModal()); $("#refreshState").addEventListener("click", () => requireOwner() && loadState());
  $("#masterToggle").addEventListener("click", event => { if (!requireOwner()) return; const running = dashboard?.system?.creator_enabled || dashboard?.system?.publishing_enabled; const action = running ? "pause" : "resume"; if (action === "resume" && !confirm("Resume autonomous creation and automatic publishing?")) return; performAction(action, event.currentTarget); });
  $("#requestVideo").addEventListener("click", () => requireOwner() && $("#creativeDialog").showModal());
  $("#connectionForm").addEventListener("submit", async event => { event.preventDefault(); const button = $("#saveConnection"); setBusy(button, true, "Unlocking…"); try { await api("/auth/login", { method: "POST", body: JSON.stringify({ password: $("#controlPassword").value }) }); authenticated = true; $("#controlPassword").value = ""; $("#connectionDialog").close(); renderSession(); await loadState({ quiet: true }); toast("Owner controls unlocked for 12 hours."); } catch (error) { toast(error.message, "error"); } finally { setBusy(button, false); } });
  $("#creativeForm").addEventListener("submit", async event => { event.preventDefault(); const button = $("#submitCreativeRequest"); setBusy(button, true, "Commissioning…"); try { const prompt = new FormData(event.currentTarget).get("prompt"); const result = await api("/create", { method: "POST", body: JSON.stringify({ prompt }) }); toast(result.message || "Request accepted."); event.currentTarget.reset(); $("#creativeDialog").close(); setTimeout(() => loadState({ quiet: true }), 2500); } catch (error) { toast(error.message, "error"); } finally { setBusy(button, false); } });
  $("#autopilotForm").addEventListener("submit", event => { event.preventDefault(); if (requireOwner()) saveSettings({ autopilot: autopilotPayload() }, $("#saveAutopilot"), "autopilotSaveState"); });
  $("#settingsForm").addEventListener("submit", event => { event.preventDefault(); if (!requireOwner()) return; const split = id => $(id).value.split("\n").map(value => value.trim()).filter(Boolean); saveSettings({ autopilot: autopilotPayload(), content_brain: { movie_preferences: split("#moviePreferences"), excluded_movies: split("#excludedMovies"), prevent_duplicate_scenes: $("#preventDuplicateScenes").checked, prevent_duplicate_hooks: $("#preventDuplicateHooks").checked }, production_rules: { duration_min_seconds: Number($("#durationMin").value), duration_max_seconds: Number($("#durationMax").value), narration_style: $("#narrationStyle").value.trim(), subtitle_preset: $("#subtitlePreset").value.trim(), music_mix: $("#musicMix").value.trim(), crop_tracking: $("#cropTracking").value.trim() }, notifications: { weekly_summary: $("#notifyWeekly").checked, upload_failures: $("#notifyFailures").checked, copyright_claims: $("#notifyCopyright").checked, credit_warnings: $("#notifyCredits").checked, email: $("#notificationEmail").value.trim() } }, $("#saveSettings"), "settingsSaveState"); });
}

bindEvents(); showPage(location.hash.slice(1) || "overview"); updateClock(); checkSession().then(ok => ok ? loadState({ quiet: true }) : renderRuns([])); setInterval(() => authenticated && loadState({ quiet: true }), 30000); setInterval(updateClock, 1000);

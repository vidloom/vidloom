const COOKIE_NAME = "vidloom_session";
const SESSION_TTL_SECONDS = 60 * 60 * 12;
const JSON_HEADERS = {
  "content-type": "application/json; charset=utf-8",
  "cache-control": "no-store",
  "x-content-type-options": "nosniff",
};

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname.startsWith("/data/")) return json({ error: "Not found" }, 404);
    if (!url.pathname.startsWith("/api/")) return env.ASSETS.fetch(request);

    try {
      if (url.pathname === "/api/health" && request.method === "GET") {
        return json({ ok: true, service: "vidloom-control", authenticated: await isAuthenticated(request, env) });
      }
      if (url.pathname === "/api/auth/login" && request.method === "POST") return login(request, env);
      if (url.pathname === "/api/auth/logout" && request.method === "POST") {
        assertSameOrigin(request);
        return json({ ok: true }, 200, { "set-cookie": expiredCookie(request) });
      }

      if (!await isAuthenticated(request, env)) return json({ error: "Authentication required" }, 401);

      if (url.pathname === "/api/state" && request.method === "GET") {
        if (env.MODAL_API_URL) return modal(env, "/api/state");
        return json(await readRepoJson(env, "control_center/data/dashboard.json"));
      }
      if (url.pathname === "/api/runs" && request.method === "GET") {
        const data = await github(env, `/actions/runs?per_page=12`);
        return json({ runs: data.workflow_runs || [] });
      }
      if (url.pathname === "/api/action" && request.method === "POST") {
        assertSameOrigin(request);
        const body = await readBody(request);
        if (env.MODAL_API_URL) return modal(env, "/api/action", { method: "POST", body });
        const spec = actionSpec(body.action, body);
        await github(env, `/actions/workflows/${spec.workflow}/dispatches`, {
          method: "POST",
          body: { ref: env.GITHUB_BRANCH || "main", inputs: spec.inputs },
        });
        return json({ ok: true, message: spec.message }, 202);
      }
      if (url.pathname === "/api/create" && request.method === "POST") {
        assertSameOrigin(request);
        const body = await readBody(request);
        const prompt = String(body.prompt || "").trim();
        if (!prompt) throw new HttpError(400, "Describe the video you want Vidloom to create");
        if (prompt.length > 1200) throw new HttpError(400, "Creative request must be 1200 characters or fewer");
        if (env.MODAL_API_URL) return modal(env, "/api/create", { method: "POST", body: { prompt } });
        const spec = actionSpec("create", { prompt });
        await github(env, `/actions/workflows/${spec.workflow}/dispatches`, {
          method: "POST",
          body: { ref: env.GITHUB_BRANCH || "main", inputs: spec.inputs },
        });
        return json({ ok: true, message: spec.message }, 202);
      }
      if (url.pathname === "/api/settings" && request.method === "PATCH") {
        assertSameOrigin(request);
        const body = await readBody(request);
        if (env.MODAL_API_URL) return modal(env, "/api/settings", { method: "PATCH", body });
        const current = await readRepoDocument(env, "automation/config.json");
        const updated = applySettings(current.value, body);
        await writeRepoJson(env, "automation/config.json", updated, current.sha, "settings: update Vidloom autopilot");
        const refresh = actionSpec("refresh");
        await github(env, `/actions/workflows/${refresh.workflow}/dispatches`, {
          method: "POST",
          body: { ref: env.GITHUB_BRANCH || "main", inputs: refresh.inputs },
        });
        return json({ ok: true, settings: publicSettings(updated), message: "Autopilot settings saved" });
      }
      if (url.pathname === "/api/queue" && request.method === "POST") {
        assertSameOrigin(request);
        const body = await readBody(request);
        const item = validateQueueItem(body);
        const current = await readRepoDocument(env, "automation/queue.json");
        current.value.items.push(item);
        await writeRepoJson(env, "automation/queue.json", current.value, current.sha, `queue: add ${item.id}`);
        return json({ ok: true, item }, 201);
      }
      if (url.pathname.startsWith("/api/queue/") && request.method === "PATCH") {
        assertSameOrigin(request);
        const id = decodeURIComponent(url.pathname.slice("/api/queue/".length));
        const body = await readBody(request);
        const allowed = new Set(["ready", "held"]);
        if (!allowed.has(body.status)) throw new HttpError(400, "Status must be ready or held");
        const current = await readRepoDocument(env, "automation/queue.json");
        const item = current.value.items.find(entry => entry.id === id);
        if (!item) throw new HttpError(404, "Queue item not found");
        item.status = body.status;
        item.last_error = body.status === "held" ? "Held from control center" : null;
        await writeRepoJson(env, "automation/queue.json", current.value, current.sha, `queue: ${body.status} ${id}`);
        return json({ ok: true, item });
      }
      return json({ error: "Not found" }, 404);
    } catch (error) {
      const status = error instanceof HttpError ? error.status : 500;
      const message = status === 500 ? "Control plane request failed" : error.message;
      if (status === 500) console.error(error);
      return json({ error: message }, status);
    }
  },
};

export function actionSpec(action, body = {}) {
  if (["pause", "resume", "refresh", "creator_pause", "creator_resume", "publishing_pause", "publishing_resume"].includes(action)) {
    return { workflow: "control.yml", inputs: { action }, message: `${action} accepted` };
  }
  if (action === "create") {
    const prompt = String(body.prompt || "").trim();
    if (!prompt) throw new HttpError(400, "A creative request is required");
    return {
      workflow: "autopilot.yml",
      inputs: { request: prompt, force: "true" },
      message: "Creative request accepted. Vidloom will choose the title, script, footage plan, and metadata.",
    };
  }
  if (action === "autopilot") {
    return {
      workflow: "autopilot.yml",
      inputs: { request: "", force: "true" },
      message: "Autonomous creator started. It will choose the idea and produce the next video.",
    };
  }
  if (action === "audit") {
    return {
      workflow: "ai-director.yml",
      inputs: { project_path: String(body.project_path || ""), refresh: "true" },
      message: "AI audit queued",
    };
  }
  if (action === "dry_run" || action === "build" || action === "upload") {
    const dry = action === "dry_run";
    return {
      workflow: "production-cycle.yml",
      inputs: {
        mode: action === "build" ? "build" : action === "upload" ? "upload" : "full",
        item_id: String(body.item_id || ""),
        dry_run: dry ? "true" : "false",
      },
      message: dry ? "Safe production rehearsal queued" : "Production cycle queued",
    };
  }
  throw new HttpError(400, "Unknown action");
}

async function login(request, env) {
  assertSameOrigin(request);
  const body = await readBody(request);
  if (!body.password || !await safeEqual(String(body.password), env.CONTROL_PASSWORD || "")) {
    return json({ error: "Wrong control password" }, 401);
  }
  const now = Math.floor(Date.now() / 1000);
  const token = await signToken({ sub: "owner", iat: now, exp: now + SESSION_TTL_SECONDS }, env.SESSION_SECRET);
  return json({ ok: true, expires_in: SESSION_TTL_SECONDS }, 200, { "set-cookie": sessionCookie(request, token) });
}

async function isAuthenticated(request, env) {
  const header = request.headers.get("cookie") || "";
  const token = header.split(/;\s*/).find(part => part.startsWith(`${COOKIE_NAME}=`))?.slice(COOKIE_NAME.length + 1);
  if (!token) return false;
  try {
    const [payloadPart, signaturePart] = token.split(".");
    if (!payloadPart || !signaturePart) return false;
    const expected = await hmac(payloadPart, env.SESSION_SECRET);
    if (!await safeEqual(signaturePart, expected)) return false;
    const payload = JSON.parse(fromBase64Url(payloadPart));
    return payload.sub === "owner" && Number(payload.exp) > Math.floor(Date.now() / 1000);
  } catch (_) {
    return false;
  }
}

async function signToken(payload, secret) {
  const encoded = toBase64Url(JSON.stringify(payload));
  return `${encoded}.${await hmac(encoded, secret)}`;
}

async function hmac(value, secret) {
  if (!secret) throw new Error("SESSION_SECRET is not configured");
  const key = await crypto.subtle.importKey("raw", new TextEncoder().encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  const signature = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(value));
  return bytesToBase64Url(new Uint8Array(signature));
}

async function safeEqual(left, right) {
  const [a, b] = await Promise.all([left, right].map(value => crypto.subtle.digest("SHA-256", new TextEncoder().encode(value))));
  const aa = new Uint8Array(a);
  const bb = new Uint8Array(b);
  let diff = 0;
  for (let index = 0; index < aa.length; index += 1) diff |= aa[index] ^ bb[index];
  return diff === 0;
}

function assertSameOrigin(request) {
  const origin = request.headers.get("origin");
  if (origin && origin !== new URL(request.url).origin) throw new HttpError(403, "Cross-origin request rejected");
}

async function readBody(request) {
  const type = request.headers.get("content-type") || "";
  if (!type.includes("application/json")) throw new HttpError(415, "Expected application/json");
  try { return await request.json(); } catch (_) { throw new HttpError(400, "Invalid JSON body"); }
}

async function github(env, path, options = {}) {
  if (!env.GITHUB_TOKEN) throw new Error("GITHUB_TOKEN is not configured");
  const response = await fetch(`https://api.github.com/repos/${encodeURIComponent(env.GITHUB_OWNER)}/${encodeURIComponent(env.GITHUB_REPO)}${path}`, {
    method: options.method || "GET",
    headers: {
      accept: "application/vnd.github+json",
      authorization: `Bearer ${env.GITHUB_TOKEN}`,
      "content-type": "application/json",
      "user-agent": "vidloom-control-plane",
      "x-github-api-version": "2022-11-28",
    },
    body: options.body ? JSON.stringify(options.body) : undefined,
  });
  if (!response.ok) {
    let detail = `GitHub returned ${response.status}`;
    try { detail = (await response.json()).message || detail; } catch (_) { /* empty body */ }
    throw new HttpError(response.status >= 500 ? 502 : response.status, detail);
  }
  return response.status === 204 ? null : response.json();
}

async function modal(env, path, options = {}) {
  if (!env.MODAL_API_URL || !env.MODAL_CONTROL_SECRET) throw new Error("Modal control endpoint is not configured");
  const response = await fetch(`${String(env.MODAL_API_URL).replace(/\/$/, "")}${path}`, {
    method: options.method || "GET",
    headers: {
      authorization: `Bearer ${env.MODAL_CONTROL_SECRET}`,
      "content-type": "application/json",
      "user-agent": "vidloom-cloudflare-control",
    },
    body: options.body ? JSON.stringify(options.body) : undefined,
  });
  let value;
  try { value = await response.json(); } catch (_) { value = { error: `Modal returned ${response.status}` }; }
  if (!response.ok) throw new HttpError(response.status >= 500 ? 502 : response.status, value.error || `Modal returned ${response.status}`);
  return json(value, response.status);
}

async function readRepoDocument(env, path) {
  const data = await github(env, `/contents/${path}?ref=${encodeURIComponent(env.GITHUB_BRANCH || "main")}`);
  return { sha: data.sha, value: JSON.parse(decodeBase64(data.content)) };
}

async function readRepoJson(env, path) {
  return (await readRepoDocument(env, path)).value;
}

async function writeRepoJson(env, path, value, sha, message) {
  return github(env, `/contents/${path}`, {
    method: "PUT",
    body: {
      message,
      content: encodeBase64(`${JSON.stringify(value, null, 2)}\n`),
      sha,
      branch: env.GITHUB_BRANCH || "main",
    },
  });
}

export function validateQueueItem(body, now = Date.now()) {
  for (const field of ["project_path", "title", "description"]) {
    if (!String(body[field] || "").trim()) throw new HttpError(400, `${field} is required`);
  }
  if (String(body.title).length > 100) throw new HttpError(400, "Title is too long");
  if (!String(body.project_path).startsWith("premium_pipeline/projects/") || !String(body.project_path).endsWith("/project.json")) {
    throw new HttpError(400, "Project path must target a premium_pipeline project.json");
  }
  const requested = body.requested_publish_at ? new Date(body.requested_publish_at) : null;
  if (requested && Number.isNaN(requested.valueOf())) throw new HttpError(400, "Invalid requested publish time");
  const slug = String(body.title).toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 50) || "project";
  return {
    id: `${slug}-${now.toString(36)}`,
    project_path: String(body.project_path).trim(),
    genre: "cinema_scene_breakdown",
    title: String(body.title).trim(),
    description: String(body.description).trim(),
    tags: Array.isArray(body.tags) ? body.tags.map(String).map(tag => tag.trim()).filter(Boolean) : String(body.tags || "").split(",").map(tag => tag.trim()).filter(Boolean),
    status: "ready",
    requested_publish_at: requested ? requested.toISOString() : null,
    scheduled_publish_at: null,
    youtube_id: null,
    youtube_url: null,
    attempts: 0,
    last_error: null,
  };
}

export function applySettings(config, body) {
  const incoming = body?.autopilot || {};
  const videosPerDay = Number(incoming.videos_per_day);
  const bufferTarget = Number(incoming.finished_buffer_target);
  const budget = Number(incoming.monthly_modal_budget_usd);
  const time = String(incoming.first_publish_time || "");
  const timezone = String(incoming.timezone || "");
  if (![1, 2, 3, 5].includes(videosPerDay)) throw new HttpError(400, "Videos per day must be 1, 2, 3, or 5");
  if (!Number.isInteger(bufferTarget) || bufferTarget < 3 || bufferTarget > 14) throw new HttpError(400, "Finished buffer target must be between 3 and 14");
  if (!Number.isFinite(budget) || budget < 1 || budget > 500) throw new HttpError(400, "Monthly budget must be between $1 and $500");
  if (!/^([01]\d|2[0-3]):[0-5]\d$/.test(time)) throw new HttpError(400, "Publishing time must use HH:MM");
  if (!/^[A-Za-z_+-]+\/[A-Za-z_+/-]+$/.test(timezone)) throw new HttpError(400, "Timezone must be an IANA timezone");
  const publishingMode = String(incoming.publishing_mode || "");
  if (!["fully_automatic", "review_required"].includes(publishingMode)) throw new HttpError(400, "Unknown publishing mode");

  const copy = structuredClone(config);
  copy.channel.timezone = timezone;
  copy.schedule.videos_per_day = videosPerDay;
  copy.schedule.publish_time = time;
  copy.automation.creator_enabled = Boolean(incoming.creator_enabled);
  copy.automation.publishing_enabled = Boolean(incoming.publishing_enabled);
  copy.automation.enabled = Boolean(incoming.publishing_enabled);
  copy.automation.publishing_mode = publishingMode;
  copy.automation.automatic_retries = Boolean(incoming.automatic_retries);
  copy.automation.finished_buffer_target = bufferTarget;
  copy.automation.monthly_modal_budget_usd = budget;

  if (body.content_brain) {
    const preferences = Array.isArray(body.content_brain.movie_preferences) ? body.content_brain.movie_preferences : [];
    const exclusions = Array.isArray(body.content_brain.excluded_movies) ? body.content_brain.excluded_movies : [];
    copy.content_brain.movie_preferences = preferences.map(value => String(value).trim()).filter(Boolean).slice(0, 30);
    copy.content_brain.excluded_movies = exclusions.map(value => String(value).trim()).filter(Boolean).slice(0, 100);
    copy.content_brain.prevent_duplicate_scenes = Boolean(body.content_brain.prevent_duplicate_scenes);
    copy.content_brain.prevent_duplicate_hooks = Boolean(body.content_brain.prevent_duplicate_hooks);
  }
  if (body.production_rules) {
    const durationMin = Number(body.production_rules.duration_min_seconds);
    const durationMax = Number(body.production_rules.duration_max_seconds);
    if (!Number.isFinite(durationMin) || !Number.isFinite(durationMax) || durationMin < 15 || durationMax > 60 || durationMin >= durationMax) {
      throw new HttpError(400, "Duration range must be between 15 and 60 seconds");
    }
    copy.production_rules.duration_min_seconds = durationMin;
    copy.production_rules.duration_max_seconds = durationMax;
    for (const key of ["narration_style", "subtitle_preset", "music_mix", "crop_tracking"]) {
      if (body.production_rules[key] !== undefined) copy.production_rules[key] = String(body.production_rules[key]).trim().slice(0, 240);
    }
  }
  if (body.notifications) {
    for (const key of ["weekly_summary", "upload_failures", "copyright_claims", "credit_warnings"]) {
      copy.notifications[key] = Boolean(body.notifications[key]);
    }
    copy.notifications.email = String(body.notifications.email || "").trim().slice(0, 254);
  }
  return copy;
}

function publicSettings(config) {
  return {
    autopilot: {
      creator_enabled: config.automation.creator_enabled,
      publishing_enabled: config.automation.publishing_enabled,
      videos_per_day: config.schedule.videos_per_day,
      first_publish_time: config.schedule.publish_time,
      timezone: config.channel.timezone,
      publishing_mode: config.automation.publishing_mode,
      automatic_retries: config.automation.automatic_retries,
      finished_buffer_target: config.automation.finished_buffer_target,
      monthly_modal_budget_usd: config.automation.monthly_modal_budget_usd,
    },
    content_brain: config.content_brain,
    production_rules: config.production_rules,
    notifications: config.notifications,
  };
}

function json(value, status = 200, headers = {}) {
  return new Response(JSON.stringify(value), { status, headers: { ...JSON_HEADERS, ...headers } });
}

function sessionCookie(request, token) {
  const secure = new URL(request.url).protocol === "https:" ? "; Secure" : "";
  return `${COOKIE_NAME}=${token}; HttpOnly${secure}; SameSite=Strict; Path=/; Max-Age=${SESSION_TTL_SECONDS}`;
}

function expiredCookie(request) {
  const secure = new URL(request.url).protocol === "https:" ? "; Secure" : "";
  return `${COOKIE_NAME}=; HttpOnly${secure}; SameSite=Strict; Path=/; Max-Age=0`;
}

function encodeBase64(value) {
  const bytes = new TextEncoder().encode(value);
  let binary = "";
  bytes.forEach(byte => { binary += String.fromCharCode(byte); });
  return btoa(binary);
}

function decodeBase64(value) {
  const binary = atob(String(value).replaceAll("\n", ""));
  return new TextDecoder().decode(Uint8Array.from(binary, char => char.charCodeAt(0)));
}

function toBase64Url(value) { return bytesToBase64Url(new TextEncoder().encode(value)); }
function fromBase64Url(value) {
  const normalized = value.replaceAll("-", "+").replaceAll("_", "/").padEnd(Math.ceil(value.length / 4) * 4, "=");
  return new TextDecoder().decode(Uint8Array.from(atob(normalized), char => char.charCodeAt(0)));
}
function bytesToBase64Url(bytes) {
  let binary = "";
  bytes.forEach(byte => { binary += String.fromCharCode(byte); });
  return btoa(binary).replaceAll("+", "-").replaceAll("/", "_").replaceAll("=", "");
}

class HttpError extends Error {
  constructor(status, message) { super(message); this.status = status; }
}

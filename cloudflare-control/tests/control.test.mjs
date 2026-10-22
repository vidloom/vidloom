import test from "node:test";
import assert from "node:assert/strict";
import { actionSpec, applySettings, validateQueueItem } from "../src/index.js";

test("safe rehearsal cannot upload", () => {
  const spec = actionSpec("dry_run", { item_id: "demo" });
  assert.equal(spec.workflow, "production-cycle.yml");
  assert.equal(spec.inputs.dry_run, "true");
  assert.equal(spec.inputs.item_id, "demo");
});

test("production upload is explicit", () => {
  const spec = actionSpec("upload", { item_id: "demo" });
  assert.equal(spec.inputs.mode, "upload");
  assert.equal(spec.inputs.dry_run, "false");
});

test("manual creation accepts only a natural-language brief", () => {
  const spec = actionSpec("create", { prompt: "Make a short about the relative-motion idea in Interstellar's docking scene" });
  assert.equal(spec.workflow, "autopilot.yml");
  assert.equal(spec.inputs.force, "true");
  assert.match(spec.inputs.request, /relative-motion/);
});

test("autopilot can commission its own next video", () => {
  const spec = actionSpec("autopilot");
  assert.equal(spec.workflow, "autopilot.yml");
  assert.equal(spec.inputs.request, "");
  assert.equal(spec.inputs.force, "true");
});

test("queue item stays locked to the approved genre", () => {
  const item = validateQueueItem({
    project_path: "premium_pipeline/projects/example/project.json",
    title: "A real scene observation",
    description: "Evidence-bound commentary.",
    tags: "film, edit",
  }, 1234);
  assert.equal(item.genre, "cinema_scene_breakdown");
  assert.equal(item.status, "ready");
  assert.deepEqual(item.tags, ["film", "edit"]);
});

test("queue rejects arbitrary filesystem paths", () => {
  assert.throws(() => validateQueueItem({ project_path: "/tmp/demo.json", title: "Demo", description: "Demo" }), /project\.json/);
});

test("autopilot settings are validated and merged without arbitrary keys", () => {
  const config = {
    channel: { timezone: "Asia/Kolkata" }, schedule: { videos_per_day: 1, publish_time: "20:00" },
    automation: { creator_enabled: true, publishing_enabled: false, enabled: false, publishing_mode: "fully_automatic", automatic_retries: true, finished_buffer_target: 6, monthly_modal_budget_usd: 10 },
    content_brain: { movie_preferences: [], excluded_movies: [], prevent_duplicate_scenes: true, prevent_duplicate_hooks: true },
    production_rules: { duration_min_seconds: 24, duration_max_seconds: 34, narration_style: "Natural", subtitle_preset: "Clean", music_mix: "Ducked", crop_tracking: "Tracked" },
    notifications: { weekly_summary: true, upload_failures: true, copyright_claims: true, credit_warnings: true, email: "" },
  };
  const result = applySettings(config, {
    autopilot: { creator_enabled: true, publishing_enabled: true, videos_per_day: 2, first_publish_time: "20:00", timezone: "Asia/Kolkata", publishing_mode: "review_required", automatic_retries: true, finished_buffer_target: 7, monthly_modal_budget_usd: 20 },
  });
  assert.equal(result.schedule.videos_per_day, 2);
  assert.equal(result.automation.finished_buffer_target, 7);
  assert.equal(result.automation.enabled, true);
});

import test from "node:test";
import assert from "node:assert/strict";
import { actionSpec, validateQueueItem } from "../src/index.js";

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

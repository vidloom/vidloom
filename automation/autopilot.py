from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from automation.common import (
    CONFIG_PATH,
    IDEAS_PATH,
    QUEUE_PATH,
    ROOT,
    SOURCES_PATH,
    STATE_PATH,
    atomic_write_json,
    iso_z,
    load_json,
)


LOCK_PATH = ROOT / "automation" / "state" / "autopilot.lock"
FINISHED_STATUSES = {"ready", "scheduled"}
ACTIVE_CREATION_STATUSES = {"planned", "analyzing", "scripting", "voicing", "editing", "qc", "build_ready", "building"}


IDEA_SCHEMA = {
    "type": "object",
    "properties": {
        "youtube_title": {"type": "string"},
        "concept": {"type": "string"},
        "hook": {"type": "string"},
        "payoff": {"type": "string"},
        "script_direction": {"type": "string"},
        "description": {"type": "string"},
        "tags": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["youtube_title", "concept", "hook", "payoff", "script_direction", "description", "tags"],
    "additionalProperties": False,
}


def inventory(queue_doc: dict) -> dict[str, int]:
    counts = Counter(item.get("status", "planned") for item in queue_doc.get("items", []))
    finished = sum(counts[status] for status in FINISHED_STATUSES)
    active = sum(counts[status] for status in ACTIVE_CREATION_STATUSES)
    return {
        "finished": finished,
        "ready": counts["ready"],
        "scheduled": counts["scheduled"],
        "published": counts["published"],
        "active": active,
        "needs_attention": counts["needs_revision"] + counts["blocked"] + counts["failed"],
    }


def autopilot_mode(config: dict, queue_doc: dict, ideas_doc: dict | None = None) -> dict:
    stats = inventory(queue_doc)
    ideas_doc = ideas_doc or {"items": []}
    queued_idea_ids = {item.get("id") for item in queue_doc.get("items", [])}
    idea_active = sum(
        1 for item in ideas_doc.get("items", [])
        if item.get("status") in ACTIVE_CREATION_STATUSES and item.get("id") not in queued_idea_ids
    )
    stats["active"] += idea_active
    target = int(config["automation"].get("finished_buffer_target", 6))
    gap = max(0, target - stats["finished"] - stats["active"])
    creator_enabled = bool(config["automation"].get("creator_enabled", True))
    if not creator_enabled:
        mode = "paused"
    elif stats["finished"] >= target:
        mode = "standing_by"
    elif gap == 0:
        mode = "creating"
    else:
        mode = "filling"
    return {**stats, "target": target, "gap": gap, "mode": mode, "creator_enabled": creator_enabled}


def source_usage(queue_doc: dict, ideas_doc: dict) -> Counter:
    usage = Counter()
    for collection in (queue_doc.get("items", []), ideas_doc.get("items", [])):
        for item in collection:
            if item.get("source_id") and item.get("status") not in {"rejected", "cancelled"}:
                usage[item["source_id"]] += 1
    return usage


def select_source(sources_doc: dict, queue_doc: dict, ideas_doc: dict, request: str | None = None) -> dict | None:
    enabled = [item for item in sources_doc.get("items", []) if item.get("enabled")]
    usage = source_usage(queue_doc, ideas_doc)
    available = [item for item in enabled if usage[item["id"]] < int(item.get("max_uses", 1))]
    if not available:
        return None
    if request:
        query = request.casefold()
        matched = [item for item in available if item["movie"].casefold() in query or item["scene"].casefold() in query]
        if matched:
            return min(matched, key=lambda item: usage[item["id"]])
    return min(available, key=lambda item: (usage[item["id"]], item["id"]))


def fallback_idea(source: dict, angle: str, request: str | None) -> dict:
    concept = request.strip() if request else angle
    movie = source["movie"]
    return {
        "youtube_title": f"The Detail That Makes {movie}'s Scene Work"[:100],
        "concept": concept,
        "hook": f"What makes this {movie} scene feel impossible to look away from?",
        "payoff": f"The final image resolves the visual rule established at the opening.",
        "script_direction": "Write one connected, evidence-bound explanation using only inspected frames from the registered source.",
        "description": f"An original visual breakdown of {source['scene']} from {movie}. #Shorts #FilmAnalysis",
        "tags": ["film analysis", "cinema breakdown", movie, "visual storytelling"],
    }


def generate_idea(source: dict, existing_titles: list[str], request: str | None, model: str) -> dict:
    angles = source.get("angles", [])
    angle = angles[len(existing_titles) % len(angles)] if angles else source["scene"]
    if not os.environ.get("GROQ_API_KEY"):
        return fallback_idea(source, angle, request)
    from groq import Groq

    system = """You are the commissioning editor for one premium YouTube Shorts channel.
The locked genre is cinema scene breakdowns: one scene, one original visual observation, evidence
for every claim, and a complete payoff. Produce one specific idea from the registered source below.
Do not invent plot facts, timestamps, dialogue, performance motives, awards, rankings, or claims
about all movies. The video must add a useful observation rather than recap the scene. The title
must be compelling without unsupported superlatives. The hook must pose a question the visible
footage can answer. Return only the schema-constrained object."""
    payload = {
        "manual_request": request,
        "registered_source": {
            "source_id": source["id"],
            "movie": source["movie"],
            "scene": source["scene"],
            "available_angles": angles,
            "preferred_angle": angle,
        },
        "titles_to_avoid": existing_titles[-30:],
    }
    response = Groq(api_key=os.environ["GROQ_API_KEY"]).chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": json.dumps(payload)}],
        response_format={"type": "json_schema", "json_schema": {"name": "vidloom_idea", "strict": True, "schema": IDEA_SCHEMA}},
        reasoning_effort="medium",
        reasoning_format="hidden",
        max_completion_tokens=1800,
    )
    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("Groq returned an empty idea")
    return json.loads(content)


def create_idea(*, request: str | None = None) -> dict:
    config = load_json(CONFIG_PATH)
    queue_doc = load_json(QUEUE_PATH)
    ideas_doc = load_json(IDEAS_PATH)
    sources_doc = load_json(SOURCES_PATH)
    source = select_source(sources_doc, queue_doc, ideas_doc, request)
    if not source:
        raise RuntimeError("The registered source library is exhausted; add another owned/licensed scene source")
    existing_titles = [item.get("title", "") for item in queue_doc.get("items", [])]
    existing_titles += [item.get("youtube_title", "") for item in ideas_doc.get("items", [])]
    data = generate_idea(source, existing_titles, request, config.get("ai", {}).get("model", "openai/gpt-oss-120b"))
    slug = re.sub(r"[^a-z0-9]+", "-", data["youtube_title"].casefold()).strip("-")[:48] or "idea"
    item = {
        "id": f"{slug}-{uuid.uuid4().hex[:8]}",
        "origin": "manual" if request else "autopilot",
        "request": request,
        "source_id": source["id"],
        "movie": source["movie"],
        "scene": source["scene"],
        "source_path": source["path"],
        "source_start": source["start"],
        "source_end": source["end"],
        "youtube_title": data["youtube_title"][:100],
        "concept": data["concept"],
        "hook": data["hook"],
        "payoff": data["payoff"],
        "script_direction": data["script_direction"],
        "description": data["description"][:5000],
        "tags": [str(tag)[:100] for tag in data["tags"][:12]],
        "status": "planned",
        "stage": "Idea approved",
        "progress": 8,
        "attempts": 0,
        "created_at": iso_z(),
        "updated_at": iso_z(),
        "last_error": None,
    }
    ideas_doc.setdefault("items", []).append(item)
    atomic_write_json(IDEAS_PATH, ideas_doc)
    return item


def plan_cycle(*, request: str | None = None, force: bool = False) -> list[dict]:
    config = load_json(CONFIG_PATH)
    queue_doc = load_json(QUEUE_PATH)
    ideas_doc = load_json(IDEAS_PATH)
    state = autopilot_mode(config, queue_doc, ideas_doc)
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    commissioned = sum(1 for item in ideas_doc.get("items", []) if str(item.get("created_at", "")).startswith(month))
    estimated_cost = float(config["automation"].get("estimated_cost_per_short_usd", 0.35))
    limit = float(config["automation"].get("monthly_modal_budget_usd", 10))
    margin = float(config["automation"].get("budget_safety_margin_usd", 1))
    if (commissioned + 1) * estimated_cost > max(0, limit - margin):
        raise RuntimeError("Monthly creation budget safety threshold reached; no new job was started")
    if request:
        count = 1
    elif not state["creator_enabled"] and not force:
        return []
    elif state["gap"] <= 0 and not force:
        return []
    else:
        count = min(state["gap"], int(config["automation"].get("max_creations_per_cycle", 1)))
    return [create_idea(request=request) for _ in range(count)]


def recoverable_item(config: dict, queue_doc: dict) -> dict | None:
    if not config["automation"].get("automatic_retries", True):
        return None
    maximum = int(config["automation"].get("maximum_job_retries", 3))
    return next((
        item for item in queue_doc.get("items", [])
        if item.get("status") == "failed"
        and item.get("origin") in {"autopilot", "manual"}
        and int(item.get("attempts", 0)) < maximum
        and item.get("project_path")
    ), None)


def recoverable_idea(config: dict, ideas_doc: dict) -> dict | None:
    if not config["automation"].get("automatic_retries", True):
        return None
    maximum = int(config["automation"].get("maximum_job_retries", 3))
    return next((
        item for item in ideas_doc.get("items", [])
        if item.get("status") == "blocked"
        and item.get("origin") in {"autopilot", "manual"}
        and int(item.get("attempts", 0)) < maximum
    ), None)


def main() -> None:
    parser = argparse.ArgumentParser(description="Maintain Vidloom's finished-video buffer and commission new work automatically.")
    parser.add_argument("--request", help="Optional owner request; treated as an extra video outside the automatic buffer rule")
    parser.add_argument("--force", action="store_true", help="Commission work even when the buffer is full or creator is paused")
    parser.add_argument("--execute", action="store_true", help="Create and build each commissioned idea on this production host")
    args = parser.parse_args()
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOCK_PATH.open("w", encoding="utf-8") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        config = load_json(CONFIG_PATH)
        queue_doc = load_json(QUEUE_PATH)
        ideas_doc = load_json(IDEAS_PATH)
        queue_recovery = recoverable_item(config, queue_doc) if args.execute and not args.request else None
        idea_recovery = recoverable_idea(config, ideas_doc) if args.execute and not args.request and not queue_recovery else None
        if idea_recovery:
            idea_recovery.update({"status": "planned", "stage": "Automatic retry queued", "progress": 8, "last_error": None, "updated_at": iso_z()})
            atomic_write_json(IDEAS_PATH, ideas_doc)
        items = [idea_recovery] if idea_recovery else [] if queue_recovery else plan_cycle(request=args.request, force=args.force)
        built = []
        if args.execute:
            from automation.creator import create, set_idea_state
            from automation.production import process
            if queue_recovery:
                queue_recovery["status"] = "build_ready"
                queue_recovery["stage"] = "Automatic retry queued"
                queue_recovery["last_error"] = None
                atomic_write_json(QUEUE_PATH, queue_doc)
                process("build", queue_recovery["id"], dry_run=False, force=True)
                built.append(queue_recovery["id"])
            for item in items:
                try:
                    queue_id = create(item["id"])
                    process("build", queue_id, dry_run=False, force=True)
                    set_idea_state(item["id"], "ready", "Finished and ready", 100)
                    built.append(queue_id)
                except Exception as error:
                    set_idea_state(item["id"], "blocked", "Needs attention", 0, str(error))
                    raise
    recovered = queue_recovery["id"] if queue_recovery else idea_recovery["id"] if idea_recovery else None
    print(json.dumps({"created": len(items) if not recovered else 0, "recovered": recovered, "idea_ids": [item["id"] for item in items], "built_ids": built}, indent=2))


if __name__ == "__main__":
    main()

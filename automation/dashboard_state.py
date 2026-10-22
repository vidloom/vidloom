from __future__ import annotations

import argparse
import os
from collections import Counter
from datetime import datetime, timezone

from automation.autopilot import autopilot_mode
from automation.common import ANALYTICS_STATE_PATH, AI_STATE_PATH, CONFIG_PATH, IDEAS_PATH, QUEUE_PATH, STATE_PATH, atomic_write_json, iso_z, load_json
from automation.schedule import next_available_publish_slot


PUBLIC_STATUSES = {
    "planned", "analyzing", "scripting", "voicing", "editing", "build_ready", "building", "qc",
    "ready", "held", "uploading", "scheduled", "published", "needs_revision", "blocked", "failed",
}


def build_public_state() -> dict:
    config = load_json(CONFIG_PATH)
    queue_doc = load_json(QUEUE_PATH)
    ideas_doc = load_json(IDEAS_PATH)
    previous = load_json(STATE_PATH)
    items = queue_doc.get("items", [])
    counts = Counter(item.get("status", "queued") for item in items)
    now = datetime.now(timezone.utc)

    queue = []
    for item in items:
        status = item.get("status", "queued")
        if status not in PUBLIC_STATUSES:
            status = "failed"
        queue.append({
            "id": item["id"],
            "project_path": item.get("project_path"),
            "source_id": item.get("source_id"),
            "origin": item.get("origin", "legacy"),
            "title": item["title"],
            "genre": item["genre"],
            "status": status,
            "stage": item.get("stage", status.replace("_", " ").title()),
            "progress": item.get("progress", 100 if status in {"ready", "scheduled", "published"} else 0),
            "scheduled_publish_at": item.get("scheduled_publish_at"),
            "youtube_id": item.get("youtube_id"),
            "youtube_url": item.get("youtube_url"),
            "created_at": item.get("created_at"),
            "updated_at": item.get("updated_at"),
            "attempts": item.get("attempts", 0),
            "last_error": item.get("last_error"),
        })

    previous["version"] = 1
    previous["generated_at"] = iso_z(now)
    previous["channel"] = {
        "name": config["channel"]["name"],
        "genre": config["genre"]["label"],
        "genre_id": config["genre"]["id"],
        "timezone": config["channel"]["timezone"],
    }
    occupied = [item.get("scheduled_publish_at") for item in items if item.get("status") == "scheduled"]
    previous["schedule"] = {
        "days": [day.title() for day in config["schedule"]["publish_days"]],
        "time": config["schedule"]["publish_time"],
        "timezone": config["channel"]["timezone"],
        "next_publish_at": next_available_publish_slot(config, now, occupied).isoformat(timespec="minutes"),
    }
    system = previous.setdefault("system", {})
    system["automation_enabled"] = bool(config["automation"].get("enabled", False))
    system["creator_enabled"] = bool(config["automation"].get("creator_enabled", True))
    system["publishing_enabled"] = bool(config["automation"].get("publishing_enabled", config["automation"].get("enabled", False)))
    previous["metrics"] = {
        "queued": counts["planned"] + counts["build_ready"] + counts["held"],
        "building": sum(counts[key] for key in ("analyzing", "scripting", "voicing", "editing", "building", "qc", "uploading")),
        "ready": counts["ready"],
        "scheduled": counts["scheduled"],
        "published": counts["published"],
        "needs_attention": counts["needs_revision"] + counts["blocked"] + counts["failed"],
    }
    previous["queue"] = queue
    autopilot = autopilot_mode(config, queue_doc, ideas_doc)
    previous["autopilot"] = {
        **autopilot,
        "publishing_enabled": system["publishing_enabled"],
        "interval_hours": config["automation"].get("autopilot_interval_hours", 2),
        "next_action": (
            "Finished buffer is full; creator is standing by"
            if autopilot["mode"] == "standing_by" else
            "Creator is paused by the owner"
            if autopilot["mode"] == "paused" else
            f"Creating {autopilot['gap']} more video{'s' if autopilot['gap'] != 1 else ''} to fill the release buffer"
        ),
    }
    previous["ideas"] = [
        {
            "id": item["id"], "origin": item.get("origin", "autopilot"), "movie": item.get("movie"),
            "scene": item.get("scene"), "title": item.get("youtube_title"), "concept": item.get("concept"),
            "status": item.get("status", "planned"), "stage": item.get("stage", "Idea approved"),
            "progress": item.get("progress", 0), "created_at": item.get("created_at"),
            "updated_at": item.get("updated_at"), "last_error": item.get("last_error"),
        }
        for item in reversed(ideas_doc.get("items", []))
    ][:12]
    previous["scheduled_videos"] = sorted(
        [item for item in queue if item["status"] == "scheduled"],
        key=lambda item: item.get("scheduled_publish_at") or "",
    )
    previous["finished_videos"] = [item for item in queue if item["status"] in {"ready", "scheduled", "published"}]
    previous["attention_videos"] = [item for item in queue if item["status"] in {"needs_revision", "blocked", "failed"}]
    previous["settings"] = {
        "autopilot": {
            "creator_enabled": system["creator_enabled"],
            "publishing_enabled": system["publishing_enabled"],
            "videos_per_day": config["schedule"].get("videos_per_day", 1),
            "first_publish_time": config["schedule"]["publish_time"],
            "timezone": config["channel"]["timezone"],
            "publishing_mode": config["automation"].get("publishing_mode", "fully_automatic"),
            "automatic_retries": config["automation"].get("automatic_retries", True),
            "finished_buffer_target": config["automation"].get("finished_buffer_target", 6),
            "monthly_modal_budget_usd": config["automation"].get("monthly_modal_budget_usd", 10),
        },
        "content_brain": config.get("content_brain", {}),
        "production_rules": config.get("production_rules", {}),
        "notifications": config.get("notifications", {}),
    }
    current_month = now.strftime("%Y-%m")
    commissioned_this_month = sum(1 for item in ideas_doc.get("items", []) if str(item.get("created_at", "")).startswith(current_month))
    estimated_per_short = float(config["automation"].get("estimated_cost_per_short_usd", 0.35))
    estimated_spend = round(commissioned_this_month * estimated_per_short, 2)
    budget_limit = float(config["automation"].get("monthly_modal_budget_usd", 10))
    safety_margin = float(config["automation"].get("budget_safety_margin_usd", 1))
    previous["costs"] = {
        "month": current_month,
        "estimated_spend_usd": estimated_spend,
        "budget_limit_usd": budget_limit,
        "safety_margin_usd": safety_margin,
        "remaining_usd": round(max(0, budget_limit - estimated_spend), 2),
        "estimated_cost_per_short_usd": estimated_per_short,
        "commissioned_this_month": commissioned_this_month,
        "source": "Estimated from configured per-Short cost; connect Modal billing export for actual spend.",
        "creation_allowed": estimated_spend + estimated_per_short <= max(0, budget_limit - safety_margin),
    }
    previous["content_memory"] = {
        "movies_used": sorted({item.get("movie") for item in ideas_doc.get("items", []) if item.get("movie")}),
        "scenes_tracked": len({item.get("source_id") for item in ideas_doc.get("items", []) if item.get("source_id")}),
        "ideas_remembered": len(ideas_doc.get("items", [])),
        "duplicate_prevention": bool(config.get("content_brain", {}).get("prevent_duplicate_scenes", True)),
    }
    previous["analytics"] = load_json(ANALYTICS_STATE_PATH) if ANALYTICS_STATE_PATH.is_file() else {}
    ai = load_json(AI_STATE_PATH) if AI_STATE_PATH.is_file() else {}
    previous["ai"] = {
        "provider": ai.get("provider", config.get("ai", {}).get("provider", "Groq")),
        "model": ai.get("model", config.get("ai", {}).get("model", "unknown")),
        "status": ai.get("status", "not_run"),
        "verdict": ai.get("verdict", "pending"),
        "project_id": ai.get("project_id"),
        "generated_at": ai.get("generated_at"),
        "summary": ai.get("summary", "AI Director has not run yet."),
        "scores": {
            key.removesuffix("_score"): ai.get(key)
            for key in ("hook_score", "clarity_score", "payoff_score", "evidence_score", "voice_score")
        },
        "risks": ai.get("risks", [])[:5],
        "recommended_edits": ai.get("recommended_edits", [])[:5],
    }
    health = previous.setdefault("health", {})
    if os.environ.get("YOUTUBE_REFRESH_TOKEN"):
        health["youtube"] = "connected"
    else:
        health.setdefault("youtube", "not_connected")
    if os.environ.get("VIDLOOM_RUNNER_ONLINE") == "true":
        health["runner"] = "online"
    else:
        health.setdefault("runner", "local" if not os.environ.get("GITHUB_ACTIONS") else "unknown")
    health["pipeline"] = "ready"
    health["ai"] = "connected" if os.environ.get("GROQ_API_KEY") else ai.get("status", "configured")
    health["queue"] = "low" if autopilot["finished"] < autopilot["target"] else "ready"
    health["creator"] = "active" if autopilot["mode"] in {"filling", "creating"} else autopilot["mode"]
    return previous


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the public, secret-free Vidloom dashboard state.")
    parser.add_argument("--output", default=str(STATE_PATH))
    args = parser.parse_args()
    state = build_public_state()
    from pathlib import Path
    atomic_write_json(Path(args.output), state)
    print(args.output)


if __name__ == "__main__":
    main()

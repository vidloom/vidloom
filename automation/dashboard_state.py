from __future__ import annotations

import argparse
import os
from collections import Counter
from datetime import datetime, timezone

from automation.common import AI_STATE_PATH, CONFIG_PATH, QUEUE_PATH, STATE_PATH, atomic_write_json, iso_z, load_json
from automation.schedule import next_publish_slot


PUBLIC_STATUSES = {"queued", "ready", "held", "building", "qc", "uploading", "scheduled", "published", "failed"}


def build_public_state() -> dict:
    config = load_json(CONFIG_PATH)
    queue_doc = load_json(QUEUE_PATH)
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
            "title": item["title"],
            "genre": item["genre"],
            "status": status,
            "scheduled_publish_at": item.get("scheduled_publish_at"),
            "youtube_url": item.get("youtube_url"),
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
    previous["schedule"] = {
        "days": [day.title() for day in config["schedule"]["publish_days"]],
        "time": config["schedule"]["publish_time"],
        "timezone": config["channel"]["timezone"],
        "next_publish_at": next_publish_slot(config, now).isoformat(timespec="minutes"),
    }
    previous.setdefault("system", {})["automation_enabled"] = bool(config["automation"]["enabled"])
    previous["metrics"] = {
        "queued": counts["queued"] + counts["ready"],
        "building": counts["building"] + counts["qc"] + counts["uploading"],
        "scheduled": counts["scheduled"],
        "published": counts["published"],
        "failed": counts["failed"],
    }
    previous["queue"] = queue
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
    health["queue"] = "low" if previous["metrics"]["queued"] < config["automation"]["minimum_queue_depth"] else "ready"
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

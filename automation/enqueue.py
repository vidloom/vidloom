from __future__ import annotations

import argparse
import re
import uuid

from automation.common import CONFIG_PATH, QUEUE_PATH, ROOT, atomic_write_json, load_json, resolve_project_path


def enqueue(project_path: str, title: str, description: str, tags: list[str], requested_publish_at: str | None) -> str:
    config = load_json(CONFIG_PATH)
    queue = load_json(QUEUE_PATH)
    project = resolve_project_path(project_path)
    relative = project.relative_to(ROOT).as_posix()
    if any(item.get("project_path") == relative and item.get("status") not in {"failed", "published"} for item in queue["items"]):
        raise ValueError("This project is already active in the queue")
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:48]
    item_id = f"{slug}-{uuid.uuid4().hex[:8]}"
    queue["items"].append({
        "id": item_id,
        "project_path": relative,
        "genre": config["genre"]["id"],
        "title": title,
        "description": description,
        "tags": tags,
        "status": "ready",
        "requested_publish_at": requested_publish_at,
        "scheduled_publish_at": None,
        "youtube_id": None,
        "youtube_url": None,
        "attempts": 0,
        "last_error": None,
    })
    atomic_write_json(QUEUE_PATH, queue)
    return item_id


def main() -> None:
    parser = argparse.ArgumentParser(description="Queue one completed v3 cinema breakdown for automated release.")
    parser.add_argument("project")
    parser.add_argument("--title", required=True)
    parser.add_argument("--description", required=True)
    parser.add_argument("--tag", action="append", default=[])
    parser.add_argument("--publish-at")
    args = parser.parse_args()
    print(enqueue(args.project, args.title, args.description, args.tag, args.publish_at))


if __name__ == "__main__":
    main()

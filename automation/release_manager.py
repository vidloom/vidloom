from __future__ import annotations

import json

from automation.common import CONFIG_PATH, QUEUE_PATH, load_json
from automation.production import process


def main() -> None:
    """Upload one finished Short when publishing is enabled; otherwise exit cleanly."""
    config = load_json(CONFIG_PATH)
    if not config["automation"].get("publishing_enabled", False):
        print(json.dumps({"action": "none", "reason": "publishing_paused"}))
        return

    queue = load_json(QUEUE_PATH)
    ready = next((item for item in queue.get("items", []) if item.get("status") == "ready" and not item.get("youtube_id")), None)
    if not ready:
        print(json.dumps({"action": "none", "reason": "no_finished_video"}))
        return

    process("upload", ready["id"], dry_run=False, force=False)
    print(json.dumps({"action": "scheduled", "item_id": ready["id"]}))


if __name__ == "__main__":
    main()

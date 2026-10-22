from __future__ import annotations

from datetime import datetime, timezone

from automation.common import QUEUE_PATH, STATE_PATH, atomic_write_json, iso_z, load_json, redact_error
from automation.dashboard_state import build_public_state
from automation.production import append_event
from automation.youtube_upload import _credentials


def sync() -> int:
    from googleapiclient.discovery import build

    queue_doc = load_json(QUEUE_PATH)
    state = load_json(STATE_PATH)
    candidates = [item for item in queue_doc.get("items", []) if item.get("youtube_id") and item.get("status") == "scheduled"]
    if not candidates:
        atomic_write_json(STATE_PATH, build_public_state())
        return 0

    youtube = build("youtube", "v3", credentials=_credentials(), cache_discovery=False)
    ids = [item["youtube_id"] for item in candidates]
    response = youtube.videos().list(part="status,processingDetails", id=",".join(ids)).execute()
    remote = {item["id"]: item for item in response.get("items", [])}
    changed = 0
    now = datetime.now(timezone.utc)

    for item in candidates:
        details = remote.get(item["youtube_id"])
        if not details:
            item["last_error"] = "YouTube no longer returns this video ID"
            continue
        processing = details.get("processingDetails", {}).get("processingStatus")
        privacy = details.get("status", {}).get("privacyStatus")
        if processing == "failed":
            item["status"] = "failed"
            item["last_error"] = "YouTube processing failed"
            append_event(state, "error", f"YouTube processing failed for {item['title']}")
            changed += 1
        elif privacy == "public":
            item["status"] = "published"
            item["last_error"] = None
            append_event(state, "success", f"Published on YouTube: {item['title']}")
            changed += 1
        elif privacy not in {"private", "public"}:
            item["last_error"] = f"Unexpected YouTube privacy state: {privacy}"
        elif item.get("scheduled_publish_at"):
            planned = datetime.fromisoformat(item["scheduled_publish_at"].replace("Z", "+00:00"))
            if planned < now:
                item["last_error"] = "Still private after the planned publish time; check channel restrictions"

    state["system"]["last_success_at"] = iso_z()
    atomic_write_json(QUEUE_PATH, queue_doc)
    atomic_write_json(STATE_PATH, state)
    atomic_write_json(STATE_PATH, build_public_state())
    return changed


def main() -> None:
    try:
        print(f"Updated {sync()} YouTube item(s)")
        from automation.analytics import sync_analytics
        sync_analytics()
    except Exception as error:
        state = load_json(STATE_PATH)
        message = redact_error(error)
        state["system"]["last_error"] = message
        append_event(state, "error", f"YouTube status sync failed: {message}")
        atomic_write_json(STATE_PATH, state)
        raise


if __name__ == "__main__":
    main()

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from automation.common import ANALYTICS_STATE_PATH, QUEUE_PATH, atomic_write_json, iso_z, load_json
from automation.youtube_upload import _credentials


def as_int(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def sync_analytics() -> dict:
    from googleapiclient.discovery import build

    youtube = build("youtube", "v3", credentials=_credentials(), cache_discovery=False)
    channel_response = youtube.channels().list(part="snippet,statistics", mine=True).execute()
    channel_item = (channel_response.get("items") or [{}])[0]
    stats = channel_item.get("statistics", {})
    queue = load_json(QUEUE_PATH)
    published = [item for item in queue.get("items", []) if item.get("youtube_id")]
    remote_videos = {}
    for offset in range(0, len(published), 50):
        ids = [item["youtube_id"] for item in published[offset:offset + 50]]
        response = youtube.videos().list(part="snippet,statistics,status", id=",".join(ids)).execute()
        remote_videos.update({item["id"]: item for item in response.get("items", [])})
    videos = []
    for item in published:
        remote = remote_videos.get(item["youtube_id"], {})
        remote_stats = remote.get("statistics", {})
        videos.append({
            "id": item["youtube_id"], "title": item["title"], "status": item.get("status"),
            "published_at": remote.get("snippet", {}).get("publishedAt"),
            "scheduled_publish_at": item.get("scheduled_publish_at"), "youtube_url": item.get("youtube_url"),
            "views": as_int(remote_stats.get("viewCount")), "likes": as_int(remote_stats.get("likeCount")),
            "comments": as_int(remote_stats.get("commentCount")),
        })
    previous = load_json(ANALYTICS_STATE_PATH) if ANALYTICS_STATE_PATH.is_file() else {"history": []}
    now = datetime.now(timezone.utc)
    snapshot = {
        "at": iso_z(now), "views": as_int(stats.get("viewCount")),
        "subscribers": as_int(stats.get("subscriberCount")), "videos": as_int(stats.get("videoCount")),
    }
    history = previous.get("history", [])
    history.append(snapshot)
    history = history[-120:]
    cutoff = now - timedelta(days=7)
    baseline = None
    for row in history:
        try:
            if datetime.fromisoformat(row["at"].replace("Z", "+00:00")) <= cutoff:
                baseline = row
        except (KeyError, ValueError):
            continue
    weekly_views = snapshot["views"] - baseline["views"] if baseline and snapshot["views"] is not None and baseline.get("views") is not None else None
    weekly_subscribers = snapshot["subscribers"] - baseline["subscribers"] if baseline and snapshot["subscribers"] is not None and baseline.get("subscribers") is not None else None
    document = {
        "version": 1, "generated_at": iso_z(now),
        "channel": {"name": channel_item.get("snippet", {}).get("title"), **snapshot},
        "weekly": {
            "views": weekly_views, "subscribers_gained": weekly_subscribers,
            "average_view_duration_seconds": None, "average_percentage_viewed": None,
        },
        "videos": sorted(videos, key=lambda row: row.get("published_at") or row.get("scheduled_publish_at") or "", reverse=True),
        "history": history,
        "retention_scope_connected": False,
        "message": "Views, likes, comments, and subscribers are live. Retention requires a refreshed OAuth grant with yt-analytics.readonly.",
    }
    atomic_write_json(ANALYTICS_STATE_PATH, document)
    return document


def main() -> None:
    document = sync_analytics()
    print(f"Synced analytics for {len(document['videos'])} video(s)")


if __name__ == "__main__":
    main()

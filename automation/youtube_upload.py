from __future__ import annotations

import argparse
import json
import os
import random
import time
from datetime import datetime, timezone
from pathlib import Path


RETRIABLE_STATUS_CODES = {500, 502, 503, 504}


def _credentials():
    from google.oauth2.credentials import Credentials

    required = ["YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN"]
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        raise RuntimeError(f"Missing GitHub Actions secrets: {', '.join(missing)}")
    return Credentials(
        token=None,
        refresh_token=os.environ["YOUTUBE_REFRESH_TOKEN"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["YOUTUBE_CLIENT_ID"],
        client_secret=os.environ["YOUTUBE_CLIENT_SECRET"],
        scopes=[
            "https://www.googleapis.com/auth/youtube.upload",
            "https://www.googleapis.com/auth/youtube.readonly",
        ],
    )


def upload_video(*, video_path: Path, title: str, description: str, tags: list[str],
                 category_id: str, publish_at: datetime, made_for_kids: bool,
                 contains_synthetic_media: bool, max_retries: int = 5) -> dict:
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaFileUpload

    if not video_path.is_file():
        raise FileNotFoundError(video_path)
    if publish_at.tzinfo is None or publish_at <= datetime.now(timezone.utc):
        raise ValueError("publish_at must be a future timezone-aware datetime")

    youtube = build("youtube", "v3", credentials=_credentials(), cache_discovery=False)
    body = {
        "snippet": {
            "title": title[:100],
            "description": description[:5000],
            "tags": tags[:500],
            "categoryId": category_id,
            "defaultLanguage": "en",
        },
        "status": {
            "privacyStatus": "private",
            "publishAt": publish_at.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
            "selfDeclaredMadeForKids": made_for_kids,
            "containsSyntheticMedia": contains_synthetic_media,
        },
    }
    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=MediaFileUpload(str(video_path), chunksize=8 * 1024 * 1024, resumable=True),
        notifySubscribers=True,
    )

    response = None
    retry = 0
    while response is None:
        try:
            _, response = request.next_chunk()
        except HttpError as error:
            if error.resp.status not in RETRIABLE_STATUS_CODES or retry >= max_retries:
                raise
            retry += 1
            time.sleep(min(2 ** retry + random.random(), 32))
        except (OSError, TimeoutError):
            if retry >= max_retries:
                raise
            retry += 1
            time.sleep(min(2 ** retry + random.random(), 32))
    return response


def main() -> None:
    parser = argparse.ArgumentParser(description="Resumably upload and schedule one validated Short.")
    parser.add_argument("video")
    parser.add_argument("metadata_json")
    parser.add_argument("publish_at")
    args = parser.parse_args()
    metadata = json.loads(Path(args.metadata_json).read_text(encoding="utf-8"))
    publish_at = datetime.fromisoformat(args.publish_at.replace("Z", "+00:00"))
    result = upload_video(
        video_path=Path(args.video),
        title=metadata["title"],
        description=metadata["description"],
        tags=metadata.get("tags", []),
        category_id=metadata.get("category_id", "24"),
        publish_at=publish_at,
        made_for_kids=metadata.get("made_for_kids", False),
        contains_synthetic_media=metadata.get("contains_synthetic_media", False),
    )
    print(json.dumps({"id": result["id"], "url": f"https://youtu.be/{result['id']}"}))


if __name__ == "__main__":
    main()

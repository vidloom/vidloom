from __future__ import annotations

import argparse
import fcntl
import hashlib
import subprocess
import sys
import os
from datetime import datetime, timezone
from pathlib import Path

from automation.common import CONFIG_PATH, QUEUE_PATH, ROOT, STATE_PATH, atomic_write_json, iso_z, load_json, redact_error, resolve_project_path
from automation.dashboard_state import build_public_state
from automation.schedule import requested_or_next


LOCK_PATH = ROOT / "automation" / "state" / "production.lock"


def run(command: list[str]) -> None:
    subprocess.run(command, cwd=ROOT, check=True)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def append_event(state: dict, level: str, message: str) -> None:
    events = state.setdefault("events", [])
    events.insert(0, {"at": iso_z(), "level": level, "message": message})
    del events[30:]


def save(queue_doc: dict, state: dict) -> None:
    atomic_write_json(QUEUE_PATH, queue_doc)
    atomic_write_json(STATE_PATH, state)


def select_item(queue_doc: dict, item_id: str | None) -> dict:
    items = queue_doc.get("items", [])
    if item_id:
        for item in items:
            if item.get("id") == item_id:
                return item
        raise ValueError(f"Unknown queue item: {item_id}")
    for item in items:
        if item.get("status") == "ready":
            return item
    raise RuntimeError("No ready queue item")


def verify_output(project_file: Path, config: dict) -> Path:
    project_dir = project_file.parent
    video = project_dir / "build" / "draft.mp4"
    qc_path = project_dir / "build" / "qc.json"
    review_path = project_dir / "FINAL_REVIEW.md"
    if not video.is_file() or not qc_path.is_file():
        raise RuntimeError("Render or QC output is missing")
    qc = load_json(qc_path)
    if config["automation"]["require_technical_qc"] and not qc.get("technical_pass"):
        raise RuntimeError(f"Technical QC failed: {qc.get('issues', [])}")
    digest = sha256(video)
    if qc.get("video_sha256") != digest:
        raise RuntimeError("QC hash does not match the rendered video")
    if config["automation"]["require_final_review_hash"]:
        if not review_path.is_file() or digest not in review_path.read_text(encoding="utf-8"):
            raise RuntimeError("FINAL_REVIEW.md is missing the exact rendered-video SHA-256")
    return video


def prepare_project(item: dict, config: dict, state: dict, *, allow_render: bool) -> Path:
    project_file = resolve_project_path(item["project_path"])
    pipeline = ROOT / "premium_pipeline" / "v3" / "pipeline.py"
    ai_config = config.get("ai", {})
    if ai_config.get("enabled") and os.environ.get("GROQ_API_KEY"):
        state["system"]["current_stage"] = "Groq editorial audit"
        state["system"]["status"] = "building"
        atomic_write_json(STATE_PATH, state)
        command = [
            sys.executable, "-m", "automation.groq_editorial", item["project_path"],
            "--model", ai_config.get("model", "openai/gpt-oss-120b"),
        ]
        if ai_config.get("require_audit_before_upload") and ai_config.get("required_verdict") == "pass":
            command.append("--require-pass")
        run(command)
    state["system"]["current_stage"] = "Validating evidence and editorial reviews"
    state["system"]["status"] = "building"
    atomic_write_json(STATE_PATH, state)
    run([sys.executable, str(pipeline), "validate", str(project_file)])

    video = project_file.parent / "build" / "draft.mp4"
    if not video.exists():
        if not allow_render:
            raise RuntimeError("Render is missing and this run is upload-only")
        state["system"]["current_stage"] = "Rendering master"
        atomic_write_json(STATE_PATH, state)
        encoder = "h264_nvenc" if config["automation"].get("prefer_nvenc", True) else "libopenh264"
        run([sys.executable, str(pipeline), "render", str(project_file), "--encoder", encoder])

    state["system"]["current_stage"] = "Running technical QC"
    item["status"] = "qc"
    atomic_write_json(STATE_PATH, state)
    run([sys.executable, str(pipeline), "qc", str(project_file)])
    return verify_output(project_file, config)


def process(mode: str, item_id: str | None, dry_run: bool, force: bool) -> None:
    config = load_json(CONFIG_PATH)
    queue_doc = load_json(QUEUE_PATH)
    state = load_json(STATE_PATH)
    if not config["automation"]["enabled"] and not force:
        raise RuntimeError("Automation is paused. Resume it from the control center first.")

    item = select_item(queue_doc, item_id)
    if item.get("youtube_id"):
        raise RuntimeError("Queue item already has a YouTube ID; refusing a duplicate upload")
    if item.get("genre") != config["genre"]["id"]:
        raise RuntimeError(f"Genre lock rejected {item.get('genre')!r}; only {config['genre']['id']!r} is allowed")
    item["attempts"] = int(item.get("attempts", 0)) + 1
    item["status"] = "building"
    item["last_error"] = None
    state["system"].update({
        "status": "building",
        "current_item_id": item["id"],
        "current_stage": "Starting production",
        "last_error": None,
    })
    append_event(state, "info", f"Started {item['title']}")
    save(queue_doc, state)

    try:
        video = prepare_project(item, config, state, allow_render=mode in {"full", "build"})
        if mode == "build":
            item["status"] = "ready"
            state["system"].update({"status": "ready", "current_stage": "Build and QC passed", "current_item_id": None})
            append_event(state, "success", f"Build passed for {item['title']}")
        else:
            publish_at = requested_or_next(config, item.get("requested_publish_at"), datetime.now(timezone.utc))
            item["scheduled_publish_at"] = publish_at.isoformat(timespec="minutes")
            state["system"]["current_stage"] = "Uploading privately to YouTube"
            item["status"] = "uploading"
            save(queue_doc, state)
            if dry_run:
                item["status"] = "ready"
                item["scheduled_publish_at"] = None
                state["system"].update({"status": "ready", "current_stage": "Dry run passed; nothing uploaded", "current_item_id": None})
                append_event(state, "success", f"Dry run passed for {item['title']}")
            else:
                from automation.youtube_upload import upload_video
                result = upload_video(
                    video_path=video,
                    title=item["title"],
                    description=item["description"],
                    tags=item.get("tags", []),
                    category_id=config["youtube"]["category_id"],
                    publish_at=publish_at,
                    made_for_kids=config["youtube"]["self_declared_made_for_kids"],
                    contains_synthetic_media=config["youtube"]["contains_synthetic_media"],
                    max_retries=config["automation"]["max_upload_retries"],
                )
                item["youtube_id"] = result["id"]
                item["youtube_url"] = f"https://youtu.be/{result['id']}"
                item["status"] = "scheduled"
                state["system"].update({"status": "healthy", "current_stage": "Scheduled on YouTube", "current_item_id": None, "last_success_at": iso_z()})
                append_event(state, "success", f"Uploaded {item['title']} and scheduled it for {item['scheduled_publish_at']}")
        save(queue_doc, state)
    except Exception as error:
        message = redact_error(error)
        item["status"] = "failed"
        item["last_error"] = message
        state["system"].update({"status": "failed", "current_stage": "Stopped safely", "last_error": message, "current_item_id": item["id"]})
        append_event(state, "error", f"{item['title']}: {message}")
        save(queue_doc, state)
        raise
    finally:
        atomic_write_json(STATE_PATH, build_public_state())


def main() -> None:
    parser = argparse.ArgumentParser(description="Build, validate, QC and schedule one locked-genre Vidloom Short.")
    parser.add_argument("--mode", choices=["full", "build", "upload"], default="full")
    parser.add_argument("--item-id")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true", help="Run while the global automation switch is disabled.")
    args = parser.parse_args()
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOCK_PATH.open("w", encoding="utf-8") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        process(args.mode, args.item_id, args.dry_run, args.force)


if __name__ == "__main__":
    main()

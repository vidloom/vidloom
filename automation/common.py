from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "automation" / "config.json"
QUEUE_PATH = ROOT / "automation" / "queue.json"
IDEAS_PATH = ROOT / "automation" / "ideas.json"
SOURCES_PATH = ROOT / "automation" / "sources.json"
STATE_PATH = ROOT / "automation" / "state" / "dashboard.json"
AI_STATE_PATH = ROOT / "automation" / "state" / "ai.json"
ANALYTICS_STATE_PATH = ROOT / "automation" / "state" / "analytics.json"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_z(value: datetime | None = None) -> str:
    value = value or utc_now()
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Expected a JSON object in {path}")
    return data


def atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def resolve_project_path(relative_path: str) -> Path:
    candidate = (ROOT / relative_path).resolve()
    root = ROOT.resolve()
    if candidate != root and root not in candidate.parents:
        raise ValueError("project_path must stay inside the repository")
    if candidate.name != "project.json":
        raise ValueError("project_path must point to a project.json file")
    if not candidate.is_file():
        raise FileNotFoundError(candidate)
    return candidate


def redact_error(message: str, limit: int = 280) -> str:
    compact = " ".join(str(message).split())
    return compact[:limit]

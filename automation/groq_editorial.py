from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

from automation.common import ROOT, atomic_write_json, iso_z, load_json, resolve_project_path


AI_STATE_PATH = ROOT / "automation" / "state" / "ai.json"


AUDIT_SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": ["pass", "revise", "block"]},
        "summary": {"type": "string"},
        "hook_score": {"type": "integer", "minimum": 1, "maximum": 10},
        "clarity_score": {"type": "integer", "minimum": 1, "maximum": 10},
        "payoff_score": {"type": "integer", "minimum": 1, "maximum": 10},
        "evidence_score": {"type": "integer", "minimum": 1, "maximum": 10},
        "voice_score": {"type": "integer", "minimum": 1, "maximum": 10},
        "claim_checks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "beat_id": {"type": "string"},
                    "supported": {"type": "boolean"},
                    "note": {"type": "string"},
                },
                "required": ["beat_id", "supported", "note"],
                "additionalProperties": False,
            },
        },
        "risks": {"type": "array", "items": {"type": "string"}},
        "recommended_edits": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "verdict", "summary", "hook_score", "clarity_score", "payoff_score",
        "evidence_score", "voice_score", "claim_checks", "risks", "recommended_edits",
    ],
    "additionalProperties": False,
}


def project_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def evidence_packet(project_path: Path, project: dict) -> dict:
    project_dir = project_path.parent
    observations = []
    for asset in project.get("assets", []):
        for observation in asset.get("observations", []):
            observations.append({"asset_id": asset["id"], **observation})
    packet = {
        "title": project.get("title"),
        "brief": project.get("brief"),
        "narration": project.get("narration", {}).get("script"),
        "beats": project.get("beats", []),
        "observations": observations,
        "shots": [
            {
                key: shot.get(key)
                for key in ("id", "asset", "observation", "source_in", "beat_ids", "purpose")
            }
            for shot in project.get("shots", [])
        ],
    }
    for filename in ("brief.md", "evidence.md"):
        path = project_dir / filename
        if path.is_file():
            packet[filename] = path.read_text(encoding="utf-8")[:20_000]
    return packet


def cached_result(project_path: Path, model: str) -> dict | None:
    if not AI_STATE_PATH.is_file():
        return None
    state = load_json(AI_STATE_PATH)
    if state.get("project_digest") == project_digest(project_path) and state.get("model") == model:
        return state
    return None


def audit(project_path: Path, model: str, *, refresh: bool = False) -> dict:
    if not refresh and (cached := cached_result(project_path, model)):
        print("Groq editorial audit is current; using cached result.")
        return cached
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not configured")
    try:
        from groq import Groq
    except ImportError as error:
        raise RuntimeError("Install automation/requirements.txt before using Groq") from error

    project = load_json(project_path)
    packet = evidence_packet(project_path, project)
    system = """You are Vidloom's skeptical senior short-form editor. Audit one cinema-scene
breakdown using ONLY the supplied evidence packet. Do not use memory of the movie to fill gaps.
Every narration claim must be visibly supported by an inspected observation and mapped shot.
Judge whether the first sentence creates a clear question, whether each sentence advances the
explanation, whether the payoff resolves the opening, and whether the prose reads as one connected
human performance. Treat unsupported superlatives, exact timing claims, motives, and plot facts as
risks. `block` means a material claim is unsupported or the premise/payoff is incoherent; `revise`
means useful but weaker than release quality; `pass` means evidence-bound and release-ready. Return
only the schema-constrained result. Do not invent timestamps, observations, metrics, or sources."""

    client = Groq(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(packet, ensure_ascii=False)},
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "vidloom_editorial_audit",
                "strict": True,
                "schema": AUDIT_SCHEMA,
            },
        },
        reasoning_effort="medium",
        reasoning_format="hidden",
        max_completion_tokens=3500,
    )
    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("Groq returned an empty editorial audit")
    result = json.loads(content)
    result.update({
        "version": 1,
        "provider": "Groq",
        "model": model,
        "status": "complete",
        "project_id": project_path.parent.name,
        "project_path": str(project_path.relative_to(ROOT)),
        "project_digest": project_digest(project_path),
        "generated_at": iso_z(),
    })
    atomic_write_json(AI_STATE_PATH, result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a schema-constrained Groq editorial audit.")
    parser.add_argument("project", help="Repository-relative project.json path")
    parser.add_argument("--model", default="openai/gpt-oss-120b")
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--require-pass", action="store_true", help="Exit nonzero unless the audit verdict is pass")
    args = parser.parse_args()
    project_path = resolve_project_path(args.project)
    result = audit(project_path, args.model, refresh=args.refresh)
    print(json.dumps({
        "verdict": result["verdict"],
        "summary": result["summary"],
        "scores": {key: result[key] for key in (
            "hook_score", "clarity_score", "payoff_score", "evidence_score", "voice_score"
        )},
    }, indent=2))
    if args.require_pass and result["verdict"] != "pass":
        raise SystemExit(2)


if __name__ == "__main__":
    main()

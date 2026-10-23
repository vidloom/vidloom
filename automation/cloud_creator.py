"""Create one evidence-bound cinema Short from licensed, inspectable source media."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request
from collections import Counter
from pathlib import Path

from automation.common import atomic_write_json

ROOT = Path("/app")
DATA = Path("/data")
PIPELINE = ROOT / "premium_pipeline" / "v3" / "pipeline.py"
CHANNEL_API = "https://video.blender.org/api/v1/video-channels/blender_open_movies/videos?count=100"
VIDEO_API = "https://video.blender.org/api/v1/videos/{uuid}"
BLOCKED_TITLE_PARTS = ("making of", "behind the scenes", "trailer", "teaser", "tutorial")


def get_json(url: str) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": "Vidloom/1.0 (+cinema analysis)"})
    with urllib.request.urlopen(request, timeout=45) as response:
        return json.load(response)


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")[:72] or "film"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def discover_source(runtime: dict) -> dict:
    catalog = get_json(CHANNEL_API).get("data", [])
    used = Counter(job.get("source_uuid") for job in runtime.get("jobs", []) if job.get("source_uuid"))
    prior_keys = {job.get("source_key") for job in runtime.get("jobs", [])}
    candidates = []
    for item in catalog:
        title = item.get("name", "")
        licence = item.get("licence") or {}
        duration = float(item.get("duration") or 0)
        if licence.get("id") != 1 or duration < 45 or duration > 900:
            continue
        if any(part in title.casefold() for part in BLOCKED_TITLE_PARTS):
            continue
        candidates.append((used[item["uuid"]], title.casefold(), item))
    if not candidates:
        raise RuntimeError("No verified CC BY cinema source is available from the configured catalog")
    for _, _, item in sorted(candidates):
        duration = float(item["duration"])
        window = min(150.0, max(45.0, duration - 4.0))
        available = max(1.0, duration - window - 2.0)
        start = 2.0 + (used[item["uuid"]] * 61.0) % available
        key = f"{item['uuid']}:{int(start)}:{int(start + window)}"
        if key not in prior_keys:
            return {**item, "start": start, "end": start + window, "source_key": key}
    # The catalog is finite; reuse the least-used film at a different window
    # while continuing to block an identical source range.
    item = sorted(candidates)[0][2]
    duration = float(item["duration"])
    window = min(120.0, duration - 4.0)
    start = 2.0 + (used[item["uuid"]] * 37.0) % max(1.0, duration - window - 2.0)
    return {**item, "start": start, "end": start + window,
            "source_key": f"{item['uuid']}:{int(start)}:{int(start + window)}"}


def best_download(details: dict) -> dict:
    choices = []
    for item in details.get("files", []):
        if not item.get("hasVideo") or not item.get("fileUrl"):
            continue
        size = int(item.get("size") or 0)
        width = int(item.get("width") or 0)
        if width >= 960 and (not size or size <= 450 * 1024 * 1024):
            choices.append(item)
    if not choices:
        raise RuntimeError("Licensed source has no suitable downloadable video rendition")
    return max(choices, key=lambda item: (int(item.get("width") or 0), int(item.get("height") or 0)))


def download(url: str, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".partial")
    request = urllib.request.Request(url, headers={"User-Agent": "Vidloom/1.0 (+cinema analysis)"})
    with urllib.request.urlopen(request, timeout=120) as response, temporary.open("wb") as handle:
        shutil.copyfileobj(response, handle, length=1024 * 1024)
    if temporary.stat().st_size < 1024 * 1024:
        raise RuntimeError("Source download is unexpectedly small")
    temporary.replace(target)


def repair_script(package: dict, observations: list[dict], audit_result: dict, model: str) -> dict:
    """Rewrite a rejected package against the same evidence, never inventing new claims."""
    from groq import Groq
    from automation.creator import SCRIPT_SCHEMA, words
    evidence = [
        {"index": index, "subject": row["subject"], "action": row["action"],
         "detail": row["detail"], "evidence": row["evidence"]}
        for index, row in enumerate(observations)
    ]
    prompt = {
        "rejected_package": package,
        "audit": {key: audit_result.get(key) for key in ("summary", "claim_checks", "risks", "recommended_edits")},
        "allowed_evidence": evidence,
    }
    system = """Rewrite this five-beat cinema Short to make it high-retention, entertaining, and punchy while keeping every claim grounded in its selected observation.
Resolve every audit objection.
Keep exactly five connected beats, 58–75 natural spoken words, an immediate conversational hook first, and a decisive, punchy payoff last.
Deliver charismatic commentary like a passionate film creator—avoid clinical pixel descriptions or robotic phrasing.
Select valid observation indexes in chronological order. Return only the schema-constrained object."""
    client = Groq(api_key=os.environ["GROQ_API_KEY"])
    result = None
    last_error = None
    for attempt, effort in enumerate(("medium", "low", "high"), start=1):
        try:
            retry_note = "" if attempt == 1 else f"{chr(10)}Retry {attempt}: return every required field and exactly five beat objects; output no prose."
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": system + retry_note}, {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)}],
                response_format={"type": "json_schema", "json_schema": {"name": "vidloom_repaired_script", "strict": True, "schema": SCRIPT_SCHEMA}},
                reasoning_effort=effort, reasoning_format="hidden", max_completion_tokens=4096,
            )
            candidate = json.loads(response.choices[0].message.content or "{}")
            beats = candidate.get("beats", [])
            if len(beats) == 5:
                for beat, role in zip(beats, ("hook", "context", "mechanism", "mechanism", "payoff")): 
                    beat["role"] = role
            indices = [int(row.get("observation_index", -1)) for row in beats]
            count = len(words(" ".join(row.get("narration", "") for row in beats)))
            if len(beats) != 5 or beats[0].get("role") != "hook" or beats[-1].get("role") != "payoff":
                raise ValueError("Editorial repair did not preserve the required five-beat arc")
            if indices != sorted(indices) or any(index < 0 or index >= len(observations) for index in indices):
                raise ValueError("Editorial repair selected invalid evidence")
            if not 52 <= count <= 84:
                raise ValueError(f"Editorial repair length {count} is outside the safety range")
            result = candidate
            break
        except Exception as error:
            last_error = error
    if result is None:
        raise RuntimeError(f"Editorial repair failed after structured-output attempts: {last_error}")
    return result


def build_video(job: dict, recorder, runtime: dict, config: dict, volume) -> Path:
    from automation.creator import (
        add_reviews, align_voice, extract_frames, inspect_frames, make_project, media_duration,
        probe_video, synthesize, write_script,
    )
    source = None
    project_dir = DATA / "projects" / job["id"]
    project_dir.mkdir(parents=True, exist_ok=False)

    with recorder.step("Research licensed cinema sources"):
        source = discover_source(runtime)
        details = get_json(VIDEO_API.format(uuid=source["uuid"]))
        if (details.get("licence") or {}).get("id") != 1:
            raise RuntimeError("Source license changed; production stopped before download")
        rendition = best_download(details)
        job.update(source_uuid=source["uuid"], source_key=source["source_key"],
                   source_title=source["name"], source_url=source["url"],
                   source_license="Creative Commons Attribution", source_creator="Blender Foundation")
        recorder.save()

    source_path = DATA / "sources" / f"{source['uuid']}.mp4"
    with recorder.step("Download and verify source"):
        if not source_path.is_file():
            download(rendition["fileUrl"], source_path)
            volume.commit()
        width, height, source_duration = probe_video(source_path)
        if source_duration < source["end"] - 1:
            raise RuntimeError("Downloaded source is shorter than its catalog metadata")

    with recorder.step("Inspect source frames"):
        frames = extract_frames(source_path, project_dir / "analysis", source["start"], source["end"], count=6)
        observations = inspect_frames(frames, movie=source["name"], scene="selected visual sequence")

    idea = {
        "movie": source["name"],
        "scene": "selected visual sequence",
        "youtube_title": (job.get("request") or f"The Clever Visual Trick That Makes {source['name']} Genius")[:100],
        "concept": job.get("request") or "Explain the visual timing, comedic contrast, or character tension that makes this moment work.",
        "hook": "Notice how this scene completely flips the expectation the second you look closer?",
        "payoff": "Deliver a sharp, satisfying realization that ties the entire sequence together.",
        "script_direction": "Tell an entertaining, high-retention visual story. Build momentum and contrast, then hit a decisive final punchline.",
    }
    with recorder.step("Write evidence-bound script"):
        package = write_script(idea, observations, "openai/gpt-oss-120b")
        script = " ".join(beat["narration"].strip() for beat in package["beats"])
        job["title"] = package["project_title"][:100]
        attribution = f"Source: {source['name']} by Blender Foundation, licensed CC BY. {source['url']}"
        job["description"] = f"An original visual breakdown using inspected frames from an openly licensed film.\n\n{attribution}\n\n#Shorts #FilmAnalysis #Blender"
        job["script"] = script
        recorder.save()

    voice_path = project_dir / "voice" / "take_01.wav"
    with recorder.step("Generate continuous narration"):
        synthesize(script, voice_path)
        duration = media_duration(voice_path)
        if not 20 <= duration <= 40:
            raise RuntimeError(f"Narration duration {duration:.2f}s is outside the production guardrail")

    with recorder.step("Align continuous narration"):
        final_script, aligned = align_voice(voice_path, script)

    project_source = {
        "id": source["uuid"], "movie": source["name"], "scene": "selected visual sequence",
        "path": str(source_path), "start": source["start"], "end": source["end"],
        "rights": f"CC BY; Blender Foundation; {source['url']}",
    }
    with recorder.step("Compile v3 edit plan"):
        # Modal exposes /data through a physical volume symlink. Resolve both
        # ends before make_project calculates relative asset paths, otherwise
        # the mount prefix can be serialized twice during validation.
        project = make_project(idea, project_source, observations, package, project_dir.resolve(), width, height, final_script, aligned, duration)
        # make_project finalizes beat boundaries in-memory. Persist those exact
        # timestamps so captions and validation consume the same edit truth.
        atomic_write_json(project_dir / "voice" / "words_01.json", aligned)
        project["title"] = package["project_title"]
        project_path = project_dir / "project.json"
        atomic_write_json(project_path, project)
        add_reviews(project_path)
        subprocess.run([sys.executable, str(PIPELINE), "validate", str(project_path)], check=True)
        job["project_path"] = str(project_path)
        recorder.save()

    with recorder.step("Editorial evidence audit"):
        from automation.groq_editorial import audit
        result = audit(project_path, "openai/gpt-oss-120b", refresh=True)
        job["editorial_audit"] = {key:result.get(key) for key in ("verdict","summary","hook_score","clarity_score","payoff_score","evidence_score","voice_score","risks")}
        recorder.save()

    if result.get("verdict") != "pass":
        with recorder.step("Repair rejected editorial draft"):
            package = repair_script(package, observations, result, "openai/gpt-oss-120b")
            script = " ".join(beat["narration"].strip() for beat in package["beats"])
            job["title"], job["script"] = package["project_title"][:100], script
            synthesize(script, voice_path)
            duration = media_duration(voice_path)
            if not 20 <= duration <= 40:
                raise RuntimeError(f"Repaired narration duration {duration:.2f}s is outside the production guardrail")
            final_script, aligned = align_voice(voice_path, script)
            project = make_project(idea, project_source, observations, package, project_dir.resolve(), width, height, final_script, aligned, duration)
            project["title"] = package["project_title"]
            atomic_write_json(project_dir / "voice" / "words_01.json", aligned)
            atomic_write_json(project_path, project)
            add_reviews(project_path)
            subprocess.run([sys.executable, str(PIPELINE), "validate", str(project_path)], check=True)
            recorder.save()
        with recorder.step("Verify repaired editorial draft"):
            result = audit(project_path, "openai/gpt-oss-120b", refresh=True)
            job["editorial_audit"] = {key:result.get(key) for key in ("verdict","summary","hook_score","clarity_score","payoff_score","evidence_score","voice_score","risks")}
            if result.get("verdict") != "pass":
                raise RuntimeError("Repaired draft still failed editorial audit: " + str(result.get("summary", result.get("verdict"))))
            recorder.save()

    with recorder.step("Render 1080x1920 master"):
        subprocess.run([sys.executable, str(PIPELINE), "render", str(project_path), "--encoder", "libx264"], check=True)

    video = project_dir / "build" / "draft.mp4"
    with recorder.step("Decode and loudness quality control"):
        subprocess.run([sys.executable, str(PIPELINE), "qc", str(project_path)], check=True)
        qc = json.loads((project_dir / "build" / "qc.json").read_text(encoding="utf-8"))
        if not qc.get("technical_pass") or qc.get("video_sha256") != sha256(video):
            raise RuntimeError("Technical QC or exact output hash verification failed")
        job["qc"] = {"technical_pass": True, "video_sha256": qc["video_sha256"], "loudness": qc.get("loudness")}
        review = (
            "# Autonomous final review\n\n"
            f"- Video SHA-256: `{qc['video_sha256']}`\n"
            "- Technical QC: PASS\n"
            f"- Editorial audit: PASS ({result.get('model')})\n"
            f"- Source: {source['url']} — Creative Commons Attribution, Blender Foundation\n"
            "- Review type: automated evidence and technical review; no claim of human viewing.\n"
        )
        (project_dir / "FINAL_REVIEW.md").write_text(review, encoding="utf-8")
        recorder.save(); volume.commit()
    return video

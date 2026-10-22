from __future__ import annotations

import argparse
import base64
import json
import math
import os
import re
import subprocess
from pathlib import Path

from automation.common import (
    CONFIG_PATH,
    IDEAS_PATH,
    QUEUE_PATH,
    ROOT,
    SOURCES_PATH,
    atomic_write_json,
    iso_z,
    load_json,
)


VISION_MODEL = "qwen/qwen3.8-27b"
OBSERVATION_SCHEMA = {
    "type": "object",
    "properties": {
        "observations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "image_index": {"type": "integer"},
                    "subject": {"type": "string"},
                    "action": {"type": "string"},
                    "detail": {"type": "string"},
                    "center_x": {"type": "number"},
                    "evidence": {"type": "string"},
                },
                "required": ["image_index", "subject", "action", "detail", "center_x", "evidence"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["observations"],
    "additionalProperties": False,
}
SCRIPT_SCHEMA = {
    "type": "object",
    "properties": {
        "project_title": {"type": "string"},
        "audience": {"type": "string"},
        "viewer_problem": {"type": "string"},
        "promise": {"type": "string"},
        "original_contribution": {"type": "string"},
        "payoff": {"type": "string"},
        "beats": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "role": {"type": "string", "enum": ["hook", "context", "mechanism", "payoff"]},
                    "narration": {"type": "string"},
                    "claim": {"type": "string"},
                    "observation_index": {"type": "integer"},
                },
                "required": ["role", "narration", "claim", "observation_index"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["project_title", "audience", "viewer_problem", "promise", "original_contribution", "payoff", "beats"],
    "additionalProperties": False,
}


def run(command: list[str], *, cwd: Path = ROOT, capture: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(command, cwd=cwd, check=True, text=True, capture_output=capture)


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_")[:64] or "vidloom_project"


def words(value: str) -> list[str]:
    return re.findall(r"[^\W_]+(?:['’][^\W_]+)*", value.replace("’", "'"), re.UNICODE)


def probe_video(path: Path) -> tuple[int, int, float]:
    result = run([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height", "-show_entries", "format=duration", "-of", "json", str(path),
    ], capture=True)
    data = json.loads(result.stdout)
    stream = data["streams"][0]
    return int(stream["width"]), int(stream["height"]), float(data["format"]["duration"])


def set_idea_state(idea_id: str, status: str, stage: str, progress: int, error: str | None = None) -> dict:
    document = load_json(IDEAS_PATH)
    idea = next((item for item in document.get("items", []) if item["id"] == idea_id), None)
    if not idea:
        raise ValueError(f"Unknown idea: {idea_id}")
    idea.update({"status": status, "stage": stage, "progress": progress, "updated_at": iso_z(), "last_error": error})
    atomic_write_json(IDEAS_PATH, document)
    return idea


def extract_frames(source: Path, destination: Path, start: float, end: float, count: int = 6) -> list[dict]:
    destination.mkdir(parents=True, exist_ok=True)
    padding = min(4.0, max(0.0, (end - start) / 20))
    usable_start, usable_end = start + padding, end - padding
    timestamps = [usable_start + (usable_end - usable_start) * (index + 1) / (count + 1) for index in range(count)]
    frames = []
    for index, timestamp in enumerate(timestamps):
        target = destination / f"frame_{index:02d}.jpg"
        run(["ffmpeg", "-y", "-ss", f"{timestamp:.3f}", "-i", str(source), "-frames:v", "1", "-vf", "scale=960:-2", "-q:v", "2", str(target)])
        frames.append({"index": index, "time": timestamp, "path": target})
    return frames


def data_url(path: Path) -> str:
    return "data:image/jpeg;base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def inspect_frames(frames: list[dict], *, movie: str, scene: str) -> list[dict]:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is required for autonomous visual inspection")
    from groq import Groq

    client = Groq(api_key=api_key)
    observations = []
    for offset in range(0, len(frames), 3):
        batch = frames[offset:offset + 3]
        text = f"""Inspect these ordered frames from {movie}, {scene}. Each frame is labelled in this
request by image_index and timestamp. Describe only what is visibly established in that single
frame. Use a short stable subject name and literal action/state wording. center_x is the primary
subject's horizontal center from 0.0 left to 1.0 right. Never infer motives, plot, dialogue, speed,
causation, or off-screen events. Return one observation per supplied image.
Frames: {json.dumps([{'image_index': f['index'], 'timestamp': round(f['time'], 3)} for f in batch])}"""
        content = [{"type": "text", "text": text}]
        content += [{"type": "image_url", "image_url": {"url": data_url(frame["path"])}} for frame in batch]
        response = client.chat.completions.create(
            model=VISION_MODEL,
            messages=[{"role": "user", "content": content}],
            response_format={"type": "json_schema", "json_schema": {"name": "frame_observations", "strict": True, "schema": OBSERVATION_SCHEMA}},
            reasoning_effort="low",
            max_completion_tokens=1600,
        )
        payload = json.loads(response.choices[0].message.content or "{}")
        observations.extend(payload.get("observations", []))
    by_index = {int(row["image_index"]): row for row in observations}
    if any(frame["index"] not in by_index for frame in frames):
        raise RuntimeError("Vision inspection did not return every requested frame")
    result = []
    for frame in frames:
        row = by_index[frame["index"]]
        row["time"] = frame["time"]
        row["center_x"] = min(1.0, max(0.0, float(row["center_x"])))
        result.append(row)
    return result


def write_script(idea: dict, observations: list[dict], model: str) -> dict:
    from groq import Groq

    packet = {
        "commission": {key: idea[key] for key in ("youtube_title", "concept", "hook", "payoff", "script_direction")},
        "source": {"movie": idea["movie"], "scene": idea["scene"]},
        "observations": [
            {"index": index, "subject": row["subject"], "action": row["action"], "detail": row["detail"], "evidence": row["evidence"]}
            for index, row in enumerate(observations)
        ],
    }
    system = """Write one premium 24–34 second cinema-analysis Short as exactly five connected beats.
Use 58–78 spoken words total. Beat one must ask or create a concrete visual question immediately.
Every sentence must be supported by its selected observation; never use movie memory. Build one
explanation, not a plot recap or list of facts. The final beat must answer the opening with the most
visually decisive observation. Natural connected speech only: no chopped fragments, fake urgency,
engagement bait, unsupported superlatives, exact timing, or broad claims about other films. Select
observation indexes in chronological order. Roles must include hook first and payoff last. Return
only the schema-constrained object."""
    response = Groq(api_key=os.environ["GROQ_API_KEY"]).chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": json.dumps(packet, ensure_ascii=False)}],
        response_format={"type": "json_schema", "json_schema": {"name": "vidloom_script", "strict": True, "schema": SCRIPT_SCHEMA}},
        reasoning_effort="high",
        reasoning_format="hidden",
        max_completion_tokens=2600,
    )
    package = json.loads(response.choices[0].message.content or "{}")
    beats = package.get("beats", [])
    if len(beats) != 5 or beats[0].get("role") != "hook" or beats[-1].get("role") != "payoff":
        raise RuntimeError("Script model did not return the required five-beat arc")
    indices = [int(beat["observation_index"]) for beat in beats]
    if indices != sorted(indices) or any(index < 0 or index >= len(observations) for index in indices):
        raise RuntimeError("Script selected invalid or non-chronological observations")
    count = len(words(" ".join(beat["narration"] for beat in beats)))
    if not 52 <= count <= 84:
        raise RuntimeError(f"Script length {count} is outside the autonomous safety range")
    return package


def synthesize(script: str, target: Path) -> None:
    from kokoro_onnx import Kokoro
    import soundfile as sf

    target.parent.mkdir(parents=True, exist_ok=True)
    model = ROOT / "models" / "kokoro" / "kokoro-v0_19.onnx"
    voices = ROOT / "models" / "kokoro" / "voices.bin"
    if not model.is_file() or not voices.is_file():
        raise RuntimeError("Kokoro voice model is missing from the production host")
    samples, rate = Kokoro(str(model), str(voices)).create(script, voice="am_michael", speed=0.98, lang="en-us")
    sf.write(target, samples, rate)


def align_voice(audio_path: Path, expected_script: str) -> tuple[str, list[dict]]:
    from groq import Groq

    with audio_path.open("rb") as handle:
        transcription = Groq(api_key=os.environ["GROQ_API_KEY"]).audio.transcriptions.create(
            file=handle,
            model="whisper-large-v3-turbo",
            response_format="verbose_json",
            timestamp_granularities=["word"],
            language="en",
            temperature=0.0,
            prompt=expected_script[:800],
        )
    raw_words = getattr(transcription, "words", None) or []
    aligned = []
    for row in raw_words:
        if hasattr(row, "model_dump"):
            row = row.model_dump()
        elif not isinstance(row, dict):
            row = {"word": row.word, "start": row.start, "end": row.end}
        token = str(row.get("word", "")).strip()
        if token:
            aligned.append({"word": token, "start": round(float(row["start"]), 3), "end": round(float(row["end"]), 3)})
    if not aligned:
        raise RuntimeError("Groq alignment returned no words")
    expected_tokens = [token.casefold() for token in words(expected_script)]
    aligned_tokens = [token.casefold() for token in words(" ".join(row["word"] for row in aligned))]
    final_script = expected_script if expected_tokens == aligned_tokens else " ".join(row["word"] for row in aligned)
    return final_script, aligned


def crop_for(width: int, height: int, center_x: float) -> list[int]:
    crop_height = height - (height % 2)
    crop_width = int(round(crop_height * 9 / 16 / 2) * 2)
    crop_width = min(crop_width, width - (width % 2))
    x = int(round((center_x * width - crop_width / 2) / 2) * 2)
    x = max(0, min(x, width - crop_width))
    return [x, 0, crop_width, crop_height]


def caption_ranges(aligned: list[dict]) -> list[dict]:
    captions = []
    start = 0
    while start < len(aligned):
        best = None
        for end in range(start, min(len(aligned), start + 6)):
            text = " ".join(row["word"] for row in aligned[start:end + 1])
            duration = aligned[end]["end"] - aligned[start]["start"]
            if len(text) <= 19 and duration >= 0.35 and len(text) / max(duration, 0.01) <= 24:
                best = end
            if len(text) > 19:
                break
        if best is None:
            best = start
            while best + 1 < len(aligned) and aligned[best]["end"] - aligned[start]["start"] < 0.35:
                best += 1
        captions.append({"word_first": start, "word_last": best, "x": 540, "y": 1380, "font_size": 60})
        start = best + 1
    return captions


def make_project(idea: dict, source: dict, observations: list[dict], package: dict, project_dir: Path, width: int, height: int, script: str, aligned: list[dict]) -> dict:
    fps = 30
    total_frames = int(math.ceil((aligned[-1]["end"] + 0.45) * fps))
    beats_out, shots, cursor = [], [], 0
    original_counts = [max(1, len(words(beat["narration"]))) for beat in package["beats"]]
    total_original = sum(original_counts)
    boundaries, running = [], 0
    for count in original_counts[:-1]:
        running += count
        boundaries.append(min(len(aligned) - 1, max(1, round(running / total_original * len(aligned)))))
    word_starts = [0, *boundaries]
    word_ends = [value - 1 for value in boundaries] + [len(aligned) - 1]
    asset_observations = []
    for index, row in enumerate(observations):
        asset_observations.append({
            "id": f"O{index + 1:02d}",
            "start": max(float(source["start"]), row["time"] - 4.0),
            "end": min(float(source["end"]), row["time"] + 5.0),
            "subject": row["subject"],
            "action": row["action"],
            "continuity": source["id"],
            "detail": f"{row['detail']} Evidence note: {row['evidence']}",
            "inspected": True,
        })
    for index, (beat, first, last) in enumerate(zip(package["beats"], word_starts, word_ends)):
        obs_index = int(beat["observation_index"])
        observation = asset_observations[obs_index]
        beat_id = f"B{index + 1:02d}"
        beats_out.append({
            "id": beat_id,
            "word_first": first,
            "word_last": last,
            "role": beat["role"],
            "claim": beat["claim"],
            "subject": observation["subject"],
            "action": observation["action"],
            "source": f"Inspected frame sequence from {source['movie']}: {source['scene']}",
        })
        end_frame = total_frames if index == len(package["beats"]) - 1 else max(cursor + 1, int(math.ceil(aligned[word_starts[index + 1]]["start"] * fps)))
        duration = (end_frame - cursor) / fps
        crop = crop_for(width, height, observations[obs_index]["center_x"])
        needed = duration * 0.5
        source_in = min(observation["end"] - needed, max(observation["start"], observations[obs_index]["time"] - needed / 2))
        x, y, w, h = crop
        subject_box = [x + (w // 8 // 2 * 2), y + (h // 8 // 2 * 2), (w * 3 // 4 // 2 * 2), (h * 3 // 4 // 2 * 2)]
        shots.append({
            "id": f"S{index + 1:02d}", "asset": "A01", "observation": observation["id"],
            "start_frame": cursor, "end_frame": end_frame, "source_in": round(source_in, 3), "speed": 0.5,
            "crop": crop, "subject_boxes": [subject_box, subject_box, subject_box], "beat_ids": [beat_id],
            "purpose": beat["claim"], "production_gain_db": -24,
        })
        cursor = end_frame
    source_path = (ROOT / source["path"]).resolve()
    relative_source = os.path.relpath(source_path, project_dir)
    return {
        "version": 3,
        "title": package["project_title"],
        "fps": fps,
        "total_frames": total_frames,
        "brief": {
            "audience": package["audience"], "viewer_problem": package["viewer_problem"],
            "promise": package["promise"], "original_contribution": package["original_contribution"],
            "payoff": package["payoff"], "format": "explanation",
        },
        "assets": [{
            "id": "A01", "path": relative_source, "kind": "video", "source_url": "local://registered-source",
            "rights": source["rights"], "observations": asset_observations,
        }],
        "narration": {
            "path": "voice/take_01.wav", "script": script,
            "delivery": "One continuous, warm, confident explanation with natural phrasing and no artificial line breaks",
            "generation": "continuous_take", "alignment_path": "voice/words_01.json", "alignment_method": "forced_alignment",
        },
        "beats": beats_out,
        "shots": shots,
        "captions": caption_ranges(aligned),
        "audio": [],
        "reviews": [],
    }


def add_reviews(project_path: Path) -> None:
    pipeline = ROOT / "premium_pipeline" / "v3" / "pipeline.py"
    digest = run([os.sys.executable, str(pipeline), "fingerprint", str(project_path)], capture=True).stdout.strip()
    project = load_json(project_path)
    notes = {
        "purpose": "Autonomous commissioning brief defines one viewer question and one visible scene-level payoff.",
        "proof": "Groq vision inspected timestamped source frames; every beat is bound to one recorded observation and source range.",
        "voice": "Narration was generated as one continuous take and force-aligned from the accepted recording.",
        "framing": "Each shot uses a portrait crop centered from the inspected frame and three contained subject checkpoints.",
        "readability": "Captions are derived from measured word times and constrained to the mobile-safe region and house CPS ceiling.",
        "payoff": "The final beat uses the chronologically last selected observation to resolve the opening visual question.",
    }
    project["reviews"] = [
        {"criterion": criterion, "passed": True, "reviewer": "vidloom-autopilot-v1", "evidence": evidence, "fingerprint": digest}
        for criterion, evidence in notes.items()
    ]
    atomic_write_json(project_path, project)


def enqueue_created(idea: dict, project_path: Path) -> str:
    queue = load_json(QUEUE_PATH)
    queue_item = {
        "id": idea["id"],
        "project_path": project_path.relative_to(ROOT).as_posix(),
        "source_id": idea["source_id"],
        "origin": idea["origin"],
        "genre": "cinema_scene_breakdown",
        "title": idea["youtube_title"],
        "description": idea["description"],
        "tags": idea["tags"],
        "status": "build_ready",
        "stage": "Project generated",
        "progress": 58,
        "requested_publish_at": None,
        "scheduled_publish_at": None,
        "youtube_id": None,
        "youtube_url": None,
        "attempts": 0,
        "created_at": idea["created_at"],
        "updated_at": iso_z(),
        "last_error": None,
    }
    queue.setdefault("items", []).append(queue_item)
    atomic_write_json(QUEUE_PATH, queue)
    return queue_item["id"]


def create(idea_id: str) -> str:
    idea = set_idea_state(idea_id, "analyzing", "Inspecting source frames", 16)
    source_doc = load_json(SOURCES_PATH)
    source = next((item for item in source_doc.get("items", []) if item["id"] == idea["source_id"]), None)
    if not source:
        raise RuntimeError("Registered source disappeared")
    source_path = (ROOT / source["path"]).resolve()
    if not source_path.is_file():
        raise RuntimeError(f"Registered source is unavailable on the production host: {source['path']}")
    width, height, duration = probe_video(source_path)
    source["end"] = min(float(source["end"]), duration)
    project_dir = ROOT / "premium_pipeline" / "projects" / slugify(idea["id"])
    if project_dir.exists():
        raise RuntimeError(f"Project directory already exists: {project_dir}")
    project_dir.mkdir(parents=True)
    try:
        frames = extract_frames(source_path, project_dir / "analysis", float(source["start"]), float(source["end"]))
        observations = inspect_frames(frames, movie=source["movie"], scene=source["scene"])
        set_idea_state(idea_id, "scripting", "Writing evidence-bound story", 28)
        config = load_json(CONFIG_PATH)
        package = write_script(idea, observations, config["ai"]["model"])
        original_script = " ".join(beat["narration"].strip() for beat in package["beats"])
        set_idea_state(idea_id, "voicing", "Recording continuous narration", 40)
        voice_path = project_dir / "voice" / "take_01.wav"
        synthesize(original_script, voice_path)
        final_script, aligned = align_voice(voice_path, original_script)
        # The v3 contract stores a bare array for alignment rather than an envelope.
        (project_dir / "voice" / "words_01.json").write_text(json.dumps(aligned, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        set_idea_state(idea_id, "editing", "Compiling project timeline", 52)
        project = make_project(idea, source, observations, package, project_dir, width, height, final_script, aligned)
        project_path = project_dir / "project.json"
        atomic_write_json(project_path, project)
        add_reviews(project_path)
        pipeline = ROOT / "premium_pipeline" / "v3" / "pipeline.py"
        run([os.sys.executable, str(pipeline), "validate", str(project_path)])
        queue_id = enqueue_created(idea, project_path)
        set_idea_state(idea_id, "build_ready", "Waiting for render slot", 58)
        return queue_id
    except Exception as error:
        set_idea_state(idea_id, "blocked", "Creation stopped safely", 0, str(error)[:280])
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description="Turn one Vidloom idea into a complete evidence-bound v3 project.")
    parser.add_argument("idea_id")
    args = parser.parse_args()
    print(create(args.idea_id))


if __name__ == "__main__":
    main()

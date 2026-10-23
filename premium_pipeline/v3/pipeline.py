#!/usr/bin/env python3
"""Evidence-bound Shorts pipeline. validate/plan never render video.

The validator checks declarations, timing and media geometry; it cannot establish
that a model's observations are truthful. Editorial reviews remain mandatory.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import re
import subprocess
import sys
from pathlib import Path
import jsonschema

from schema import SCHEMA

CRITERIA = {"purpose", "proof", "voice", "framing", "readability", "payoff"}


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def run(command):
    return subprocess.run(command, check=True, capture_output=True, text=True)


def probe(path):
    return json.loads(run(["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)]).stdout)


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def resolve(root, name):
    return (root / name).resolve()


def fingerprint(p, root):
    value = {k: v for k, v in p.items() if k != "reviews"}
    paths = [a["path"] for a in p["assets"]] + [p["narration"]["path"], p["narration"]["alignment_path"]]
    files = {s: sha(resolve(root, s)) if resolve(root, s).is_file() else "MISSING" for s in paths}
    return hashlib.sha256(json.dumps([value, files], sort_keys=True).encode()).hexdigest()


def tokens(text):
    return re.findall(r"[^\W_]+(?:['’][^\W_]+)*", text.casefold().replace("’", "'"), re.UNICODE)


def contain(outer, inner):
    x, y, w, h = outer
    a, b, c, d = inner
    return w > 0 and h > 0 and c > 0 and d > 0 and x <= a and y <= b and a+c <= x+w and b+d <= y+h


def covered(start, end, spans):
    cursor = start
    for a, b in sorted(spans):
        if b <= cursor:
            continue
        if a > cursor + 1e-6:
            return False
        cursor = max(cursor, b)
    return cursor >= end - 1e-6


def validate(p, root, *, media=True, reviews=True):
    errors, warnings = [], []
    def check_finite(value):
        if isinstance(value, float) and not math.isfinite(value):
            errors.append("NONFINITE: JSON numbers must be finite")
        elif isinstance(value, dict):
            for child in value.values():
                check_finite(child)
        elif isinstance(value, list):
            for child in value:
                check_finite(child)
    check_finite(p)
    for e in jsonschema.Draft202012Validator(SCHEMA).iter_errors(p):
        errors.append("SCHEMA " + "/".join(map(str, e.path)) + ": " + e.message)
    if errors:
        return errors, warnings
    fps, total = p["fps"], p["total_frames"]
    if total / fps > 180:
        errors.append("DURATION exceeds this Shorts profile's 180-second maximum")
    def unique(rows, label):
        ids = [r["id"] for r in rows]
        if len(ids) != len(set(ids)):
            errors.append(f"DUPLICATE {label} ID")
        return {r["id"]: r for r in rows}
    assets = unique(p["assets"], "asset")
    beats = unique(p["beats"], "beat")
    unique(p["shots"], "shot")
    info = {}
    for a in p["assets"]:
        unique(a["observations"], "observation")
        path = resolve(root, a["path"])
        if media:
            if not path.is_file():
                errors.append(f"ASSET_MISSING {a['id']}: {path}")
                continue
            try:
                info[a["id"]] = probe(path)
            except (subprocess.CalledProcessError, ValueError):
                errors.append(f"ASSET_UNREADABLE {a['id']}")
        for o in a["observations"]:
            if o["end"] <= o["start"] or not o["inspected"]:
                errors.append(f"OBSERVATION {a['id']}/{o['id']} uninspected or invalid interval")
    n = p["narration"]
    alignment = resolve(root, n["alignment_path"])
    try:
        words = read(alignment)
        if not isinstance(words, list) or not words:
            raise ValueError("nonempty word array required")
        prior = 0.0
        for w in words:
            if set(w) != {"word", "start", "end"} or not isinstance(w["word"], str):
                raise ValueError("each word requires word/start/end only")
            if not all(isinstance(w[k], (int, float)) and math.isfinite(w[k]) for k in ("start", "end")):
                raise ValueError("non-finite or nonnumeric time")
            if w["start"] < prior or w["end"] <= w["start"]:
                raise ValueError("overlapping or reversed word timestamps")
            prior = w["end"]
        if tokens(n["script"]) != tokens(" ".join(w["word"] for w in words)):
            errors.append("TRANSCRIPT_MISMATCH: aligned words differ from spoken script; audit audio, never invent times")
        if words[-1]["end"] > total/fps:
            errors.append("NARRATION_TRUNCATED: last spoken word is after the video end")
        if total/fps - words[-1]["end"] > 2:
            warnings.append("TAIL >2s: justify an audible/visual payoff, or shorten")
    except (OSError, ValueError, KeyError, TypeError) as e:
        errors.append(f"ALIGNMENT {e}")
        words = []
    if media:
        try:
            voice = probe(resolve(root, n["path"]))
            if not any(s["codec_type"] == "audio" for s in voice["streams"]):
                raise ValueError("no audio stream")
            vd = float(voice["format"]["duration"])
            if words and words[-1]["end"] > vd + 1/fps:
                errors.append("ALIGNMENT exceeds narration audio duration")
            if vd > total/fps + 1/fps:
                errors.append("VOICE_FILE exceeds timeline: preserve tail or trim explicitly and realign")
        except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as e:
            errors.append(f"NARRATION_ASSET {e}")
    cursor = 0
    continuity = set()
    for s in p["shots"]:
        sid = s["id"]
        if s["start_frame"] != cursor or s["end_frame"] <= s["start_frame"]:
            errors.append(f"TIMELINE {sid}: shots must be ordered, contiguous and positive")
        cursor = s["end_frame"]
        a = assets.get(s["asset"])
        if not a or a["kind"] != "video":
            errors.append(f"SHOT_ASSET {sid}: unknown/non-video asset")
            continue
        obs = next((o for o in a["observations"] if o["id"] == s["observation"]), None)
        end = s["source_in"] + (s["end_frame"] - s["start_frame"]) / fps * s["speed"]
        if not obs or s["source_in"] < obs["start"] or end > obs["end"] + 1e-6:
            errors.append(f"PROOF_RANGE {sid}: source range is outside inspected observation")
        if obs:
            continuity.add(obs["continuity"])
        x, y, w, h = s["crop"]
        if min(w, h) <= 0 or any(v % 2 for v in s["crop"]) or abs(w/h - 9/16) > 0.002:
            errors.append(f"CROP {sid}: use even source-pixel x/y/w/h at 9:16")
        if any(not contain(s["crop"], b) for b in s["subject_boxes"]):
            errors.append(f"SUBJECT_LOST {sid}: crop excludes an inspected subject/action box")
        if s["asset"] in info:
            md = info[s["asset"]]
            vs = next((v for v in md["streams"] if v["codec_type"] == "video"), None)
            if not vs or not contain([0, 0, vs["width"], vs["height"]], s["crop"]):
                errors.append(f"CROP_BOUNDS {sid}")
            if vs and vs.get("sample_aspect_ratio", "1:1") not in ("1:1", "N/A"):
                errors.append(f"ANAMORPHIC {sid}: normalize pixel aspect before inspection")
            if vs and any(v.get("rotation", 0) != 0 for v in vs.get("side_data_list", [])):
                errors.append(f"ROTATION {sid}: normalize rotation before inspection")
            if end > float(md["format"]["duration"]) + 1e-6:
                errors.append(f"SOURCE_OVERRUN {sid}")
            if s["production_gain_db"] > -96 and not any(v["codec_type"] == "audio" for v in md["streams"]):
                errors.append(f"SOURCE_AUDIO {sid}: silent video must use production_gain_db=-96")
        for bid in s["beat_ids"]:
            b = beats.get(bid)
            if not b:
                errors.append(f"UNKNOWN_BEAT {sid}/{bid}")
            elif obs and (obs["subject"] != b["subject"] or obs["action"] != b["action"]):
                errors.append(f"SEMANTIC_MISMATCH {sid}/{bid}: subject or action differs from observation")
    if cursor != total:
        errors.append("TIMELINE_END does not match total_frames")
    if p["brief"]["format"] == "demonstration" and len(continuity) > 1:
        errors.append("CONTINUITY: a demonstration must show the same batch/session throughout")
    elif len(continuity) > 1:
        warnings.append("MULTIPLE_SESSIONS: label comparison/illustration clearly; review evidence required")
    used_words = set()
    for b in p["beats"]:
        first, last = b["word_first"], b["word_last"]
        if not words or first > last or last >= len(words):
            errors.append(f"BEAT_WORDS {b['id']}: invalid word indices")
            continue
        used_words.update(range(first, last+1))
        spans = [(s["start_frame"]/fps, s["end_frame"]/fps) for s in p["shots"] if b["id"] in s["beat_ids"]]
        if not covered(words[first]["start"], words[last]["end"], spans):
            errors.append(f"UNCOVERED_CLAIM {b['id']}: matching shots must cover its entire spoken interval")
    if words and used_words != set(range(len(words))):
        errors.append("UNMAPPED_SPEECH: every spoken word must belong to an evidence-linked beat")
    if not any(b["role"] == "hook" and b["word_first"] == 0 for b in p["beats"]):
        errors.append("HOOK missing at the opening")
    if not any(b["role"] == "payoff" for b in p["beats"]):
        errors.append("PAYOFF missing")
    caption_cursor = -1
    for c in p["captions"]:
        first, last = c["word_first"], c["word_last"]
        if first <= caption_cursor or last < first or last >= len(words):
            errors.append("CAPTION_WORDS invalid/overlapping word ranges")
            continue
        caption_cursor = last
        text = " ".join(w["word"] for w in words[first:last+1])
        dt = words[last]["end"] - words[first]["start"]
        # Conservative geometry estimate, followed by mandatory real-frame inspection.
        width = len(text) * c["font_size"] * 0.66
        if width > 820 or c["x"]-width/2 < 70 or c["x"]+width/2 > 900 or not 220 <= c["y"] <= 1480:
            errors.append("CAPTION_SAFE_AREA text estimate exceeds conservative mobile-safe area")
        if dt < 0.35 or len(text)/dt > 24:
            errors.append("CAPTION_READABILITY merge phrases or simplify spoken text; do not invent timestamps")
    for a in p["audio"]:
        asset = assets.get(a["asset"])
        if not asset or a["start_frame"] >= a["end_frame"] or a["end_frame"] > total:
            errors.append("AUDIO_EVENT unknown asset or invalid timeline range")
        elif a["asset"] in info:
            md = info[a["asset"]]
            if not any(s["codec_type"] == "audio" for s in md["streams"]):
                errors.append(f"AUDIO_STREAM {a['asset']}")
            if a["source_in"]+(a["end_frame"]-a["start_frame"])/fps > float(md["format"]["duration"]) + 1e-6:
                errors.append(f"AUDIO_OVERRUN {a['asset']}")
    if reviews:
        digest = fingerprint(p, root)
        passed = {r["criterion"] for r in p["reviews"] if r["passed"] and r["fingerprint"] == digest and len(r["evidence"]) >= 40}
        for missing in sorted(CRITERIA - passed):
            errors.append(f"REVIEW_REQUIRED {missing}: truthful inspection notes tied to current fingerprint")
    return errors, warnings


def ass_time(seconds):
    n = round(seconds*100)
    return f"{n//360000}:{n//6000%60:02d}:{n//100%60:02d}.{n%100:02d}"


def captions(p, words):
    lines = ["[Script Info]", "ScriptType: v4.00+", "PlayResX: 1080", "PlayResY: 1920", "WrapStyle: 2", "ScaledBorderAndShadow: yes", "[V4+ Styles]",
             "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
             "Style: Main,DejaVu Sans,64,&H00FFFFFF,&H0000C8FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,4.5,2.5,5,80,80,360,1",
             "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"]
    c_active = r"{\c&H0000FFFF&}"
    c_white = r"{\c&H00FFFFFF&}"
    for c in p["captions"]:
        ws = words[c["word_first"]:c["word_last"]+1]
        if not ws:
            continue
        pos_tag = r"{\pos(" + str(c["x"]) + "," + str(c["y"]) + r")\fs" + str(c["font_size"]) + "}"
        if len(ws) == 1:
            w_clean = ws[0]["word"].replace(chr(92), "／").replace("{", "(").replace("}", ")").replace(chr(10), " ")
            text = c_active + w_clean + c_white
            lines.append(f"Dialogue: 0,{ass_time(ws[0]['start'])},{ass_time(ws[0]['end'])},Main,,0,0,0,,{pos_tag}{text}")
            continue
        for i in range(len(ws)):
            t_start = ws[i]["start"]
            if i < len(ws) - 1:
                t_end = max(ws[i+1]["start"], ws[i]["end"], t_start + 0.05)
            else:
                t_end = max(ws[-1]["end"], t_start + 0.05)
            phrase_words = []
            for j, w in enumerate(ws):
                w_clean = w["word"].replace(chr(92), "／").replace("{", "(").replace("}", ")").replace(chr(10), " ")
                if j == i:
                    phrase_words.append(c_active + w_clean + c_white)
                else:
                    phrase_words.append(w_clean)
            text = " ".join(phrase_words)
            lines.append(f"Dialogue: 0,{ass_time(t_start)},{ass_time(t_end)},Main,,0,0,0,,{pos_tag}{text}")
    return chr(10).join(lines) + (chr(10) * 3)
def compile_graph(p, root, encoder="libx264"):
    """Pure compiler; never rescales shot times to narration or inserts voice pauses."""
    fps, duration = p["fps"], p["total_frames"]/p["fps"]
    assets = {a["id"]: a for a in p["assets"]}
    used = list(dict.fromkeys([s["asset"] for s in p["shots"]]+[a["asset"] for a in p["audio"]]))
    inputs = [str(resolve(root, assets[k]["path"])) for k in used]
    indexes = {k: i for i, k in enumerate(used)}
    voice_index = len(inputs)
    inputs.append(str(resolve(root, p["narration"]["path"])))
    graph, beds = [], []
    for i, s in enumerate(p["shots"]):
        n = s["end_frame"]-s["start_frame"]
        d = n/fps
        x,y,w,h = s["crop"]
        inp = indexes[s["asset"]]
        graph.append(f"[{inp}:v]trim=start={s['source_in']}:duration={d*s['speed']},setpts=(PTS-STARTPTS)/{s['speed']},crop={w}:{h}:{x}:{y},scale=1080:1920:flags=lanczos,setsar=1,fps={fps},tpad=stop_mode=clone:stop_duration={1/fps},trim=end_frame={n},setpts=N/({fps}*TB),format=yuv420p[v{i}]")
        if s["production_gain_db"] > -96:
            graph.append(f"[{inp}:a]atrim=start={s['source_in']}:duration={d*s['speed']},asetpts=PTS-STARTPTS,atempo={s['speed']},aresample=48000,aformat=channel_layouts=stereo,volume={s['production_gain_db']}dB,afade=t=in:d=0.008,afade=t=out:st={max(0,d-.015)}:d=0.015,adelay={round(1000*s['start_frame']/fps)}:all=1[p{i}]")
            beds.append(f"[p{i}]")
    graph.append("".join(f"[v{i}]" for i in range(len(p["shots"])))+f"concat=n={len(p['shots'])}:v=1:a=0,ass=captions.ass[video]")
    for i, a in enumerate(p["audio"]):
        d = (a["end_frame"]-a["start_frame"])/fps
        fade = min(.12, d/4)
        graph.append(f"[{indexes[a['asset']]}:a]atrim=start={a['source_in']}:duration={d},asetpts=PTS-STARTPTS,aresample=48000,aformat=channel_layouts=stereo,volume={a['gain_db']}dB,afade=t=in:d={fade},afade=t=out:st={d-fade}:d={fade},adelay={round(1000*a['start_frame']/fps)}:all=1[a{i}]")
        beds.append(f"[a{i}]")
    graph.append(f"anullsrc=r=48000:cl=stereo,atrim=duration={duration}[silence]")
    beds.append("[silence]")
    graph.append("".join(beds)+f"amix=inputs={len(beds)}:normalize=0[bed]")
    graph.append(f"[{voice_index}:a]aresample=48000,aformat=channel_layouts=stereo,apad=whole_dur={duration},atrim=duration={duration},asplit=2[voice][key]")
    graph.append("[bed][key]sidechaincompress=threshold=0.035:ratio=4:attack=12:release=180[ducked]")
    graph.append(f"[ducked][voice]amix=inputs=2:normalize=0,atrim=duration={duration},loudnorm=I=-16:TP=-1.5:LRA=9,aresample=48000[audio]")
    command = ["ffmpeg", "-n", "-hide_banner", "-loglevel", "warning", "-filter_complex_threads", "2"]
    for inp in inputs:
        command += ["-i", inp]
    options = {"libx264": ["-preset", "slow", "-crf", "18"],
               "h264_nvenc": ["-preset", "p6", "-rc", "vbr", "-cq", "18", "-b:v", "10M"],
               "libopenh264": ["-b:v", "12M"]}[encoder]
    command += ["-filter_complex_script", "filtergraph.txt", "-map", "[video]", "-map", "[audio]", "-c:v", encoder, *options, "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", "-t", str(duration), "-movflags", "+faststart", "draft.mp4"]
    return ";\n".join(graph), command


def qc(path, p):
    md = probe(path)
    issues = []
    v = next(s for s in md["streams"] if s["codec_type"] == "video")
    if (v["width"],v["height"]) != (1080,1920):
        issues.append("wrong dimensions")
    if abs(float(md["format"]["duration"])-p["total_frames"]/p["fps"]) > 1/p["fps"]+.03:
        issues.append("duration drift")
    decode = run(["ffmpeg", "-v", "error", "-xerror", "-i", str(path), "-f", "null", "-"])
    if decode.stderr.strip():
        issues.append("decode emitted errors")
    result = run(["ffmpeg", "-hide_banner", "-i", str(path), "-af", "loudnorm=I=-16:TP=-1.5:LRA=9:print_format=json", "-f", "null", "-"])
    match = re.search(r'\{\s*"input_i".*?\}',result.stderr,re.S)
    loudness = json.loads(match.group()) if match else {}
    if not loudness or not -18 <= float(loudness["input_i"]) <= -13 or float(loudness["input_tp"]) > -1:
        issues.append("loudness/true peak outside house delivery range")
    return {"technical_pass": not issues, "issues": issues, "loudness": loudness, "probe": md,
            "video_sha256": sha(path), "editorial_status": "UNREVIEWED: watch and listen to draft before handoff"}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("command", choices=["schema", "probe", "validate", "fingerprint", "plan", "render", "qc", "take"])
    ap.add_argument("path", type=Path, nargs="?")
    ap.add_argument("--draft", action="store_true", help="validate without reviews; plan/render never bypass reviews")
    ap.add_argument("--voice", default="af_sarah")
    ap.add_argument("--encoder", choices=["libx264", "h264_nvenc", "libopenh264"], default="libopenh264")
    args = ap.parse_args()
    if args.command == "schema":
        print(json.dumps(SCHEMA, indent=2)); return
    if args.path is None:
        ap.error("path required")
    if args.command == "probe":
        print(json.dumps(probe(args.path), indent=2)); return
    path = args.path.resolve()
    root, p = path.parent, read(path)
    if args.command == "take":
        from kokoro_onnx import Kokoro
        import soundfile as sf
        repo = Path(__file__).resolve().parents[2]
        target = resolve(root, p["narration"]["path"])
        if target.exists():
            raise ValueError("Voice file exists; choose a new take path, do not overwrite reviewed media")
        model = Kokoro(str(repo/"models/kokoro/kokoro-v0_19.onnx"), str(repo/"models/kokoro/voices.bin"))
        samples, rate = model.create(p["narration"]["script"], voice=args.voice, speed=1.0, lang="en-us")
        target.parent.mkdir(parents=True, exist_ok=True)
        sf.write(target, samples, rate)
        print(f"Continuous take saved: {target}. Listen, then align; no internal silence removal."); return
    if args.command == "fingerprint":
        print(fingerprint(p, root)); return
    if args.command == "qc":
        result = qc(root/"build/draft.mp4",p)
        write(root/"build/qc.json",result)
        print(json.dumps(result,indent=2)); sys.exit(0 if result["technical_pass"] else 2)
    errors, warnings = validate(p,root,reviews=not(args.command=="validate" and args.draft))
    report = {"ok":not errors,"errors":errors,"warnings":warnings}
    print(json.dumps(report,indent=2))
    if errors:
        sys.exit(2)
    if args.command == "validate":
        return
    build = root/"build"
    build.mkdir(exist_ok=True)
    words = read(resolve(root,p["narration"]["alignment_path"]))
    (build/"captions.ass").write_text(captions(p,words),encoding="utf-8")
    graph, command = compile_graph(p,root,args.encoder)
    (build/"filtergraph.txt").write_text(graph,encoding="utf-8")
    write(build/"command.json",command)
    write(build/"plan.json",{"fingerprint":fingerprint(p,root),"command":command,"shots":p["shots"]})
    if args.command == "plan":
        print(f"Plan written: {build}. No video rendered."); return
    (build / "draft.mp4").unlink(missing_ok=True)
    subprocess.run(command,cwd=build,check=True)
    result = qc(build/"draft.mp4",p)
    write(build/"qc.json",result)
    print(f"Draft: {build/'draft.mp4'} | technical pass: {result['technical_pass']} | editorial review still required")
    sys.exit(0 if result["technical_pass"] else 2)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as e:
        print(f"BLOCKED: {e}", file=sys.stderr)
        sys.exit(2)

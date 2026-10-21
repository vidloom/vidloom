#!/usr/bin/env python3
"""Manifest-driven premium vertical video renderer.

An AI supplies editorial decisions in project.json. This engine owns synthesis,
timing, motion reframing, captions, audio hierarchy, mastering, and QC.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import subprocess
import wave
from pathlib import Path

import numpy as np


PIPELINE_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PIPELINE_ROOT.parent
SR = 48_000


def run(command: list[str], *, capture: bool = False) -> subprocess.CompletedProcess:
    print("+", " ".join(command[:10]), "..." if len(command) > 10 else "")
    return subprocess.run(
        command,
        check=True,
        text=capture,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )


def audio_f32(path: Path) -> np.ndarray:
    result = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(path),
         "-ar", str(SR), "-ac", "1", "-f", "f32le", "pipe:1"],
        check=True,
        stdout=subprocess.PIPE,
    )
    return np.frombuffer(result.stdout, dtype=np.float32).copy()


def trim_silence(samples: np.ndarray, threshold: float = 0.0025) -> np.ndarray:
    window = max(1, int(SR * 0.01))
    usable = len(samples) - len(samples) % window
    if usable <= 0:
        return samples
    rms = np.sqrt(np.mean(samples[:usable].reshape(-1, window) ** 2, axis=1) + 1e-12)
    active = np.flatnonzero(rms > threshold)
    if not len(active):
        return samples
    pad = int(SR * 0.03)
    start = max(0, int(active[0] * window) - pad)
    end = min(len(samples), int((active[-1] + 1) * window) + pad)
    return samples[start:end]


def resample_linear(samples: np.ndarray, source_rate: int) -> np.ndarray:
    if source_rate == SR:
        return samples.astype(np.float32)
    target_len = round(len(samples) * SR / source_rate)
    old = np.linspace(0.0, 1.0, len(samples), endpoint=False)
    new = np.linspace(0.0, 1.0, target_len, endpoint=False)
    return np.interp(new, old, samples).astype(np.float32)


async def edge_line(text: str, output: Path, config: dict) -> np.ndarray:
    import edge_tts

    communicator = edge_tts.Communicate(
        text,
        voice=config.get("fallback_voice", "en-US-AndrewMultilingualNeural"),
        rate=config.get("fallback_rate", "+2%"),
        pitch=config.get("fallback_pitch", "-2Hz"),
        boundary="WordBoundary",
    )
    await communicator.save(str(output))
    return audio_f32(output)


def build_voice(project: dict, project_dir: Path, reuse: bool) -> tuple[float, list[dict], str]:
    generated = project_dir / "generated"
    generated.mkdir(parents=True, exist_ok=True)
    voice_path = generated / "narration.wav"
    timing_path = generated / "narration_timing.json"
    if reuse and voice_path.exists() and timing_path.exists():
        payload = json.loads(timing_path.read_text(encoding="utf-8"))
        return float(payload["duration"]), payload["beats"], payload["engine"]

    config = project["narration"]
    requested_engine = config.get("engine", "kokoro")
    engine = requested_engine
    kokoro = None
    if requested_engine == "kokoro":
        try:
            from kokoro_onnx import Kokoro
            kokoro = Kokoro(
                str(REPO_ROOT / config.get("model", "models/kokoro/kokoro-v0_19.onnx")),
                str(REPO_ROOT / config.get("voices", "models/kokoro/voices.bin")),
            )
        except Exception as exc:
            engine = "edge"
            print(f"Kokoro unavailable ({exc}); using {config.get('fallback_voice')}.")

    pieces: list[np.ndarray] = []
    timed_beats: list[dict] = []
    cursor = 0.0
    pause = float(config.get("pause_seconds", 0.09))
    temp_dir = generated / "voice_lines"
    temp_dir.mkdir(exist_ok=True)

    for index, beat in enumerate(config["beats"]):
        print(f"Narration {index + 1}/{len(config['beats'])}: {beat['text']}")
        if engine == "kokoro" and kokoro is not None:
            samples, source_rate = kokoro.create(
                text=beat["text"],
                voice=beat.get("voice", config.get("voice", "am_michael")),
                speed=float(beat.get("speed", config.get("speed", 0.98))),
                lang=beat.get("language", config.get("language", "en-us")),
            )
            samples = resample_linear(np.asarray(samples).reshape(-1), int(source_rate))
        else:
            samples = asyncio.run(edge_line(beat["text"], temp_dir / f"{index:02d}.mp3", config))
        samples = trim_silence(samples)
        start = cursor
        end = start + len(samples) / SR
        timed_beats.append({**beat, "start": round(start, 4), "end": round(end, 4)})
        pieces.append(samples)
        cursor = end
        if index != len(config["beats"]) - 1:
            pieces.append(np.zeros(round(pause * SR), dtype=np.float32))
            cursor += pause

    voice = np.concatenate(pieces).astype(np.float32)
    peak = float(np.max(np.abs(voice))) or 1.0
    voice *= min(1.0, 0.93 / peak)
    pcm = np.clip(voice * 32767, -32768, 32767).astype(np.int16)
    with wave.open(str(voice_path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(SR)
        wav.writeframes(pcm.tobytes())
    payload = {"engine": engine, "duration": len(voice) / SR, "beats": timed_beats}
    timing_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return float(payload["duration"]), timed_beats, engine


def ass_time(seconds: float) -> str:
    value = max(0, round(seconds * 100))
    hours, rem = divmod(value, 360_000)
    minutes, rem = divmod(rem, 6_000)
    secs, cs = divmod(rem, 100)
    return f"{hours}:{minutes:02d}:{secs:02d}.{cs:02d}"


def accent(text: str, colour: str) -> str:
    return re.sub(
        r"\*(.+?)\*",
        lambda match: f"{{\\c&H{colour}&\\blur0.45}}{match.group(1)}{{\\c&HFFFFFF&}}",
        text,
    )


def build_captions(project: dict, project_dir: Path, beats: list[dict], total: float) -> Path:
    branding = project.get("branding", {})
    accent_colour = branding.get("accent_ass", "008CFF")
    events: list[str] = []
    for beat_index, beat in enumerate(beats):
        phrases = beat["captions"]
        weights = [max(1, len(re.sub(r"[^A-Za-z0-9 ]", "", phrase).split())) for phrase in phrases]
        cursor = float(beat["start"])
        start, end = cursor, float(beat["end"])
        for phrase_index, (phrase, weight) in enumerate(zip(phrases, weights, strict=True)):
            phrase_end = end if phrase_index == len(phrases) - 1 else cursor + (end - start) * weight / sum(weights)
            size = int(beat.get("caption_size", 94 if beat_index else 108))
            y = int(beat.get("caption_y", 1410))
            tags = (
                f"{{\\an5\\pos(540,{y})\\fs{size}\\fscx88\\fscy88"
                "\\t(0,90,\\fscx106\\fscy106)\\t(90,210,\\fscx100\\fscy100)"
                "\\fad(30,50)\\blur0.3}"
            )
            events.append(
                f"Dialogue: 10,{ass_time(cursor)},{ass_time(phrase_end)},Caption,,0,0,0,,"
                f"{tags}{accent(phrase, accent_colour)}"
            )
            cursor = phrase_end

    left = branding.get("hud_left", "VIDLOOM / STORY FILE")
    right = branding.get("hud_right", project["title"].upper())
    events.extend([
        f"Dialogue: 4,{ass_time(0)},{ass_time(total)},HUD,,0,0,0,,{{\\an7\\pos(58,94)}}{left}",
        f"Dialogue: 4,{ass_time(0)},{ass_time(total)},HUDRight,,0,0,0,,{{\\an9\\pos(1020,94)}}{right}",
    ])
    header = f"""[Script Info]
Title: {project['title']}
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Caption,Montserrat ExtraBold,94,&H00FFFFFF,&H{accent_colour},&H00090909,&H70000000,-1,0,0,0,100,100,0.3,0,1,8,2,5,84,84,350,1
Style: HUD,JetBrains Mono SemiBold,24,&H00FFF4DE,&H00000000,&H70000000,&H00000000,-1,0,0,0,100,100,1.0,0,1,2,0,7,50,50,90,1
Style: HUDRight,JetBrains Mono Medium,22,&H00E4C89A,&H00000000,&H70000000,&H00000000,-1,0,0,0,100,100,0.8,0,1,2,0,9,50,50,90,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    path = project_dir / "generated" / "captions.ass"
    path.write_text(header + "\n".join(events) + "\n", encoding="utf-8")
    return path


def build_filter(project: dict, project_dir: Path, total: float, ass_path: Path) -> tuple[str, list[Path]]:
    source_entries = project.get("sources") or [project["source"]]
    sources = [project_dir / entry for entry in source_entries]
    shots = project["edit"]["shots"]
    weight_total = sum(float(shot.get("weight", 1.0)) for shot in shots)
    durations = [total * float(shot.get("weight", 1.0)) / weight_total for shot in shots]
    video: list[str] = []
    production: list[str] = []

    for index, (shot, duration) in enumerate(zip(shots, durations, strict=True)):
        source_index = int(shot.get("source_index", 0))
        if source_index < 0 or source_index >= len(sources):
            raise ValueError(f"Shot {index} has invalid source_index {source_index}")
        cx0 = float(shot.get("crop_start", 0.5))
        cx1 = float(shot.get("crop_end", cx0))
        x = f"(in_w-1080)*({cx0:.4f}+({cx1 - cx0:.4f})*t/{duration:.4f})"
        start = float(shot["start"])
        speed = float(shot.get("speed", 1.0))
        if speed <= 0:
            raise ValueError(f"Shot {index} speed must be greater than zero")
        source_duration = duration * speed
        active_crop = project["edit"].get("active_crop")
        source_crop = f"crop={active_crop}," if active_crop else ""
        video.append(
            f"[{source_index}:v]trim=start={start:.3f}:duration={source_duration:.4f},"
            f"setpts=(PTS-STARTPTS)/{speed:.4f},"
            f"{source_crop}scale=-2:2020:flags=lanczos,crop=1080:1920:'{x}':50,fps=30,setsar=1,"
            "eq=contrast=1.085:brightness=-0.012:saturation=1.08:gamma=0.98,"
            f"unsharp=5:5:0.32:3:3:0,format=yuv420p[v{index}];"
        )
        if project["audio"].get("include_production", True):
            production.append(
                f"[{source_index}:a]atrim=start={start:.3f}:duration={source_duration:.4f},"
                f"asetpts=(PTS-STARTPTS)/{speed:.4f},"
                f"afade=t=in:st=0:d=0.02,afade=t=out:st={max(0, duration - 0.04):.4f}:d=0.04[p{index}];"
            )

    v_inputs = "".join(f"[v{i}]" for i in range(len(shots)))
    ass_escaped = str(ass_path).replace("\\", "/").replace(":", "\\:").replace("'", "\\'")
    graph = "".join(video + production)
    graph += f"{v_inputs}concat=n={len(shots)}:v=1:a=0[story];"
    if production:
        p_inputs = "".join(f"[p{i}]" for i in range(len(shots)))
        graph += f"{p_inputs}concat=n={len(shots)}:v=0:a=1[production];"
    graph += (
        "[story]vignette=PI/12,"
        "drawbox=x=48:y=78:w=984:h=2:color=white@0.28:t=fill,"
        "drawbox=x=48:y=118:w=178:h=5:color=#ff8c00@0.92:t=fill,"
        "drawbox=x=226:y=118:w=806:h=5:color=white@0.14:t=fill,"
        "drawbox=x=0:y=0:w=iw:h=ih:color=white@0.68:t=fill:enable='between(t,0,0.04)',"
        f"ass='{ass_escaped}'[video];"
    )

    extra_inputs: list[Path] = []
    bed_labels: list[str] = []
    if production:
        bed_labels.append("[film]")
        graph += f"[production]volume={project['audio'].get('production_volume', 0.28)},highpass=f=55[film];"
    graph += f"anullsrc=r={SR}:cl=stereo,atrim=duration={total:.4f}[silence];"
    bed_labels.append("[silence]")
    voice_input = len(sources)
    next_input = voice_input + 1
    for index, track in enumerate(project["audio"].get("music", [])):
        path = project_dir / track["file"]
        extra_inputs.append(path)
        timeline_start = float(track.get("timeline_start", 0.0))
        play_duration = max(0.1, total - timeline_start)
        source_start = float(track.get("source_start", 0.0))
        fade_in = min(float(track.get("fade_in", 0.4)), play_duration / 2)
        fade_out = min(float(track.get("fade_out", 0.5)), play_duration / 2)
        graph += (
            f"[{next_input}:a]atrim=start={source_start:.3f}:duration={play_duration:.4f},asetpts=PTS-STARTPTS,"
            f"afade=t=in:st=0:d={fade_in:.3f},afade=t=out:st={max(0, play_duration - fade_out):.4f}:d={fade_out:.3f},"
            f"volume={float(track.get('volume', 0.18))},adelay={round(timeline_start * 1000)}:all=1,"
            f"apad=whole_dur={total:.4f},atrim=duration={total:.4f}[m{index}];"
        )
        bed_labels.append(f"[m{index}]")
        next_input += 1

    for index, effect in enumerate(project["audio"].get("sfx", [])):
        path = project_dir / effect["file"]
        extra_inputs.append(path)
        at = float(effect.get("at", total * float(effect.get("at_fraction", 0.0))))
        graph += (
            f"[{next_input}:a]atrim=start={float(effect.get('source_start', 0))}:duration={float(effect.get('duration', 3.0))},"
            f"asetpts=PTS-STARTPTS,volume={float(effect.get('volume', 0.5))},"
            f"adelay={round(at * 1000)}:all=1,apad=whole_dur={total:.4f},atrim=duration={total:.4f}[s{index}];"
        )
        bed_labels.append(f"[s{index}]")
        next_input += 1

    graph += (
        f"{''.join(bed_labels)}amix=inputs={len(bed_labels)}:normalize=0[bed];"
        f"[{voice_input}:a]highpass=f=70,lowpass=f=15500,equalizer=f=190:t=q:w=1.2:g=-1.8,"
        "equalizer=f=3000:t=q:w=1.0:g=1.8,acompressor=threshold=0.11:ratio=2.8:attack=8:release=130:makeup=1.55,"
        "asplit=2[voice][key];[bed][key]sidechaincompress=threshold=0.025:ratio=9:attack=10:release=280[ducked];"
        "[ducked][voice]amix=inputs=2:normalize=0,loudnorm=I=-14:TP=-1.8:LRA=7[audio]"
    )
    return graph, [*sources, project_dir / "generated" / "narration.wav", *extra_inputs]


def render(project: dict, project_dir: Path, total: float, captions: Path) -> Path:
    graph, inputs = build_filter(project, project_dir, total, captions)
    graph_path = project_dir / "generated" / "filtergraph.txt"
    graph_path.write_text(graph, encoding="utf-8")
    output_dir = project_dir / "output"
    output_dir.mkdir(exist_ok=True)
    output = output_dir / project.get("output", "premium_short.mp4")
    command = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "warning"]
    for path in inputs:
        command.extend(["-i", str(path)])
    command.extend([
        "-filter_complex_script", str(graph_path), "-map", "[video]", "-map", "[audio]",
        "-c:v", "h264_nvenc", "-preset", "p6", "-tune", "hq", "-rc", "vbr", "-cq", "17",
        "-b:v", "9M", "-maxrate", "16M", "-bufsize", "24M", "-profile:v", "high", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "256k", "-ar", str(SR), "-ac", "2", "-movflags", "+faststart",
        "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
        "-t", f"{total:.4f}", str(output),
    ])
    run(command)
    return output


def qc(output: Path) -> None:
    output_dir = output.parent
    probe = run([
        "ffprobe", "-v", "error", "-show_entries",
        "format=duration,size,bit_rate:stream=codec_name,codec_type,width,height,r_frame_rate,sample_rate,channels",
        "-of", "json", str(output),
    ], capture=True)
    (output_dir / "qc_probe.json").write_text(probe.stdout, encoding="utf-8")
    loudness = subprocess.run([
        "ffmpeg", "-hide_banner", "-i", str(output), "-af",
        "loudnorm=I=-14:TP=-1.2:LRA=7:print_format=json", "-f", "null", "-",
    ], text=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True)
    match = re.search(r"\{\s*\"input_i\".*?\}", loudness.stderr, re.S)
    (output_dir / "qc_loudness.json").write_text(match.group(0) + "\n" if match else loudness.stderr, encoding="utf-8")
    run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(output),
        "-vf", "fps=1/2.3,scale=270:480,tile=4x3", "-frames:v", "1", str(output_dir / "contact_sheet.jpg"),
    ])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("project", type=Path, help="project directory containing project.json")
    parser.add_argument("--reuse-voice", action="store_true")
    args = parser.parse_args()
    project_dir = args.project.resolve()
    project = json.loads((project_dir / "project.json").read_text(encoding="utf-8"))
    duration, beats, engine = build_voice(project, project_dir, args.reuse_voice)
    total = max(float(project.get("minimum_duration", 0)), duration + float(project.get("tail_seconds", 0.38)))
    print(f"Voice engine: {engine} | narration {duration:.3f}s | master {total:.3f}s")
    captions = build_captions(project, project_dir, beats, total)
    output = render(project, project_dir, total, captions)
    qc(output)
    print(f"Finished: {output}")


if __name__ == "__main__":
    main()

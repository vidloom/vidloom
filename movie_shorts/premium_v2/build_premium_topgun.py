#!/usr/bin/env python3
"""Build the premium Vidloom Top Gun proof-of-concept.

This is deliberately a hand-authored reference edit.  The reusable ideas are the
beat map, phrase captions, moving reframes, dialogue-aware ducking, and QC pass.
The bundled movie/score assets are for the owner's private prototype only.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import re
import subprocess
import wave
from dataclasses import dataclass
from pathlib import Path

import edge_tts
import numpy as np


ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets"
GENERATED = ROOT / "generated"
VOICE_LINES = GENERATED / "voice_lines"
OUTPUT = ROOT / "output"
SOURCE = ASSETS / "topgun_source.mp4"
SCORE = ASSETS / "topgun_score.webm"
VOICE_WAV = GENERATED / "premium_voice.wav"
TIMINGS_JSON = GENERATED / "timings.json"
CAPTIONS_ASS = GENERATED / "premium_captions.ass"
FINAL = OUTPUT / "vidloom_topgun_premium_v2.mp4"

SAMPLE_RATE = 48_000
PAUSE_SECONDS = 0.085


@dataclass(frozen=True)
class VoiceBeat:
    spoken: str
    captions: tuple[str, ...]
    rate: str = "+10%"
    pitch: str = "-4Hz"


VOICE_BEATS = (
    VoiceBeat(
        "This mission was built so no fighter pilot could survive it.",
        ("BUILT TO BE", "*IMPOSSIBLE*"),
        "+8%",
        "-6Hz",
    ),
    VoiceBeat(
        "Six hundred sixty knots. Canyon walls. A target just three meters wide.",
        ("*660 KNOTS*", "CANYON WALLS", "3-METER TARGET"),
        "+14%",
        "-4Hz",
    ),
    VoiceBeat(
        "The clock: two minutes, fifteen.",
        ("THE CLOCK", "*02:15*"),
        "+5%",
        "-6Hz",
    ),
    VoiceBeat(
        "Every pilot said impossible.",
        ("EVERY PILOT SAID", "*IMPOSSIBLE*"),
        "+7%",
        "-5Hz",
    ),
    VoiceBeat(
        "So Maverick took the jet himself.",
        ("MAVERICK TOOK", "THE JET HIMSELF"),
        "+9%",
        "-5Hz",
    ),
    VoiceBeat(
        "Nine Gs. One bomb. No margin.",
        ("*NINE Gs*", "ONE BOMB", "NO MARGIN"),
        "+12%",
        "-4Hz",
    ),
    VoiceBeat(
        "He hit the target...",
        ("HE HIT", "THE TARGET"),
        "+2%",
        "-7Hz",
    ),
    VoiceBeat(
        "then stopped the clock with one second left.",
        ("ONE SECOND", "*LEFT*"),
        "+5%",
        "-5Hz",
    ),
    VoiceBeat(
        "That's not flying.",
        ("THAT'S NOT", "FLYING"),
        "+0%",
        "-7Hz",
    ),
    VoiceBeat(
        "That's rewriting the limit.",
        ("HE REWROTE", "*THE LIMIT*"),
        "+0%",
        "-8Hz",
    ),
)


# source start, relative duration weight, start crop center, end crop center
# Short, contrasting shots make the story legible even with the sound muted.
CUTS = (
    (136.55, 0.66, 0.50, 0.50),  # cold-open impact
    (16.00, 0.86, 0.55, 0.56),   # resolve
    (2.50, 1.04, 0.34, 0.39),    # terrain model
    (32.50, 1.00, 0.50, 0.54),   # launch
    (50.00, 1.05, 0.48, 0.52),   # cockpit
    (64.00, 1.02, 0.52, 0.46),   # knife edge
    (92.00, 0.82, 0.58, 0.54),   # room reaction
    (70.00, 1.04, 0.50, 0.56),   # canyon
    (110.00, 0.96, 0.50, 0.50),  # popup
    (114.00, 0.76, 0.56, 0.52),  # disbelief
    (116.50, 1.06, 0.50, 0.50),  # dive
    (124.00, 0.86, 0.48, 0.55),  # external jet
    (130.00, 0.92, 0.56, 0.53),  # G force
    (132.00, 0.88, 0.50, 0.46),  # inverted dive
    (136.50, 1.10, 0.50, 0.50),  # weapon release
    (140.00, 0.86, 0.48, 0.52),  # target
    (146.00, 1.00, 0.50, 0.55),  # blast
    (150.00, 0.78, 0.52, 0.50),  # reaction
    (159.50, 0.92, 0.50, 0.50),  # clock / face
    (161.00, 1.18, 0.50, 0.50),  # jet clears frame into open sky: visual release
)


def run(command: list[str], *, capture: bool = False) -> subprocess.CompletedProcess:
    print("+", " ".join(command[:8]), "..." if len(command) > 8 else "")
    return subprocess.run(
        command,
        check=True,
        text=capture,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )


def decode_f32(path: Path) -> np.ndarray:
    result = subprocess.run(
        [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(path),
            "-ar", str(SAMPLE_RATE), "-ac", "1", "-f", "f32le", "pipe:1",
        ],
        check=True,
        stdout=subprocess.PIPE,
    )
    return np.frombuffer(result.stdout, dtype=np.float32).copy()


def trim_bounds(samples: np.ndarray) -> tuple[int, int]:
    window = max(1, int(SAMPLE_RATE * 0.01))
    usable = len(samples) - (len(samples) % window)
    rms = np.sqrt(np.mean(samples[:usable].reshape(-1, window) ** 2, axis=1) + 1e-12)
    active = np.flatnonzero(rms > 0.003)
    if not len(active):
        return 0, len(samples)
    pad = int(SAMPLE_RATE * 0.025)
    start = max(0, int(active[0] * window) - pad)
    end = min(len(samples), int((active[-1] + 1) * window) + pad)
    return start, end


async def synthesize_line(index: int, beat: VoiceBeat) -> dict:
    mp3_path = VOICE_LINES / f"{index:02d}.mp3"
    communicator = edge_tts.Communicate(
        beat.spoken,
        voice="en-US-BrianMultilingualNeural",
        rate=beat.rate,
        pitch=beat.pitch,
        volume="+0%",
        boundary="WordBoundary",
    )
    audio = bytearray()
    words: list[dict] = []
    async for chunk in communicator.stream():
        if chunk["type"] == "audio":
            audio.extend(chunk["data"])
        elif chunk["type"] == "WordBoundary":
            start = chunk["offset"] / 10_000_000
            duration = chunk["duration"] / 10_000_000
            words.append({"text": chunk["text"], "start": start, "end": start + duration})
    mp3_path.write_bytes(audio)
    return {"path": mp3_path, "words": words}


async def synthesize_all() -> list[dict]:
    results: list[dict] = []
    # Sequential calls are intentional: this avoids Edge's burst throttling and
    # keeps the same neural voice/prosody from drifting across simultaneous jobs.
    for index, beat in enumerate(VOICE_BEATS, start=1):
        print(f"Synthesizing beat {index}/{len(VOICE_BEATS)}")
        results.append(await synthesize_line(index, beat))
    return results


def build_voice(reuse: bool) -> tuple[float, list[dict]]:
    if reuse and VOICE_WAV.exists() and TIMINGS_JSON.exists():
        payload = json.loads(TIMINGS_JSON.read_text(encoding="utf-8"))
        return float(payload["duration"]), payload["lines"]

    raw_lines = asyncio.run(synthesize_all())
    assembled: list[np.ndarray] = []
    timing_lines: list[dict] = []
    cursor = 0.0

    for index, (beat, raw) in enumerate(zip(VOICE_BEATS, raw_lines, strict=True)):
        samples = decode_f32(raw["path"])
        trim_start, trim_end = trim_bounds(samples)
        clipped = samples[trim_start:trim_end]
        line_start = cursor
        line_duration = len(clipped) / SAMPLE_RATE
        line_end = line_start + line_duration
        trim_seconds = trim_start / SAMPLE_RATE
        words = [
            {
                "text": item["text"],
                "start": max(line_start, line_start + item["start"] - trim_seconds),
                "end": min(line_end, line_start + item["end"] - trim_seconds),
            }
            for item in raw["words"]
        ]
        timing_lines.append(
            {
                "spoken": beat.spoken,
                "captions": list(beat.captions),
                "start": round(line_start, 4),
                "end": round(line_end, 4),
                "words": words,
            }
        )
        assembled.append(clipped)
        cursor = line_end
        if index < len(VOICE_BEATS) - 1:
            assembled.append(np.zeros(int(SAMPLE_RATE * PAUSE_SECONDS), dtype=np.float32))
            cursor += PAUSE_SECONDS

    voice = np.concatenate(assembled)
    # Gentle clip protection here; final loudness is handled after the full mix.
    peak = float(np.max(np.abs(voice))) or 1.0
    voice *= min(1.0, 0.92 / peak)
    pcm = np.clip(voice * 32767.0, -32768, 32767).astype(np.int16)
    with wave.open(str(VOICE_WAV), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(SAMPLE_RATE)
        output.writeframes(pcm.tobytes())

    payload = {"duration": len(voice) / SAMPLE_RATE, "lines": timing_lines}
    TIMINGS_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return float(payload["duration"]), timing_lines


def ass_time(seconds: float) -> str:
    centiseconds = max(0, int(round(seconds * 100)))
    hours, remainder = divmod(centiseconds, 360_000)
    minutes, remainder = divmod(remainder, 6_000)
    secs, cs = divmod(remainder, 100)
    return f"{hours}:{minutes:02d}:{secs:02d}.{cs:02d}"


def caption_text(text: str) -> str:
    # ASS colours are BGR. Cyan is the brand signal; warm yellow is reserved for
    # the active proof/payoff words.
    text = re.sub(
        r"\*(.+?)\*",
        lambda match: "{\\c&H006FFF&\\blur0.5}" + match.group(1) + "{\\c&HFFFFFF&}",
        text,
    )
    return text


def build_captions(lines: list[dict], total: float) -> None:
    events: list[str] = []
    for line_index, line in enumerate(lines):
        captions = line["captions"]
        start = float(line["start"])
        end = float(line["end"])
        weights = [max(1, len(re.sub(r"[^A-Za-z0-9 ]", "", item).split())) for item in captions]
        weight_total = sum(weights)
        cursor = start
        for phrase_index, (phrase, weight) in enumerate(zip(captions, weights, strict=True)):
            phrase_end = end if phrase_index == len(captions) - 1 else cursor + (end - start) * weight / weight_total
            size = 116 if line_index == 0 or any(char.isdigit() for char in phrase) else 96
            y = 1390 if line_index == 0 else 1420
            tags = (
                f"{{\\an5\\pos(540,{y})\\fs{size}\\fscx88\\fscy88"
                "\\t(0,95,\\fscx105\\fscy105)\\t(95,220,\\fscx100\\fscy100)"
                "\\fad(35,55)\\blur0.35}"
            )
            rendered = caption_text(phrase)
            events.append(
                f"Dialogue: 10,{ass_time(cursor)},{ass_time(phrase_end)},Caption,,0,0,0,,{tags}{rendered}"
            )
            cursor = phrase_end

    # Small editorial devices: information, not decoration.
    events.extend(
        [
            f"Dialogue: 5,{ass_time(0.00)},{ass_time(total)},HUD,,0,0,0,,{{\\an7\\pos(58,94)}}VIDLOOM  /  FLIGHT FILE 014",
            f"Dialogue: 5,{ass_time(0.00)},{ass_time(total)},HUDRight,,0,0,0,,{{\\an9\\pos(1020,94)}}MISSION CLOCK  /  02:15",
        ]
    )

    header = """[Script Info]
Title: Vidloom Premium Reference Edit
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Caption,Montserrat ExtraBold,96,&H00FFFFFF,&H00006FFF,&H000A0A0A,&H70000000,-1,0,0,0,100,100,0.4,0,1,8,2,5,80,80,360,1
Style: HUD,JetBrains Mono SemiBold,25,&H00FFF4DE,&H00000000,&H70000000,&H00000000,-1,0,0,0,100,100,1.1,0,1,2,0,7,50,50,90,1
Style: HUDRight,JetBrains Mono Medium,23,&H009BEAFF,&H00000000,&H70000000,&H00000000,-1,0,0,0,100,100,1.0,0,1,2,0,9,50,50,90,1
Style: ColdOpen,Montserrat Black,66,&H00FFFFFF,&H00000000,&H00202020,&H00000000,-1,0,0,0,100,100,1.0,0,1,7,2,5,70,70,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    CAPTIONS_ASS.write_text(header + "\n".join(events) + "\n", encoding="utf-8")


def build_filter(total: float) -> str:
    weight_total = sum(cut[1] for cut in CUTS)
    durations = [total * cut[1] / weight_total for cut in CUTS]
    video_chains: list[str] = []
    audio_chains: list[str] = []

    for index, ((source_start, _, cx_start, cx_end), duration) in enumerate(zip(CUTS, durations, strict=True)):
        delta = cx_end - cx_start
        x_expr = f"(in_w-1080)*({cx_start:.4f}+({delta:.4f})*t/{duration:.4f})"
        video_chains.append(
            f"[0:v]trim=start={source_start:.3f}:duration={duration:.4f},setpts=PTS-STARTPTS,"
            f"scale=-2:2020:flags=lanczos,crop=1080:1920:'{x_expr}':50,"
            "fps=30,setsar=1,eq=contrast=1.075:brightness=-0.008:saturation=1.10:gamma=0.98,"
            f"unsharp=5:5:0.35:3:3:0.0,format=yuv420p[v{index}];"
        )
        audio_chains.append(
            f"[0:a]atrim=start={source_start:.3f}:duration={duration:.4f},asetpts=PTS-STARTPTS,"
            f"afade=t=in:st=0:d=0.025,afade=t=out:st={max(0.0, duration - 0.04):.4f}:d=0.04[a{index}];"
        )

    video_inputs = "".join(f"[v{i}]" for i in range(len(CUTS)))
    audio_inputs = "".join(f"[a{i}]" for i in range(len(CUTS)))
    ass_path = str(CAPTIONS_ASS).replace("\\", "/").replace(":", "\\:").replace("'", "\\'")

    finish = (
        f"{video_inputs}concat=n={len(CUTS)}:v=1:a=0[story];"
        f"{audio_inputs}concat=n={len(CUTS)}:v=0:a=1[production];"
        "[story]vignette=PI/11,"
        "drawbox=x=48:y=78:w=984:h=2:color=white@0.32:t=fill,"
        "drawbox=x=48:y=118:w=210:h=5:color=#ff6f00@0.95:t=fill,"
        "drawbox=x=258:y=118:w=774:h=5:color=white@0.16:t=fill,"
        "drawbox=x=0:y=0:w=iw:h=ih:color=white@0.70:t=fill:enable='between(t,0,0.045)',"
        f"ass='{ass_path}'[video];"
        f"[2:a]atrim=start=35.0:duration={total:.4f},asetpts=PTS-STARTPTS,"
        f"afade=t=in:st=0:d=0.35,afade=t=out:st={max(0.0, total - 0.45):.4f}:d=0.45,volume=0.23[score];"
        "[production]volume=0.24,highpass=f=70[film];"
        "[film][score]amix=inputs=2:weights='1 1':normalize=0[bed];"
        "[1:a]highpass=f=72,lowpass=f=15500,equalizer=f=190:t=q:w=1.2:g=-2.2,"
        "equalizer=f=3200:t=q:w=1.0:g=2.2,acompressor=threshold=0.10:ratio=3.0:attack=8:release=120:makeup=1.65,"
        "asplit=2[voice_main][voice_key];"
        "[bed][voice_key]sidechaincompress=threshold=0.025:ratio=8:attack=12:release=260:makeup=1[ducked];"
        "[ducked][voice_main]amix=inputs=2:weights='1 1':normalize=0,"
        "loudnorm=I=-14.0:TP=-1.2:LRA=7.0[audio]"
    )
    return "".join(video_chains + audio_chains) + finish


def render(total: float) -> None:
    filtergraph = build_filter(total)
    filter_file = GENERATED / "filtergraph.txt"
    filter_file.write_text(filtergraph, encoding="utf-8")

    command = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "warning",
        "-i", str(SOURCE), "-i", str(VOICE_WAV), "-i", str(SCORE),
        "-filter_complex_script", str(filter_file),
        "-map", "[video]", "-map", "[audio]",
        "-c:v", "h264_nvenc", "-preset", "p6", "-tune", "hq",
        "-rc", "vbr", "-cq", "17", "-b:v", "9M", "-maxrate", "16M", "-bufsize", "24M",
        "-profile:v", "high", "-level", "4.2", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "256k", "-ar", str(SAMPLE_RATE), "-ac", "2",
        "-movflags", "+faststart", "-colorspace", "bt709", "-color_primaries", "bt709",
        "-color_trc", "bt709", "-t", f"{total:.4f}", str(FINAL),
    ]
    try:
        run(command)
    except subprocess.CalledProcessError:
        print("NVENC failed; retrying with the software OpenH264 encoder.")
        software = command.copy()
        start = software.index("-c:v")
        end = software.index("-c:a")
        software[start:end] = ["-c:v", "libopenh264", "-b:v", "9M", "-maxrate", "16M", "-bufsize", "24M", "-pix_fmt", "yuv420p"]
        run(software)


def qc() -> None:
    probe = run(
        [
            "ffprobe", "-v", "error", "-show_entries",
            "format=duration,size,bit_rate:stream=codec_name,codec_type,width,height,r_frame_rate,sample_rate,channels",
            "-of", "json", str(FINAL),
        ],
        capture=True,
    )
    (OUTPUT / "qc_probe.json").write_text(probe.stdout, encoding="utf-8")
    loudness = subprocess.run(
        [
            "ffmpeg", "-hide_banner", "-i", str(FINAL),
            "-af", "loudnorm=I=-14:TP=-1.2:LRA=7:print_format=json", "-f", "null", "-",
        ],
        text=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        check=True,
    )
    match = re.search(r"\{\s*\"input_i\".*?\}", loudness.stderr, re.S)
    (OUTPUT / "qc_loudness.json").write_text(match.group(0) + "\n" if match else loudness.stderr, encoding="utf-8")
    run(
        [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(FINAL),
            "-vf", "fps=1/2.15,scale=270:480,tile=4x3", "-frames:v", "1",
            str(OUTPUT / "contact_sheet.jpg"),
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reuse-voice", action="store_true", help="reuse generated voice and timing data")
    parser.add_argument("--skip-render", action="store_true", help="only create voice, timing, and caption assets")
    args = parser.parse_args()

    for directory in (GENERATED, VOICE_LINES, OUTPUT):
        directory.mkdir(parents=True, exist_ok=True)
    for required in (SOURCE, SCORE):
        if not required.exists():
            raise FileNotFoundError(f"Missing required private prototype asset: {required}")

    voice_duration, timings = build_voice(args.reuse_voice)
    total_duration = max(voice_duration + 0.34, 20.0)
    print(f"Voice: {voice_duration:.3f}s | master: {total_duration:.3f}s")
    build_captions(timings, total_duration)
    if not args.skip_render:
        render(total_duration)
        qc()
        print(f"\nFinished: {FINAL}")


if __name__ == "__main__":
    main()

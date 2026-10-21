import subprocess
import os
import random
from pathlib import Path
from typing import Optional, List, Dict
from config.settings import (
    BASE_DIR,
    TEMP_DIR,
    FINAL_DIR,
    BACKGROUNDS_DIR,
    MUSIC_DIR,
    SFX_DIR,
    VIDEO_WIDTH,
    VIDEO_HEIGHT,
    VIDEO_FPS
)
from core.pexels import download_pexels_video, extract_search_query

def segment_words_into_scenes(words_data: List[Dict], total_duration: float, max_scene_duration: float = 3.2) -> List[Dict]:
    """
    Splits narration words into high-engagement visual scenes lasting 2.2s - 3.4s each.
    Breaks on sentences, clauses, or when a scene exceeds max_scene_duration.
    """
    if not words_data:
        return []

    scenes = []
    current_words = []
    scene_start = words_data[0]["start"]

    for item in words_data:
        current_words.append(item)
        word_text = item["word"]
        current_dur = item["end"] - scene_start

        # Break conditions:
        # 1. Major punctuation (., !, ?)
        is_sentence_end = any(word_text.endswith(p) for p in ('.', '!', '?', ';'))
        # 2. Clause break (comma) after at least 2.0 seconds
        is_clause_break = word_text.endswith(',') and current_dur >= 2.0
        # 3. Time threshold exceeded (max 3.2s)
        is_time_limit = current_dur >= max_scene_duration

        if is_sentence_end or is_clause_break or is_time_limit:
            scenes.append({
                "text": " ".join(w["word"] for w in current_words),
                "start": scene_start,
                "end": item["end"]
            })
            current_words = []
            scene_start = item["end"]

    if current_words:
        scenes.append({
            "text": " ".join(w["word"] for w in current_words),
            "start": scene_start,
            "end": words_data[-1]["end"]
        })

    # Seamless alignment with zero dead air gaps:
    scenes[0]["start"] = 0.0
    for i in range(len(scenes) - 1):
        next_start = scenes[i+1]["start"]
        scenes[i]["duration"] = round(next_start - scenes[i]["start"], 3)

    scenes[-1]["duration"] = round(max(0.5, total_duration - scenes[-1]["start"]), 3)

    # Filter out tiny trailing glitches (< 0.6s) by merging into previous scene
    if len(scenes) > 1 and scenes[-1]["duration"] < 0.7:
        trailing = scenes.pop()
        scenes[-1]["duration"] = round(scenes[-1]["duration"] + trailing["duration"], 3)
        scenes[-1]["text"] += " " + trailing["text"]

    return scenes

def render_multi_scene_video(
    words_data: List[Dict],
    audio_path: Path,
    subtitles_path: Path,
    duration: float,
    reddit_card_path: Optional[Path] = None,
    context_theme: str = "",
    output_path: Optional[Path] = None
) -> Path:
    """
    Assembles a god-level vertical video (9:16) with:
    1. Fast visual pacing: Scene cuts every 2.2s - 3.4s.
    2. Dynamic punch-cuts: Alternating zoom scales (100% vs 108% zoom punch).
    3. Context-anchored B-roll: 100% relevant footage matching video domain.
    4. Cinematic grading: Contrast curve + edge vignette.
    5. Smooth Reddit card hook: Fades out smoothly into the video.
    6. Audio mixing: Ducked suspense BGM (-22dB) + hook impact + whoosh on cuts.
    7. Burned-in ASS subtitles with active neon highlights.
    """
    out_video = output_path or (FINAL_DIR / "final_short.mp4")
    scenes = segment_words_into_scenes(words_data, duration, max_scene_duration=3.2)
    
    if not scenes:
        raise RuntimeError("No scene data provided for video rendering.")
        
    print(f"[VideoEngine] Assembling {len(scenes)} high-retention scenes (Theme: '{context_theme}')...")

    # 1. Render scenes with alternating punch-zoom & cinematic grading
    segment_files = []
    
    for idx, s in enumerate(scenes):
        query = extract_search_query(s["text"], context_theme=context_theme)
        seg_dur = s["duration"]
        
        # Alternate between standard scale and 108% punch-in zoom for dynamic rhythm
        is_punch_zoom = (idx % 2 == 1)
        punch_w = int(VIDEO_WIDTH * 1.08)
        punch_h = int(VIDEO_HEIGHT * 1.08)
        
        if is_punch_zoom:
            vf_scale = f"scale={punch_w}:{punch_h}:force_original_aspect_ratio=increase,crop={VIDEO_WIDTH}:{VIDEO_HEIGHT}"
            zoom_tag = " [108% PUNCH]"
        else:
            vf_scale = f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=increase,crop={VIDEO_WIDTH}:{VIDEO_HEIGHT}"
            zoom_tag = ""

        is_promo = any(k in context_theme.lower() for k in ["handbag", "fashion", "luxury", "promo"])
        if is_promo:
            vf_grade = (
                f"{vf_scale},"
                f"fps={VIDEO_FPS},"
                f"eq=contrast=1.08:brightness=0.04:saturation=1.22"
            )
        else:
            vf_grade = (
                f"{vf_scale},"
                f"fps={VIDEO_FPS},"
                f"eq=contrast=1.12:brightness=-0.06:saturation=1.1,"
                f"vignette=PI/4"
            )

        print(f"  -> Scene {idx+1}/{len(scenes)} ({seg_dur:.1f}s){zoom_tag}: \"{s['text'][:32]}...\" | Query: '{query}'")
        
        bg_clip = download_pexels_video(query=query, context_theme=context_theme)
        seg_output = TEMP_DIR / f"scene_{idx}.mp4"
        
        cmd_cut = [
            "ffmpeg", "-y",
            "-stream_loop", "-1",
            "-i", str(bg_clip),
            "-t", f"{seg_dur:.3f}",
            "-vf", vf_grade,
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-pix_fmt", "yuv420p",
            "-an",
            str(seg_output)
        ]
        res = subprocess.run(cmd_cut, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res.returncode != 0:
            print(f"[VideoEngine] Error rendering scene {idx}:", res.stderr[-400:])
            raise RuntimeError(f"FFmpeg failed rendering scene {idx}")
            
        segment_files.append(seg_output)

    # 2. Write concat manifest
    concat_manifest = TEMP_DIR / "scenes_concat.txt"
    with open(concat_manifest, "w", encoding="utf-8") as f:
        for seg in segment_files:
            safe_path = seg.resolve().as_posix().replace("'", r"'\''")
            f.write(f"file '{safe_path}'\n")

    # 3. Format subtitles path for Windows FFmpeg
    try:
        rel_sub = subtitles_path.relative_to(BASE_DIR).as_posix()
    except ValueError:
        rel_sub = subtitles_path.as_posix()
    escaped_sub = rel_sub.replace(":", r"\:").replace("'", r"\'")

    # 4. Check available BGM and SFX
    is_promo = any(k in context_theme.lower() for k in ["handbag", "fashion", "luxury", "promo"])
    if is_promo and (MUSIC_DIR / "upbeat_promo_bgm.mp3").exists():
        bgm_file = MUSIC_DIR / "upbeat_promo_bgm.mp3"
        bgm_vol = 0.12
    else:
        bgm_file = MUSIC_DIR / "suspense_bgm.mp3"
        bgm_vol = 0.08

    whoosh_file = SFX_DIR / "whoosh.mp3"
    impact_file = SFX_DIR / "impact.mp3"

    has_bgm = bgm_file.exists()
    has_whoosh = whoosh_file.exists()
    has_impact = impact_file.exists()

    cmd_final = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_manifest),
        "-i", str(audio_path)
    ]

    input_index = 2
    bgm_idx = None
    whoosh_idx = None
    impact_idx = None

    if has_bgm:
        cmd_final.extend(["-stream_loop", "-1", "-i", str(bgm_file)])
        bgm_idx = input_index
        input_index += 1

    if has_whoosh:
        cmd_final.extend(["-i", str(whoosh_file)])
        whoosh_idx = input_index
        input_index += 1

    if has_impact:
        cmd_final.extend(["-i", str(impact_file)])
        impact_idx = input_index
        input_index += 1

    has_card = reddit_card_path is not None and reddit_card_path.exists()
    card_idx = None
    if has_card:
        cmd_final.extend(["-i", str(reddit_card_path)])
        card_idx = input_index
        input_index += 1

    # 5. Construct Audio Filter Complex
    filter_parts = []
    audio_mix_inputs = []

    # Voiceover (100% volume, center channel)
    filter_parts.append("[1:a]volume=1.0[voice]")
    audio_mix_inputs.append("[voice]")

    # BGM with gentle fade in/out
    if bgm_idx is not None:
        fade_out_start = max(1.0, duration - 1.5)
        filter_parts.append(
            f"[{bgm_idx}:a]volume={bgm_vol},afade=t=in:ss=0:d=1.0,afade=t=out:st={fade_out_start:.2f}:d=1.5[bgm]"
        )
        audio_mix_inputs.append("[bgm]")

    # Hook impact hit at t=0
    if impact_idx is not None:
        impact_vol = 0.25 if is_promo else 0.35
        filter_parts.append(f"[{impact_idx}:a]volume={impact_vol}[impact]")
        audio_mix_inputs.append("[impact]")

    # Whoosh at every scene transition
    num_transitions = len(scenes) - 1
    whoosh_vol = 0.25 if is_promo else 0.35
    if whoosh_idx is not None and num_transitions > 0:
        if num_transitions == 1:
            t_ms = int(scenes[1]["start"] * 1000)
            filter_parts.append(f"[{whoosh_idx}:a]adelay={t_ms}|{t_ms},volume={whoosh_vol}[s0]")
            audio_mix_inputs.append("[s0]")
        else:
            split_labels = "".join([f"[w{j}]" for j in range(num_transitions)])
            filter_parts.append(f"[{whoosh_idx}:a]asplit={num_transitions}{split_labels}")
            for j in range(num_transitions):
                t_ms = int(scenes[j+1]["start"] * 1000)
                filter_parts.append(f"[w{j}]adelay={t_ms}|{t_ms},volume={whoosh_vol}[s{j}]")
                audio_mix_inputs.append(f"[s{j}]")

    # Combine all audio streams
    mix_line = "".join(audio_mix_inputs) + f"amix=inputs={len(audio_mix_inputs)}:normalize=0[aout]"
    filter_parts.append(mix_line)

    # 6. Video Filter: Smooth Reddit Card Fade-Out + Subtitles burn
    hook_dur = min(4.0, max(2.5, scenes[0]["duration"]))
    if has_card:
        fade_dur = 0.4
        fade_start = max(0.1, hook_dur - fade_dur)
        # Smooth alpha fade-out on the card
        filter_parts.append(f"[{card_idx}:v]fade=t=out:st={fade_start:.2f}:d={fade_dur:.2f}:alpha=1[fcard]")
        filter_parts.append(
            f"[0:v][fcard]overlay=(main_w-overlay_w)/2:(main_h-overlay_h)/2-140:enable='between(t,0,{hook_dur:.2f})':format=auto[vcard]"
        )
        filter_parts.append(f"[vcard]subtitles='{escaped_sub}'[vout]")
    else:
        filter_parts.append(f"[0:v]subtitles='{escaped_sub}'[vout]")

    full_filter = ";".join(filter_parts)

    cmd_final.extend([
        "-filter_complex", full_filter,
        "-map", "[vout]",
        "-map", "[aout]",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "20",
        "-c:a", "aac",
        "-b:a", "192k",
        "-t", f"{duration:.2f}",
        "-pix_fmt", "yuv420p",
        str(out_video)
    ])

    print(f"[VideoEngine] Stitching scenes, mixing multi-track audio & burning captions...")
    res_final = subprocess.run(cmd_final, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res_final.returncode != 0:
        print("[VideoEngine] Final stitch error:", res_final.stderr[-800:])
        raise RuntimeError(f"FFmpeg final assembly failed with exit code {res_final.returncode}")

    print(f"[VideoEngine] God-level render complete: {out_video}")
    return out_video

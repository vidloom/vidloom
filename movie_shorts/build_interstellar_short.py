import subprocess
import numpy as np
import wave
import os

def load_audio_resampled(path, target_sr=44100):
    cmd = ['ffmpeg', '-y', '-i', path, '-ar', str(target_sr), '-ac', '1', '-f', 'wav', 'pipe:1']
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=True)
    raw = res.stdout[44:]
    samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    return samples

def mix_master_audio(total_duration=24.5, sr=44100):
    total_samples = int(total_duration * sr)
    master = np.zeros(total_samples, dtype=np.float32)

    # 1. Load Natural Tight Voiceover (18.23s, 1.0x normal human pace)
    vox = load_audio_resampled('scratch/epic_story_tight.wav', sr)

    # 2. Hans Zimmer - No Time For Caution OST
    zimmer_raw = load_audio_resampled('scratch/no_time_caution.webm', sr)
    # The climax organ drop happens at 26.0s in Zimmer's track.
    # We want it to hit right at 21.5s when the mechanical clamp locks!
    start_offset = int(sr * 4.5)
    zimmer = zimmer_raw[start_offset:start_offset + total_samples]
    if len(zimmer) < total_samples:
        zimmer = np.pad(zimmer, (0, total_samples - len(zimmer)))

    # Dynamic volume envelope:
    # 38% volume while narrator speaks (driving organ rhythm and tension build)
    # Swells to 92% at 21.0s to 21.5s when the docking mechanism locks!
    t = np.linspace(0, total_duration, total_samples)
    music_vol = np.where(t < 21.0, 0.38, 0.38 + 0.54 * np.clip((t - 21.0) / 1.0, 0, 1))

    # 3. Authentic metallic clamp impact sound at 21.5s
    metal_sfx = load_audio_resampled('scratch/metal_lock.wav', sr)

    # Master assembly
    master += zimmer * music_vol
    
    # Voiceover overlay at dominant volume (1.35x)
    vox_len = min(len(vox), total_samples)
    master[:vox_len] += vox[:vox_len] * 1.35

    # Add metallic dock impact right at the 21.5s climax
    metal_start = int(21.5 * sr)
    metal_len = min(len(metal_sfx), total_samples - metal_start)
    if metal_len > 0:
        master[metal_start:metal_start + metal_len] += metal_sfx[:metal_len] * 0.90

    # Peak limiter
    peak = np.max(np.abs(master))
    if peak > 0.95:
        master = master * (0.95 / peak)

    int_samples = (master * 32767).astype(np.int16)
    with wave.open('scratch/epic_master_audio.wav', 'w') as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sr)
        f.writeframes(int_samples.tobytes())
    print("Mixed master audio with authentic score and natural voice!")

def generate_captions():
    ass = """[Script Info]
Title: Interstellar Master Short
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: None
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: YellowHook,Liberation Sans,70,&H0000E5FF,&H000000FF,&H00000000,&H80000000,1,0,0,0,105,105,1,0,1,8,0,2,40,40,360,1
Style: WhiteBold,Liberation Sans,68,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,1,0,0,0,100,100,1,0,1,7,0,2,40,40,360,1
Style: RedImpact,Liberation Sans,72,&H00303BFF,&H000000FF,&H00000000,&H80000000,1,0,0,0,108,108,1,0,1,8,0,2,40,40,360,1
Style: CyanClimax,Liberation Sans,74,&H00FFFF00,&H000000FF,&H00000000,&H80000000,1,0,0,0,110,110,2,0,1,9,0,2,40,40,360,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:02.80,RedImpact,,0,0,0,,WHEN THE AIRLOCK EXPLODED,
Dialogue: 0,0:00:02.80,0:00:04.60,WhiteBold,,0,0,0,,HUMANITY'S LAST HOPE
Dialogue: 0,0:00:04.60,0:00:06.20,YellowHook,,0,0,0,,BEGAN SPINNING AT 68 RPM!
Dialogue: 0,0:00:06.20,0:00:07.80,RedImpact,,0,0,0,,INTO A DEATH DIVE.
Dialogue: 0,0:00:07.80,0:00:10.20,WhiteBold,,0,0,0,,HIS CREW SCREAMED IT WAS IMPOSSIBLE!
Dialogue: 0,0:00:10.20,0:00:11.70,WhiteBold,,0,0,0,,COOPER HAD ONLY ONE ANSWER:
Dialogue: 0,0:00:11.70,0:00:13.20,YellowHook,,0,0,0,,\"IT'S NECESSARY.\"
Dialogue: 0,0:00:13.20,0:00:15.20,RedImpact,,0,0,0,,HE FIRED EVERY THRUSTER,
Dialogue: 0,0:00:15.20,0:00:16.80,YellowHook,,0,0,0,,MATCHED THE FATAL ROTATION,
Dialogue: 0,0:00:16.80,0:00:18.50,RedImpact,,0,0,0,,AND FOUGHT BLACKOUT G-FORCES...
Dialogue: 0,0:00:18.50,0:00:20.00,WhiteBold,,0,0,0,,PULLING OFF THE GREATEST MANEUVER
Dialogue: 0,0:00:20.00,0:00:21.50,YellowHook,,0,0,0,,IN CINEMATIC HISTORY.
Dialogue: 0,0:00:21.50,0:00:24.50,CyanClimax,,0,0,0,,LOCK ACHIEVED.
"""
    with open('scratch/epic_captions.ass', 'w', encoding='utf-8') as f:
        f.write(ass)
    print("Generated epic captions ASS file!")

def render():
    mix_master_audio(total_duration=24.5)
    generate_captions()

    cuts = [
        # (start_ss, duration, crop_x_pct)
        # 1. Catastrophic explosion (0.0s - 2.8s)
        (83.0, 2.8, 0.50),
        # 2. Wide aerial spinning ring in orbit against ice planet (2.8s - 7.8s)
        (92.5, 5.0, 0.75),
        # 3. Brand terrified in helmet shouting (7.8s - 10.2s)
        (127.8, 2.4, 0.48),
        # 4. Cooper looking up at spinning station with high contrast cockpit light (10.2s - 11.7s)
        (180.0, 1.5, 0.50),
        # 5. Cooper close-up determination, sweating, steely gaze (11.7s - 13.2s)
        (198.5, 1.5, 0.42),
        # 6. RCS thruster plumes firing violent gas jets into space (13.2s - 15.2s)
        (271.5, 2.0, 0.58),
        # 7. Exterior Ranger spinning on axis matching 68 RPM (15.2s - 16.8s)
        (260.0, 1.6, 0.50),
        # 8. Violent blackout G-forces shaking cockpit (16.8s - 18.5s)
        (282.0, 1.7, 0.45),
        # 9. Ranger nose slides into spinning dock tunnel (18.5s - 21.5s)
        (310.0, 3.0, 0.50),
        # 10. Mechanical dock clamp locks into place + organ climax (21.5s - 24.5s)
        (296.5, 3.0, 0.50),
    ]

    filter_chains = []
    for idx, (ss, dur, cx) in enumerate(cuts):
        v_name = f"v{idx}"
        chain = (
            f"[0:v]trim=start={ss}:duration={dur},setpts=PTS-STARTPTS,"
            f"scale=-1:1920,crop=1080:1920:(in_w-1080)*{cx}:0,"
            f"eq=contrast=1.18:brightness=0.02:saturation=1.25[{v_name}];"
        )
        filter_chains.append(chain)

    concat_inputs = "".join([f"[v{i}]" for i in range(len(cuts))])
    concat_filter = f"{concat_inputs}concat=n={len(cuts)}:v=1:a=0[v_concat];"

    final_v_chain = (
        "[v_concat]"
        "drawbox=x=0:y=180:w=1080:h=90:color=black@0.7:t=fill,"
        "drawtext=text='INTERSTELLAR':font='Liberation Sans':fontsize=32:fontcolor=white:x=(w-text_w)/2:y=208,"
        "drawtext=text='THE IMPOSSIBLE DOCKING':font='Liberation Sans':fontsize=20:fontcolor=#00E5FF:x=(w-text_w)/2:y=188,"
        "ass=scratch/epic_captions.ass[out_v]"
    )

    full_filter = "".join(filter_chains) + concat_filter + final_v_chain

    cmd = [
        'ffmpeg', '-y',
        '-i', 'scratch/paramount_docking_full.mkv',
        '-i', 'scratch/epic_master_audio.wav',
        '-filter_complex', full_filter,
        '-map', '[out_v]',
        '-map', '1:a',
        '-c:v', 'libopenh264',
        '-b:v', '5.5M',
        '-c:a', 'aac',
        '-b:a', '192k',
        '-t', '24.5',
        'scratch/interstellar_epic_short.mp4'
    ]

    print("Rendering 24.5s epic short from 7-min movie master...")
    subprocess.run(cmd, check=True)
    print("Render finished successfully!")

if __name__ == '__main__':
    render()

import subprocess
import os

def generate_captions():
    ass_path = '/home/omie/.gemini/antigravity-ide/brain/990f0144-ba21-4d53-8f8f-b6b54be76818/scratch/topgun_captions.ass'
    ass_content = """[Script Info]
Title: Top Gun Maverick Canyon Short
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
Style: CyanClimax,Liberation Sans,76,&H00FFFF00,&H000000FF,&H00000000,&H80000000,1,0,0,0,110,110,2,0,1,9,0,2,40,40,360,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:01.10,RedImpact,,0,0,0,,THE NAVY SAID
Dialogue: 0,0:00:01.10,0:00:02.26,YellowHook,,0,0,0,,THE MISSION WAS SUICIDE.
Dialogue: 0,0:00:02.26,0:00:04.30,WhiteBold,,0,0,0,,FLY AN F-18 AT 660 KNOTS
Dialogue: 0,0:00:04.30,0:00:06.54,YellowHook,,0,0,0,,THROUGH A WINDING CANYON...
Dialogue: 0,0:00:06.54,0:00:08.50,WhiteBold,,0,0,0,,HIT A 3-METER TARGET
Dialogue: 0,0:00:08.50,0:00:10.58,RedImpact,,0,0,0,,IN UNDER 2 MIN 15 SEC.
Dialogue: 0,0:00:10.58,0:00:12.74,RedImpact,,0,0,0,,EVERY PILOT CALLED IT IMPOSSIBLE.
Dialogue: 0,0:00:12.74,0:00:14.20,WhiteBold,,0,0,0,,SO MAVERICK STOLE A JET
Dialogue: 0,0:00:14.20,0:00:15.82,YellowHook,,0,0,0,,TO PROVE THEM WRONG.
Dialogue: 0,0:00:15.82,0:00:18.00,RedImpact,,0,0,0,,PULLING 9 G's BETWEEN CLIFFS,
Dialogue: 0,0:00:18.00,0:00:20.66,YellowHook,,0,0,0,,DIVES VERTICAL INTO THE CRATER.
Dialogue: 0,0:00:20.66,0:00:22.00,WhiteBold,,0,0,0,,MIRACLE NUMBER ONE.
Dialogue: 0,0:00:22.00,0:00:23.60,CyanClimax,,0,0,0,,DIRECT HIT!
Dialogue: 0,0:00:23.60,0:00:25.60,YellowHook,,0,0,0,,2 MINUTES, 14 SECONDS.
Dialogue: 0,0:00:25.60,0:00:28.20,CyanClimax,,0,0,0,,\"CLASS DISMISSED.\"
"""
    with open(ass_path, 'w', encoding='utf-8') as f:
        f.write(ass_content)
    print("Generated Top Gun captions ASS file!")

def render_topgun_short():
    generate_captions()

    source_video = '/home/omie/.gemini/antigravity-ide/brain/990f0144-ba21-4d53-8f8f-b6b54be76818/scratch/topgun_movieclips.mp4'
    master_audio = '/home/omie/.gemini/antigravity-ide/brain/990f0144-ba21-4d53-8f8f-b6b54be76818/scratch/topgun_master_audio.wav'
    output_video = '/home/omie/.gemini/antigravity-ide/brain/990f0144-ba21-4d53-8f8f-b6b54be76818/scratch/topgun_maverick_epic_short.mp4'

    cuts = [
        # (start_ss, duration, crop_x_pct)
        # 1. Briefing room / map route (0.00s -> 2.26s)
        (2.5, 2.26, 0.35),
        # 2. Screaming into low-altitude canyon (2.26s -> 6.54s)
        (33.0, 4.28, 0.50),
        # 3. Inverted 90-degree knife-edge bank (6.54s -> 10.58s)
        (64.0, 4.04, 0.52),
        # 4. Control room recruits staring in shock (10.58s -> 12.74s)
        (92.0, 2.16, 0.55),
        # 5. Tom Cruise cockpit determination close-up (12.74s -> 15.82s)
        (16.0, 3.08, 0.56),
        # 6a. Vertical pop-up climb over mountain (15.82s -> 18.00s)
        (110.0, 2.18, 0.50),
        # 6b. Inverted vertical dive down ridge (18.00s -> 20.66s)
        (116.5, 2.66, 0.50),
        # 7. Bomb hit & massive fiery explosion (20.66s -> 23.60s)
        (136.5, 2.94, 0.50),
        # 8a. Cyclone frozen in shock in dark control room (23.60s -> 25.60s)
        (159.5, 2.00, 0.50),
        # 8b. Pulling 9.5 Gs into the clouds & victory roll (25.60s -> 28.20s)
        (171.2, 2.60, 0.50),
    ]

    filter_chains = []
    for idx, (ss, dur, cx) in enumerate(cuts):
        v_name = f"v{idx}"
        chain = (
            f"[0:v]trim=start={ss}:duration={dur},setpts=PTS-STARTPTS,"
            f"scale=-1:1920,crop=1080:1920:(in_w-1080)*{cx}:0,"
            f"eq=contrast=1.16:brightness=0.02:saturation=1.22[{v_name}];"
        )
        filter_chains.append(chain)

    concat_inputs = "".join([f"[v{i}]" for i in range(len(cuts))])
    concat_filter = f"{concat_inputs}concat=n={len(cuts)}:v=1:a=0[v_concat];"

    final_v_chain = (
        "[v_concat]"
        "drawbox=x=0:y=180:w=1080:h=90:color=black@0.7:t=fill,"
        "drawtext=text='TOP GUN - MAVERICK':font='Liberation Sans':fontsize=32:fontcolor=white:x=(w-text_w)/2:y=208,"
        "drawtext=text='THE IMPOSSIBLE CANYON RUN':font='Liberation Sans':fontsize=20:fontcolor=#00E5FF:x=(w-text_w)/2:y=188,"
        "ass=/home/omie/.gemini/antigravity-ide/brain/990f0144-ba21-4d53-8f8f-b6b54be76818/scratch/topgun_captions.ass[out_v]"
    )

    full_filter = "".join(filter_chains) + concat_filter + final_v_chain

    cmd = [
        'ffmpeg', '-y',
        '-i', source_video,
        '-i', master_audio,
        '-filter_complex', full_filter,
        '-map', '[out_v]',
        '-map', '1:a',
        '-c:v', 'libopenh264',
        '-b:v', '5.5M',
        '-c:a', 'aac',
        '-b:a', '192k',
        '-t', '28.2',
        output_video
    ]

    print("Rendering 28.2s Top Gun: Maverick epic short...")
    subprocess.run(cmd, check=True)
    print(f"Render finished successfully: {output_video}")

if __name__ == '__main__':
    render_topgun_short()

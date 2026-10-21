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

def build_topgun_audio(total_duration=28.2, sr=44100):
    total_samples = int(total_duration * sr)
    master = np.zeros(total_samples, dtype=np.float32)

    # 1. Assemble tightened voice lines
    lines = [
        'line_01.mp3',
        'line_02.mp3',
        'line_03.mp3',
        'line_04.mp3',
        'line_05.mp3',
        'line_06.mp3',
        'line_07.mp3',
        'line_08.mp3',
    ]

    processed_lines = []
    for fname in lines:
        mp3_path = os.path.join('/home/omie/.gemini/antigravity-ide/brain/990f0144-ba21-4d53-8f8f-b6b54be76818/scratch/voice_lines', fname)
        samples = load_audio_resampled(mp3_path, sr)
        # trim leading/trailing silence
        win = int(sr * 0.02)
        energy = [np.mean(samples[i:i+win]**2) for i in range(0, len(samples), win)]
        threshold = 0.0005

        start_idx = 0
        for idx, e in enumerate(energy):
            if e > threshold:
                start_idx = max(0, idx * win - int(sr * 0.04))
                break

        end_idx = len(samples)
        for idx in range(len(energy)-1, -1, -1):
            if energy[idx] > threshold:
                end_idx = min(len(samples), (idx + 1) * win + int(sr * 0.04))
                break

        processed_lines.append(samples[start_idx:end_idx])

    # Assemble voice with 0.12s pause
    pause_len = int(sr * 0.12)
    vox_audio = []
    line_timestamps = []
    curr = 0.0

    for idx, l_samp in enumerate(processed_lines):
        st = curr
        vox_audio.extend(l_samp)
        dur = len(l_samp) / sr
        curr += dur
        en = curr
        line_timestamps.append((st, en, dur))
        if idx < len(processed_lines) - 1:
            vox_audio.extend(np.zeros(pause_len, dtype=np.float32))
            curr += 0.12

    vox_audio = np.array(vox_audio, dtype=np.float32)
    print(f"Total voice duration: {len(vox_audio)/sr:.2f}s")
    for i, (st, en, d) in enumerate(line_timestamps):
        print(f"Line {i+1}: {st:.2f}s -> {en:.2f}s")

    # 2. Authentic Soundtrack: Lorne Balfe / Hans Zimmer - The Man, The Legend
    ost_raw = load_audio_resampled('/home/omie/.gemini/antigravity-ide/brain/990f0144-ba21-4d53-8f8f-b6b54be76818/scratch/topgun_the_man_the_legend.webm', sr)
    # Start at 35.0s in OST so the epic brass crescendo lands right at 26.5s-28.0s
    ost_start = int(35.0 * sr)
    ost_chunk = ost_raw[ost_start:ost_start + total_samples]
    if len(ost_chunk) < total_samples:
        ost_chunk = np.pad(ost_chunk, (0, total_samples - len(ost_chunk)))

    # Music volume automation:
    # 36% volume during voice narrative, swells to 82% at 26.0s for the final victory roll
    t = np.linspace(0, total_duration, total_samples)
    music_vol = np.where(t < 25.5, 0.36, 0.36 + 0.46 * np.clip((t - 25.5) / 1.5, 0, 1))

    # 3. Bomb explosion impact at 20.66s (when "Direct hit" occurs)
    # Extract authentic explosion sound from Movieclips source at 138.0s
    exp_source_cmd = ['ffmpeg', '-y', '-ss', '138.0', '-t', '3.0', '-i', '/home/omie/.gemini/antigravity-ide/brain/990f0144-ba21-4d53-8f8f-b6b54be76818/scratch/topgun_movieclips.mp4', '-ar', str(sr), '-ac', '1', '-f', 'wav', 'pipe:1']
    res_exp = subprocess.run(exp_source_cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=True)
    exp_samples = np.frombuffer(res_exp.stdout[44:], dtype=np.int16).astype(np.float32) / 32768.0

    # Mix together
    master += ost_chunk * music_vol

    # Add explosion at 20.66s
    exp_start_idx = int(20.66 * sr)
    exp_len = min(len(exp_samples), total_samples - exp_start_idx)
    if exp_len > 0:
        master[exp_start_idx:exp_start_idx + exp_len] += exp_samples[:exp_len] * 0.75

    # Voiceover overlay at dominant volume (1.35x)
    vox_len = min(len(vox_audio), total_samples)
    master[:vox_len] += vox_audio[:vox_len] * 1.35

    # Master limiter
    peak = np.max(np.abs(master))
    if peak > 0.95:
        master = master * (0.95 / peak)

    out_wav = '/home/omie/.gemini/antigravity-ide/brain/990f0144-ba21-4d53-8f8f-b6b54be76818/scratch/topgun_master_audio.wav'
    int_samples = (master * 32767).astype(np.int16)
    with wave.open(out_wav, 'w') as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sr)
        f.writeframes(int_samples.tobytes())

    print(f"Master audio generated: {out_wav} (28.2s)")
    return line_timestamps

if __name__ == '__main__':
    build_topgun_audio()

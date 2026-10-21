import os
import sys
import time
import argparse
from pathlib import Path
import soundfile as sf

# Ensure UTF-8 output on Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

from kokoro_onnx import Kokoro

VOICE_PRESETS = {
    "1": ("am_adam", "American Male (Deep, Narrative)"),
    "2": ("am_michael", "American Male (Expressive Storyteller)"),
    "3": ("am_fenrir", "American Male (Intense, Raspy)"),
    "4": ("af_bella", "American Female (Warm, Engaging)"),
    "5": ("bm_george", "British Male (Classic Documentary)"),
    "6": ("bf_emma", "British Female (Elegant Narrator)")
}

def synthesize_and_play(
    text: str,
    voice: str = "am_adam",
    speed: float = 1.05
):
    model_path = Path("models/kokoro/kokoro-v0_19.onnx")
    voices_path = Path("models/kokoro/voices.bin")
    output_wav = Path(f"output/test_kokoro_{voice}.wav")
    output_wav.parent.mkdir(parents=True, exist_ok=True)
    
    if not model_path.exists() or not voices_path.exists():
        print("[Error] Kokoro model files not ready yet. Please ensure download completes.")
        return
        
    print("=" * 60)
    print("🎙️   KOKORO-82M STYLE-DIFFUSION TTS")
    print(f">> Voice: {voice} | Speed: {speed}x")
    print(f">> Text:  \"{text}\"")
    print("=" * 60)
    
    print("\n>> Initializing neural model & style latent...")
    start_load = time.time()
    kokoro = Kokoro(str(model_path), str(voices_path))
    print(f">> Ready in {time.time() - start_load:.2f}s")
    
    print(">> Synthesizing expressive audio...")
    start_syn = time.time()
    lang = "en-gb" if voice.startswith("b") else "en-us"
    samples, sample_rate = kokoro.create(
        text=text,
        voice=voice,
        speed=speed,
        lang=lang
    )
    elapsed = time.time() - start_syn
    
    sf.write(str(output_wav), samples, sample_rate)
    print(f"[SUCCESS] Synthesized in {elapsed:.2f}s (100% OFFLINE on CPU)!")
    print(f"[SAVED]   {output_wav.resolve()}")
    
    # Auto-play on Windows
    try:
        os.startfile(str(output_wav))
        print("[PLAYING] Audio launched in your default player.\n")
    except Exception:
        pass

def interactive_mode():
    print("=" * 60)
    print("🎙️   KOKORO-82M INTERACTIVE VOICE TESTER")
    print("=" * 60)
    print("Choose a voice personality:")
    for k, (v_id, label) in VOICE_PRESETS.items():
        print(f"  [{k}] {v_id.ljust(12)} - {label}")
        
    choice = input("\nEnter choice (1-6, default: 1 [am_adam]): ").strip() or "1"
    voice_id = VOICE_PRESETS.get(choice, ("am_adam", ""))[0]
    
    print(f"\n>> Active Voice: {voice_id}")
    print(">> Type any sentence below and hit ENTER. Type 'exit' to quit.\n")
    
    while True:
        try:
            user_text = input("Story line: ").strip()
            if not user_text:
                continue
            if user_text.lower() in ("exit", "quit", "q"):
                print("Exiting...")
                break
            synthesize_and_play(user_text, voice=voice_id)
            print("-" * 50)
        except (KeyboardInterrupt, EOFError):
            print("\nExiting...")
            break

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test offline Kokoro-82M TTS")
    parser.add_argument("--voice", type=str, default="am_adam", help="Voice id (e.g. am_adam, am_michael, bm_george)")
    parser.add_argument("--text", type=str, default=None, help="Text to speak")
    parser.add_argument("--speed", type=float, default=1.05, help="Speech speed multiplier")
    args = parser.parse_args()
    
    if args.text:
        synthesize_and_play(args.text, voice=args.voice, speed=args.speed)
    else:
        interactive_mode()

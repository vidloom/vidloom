import os
import sys
import wave
import time
import argparse
from pathlib import Path

# Ensure UTF-8 output on Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

from piper.voice import PiperVoice

VOICE_MAP = {
    "1": ("hindi", "hi_IN-pratham-medium"),
    "2": ("us", "en_US-lessac-medium"),
    "hindi": ("hindi", "hi_IN-pratham-medium"),
    "us": ("us", "en_US-lessac-medium")
}

def synthesize_and_play(text: str, voice_key: str = "hindi"):
    alias, model_file = VOICE_MAP.get(voice_key, ("custom", voice_key))
    model_path = Path(f"models/piper/{model_file}.onnx")
    config_path = Path(f"models/piper/{model_file}.onnx.json")
    output_wav = Path(f"output/test_{alias}.wav")
    output_wav.parent.mkdir(parents=True, exist_ok=True)
    
    if not model_path.exists():
        print(f"\n[Error] Model file {model_path} not found!")
        return
        
    print(f"\n>> Synthesizing with {model_file}...")
    start_time = time.time()
    
    voice = PiperVoice.load(model_path, config_path=config_path)
    with wave.open(str(output_wav), "wb") as wav_file:
        voice.synthesize_wav(text, wav_file)
        
    elapsed = time.time() - start_time
    print(f"[Done] Audio generated in {elapsed:.2f}s!")
    print(f"[Saved] {output_wav.resolve()}")
    
    # Automatically open and play in default Windows audio player
    try:
        os.startfile(str(output_wav))
        print("[Playing] Audio launched in your default player.")
    except Exception:
        pass

def interactive_mode():
    print("=" * 60)
    print("🎙️   VIDLOOM OFFLINE TTS TESTER")
    print("=" * 60)
    print("Select Voice:")
    print("  [1] 🇮🇳 Hindi (Pratham)")
    print("  [2] 🇺🇸 US English (Lessac)")
    
    choice = input("\nEnter choice (1 or 2, default: 1): ").strip() or "1"
    voice_key = "1" if choice == "1" else "2"
    voice_name = "Hindi" if voice_key == "1" else "US English"
    
    print(f"\n>> Active Voice: {voice_name}")
    print(">> Type any text below and hit ENTER. Type 'exit' to quit.\n")
    
    while True:
        try:
            user_text = input("Text to speak: ").strip()
            if not user_text:
                continue
            if user_text.lower() in ("exit", "quit", "q"):
                print("Exiting...")
                break
            synthesize_and_play(user_text, voice_key)
            print("-" * 50)
        except (KeyboardInterrupt, EOFError):
            print("\nExiting...")
            break

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test offline Piper voice synthesis")
    parser.add_argument("--voice", choices=["hindi", "us"], default=None, help="Voice to use")
    parser.add_argument("--text", type=str, default=None, help="Text to speak")
    args = parser.parse_args()
    
    if args.text and args.voice:
        synthesize_and_play(args.text, args.voice)
    else:
        # Run interactive mode if no arguments are provided
        interactive_mode()

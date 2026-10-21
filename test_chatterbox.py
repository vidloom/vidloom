import os
import sys
import time
from pathlib import Path

# Ensure UTF-8 output on Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# Fix Perth watermarker shim before Chatterbox imports
import perth
if getattr(perth, 'PerthImplicitWatermarker', None) is None:
    perth.PerthImplicitWatermarker = perth.DummyWatermarker
sys.modules['resemble_perth'] = perth

import torch
import torchaudio as ta
from chatterbox.models.s3gen.s3gen import S3Token2Wav as S3Gen
from chatterbox.models.t3.t3 import T3, T3Config
from chatterbox.models.tokenizers.tokenizer import EnTokenizer
from chatterbox.models.voice_encoder.voice_encoder import VoiceEncoder
from chatterbox.tts import ChatterboxTTS, Conditionals
from safetensors.torch import load_file

def load_chatterbox(ckpt_dir: Path = Path("models/chatterbox"), device: str = "cpu"):
    ve = VoiceEncoder()
    ve.load_state_dict(load_file(ckpt_dir / "ve.safetensors"))
    ve.eval()
    
    t3 = T3(T3Config.multilingual())
    t3_state = load_file(ckpt_dir / "t3_mtl23ls_v3.safetensors")
    if "model" in t3_state:
        t3_state = t3_state["model"][0]
    t3.load_state_dict(t3_state)
    t3.eval()
    
    s3gen = S3Gen()
    s3gen.load_state_dict(load_file(ckpt_dir / "s3gen_v3.safetensors"), strict=False)
    s3gen.eval()
    
    tokenizer = EnTokenizer(str(ckpt_dir / "mtl_tokenizer.json"))
    conds = Conditionals.load(ckpt_dir / "conds.pt", map_location=torch.device(device))
    
    return ChatterboxTTS(t3, s3gen, ve, tokenizer, device, conds=conds)

def test_chatterbox(text: str, output_name: str = "test_chatterbox.wav"):
    output_path = Path("output") / output_name
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    print("=" * 65)
    print("🎭  CHATTERBOX TTS (RESEMBLE AI) — EMOTIVE SPEECH TEST")
    print(f">> Text: \"{text}\"")
    print("=" * 65)
    
    print("\n>> Loading Chatterbox model into memory (CPU)...")
    start_load = time.time()
    model = load_chatterbox()
    print(f">> Model loaded in {time.time() - start_load:.2f}s")
    
    print(">> Generating expressive speech with emotion tags...")
    start_syn = time.time()
    wav = model.generate(text)
    syn_time = time.time() - start_syn
    
    ta.save(str(output_path), wav, model.sr)
    print(f"\n[SUCCESS] Audio synthesized in {syn_time:.2f}s!")
    print(f"[SAVED]   {output_path.resolve()}")
    
    # Auto-play on Windows
    try:
        os.startfile(str(output_path))
        print("[PLAYING] Audio launched in your default player.\n")
    except Exception:
        pass

if __name__ == "__main__":
    default_text = "I walked into the dark room... [gasp] and the door slammed behind me! [whisper] Please don't look over here..."
    input_text = sys.argv[1] if len(sys.argv) > 1 else default_text
    test_chatterbox(input_text)

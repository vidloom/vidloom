import os
import sys
import re
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
import soundfile as sf
import gradio as gr
from chatterbox.models.s3gen.s3gen import S3Token2Wav as S3Gen
from chatterbox.models.t3.t3 import T3, T3Config
from chatterbox.models.tokenizers.tokenizer import EnTokenizer
from chatterbox.models.voice_encoder.voice_encoder import VoiceEncoder
from chatterbox.tts import ChatterboxTTS, Conditionals
from safetensors.torch import load_file

# Cache model in memory
_MODEL = None

def get_model(ckpt_dir: Path = Path("models/chatterbox"), device: str = "cpu"):
    global _MODEL
    if _MODEL is None:
        print("[Chatterbox] Loading model weights into memory (CPU)...")
        start_t = time.time()
        
        # 1. Voice Encoder
        ve = VoiceEncoder()
        ve.load_state_dict(load_file(ckpt_dir / "ve.safetensors"))
        ve.eval()
        
        # 2. Multilingual T3 Transformer
        t3 = T3(T3Config.multilingual())
        t3_state = load_file(ckpt_dir / "t3_mtl23ls_v3.safetensors")
        if "model" in t3_state:
            t3_state = t3_state["model"][0]
        t3.load_state_dict(t3_state)
        t3.eval()
        
        # 3. S3Gen Vocoder
        s3gen = S3Gen()
        s3gen.load_state_dict(load_file(ckpt_dir / "s3gen_v3.safetensors"), strict=False)
        s3gen.eval()
        
        # 4. Multilingual Tokenizer & Conditionals
        tokenizer = EnTokenizer(str(ckpt_dir / "mtl_tokenizer.json"))
        conds = Conditionals.load(ckpt_dir / "conds.pt", map_location=torch.device(device))
        
        # 5. Assemble Chatterbox TTS Engine
        _MODEL = ChatterboxTTS(t3, s3gen, ve, tokenizer, device, conds=conds)
        print(f"[Chatterbox] Model loaded and ready in {time.time() - start_t:.1f}s!")
    return _MODEL

TAG_MAP = {
    r"\[chuckle\]": "[giggle]",
    r"\[laugh\]": "[laughter]",
    r"\[snicker\]": "[giggle]",
    r"\[breath\]": "[inhale]",
    r"\[breathe\]": "[exhale]",
}

def chunk_text(text: str) -> list[str]:
    """Splits long paragraphs into individual sentences so Chatterbox doesn't cut off after 2 seconds."""
    # Map common aliases to native Chatterbox emotion tokens
    for pattern, repl in TAG_MAP.items():
        text = re.sub(pattern, repl, text, flags=re.IGNORECASE)
        
    text = text.strip()
    raw_sentences = re.split(r'(?<=[.!?\n])\s+', text)
    sentences = []
    for s in raw_sentences:
        s = s.strip()
        if not s:
            continue
        # If the chunk is just an emotion tag by itself, merge it
        if re.fullmatch(r'\[[a-zA-Z_]+\]', s) and sentences:
            sentences[-1] += " " + s
        else:
            sentences.append(s)
    return sentences if sentences else [text]

def generate_voice(
    text: str,
    audio_ref,
    exaggeration: float,
    temperature: float,
    repetition_penalty: float,
    progress=gr.Progress(track_tqdm=True)
):
    if not text.strip():
        return None, "Please enter some text."
        
    model = get_model()
    
    ref_path = None
    if audio_ref is not None and str(audio_ref).strip():
        ref_path = str(audio_ref)
        
    chunks = chunk_text(text)
    start_t = time.time()
    print(f"\n>> Generating script ({len(chunks)} sentences, Exaggeration: {exaggeration})...")
    
    all_wavs = []
    silence = torch.zeros(1, int(model.sr * 0.18)) # 180ms natural pause
    
    for i, chunk in enumerate(chunks):
        progress((i) / len(chunks), desc=f"Generating sentence {i+1} of {len(chunks)}...")
        print(f"   [{i+1}/{len(chunks)}] \"{chunk}\"")
        try:
            c_wav = model.generate(
                text=chunk,
                audio_prompt_path=ref_path,
                exaggeration=exaggeration,
                temperature=temperature,
                repetition_penalty=repetition_penalty
            )
            all_wavs.append(c_wav)
            all_wavs.append(silence)
        except Exception as e:
            print(f"   [Error on chunk {i+1}]: {e}")
            
    progress(1.0, desc="Stitching audio together...")
    
    if not all_wavs:
        return None, "Generation failed for all chunks."
        
    full_wav = torch.cat(all_wavs[:-1], dim=1)
    
    elapsed = time.time() - start_t
    output_path = Path("output/chatterbox_gui_sample.wav")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    audio_np = full_wav.squeeze().cpu().numpy()
    sf.write(str(output_path), audio_np, model.sr)
    
    total_duration = audio_np.shape[0] / model.sr
    status_msg = f"Generated {total_duration:.1f}s of audio across {len(chunks)} sentences in {elapsed:.1f}s!"
    print(f">> {status_msg}")
    return str(output_path), status_msg

def append_tag(current_text: str, tag: str) -> str:
    if current_text:
        return current_text.rstrip() + f" {tag} "
    return tag + " "

def build_gui():
    with gr.Blocks(title="Chatterbox Studio - Local Voice AI", theme=gr.themes.Soft()) as demo:
        gr.Markdown(
            """
            # 🎭 Chatterbox TTS Studio
            ### Human-level expressive voice acting with emotion tags and zero-shot voice cloning.
            *Runs 100% locally on your machine.*
            """
        )
        
        with gr.Row():
            with gr.Column(scale=2):
                text_input = gr.Textbox(
                    label="Script / Story Text",
                    placeholder="Enter what you want the voice to say...",
                    value="I thought I was completely alone in that room. [gasp] But then the door slammed shut! [whisper] Please don't look over here... [chuckle] Did you really think you could escape?",
                    lines=5
                )
                
                gr.Markdown("**Quick Insert Emotion Tags:**")
                with gr.Row():
                    btn_whisper = gr.Button("🤫 [whisper]", size="sm")
                    btn_gasp = gr.Button("😱 [gasp]", size="sm")
                    btn_laugh = gr.Button("😂 [laughter]", size="sm")
                    btn_chuckle = gr.Button("🤭 [giggle]", size="sm")
                    btn_sigh = gr.Button("😮‍💨 [sigh]", size="sm")
                    btn_cough = gr.Button("😷 [cough]", size="sm")
                    
                # Tag click handlers
                btn_whisper.click(fn=lambda t: append_tag(t, "[whisper]"), inputs=[text_input], outputs=[text_input])
                btn_gasp.click(fn=lambda t: append_tag(t, "[gasp]"), inputs=[text_input], outputs=[text_input])
                btn_laugh.click(fn=lambda t: append_tag(t, "[laughter]"), inputs=[text_input], outputs=[text_input])
                btn_chuckle.click(fn=lambda t: append_tag(t, "[giggle]"), inputs=[text_input], outputs=[text_input])
                btn_sigh.click(fn=lambda t: append_tag(t, "[sigh]"), inputs=[text_input], outputs=[text_input])
                btn_cough.click(fn=lambda t: append_tag(t, "[cough]"), inputs=[text_input], outputs=[text_input])
                
                with gr.Accordion("Voice Cloning & Settings (Optional)", open=True):
                    audio_ref = gr.Audio(
                        label="Voice Clone Reference (Upload ANY 5-10s clip to clone)",
                        type="filepath"
                    )
                    with gr.Row():
                        exaggeration = gr.Slider(0.0, 1.0, value=0.6, step=0.05, label="Drama / Exaggeration")
                        temperature = gr.Slider(0.1, 1.2, value=0.8, step=0.05, label="Prosody Variance")
                        rep_penalty = gr.Slider(1.0, 2.0, value=1.2, step=0.05, label="Repetition Penalty")
                        
                generate_btn = gr.Button("🎙️ Generate Voice", variant="primary", size="lg")

            with gr.Column(scale=1):
                audio_output = gr.Audio(label="Generated Voice Output", type="filepath")
                status_output = gr.Label(label="Status")

        generate_btn.click(
            fn=generate_voice,
            inputs=[text_input, audio_ref, exaggeration, temperature, rep_penalty],
            outputs=[audio_output, status_output]
        )

    return demo

if __name__ == "__main__":
    demo = build_gui()
    print("\n" + "=" * 65)
    print("🚀  LAUNCHING CHATTERBOX STUDIO GUI")
    print(">> Open your browser at: http://127.0.0.1:7860")
    print("=" * 65 + "\n")
    demo.launch(inbrowser=True)

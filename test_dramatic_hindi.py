import os
import sys
import asyncio
from pathlib import Path
import edge_tts

# Ensure UTF-8 output on Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

async def generate_dramatic_hindi(text: str, voice: str = "hi-IN-MadhurNeural"):
    output_mp3 = Path("output/test_hindi_dramatic.mp3")
    output_mp3.parent.mkdir(parents=True, exist_ok=True)
    
    print("=" * 60)
    print("🎭  MICROSOFT NEURAL TTS — DRAMATIC HINDI TEST")
    print(f">> Voice: {voice} (Madhur Neural - Storyteller)")
    print(f">> Text:  \"{text}\"")
    print("=" * 60)
    
    # -4% rate and -2Hz pitch creates a slower, deeper, suspenseful cadence
    communicate = edge_tts.Communicate(
        text=text,
        voice=voice,
        rate="-4%",
        pitch="-2Hz"
    )
    
    print("\n>> Generating high-fidelity neural audio...")
    await communicate.save(str(output_mp3))
    print(f"[Done] Audio generated!")
    print(f"[Saved] {output_mp3.resolve()}")
    
    # Auto-play on Windows
    try:
        os.startfile(str(output_mp3))
        print("[Playing] Audio launched in your default player.\n")
    except Exception:
        pass

if __name__ == "__main__":
    # Dramatic horror/mystery storytelling sample
    default_dramatic_text = (
        "रात के ठीक तीन बजे... मेरे दरवाज़े पर किसी ने धीरे से दस्तक दी। "
        "जब मैंने सिक्योरिटी कैमरा चेक किया... तो बाहर कोई नहीं था। "
        "लेकिन तभी मेरी नज़र दरवाज़े पर पड़ी... और दरवाज़े का हैंडल... धीरे-धीरे नीचे झुक रहा था।"
    )
    
    custom_text = sys.argv[1] if len(sys.argv) > 1 else default_dramatic_text
    asyncio.run(generate_dramatic_hindi(custom_text))

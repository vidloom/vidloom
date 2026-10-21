import asyncio
import json
from pathlib import Path
from typing import Dict, List, Optional
import edge_tts
from config.settings import DEFAULT_VOICE, TEMP_DIR

AVAILABLE_VOICES = {
    "viral_narrator": "en-US-BrianMultilingualNeural",
    "us_male": "en-US-ChristopherNeural",
    "us_female": "en-US-EmmaNeural",
    "us_casual": "en-US-GuyNeural",
    "uk_male": "en-GB-RyanNeural",
    "uk_female": "en-GB-SoniaNeural",
    "in_male": "en-IN-PrabhatNeural",
    "in_female": "en-IN-NeerjaNeural"
}

async def _synthesize(
    text: str,
    voice: str = DEFAULT_VOICE,
    rate: str = "+5%",
    output_audio: Optional[Path] = None,
    output_meta: Optional[Path] = None
) -> Dict:
    audio_path = output_audio or (TEMP_DIR / "speech.mp3")
    meta_path = output_meta or (TEMP_DIR / "timestamps.json")
    
    communicate = edge_tts.Communicate(
        text=text,
        voice=voice,
        rate=rate,
        boundary="WordBoundary"
    )
    
    audio_bytes = bytearray()
    words_data: List[Dict] = []
    
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_bytes.extend(chunk["data"])
        elif chunk["type"] == "WordBoundary":
            # Offset and duration are in 100ns units (1 sec = 10,000,000 units)
            start_sec = round(chunk["offset"] / 10_000_000, 3)
            duration_sec = round(chunk["duration"] / 10_000_000, 3)
            end_sec = round(start_sec + duration_sec, 3)
            
            clean_word = chunk["text"].strip()
            if clean_word:
                words_data.append({
                    "word": clean_word,
                    "start": start_sec,
                    "end": end_sec
                })
                
    # Save audio file
    with open(audio_path, "wb") as f:
        f.write(audio_bytes)
        
    # Save timestamp metadata
    total_duration = words_data[-1]["end"] if words_data else 0.0
    payload = {
        "text": text,
        "voice": voice,
        "rate": rate,
        "duration": total_duration,
        "word_count": len(words_data),
        "words": words_data
    }
    
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
        
    return {
        "audio_path": audio_path,
        "meta_path": meta_path,
        "duration": total_duration,
        "words": words_data
    }

def generate_voiceover(
    text: str,
    voice: str = DEFAULT_VOICE,
    rate: str = "+5%",
    output_audio: Optional[Path] = None,
    output_meta: Optional[Path] = None
) -> Dict:
    """Synchronous wrapper around edge-tts synthesis."""
    return asyncio.run(_synthesize(text, voice, rate, output_audio, output_meta))

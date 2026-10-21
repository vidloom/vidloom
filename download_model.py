import os
import sys
import argparse
from pathlib import Path
import urllib.request
from tqdm import tqdm

VOICE_REGISTRY = {
    "hindi": {
        "name": "hi_IN-pratham-medium",
        "description": "Native Hindi Male (Pratham)",
        "base_url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/hi/hi_IN/pratham/medium/"
    },
    "hindi_female": {
        "name": "hi_IN-priyamvada-medium",
        "description": "Native Hindi Female (Priyamvada)",
        "base_url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/hi/hi_IN/priyamvada/medium/"
    },
    "us": {
        "name": "en_US-lessac-medium",
        "description": "US English Male/Narrator (Lessac)",
        "base_url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/"
    },
    "uk": {
        "name": "en_GB-alan-medium",
        "description": "UK English Male (Alan)",
        "base_url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/alan/medium/"
    }
}

class DownloadProgressBar(tqdm):
    def update_to(self, b=1, bsize=1, tsize=None):
        if tsize is not None:
            self.total = tsize
        self.update(b * bsize - self.n)

def download_voice(voice_key: str, dest_dir: Path = Path("models/piper")):
    if voice_key not in VOICE_REGISTRY:
        print(f"[Error] Unknown voice '{voice_key}'. Available: {list(VOICE_REGISTRY.keys())}")
        return False
        
    voice_info = VOICE_REGISTRY[voice_key]
    dest_dir.mkdir(parents=True, exist_ok=True)
    
    name = voice_info["name"]
    base_url = voice_info["base_url"]
    
    files_to_download = [
        f"{name}.onnx",
        f"{name}.onnx.json"
    ]
    
    print(f"\n>> Downloading Offline Voice: {voice_info['description']}")
    print(f">> Target Directory: {dest_dir.resolve()}\n")
    
    for filename in files_to_download:
        target_path = dest_dir / filename
        if target_path.exists() and target_path.stat().st_size > 1000:
            print(f"[Exists] {filename} is already downloaded.")
            continue
            
        url = base_url + filename
        print(f"Downloading {filename}...")
        try:
            with DownloadProgressBar(unit='B', unit_scale=True, miniters=1, desc=filename) as t:
                urllib.request.urlretrieve(url, filename=target_path, reporthook=t.update_to)
            print(f"[Done] Saved {filename} ({target_path.stat().st_size / (1024*1024):.1f} MB)")
        except Exception as e:
            print(f"[Error] Failed downloading {filename}: {e}")
            if target_path.exists():
                target_path.unlink()
            return False
            
    print(f"\n[Success] Voice '{voice_key}' ({name}) is ready for offline use!")
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download offline Piper TTS voices")
    parser.add_argument("voice", choices=list(VOICE_REGISTRY.keys()), default="hindi", nargs="?", help="Voice to download")
    args = parser.parse_args()
    download_voice(args.voice)

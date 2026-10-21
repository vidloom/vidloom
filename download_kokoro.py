import sys
import time
from pathlib import Path
import requests
from tqdm import tqdm

KOKORO_FILES = {
    "kokoro-v0_19.onnx": "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files/kokoro-v0_19.onnx",
    "voices.bin": "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files/voices.bin"
}

def download_file_with_retry(url: str, dest_path: Path, max_retries: int = 5):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }
    
    # Check existing partial size
    initial_pos = 0
    if dest_path.exists():
        initial_pos = dest_path.stat().st_size

    # First get total size
    head_resp = requests.head(url, headers=headers, allow_redirects=True, timeout=15)
    total_size = int(head_resp.headers.get('content-length', 0))

    if initial_pos >= total_size and total_size > 0:
        print(f"[Exists] {dest_path.name} is already complete ({initial_pos / (1024*1024):.1f} MB).")
        return True

    for attempt in range(max_retries):
        try:
            resume_headers = dict(headers)
            if initial_pos > 0:
                resume_headers["Range"] = f"bytes={initial_pos}-"
                print(f"[Resuming] Continuing from {initial_pos / (1024*1024):.1f} MB / {total_size / (1024*1024):.1f} MB...")
            else:
                print(f"[Downloading] {dest_path.name} ({total_size / (1024*1024):.1f} MB)...")

            response = requests.get(url, headers=resume_headers, stream=True, timeout=20)
            
            mode = "ab" if initial_pos > 0 and response.status_code == 206 else "wb"
            if mode == "wb":
                initial_pos = 0

            with open(dest_path, mode) as f, tqdm(
                total=total_size,
                initial=initial_pos,
                unit='B',
                unit_scale=True,
                desc=dest_path.name
            ) as bar:
                for chunk in response.iter_content(chunk_size=1024 * 512): # 512KB chunks
                    if chunk:
                        f.write(chunk)
                        bar.update(len(chunk))
                        initial_pos += len(chunk)
                        
            print(f"[Done] Saved {dest_path.name} ({dest_path.stat().st_size / (1024*1024):.1f} MB)")
            return True

        except Exception as e:
            print(f"\n[Warning] Connection glitch on attempt {attempt+1}/{max_retries}: {e}")
            time.sleep(2)
            if dest_path.exists():
                initial_pos = dest_path.stat().st_size

    return False

def download_kokoro():
    dest_dir = Path("models/kokoro")
    dest_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 60)
    print(">> DOWNLOADING KOKORO-82M (OFFLINE STYLE-DIFFUSION MODEL)")
    print(f">> Destination: {dest_dir.resolve()}")
    print("=" * 60)
    
    for filename, url in KOKORO_FILES.items():
        dest_file = dest_dir / filename
        success = download_file_with_retry(url, dest_file)
        if not success:
            print(f"[Error] Failed to complete download for {filename}")
            return False
            
    print("\n" + "=" * 60)
    print("[SUCCESS] Kokoro-82M model and voices are completely downloaded!")
    print("=" * 60)
    return True

if __name__ == "__main__":
    download_kokoro()

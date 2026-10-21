import sys
import time
from pathlib import Path
import requests
from tqdm import tqdm

# Ensure UTF-8 output on Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

BASE_URL = "https://huggingface.co/ResembleAI/chatterbox/resolve/main/"
FILES_TO_DOWNLOAD = [
    "s3gen_v3.safetensors",
    "t3_mtl23ls_v3.safetensors",
    "ve.safetensors",
    "conds.pt",
    "tokenizer.json",
    "mtl_tokenizer.json"
]

def download_file_with_resume(filename: str, dest_dir: Path, max_retries: int = 10):
    dest_path = dest_dir / filename
    url = BASE_URL + filename
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }

    # Get total file size
    head = requests.head(url, headers=headers, allow_redirects=True, timeout=25)
    total_bytes = int(head.headers.get('content-length', 0))
    
    # Check if already completed
    if dest_path.exists() and total_bytes > 0 and dest_path.stat().st_size >= total_bytes:
        print(f"[Done] {filename} is already completed ({dest_path.stat().st_size / (1024*1024):.1f} MB)")
        return True

    # Retry loop with automatic range resume
    for attempt in range(1, max_retries + 1):
        try:
            initial_bytes = dest_path.stat().st_size if dest_path.exists() else 0
            if total_bytes > 0 and initial_bytes >= total_bytes:
                return True

            resume_headers = dict(headers)
            if initial_bytes > 0:
                resume_headers["Range"] = f"bytes={initial_bytes}-"
                mode = "ab"
                if attempt > 1:
                    print(f">> [Attempt {attempt}/{max_retries}] Resuming from {initial_bytes / (1024*1024):.1f} MB...")
            else:
                mode = "wb"

            response = requests.get(url, headers=resume_headers, stream=True, timeout=30)
            
            # If server doesn't support 206 Partial Content, reset
            if initial_bytes > 0 and response.status_code != 206:
                mode = "wb"
                initial_bytes = 0

            bar_format = "{desc}: {percentage:3.0f}%|{bar:25}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]"
            
            with open(dest_path, mode) as f, tqdm(
                total=total_bytes,
                initial=initial_bytes,
                unit='B',
                unit_scale=True,
                unit_divisor=1024,
                desc=filename.ljust(25),
                bar_format=bar_format
            ) as bar:
                for chunk in response.iter_content(chunk_size=1024 * 512):
                    if chunk:
                        f.write(chunk)
                        bar.update(len(chunk))
                        initial_bytes += len(chunk)

            # Successfully completed
            if dest_path.stat().st_size >= total_bytes:
                print(f"[Done] Finished {filename} ({dest_path.stat().st_size / (1024*1024):.1f} MB)")
                return True

        except Exception as e:
            curr_mb = dest_path.stat().st_size / (1024*1024) if dest_path.exists() else 0
            print(f"\n[Connection dropped at {curr_mb:.1f} MB: {e}] Reconnecting in 2s...")
            time.sleep(2)

    print(f"[Error] Max retries exceeded for {filename}")
    return False

def main():
    dest_dir = Path("models/chatterbox")
    dest_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 75)
    print("📥  DOWNLOADING CHATTERBOX TTS (AUTO-RESUME ENABLED)")
    print(f">> Destination: {dest_dir.resolve()}")
    print("=" * 75)
    
    start_all = time.time()
    for idx, fname in enumerate(FILES_TO_DOWNLOAD, 1):
        print(f"\n[{idx}/{len(FILES_TO_DOWNLOAD)}] Checking / Downloading {fname}...")
        success = download_file_with_resume(fname, dest_dir)
        if not success:
            print(f"[Error] Could not complete {fname}.")
            return
        
    total_time = time.time() - start_all
    print("\n" + "=" * 75)
    print(f"[SUCCESS] All 6 Chatterbox files downloaded in {total_time:.1f} seconds!")
    print(f">> Folder: {dest_dir.resolve()}")
    print("=" * 75)

if __name__ == "__main__":
    main()

from __future__ import annotations

import json
import subprocess
from pathlib import Path


SCOPE = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]


def set_secret(repo: str, name: str, value: str) -> None:
    subprocess.run(
        ["gh", "secret", "set", name, "--repo", repo],
        input=value,
        text=True,
        check=True,
    )


def main() -> None:
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError as error:
        raise SystemExit("Install automation/requirements.txt first") from error

    repo = input("Private GitHub repository (OWNER/REPO): ").strip()
    secrets_path = Path(input("Google OAuth desktop client JSON path: ").strip()).expanduser().resolve()
    if not secrets_path.is_file():
        raise SystemExit(f"File not found: {secrets_path}")
    config = json.loads(secrets_path.read_text(encoding="utf-8"))
    client = config.get("installed") or config.get("web")
    if not client:
        raise SystemExit("OAuth JSON does not contain an installed or web client")

    flow = InstalledAppFlow.from_client_config(config, scopes=SCOPE)
    credentials = flow.run_local_server(host="127.0.0.1", port=0, access_type="offline", prompt="consent")
    if not credentials.refresh_token:
        raise SystemExit("Google did not return a refresh token. Revoke prior consent and run again.")

    print("Sending three values directly to GitHub encrypted secrets; values are not written locally.")
    set_secret(repo, "YOUTUBE_CLIENT_ID", client["client_id"])
    set_secret(repo, "YOUTUBE_CLIENT_SECRET", client["client_secret"])
    set_secret(repo, "YOUTUBE_REFRESH_TOKEN", credentials.refresh_token)
    print("YouTube upload credentials configured.")


if __name__ == "__main__":
    main()

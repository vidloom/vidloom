"""Laptop-independent Vidloom deployment. `modal deploy automation/cloud_app.py`."""
from pathlib import Path
import modal

ROOT = Path(__file__).resolve().parents[1]
app = modal.App("vidloom-autopilot")
volume = modal.Volume.from_name("vidloom-production", create_if_missing=True)
store = modal.Dict.from_name("vidloom-control-v2", create_if_missing=True)
secret = modal.Secret.from_name("vidloom-runtime")
base = modal.Image.debian_slim(python_version="3.11").pip_install("fastapi==0.115.12", "httpx==0.28.1")
control_image = (base
    .env({"PYTHONPATH": "/app"})
    .add_local_dir(ROOT / "automation", "/app/automation", ignore=["**/__pycache__/**", "tests/**"], copy=True))
image = (base.apt_install("ffmpeg", "curl", "libespeak-ng1", "fonts-liberation", "fonts-dejavu-core")
    .pip_install("groq==1.7.0", "kokoro-onnx==0.6.1", "soundfile==0.13.1", "jsonschema==4.25.1",
                 "google-api-python-client==2.185.0", "google-auth-httplib2==0.2.0", "numpy==2.2.6",
                 "Pillow==12.0.0")
    .run_commands(
        "mkdir -p /app/models/kokoro && "
        "curl -fL --retry 4 -o /app/models/kokoro/kokoro-v0_19.onnx "
        "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files/kokoro-v0_19.onnx && "
        "curl -fL --retry 4 -o /app/models/kokoro/voices.bin "
        "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files/voices.bin"
    )
    .env({"OMP_NUM_THREADS": "4", "PYTHONPATH": "/app"})
    .add_local_dir(ROOT / "automation", "/app/automation", ignore=["**/__pycache__/**", "tests/**"], copy=True)
    .add_local_dir(ROOT / "premium_pipeline/v3", "/app/premium_pipeline/v3", ignore=["**/__pycache__/**", "tests/**"], copy=True))

@app.function(image=image, secrets=[secret], volumes={"/data": volume},
              cpu=(2, 4), memory=(4096, 8192), timeout=1800, max_containers=1,
              scaledown_window=2, retries=0)
@modal.concurrent(max_inputs=1)
def cycle(test: bool = False, request: str = ""):
    from automation.cloud_runtime import run_cycle
    return run_cycle(store, volume, test=test, request=request)

@app.function(image=base, schedule=modal.Cron("11 * * * *"), timeout=30,
              max_containers=1, scaledown_window=2)
def heartbeat():
    # Control endpoint and timer never render; processing runs in one durable lane.
    cfg = store.get("config", {})
    if cfg.get("enabled", True):
        active = store.get("runtime", {}).get("active")
        import time
        if not active or time.time() - active.get("heartbeat", 0) > 1900:
            cycle.spawn()

@app.function(image=control_image, secrets=[secret], timeout=60, max_containers=1, scaledown_window=2)
@modal.concurrent(max_inputs=1)
@modal.asgi_app()
def api():
    import hmac, os, time
    from fastapi import FastAPI, Request
    from fastapi.responses import JSONResponse
    web = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    @web.api_route("/api/{path:path}", methods=["GET", "POST", "PATCH"])
    async def route(path: str, req: Request):
        expected = os.environ.get("CLOUD_CONTROL_SECRET", "")
        if not expected or not hmac.compare_digest(req.headers.get("authorization", ""), "Bearer " + expected):
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        from automation.cloud_runtime import DEFAULT_CONFIG, public_state, validate_settings
        if path == "state" and req.method == "GET":
            return public_state(store)
        if path == "settings" and req.method == "PATCH":
            try:
                settings = validate_settings(await req.json(), store.get("config", DEFAULT_CONFIG))
            except (ValueError, TypeError) as error:
                return JSONResponse({"error": str(error)}, status_code=400)
            store["config"] = settings
            return {"ok": True, "message": "Settings saved", "config": settings}
        if path == "action" and req.method == "POST":
            body = await req.json()
            action = body.get("action")
            cfg = store.get("config", DEFAULT_CONFIG).copy()
            if action in ("pause", "resume"):
                cfg["enabled"] = action == "resume"
                store["config"] = cfg
                if action == "resume":
                    cycle.spawn()
                return {"ok": True, "message": "Autopilot " + ("resumed" if cfg["enabled"] else "paused after current step")}
            if action in ("run", "autopilot", "refresh"):
                active = store.get("runtime", {}).get("active")
                if active and time.time() - active.get("heartbeat", 0) < 1900:
                    return {"ok": True, "message": "Production is already running"}
                cycle.spawn()
                return JSONResponse({"ok": True, "message": "Cloud cycle queued"}, status_code=202)
            return JSONResponse({"error": "Unknown action"}, status_code=400)
        if path == "create" and req.method == "POST":
            body = await req.json()
            prompt = str(body.get("prompt", "")).strip()
            if not prompt or len(prompt) > 1200:
                return JSONResponse({"error": "Enter a request of 1–1200 characters"}, status_code=400)
            cycle.spawn(request=prompt)
            return JSONResponse({"ok": True, "message": "Your extra request is queued"}, status_code=202)
        return JSONResponse({"error": "Not found"}, status_code=404)
    return web

@app.local_entrypoint()
def main(test: bool = False, status: bool = False):
    import json
    if status:
        from automation.cloud_runtime import public_state
        print(json.dumps(public_state(store), indent=2))
    else:
        print(json.dumps(cycle.remote(test=test), indent=2))

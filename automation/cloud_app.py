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


@app.function(image=image, secrets=[secret], volumes={"/data": volume},
              cpu=(2, 4), memory=(4096, 8192), timeout=1800, max_containers=1,
              scaledown_window=2, retries=0)
def render_and_upload_project(project_rel_path: str, test: bool = False):
    import json, os, subprocess, sys, time, uuid
    from pathlib import Path
    from automation.cloud_runtime import Recorder, now, upload, youtube_client, RATE_RESERVED, RATE_UPPER

    started = time.monotonic()
    runtime = store.get("runtime", {"jobs": [], "events": [], "active": None})
    cfg = store.get("config", {})

    project_dir = Path("/data") / project_rel_path
    project_path = project_dir / "project.json"
    pipeline_py = Path("/app/premium_pipeline/v3/pipeline.py")

    with open(project_path) as f:
        project = json.load(f)

    job_id = "v-jack-" + uuid.uuid4().hex[:8]
    job = {
        "id": job_id,
        "title": project.get("title", "The Greatest Character Entrance in Cinema History")[:100],
        "status": "building",
        "created_at": now(),
        "steps": [],
        "description": "#Shorts #PiratesOfTheCaribbean #CinemaAnalysis" + chr(10) + chr(10) + "Captain Jack Sparrow's iconic entrance analyzed." + chr(10) + "Fair use film critique and cinematic commentary.",
    }
    runtime["jobs"].insert(0, job)
    rec = Recorder(store, runtime, job)
    rec.save()

    with rec.step("Validate project"):
        subprocess.run([sys.executable, str(pipeline_py), "validate", str(project_path)], check=True)

    with rec.step("Render 1440x2560 2K 60fps master with highlighted captions & RTX grading"):
        (project_dir / "build" / "draft.mp4").unlink(missing_ok=True)
        subprocess.run([sys.executable, str(pipeline_py), "render", str(project_path), "--encoder", "libx264"], check=True)

    with rec.step("Decode and loudness quality control"):
        qc_file = project_dir / "build" / "qc.json"
        video = project_dir / "build" / "draft.mp4"
        if not video.exists():
            raise RuntimeError("Draft video was not generated")
        qc_data = json.loads(qc_file.read_text(encoding="utf-8"))
        if not qc_data.get("technical_pass"):
            raise RuntimeError("Technical QC failed: " + str(qc_data.get("failures")))
        job.update(status="ready", video_path=str(video), qc={"technical_pass": True, "video_sha256": qc_data.get("video_sha256"), "loudness": qc_data.get("loudness")})
        rec.save()
        volume.commit()

    with rec.step("YouTube upload & schedule"):
        upload(job, video, rec, runtime, store, volume, test=test)
        runtime["last_success_at"] = now()

    elapsed = time.monotonic() - started
    job["elapsed_seconds"] = round(elapsed, 3)
    job["cost"] = {
        "modal_reserved_usd": round((elapsed + 2) * RATE_RESERVED, 6),
        "modal_upper_usd": round((elapsed + 2) * RATE_UPPER, 6),
        "actual_invoice_usd": None,
        "groq_actual_usd": 0.0,
        "groq_plan_assumption": "User free tier; no paid billing enabled by Vidloom",
        "includes": "Function wall time and 2-second idle allowance; excludes image build/cold start and control calls",
    }
    runtime["active"] = None
    runtime["updated_at"] = now()
    store["runtime"] = runtime
    volume.commit()
    return {"status": job["status"], "job": job}


@app.function(image=image, secrets=[secret], volumes={"/data": volume},
              cpu=(2, 4), memory=(4096, 8192), timeout=1800, max_containers=1,
              scaledown_window=2, retries=0)
def upload_custom_video(video_rel_path: str, title: str, description: str, test: bool = False):
    import time, uuid
    from pathlib import Path
    from automation.cloud_runtime import Recorder, now, upload, RATE_RESERVED, RATE_UPPER

    started = time.monotonic()
    runtime = store.get("runtime", {"jobs": [], "events": [], "active": None})
    cfg = store.get("config", {})
    video = Path("/data") / video_rel_path

    job_id = "v-topgun-" + uuid.uuid4().hex[:8]
    job = {
        "id": job_id,
        "title": title[:100],
        "status": "ready",
        "video_path": str(video),
        "created_at": now(),
        "steps": [],
        "description": description,
    }
    runtime["jobs"].insert(0, job)
    rec = Recorder(store, runtime, job)
    rec.save()

    with rec.step("YouTube upload & schedule"):
        upload(job, video, rec, runtime, store, volume, test=test)
        runtime["last_success_at"] = now()

    elapsed = time.monotonic() - started
    job["elapsed_seconds"] = round(elapsed, 3)
    job["cost"] = {
        "modal_reserved_usd": round((elapsed + 2) * RATE_RESERVED, 6),
        "modal_upper_usd": round((elapsed + 2) * RATE_UPPER, 6),
        "actual_invoice_usd": None,
        "groq_actual_usd": 0.0,
        "groq_plan_assumption": "User free tier; no paid billing enabled by Vidloom",
        "includes": "Function wall time and 2-second idle allowance; excludes image build/cold start and control calls",
    }
    runtime["active"] = None
    runtime["updated_at"] = now()
    store["runtime"] = runtime
    volume.commit()
    return {"status": job["status"], "job": job}

@app.local_entrypoint()
def main(test: bool = False, status: bool = False, render_project: str = "", jack: bool = False, topgun: bool = False):
    import json
    if status:
        from automation.cloud_runtime import public_state
        print(json.dumps(public_state(store), indent=2))
    elif topgun:
        title = "Why Maverick's Canyon Run is the Greatest Stunt in Cinema History"
        desc = "#Shorts #TopGun #TopGunMaverick #TomCruise #Cinema #Film" + chr(10) + chr(10) + "The Navy said the mission was suicide: fly an F-18 at 660 knots through a winding canyon and hit a 3-meter target in under 2 minutes 15 seconds. Every pilot called it impossible. So Maverick stole a jet to prove them wrong."
        print(json.dumps(upload_custom_video.remote("shorts/topgun_maverick_epic_short.mp4", title, desc, test=test), indent=2))
    elif jack:
        print(json.dumps(render_and_upload_project.remote("projects/jack_sparrow_entrance", test=test), indent=2))
    elif render_project:
        print(json.dumps(render_and_upload_project.remote(render_project, test=test), indent=2))
    else:
        print(json.dumps(cycle.remote(test=test), indent=2))

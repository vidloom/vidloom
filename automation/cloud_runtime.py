"""Durable orchestration, verified publishing and honest cost accounting."""
from __future__ import annotations
import copy
import hashlib
import json
import os
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

DEFAULT_CONFIG = {
    "enabled": True, "publishing_enabled": True, "videos_per_day": 3,
    "publish_times_utc": ["01:00", "13:00", "18:00"], "buffer_target": 6,
    "monthly_budget_usd": 30, "budget_margin_usd": 2, "max_daily_creations": 6,
    "genre": "Cinema scene breakdowns", "voice": "am_michael", "language": "en",
    "schedule_rationale": "Three test windows for Americas, Europe and Asia. Review channel analytics after 28 days; timing does not guarantee audience geography or revenue.",
}
# Upper resource envelope at published rates, excluding cold start/control calls.
RATE_UPPER = 4 * 0.0000131 + 8 * 0.00000222
RATE_RESERVED = 2 * 0.0000131 + 4 * 0.00000222

def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

def validate_settings(body, current):
    incoming = body.get("autopilot", body) if isinstance(body, dict) else {}
    body = {
        "enabled": incoming.get("creator_enabled", incoming.get("enabled", current.get("enabled", True))),
        "publishing_enabled": incoming.get("publishing_enabled", current.get("publishing_enabled", True)),
        "videos_per_day": incoming.get("videos_per_day", current.get("videos_per_day", 3)),
        "buffer_target": incoming.get("finished_buffer_target", incoming.get("buffer_target", current.get("buffer_target", 6))),
        "monthly_budget_usd": incoming.get("monthly_modal_budget_usd", incoming.get("monthly_budget_usd", current.get("monthly_budget_usd", 30))),
    }
    cfg = copy.deepcopy(current)
    for key in ("enabled", "publishing_enabled"):
        if key in body:
            if type(body[key]) is not bool: raise ValueError(f"{key} must be a boolean")
            cfg[key] = body[key]
    for key, lo, hi in (("videos_per_day", 1, 5), ("buffer_target", 1, 10), ("monthly_budget_usd", 1, 30)):
        if key in body:
            if isinstance(body[key], bool): raise ValueError("Invalid number")
            value = float(body[key])
            if not lo <= value <= hi or (key != "monthly_budget_usd" and value != int(value)):
                raise ValueError(f"{key} must be between {lo} and {hi}")
            cfg[key] = value if key == "monthly_budget_usd" else int(value)
    if "videos_per_day" in body:
        cfg["publish_times_utc"] = {1:["18:00"], 2:["01:00","17:00"], 3:["01:00","13:00","18:00"], 4:["01:00","07:00","13:00","19:00"], 5:["01:00","06:00","11:00","16:00","21:00"]}[cfg["videos_per_day"]]
    return cfg

def next_slot(config, jobs, after=None):
    after = after or datetime.now(timezone.utc) + timedelta(minutes=30)
    occupied = {j.get("publish_at") for j in jobs if j.get("youtube_id")}
    for day in range(365):
        date = (after + timedelta(days=day)).date()
        for value in config["publish_times_utc"]:
            hour, minute = map(int, value.split(":"))
            candidate = datetime(date.year,date.month,date.day,hour,minute,tzinfo=timezone.utc)
            stamp = candidate.isoformat(timespec="seconds").replace("+00:00", "Z")
            if candidate > after and stamp not in occupied: return stamp
    raise RuntimeError("No available publication slot")

def public_state(store):
    cfg = store.get("config", copy.deepcopy(DEFAULT_CONFIG))
    runtime = store.get("runtime", {"jobs": [], "events": [], "active": None})
    jobs = runtime.get("jobs", [])
    month = now()[:7]
    spent = sum(j.get("cost", {}).get("modal_upper_usd", 0) for j in jobs if j.get("created_at", "").startswith(month))
    upcoming = sorted([j for j in jobs if j.get("status") == "scheduled"], key=lambda j:j.get("publish_at", ""))
    counts = {s:sum(j.get("status")==s for j in jobs) for s in ("published","scheduled","ready","failed","blocked")}
    active = runtime.get("active")
    queue = []
    for item in jobs:
        status = item.get("status", "planned")
        progress = {"building":45,"ready":100,"uploading":90,"scheduled":100,"published":100,"failed":0,"blocked":0}.get(status,10)
        queue.append({**item, "origin":"autopilot", "stage":item.get("stage", status), "progress":progress,
                      "scheduled_publish_at":item.get("publish_at")})
    finished = [j for j in queue if j.get("status") in ("ready","scheduled","published")]
    scheduled = [j for j in queue if j.get("status")=="scheduled"]
    attention = [j for j in queue if j.get("status") in ("failed","blocked")]
    total_finished = counts["ready"]+counts["scheduled"]
    events = list(runtime.get("events", []))
    for item in jobs[:20]:
        for step in reversed(item.get("steps", [])):
            events.append({"at":step.get("finished_at") or step.get("started_at"), "level":"success" if step.get("status")=="success" else "error", "message":f"{item.get('title','Video')}: {step.get('name')} ({step.get('seconds',0):.1f}s)"})
    channel = runtime.get("channel", {})
    settings = {"autopilot":{"creator_enabled":cfg["enabled"],"publishing_enabled":cfg["publishing_enabled"],"videos_per_day":cfg["videos_per_day"],"first_publish_time":cfg["publish_times_utc"][0],"timezone":"UTC","publishing_mode":"fully_automatic","automatic_retries":True,"finished_buffer_target":cfg["buffer_target"],"monthly_modal_budget_usd":cfg["monthly_budget_usd"]},
                "content_brain":{"movie_preferences":["licensed open cinema", "clear visual storytelling"],"excluded_movies":[],"prevent_duplicate_scenes":True,"prevent_duplicate_hooks":True},
                "production_rules":{"duration_min_seconds":24,"duration_max_seconds":34,"narration_style":"Connected evidence-bound explanation","subtitle_preset":"Clean kinetic","music_mix":"Source-aware ducking","crop_tracking":"Inspected subject crop"},
                "notifications":{"weekly_summary":False,"upload_failures":False,"copyright_claims":False,"credit_warnings":False,"email":""}}
    return {"generated_at":now(), "channel":{"name":channel.get("title","Vidloom Cinema"),"genre":cfg["genre"],"timezone":"UTC"},
            "system":{"creator_enabled":cfg["enabled"],"publishing_enabled":cfg["publishing_enabled"],"status":"building" if active else ("healthy" if cfg["enabled"] else "paused"),"current_stage":active.get("stage") if active else runtime.get("idle_reason","Waiting for hourly inventory check")},
            "metrics":{"published":counts["published"],"scheduled":counts["scheduled"],"ready":counts["ready"],"needs_attention":counts["failed"]+counts["blocked"]},
            "autopilot":{"mode":"creating" if active else ("paused" if not cfg["enabled"] else "standing_by" if total_finished>=cfg["buffer_target"] else "filling"),"active":1 if active else 0,"finished":total_finished,"target":cfg["buffer_target"],"gap":max(0,cfg["buffer_target"]-total_finished-(1 if active else 0)),"interval_hours":1,"next_action":active.get("stage") if active else runtime.get("idle_reason","Research and produce the next licensed cinema breakdown")},
            "queue":queue,"ideas":[],"finished_videos":finished,"scheduled_videos":scheduled,"attention_videos":attention,
            "schedule":{"timezone":"UTC","days":["monday","tuesday","wednesday","thursday","friday","saturday","sunday"],"publish_time":cfg["publish_times_utc"][0],"videos_per_day":cfg["videos_per_day"],"next_publish_at":upcoming[0].get("publish_at") if upcoming else None},
            "settings":settings,"analytics":{"channel":{"views":int(channel.get("statistics",{}).get("viewCount",0)),"subscribers":int(channel.get("statistics",{}).get("subscriberCount",0))},"weekly":{"views":None,"subscribers_gained":None,"average_percentage_viewed":None},"videos":[{"id":j.get("youtube_id"),"title":j.get("title"),"views":int(j.get("statistics",{}).get("viewCount",0)),"likes":int(j.get("statistics",{}).get("likeCount",0)),"comments":int(j.get("statistics",{}).get("commentCount",0))} for j in jobs if j.get("youtube_id")],"message":"Per-video YouTube statistics sync hourly; retention needs the separate YouTube Analytics scope.","generated_at":runtime.get("updated_at")},
            "costs":{"estimated_spend_usd":round(spent,5),"budget_limit_usd":cfg["monthly_budget_usd"],"remaining_usd":round(max(0,cfg["monthly_budget_usd"]-spent),5),"creation_allowed":spent<cfg["monthly_budget_usd"]-cfg["budget_margin_usd"],"source":"Modal envelope estimate; open a job for measured step timings."},
            "health":{"creator":"active" if cfg["enabled"] else "paused","runner":"online","youtube":"connected" if channel else "not_connected","pipeline":"ready","ai":"configured","queue":"healthy" if not attention else "attention"},
            "events":sorted(events,key=lambda e:e.get("at") or "",reverse=True)[:30],
            "engine":{"provider":"Modal","laptop_required":False,"heartbeat":"Hourly at minute 11","pipeline":"v3 evidence validator, captions, sound mixing, renderer and QC"}}

class Recorder:
    def __init__(self, store, runtime, job):
        self.store,self.runtime,self.job = store,runtime,job
    def save(self):
        self.job["updated_at"] = now()
        self.runtime["updated_at"] = now()
        self.store["runtime"] = self.runtime
    @contextmanager
    def step(self, name):
        record = {"name": name, "started_at": now(), "status":"running"}
        self.job.setdefault("steps", []).append(record)
        self.job["stage"] = name
        self.runtime["active"] = {"id":self.job["id"], "stage":name, "heartbeat":time.time()}
        self.save()
        start = time.monotonic()
        try:
            yield
            record["status"] = "success"
        except Exception:
            record["status"] = "failed"
            raise
        finally:
            record["seconds"] = round(time.monotonic()-start, 3)
            record["finished_at"] = now()
            self.save()

def youtube_client():
    from googleapiclient.discovery import build
    from automation.youtube_upload import _credentials
    return build("youtube","v3",credentials=_credentials(),cache_discovery=False)

def sync_status(runtime, youtube):
    ids = [j["youtube_id"] for j in runtime["jobs"] if j.get("youtube_id")]
    for offset in range(0,len(ids),50):
        response = youtube.videos().list(part="status,statistics,processingDetails",id=",".join(ids[offset:offset+50])).execute()
        lookup = {v["id"]:v for v in response.get("items",[])}
        for job in runtime["jobs"]:
            if job.get("youtube_id") not in lookup: continue
            value = lookup[job["youtube_id"]]
            job["youtube_status"] = value.get("status",{})
            job["statistics"] = value.get("statistics",{})
            job["processing"] = value.get("processingDetails",{})
            status = job["youtube_status"]
            if status.get("privacyStatus") == "public": job["status"]="published"
            elif status.get("publishAt"): job["status"]="scheduled"
            elif status.get("privacyStatus") == "private":
                job["status"]="blocked"
                job["last_error"]="YouTube kept this upload private without a publish time. Check the channel/API publishing restrictions."

def upload(job, video, recorder, runtime, store, volume, test=False):
    from googleapiclient.http import MediaFileUpload
    cfg = store.get("config",DEFAULT_CONFIG)
    if not cfg.get("publishing_enabled",True) or not cfg.get("enabled",True):
        job["status"]="ready"; return
    if job.get("youtube_id"): return
    # Persist intent before network I/O. An interrupted ambiguous upload is
    # reconciled via a unique description marker; never blindly reinsert it.
    marker = "Vidloom production: " + job["id"]
    with recorder.step("YouTube upload"):
        yt = youtube_client()
        publish_at = None if test else next_slot(cfg,runtime["jobs"])
        job.update(status="uploading",publish_at=publish_at,upload_intent_at=now())
        recorder.save(); volume.commit()
        status = {"privacyStatus":"public" if test else "private", "selfDeclaredMadeForKids":False, "containsSyntheticMedia":False}
        if publish_at: status["publishAt"]=publish_at
        description = job["description"] + "\n\n" + marker
        request = yt.videos().insert(part="snippet,status",notifySubscribers=False,
            body={"snippet":{"title":job["title"][:100],"description":description[:5000],"categoryId":"24","defaultLanguage":"en","tags":["film analysis","visual storytelling","Shorts"]},"status":status},
            media_body=MediaFileUpload(str(video),mimetype="video/mp4",chunksize=8*1024*1024,resumable=True))
        result = None
        for attempt in range(8):
            try:
                while result is None:
                    _,result = request.next_chunk(num_retries=3)
                break
            except Exception as error:
                if getattr(getattr(error,"resp",None),"status",0) not in (500,502,503,504): raise
                time.sleep(min(2**attempt,30))
        if result is None: raise RuntimeError("Resumable upload did not return a video ID")
        job.update(youtube_id=result["id"], youtube_url="https://youtu.be/"+result["id"], status="uploaded", youtube_status=result.get("status",{}))
        recorder.save(); volume.commit()
    with recorder.step("Verify YouTube processing and visibility"):
        for attempt in range(18):
            sync_status(runtime,yt); recorder.save()
            processing=job.get("processing",{}).get("processingStatus")
            if processing in ("failed","terminated"): raise RuntimeError("YouTube processing failed: "+processing)
            if processing=="succeeded": break
            time.sleep(5)
        if job["status"]=="blocked": raise RuntimeError(job["last_error"])

def reconcile_upload(job, yt, runtime):
    channel=yt.channels().list(part="contentDetails",mine=True).execute()["items"][0]
    pid=channel["contentDetails"]["relatedPlaylists"]["uploads"]
    ids=[v["contentDetails"]["videoId"] for v in yt.playlistItems().list(part="contentDetails",playlistId=pid,maxResults=50).execute().get("items",[])]
    if ids:
        for v in yt.videos().list(part="snippet,status",id=",".join(ids)).execute().get("items",[]):
            if "Vidloom production: "+job["id"] in v.get("snippet",{}).get("description",""):
                job.update(youtube_id=v["id"],youtube_url="https://youtu.be/"+v["id"],status="uploaded")
                sync_status(runtime,yt); return
    job.update(status="blocked",last_error="Upload interrupted without a confirmed ID. Reconciliation found no matching video; retry is held to avoid duplicate publication.")

def run_cycle(store, volume, *, test=False, request=""):
    from automation.cloud_creator import build_video
    started=time.monotonic()
    cfg=store.get("config",copy.deepcopy(DEFAULT_CONFIG)); store["config"]=cfg
    runtime=store.get("runtime",{"jobs":[],"events":[],"active":None})
    if not cfg["enabled"]: return {"status":"paused"}
    # No jobs or media from the old local queue are imported.
    job=None
    try:
        yt=youtube_client()
        channel=yt.channels().list(part="snippet,statistics",mine=True).execute().get("items",[])
        if not channel: raise RuntimeError("Authorized Google account has no YouTube channel")
        runtime["channel"]={"id":channel[0]["id"],"title":channel[0]["snippet"]["title"],"statistics":channel[0].get("statistics",{})}
        for old in runtime["jobs"]:
            if old.get("status")=="uploading" and not old.get("youtube_id"): reconcile_upload(old,yt,runtime)
            if old.get("status")=="building": old.update(status="failed",last_error="Previous cloud worker interrupted; source retained for recovery.")
        sync_status(runtime,yt)
        store["runtime"]=runtime
        # Release an already rendered video before spending more on generation.
        ready=next((j for j in runtime["jobs"] if j.get("status")=="ready"),None)
        if ready and cfg["publishing_enabled"]:
            job=ready; rec=Recorder(store,runtime,job)
            upload(job,Path(job["video_path"]),rec,runtime,store,volume,test=test)
            return {"status":job["status"],"job":job}
        month=now()[:7]
        spent=sum(j.get("cost",{}).get("modal_upper_usd",0) for j in runtime["jobs"] if j.get("created_at","").startswith(month))
        # Reserve the worst-case 30-minute job envelope before launching it.
        if spent + 1805*RATE_UPPER > cfg["monthly_budget_usd"]-cfg["budget_margin_usd"]:
            runtime["idle_reason"]="Monthly compute budget reserve reached"; return {"status":"budget_hold"}
        today=sum(j.get("created_at","").startswith(now()[:10]) for j in runtime["jobs"])
        finished=sum(j.get("status") in ("scheduled","ready") for j in runtime["jobs"])
        if finished>=cfg["buffer_target"] and not test and not request:
            runtime["idle_reason"]="Finished buffer is full; production resumes when a slot opens"; return {"status":"buffer_full"}
        if today>=cfg["max_daily_creations"] and not test:
            runtime["idle_reason"]="Daily creation limit reached; next cycle will resume tomorrow"; return {"status":"daily_limit"}
        job={"id":"v-"+uuid.uuid4().hex[:12],"title":"Researching a new film scene","status":"building","created_at":now(),"steps":[],"request":request}
        runtime["jobs"].insert(0,job); runtime["idle_reason"]=None
        rec=Recorder(store,runtime,job); rec.save()
        video=build_video(job,rec,runtime,cfg,volume)
        job.update(status="ready",video_path=str(video)); rec.save(); volume.commit()
        upload(job,video,rec,runtime,store,volume,test=test)
        runtime["last_success_at"]=now()
        return {"status":job["status"],"job":job}
    except Exception as error:
        message=str(error)[:500]
        runtime["last_error"]=message
        if job:
            job["last_error"]=message
            if job.get("status") not in ("uploading","blocked","published","scheduled"): job["status"]="failed"
        runtime["events"].insert(0,{"at":now(),"level":"error","message":message})
        return {"status":"failed","error":message,"job":job}
    finally:
        elapsed=time.monotonic()-started
        if job:
            job["elapsed_seconds"]=round(elapsed,3)
            job["cost"]={"modal_reserved_usd":round((elapsed+2)*RATE_RESERVED,6),"modal_upper_usd":round((elapsed+2)*RATE_UPPER,6),"actual_invoice_usd":None,
                         "groq_actual_usd":None,"groq_plan_assumption":"User free tier; no paid billing enabled by Vidloom", "includes":"Function wall time and 2-second idle allowance; excludes image build/cold start and control calls"}
        runtime["active"]=None; runtime["updated_at"]=now()
        runtime["events"]=runtime.get("events",[])[:60]
        store["runtime"]=runtime
        Path("/data/reports").mkdir(parents=True,exist_ok=True)
        if job: Path("/data/reports",job["id"]+".json").write_text(json.dumps(job,indent=2))
        volume.commit()

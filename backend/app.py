from fastapi import FastAPI, Query, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, HttpUrl
from typing import Optional, Dict, Any, List
import os
import sys
import uuid
import threading
import time

# Ensure parent directory is in path to import downloader engine
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from downloader.detector import PlatformDetector, Platform
from downloader.universal_extractor import UniversalExtractor
from downloader.universal_downloader import UniversalDownloader

app = FastAPI(
    title="Universal Video Downloader API",
    description="Backend API powering Web and Mobile (Capacitor) apps with real-time platform auto-detection and media extraction.",
    version="1.0.0"
)

# Enable CORS for Web and Mobile WebView clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

extractor = UniversalExtractor()
universal_downloader = UniversalDownloader()

# Cache directory for web downloads
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")
os.makedirs(CACHE_DIR, exist_ok=True)

# Active background download jobs tracker
# job_id -> { status, percent, speed, eta, file_path, filename, error }
jobs: Dict[str, Dict[str, Any]] = {}

# Serve static files for web/mobile client
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


class ExtractRequest(BaseModel):
    url: str
    target_store: Optional[str] = "web"  # "web", "playstore", or "direct_apk"


class DownloadJobRequest(BaseModel):
    url: str
    format_id: Optional[str] = "bestvideo+bestaudio/best"
    ext: Optional[str] = "mp4"
    title: Optional[str] = "video"


@app.get("/")
def serve_index():
    index_file = os.path.join(static_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {
        "status": "online",
        "service": "Universal Video Downloader API",
        "supported_platforms": [p.value for p in Platform]
    }


@app.get("/api/detect")
def detect_url(url: str = Query(..., description="The media URL to analyze in real-time")):
    """
    Real-time URL auto-detection endpoint.
    Returns brand badges, platform name, content type hint, and color codes.
    """
    detection = PlatformDetector.detect(url)
    return detection


@app.post("/api/extract")
def extract_media(payload: ExtractRequest):
    """
    Extracts video formats, resolutions, thumbnail, author, duration,
    or drama series episode list.
    """
    url = payload.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL cannot be empty.")

    detection = PlatformDetector.detect(url)

    # Google Play Store Compliance Policy Enforcement
    if payload.target_store == "playstore" and detection["platform"] == Platform.YOUTUBE:
        raise HTTPException(
            status_code=403,
            detail="In accordance with Google Play Store Developer Policy (Section 4.4), YouTube downloads are disabled on the Play Store release. Please use our direct Web version or APK."
        )

    try:
        result = extractor.extract(url)
        if not result.get("success"):
            raise HTTPException(status_code=422, detail=result.get("error", "Failed to extract media."))
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/download/start")
def start_download_job(payload: DownloadJobRequest):
    """
    Initiates a background download and muxing job on the server.
    Returns a job_id for real-time progress polling.
    """
    job_id = uuid.uuid4().hex[:12]
    safe_title = UniversalDownloader.sanitize_filename(payload.title or "video")

    jobs[job_id] = {
        "status": "downloading",
        "percent": 0.0,
        "speed": "",
        "eta": "",
        "file_path": None,
        "filename": f"{safe_title}.{payload.ext}",
        "error": None,
        "created_at": time.time()
    }

    def _worker():
        try:
            dest_dir = os.path.join(CACHE_DIR, job_id)
            os.makedirs(dest_dir, exist_ok=True)

            def progress_hook(pct, dl_str, spd, eta):
                if job_id in jobs:
                    jobs[job_id]["percent"] = round(pct, 1)
                    jobs[job_id]["speed"] = spd
                    jobs[job_id]["eta"] = eta

            final_file = universal_downloader.download_sync(
                url=payload.url,
                dest_folder=dest_dir,
                format_id=payload.format_id or "bestvideo+bestaudio/best",
                target_ext=payload.ext or "mp4",
                progress_callback=progress_hook
            )

            if job_id in jobs:
                jobs[job_id]["status"] = "ready"
                jobs[job_id]["percent"] = 100.0
                jobs[job_id]["file_path"] = final_file
                jobs[job_id]["filename"] = os.path.basename(final_file)
        except Exception as e:
            if job_id in jobs:
                jobs[job_id]["status"] = "failed"
                jobs[job_id]["error"] = str(e)

    threading.Thread(target=_worker, daemon=True).start()

    return {"job_id": job_id, "status": "downloading"}


@app.get("/api/download/status")
def get_download_status(job_id: str = Query(...)):
    """
    Checks the progress of an ongoing download job.
    """
    if job_id not in jobs:
        # Fallback to cache disk check
        job_dir = os.path.join(CACHE_DIR, job_id)
        if os.path.exists(job_dir):
            files = [os.path.join(job_dir, f) for f in os.listdir(job_dir) if not f.endswith('.part') and not f.endswith('.ytdl')]
            if files:
                return {"status": "ready", "percent": 100.0, "speed": "", "eta": "", "error": None}
        raise HTTPException(status_code=404, detail="Job not found.")

    job = jobs[job_id]
    return {
        "status": job["status"],
        "percent": job["percent"],
        "speed": job["speed"],
        "eta": job["eta"],
        "error": job["error"]
    }


@app.get("/api/download/file")
def get_downloaded_file(job_id: str = Query(...)):
    """
    Serves the prepared video or audio file with RFC 5987 UTF-8 headers,
    prompting the browser to immediately save it to the user's Downloads folder.
    """
    file_path = None
    filename = None

    if job_id in jobs:
        job = jobs[job_id]
        if job.get("status") == "ready" and job.get("file_path") and os.path.exists(job["file_path"]):
            file_path = job["file_path"]
            filename = job.get("filename")

    if not file_path:
        # Fallback check on cache folder
        job_dir = os.path.join(CACHE_DIR, job_id)
        if os.path.exists(job_dir):
            files = [
                os.path.join(job_dir, f) for f in os.listdir(job_dir)
                if not f.endswith('.part') and not f.endswith('.ytdl') and not f.endswith('.temp')
            ]
            if files:
                file_path = files[0]
                filename = os.path.basename(file_path)

    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File is not ready or has expired.")

    if not filename:
        filename = os.path.basename(file_path)

    # Let Starlette's FileResponse automatically format the RFC 5987 / UTF-8 header!
    # DO NOT pass a manual Content-Disposition header in the `headers` argument!
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/octet-stream"
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)

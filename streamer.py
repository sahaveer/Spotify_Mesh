import os
import re
import urllib.parse
import pathlib
import hashlib
import shutil
import subprocess
import tempfile
import threading
import time
from typing import Generator, Optional
from fastapi import Request, HTTPException
from fastapi.responses import StreamingResponse, FileResponse

_conversion_slots = threading.BoundedSemaphore(2)
_conversion_jobs = {}
_jobs_lock = threading.Lock()


def compatibility_job(file_path: str, is_video: bool, start: bool = False):
    """Short polling requests let preparation survive a remote proxy timeout."""
    try:
        stat = os.stat(file_path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Media file missing. Check the server drive and rescan.")
    except PermissionError:
        raise HTTPException(status_code=403, detail="The server cannot read this file. Check folder permissions.")
    key = (file_path, stat.st_mtime_ns, stat.st_size, is_video)
    with _jobs_lock:
        for old_key, job in list(_conversion_jobs.items()):
            if job["status"] != "preparing" and time.monotonic() - job["updated"] > 3600:
                del _conversion_jobs[old_key]
        existing = _conversion_jobs.get(key)
        if existing and (not start or existing["status"] in ("preparing", "ready")):
            return {k: v for k, v in existing.items() if k != "updated"}
        if not start:
            return {"status": "idle"}
        if sum(job["status"] == "preparing" for job in _conversion_jobs.values()) >= 2:
            raise HTTPException(status_code=503, detail="The server is preparing other files. Try again shortly.")
        _conversion_jobs[key] = {"status": "preparing", "updated": time.monotonic()}

    def worker():
        try:
            compatible_media(file_path, is_video)
            result = {"status": "ready"}
        except HTTPException as error:
            result = {"status": "failed", "detail": error.detail}
        except Exception:
            result = {"status": "failed", "detail": "The server could not prepare this file. Try VLC."}
        with _jobs_lock:
            _conversion_jobs[key] = {**result, "updated": time.monotonic()}

    threading.Thread(target=worker, daemon=True, name="CompatiblePlayback").start()
    return {"status": "preparing"}

CHUNK_SIZE = 512 * 1024  # 512KB chunks for smooth buffering of audio and 1080p/4K video

def parse_range_header(range_header: str, file_size: int):
    """
    Parses 'Range: bytes=start-end' header and returns (start, end, content_length).
    """
    match = re.fullmatch(r"bytes=(\d*)-(\d*)", range_header.strip())
    if not match:
        return 0, file_size - 1, file_size
    
    start_str, end_str = match.groups()
    if not start_str and end_str:
        start = max(0, file_size - int(end_str))
        end = file_size - 1
    elif start_str:
        start = int(start_str)
        end = min(int(end_str), file_size - 1) if end_str else file_size - 1
    else:
        start, end = file_size, file_size - 1

    if start >= file_size or end >= file_size or start > end:
        raise HTTPException(
            status_code=416,
            detail="Requested Range Not Satisfiable",
            headers={"Content-Range": f"bytes */{file_size}"}
        )

    content_length = end - start + 1
    return start, end, content_length

def file_chunk_generator(file_path: str, start: int, end: int, chunk_size: int = CHUNK_SIZE) -> Generator[bytes, None, None]:
    """Reads a slice of an audio or video file in chunks without loading everything into memory."""
    with open(file_path, "rb") as f:
        f.seek(start)
        remaining = end - start + 1
        while remaining > 0:
            read_size = min(chunk_size, remaining)
            data = f.read(read_size)
            if not data:
                break
            remaining -= len(data)
            yield data

def stream_audio(file_path: str, request: Request, mime_type: str = "audio/mpeg", download_filename: Optional[str] = None) -> StreamingResponse:
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Media file not found")

    try:
        with open(file_path, "rb") as source:
            file_size = os.fstat(source.fileno()).st_size
    except PermissionError:
        raise HTTPException(status_code=403, detail="The server cannot read this media file. Check its folder permissions.")
    if not file_size:
        raise HTTPException(status_code=422, detail="This media file is empty.")
    range_header = request.headers.get("range")
    is_download = request.query_params.get("download") == "true" or download_filename is not None

    headers = {
        "Accept-Ranges": "bytes",
        "Content-Type": mime_type,
    }

    if is_download:
        safe_name = download_filename or os.path.basename(file_path)
        encoded_name = urllib.parse.quote(safe_name)
        ascii_fallback = safe_name.encode('ascii', 'ignore').decode('ascii').replace('"', '') or 'media_file'
        headers["Content-Disposition"] = f'attachment; filename="{ascii_fallback}"; filename*=UTF-8\'\'{encoded_name}'

    if range_header:
        start, end, content_length = parse_range_header(range_header, file_size)
        headers.update({
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Content-Length": str(content_length),
        })
        return StreamingResponse(
            file_chunk_generator(file_path, start, end),
            status_code=206,
            headers=headers
        )
    else:
        headers["Content-Length"] = str(file_size)
        return StreamingResponse(
            file_chunk_generator(file_path, 0, file_size - 1),
            status_code=200,
            headers=headers
        )


def compatible_media(file_path: str, is_video: bool):
    """Cache a browser-compatible copy; never modify the original media file."""
    import config
    try:
        with open(file_path, "rb") as source:
            stat = os.fstat(source.fileno())
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Media file missing. Check the server drive and rescan the library.")
    except PermissionError:
        raise HTTPException(status_code=403, detail="The server cannot read this file. Check folder permissions.")
    if not stat.st_size:
        raise HTTPException(status_code=422, detail="This media file is empty.")
    key = hashlib.sha256(f"v1:{file_path}:{stat.st_mtime_ns}:{stat.st_size}:{is_video}".encode()).hexdigest()
    cache = config.CACHE_DIR / "playback"
    cache.mkdir(parents=True, exist_ok=True)
    target = cache / (key + (".mp4" if is_video else ".mp3"))
    mime = "video/mp4" if is_video else "audio/mpeg"
    if target.is_file():
        return FileResponse(target, media_type=mime)
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        try:
            import imageio_ffmpeg
            ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            raise HTTPException(status_code=503, detail="Compatible playback needs FFmpeg on the server. Install FFmpeg or use VLC.")
    if not _conversion_slots.acquire(blocking=False):
        raise HTTPException(status_code=503, detail="The server is preparing other videos. Try again shortly or use VLC.")
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(dir=cache, suffix=target.suffix, delete=False) as temp:
            temp_path = pathlib.Path(temp.name)
        command = [ffmpeg, "-nostdin", "-hide_banner", "-loglevel", "error", "-y", "-i", file_path]
        if is_video:
            command += ["-map", "0:v:0", "-map", "0:a:0?", "-sn", "-dn", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2", "-pix_fmt", "yuv420p", "-c:a", "aac", "-ac", "2", "-movflags", "+faststart"]
        else:
            command += ["-map", "0:a:0", "-vn", "-c:a", "libmp3lame", "-b:a", "192k", "-ac", "2"]
        command.append(str(temp_path))
        result = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=300)
        if result.returncode or not temp_path.stat().st_size:
            raise HTTPException(status_code=422, detail="This file could not be converted. It may be damaged or contain no playable media. Try VLC.")
        os.replace(temp_path, target)
        return FileResponse(target, media_type=mime)
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Preparing this file took too long. Try playing the original in VLC.")
    except OSError:
        raise HTTPException(status_code=503, detail="The server could not prepare playback. Check FFmpeg and free cache disk space.")
    finally:
        if temp_path:
            temp_path.unlink(missing_ok=True)
        _conversion_slots.release()

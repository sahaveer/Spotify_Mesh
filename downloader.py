import os
import time
import uuid
import threading
import logging
import pathlib
from typing import Dict, Any, Optional
import yt_dlp

try:
    import imageio_ffmpeg
    FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    FFMPEG_PATH = None

import config
import settings
import scanner

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("downloader")

_download_tasks: Dict[str, Dict[str, Any]] = {}
_lock = threading.Lock()

def get_download_status(task_id: Optional[str] = None) -> Any:
    with _lock:
        if task_id:
            return _download_tasks.get(task_id)
        return list(_download_tasks.values())

def _progress_hook(d: Dict[str, Any], task_id: str):
    with _lock:
        if task_id not in _download_tasks:
            return
        task = _download_tasks[task_id]

        if d.get("status") == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            downloaded = d.get("downloaded_bytes") or 0
            if total > 0:
                percent = round((downloaded / total) * 100, 1)
                task["progress"] = percent
            task["status"] = "downloading"
            task["speed"] = d.get("speed", 0)
            task["eta"] = d.get("eta", 0)

        elif d.get("status") == "finished":
            task["status"] = "processing"
            task["progress"] = 100

def _run_download(task_id: str, url: str, media_format: str, quality: str, target_dir: pathlib.Path, owner_id: str = "host", owner_name: str = "Host"):
    task = _download_tasks[task_id]
    target_dir.mkdir(parents=True, exist_ok=True)
    out_template = str(target_dir / "%(title)s.%(ext)s")

    ydl_opts: Dict[str, Any] = {
        "outtmpl": out_template,
        "quiet": False,
        "no_warnings": False,
        "progress_hooks": [lambda d: _progress_hook(d, task_id)],
        "writethumbnail": True,
    }

    if FFMPEG_PATH and os.path.exists(FFMPEG_PATH):
        ydl_opts["ffmpeg_location"] = FFMPEG_PATH

    if media_format == "audio":
        # Extract audio stream as MP3 with embedded tags and thumbnail
        if FFMPEG_PATH and os.path.exists(FFMPEG_PATH):
            ydl_opts.update({
                "format": "bestaudio/best",
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "192",
                    },
                    {"key": "EmbedThumbnail"},
                    {"key": "FFmpegMetadata"},
                ],
            })
        else:
            ydl_opts.update({
                "format": "bestaudio[ext=m4a]/bestaudio[ext=mp3]/bestaudio/best",
            })
    else:
        # Video download
        if quality == "1080p":
            format_str = "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best"
        elif quality == "720p":
            format_str = "bestvideo[height<=720]+bestaudio/best[height<=720]/best"
        else:
            format_str = "bestvideo+bestaudio/best"

        ydl_opts.update({
            "format": format_str,
            "merge_output_format": "mp4",
        })
        if FFMPEG_PATH and os.path.exists(FFMPEG_PATH):
            ydl_opts["postprocessors"] = [{"key": "FFmpegMetadata"}]

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            raw_title = info.get("title", "Unknown Title")
            
            # Find the actual downloaded file on disk
            downloaded_file = None
            try:
                base_target = ydl.prepare_filename(info)
                # If audio conversion changed extension to mp3
                if media_format == "audio":
                    possible_mp3 = pathlib.Path(base_target).with_suffix(".mp3")
                    if possible_mp3.exists():
                        downloaded_file = possible_mp3
                if not downloaded_file or not downloaded_file.exists():
                    p = pathlib.Path(base_target)
                    if p.exists():
                        downloaded_file = p
            except Exception:
                pass

            # Fallback file search in target_dir if filename differed
            if not downloaded_file or not downloaded_file.exists():
                for f in target_dir.glob("*.*"):
                    if f.is_file() and f.suffix.lower() in config.SUPPORTED_EXTENSIONS:
                        if abs(f.stat().st_mtime - time.time()) < 60:
                            downloaded_file = f
                            break

            song_id = None
            if downloaded_file and downloaded_file.exists():
                media_item = scanner.parse_media_file(
                    downloaded_file,
                    folder_type="music" if media_format == "audio" else "video",
                    owner_id=owner_id,
                    owner_name=owner_name
                )
                if media_item:
                    import database
                    database.upsert_song(media_item)
                    song_id = media_item["id"]
                    raw_title = media_item["title"]
                    artist_name = media_item.get("artist", "")
            else:
                artist_name = ""

            with _lock:
                task["title"] = raw_title
                task["artist"] = artist_name
                task["song_id"] = song_id
                task["status"] = "completed"
                task["progress"] = 100
                task["duration"] = info.get("duration", 0)

        # Rescan full library in background to ensure all indices stay synchronized
        threading.Thread(target=scanner.scan_library, daemon=True).start()

    except Exception as e:
        logger.warning(f"Download with standard opts failed ({e}), trying fallback stream download...")
        try:
            fallback_opts = {
                "outtmpl": out_template,
                "quiet": True,
                "no_warnings": True,
                "progress_hooks": [lambda d: _progress_hook(d, task_id)],
                "format": "bestaudio[ext=m4a]/bestaudio/best" if media_format == "audio" else "best[ext=mp4]/best",
            }
            if FFMPEG_PATH and os.path.exists(FFMPEG_PATH):
                fallback_opts["ffmpeg_location"] = FFMPEG_PATH

            with yt_dlp.YoutubeDL(fallback_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                raw_title = info.get("title", "Unknown Title")
                
                downloaded_file = None
                try:
                    p = pathlib.Path(ydl.prepare_filename(info))
                    if p.exists():
                        downloaded_file = p
                except Exception:
                    pass

                song_id = None
                if downloaded_file and downloaded_file.exists():
                    media_item = scanner.parse_media_file(
                        downloaded_file,
                        folder_type="music" if media_format == "audio" else "video",
                        owner_id=owner_id,
                        owner_name=owner_name
                    )
                    if media_item:
                        import database
                        database.upsert_song(media_item)
                        song_id = media_item["id"]
                        raw_title = media_item["title"]

                with _lock:
                    task["title"] = raw_title
                    task["song_id"] = song_id
                    task["status"] = "completed"
                    task["progress"] = 100

            threading.Thread(target=scanner.scan_library, daemon=True).start()
        except Exception as err:
            logger.error(f"Download task {task_id} failed: {err}")
            with _lock:
                task["status"] = "failed"
                task["error"] = str(err)

def start_download(
    url: str,
    media_format: str = "audio",
    quality: str = "best",
    custom_folder: Optional[str] = None,
    owner_id: str = "host",
    owner_name: str = "Host"
) -> str:
    """
    Enqueues a download task in background and returns task_id.
    """
    task_id = str(uuid.uuid4())
    
    current_settings = settings.load_settings()
    if custom_folder:
        target_dir = pathlib.Path(custom_folder)
    else:
        target_dir = pathlib.Path(current_settings.get("download_dir", str(config.DEFAULT_MUSIC_DIR)))

    with _lock:
        _download_tasks[task_id] = {
            "id": task_id,
            "url": url,
            "title": "Fetching metadata...",
            "format": media_format,
            "quality": quality,
            "owner_id": owner_id,
            "owner_name": owner_name,
            "status": "pending",
            "progress": 0,
            "target_dir": str(target_dir),
            "error": None
        }

    thread = threading.Thread(
        target=_run_download,
        args=(task_id, url, media_format, quality, target_dir, owner_id, owner_name),
        daemon=True
    )
    thread.start()
    return task_id

import os
import re
import time
import uuid
import shutil
import threading
import logging
import pathlib
import json
import urllib.request
import urllib.parse
from typing import Dict, Any, Optional, Tuple
import yt_dlp

# Detect FFmpeg: prioritize system ffmpeg (e.g. Linux /usr/bin/ffmpeg or Windows PATH)
FFMPEG_PATH = shutil.which("ffmpeg")
if not FFMPEG_PATH:
    try:
        import imageio_ffmpeg
        FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        FFMPEG_PATH = None

# Detect Node.js: essential for solving modern YouTube JS challenges (n-sig, bot-check)
NODE_PATH = shutil.which("node")
if not NODE_PATH:
    common_node_paths = [
        r"C:\Program Files\nodejs\node.exe",
        r"C:\Program Files (x86)\nodejs\node.exe",
        os.path.expanduser(r"~\AppData\Roaming\nvm\default\node.exe"),
        "/usr/bin/node",
        "/usr/local/bin/node",
        "/data/data/com.termux/files/usr/bin/node",
    ]
    for np in common_node_paths:
        if os.path.exists(np):
            NODE_PATH = np
            break

import config
import settings
import scanner

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("downloader")

_download_tasks: Dict[str, Dict[str, Any]] = {}
_lock = threading.Lock()

def _resolve_media_url(raw_input: str) -> Tuple[str, Optional[str]]:
    """
    Resolves input into a yt-dlp compatible URL or search query.
    Handles:
    - Spotify URLs: Scrapes public oEmbed / title tag and converts to ytsearch1:{artist} {track}
    - Plain text search queries: Automatically prefixes with ytsearch1:
    - Standard URLs (YouTube, SoundCloud, TikTok, Vimeo, etc.): Left intact
    """
    text = raw_input.strip()
    if not text:
        return text, None

    # Case 1: Plain text search query (no http scheme)
    if not text.startswith(("http://", "https://")):
        return f"ytsearch1:{text}", text

    # Case 2: Spotify link (Spotify audio files have DRM; resolve to high-quality audio search)
    if "spotify.com" in text or text.startswith("spotify:"):
        clean_url = text.split("?")[0]
        resolved_title = None
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"}

        # Attempt 1: Fetch public Spotify embed page (contains pristine unauthenticated JSON metadata)
        try:
            parts = clean_url.rstrip("/").split("/")
            if len(parts) >= 2:
                media_type = parts[-2] # e.g. track, album, playlist
                media_id = parts[-1]
                embed_url = f"https://open.spotify.com/embed/{media_type}/{media_id}"
                req = urllib.request.Request(embed_url, headers=headers)
                with urllib.request.urlopen(req, timeout=5) as resp:
                    html = resp.read().decode("utf-8", errors="ignore")
                    artists = re.findall(r'\"artists\":\[\{\"name\":\"([^\"]+)\"', html)
                    titles = re.findall(r'\"name\":\"([^\"]+)\"', html)
                    artist = artists[0].strip() if artists else ""
                    title = titles[0].strip() if titles else ""
                    if title and artist and "Spotify" not in artist and "Web Player" not in title:
                        resolved_title = f"{artist} - {title}"
                    elif title and "Spotify" not in title and "Web Player" not in title:
                        resolved_title = title
        except Exception as e:
            logger.debug(f"Spotify embed metadata fetch failed: {e}")

        # Attempt 2: Spotify public oEmbed endpoint
        if not resolved_title:
            try:
                oembed_url = f"https://open.spotify.com/oembed?url={urllib.parse.quote(clean_url)}"
                req = urllib.request.Request(oembed_url, headers=headers)
                with urllib.request.urlopen(req, timeout=5) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    raw_title = data.get("title", "").strip()
                    if raw_title and "Spotify" not in raw_title and "Web Player" not in raw_title:
                        resolved_title = raw_title
            except Exception as e:
                logger.debug(f"Spotify oEmbed fetch failed: {e}")

        # Attempt 3: Scrape main webpage title
        if not resolved_title:
            try:
                req = urllib.request.Request(clean_url, headers=headers)
                with urllib.request.urlopen(req, timeout=5) as resp:
                    html = resp.read().decode("utf-8", errors="ignore")
                    m = re.search(r"<title>([^<]+)</title>", html)
                    if m:
                        t = m.group(1).replace(" | Spotify", "").strip()
                        for sep in [" - song and lyrics by ", " - song by ", " - single by ", " - album by ", " - track by "]:
                            if sep in t:
                                song, artist = t.split(sep, 1)
                                resolved_title = f"{artist.strip()} - {song.strip()}"
                                break
                        if not resolved_title and t and "Spotify" not in t and "Web Player" not in t:
                            resolved_title = t
            except Exception as e:
                logger.debug(f"Spotify webpage title scrape failed: {e}")

        if resolved_title:
            logger.info(f"Resolved Spotify link '{clean_url}' -> search '{resolved_title}'")
            return f"ytsearch1:{resolved_title}", resolved_title
        else:
            fallback_query = clean_url.rstrip("/").split("/")[-1]
            return f"ytsearch1:{fallback_query}", fallback_query

    # Case 3: Standard direct media link (YouTube, Vimeo, etc.)
    return text, None

def get_download_status(task_id: Optional[str] = None) -> Any:
    with _lock:
        if task_id:
            return _download_tasks.get(task_id)
        return list(_download_tasks.values())

def get_download_file(task_id: str) -> Optional[pathlib.Path]:
    with _lock:
        task = _download_tasks.get(task_id)
        if not task:
            return None
        fpath = task.get("file_path")
        if fpath:
            p = pathlib.Path(fpath)
            if p.exists():
                return p
        # Check target_dir if file_path wasn't stored
        tdir = task.get("target_dir")
        if tdir:
            p_tdir = pathlib.Path(tdir)
            if p_tdir.exists():
                for f in p_tdir.glob("*.*"):
                    if f.is_file() and f.suffix.lower() in config.SUPPORTED_EXTENSIONS:
                        return f
    return None

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

def _run_download(
    task_id: str,
    raw_url: str,
    media_format: str,
    quality: str,
    target_dir: pathlib.Path,
    destination: str = "server",
    owner_id: str = "host",
    owner_name: str = "Host"
):
    task = _download_tasks[task_id]
    target_dir.mkdir(parents=True, exist_ok=True)
    out_template = str(target_dir / "%(title)s.%(ext)s")

    # Resolve URL (e.g. Spotify DRM -> YouTube search, plain query -> ytsearch1)
    target_url, resolved_hint = _resolve_media_url(raw_url)
    if resolved_hint:
        with _lock:
            task["title"] = resolved_hint

    # Base configuration for yt-dlp
    ydl_opts: Dict[str, Any] = {
        "outtmpl": out_template,
        "quiet": False,
        "no_warnings": False,
        "progress_hooks": [lambda d: _progress_hook(d, task_id)],
        "writethumbnail": True,
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    }

    if FFMPEG_PATH and os.path.exists(FFMPEG_PATH):
        ydl_opts["ffmpeg_location"] = FFMPEG_PATH

    if NODE_PATH and os.path.exists(NODE_PATH):
        ydl_opts["js_runtimes"] = {"node": {"path": NODE_PATH}}

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

    def _locate_file(ydl_instance, entry_dict) -> Optional[pathlib.Path]:
        """Locates the final downloaded media file on disk."""
        try:
            base_target = ydl_instance.prepare_filename(entry_dict)
            p_base = pathlib.Path(base_target)
            if media_format == "audio":
                for ext in [".mp3", ".m4a", ".opus", ".flac", ".ogg", ".webm"]:
                    candidate = p_base.with_suffix(ext)
                    if candidate.exists():
                        return candidate
            else:
                for ext in [".mp4", ".mkv", ".webm"]:
                    candidate = p_base.with_suffix(ext)
                    if candidate.exists():
                        return candidate
            if p_base.exists():
                return p_base
        except Exception:
            pass

        # Fallback: scan target_dir for the most recently created supported file
        candidates = sorted(
            [f for f in target_dir.glob("*.*") if f.is_file() and f.suffix.lower() in config.SUPPORTED_EXTENSIONS],
            key=lambda f: f.stat().st_mtime,
            reverse=True
        )
        if candidates and (time.time() - candidates[0].stat().st_mtime < 180):
            return candidates[0]
        return None

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(target_url, download=True)
            
            # Unpack playlist / search result dict if needed
            if info and "entries" in info and info["entries"]:
                entries = list(info["entries"])
                entry = entries[0] if entries else info
            else:
                entry = info or {}

            raw_title = entry.get("title") or resolved_hint or "Downloaded Media"
            artist_name = entry.get("artist") or entry.get("uploader") or ""
            downloaded_file = _locate_file(ydl, entry)

            song_id = None
            if downloaded_file and downloaded_file.exists():
                if destination == "server":
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
                    raw_title = downloaded_file.stem

            with _lock:
                task["title"] = raw_title
                task["artist"] = artist_name
                task["song_id"] = song_id
                task["file_path"] = str(downloaded_file.resolve()) if downloaded_file else None
                task["download_url"] = f"/api/downloads/{task_id}/file" if destination == "client" else (f"/api/stream/{song_id}?download=true" if song_id else None)
                task["status"] = "completed"
                task["progress"] = 100
                task["duration"] = entry.get("duration", 0)
                task["error"] = None

        if destination == "server":
            threading.Thread(target=scanner.scan_library, daemon=True).start()

    except Exception as e:
        logger.warning(f"Download with standard opts failed ({e}), attempting fallback stream download...")
        try:
            fallback_opts: Dict[str, Any] = {
                "outtmpl": out_template,
                "quiet": True,
                "no_warnings": True,
                "progress_hooks": [lambda d: _progress_hook(d, task_id)],
                "format": "bestaudio[ext=m4a]/bestaudio/best" if media_format == "audio" else "best[ext=mp4]/best",
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            }
            if FFMPEG_PATH and os.path.exists(FFMPEG_PATH):
                fallback_opts["ffmpeg_location"] = FFMPEG_PATH
            if NODE_PATH and os.path.exists(NODE_PATH):
                fallback_opts["js_runtimes"] = {"node": {"path": NODE_PATH}}

            with yt_dlp.YoutubeDL(fallback_opts) as ydl:
                info = ydl.extract_info(target_url, download=True)
                
                if info and "entries" in info and info["entries"]:
                    entries = list(info["entries"])
                    entry = entries[0] if entries else info
                else:
                    entry = info or {}

                raw_title = entry.get("title") or resolved_hint or "Downloaded Media"
                artist_name = entry.get("artist") or entry.get("uploader") or ""
                downloaded_file = _locate_file(ydl, entry)

                song_id = None
                if downloaded_file and downloaded_file.exists():
                    if destination == "server":
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
                        raw_title = downloaded_file.stem

                with _lock:
                    task["title"] = raw_title
                    task["artist"] = artist_name
                    task["song_id"] = song_id
                    task["file_path"] = str(downloaded_file.resolve()) if downloaded_file else None
                    task["download_url"] = f"/api/downloads/{task_id}/file" if destination == "client" else (f"/api/stream/{song_id}?download=true" if song_id else None)
                    task["status"] = "completed"
                    task["progress"] = 100
                    task["duration"] = entry.get("duration", 0)
                    task["error"] = None

            if destination == "server":
                threading.Thread(target=scanner.scan_library, daemon=True).start()

        except Exception as err:
            logger.error(f"Download task {task_id} failed: {err}")
            clean_err = str(err)
            if "DRM" in clean_err:
                clean_err = "DRM protected stream. Try searching by song title."
            elif "Sign in to confirm" in clean_err:
                clean_err = "Platform bot challenge detected. Please try again in a few moments."
            elif "403" in clean_err:
                clean_err = "Access forbidden by media host (HTTP 403). Stream may be geo-restricted."
            
            with _lock:
                task["status"] = "failed"
                task["error"] = clean_err
                if task["title"] == "Fetching metadata...":
                    task["title"] = resolved_hint or raw_url.split("?")[0].split("/")[-1] or "Download Failed"

def start_download(
    url: str,
    media_format: str = "audio",
    quality: str = "best",
    destination: str = "server",
    custom_folder: Optional[str] = None,
    owner_id: str = "host",
    owner_name: str = "Host"
) -> str:
    """
    Enqueues a download task in background and returns task_id.
    destination: "server" (saves to host media library) or "client" (saves to staging for direct browser download)
    """
    task_id = str(uuid.uuid4())
    
    current_settings = settings.load_settings()
    if destination == "client":
        target_dir = config.STAGING_DIR / f"client_{task_id}"
    elif custom_folder:
        target_dir = pathlib.Path(custom_folder)
    else:
        target_dir = settings.get_target_upload_folder(media_type="video" if media_format == "video" else "audio")

    with _lock:
        _download_tasks[task_id] = {
            "id": task_id,
            "url": url,
            "title": "Fetching metadata...",
            "format": media_format,
            "quality": quality,
            "destination": destination,
            "owner_id": owner_id,
            "owner_name": owner_name,
            "status": "pending",
            "progress": 0,
            "target_dir": str(target_dir),
            "error": None
        }

    thread = threading.Thread(
        target=_run_download,
        args=(task_id, url, media_format, quality, target_dir, destination, owner_id, owner_name),
        daemon=True
    )
    thread.start()
    return task_id

def clear_downloads() -> None:
    """Removes completed, failed, or cancelled download tasks from the queue."""
    with _lock:
        global _download_tasks
        _download_tasks = {
            tid: t for tid, t in _download_tasks.items()
            if t.get("status") in ("downloading", "pending", "processing")
        }



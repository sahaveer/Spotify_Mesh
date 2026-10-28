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
import sys
import subprocess
import signal
import importlib.util
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


def _youtube_runtime():
    if importlib.util.find_spec("yt_dlp_ejs") is None:
        raise RuntimeError('YouTube support is incomplete. On the server, run: python -m pip install -U "yt-dlp[default]"')
    for name, executable, minimum in (("deno", shutil.which("deno"), (2, 3)), ("node", NODE_PATH, (22, 0))):
        if not executable:
            continue
        try:
            result = subprocess.run([executable, "--version"], capture_output=True, text=True, timeout=5)
            match = re.search(r"(\d+)\.(\d+)", result.stdout)
            if result.returncode == 0 and match and tuple(map(int, match.groups())) >= minimum:
                return {name: {"path": executable}}
        except (OSError, subprocess.TimeoutExpired):
            continue
    raise RuntimeError("YouTube needs a supported JavaScript runtime on the server. Install Node.js 22+ or Deno 2.3+ and restart MediaPlayer.")

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
        if task.get("status") != "completed":
            return None
        fpath = task.get("file_path")
        if fpath:
            p = pathlib.Path(fpath)
            if p.exists():
                return p
    return None

def _progress_hook(d: Dict[str, Any], task_id: str):
    with _lock:
        if task_id not in _download_tasks:
            return
        task = _download_tasks[task_id]
        info = d.get('info_dict') or {}
        if info.get('title'):
            task['title'] = info['title']

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

def _perform_download(
    task_id: str,
    raw_url: str,
    media_format: str,
    quality: str,
    target_dir: pathlib.Path,
    destination: str = "server",
    owner_id: str = "host",
    owner_name: str = "Host",
    cookies_browser: Optional[str] = None
):
    task = _download_tasks[task_id]
    target_dir.mkdir(parents=True, exist_ok=True)
    out_template = str(target_dir / "%(title).100B [%(id)s].%(ext)s")

    # Resolve URL (e.g. Spotify DRM -> YouTube search, plain query -> ytsearch1)
    target_url, resolved_hint = _resolve_media_url(raw_url)
    hostname = (urllib.parse.urlparse(target_url).hostname or "").lower()
    is_youtube = target_url.startswith("ytsearch") or hostname == "youtu.be" or hostname == "youtube.com" or hostname.endswith(".youtube.com")
    youtube_runtime = _youtube_runtime() if is_youtube else None
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
        "socket_timeout": 20,
        "retries": 2,
        "extractor_retries": 2,
        "fragment_retries": 2,
        "noplaylist": True,
        "playlistend": 1,
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    }

    # Browser cookies: unlocks login-gated Instagram reels/posts, age gates & bypasses bot checks
    if cookies_browser and str(cookies_browser).strip().lower() not in ("none", "off", "disabled", "false", ""):
        ydl_opts["cookiesfrombrowser"] = (str(cookies_browser).strip().lower(),)

    if FFMPEG_PATH and os.path.exists(FFMPEG_PATH):
        ydl_opts["ffmpeg_location"] = FFMPEG_PATH

    if NODE_PATH and os.path.exists(NODE_PATH):
        ydl_opts["js_runtimes"] = {"node": {"path": NODE_PATH}}
    if youtube_runtime:
        ydl_opts["js_runtimes"] = youtube_runtime

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

        limit = "[height<=1080]" if quality == "1080p" else "[height<=720]" if quality == "720p" else ""
        if FFMPEG_PATH and os.path.exists(FFMPEG_PATH):
            format_str = f"bestvideo[ext=mp4][vcodec^=avc1]{limit}+bestaudio[ext=m4a]/best[ext=mp4]{limit}/" + format_str
        else:
            format_str = f"best[ext=mp4]{limit}/best{limit}"

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

        # Never guess from other files in the shared library.
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
            if not downloaded_file:
                raise RuntimeError("The downloader returned no completed media file.")

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
                "socket_timeout": 20,
                "retries": 1,
                "extractor_retries": 1,
                "fragment_retries": 1,
                "noplaylist": True,
                "playlistend": 1,
                "no_warnings": True,
                "progress_hooks": [lambda d: _progress_hook(d, task_id)],
                "format": "bestaudio[ext=m4a]/bestaudio/best" if media_format == "audio" else "best[ext=mp4]/best",
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            }
            if FFMPEG_PATH and os.path.exists(FFMPEG_PATH):
                fallback_opts["ffmpeg_location"] = FFMPEG_PATH
            if NODE_PATH and os.path.exists(NODE_PATH):
                fallback_opts["js_runtimes"] = {"node": {"path": NODE_PATH}}
            if youtube_runtime:
                fallback_opts["js_runtimes"] = youtube_runtime
            if cookies_browser and str(cookies_browser).strip().lower() not in ("none", "off", "disabled", "false", ""):
                if "cookie" not in str(e).lower():
                    fallback_opts["cookiesfrombrowser"] = (str(cookies_browser).strip().lower(),)
                else:
                    logger.warning(f"Browser cookies from '{cookies_browser}' caused extraction failure ({e}). Retrying fallback without cookies.")

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
                if not downloaded_file:
                    raise RuntimeError("The downloader returned no completed media file.")

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
            elif "Sign in to confirm" in clean_err or "bot" in clean_err.lower():
                clean_err = "YouTube requires sign-in or detected a bot check. Enable Browser Cookies (e.g. Chrome) in Downloader."
            elif "login" in clean_err.lower() and "instagram" in clean_err.lower():
                clean_err = "Instagram requires login to view this reel/post. Enable Browser Cookies (e.g. Chrome) in Downloader."
            elif "403" in clean_err:
                clean_err = "Access forbidden by media host (HTTP 403). Stream may be geo-restricted or require login cookies."
            
            with _lock:
                task["status"] = "failed"
                task["error"] = clean_err
                if task["title"] == "Fetching metadata...":
                    task["title"] = resolved_hint or raw_url.split("?")[0].split("/")[-1] or "Download Failed"

def _run_download(task_id, raw_url, media_format, quality, target_dir, destination="server", owner_id="host", owner_name="Host", cookies_browser=None):
    """Supervise an isolated worker so extractor hangs cannot leave pending tasks."""
    process = None
    def fail(message):
        with _lock:
            _download_tasks[task_id].update(status="failed", error=message, title=_download_tasks[task_id].get("title") or raw_url)
    try:
        if getattr(sys, "frozen", False):
            _perform_download(task_id, raw_url, media_format, quality, target_dir, destination, owner_id, owner_name, cookies_browser)
            return
        with _lock:
            initial = dict(_download_tasks[task_id])
        process = subprocess.Popen(
            [sys.executable, "-u", str(pathlib.Path(__file__).resolve()), "--download-worker"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace",
            start_new_session=os.name != "nt",
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        process.stdin.write(json.dumps(initial) + "\n")
        process.stdin.close()
        def read_updates():
            for line in process.stdout:
                if not line.startswith("MEDIA_TASK:"):
                    continue
                try:
                    update = json.loads(line[len("MEDIA_TASK:"):])
                    with _lock:
                        if _download_tasks[task_id]["status"] not in ("failed", "completed"):
                            _download_tasks[task_id].update(update)
                except (ValueError, TypeError):
                    continue
        reader = threading.Thread(target=read_updates, daemon=True)
        reader.start()
        started = time.monotonic()
        while process.poll() is None:
            elapsed = time.monotonic() - started
            with _lock:
                status = _download_tasks[task_id]["status"]
            if (status == "pending" and elapsed > 120) or elapsed > 1800:
                fail("The server timed out fetching metadata. Check internet access and the yt-dlp JavaScript runtime setup." if status == "pending" else "Download exceeded the 30-minute limit. Try a lower quality or shorter video.")
                return
            time.sleep(0.25)
        reader.join(timeout=3)
        with _lock:
            status = _download_tasks[task_id]["status"]
        if status not in ("completed", "failed"):
            fail("The download worker stopped unexpectedly. Check the server's Python dependencies and folder permissions.")
    except Exception as error:
        logger.exception("Download worker failed")
        fail(f"Could not start download: {error}")
    finally:
        if process:
            if process.poll() is None:
                if os.name == "nt":
                    subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                process.wait(timeout=10)
            if process.stdout:
                process.stdout.close()


def _download_worker():
    task = json.loads(sys.stdin.readline())
    task_id = task["id"]
    _download_tasks[task_id] = task
    done = threading.Event()
    def emit():
        with _lock:
            print("MEDIA_TASK:" + json.dumps(dict(task)), flush=True)
    def report():
        while not done.wait(0.5):
            emit()
    threading.Thread(target=report, daemon=True).start()
    try:
        _perform_download(
            task_id,
            task["url"],
            task["format"],
            task["quality"],
            pathlib.Path(task["target_dir"]),
            task["destination"],
            task["owner_id"],
            task["owner_name"],
            task.get("cookies_browser")
        )
    except Exception as error:
        with _lock:
            task.update(status="failed", error=f"Download failed: {error}")
    finally:
        done.set()
        emit()


def start_download(
    url: str,
    media_format: str = "audio",
    quality: str = "best",
    destination: str = "server",
    custom_folder: Optional[str] = None,
    owner_id: str = "host",
    owner_name: str = "Host",
    cookies_browser: Optional[str] = None
) -> str:
    """
    Enqueues a download task in background and returns task_id.
    destination: "server" (saves to host media library) or "client" (saves to staging for direct browser download)
    cookies_browser: "chrome", "edge", "firefox", or None/empty
    """
    if media_format not in ("audio", "video") or destination not in ("server", "client"):
        raise ValueError("Choose Audio or Video and a valid download destination.")
    task_id = str(uuid.uuid4())
    
    current_settings = settings.load_settings()
    if destination == "client":
        target_dir = config.STAGING_DIR / f"client_{task_id}"
    elif custom_folder:
        target_dir = pathlib.Path(custom_folder)
    else:
        target_dir = settings.get_target_upload_folder(media_type="video" if media_format == "video" else "audio")

    # Resolve cookies browser choice: per-request option overrides setting default
    active_cookies_browser = cookies_browser if cookies_browser is not None else current_settings.get("download_browser_cookies", "")
    if active_cookies_browser:
        active_cookies_browser = str(active_cookies_browser).strip().lower()
        if active_cookies_browser in ("none", "off", "disabled", "false", ""):
            active_cookies_browser = None
    else:
        active_cookies_browser = None

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
            "cookies_browser": active_cookies_browser,
            "status": "pending",
            "progress": 0,
            "target_dir": str(target_dir),
            "error": None
        }

    thread = threading.Thread(
        target=_run_download,
        args=(task_id, url, media_format, quality, target_dir, destination, owner_id, owner_name, active_cookies_browser),
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


if __name__ == "__main__" and "--download-worker" in sys.argv:
    _download_worker()



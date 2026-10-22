import os
import pathlib

BASE_DIR = pathlib.Path(__file__).resolve().parent

# Default Music directory
DEFAULT_MUSIC_DIR = pathlib.Path(os.path.expanduser("~/Music"))
if not DEFAULT_MUSIC_DIR.exists():
    try:
        DEFAULT_MUSIC_DIR.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass

# Default Videos directory
DEFAULT_VIDEO_DIR = pathlib.Path(os.path.expanduser("~/Videos"))

# Supported Audio & Video Formats
AUDIO_EXTENSIONS = {
    ".mp3",
    ".flac",
    ".m4a",
    ".aac",
    ".ogg",
    ".opus",
    ".wav",
    ".wma",
}

VIDEO_EXTENSIONS = {
    ".mp4",
    ".mkv",
    ".mov",
    ".avi",
    ".m4v",
    ".ts",
}

# Ambiguous formats that can be audio or video
DUAL_EXTENSIONS = {
    ".webm",
}

SUPPORTED_EXTENSIONS = AUDIO_EXTENSIONS.union(VIDEO_EXTENSIONS).union(DUAL_EXTENSIONS)

# Cache & DB Paths
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

CACHE_DIR = DATA_DIR / "cache"
COVERS_DIR = CACHE_DIR / "covers"
COVERS_DIR.mkdir(parents=True, exist_ok=True)

VIDEO_THUMBS_DIR = CACHE_DIR / "video_thumbs"
VIDEO_THUMBS_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "media.db"

# Server Host & Port
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", 8000))

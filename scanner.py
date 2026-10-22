import os
import pathlib
import hashlib
import io
import mimetypes
import logging
from typing import Optional, Dict, Any, List
from PIL import Image
import mutagen
from mutagen.id3 import ID3, APIC
from mutagen.mp4 import MP4, MP4Cover
from mutagen.flac import FLAC, Picture

import config
import settings
import database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("scanner")

def get_file_id(filepath: str) -> str:
    return hashlib.sha1(filepath.encode("utf-8")).hexdigest()

def extract_cover_art(audio_obj: Any, file_path: pathlib.Path) -> Optional[str]:
    """Extracts embedded cover art or looks for folder.jpg/cover.jpg, saves thumbnail, returns hash."""
    image_bytes = None
    
    # 1. Try embedded cover art
    try:
        if isinstance(audio_obj, FLAC) and audio_obj.pictures:
            image_bytes = audio_obj.pictures[0].data
        elif hasattr(audio_obj, "tags") and audio_obj.tags:
            tags = audio_obj.tags
            if isinstance(tags, ID3) or hasattr(tags, "getall"):
                apics = tags.getall("APIC")
                if apics:
                    image_bytes = apics[0].data
            elif isinstance(tags, dict) and "covr" in tags:
                covers = tags["covr"]
                if covers:
                    image_bytes = bytes(covers[0])
    except Exception as e:
        logger.debug(f"Error reading embedded cover for {file_path}: {e}")

    # 2. If no embedded cover, look for sibling cover/poster image
    if not image_bytes:
        folder = file_path.parent
        candidates = [
            f"{file_path.stem}.jpg", f"{file_path.stem}.png", f"{file_path.stem}.webp",
            "cover.jpg", "cover.png", "folder.jpg", "folder.png", "poster.jpg", "poster.png"
        ]
        for candidate in candidates:
            cand_path = folder / candidate
            if cand_path.exists() and cand_path.is_file():
                try:
                    with open(cand_path, "rb") as f:
                        image_bytes = f.read()
                    break
                except Exception:
                    pass

    if not image_bytes:
        return None

    # Compute hash and save thumbnail
    try:
        cover_hash = hashlib.sha1(image_bytes).hexdigest()
        dest_path = config.COVERS_DIR / f"{cover_hash}.jpg"
        if not dest_path.exists():
            img = Image.open(io.BytesIO(image_bytes))
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            img.thumbnail((500, 500), Image.Resampling.LANCZOS)
            img.save(dest_path, "JPEG", quality=85)
        return cover_hash
    except Exception as e:
        logger.debug(f"Failed to process cover image for {file_path}: {e}")
        return None

def parse_media_file(file_path: pathlib.Path, folder_type: str = "both", owner_id: str = "host", owner_name: str = "Host") -> Optional[Dict[str, Any]]:
    """Extracts metadata from an audio or video file."""
    try:
        stat = file_path.stat()
        mtime = stat.st_mtime
        filesize = stat.st_size
    except Exception:
        return None

    # Skip empty 0-byte or tiny corrupt files
    if filesize < 1024:
        return None

    str_path = str(file_path.resolve())
    media_id = get_file_id(str_path)
    suffix = file_path.suffix.lower()
    
    # Classify as audio vs video
    if folder_type == "music":
        is_video = False
    elif folder_type == "video":
        is_video = True
    elif suffix in config.AUDIO_EXTENSIONS:
        is_video = False
    elif suffix in config.VIDEO_EXTENSIONS:
        is_video = True
    elif suffix in config.DUAL_EXTENSIONS:
        # Default .webm in music folders to audio
        is_video = "music" not in str(file_path.parent).lower()
    else:
        is_video = False

    media_type = "video" if is_video else "audio"

    name_stem = file_path.stem
    # Normalize Unicode characters often found in YouTube / web titles
    cleaned_name = (
        name_stem
        .replace("｜", "|")
        .replace("：", ":")
        .replace("―", "-")
        .replace("–", "-")
        .replace("—", "-")
    )

    # Clean YouTube IDs like [xvT1jH8B9AM] or [8of5w7RgcTc]
    import re
    cleaned_name = re.sub(r'\s*\[[a-zA-Z0-9_-]{10,12}\](\.part)?$', '', cleaned_name).strip()

    # Strip web watermarks
    for prefix in ["[Songs.PK] ", "[Songs.PK]", "(webmusic.in)_", "(webmusic.in)", "[PublicMasti] ", "[PublicMasti]"]:
        if cleaned_name.startswith(prefix):
            cleaned_name = cleaned_name[len(prefix):].strip()

    title = cleaned_name
    artist = "Unknown Artist" if not is_video else "Video / Movie"
    album = "Single / Unknown Album" if not is_video else "Local Videos"
    album_artist = None
    year = None
    genre = "Movie" if is_video else "Unknown"
    track_number = 1
    disc_number = 1
    duration = 0.0
    bitrate = 128
    cover_hash = None
    resolution = None

    if not is_video:
        # Detect leading track numbers like "01 - Song", "02. Song", "01-Song"
        m = re.match(r'^(\d{1,3})[\s\.\-_]+(.+)$', cleaned_name)
        if m:
            track_number = int(m.group(1))
            cleaned_name = m.group(2).strip()

        if " - " in cleaned_name:
            parts = [p.strip() for p in cleaned_name.split(" - ") if p.strip()]
            if len(parts) == 1:
                title = parts[0]
            elif len(parts) >= 2:
                artist = parts[0]
                title = " - ".join(parts[1:])
        elif " | " in cleaned_name:
            parts = [p.strip() for p in cleaned_name.split("|") if p.strip()]
            title = parts[0]
            if len(parts) > 1:
                artist = parts[1]
        else:
            title = cleaned_name

        # Clean noise suffixes in title & artist
        noise_patterns = [
            r'\(Official\s*(?:Music\s*)?Video\)',
            r'\[Official\s*(?:Music\s*)?Video\]',
            r'\(Official\s*Audio\)',
            r'\[Official\s*Audio\]',
            r'\(Lyrical(?:\s*Video)?\)',
            r'\[Lyrical(?:\s*Video)?\]',
            r'\(Audio\)',
            r'\(Visualizer\)',
            r'\(Lyric\s*Video\)',
            r'\|\s*8K\s*Video\s*\|',
            r'\|\s*4K\s*Video\s*\|',
            r'\|\s*4K\s*\|',
            r'8K\s*Full\s*Song:',
            r'Full\s*Video\s*Song:',
            r'Full\s*Video:',
            r'Full\s*Song:',
            r'Video\s*Song\s*\|',
            r'-\s*DownloadMing\.\w+',
            r'DownloadMing\.\w+',
        ]
        for np in noise_patterns:
            title = re.sub(np, '', title, flags=re.IGNORECASE).strip()
            artist = re.sub(np, '', artist, flags=re.IGNORECASE).strip()

        # Ensure title is never empty
        if not title:
            title = artist or name_stem
            artist = "Unknown Artist"
        if not artist:
            artist = "Unknown Artist"
        if title == artist:
            artist = "Unknown Artist"

    mime_type, _ = mimetypes.guess_type(str_path)
    if not mime_type:
        mime_type = "video/mp4" if is_video else "audio/mpeg"

    try:
        media_obj = mutagen.File(str_path)
        if media_obj is not None:
            if hasattr(media_obj, "info") and media_obj.info is not None:
                duration = getattr(media_obj.info, "length", 0.0)
                bitrate = int(getattr(media_obj.info, "bitrate", 0) / 1000) if getattr(media_obj.info, "bitrate", 0) else 128

            tags = getattr(media_obj, "tags", None)
            if tags:
                def get_tag_val(keys: List[str]) -> Optional[str]:
                    for k in keys:
                        if k in tags:
                            val = tags[k]
                            if isinstance(val, (list, tuple)) and val:
                                return str(val[0])
                            return str(val)
                    return None

                t_title = get_tag_val(["TIT2", "title", "\xa9nam", "TITLE"])
                if t_title and t_title.strip():
                    title = t_title.strip()

                t_artist = get_tag_val(["TPE1", "artist", "\xa9ART", "ARTIST"])
                if t_artist and t_artist.strip():
                    artist = t_artist.strip()

                t_album = get_tag_val(["TALB", "album", "\xa9alb", "ALBUM"])
                if t_album and t_album.strip():
                    album = t_album.strip()

                t_album_artist = get_tag_val(["TPE2", "albumartist", "aART", "ALBUMARTIST"])
                if t_album_artist and t_album_artist.strip():
                    album_artist = t_album_artist.strip()

                t_genre = get_tag_val(["TCON", "genre", "\xa9gen", "GENRE"])
                if t_genre and t_genre.strip():
                    genre = t_genre.strip()

                t_date = get_tag_val(["TDRC", "TYER", "date", "\xa9day", "DATE", "YEAR"])
                if t_date:
                    try:
                        year = int(str(t_date)[:4])
                    except ValueError:
                        pass

            cover_hash = extract_cover_art(media_obj, file_path)

    except Exception as e:
        logger.debug(f"Mutagen read error for {file_path}: {e}")

    return {
        "id": media_id,
        "path": str_path,
        "title": title,
        "artist": artist,
        "album": album,
        "album_artist": album_artist or artist,
        "year": year,
        "genre": genre,
        "track_number": track_number,
        "disc_number": disc_number,
        "duration": round(duration, 2),
        "bitrate": bitrate,
        "filesize": filesize,
        "mtime": mtime,
        "cover_hash": cover_hash,
        "mime_type": mime_type,
        "media_type": media_type,
        "resolution": resolution,
        "owner_id": owner_id,
        "owner_name": owner_name
    }

def scan_library(full_rescan: bool = False) -> Dict[str, Any]:
    """
    Scans explicitly shared folders from settings.py and updates the database.
    If master privacy is disabled, clears the database.
    """
    database.init_db()
    current_settings = settings.load_settings()

    # Privacy check: If sharing is disabled, clear database (Stealth Mode)
    if not current_settings.get("sharing_enabled", True):
        logger.info("Master sharing is disabled (Stealth Mode). Clearing shared database.")
        database.clear_all_media()
        return {
            "scanned_files": 0,
            "updated": 0,
            "stats": database.get_stats(),
            "privacy_mode": "stealth"
        }

    shared_folders = settings.get_active_shared_folders()
    logger.info(f"Starting scan across {len(shared_folders)} explicitly shared folders...")

    valid_paths = []
    scanned_count = 0
    added_or_updated = 0

    for folder in shared_folders:
        if not folder.exists():
            continue

        for root, _, files in os.walk(folder):
            for file in files:
                file_path = pathlib.Path(root) / file
                suffix = file_path.suffix.lower()
                if suffix in config.SUPPORTED_EXTENSIONS:
                    scanned_count += 1
                    str_path = str(file_path.resolve())

                    # Skip empty / corrupted 0-byte files
                    try:
                        if file_path.stat().st_size < 1024:
                            continue
                    except Exception:
                        continue

                    valid_paths.append(str_path)

                    if not full_rescan:
                        existing = database.get_song(get_file_id(str_path))
                        if existing and abs(existing["mtime"] - file_path.stat().st_mtime) < 1.0:
                            continue

                    item_data = parse_media_file(file_path)
                    if item_data:
                        database.upsert_song(item_data)
                        added_or_updated += 1

    database.delete_songs_not_in_paths(valid_paths)
    stats = database.get_stats()
    logger.info(f"Scan complete. Found: {scanned_count}, Added/Updated: {added_or_updated}. Songs: {stats['total_songs']}, Videos: {stats['total_videos']}")
    return {
        "scanned_files": scanned_count,
        "updated": added_or_updated,
        "stats": stats
    }

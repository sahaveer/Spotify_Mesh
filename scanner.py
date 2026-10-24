import os
import pathlib
import hashlib
import io
import mimetypes
import logging
import re
import shutil
import subprocess
from typing import Optional, Dict, Any, List, Tuple
from PIL import Image, ImageOps
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

def extract_video_thumbnail(file_path: pathlib.Path) -> Tuple[Optional[str], Optional[str]]:
    """
    Generates a cached video snapshot frame using ffmpeg and detects frame dimensions.
    Returns (cover_hash, detected_resolution).
    """
    str_path = str(file_path.resolve())
    try:
        stat = file_path.stat()
        cover_hash = hashlib.sha1(f"{str_path}_{stat.st_mtime}".encode("utf-8")).hexdigest()
        dest_path = config.COVERS_DIR / f"{cover_hash}.jpg"

        if dest_path.exists():
            return cover_hash, None

        ffmpeg_bin = shutil.which("ffmpeg")
        if not ffmpeg_bin:
            try:
                import imageio_ffmpeg
                ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()
            except Exception:
                ffmpeg_bin = None

        if not ffmpeg_bin or not os.path.exists(ffmpeg_bin):
            return None, None

        cmd = [
            ffmpeg_bin,
            "-ss", "00:00:03",
            "-i", str_path,
            "-vframes", "1",
            "-q:v", "3",
            "-f", "image2pipe",
            "-vcodec", "mjpeg",
            "pipe:1"
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=8)
        if res.returncode != 0 or len(res.stdout) < 1024:
            cmd[2] = "00:00:01"
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=5)

        if res.returncode == 0 and len(res.stdout) >= 1024:
            img = Image.open(io.BytesIO(res.stdout))
            w, h = img.size
            detected_res = None
            if h >= 2100 or w >= 3800:
                detected_res = "4K / 2160p"
            elif h >= 1000 or w >= 1900:
                detected_res = "1080p"
            elif h >= 700 or w >= 1200:
                detected_res = "720p"
            elif h >= 400:
                detected_res = "480p"

            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            img.thumbnail((600, 600), Image.Resampling.LANCZOS)
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            img.save(dest_path, "JPEG", quality=85)
            return cover_hash, detected_res

    except Exception as e:
        logger.debug(f"Video thumbnail extraction skipped for {file_path}: {e}")

    return None, None

def clean_video_filename(name_stem: str) -> Dict[str, Any]:
    """
    Parses messy video/movie filenames into clean Jellyfin-grade metadata:
    - Detects TV Shows (S01E02, 1x02, Season 1 Episode 2)
    - Detects Movie Release Year (1900-2099)
    - Detects Video Resolution (4K, 1080p, 720p, 480p)
    - Strips scene release tags (BluRay, WEBRip, x264, x265, HEVC, YIFY, RARBG, etc.)
    - Normalizes dots and underscores into clean titles.
    """
    raw = name_stem.replace("｜", "|").replace("：", ":").replace("―", "-").replace("–", "-").replace("—", "-")
    raw = re.sub(r'\s*\[[a-zA-Z0-9_-]{10,12}\](\.part)?$', '', raw).strip()

    tv_match = re.search(r'[\s._-](?:[sS](\d{1,2})[eE](\d{1,2})|(\d{1,2})x(\d{1,2}))(?:[\s._-]|$)', raw)
    if tv_match:
        season = int(tv_match.group(1) or tv_match.group(3))
        episode = int(tv_match.group(2) or tv_match.group(4))
        series_part = raw[:tv_match.start()]
        remainder = raw[tv_match.end():]
        series = re.sub(r'[\._]', ' ', series_part).strip(' -_[]()')
        series = re.sub(r'\s+', ' ', series).strip()

        remainder = re.sub(r'\b(2160p|1080p|720p|480p|4k|bluray|blu-ray|web-dl|webrip|hdrip|dvdrip|x264|x265|hevc|h264|aac|ac3|dts|atmos|rarbg|yify|eztv|tgx)\b.*$', '', remainder, flags=re.I)
        ep_title = re.sub(r'[\._]', ' ', remainder).strip(' -_[]()')
        ep_title = re.sub(r'\s+', ' ', ep_title).strip()

        res = None
        if re.search(r'\b(2160p|4k|uhd)\b', raw, re.I): res = '4K / 2160p'
        elif re.search(r'\b(1080p|fhd)\b', raw, re.I): res = '1080p'
        elif re.search(r'\b(720p|hd)\b', raw, re.I): res = '720p'
        elif re.search(r'\b(480p|576p|sd)\b', raw, re.I): res = '480p'

        formatted_title = f"S{season:02d}E{episode:02d}" + (f" - {ep_title}" if ep_title else "")
        return {
            "is_tv": True,
            "title": formatted_title,
            "series": series or "TV Series",
            "album": f"{series} (Season {season})" if series else f"Season {season}",
            "season": season,
            "episode": episode,
            "year": None,
            "resolution": res,
            "genre": "TV Show"
        }

    year = None
    year_match = re.search(r'[\s._\(\[\-]((?:19|20)\d{2})(?:[\s._\)\]\-]|$)', raw)
    if year_match:
        try:
            year = int(year_match.group(1))
            title_part = raw[:year_match.start()]
        except Exception:
            title_part = raw
    else:
        title_part = raw

    res = None
    if re.search(r'\b(2160p|4k|uhd)\b', raw, re.I): res = '4K / 2160p'
    elif re.search(r'\b(1080p|fhd)\b', raw, re.I): res = '1080p'
    elif re.search(r'\b(720p|hd)\b', raw, re.I): res = '720p'
    elif re.search(r'\b(480p|576p|sd)\b', raw, re.I): res = '480p'

    if not year_match:
        title_part = re.sub(r'\b(2160p|1080p|720p|480p|4k|bluray|blu-ray|web-dl|webrip|hdrip|dvdrip|x264|x265|hevc|h264|aac|ac3|dts|atmos|rarbg|yify|eztv|tgx)\b.*$', '', title_part, flags=re.I)

    clean_title = re.sub(r'[\._]', ' ', title_part).strip(' -_[]()')
    clean_title = re.sub(r'\s+', ' ', clean_title).strip()
    if not clean_title:
        clean_title = name_stem

    return {
        "is_tv": False,
        "title": clean_title,
        "series": None,
        "album": "Movies" if year else "Local Videos",
        "season": None,
        "episode": None,
        "year": year,
        "resolution": res,
        "genre": "Movie"
    }

def extract_cover_art(audio_obj: Any, file_path: pathlib.Path, is_video: bool = False) -> Tuple[Optional[str], Optional[str]]:
    """Extracts embedded cover art, sibling cover/poster image, or video snapshot. Returns (cover_hash, detected_res)."""
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

    if image_bytes:
        # Compute hash and save thumbnail
        try:
            cover_hash = hashlib.sha1(image_bytes).hexdigest()
            dest_path = config.COVERS_DIR / f"{cover_hash}.jpg"
            if not dest_path.exists():
                img = Image.open(io.BytesIO(image_bytes))
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                img.thumbnail((500, 500), Image.Resampling.LANCZOS)
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                img.save(dest_path, "JPEG", quality=85)
            return cover_hash, None
        except Exception as e:
            logger.debug(f"Failed to process cover image for {file_path}: {e}")
            return None, None

    # 3. For video files: generate crisp snapshot thumbnail frame using ffmpeg
    if is_video:
        return extract_video_thumbnail(file_path)

    return None, None

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
    season = None
    episode = None
    duration = 0.0
    bitrate = 128
    cover_hash = None
    resolution = None

    if is_video:
        vid_meta = clean_video_filename(name_stem)
        title = vid_meta["title"]
        artist = vid_meta["series"] or "Video / Movie"
        album = vid_meta["album"]
        year = vid_meta["year"]
        genre = vid_meta["genre"]
        resolution = vid_meta["resolution"]
        season = vid_meta["season"]
        episode = vid_meta["episode"]
        if episode:
            track_number = episode
        if season:
            disc_number = season
    else:
        # Music audio parsing: check if release year is present in parentheses / brackets
        m_year = re.search(r'[\(\[]((?:19|20)\d{2})[\)\]]', name_stem)
        if m_year:
            try:
                year = int(m_year.group(1))
            except ValueError:
                pass

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
                if t_artist and t_artist.strip() and not (is_video and vid_meta.get("is_tv")):
                    artist = t_artist.strip()

                t_album = get_tag_val(["TALB", "album", "\xa9alb", "ALBUM"])
                if t_album and t_album.strip() and not (is_video and vid_meta.get("is_tv")):
                    album = t_album.strip()

                t_album_artist = get_tag_val(["TPE2", "albumartist", "aART", "ALBUMARTIST"])
                if t_album_artist and t_album_artist.strip():
                    album_artist = t_album_artist.strip()

                t_genre = get_tag_val(["TCON", "genre", "\xa9gen", "GENRE"])
                if t_genre and t_genre.strip():
                    genre = t_genre.strip()

                t_date = get_tag_val(["TDRC", "TYER", "date", "\xa9day", "DATE", "YEAR"])
                if t_date and not year:
                    try:
                        year = int(str(t_date)[:4])
                    except ValueError:
                        pass

        cover_hash, detected_res = extract_cover_art(media_obj, file_path, is_video=is_video)
        if is_video and not resolution and detected_res:
            resolution = detected_res

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
        "season": season,
        "episode": episode,
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

def parse_photo_file(file_path: pathlib.Path, owner_id: str = "host", owner_name: str = "Host") -> Optional[Dict[str, Any]]:
    """Extracts metadata, dimensions, EXIF tags, and generates cached thumbnail for a photo."""
    try:
        stat = file_path.stat()
        mtime = stat.st_mtime
        filesize = stat.st_size
    except Exception:
        return None

    if filesize < 512:
        return None

    str_path = str(file_path.resolve())
    photo_id = get_file_id(str_path)

    mime_type, _ = mimetypes.guess_type(str_path)
    if not mime_type:
        mime_type = "image/jpeg"

    import datetime
    dt_obj = datetime.datetime.fromtimestamp(mtime)
    date_taken = dt_obj.strftime("%Y-%m-%d %H:%M:%S")
    year = dt_obj.year
    month = dt_obj.month

    camera_make = None
    camera_model = None
    width = 0
    height = 0
    thumb_hash = None

    try:
        with Image.open(str_path) as img:
            try:
                img = ImageOps.exif_transpose(img)
            except Exception:
                pass
            width, height = img.size

            try:
                exif = img.getexif()
                if exif:
                    camera_make = exif.get(0x010F)
                    camera_model = exif.get(0x0110)
                    if camera_make and isinstance(camera_make, bytes):
                        camera_make = camera_make.decode(errors="ignore")
                    if camera_model and isinstance(camera_model, bytes):
                        camera_model = camera_model.decode(errors="ignore")

                    raw_dt = exif.get(0x0132)
                    try:
                        sub_ifd = exif.get_ifd(0x8769)
                        if sub_ifd and 0x9003 in sub_ifd:
                            raw_dt = sub_ifd[0x9003]
                    except Exception:
                        pass

                    if raw_dt and isinstance(raw_dt, str):
                        parts = raw_dt.strip().split(" ")
                        if len(parts) >= 1:
                            date_part = parts[0].replace(":", "-")
                            time_part = parts[1] if len(parts) > 1 else "00:00:00"
                            date_taken = f"{date_part} {time_part}"
                            try:
                                parsed_year = int(date_part[:4])
                                parsed_month = int(date_part[5:7])
                                if 1970 <= parsed_year <= 2100 and 1 <= parsed_month <= 12:
                                    year = parsed_year
                                    month = parsed_month
                            except Exception:
                                pass
            except Exception as e:
                logger.debug(f"EXIF parsing skipped for {file_path}: {e}")

            # Generate and cache 400x400 thumbnail
            thumb_hash = hashlib.sha1(f"{str_path}_{mtime}".encode("utf-8")).hexdigest()
            dest_thumb = config.PHOTO_THUMBS_DIR / f"{thumb_hash}.jpg"
            if not dest_thumb.exists():
                thumb_img = img.copy()
                if thumb_img.mode in ("RGBA", "P"):
                    thumb_img = thumb_img.convert("RGB")
                thumb_img.thumbnail((400, 400), Image.Resampling.LANCZOS)
                thumb_img.save(dest_thumb, "JPEG", quality=82)

    except Exception as e:
        logger.debug(f"Pillow image error for {file_path}: {e}")
        return None

    parent_name = file_path.parent.name
    album = parent_name if parent_name and parent_name not in ("Pictures", "Photos", "Downloads", "Desktop", "") else "Camera / Uploads"
    title = file_path.stem

    return {
        "id": photo_id,
        "path": str_path,
        "title": title,
        "album": album,
        "date_taken": date_taken,
        "year": year,
        "month": month,
        "width": width,
        "height": height,
        "filesize": filesize,
        "mtime": mtime,
        "thumb_hash": thumb_hash,
        "camera_make": str(camera_make).strip() if camera_make else None,
        "camera_model": str(camera_model).strip() if camera_model else None,
        "mime_type": mime_type,
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

    valid_audio_video_paths = []
    valid_photo_paths = []
    scanned_count = 0
    added_or_updated = 0

    for folder in shared_folders:
        if not folder.exists():
            continue

        for root, _, files in os.walk(folder):
            for file in files:
                file_path = pathlib.Path(root) / file
                suffix = file_path.suffix.lower()
                if suffix not in config.SUPPORTED_EXTENSIONS:
                    continue

                scanned_count += 1
                str_path = str(file_path.resolve())

                # Skip empty / corrupted files
                try:
                    if file_path.stat().st_size < 512:
                        continue
                except Exception:
                    continue

                if suffix in config.PHOTO_EXTENSIONS:
                    valid_photo_paths.append(str_path)
                    if not full_rescan:
                        existing_photo = database.get_photo(get_file_id(str_path))
                        if existing_photo and abs(existing_photo["mtime"] - file_path.stat().st_mtime) < 1.0:
                            continue

                    photo_data = parse_photo_file(file_path)
                    if photo_data:
                        database.upsert_photo(photo_data)
                        added_or_updated += 1
                else:
                    valid_audio_video_paths.append(str_path)
                    if not full_rescan:
                        existing = database.get_song(get_file_id(str_path))
                        if existing and abs(existing["mtime"] - file_path.stat().st_mtime) < 1.0:
                            continue

                    item_data = parse_media_file(file_path)
                    if item_data:
                        database.upsert_song(item_data)
                        added_or_updated += 1

    database.delete_songs_not_in_paths(valid_audio_video_paths)
    database.delete_photos_not_in_paths(valid_photo_paths)
    stats = database.get_stats()
    logger.info(f"Scan complete. Found: {scanned_count}, Added/Updated: {added_or_updated}. Songs: {stats['total_songs']}, Videos: {stats['total_videos']}, Photos: {stats.get('total_photos', 0)}")
    return {
        "scanned_files": scanned_count,
        "updated": added_or_updated,
        "stats": stats
    }

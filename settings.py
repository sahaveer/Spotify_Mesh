import os
import json
import uuid
import socket
import pathlib
from typing import Dict, Any, List, Optional

import config

SETTINGS_FILE = config.DATA_DIR / "settings.json"

def get_default_device_name() -> str:
    try:
        hostname = socket.gethostname()
        return f"{hostname}'s Hub"
    except Exception:
        return "Media Hub"

def get_default_settings() -> Dict[str, Any]:
    default_music = config.DEFAULT_MUSIC_DIR
    default_download = str(default_music)
    default_photo = config.DEFAULT_PHOTO_DIR
    
    shared_folders = [
        {
            "id": str(uuid.uuid4()),
            "path": str(default_music),
            "name": "Default Music",
            "type": "both",  # "music" | "video" | "photos" | "both" | "all"
            "enabled": True
        }
    ]
    if default_photo.exists():
        shared_folders.append({
            "id": str(uuid.uuid4()),
            "path": str(default_photo),
            "name": "Default Pictures",
            "type": "photos",
            "enabled": True
        })

    return {
        "device_id": str(uuid.uuid4()),
        "device_name": get_default_device_name(),
        "sharing_enabled": True,  # Master privacy toggle
        "upload_approval_required": False,  # Host approval required for peer uploads
        "global_access_enabled": True,  # Worldwide remote access via Cloudflare tunnel enabled by default
        "global_tunnel_token": "",
        "trust_tailscale_admin": True,  # Grant admin access to devices connected via Tailscale (100.64.0.0/10)
        "trust_lan_admin": False,  # Grant admin access to devices on local Wi-Fi/LAN (192.168.x.x, 10.x.x.x)
        "admin_token": "",  # Optional custom admin token / password for remote admin access
        "download_dir": default_download,
        "shared_folders": shared_folders
    }

def load_settings() -> Dict[str, Any]:
    if not SETTINGS_FILE.exists():
        settings = get_default_settings()
        save_settings(settings)
        return settings
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Ensure required keys exist
            if "device_id" not in data:
                data["device_id"] = str(uuid.uuid4())
            if "device_name" not in data:
                data["device_name"] = get_default_device_name()
            if "sharing_enabled" not in data:
                data["sharing_enabled"] = True
            if "upload_approval_required" not in data:
                data["upload_approval_required"] = False
            if "global_access_enabled" not in data:
                data["global_access_enabled"] = True
            if "global_tunnel_token" not in data:
                data["global_tunnel_token"] = ""
            if "trust_tailscale_admin" not in data:
                data["trust_tailscale_admin"] = True
            if "trust_lan_admin" not in data:
                data["trust_lan_admin"] = False
            if "admin_token" not in data:
                data["admin_token"] = ""
            if "shared_folders" not in data:
                data["shared_folders"] = []
            if "download_dir" not in data:
                data["download_dir"] = str(config.DEFAULT_MUSIC_DIR)
            return data
    except Exception:
        return get_default_settings()

def save_settings(settings: Dict[str, Any]):
    config.DATA_DIR.mkdir(exist_ok=True)
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)

def get_active_shared_folders(media_type: Optional[str] = None) -> List[pathlib.Path]:
    """
    Returns the list of folder paths that the user has explicitly allowed for sharing.
    If master sharing_enabled is False, returns [] (Stealth/Privacy Mode).
    """
    settings = load_settings()
    if not settings.get("sharing_enabled", True):
        return []

    active_paths = []
    for item in settings.get("shared_folders", []):
        if item.get("enabled", True):
            folder_type = item.get("type", "both")
            if media_type is None or folder_type == "both" or folder_type == "all" or folder_type == media_type:
                p = pathlib.Path(item["path"])
                if p.exists() and p.is_dir():
                    active_paths.append(p)
    return active_paths

def get_target_upload_folder(media_type: str = "audio") -> pathlib.Path:
    """
    Finds the optimal target directory for incoming uploads based on media type:
    - Prioritizes real user shared folders (e.g. D:\\MEDIA PLAYER) over internal test directories
    - If the folder contains specialized subfolders (VIDEOS, MUSIC, PHOTOS), saves directly into them
      so CasaOS, Plex, and other media managers see them organized immediately.
    """
    m_type = "video" if media_type == "video" else ("music" if media_type == "audio" else "photos")
    active_folders = get_active_shared_folders(media_type=m_type)
    
    # Filter out internal data/test_* directories if real user shared folders exist
    user_folders = [f for f in active_folders if "data\\test_" not in str(f) and "data/test_" not in str(f)]
    selected_folder = user_folders[0] if user_folders else (active_folders[0] if active_folders else None)

    if not selected_folder:
        all_active = get_active_shared_folders()
        all_user = [f for f in all_active if "data\\test_" not in str(f) and "data/test_" not in str(f)]
        selected_folder = all_user[0] if all_user else (all_active[0] if all_active else None)

    if selected_folder:
        # Check for matching subfolders (e.g. D:\MEDIA PLAYER\VIDEOS or D:\MEDIA PLAYER\MUSIC)
        if media_type == "video":
            for sub in ["VIDEOS", "videos", "Movies", "movies", "Video", "video"]:
                candidate = selected_folder / sub
                if candidate.exists() and candidate.is_dir():
                    return candidate
        elif media_type == "audio":
            for sub in ["MUSIC", "music", "Audio", "audio", "Songs", "songs"]:
                candidate = selected_folder / sub
                if candidate.exists() and candidate.is_dir():
                    return candidate
        elif media_type == "photos":
            for sub in ["PHOTOS", "photos", "Pictures", "pictures", "Photos", "Images"]:
                candidate = selected_folder / sub
                if candidate.exists() and candidate.is_dir():
                    return candidate
        return selected_folder

    current_settings = load_settings()
    if media_type == "video":
        return config.DEFAULT_VIDEO_DIR
    elif media_type == "photos":
        return config.DEFAULT_PHOTO_DIR
    return pathlib.Path(current_settings.get("download_dir", str(config.DEFAULT_MUSIC_DIR)))


def add_shared_folder(path: str, name: Optional[str] = None, folder_type: str = "both") -> Dict[str, Any]:
    clean_path = path.strip()
    # Normalize Windows backslashes if running on Linux/POSIX
    if os.name != "nt" and "\\" in clean_path:
        clean_path = clean_path.replace("\\", "/")
    p = pathlib.Path(clean_path).resolve()
    if not p.exists() or not p.is_dir():
        raise ValueError(f"Directory does not exist: {clean_path}")

    settings = load_settings()
    str_path = str(p)

    # Check if already in list
    for item in settings["shared_folders"]:
        if pathlib.Path(item["path"]).resolve() == p:
            item["enabled"] = True
            item["type"] = folder_type
            if name:
                item["name"] = name
            save_settings(settings)
            return item

    new_item = {
        "id": str(uuid.uuid4()),
        "path": str_path,
        "name": name or p.name or str_path,
        "type": folder_type,
        "enabled": True
    }
    settings["shared_folders"].append(new_item)
    save_settings(settings)
    return new_item

def remove_shared_folder(folder_id: str) -> bool:
    settings = load_settings()
    initial_len = len(settings["shared_folders"])
    settings["shared_folders"] = [f for f in settings["shared_folders"] if f["id"] != folder_id]
    if len(settings["shared_folders"]) < initial_len:
        save_settings(settings)
        return True
    return False

def toggle_shared_folder(folder_id: str, enabled: bool) -> bool:
    settings = load_settings()
    for f in settings["shared_folders"]:
        if f["id"] == folder_id:
            f["enabled"] = enabled
            save_settings(settings)
            return True
    return False

def set_master_sharing(enabled: bool):
    settings = load_settings()
    settings["sharing_enabled"] = enabled
    save_settings(settings)

def set_device_name(name: str):
    settings = load_settings()
    settings["device_name"] = name.strip() or get_default_device_name()
    save_settings(settings)

def set_download_dir(path: str):
    p = pathlib.Path(path).resolve()
    if not p.exists():
        p.mkdir(parents=True, exist_ok=True)
    settings = load_settings()
    settings["download_dir"] = str(p)
    save_settings(settings)

def is_global_access_enabled() -> bool:
    return bool(load_settings().get("global_access_enabled", True))

def set_global_access(enabled: bool):
    settings = load_settings()
    settings["global_access_enabled"] = enabled
    save_settings(settings)

def set_tunnel_token(token: str):
    settings = load_settings()
    settings["global_tunnel_token"] = token.strip()
    save_settings(settings)

def is_upload_approval_required() -> bool:
    return bool(load_settings().get("upload_approval_required", False))

def set_upload_approval_required(required: bool):
    settings = load_settings()
    settings["upload_approval_required"] = bool(required)
    save_settings(settings)


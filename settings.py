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
    
    return {
        "device_id": str(uuid.uuid4()),
        "device_name": get_default_device_name(),
        "sharing_enabled": True,  # Master privacy toggle
        "download_dir": default_download,
        "shared_folders": [
            {
                "id": str(uuid.uuid4()),
                "path": str(default_music),
                "name": "Default Music",
                "type": "both",  # "music" | "video" | "both"
                "enabled": True
            }
        ]
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
            if media_type is None or folder_type == "both" or folder_type == media_type:
                p = pathlib.Path(item["path"])
                if p.exists() and p.is_dir():
                    active_paths.append(p)
    return active_paths

def add_shared_folder(path: str, name: Optional[str] = None, folder_type: str = "both") -> Dict[str, Any]:
    p = pathlib.Path(path).resolve()
    if not p.exists() or not p.is_dir():
        raise ValueError(f"Directory does not exist: {path}")

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

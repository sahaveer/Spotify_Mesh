import socket
import time
import threading
import logging
from typing import Dict, Any, List, Optional
import urllib.request
import json
from zeroconf import Zeroconf, ServiceInfo, ServiceBrowser, ServiceStateChange

import config
import settings
import database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mesh")

SERVICE_TYPE = "_meshmedia._tcp.local."

_zeroconf: Optional[Zeroconf] = None
_service_info: Optional[ServiceInfo] = None
_discovered_peers: Dict[str, Dict[str, Any]] = {}
_peer_lock = threading.Lock()

class MeshServiceListener:
    def __init__(self, zc: Zeroconf):
        self.zc = zc

    def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        with _peer_lock:
            if name in _discovered_peers:
                logger.info(f"Peer left Wi-Fi: {_discovered_peers[name].get('device_name', name)}")
                del _discovered_peers[name]

    def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        info = zc.get_service_info(type_, name)
        if not info:
            return

        # Get local device_id to ignore self
        my_settings = settings.load_settings()
        my_id = my_settings.get("device_id")

        try:
            properties = {k.decode("utf-8"): v.decode("utf-8") for k, v in info.properties.items()}
            peer_id = properties.get("device_id", name)
            if peer_id == my_id:
                return  # Skip self

            addresses = [socket.inet_ntoa(addr) for addr in info.addresses if len(addr) == 4]
            if not addresses:
                return
            host_ip = addresses[0]
            port = info.port
            device_name = properties.get("device_name", name.split(".")[0])

            with _peer_lock:
                _discovered_peers[name] = {
                    "id": peer_id,
                    "service_name": name,
                    "device_name": device_name,
                    "host": host_ip,
                    "port": port,
                    "url": f"http://{host_ip}:{port}",
                    "music_count": int(properties.get("music_count", 0)),
                    "video_count": int(properties.get("video_count", 0)),
                    "last_seen": time.time()
                }
                logger.info(f"Discovered new peer on Wi-Fi: {device_name} at http://{host_ip}:{port}")
        except Exception as e:
            logger.debug(f"Error parsing peer info for {name}: {e}")

    def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        self.add_service(zc, type_, name)

def get_local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def start_mesh_service(port: int = config.PORT):
    global _zeroconf, _service_info
    try:
        _zeroconf = Zeroconf()
        current_settings = settings.load_settings()
        device_id = current_settings.get("device_id")
        device_name = current_settings.get("device_name", "MediaHub")

        stats = database.get_stats()
        local_ip = get_local_ip()
        ip_bytes = socket.inet_aton(local_ip)

        props = {
            "device_id": device_id,
            "device_name": device_name,
            "music_count": str(stats["total_songs"]),
            "video_count": str(stats["total_videos"]),
            "photo_count": str(stats.get("total_photos", 0)),
            "version": "2.0.0"
        }

        # Safe service name
        clean_name = "".join(c for c in device_name if c.isalnum() or c in ("-", "_", " "))
        service_name = f"{clean_name}-{device_id[:6]}.{SERVICE_TYPE}"

        _service_info = ServiceInfo(
            SERVICE_TYPE,
            service_name,
            addresses=[ip_bytes],
            port=port,
            properties=props,
            server=f"{socket.gethostname()}.local."
        )

        _zeroconf.register_service(_service_info)
        listener = MeshServiceListener(_zeroconf)
        ServiceBrowser(_zeroconf, SERVICE_TYPE, listener)
        logger.info(f"Mesh service broadcast active as '{clean_name}' on port {port}")
    except Exception as e:
        logger.warning(f"Failed to start Zeroconf mesh service: {e}")

def stop_mesh_service():
    global _zeroconf, _service_info
    if _zeroconf and _service_info:
        try:
            _zeroconf.unregister_service(_service_info)
            _zeroconf.close()
        except Exception:
            pass

def get_active_peers() -> List[Dict[str, Any]]:
    with _peer_lock:
        return list(_discovered_peers.values())

def fetch_peer_library(peer_url: str) -> Dict[str, Any]:
    """Fetches remote peer's public songs, videos, and photos."""
    result = {"songs": [], "photos": [], "count": 0}
    try:
        req = urllib.request.Request(f"{peer_url}/api/songs", headers={"User-Agent": "MediaMesh/2.0"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode())
            result["songs"] = data.get("songs", [])
            result["count"] = data.get("count", len(result["songs"]))
    except Exception as e:
        logger.debug(f"Failed to fetch songs from peer {peer_url}: {e}")

    try:
        req_p = urllib.request.Request(f"{peer_url}/api/photos", headers={"User-Agent": "MediaMesh/2.0"})
        with urllib.request.urlopen(req_p, timeout=3) as resp:
            p_data = json.loads(resp.read().decode())
            result["photos"] = p_data.get("photos", [])
    except Exception as e:
        logger.debug(f"Failed to fetch photos from peer {peer_url}: {e}")

    return result

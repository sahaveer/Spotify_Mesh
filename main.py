import os
import re
import io
import time
import uuid
import shutil
import urllib.parse
import pathlib
import threading
import ipaddress
from contextlib import asynccontextmanager
from typing import Optional, List, Dict, Any
import qrcode

from fastapi import FastAPI, Request, Response, HTTPException, Query, BackgroundTasks, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel

import config
import settings
import database
import scanner
import streamer
import downloader
import mesh
import run_server
import tunnel
import dlna

# Connected Client Tracker
_connected_clients: Dict[str, Dict[str, Any]] = {}
_clients_lock = threading.Lock()

def run_status_auto_prune():
    """Background daemon task that cleans up expired 24-hour statuses."""
    while True:
        try:
            now = time.time()
            expired_paths = database.cleanup_expired_statuses(now)
            for fpath in expired_paths:
                try:
                    p = pathlib.Path(fpath)
                    if p.exists():
                        p.unlink()
                except Exception:
                    pass
        except Exception:
            pass
        time.sleep(300)

@asynccontextmanager
async def lifespan(app: FastAPI):
    database.init_db()
    # Trigger initial library scan
    threading.Thread(target=scanner.scan_library, daemon=True).start()
    # Start Zeroconf peer discovery broadcast (Mesh Network)
    threading.Thread(target=mesh.start_mesh_service, daemon=True).start()
    # Start UPnP/DLNA responder service for VLC & Smart TVs
    threading.Thread(target=dlna.start_dlna_service, args=(config.PORT,), daemon=True).start()
    # Start 24h Status auto-pruning background task
    threading.Thread(target=run_status_auto_prune, daemon=True).start()
    # Start Worldwide Remote Access (Global Cloudflare Tunnel) if enabled
    if settings.is_global_access_enabled():
        token = settings.load_settings().get("global_tunnel_token")
        threading.Thread(target=tunnel.start_tunnel, args=(config.PORT, token), daemon=True).start()
    yield
    mesh.stop_mesh_service()
    tunnel.stop_tunnel()
    dlna.stop_dlna_service()

app = FastAPI(title="Decentralized Media Hub", version="2.0.0", lifespan=lifespan)

# Allow CORS for mobile web apps & native clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class UpdateMediaMetadataRequest(BaseModel):
    title: Optional[str] = None
    artist: Optional[str] = None
    album: Optional[str] = None
    album_artist: Optional[str] = None
    year: Optional[int] = None
    genre: Optional[str] = None
    resolution: Optional[str] = None
    season: Optional[int] = None
    episode: Optional[int] = None

# Pydantic Schemas
class CreatePlaylistRequest(BaseModel):
    name: str

class UpdateSettingsRequest(BaseModel):
    device_name: Optional[str] = None
    sharing_enabled: Optional[bool] = None
    upload_approval_required: Optional[bool] = None
    global_access_enabled: Optional[bool] = None
    global_tunnel_token: Optional[str] = None
    download_dir: Optional[str] = None
    trust_tailscale_admin: Optional[bool] = None
    admin_token: Optional[str] = None

class AddFolderRequest(BaseModel):
    path: str
    name: Optional[str] = None
    type: str = "both"  # "music", "video", "photos", "both", "all"

class DownloadMediaRequest(BaseModel):
    url: str
    format: str = "audio"  # "audio" or "video"
    quality: str = "best"   # "best", "1080p", "720p"
    destination: str = "server"  # "server" or "client"
    custom_folder: Optional[str] = None
    client_id: Optional[str] = None
    device_name: Optional[str] = None

class ClientPingRequest(BaseModel):
    client_id: str
    device_name: Optional[str] = "Web Player"
    user_agent: Optional[str] = None

def get_client_ip(request: Optional[Request]) -> str:
    if not request or not request.client:
        return ""
    # Cloudflare Tunnel passes CF-Connecting-IP with the true remote visitor IP
    cf_ip = request.headers.get("cf-connecting-ip")
    if cf_ip and cf_ip.strip():
        return cf_ip.strip()
    xff = request.headers.get("x-forwarded-for")
    if xff and xff.strip():
        return xff.split(",")[0].strip()
    return request.client.host

def get_request_client_id(request: Request, explicit_client_id: Optional[str] = None) -> str:
    if explicit_client_id and explicit_client_id.strip():
        return explicit_client_id.strip()
    header_client_id = request.headers.get("x-client-id")
    if header_client_id and header_client_id.strip():
        return header_client_id.strip()
    if is_host_admin(request):
        return "host"
    client_ip = get_client_ip(request)
    return f"peer_{client_ip.replace('.', '_').replace(':', '_')}" if client_ip else "peer_remote"

def is_lan_ip(ip_str: Optional[str]) -> bool:
    if not ip_str:
        return False
    try:
        ip = ipaddress.ip_address(str(ip_str).strip())
        return ip.is_private and not run_server.is_tailscale_ip(ip_str)
    except Exception:
        pass
    return False

def is_host_admin(request: Optional[Request]) -> bool:
    if not request:
        return True
    
    # Check if request arrived through Cloudflare Tunnel (CF-Connecting-IP is present)
    is_via_cloudflare = bool(request.headers.get("cf-connecting-ip"))
    client_ip = get_client_ip(request)

    # 1. Direct local console connection (only when NOT proxying through Cloudflare)
    if not is_via_cloudflare:
        if client_ip in ("127.0.0.1", "::1", "localhost", "testclient"):
            return True
        try:
            if client_ip in run_server.get_local_ips():
                return True
        except Exception:
            pass

    app_settings = settings.load_settings()

    # 2. If client is connecting over Tailscale, check if trusted in settings (default: True)
    try:
        if app_settings.get("trust_tailscale_admin", True) and run_server.is_tailscale_ip(client_ip):
            return True
    except Exception:
        pass

    # 3. If trust_lan_admin is explicitly enabled in settings (e.g. on dedicated home servers)
    try:
        direct_lan = not is_via_cloudflare and not request.headers.get("x-forwarded-for") and is_lan_ip(request.client.host if request.client else "")
        password_unset = not app_settings.get("admin_token", "").strip()
        if direct_lan and (password_unset or app_settings.get("trust_lan_admin", False)):
            return True
    except Exception:
        pass

    # 4. Admin Token via header (x-admin-token) or query parameter (admin_token)
    try:
        token = app_settings.get("admin_token")
        if token and token.strip():
            header_token = request.headers.get("x-admin-token") or request.query_params.get("admin_token")
            if header_token == token.strip():
                return True
    except Exception:
        pass
    return False

# --- Status & Settings API ---
@app.post("/api/client/ping")
def client_ping(body: ClientPingRequest, request: Request):
    client_ip = request.client.host if request.client else "127.0.0.1"
    now = time.time()
    with _clients_lock:
        _connected_clients[body.client_id] = {
            "client_id": body.client_id,
            "device_name": body.device_name or "Web Player",
            "ip": client_ip,
            "user_agent": body.user_agent or request.headers.get("user-agent", "Unknown Browser"),
            "last_seen": now
        }
    return {"status": "ok"}

@app.get("/api/clients")
def get_connected_clients():
    now = time.time()
    with _clients_lock:
        active = [c for c in _connected_clients.values() if now - c["last_seen"] < 60]
    return {"clients": active, "count": len(active)}

@app.get("/api/peers/connected")
def get_connected_peers_list():
    now = time.time()
    with _clients_lock:
        active = [c for c in _connected_clients.values() if now - c["last_seen"] < 60]
    
    uploading = database.get_peers_with_media()
    seen_ids = set()
    combined = []
    
    for c in active:
        cid = c.get("client_id")
        if cid and cid != "host" and cid not in seen_ids:
            seen_ids.add(cid)
            combined.append({
                "id": cid,
                "name": c.get("device_name") or f"Peer ({cid[:6]})",
                "active": True
            })
            
    for u in uploading:
        uid = u.get("id")
        if uid and uid != "host" and uid not in seen_ids:
            seen_ids.add(uid)
            combined.append({
                "id": uid,
                "name": u.get("name") or f"Peer ({uid[:6]})",
                "active": False
            })
            
    return {"peers": combined, "count": len(combined)}


@app.get("/api/status")
def get_server_status(request: Request):
    current_settings = settings.load_settings()
    stats = database.get_stats()
    local_ip = mesh.get_local_ip()
    try:
        available_ips = run_server.get_local_ips()
    except Exception:
        available_ips = [local_ip]

    now = time.time()
    with _clients_lock:
        active_clients = [c for c in _connected_clients.values() if now - c["last_seen"] < 60]

    tunnel_info = tunnel.get_tunnel_status()
    tailscale_ip = run_server.get_tailscale_ip()

    return {
        "status": "online",
        "is_admin": is_host_admin(request),
        "device_id": current_settings.get("device_id"),
        "device_name": current_settings.get("device_name", "MediaHub"),
        "sharing_enabled": current_settings.get("sharing_enabled", True),
        "upload_approval_required": current_settings.get("upload_approval_required", False),
        "shared_folders": [f["path"] for f in current_settings.get("shared_folders", []) if f.get("enabled", True)],
        "local_ip": local_ip,
        "available_ips": available_ips,
        "tailscale_ip": tailscale_ip,
        "tailscale_url": f"http://{tailscale_ip}:{config.PORT}" if tailscale_ip else None,
        "port": config.PORT,
        "connect_url": f"http://{local_ip}:{config.PORT}",
        "global_enabled": current_settings.get("global_access_enabled", False),
        "global_status": tunnel_info["status"],
        "global_active": tunnel_info["is_active"],
        "global_url": tunnel_info["url"],
        "global_error": tunnel_info["error"],
        "connected_clients": len(active_clients),
        "stats": stats
    }

@app.get("/api/qr")
def generate_qr_code(url: Optional[str] = None):
    target = url or f"http://{mesh.get_local_ip()}:{config.PORT}"
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=2,
    )
    qr.add_data(target)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#0c0e14", back_color="#ffffff")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return Response(content=buf.getvalue(), media_type="image/png")

@app.get("/api/settings")
def get_all_settings():
    return public_settings(settings.load_settings())


def public_settings(current):
    result = dict(current)
    result["admin_password_set"] = bool(result.pop("admin_token", "").strip())
    result.pop("global_tunnel_token", None)
    return result

@app.post("/api/settings")
def update_settings(body: UpdateSettingsRequest, request: Request):
    if not is_host_admin(request):
        raise HTTPException(
            status_code=403,
            detail="Permission denied. Only the host server administrator can change server settings."
        )
    current = settings.load_settings()
    if body.device_name is not None:
        current["device_name"] = body.device_name.strip()
    if body.sharing_enabled is not None:
        current["sharing_enabled"] = body.sharing_enabled
    if body.upload_approval_required is not None:
        current["upload_approval_required"] = body.upload_approval_required
    if body.download_dir is not None:
        current["download_dir"] = body.download_dir.strip()
    if body.global_access_enabled is not None:
        current["global_access_enabled"] = body.global_access_enabled
        if body.global_access_enabled:
            token = current.get("global_tunnel_token")
            threading.Thread(target=tunnel.start_tunnel, args=(config.PORT, token), daemon=True).start()
        else:
            threading.Thread(target=tunnel.stop_tunnel, daemon=True).start()
    if body.global_tunnel_token is not None:
        current["global_tunnel_token"] = body.global_tunnel_token.strip()
    if body.trust_tailscale_admin is not None:
        current["trust_tailscale_admin"] = body.trust_tailscale_admin
    if body.admin_token is not None:
        current["admin_token"] = body.admin_token.strip()

    settings.save_settings(current)
    # Trigger rescan to apply privacy mode
    scanner.scan_library()
    return public_settings(current)

# --- Worldwide Remote Access (Global Cloudflare Tunnel) Endpoints ---
@app.get("/api/tunnel/status")
def get_tunnel_status_endpoint():
    status = tunnel.get_tunnel_status()
    status["enabled"] = settings.is_global_access_enabled()
    return status

@app.post("/api/tunnel/start")
def start_tunnel_endpoint(request: Request):
    if not is_host_admin(request):
        raise HTTPException(
            status_code=403,
            detail="Permission denied. Only the host server administrator can manage worldwide remote access."
        )
    settings.set_global_access(True)
    current = settings.load_settings()
    status = tunnel.start_tunnel(config.PORT, current.get("global_tunnel_token"))
    return status

@app.post("/api/tunnel/stop")
def stop_tunnel_endpoint(request: Request):
    if not is_host_admin(request):
        raise HTTPException(
            status_code=403,
            detail="Permission denied. Only the host server administrator can manage worldwide remote access."
        )
    settings.set_global_access(False)
    status = tunnel.stop_tunnel()
    return status


@app.get("/api/settings/browse")
def browse_server_folders(request: Request, path: Optional[str] = None):
    if not is_host_admin(request):
        raise HTTPException(status_code=403, detail="Only the server administrator can browse media folders.")
    candidates = [pathlib.Path(f["path"]) for f in settings.load_settings().get("shared_folders", [])]
    candidates += [pathlib.Path("/DATA/Media"), config.DEFAULT_MUSIC_DIR, config.DEFAULT_VIDEO_DIR]
    roots = []
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
            if resolved != pathlib.Path(resolved.anchor) and resolved.is_dir() and resolved not in roots:
                roots.append(resolved)
        except OSError:
            continue
    if path is None:
        return {"path": None, "parent": None, "folders": [{"name": p.name, "path": str(p)} for p in roots]}
    try:
        folder = pathlib.Path(path)
        if not folder.is_absolute():
            raise HTTPException(status_code=400, detail="Choose an absolute media folder path.")
        folder = folder.resolve()
        if not any(folder.is_relative_to(root) for root in roots):
            raise HTTPException(status_code=403, detail="Browse within the listed media locations. To use another location, add its server path manually.")
        if not folder.is_dir():
            raise HTTPException(status_code=404, detail="Folder not found on this server. Check that the drive is mounted.")
        children = []
        for child in folder.iterdir():
            try:
                if child.is_dir() and any(child.resolve().is_relative_to(root) for root in roots):
                    children.append({"name": child.name, "path": str(child)})
            except OSError:
                continue
        children.sort(key=lambda item: item["name"].casefold())
    except PermissionError:
        raise HTTPException(status_code=403, detail="The media server does not have permission to read this folder.")
    except (OSError, ValueError):
        raise HTTPException(status_code=404, detail="Cannot read this media folder. Check that the drive is mounted.")
    parent = folder.parent
    return {"path": str(folder), "parent": str(parent) if parent != folder and any(parent.is_relative_to(root) for root in roots) else None, "folders": children}


@app.post("/api/settings/folders")
def add_folder_to_shared(body: AddFolderRequest, request: Request):
    if not is_host_admin(request):
        raise HTTPException(
            status_code=403,
            detail="Permission denied. Only the host server administrator can add shared folders."
        )
    try:
        new_item = settings.add_shared_folder(body.path, body.name, body.type)
        scanner.scan_library()
        return new_item
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/api/settings/folders/{folder_id}")
def delete_shared_folder(folder_id: str, request: Request):
    if not is_host_admin(request):
        raise HTTPException(
            status_code=403,
            detail="Permission denied. Only the host server administrator can remove shared folders."
        )
    removed = settings.remove_shared_folder(folder_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Folder not found in settings")
    scanner.scan_library()
    return {"message": "Folder removed from sharing"}

@app.post("/api/settings/folders/{folder_id}/toggle")
def toggle_folder(folder_id: str, request: Request, enabled: bool = Query(True)):
    if not is_host_admin(request):
        raise HTTPException(
            status_code=403,
            detail="Permission denied. Only the host server administrator can toggle shared folders."
        )
    toggled = settings.toggle_shared_folder(folder_id, enabled)
    if not toggled:
        raise HTTPException(status_code=404, detail="Folder not found")
    scanner.scan_library()
    return {"message": f"Folder sharing set to {enabled}"}

@app.post("/api/scan")
def trigger_scan(background_tasks: BackgroundTasks, request: Request, full: bool = False):
    if not is_host_admin(request):
        raise HTTPException(
            status_code=403,
            detail="Permission denied. Only the host server administrator can initiate a library scan."
        )
    background_tasks.add_task(scanner.scan_library, full)
    return {"message": "Library scan initiated in background"}

# --- Web Share Target API (Native System Share Sheet Handling) ---
@app.get("/share-target")
def handle_share_target_get(title: Optional[str] = None, text: Optional[str] = None, url: Optional[str] = None):
    raw_content = f"{url or ''} {text or ''} {title or ''}"
    urls = re.findall(r'https?://[^\s]+', raw_content)
    target_url = urls[0] if urls else (url or text or "")
    encoded = urllib.parse.quote(target_url)
    return RedirectResponse(url=f"/?shared_url={encoded}", status_code=303)

@app.post("/share-target")
async def handle_share_target_post(
    request: Request,
    title: Optional[str] = Form(None),
    text: Optional[str] = Form(None),
    url: Optional[str] = Form(None),
    client_id: Optional[str] = Form(None),
    device_name: Optional[str] = Form(None),
    files: Optional[List[UploadFile]] = File(None)
):
    cid = get_request_client_id(request, client_id)
    dname = device_name or ("Host" if cid == "host" else f"Peer ({cid[:6]})")
    # If video/audio files were shared directly from Gallery/Photos
    if files:
        saved_count = 0
        for f in files:
            if f.filename:
                suffix = pathlib.Path(f.filename).suffix.lower()
                mtype = "photo" if suffix in config.PHOTO_EXTENSIONS else ("video" if suffix in config.VIDEO_EXTENSIONS else "audio")
                target_dir = settings.get_target_upload_folder(mtype)
                target_dir.mkdir(parents=True, exist_ok=True)
                save_path = target_dir / f.filename
                with open(save_path, "wb") as buffer:
                    while chunk := await f.read(1024 * 1024):
                        buffer.write(chunk)
                if mtype == "photo":
                    pitem = scanner.parse_photo_file(save_path, owner_id=cid, owner_name=dname)
                    if pitem: database.upsert_photo(pitem)
                else:
                    media_item = scanner.parse_media_file(save_path, owner_id=cid, owner_name=dname)
                    if media_item:
                        database.upsert_song(media_item)
                saved_count += 1

        scanner.scan_library()
        return RedirectResponse(url=f"/?shared_files={saved_count}", status_code=303)

    # If a URL/link was shared from YouTube or browser
    raw_content = f"{url or ''} {text or ''} {title or ''}"
    urls = re.findall(r'https?://[^\s]+', raw_content)
    target_url = urls[0] if urls else (url or text or "")
    encoded = urllib.parse.quote(target_url)
    return RedirectResponse(url=f"/?shared_url={encoded}", status_code=303)

# --- Live Peer Share Tracker (P2P Broadcast with Zero Server Clutter) ---
_live_peer_shares: Dict[str, Dict[str, Any]] = {}
_shares_lock = threading.Lock()

def cleanup_expired_live_shares(max_idle_seconds: int = 90):
    """Removes live peer shares for devices that disconnected / stopped pinging."""
    now = time.time()
    with _shares_lock:
        to_delete = []
        for sid, s in list(_live_peer_shares.items()):
            cid = s.get("client_id")
            client_active = True
            if cid != "host":
                with _clients_lock:
                    c = _connected_clients.get(cid)
                    client_active = bool(
                        (c and (now - c.get("last_seen", 0) < max_idle_seconds)) or
                        (now - s.get("last_seen", s.get("created_at", 0)) < max_idle_seconds)
                    )
            
            if not client_active:
                to_delete.append(sid)
                if not s.get("copied_to_server"):
                    try:
                        p = pathlib.Path(s["file_path"])
                        if p.exists():
                            p.unlink()
                    except Exception:
                        pass
        for sid in to_delete:
            _live_peer_shares.pop(sid, None)

@app.post("/api/peers/share")
async def create_live_peer_share(
    request: Request,
    file: UploadFile = File(...),
    client_id: Optional[str] = Form(None),
    device_name: Optional[str] = Form(None)
):
    """
    Live Peer Share: Broadcasts a file directly to all connected peers while active.
    Ephemeral and does NOT clutter permanent server hard drive storage unless copied.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected")
    
    cid = get_request_client_id(request, client_id)
    dname = device_name or ("Host" if cid == "host" else f"Peer ({cid[:6]})")
    suffix = pathlib.Path(file.filename).suffix.lower()
    is_photo = suffix in config.PHOTO_EXTENSIONS
    is_video = suffix in config.VIDEO_EXTENSIONS
    mtype = "photo" if is_photo else ("video" if is_video else "audio")
    
    share_id = str(uuid.uuid4())
    live_dir = config.STAGING_DIR / "live_shares"
    live_dir.mkdir(parents=True, exist_ok=True)
    temp_path = live_dir / f"{share_id}_{file.filename}"
    
    filesize = 0
    with open(temp_path, "wb") as buffer:
        while chunk := await file.read(1024 * 1024):
            filesize += len(chunk)
            buffer.write(chunk)
            
    now = time.time()
    with _clients_lock:
        if cid in _connected_clients:
            _connected_clients[cid]["last_seen"] = now
        else:
            _connected_clients[cid] = {
                "name": dname,
                "ip": request.client.host if request.client else "unknown",
                "last_seen": now
            }

    share_obj = {
        "id": share_id,
        "client_id": cid,
        "owner_id": cid,
        "owner_name": dname,
        "filename": file.filename,
        "title": pathlib.Path(file.filename).stem,
        "media_type": mtype,
        "filesize": filesize,
        "file_path": str(temp_path.resolve()),
        "created_at": now,
        "last_seen": now,
        "stream_url": f"/api/peers/shares/{share_id}/stream",
        "download_url": f"/api/peers/shares/{share_id}/download",
        "copied_to_server": False
    }
    
    with _shares_lock:
        _live_peer_shares[share_id] = share_obj
        
    return {
        "status": "ok",
        "message": f"Broadcasting '{file.filename}' live to all connected peers!",
        "share": share_obj
    }

@app.get("/api/peers/shares")
def get_live_peer_shares(
    request: Request,
    media_type: Optional[str] = Query(None),
    client_id: Optional[str] = Query(None)
):
    """Returns active live shares broadcast by connected peers."""
    cleanup_expired_live_shares()
    cid = get_request_client_id(request, client_id)
    with _shares_lock:
        shares = [dict(s) for s in _live_peer_shares.values()]
        
    if media_type and media_type != "all":
        shares = [s for s in shares if s.get("media_type") == media_type]
        
    for s in shares:
        s["is_owner"] = (s.get("client_id") == cid or (s.get("client_id") == "host" and cid == "host"))
        
    return {"shares": shares, "count": len(shares)}

@app.get("/api/peers/shares/{share_id}/stream")
def stream_live_peer_share(share_id: str, request: Request, download: bool = False):
    """Direct streaming of live peer media with Range seeking."""
    with _shares_lock:
        s = _live_peer_shares.get(share_id)
    if not s:
        raise HTTPException(status_code=404, detail="Live peer share not found or device disconnected")
        
    fpath = pathlib.Path(s["file_path"])
    if not fpath.exists():
        raise HTTPException(status_code=404, detail="Live share file not found")
        
    mime = "video/mp4" if s["media_type"] == "video" else ("image/jpeg" if s["media_type"] == "photo" else "audio/mpeg")
    dl_name = s["filename"] if download else None
    return streamer.stream_audio(str(fpath), request, mime, dl_name)

@app.get("/api/peers/shares/{share_id}/download")
def download_live_peer_share(share_id: str, request: Request):
    """Direct 1-click download of live peer media."""
    return stream_live_peer_share(share_id, request, download=True)

@app.post("/api/peers/shares/{share_id}/copy-to-server")
def copy_live_peer_share_to_server(share_id: str, request: Request):
    """
    Explicitly copies a live peer share into permanent server storage (e.g. D:\\MEDIA PLAYER\\VIDEOS)
    so it becomes accessible in CasaOS and stays permanently even after the peer leaves.
    """
    with _shares_lock:
        s = _live_peer_shares.get(share_id)
    if not s:
        raise HTTPException(status_code=404, detail="Live peer share not found or device disconnected")
        
    fpath = pathlib.Path(s["file_path"])
    if not fpath.exists():
        raise HTTPException(status_code=404, detail="Live share file not found")

    cid = s.get("client_id", "peer")
    dname = s.get("owner_name", "Peer")
    mtype = s.get("media_type", "video")

    if settings.is_upload_approval_required() and not is_host_admin(request):
        upload_id = str(uuid.uuid4())
        staging_dir = config.STAGING_DIR
        staging_dir.mkdir(parents=True, exist_ok=True)
        permanent_staging = staging_dir / f"{upload_id}_{s['filename']}"
        shutil.copy2(fpath, permanent_staging)
        database.add_pending_upload(
            upload_id=upload_id,
            filename=s["filename"],
            staging_path=str(permanent_staging.resolve()),
            filesize=s["filesize"],
            media_type=mtype,
            owner_id=cid,
            owner_name=dname,
            target_folder=str(settings.get_target_upload_folder(mtype))
        )
        return {
            "status": "pending",
            "message": f"'{s['filename']}' sent to Host Approval Queue before saving to server drive."
        }

    target_dir = settings.get_target_upload_folder(mtype)
    target_dir.mkdir(parents=True, exist_ok=True)
    dest_path = target_dir / s["filename"]

    # Copy to permanent server drive (e.g. D:\MEDIA PLAYER\VIDEOS)
    shutil.copy2(fpath, dest_path)
    
    if mtype == "photo":
        pitem = scanner.parse_photo_file(dest_path, owner_id=cid, owner_name=dname)
        if pitem: database.upsert_photo(pitem)
    else:
        mitem = scanner.parse_media_file(dest_path, folder_type=mtype, owner_id=cid, owner_name=dname)
        if mitem: database.upsert_song(mitem)
        
    threading.Thread(target=scanner.scan_library, daemon=True).start()
    
    with _shares_lock:
        s["copied_to_server"] = True
        s["server_path"] = str(dest_path)
        
    return {
        "status": "ok",
        "message": f"Permanently copied '{s['filename']}' to server ({target_dir.name}) for CasaOS!",
        "target_path": str(dest_path),
        "copied_to_server": True
    }

# --- Downloader & Upload API ---
@app.post("/api/upload")
async def upload_media_file(
    request: Request,
    file: UploadFile = File(...),
    client_id: Optional[str] = Form(None),
    device_name: Optional[str] = Form(None)
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected")
    
    cid = get_request_client_id(request, client_id)
    dname = device_name or ("Host" if cid == "host" else f"Peer ({cid[:6]})")
    suffix = pathlib.Path(file.filename).suffix.lower()
    is_photo = suffix in config.PHOTO_EXTENSIONS
    media_type = "photo" if is_photo else ("video" if suffix in config.VIDEO_EXTENSIONS else "audio")
    
    # Check if Host Approval Queue is active and client is not host
    if settings.is_upload_approval_required() and not is_host_admin(request):
        upload_id = str(uuid.uuid4())
        staging_dir = config.STAGING_DIR
        staging_dir.mkdir(parents=True, exist_ok=True)
        staging_path = staging_dir / f"{upload_id}_{file.filename}"
        filesize = 0
        with open(staging_path, "wb") as buffer:
            while chunk := await file.read(1024 * 1024):
                filesize += len(chunk)
                buffer.write(chunk)
        database.add_pending_upload(
            upload_id=upload_id,
            filename=file.filename,
            staging_path=str(staging_path.resolve()),
            filesize=filesize,
            media_type=media_type,
            owner_id=cid,
            owner_name=dname,
            target_folder=str(config.DEFAULT_PHOTO_DIR if is_photo else config.DEFAULT_MUSIC_DIR)
        )
        return {
            "status": "pending",
            "upload_id": upload_id,
            "filename": file.filename,
            "message": f"'{file.filename}' sent to host approval queue.",
            "owner_name": dname
        }

    target_dir = settings.get_target_upload_folder(media_type)
    target_dir.mkdir(parents=True, exist_ok=True)
    
    save_path = target_dir / file.filename
    with open(save_path, "wb") as buffer:
        while chunk := await file.read(1024 * 1024):
            buffer.write(chunk)
            
    # Parse and upsert with owner info
    if is_photo:
        photo_item = scanner.parse_photo_file(save_path, owner_id=cid, owner_name=dname)
        if photo_item:
            database.upsert_photo(photo_item)
        else:
            scanner.scan_library()
    else:
        media_item = scanner.parse_media_file(save_path, owner_id=cid, owner_name=dname)
        if media_item:
            database.upsert_song(media_item)
        else:
            scanner.scan_library()

    return {"status": "ok", "message": f"Successfully shared '{file.filename}' with everyone!", "filename": file.filename, "owner_name": dname}

@app.post("/api/upload/photos")
async def upload_photos_batch(
    request: Request,
    files: List[UploadFile] = File(...),
    client_id: Optional[str] = Form(None),
    device_name: Optional[str] = Form(None)
):
    cid = get_request_client_id(request, client_id)
    dname = device_name or ("Host" if cid == "host" else f"Peer ({cid[:6]})")
    approval_required = settings.is_upload_approval_required() and not is_host_admin(request)
    
    target_dir = config.DEFAULT_PHOTO_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    staging_dir = config.STAGING_DIR
    staging_dir.mkdir(parents=True, exist_ok=True)
    
    saved_count = 0
    pending_count = 0
    
    for f in files:
        if not f.filename:
            continue
        if approval_required:
            upload_id = str(uuid.uuid4())
            staging_path = staging_dir / f"{upload_id}_{f.filename}"
            filesize = 0
            with open(staging_path, "wb") as buffer:
                while chunk := await f.read(1024 * 1024):
                    filesize += len(chunk)
                    buffer.write(chunk)
            database.add_pending_upload(
                upload_id=upload_id,
                filename=f.filename,
                staging_path=str(staging_path.resolve()),
                filesize=filesize,
                media_type="photo",
                owner_id=cid,
                owner_name=dname,
                target_folder=str(target_dir)
            )
            pending_count += 1
        else:
            save_path = target_dir / f.filename
            with open(save_path, "wb") as buffer:
                while chunk := await f.read(1024 * 1024):
                    buffer.write(chunk)
            photo_item = scanner.parse_photo_file(save_path, owner_id=cid, owner_name=dname)
            if photo_item:
                database.upsert_photo(photo_item)
            saved_count += 1
            
    if saved_count > 0:
        threading.Thread(target=scanner.scan_library, daemon=True).start()
        
    return {
        "status": "ok",
        "saved_count": saved_count,
        "pending_count": pending_count,
        "message": f"Processed {len(files)} photos ({saved_count} added, {pending_count} pending approval)."
    }

# --- Host Approval Queue Endpoints ---
@app.get("/api/admin/pending-uploads")
def get_pending_uploads_endpoint(request: Request):
    if not is_host_admin(request):
        raise HTTPException(status_code=403, detail="Permission denied. Only host admin can view approval queue.")
    return {"pending": database.get_pending_uploads(status="pending")}

@app.post("/api/admin/pending-uploads/{upload_id}/approve")
def approve_pending_upload(upload_id: str, request: Request):
    if not is_host_admin(request):
        raise HTTPException(status_code=403, detail="Permission denied.")
    item = database.get_pending_upload(upload_id)
    if not item:
        raise HTTPException(status_code=404, detail="Upload request not found")
    
    staging_file = pathlib.Path(item["staging_path"])
    if not staging_file.exists():
        database.delete_pending_upload(upload_id)
        raise HTTPException(status_code=404, detail="Staged file missing on disk")
        
    current_settings = settings.load_settings()
    is_photo = staging_file.suffix.lower() in config.PHOTO_EXTENSIONS
    if is_photo:
        target_dir = config.DEFAULT_PHOTO_DIR
    else:
        target_dir = pathlib.Path(current_settings.get("download_dir", str(config.DEFAULT_MUSIC_DIR)))
    target_dir.mkdir(parents=True, exist_ok=True)
    
    dest_path = target_dir / item["filename"]
    if dest_path.exists():
        dest_path = target_dir / f"{staging_file.stem}_{uuid.uuid4().hex[:4]}{staging_file.suffix}"
    
    shutil.move(str(staging_file), str(dest_path))
    
    if is_photo:
        photo_item = scanner.parse_photo_file(dest_path, owner_id=item["owner_id"], owner_name=item["owner_name"])
        if photo_item:
            database.upsert_photo(photo_item)
    else:
        media_item = scanner.parse_media_file(dest_path, owner_id=item["owner_id"], owner_name=item["owner_name"])
        if media_item:
            database.upsert_song(media_item)
            
    database.update_pending_upload_status(upload_id, "approved")
    scanner.scan_library()
    return {"message": f"Approved '{item['filename']}' successfully", "status": "approved"}

@app.post("/api/admin/pending-uploads/{upload_id}/reject")
def reject_pending_upload(upload_id: str, request: Request):
    if not is_host_admin(request):
        raise HTTPException(status_code=403, detail="Permission denied.")
    item = database.get_pending_upload(upload_id)
    if not item:
        raise HTTPException(status_code=404, detail="Upload request not found")
        
    staging_file = pathlib.Path(item["staging_path"])
    if staging_file.exists():
        try:
            staging_file.unlink()
        except Exception:
            pass
            
    database.update_pending_upload_status(upload_id, "rejected")
    return {"message": f"Rejected '{item['filename']}'", "status": "rejected"}

@app.post("/api/download")
def enqueue_download(body: DownloadMediaRequest, request: Request):
    if not body.url.strip():
        raise HTTPException(status_code=400, detail="URL cannot be empty")
    cid = get_request_client_id(request, body.client_id)
    dname = body.device_name or ("Host" if cid == "host" else f"Peer ({cid[:6]})")
    try:
        task_id = downloader.start_download(
            url=body.url.strip(), media_format=body.format, quality=body.quality,
            destination=body.destination or "server", custom_folder=body.custom_folder,
            owner_id=cid, owner_name=dname
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    return {"task_id": task_id, "destination": body.destination or "server", "message": "Download started in background"}

@app.get("/api/downloads/status")
def get_downloads():
    return {"tasks": downloader.get_download_status()}

@app.post("/api/downloads/clear")
def clear_download_history():
    downloader.clear_downloads()
    return {"message": "Download history cleared", "tasks": downloader.get_download_status()}

@app.get("/api/downloads/{task_id}/file")
def get_downloaded_file(task_id: str):
    file_path = downloader.get_download_file(task_id)
    if not file_path or not file_path.exists():
        raise HTTPException(status_code=404, detail="Downloaded file not found")
    return FileResponse(
        str(file_path),
        filename=file_path.name,
        media_type="application/octet-stream",
    )

# --- Photos Endpoints ---
@app.get("/api/photos")
def list_photos(
    request: Request,
    query: Optional[str] = Query(None, description="Search term for title or album"),
    album: Optional[str] = Query(None, description="Filter by album"),
    year: Optional[int] = Query(None, description="Filter by year"),
    month: Optional[int] = Query(None, description="Filter by month"),
    client_id: Optional[str] = Query(None),
    favorites_only: bool = Query(False),
    scope: str = Query("all", description="'all', 'mine', or 'shared'"),
    limit: int = Query(500, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    cid = get_request_client_id(request, client_id)
    photos = database.get_photos(
        query=query,
        album=album,
        year=year,
        month=month,
        client_id=cid,
        favorites_only=favorites_only,
        scope=scope,
        limit=limit,
        offset=offset
    )
    return {"photos": photos, "count": len(photos)}

@app.get("/api/photos/timeline")
def get_photos_timeline():
    return {"timeline": database.get_photo_timeline()}

@app.get("/api/photos/albums")
def get_photos_albums():
    return {"albums": database.get_photo_albums()}

@app.get("/api/photo/{photo_id}")
def get_photo_detail(photo_id: str, request: Request, client_id: Optional[str] = Query(None)):
    cid = get_request_client_id(request, client_id)
    photo = database.get_photo(photo_id, client_id=cid)
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    return photo

@app.get("/api/photo/{photo_id}/thumb")
def get_photo_thumbnail(photo_id: str):
    photo = database.get_photo(photo_id)
    if not photo or not photo.get("thumb_hash"):
        raise HTTPException(status_code=404, detail="Photo or thumbnail not found")
    thumb_file = config.PHOTO_THUMBS_DIR / f"{photo['thumb_hash']}.jpg"
    if not thumb_file.exists():
        p_raw = pathlib.Path(photo["path"])
        if p_raw.exists():
            return FileResponse(str(p_raw), media_type=photo.get("mime_type", "image/jpeg"))
        raise HTTPException(status_code=404, detail="Thumbnail file missing")
    return FileResponse(str(thumb_file), media_type="image/jpeg", headers={"Cache-Control": "public, max-age=86400"})

@app.get("/api/photo/{photo_id}/raw")
def get_photo_raw(photo_id: str, download: bool = False):
    photo = database.get_photo(photo_id)
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    p = pathlib.Path(photo["path"])
    if not p.exists():
        raise HTTPException(status_code=404, detail="File on disk missing")
    headers = {}
    if download:
        headers["Content-Disposition"] = f'attachment; filename="{p.name}"'
    return FileResponse(str(p), media_type=photo.get("mime_type", "image/jpeg"), headers=headers)

@app.delete("/api/photo/{photo_id}")
def delete_photo_endpoint(photo_id: str, request: Request, client_id: Optional[str] = Query(None)):
    cid = get_request_client_id(request, client_id)
    photo = database.get_photo(photo_id)
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    owner_id = photo.get("owner_id") or "host"
    is_owner = (owner_id == cid) or (owner_id == "host" and is_host_admin(request)) or is_host_admin(request)
    if not is_owner:
        raise HTTPException(status_code=403, detail="Permission denied. Only the owner who shared this photo can delete it.")
    file_path = photo.get("path")
    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception:
            pass
    database.delete_photo(photo_id)
    return {"message": "Photo deleted successfully", "id": photo_id}

# --- 24-Hour Ephemeral Status / Stories Endpoints ---
@app.post("/api/status/post")
async def post_status_endpoint(
    request: Request,
    file: UploadFile = File(...),
    caption: Optional[str] = Form(""),
    client_id: Optional[str] = Form(None),
    device_name: Optional[str] = Form(None)
):
    """
    Snapchat-style 24-hour disappearing photo status update.
    Ideal for field workers, job-site check-ins, or casual sharing without cluttering server drive.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No photo file provided")
    
    cid = get_request_client_id(request, client_id)
    dname = device_name or ("Host" if cid == "host" else f"Peer ({cid[:6]})")
    
    suffix = pathlib.Path(file.filename).suffix.lower()
    if suffix not in config.PHOTO_EXTENSIONS and suffix not in config.VIDEO_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported format {suffix}. Please upload an image.")
    
    status_id = str(uuid.uuid4())
    safe_name = f"{status_id}_{pathlib.Path(file.filename).name}"
    save_path = config.STATUS_DIR / safe_name
    
    filesize = 0
    with open(save_path, "wb") as buffer:
        while chunk := await file.read(1024 * 1024):
            filesize += len(chunk)
            buffer.write(chunk)
            
    now = time.time()
    expires_at = now + 86400.0  # 24 hours
    
    mime_type = "image/jpeg"
    if suffix == ".png": mime_type = "image/png"
    elif suffix == ".webp": mime_type = "image/webp"
    elif suffix == ".gif": mime_type = "image/gif"
    elif suffix in config.VIDEO_EXTENSIONS: mime_type = "video/mp4"
    
    database.add_status(
        status_id=status_id,
        owner_id=cid,
        owner_name=dname,
        caption=caption.strip() if caption else "",
        file_path=str(save_path.resolve()),
        filename=file.filename,
        filesize=filesize,
        mime_type=mime_type,
        created_at=now,
        expires_at=expires_at
    )
    
    # Update client activity
    with _clients_lock:
        if cid in _connected_clients:
            _connected_clients[cid]["last_seen"] = now
        else:
            _connected_clients[cid] = {
                "name": dname,
                "ip": request.client.host if request.client else "unknown",
                "last_seen": now
            }
            
    return {
        "status": "ok",
        "message": f"Status published! Visible for 24 hours to all peers and host server.",
        "status_id": status_id,
        "expires_in_hours": 24
    }

@app.get("/api/status/active")
def get_active_statuses_endpoint(request: Request, client_id: Optional[str] = Query(None)):
    """
    Returns active 24-hour statuses grouped by worker/device with auto-pruning.
    """
    cid = get_request_client_id(request, client_id)
    now = time.time()
    
    # Inline prune of any expired items
    expired_paths = database.cleanup_expired_statuses(now)
    for p in expired_paths:
        try:
            pp = pathlib.Path(p)
            if pp.exists():
                pp.unlink()
        except Exception:
            pass
            
    active = database.get_active_statuses(now)
    groups_dict: Dict[str, Dict[str, Any]] = {}
    
    for s in active:
        oid = s["owner_id"]
        if oid not in groups_dict:
            groups_dict[oid] = {
                "owner_id": oid,
                "owner_name": s["owner_name"],
                "is_owner": (oid == cid) or (oid == "host" and cid == "host"),
                "latest_created_at": s["created_at"],
                "items": []
            }
        remaining_sec = max(0, int(s["expires_at"] - now))
        item = {
            "id": s["id"],
            "caption": s.get("caption", ""),
            "created_at": s["created_at"],
            "expires_at": s["expires_at"],
            "expires_in_seconds": remaining_sec,
            "filename": s["filename"],
            "filesize": s["filesize"],
            "mime_type": s["mime_type"],
            "is_saved": bool(s.get("is_saved")),
            "is_owner": (oid == cid) or (oid == "host" and cid == "host"),
            "image_url": f"/api/status/{s['id']}/image",
            "download_url": f"/api/status/{s['id']}/image?download=true"
        }
        groups_dict[oid]["items"].append(item)
        if s["created_at"] > groups_dict[oid]["latest_created_at"]:
            groups_dict[oid]["latest_created_at"] = s["created_at"]
            
    groups_list = list(groups_dict.values())
    groups_list.sort(key=lambda g: (0 if g["is_owner"] else 1, -g["latest_created_at"]))
    
    return {
        "groups": groups_list,
        "total_active": len(active),
        "server_time": now
    }

@app.get("/api/status/{status_id}/image")
def get_status_image_endpoint(status_id: str, download: bool = False):
    """Streams or downloads the status image file."""
    status = database.get_status(status_id)
    if not status:
        raise HTTPException(status_code=404, detail="Status not found or expired")
    fpath = pathlib.Path(status["file_path"])
    if not fpath.exists():
        raise HTTPException(status_code=404, detail="Status media file missing on server")
    headers = {}
    if download:
        headers["Content-Disposition"] = f'attachment; filename="{status["filename"]}"'
    return FileResponse(str(fpath), media_type=status.get("mime_type", "image/jpeg"), headers=headers)

@app.post("/api/status/{status_id}/save")
def save_status_to_permanent_library(status_id: str, request: Request):
    """
    Host or supervisor saves an important status photo permanently so it will NOT vanish after 24 hours.
    Copies it into the main server Photos library and indexes it in the database.
    """
    status = database.get_status(status_id)
    if not status:
        raise HTTPException(status_code=404, detail="Status not found or expired")
    fpath = pathlib.Path(status["file_path"])
    if not fpath.exists():
        raise HTTPException(status_code=404, detail="Status file missing on server")
        
    target_dir = settings.get_target_upload_folder("photo")
    target_dir.mkdir(parents=True, exist_ok=True)
    
    orig_name = pathlib.Path(status["filename"]).name
    dest_filename = f"Status_{int(status['created_at'])}_{orig_name}"
    dest_path = target_dir / dest_filename
    
    shutil.copy2(fpath, dest_path)
    
    cid = status.get("owner_id", "host")
    dname = status.get("owner_name", "Host")
    pitem = scanner.parse_photo_file(dest_path, owner_id=cid, owner_name=dname)
    saved_photo_id = None
    if pitem:
        if status.get("caption"):
            pitem["title"] = f"{status['caption']} ({orig_name})"
        database.upsert_photo(pitem)
        saved_photo_id = pitem.get("id")
    else:
        threading.Thread(target=scanner.scan_library, daemon=True).start()
        
    database.mark_status_saved(status_id, saved_photo_id)
    
    return {
        "status": "ok",
        "message": f"Successfully preserved '{orig_name}' in server Photos library! It will never vanish.",
        "dest_path": str(dest_path),
        "is_saved": True
    }

@app.delete("/api/status/{status_id}")
def delete_status_endpoint(status_id: str, request: Request, client_id: Optional[str] = Query(None)):
    """Deletes a status early (by owner or host admin)."""
    cid = get_request_client_id(request, client_id)
    status = database.get_status(status_id)
    if not status:
        raise HTTPException(status_code=404, detail="Status not found")
        
    owner_id = status.get("owner_id") or "host"
    is_owner = (owner_id == cid) or (owner_id == "host" and is_host_admin(request)) or is_host_admin(request)
    if not is_owner:
        raise HTTPException(status_code=403, detail="Permission denied. Only the uploader or host admin can delete this status.")
        
    fpath = pathlib.Path(status["file_path"])
    if fpath.exists():
        try:
            fpath.unlink()
        except Exception:
            pass
            
    database.delete_status(status_id)
    return {"status": "ok", "message": "Status deleted successfully"}

# --- Media Endpoints ---
@app.get("/api/songs")
def list_songs(
    request: Request,
    query: Optional[str] = Query(None, description="Search term for title, artist, or album"),
    artist: Optional[str] = Query(None, description="Filter by artist name"),
    album: Optional[str] = Query(None, description="Filter by album title"),
    genre: Optional[str] = Query(None, description="Filter by genre"),
    media_type: str = Query("audio", description="'audio', 'video', or 'all'"),
    sort_by: str = Query("title", description="Field to sort by"),
    ascending: bool = Query(True, description="Sort direction"),
    year: Optional[int] = Query(None, description="Filter by release year"),
    decade: Optional[str] = Query(None, description="Filter by decade (e.g. 2020s, 2010s)"),
    client_id: Optional[str] = Query(None),
    favorites_only: bool = Query(False),
    scope: str = Query("all", description="'all', 'mine', or 'shared'"),
    limit: int = Query(2000, ge=1, le=5000),
    offset: int = Query(0, ge=0),
):
    cid = get_request_client_id(request, client_id)
    songs = database.get_songs(
        query=query,
        artist=artist,
        album=album,
        genre=genre,
        media_type=media_type,
        sort_by=sort_by,
        ascending=ascending,
        client_id=cid,
        favorites_only=favorites_only,
        scope=scope,
        year=year,
        decade=decade,
        limit=limit,
        offset=offset
    )
    return {"songs": songs, "count": len(songs)}

@app.get("/api/videos")
def list_videos(
    request: Request,
    query: Optional[str] = Query(None, description="Search term for video title"),
    sort_by: str = Query("title", description="Field to sort by"),
    ascending: bool = Query(True, description="Sort direction"),
    year: Optional[int] = Query(None, description="Filter by release year"),
    decade: Optional[str] = Query(None, description="Filter by decade (e.g. 2020s, 2010s)"),
    resolution: Optional[str] = Query(None, description="Filter by resolution (e.g. 1080p, 4K)"),
    category: Optional[str] = Query(None, description="Filter by category ('movies', 'tv', 'all')"),
    client_id: Optional[str] = Query(None),
    favorites_only: bool = Query(False),
    scope: str = Query("all", description="'all', 'mine', or 'shared'"),
    limit: int = Query(500, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    cid = get_request_client_id(request, client_id)
    videos = database.get_videos(
        query=query,
        sort_by=sort_by,
        ascending=ascending,
        client_id=cid,
        favorites_only=favorites_only,
        scope=scope,
        year=year,
        decade=decade,
        resolution=resolution,
        video_category=category,
        limit=limit,
        offset=offset
    )
    return {"videos": videos, "count": len(videos)}

@app.put("/api/media/{media_id}")
def update_media_endpoint(media_id: str, body: UpdateMediaMetadataRequest, request: Request, client_id: Optional[str] = Query(None)):
    cid = get_request_client_id(request, client_id)
    song = database.get_song(media_id)
    if not song:
        raise HTTPException(status_code=404, detail="Media item not found")

    owner_id = song.get("owner_id") or "host"
    is_owner = (owner_id == cid) or (owner_id == "host" and is_host_admin(request)) or is_host_admin(request)
    if not is_owner:
        raise HTTPException(
            status_code=403,
            detail="Permission denied. Only the owner who shared this file or host admin can edit its metadata."
        )

    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    updated = database.update_media(media_id, updates)
    return {"status": "ok", "message": "Metadata updated successfully", "media": updated}

@app.get("/api/my-media")
def get_my_media(request: Request, client_id: Optional[str] = Query(None)):
    cid = get_request_client_id(request, client_id)
    my_songs = database.get_songs(media_type="audio", client_id=cid, scope="mine", limit=1000)
    my_videos = database.get_videos(client_id=cid, scope="mine", limit=500)
    return {
        "client_id": cid,
        "songs": my_songs,
        "videos": my_videos,
        "total_songs": len(my_songs),
        "total_videos": len(my_videos),
        "total_count": len(my_songs) + len(my_videos)
    }

@app.get("/api/favorites")
def list_favorites(
    request: Request,
    media_type: str = Query("all", description="'audio', 'video', or 'all'"),
    client_id: Optional[str] = Query(None),
    limit: int = Query(2000, ge=1, le=5000),
    offset: int = Query(0, ge=0)
):
    cid = get_request_client_id(request, client_id)
    items = database.get_songs(
        media_type=media_type,
        client_id=cid,
        favorites_only=True,
        limit=limit,
        offset=offset
    )
    return {"favorites": items, "count": len(items)}

@app.post("/api/media/{media_id}/favorite")
def toggle_media_favorite(media_id: str, request: Request, client_id: Optional[str] = Query(None)):
    cid = get_request_client_id(request, client_id)
    song = database.get_song(media_id)
    if not song:
        raise HTTPException(status_code=404, detail="Media item not found")
    is_fav = database.toggle_favorite(cid, media_id)
    return {"media_id": media_id, "is_favorite": is_fav}

@app.delete("/api/media/{media_id}")
def delete_media_item(media_id: str, request: Request, client_id: Optional[str] = Query(None)):
    cid = get_request_client_id(request, client_id)
    song = database.get_song(media_id)
    if not song:
        raise HTTPException(status_code=404, detail="Media item not found")
    
    # Ownership guard: Only the owner device or host admin can delete
    owner_id = song.get("owner_id") or "host"
    is_owner = (owner_id == cid) or (owner_id == "host" and is_host_admin(request)) or is_host_admin(request)
    if not is_owner:
        raise HTTPException(
            status_code=403,
            detail="Permission denied. Only the owner who shared this file can delete it."
        )

    # Delete the physical file from disk if it exists
    file_path = song.get("path")
    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception:
            pass

    database.delete_media(media_id)
    return {"message": "Media deleted successfully", "id": media_id}

@app.get("/api/song/{song_id}")
def get_song_details(song_id: str, request: Request, client_id: Optional[str] = Query(None)):
    cid = get_request_client_id(request, client_id)
    song = database.get_song(song_id, client_id=cid)
    if not song:
        raise HTTPException(status_code=404, detail="Media item not found")
    return song

@app.get("/api/artists")
def list_artists():
    artists = database.get_artists()
    return {"artists": artists, "count": len(artists)}

@app.get("/api/albums")
def list_albums(artist: Optional[str] = None):
    albums = database.get_albums(artist=artist)
    return {"albums": albums, "count": len(albums)}

@app.get("/api/stream/{song_id}")
def stream_media(song_id: str, request: Request, download: bool = False, compatible: bool = False):
    song = database.get_song(song_id)
    if not song:
        raise HTTPException(status_code=404, detail="Media not found")
    
    file_path = song["path"]
    filename = os.path.basename(file_path)
    mime_type = song.get("mime_type") or ("video/mp4" if song.get("media_type") == "video" else "audio/mpeg")
    download_filename = filename if download else None

    if compatible and not download:
        return streamer.compatible_media(file_path, song.get("media_type") == "video")
    return streamer.stream_audio(file_path, request, mime_type, download_filename)


@app.post("/api/playback/{song_id}/compatible")
def prepare_compatible_playback(song_id: str):
    song = database.get_song(song_id)
    if not song:
        raise HTTPException(status_code=404, detail="Media not found")
    return streamer.compatibility_job(song["path"], song.get("media_type") == "video", start=True)


@app.get("/api/playback/{song_id}/compatible")
def compatible_playback_status(song_id: str):
    song = database.get_song(song_id)
    if not song:
        raise HTTPException(status_code=404, detail="Media not found")
    return streamer.compatibility_job(song["path"], song.get("media_type") == "video")

@app.get("/api/cover/{song_id}")
def get_cover_art(song_id: str):
    song = database.get_song(song_id)
    if not song or not song.get("cover_hash"):
        raise HTTPException(status_code=404, detail="No cover art available")
    
    cover_file = config.COVERS_DIR / f"{song['cover_hash']}.jpg"
    if not cover_file.exists():
        raise HTTPException(status_code=404, detail="Cover art file missing")

    return FileResponse(str(cover_file), media_type="image/jpeg", headers={"Cache-Control": "public, max-age=86400"})

# --- Playlists ---
@app.get("/api/playlists")
def list_playlists():
    return {"playlists": database.get_playlists()}

@app.post("/api/playlists")
def create_new_playlist(body: CreatePlaylistRequest):
    if not body.name.strip():
        raise HTTPException(status_code=400, detail="Playlist name cannot be empty")
    pid = database.create_playlist(body.name.strip())
    return {"id": pid, "name": body.name.strip()}

@app.get("/api/playlists/{playlist_id}/songs")
def get_playlist_tracks(playlist_id: str):
    return {"songs": database.get_playlist_songs(playlist_id)}

@app.post("/api/playlists/{playlist_id}/songs/{song_id}")
def add_song_to_pl(playlist_id: str, song_id: str):
    database.add_song_to_playlist(playlist_id, song_id)
    return {"message": "Song added to playlist"}

@app.delete("/api/playlists/{playlist_id}")
def remove_playlist(playlist_id: str):
    database.delete_playlist(playlist_id)
    return {"message": "Playlist deleted"}

# --- Mesh Peers & Collective Library ---
@app.get("/api/mesh/peers")
def list_mesh_peers():
    peers = mesh.get_active_peers()
    now = time.time()
    with _clients_lock:
        active_clients = [c for c in _connected_clients.values() if now - c["last_seen"] < 60]
    return {
        "peers": peers,
        "count": len(peers),
        "clients": active_clients,
        "clients_count": len(active_clients)
    }

@app.get("/api/mesh/collective")
def get_collective_library():
    my_settings = settings.load_settings()
    local_songs = database.get_songs(media_type="all")
    for s in local_songs:
        s["source_device"] = my_settings.get("device_name", "My Device")
        s["source_url"] = ""

    local_photos = database.get_photos(limit=1000)
    for p in local_photos:
        p["source_device"] = my_settings.get("device_name", "My Device")
        p["source_url"] = ""

    all_media = list(local_songs)
    all_photos = list(local_photos)

    for peer in mesh.get_active_peers():
        peer_data = mesh.fetch_peer_library(peer["url"])
        for s in peer_data.get("songs", []):
            s["source_device"] = peer.get("device_name", "Peer")
            s["source_url"] = peer["url"]
            all_media.append(s)
        for p in peer_data.get("photos", []):
            p["source_device"] = peer.get("device_name", "Peer")
            p["source_url"] = peer["url"]
            all_photos.append(p)

    return {
        "media": all_media,
        "count": len(all_media),
        "photos": all_photos,
        "photos_count": len(all_photos),
        "peers_count": len(mesh.get_active_peers())
    }

# --- VLC & Smart TV M3U Playlist Endpoints ---
def generate_m3u_content(items: List[Dict[str, Any]], base_url: str) -> str:
    lines = ["#EXTM3U"]
    for item in items:
        media_id = item["id"]
        title = item.get("title") or "Unknown Title"
        artist = item.get("artist") or "Unknown Artist"
        duration = int(item.get("duration") or -1)
        media_type = item.get("media_type", "audio")
        group = "Movies & Videos" if media_type == "video" else "Music"
        
        logo_attr = f' tvg-logo="{base_url}/api/cover/{media_id}"' if item.get("cover_hash") else ''
        stream_url = f"{base_url}/api/stream/{media_id}"
        
        display_name = f"{artist} - {title}" if (media_type == "audio" and artist != "Unknown Artist") else title
        lines.append(f'#EXTINF:{duration} tvg-id="{media_id}" tvg-name="{title}"{logo_attr} group-title="{group}",{display_name}')
        lines.append(stream_url)
    return "\n".join(lines) + "\n"

@app.get("/api/playlist.m3u")
@app.get("/api/tv/playlist.m3u")
def get_m3u_playlist(request: Request, media_type: str = "all"):
    host = request.headers.get("host") or f"{mesh.get_local_ip()}:{config.PORT}"
    base_url = f"http://{host}"
    items = database.get_songs(media_type=media_type, limit=5000)
    m3u_text = generate_m3u_content(items, base_url)
    return Response(
        content=m3u_text,
        media_type="application/x-mpegurl",
        headers={"Content-Disposition": "inline; filename=mediahub_all.m3u"}
    )

@app.get("/api/playlist/movies.m3u")
def get_movies_m3u(request: Request):
    host = request.headers.get("host") or f"{mesh.get_local_ip()}:{config.PORT}"
    base_url = f"http://{host}"
    items = database.get_videos(limit=5000)
    m3u_text = generate_m3u_content(items, base_url)
    return Response(
        content=m3u_text,
        media_type="application/x-mpegurl",
        headers={"Content-Disposition": "inline; filename=mediahub_movies.m3u"}
    )

@app.get("/api/playlist/music.m3u")
def get_music_m3u(request: Request):
    host = request.headers.get("host") or f"{mesh.get_local_ip()}:{config.PORT}"
    base_url = f"http://{host}"
    items = database.get_songs(media_type="audio", limit=5000)
    m3u_text = generate_m3u_content(items, base_url)
    return Response(
        content=m3u_text,
        media_type="application/x-mpegurl",
        headers={"Content-Disposition": "inline; filename=mediahub_music.m3u"}
    )

# --- UPnP / DLNA Endpoints ---
@app.get("/dlna/desc.xml")
def get_dlna_desc(request: Request):
    host = request.headers.get("host") or f"{mesh.get_local_ip()}:{config.PORT}"
    base_url = f"http://{host}"
    return Response(content=dlna.get_desc_xml(base_url), media_type="application/xml")

@app.get("/dlna/content_directory.xml")
def get_dlna_cd_scpd():
    return Response(content=dlna.get_content_directory_scpd(), media_type="application/xml")

@app.get("/dlna/connection_manager.xml")
def get_dlna_cm_scpd():
    return Response(content=dlna.get_connection_manager_scpd(), media_type="application/xml")

@app.post("/dlna/control")
async def handle_dlna_control(request: Request):
    body = await request.body()
    body_str = body.decode("utf-8", errors="ignore")
    host = request.headers.get("host") or f"{mesh.get_local_ip()}:{config.PORT}"
    base_url = f"http://{host}"

    object_id = "0"
    starting_index = 0
    requested_count = 100

    import re
    obj_match = re.search(r'<ObjectID>(.*?)</ObjectID>', body_str)
    if obj_match:
        object_id = obj_match.group(1).strip()
    idx_match = re.search(r'<StartingIndex>(.*?)</StartingIndex>', body_str)
    if idx_match:
        try:
            starting_index = int(idx_match.group(1).strip())
        except Exception:
            pass
    cnt_match = re.search(r'<RequestedCount>(.*?)</RequestedCount>', body_str)
    if cnt_match:
        try:
            requested_count = int(cnt_match.group(1).strip()) or 100
        except Exception:
            pass

    didl, num_returned, total_matches = dlna.build_didl_browse(object_id, base_url, starting_index, requested_count)
    import xml.sax.saxutils as saxutils
    escaped_didl = saxutils.escape(didl)

    soap_resp = f"""<?xml version="1.0" encoding="utf-8"?>
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
  <s:Body>
    <u:BrowseResponse xmlns:u="urn:schemas-upnp-org:service:ContentDirectory:1">
      <Result>{escaped_didl}</Result>
      <NumberReturned>{num_returned}</NumberReturned>
      <TotalMatches>{total_matches}</TotalMatches>
      <UpdateID>1</UpdateID>
    </u:BrowseResponse>
  </s:Body>
</s:Envelope>"""
    return Response(content=soap_resp, media_type="text/xml; charset=utf-8")

@app.get("/tv")
def get_tv_page():
    tv_file = config.BASE_DIR / "static" / "tv.html"
    if tv_file.exists():
        return FileResponse(str(tv_file), media_type="text/html")
    return RedirectResponse(url="/")

# Mount Static Web App Frontend
static_dir = config.BASE_DIR / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=config.HOST, port=config.PORT, reload=True)

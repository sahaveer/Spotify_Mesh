import os
import re
import io
import time
import urllib.parse
import pathlib
import threading
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

# Connected Client Tracker
_connected_clients: Dict[str, Dict[str, Any]] = {}
_clients_lock = threading.Lock()

@asynccontextmanager
async def lifespan(app: FastAPI):
    database.init_db()
    # Trigger initial library scan
    threading.Thread(target=scanner.scan_library, daemon=True).start()
    # Start Zeroconf peer discovery broadcast
    threading.Thread(target=mesh.start_mesh_service, daemon=True).start()
    yield
    mesh.stop_mesh_service()

app = FastAPI(title="Decentralized Media Hub", version="2.0.0", lifespan=lifespan)

# Allow CORS for mobile web apps & native clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic Schemas
class CreatePlaylistRequest(BaseModel):
    name: str

class UpdateSettingsRequest(BaseModel):
    device_name: Optional[str] = None
    sharing_enabled: Optional[bool] = None
    download_dir: Optional[str] = None

class AddFolderRequest(BaseModel):
    path: str
    name: Optional[str] = None
    type: str = "both"  # "music", "video", "both"

class DownloadMediaRequest(BaseModel):
    url: str
    format: str = "audio"  # "audio" or "video"
    quality: str = "best"   # "best", "1080p", "720p"
    custom_folder: Optional[str] = None
    client_id: Optional[str] = None
    device_name: Optional[str] = None

class ClientPingRequest(BaseModel):
    client_id: str
    device_name: Optional[str] = "Web Player"
    user_agent: Optional[str] = None

def get_request_client_id(request: Request, explicit_client_id: Optional[str] = None) -> str:
    if explicit_client_id and explicit_client_id.strip():
        return explicit_client_id.strip()
    header_client_id = request.headers.get("x-client-id")
    if header_client_id and header_client_id.strip():
        return header_client_id.strip()
    return "host"

def is_host_admin(request: Request) -> bool:
    client_ip = request.client.host if request.client else ""
    return client_ip in ("127.0.0.1", "::1", "localhost")

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

@app.get("/api/status")
def get_server_status():
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

    return {
        "status": "online",
        "device_id": current_settings.get("device_id"),
        "device_name": current_settings.get("device_name", "MediaHub"),
        "sharing_enabled": current_settings.get("sharing_enabled", True),
        "shared_folders": [f["path"] for f in current_settings.get("shared_folders", []) if f.get("enabled", True)],
        "local_ip": local_ip,
        "available_ips": available_ips,
        "port": config.PORT,
        "connect_url": f"http://{local_ip}:{config.PORT}",
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
    return settings.load_settings()

@app.post("/api/settings")
def update_settings(body: UpdateSettingsRequest):
    current = settings.load_settings()
    if body.device_name is not None:
        current["device_name"] = body.device_name.strip()
    if body.sharing_enabled is not None:
        current["sharing_enabled"] = body.sharing_enabled
    if body.download_dir is not None:
        current["download_dir"] = body.download_dir.strip()
    settings.save_settings(current)
    # Trigger rescan to apply privacy mode
    scanner.scan_library()
    return current

@app.post("/api/settings/folders")
def add_folder_to_shared(body: AddFolderRequest):
    try:
        new_item = settings.add_shared_folder(body.path, body.name, body.type)
        scanner.scan_library()
        return new_item
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/api/settings/folders/{folder_id}")
def delete_shared_folder(folder_id: str):
    removed = settings.remove_shared_folder(folder_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Folder not found in settings")
    scanner.scan_library()
    return {"message": "Folder removed from sharing"}

@app.post("/api/settings/folders/{folder_id}/toggle")
def toggle_folder(folder_id: str, enabled: bool = Query(True)):
    toggled = settings.toggle_shared_folder(folder_id, enabled)
    if not toggled:
        raise HTTPException(status_code=404, detail="Folder not found")
    scanner.scan_library()
    return {"message": f"Folder sharing set to {enabled}"}

@app.post("/api/scan")
def trigger_scan(background_tasks: BackgroundTasks, full: bool = False):
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
        current_settings = settings.load_settings()
        target_dir = pathlib.Path(current_settings.get("download_dir", str(config.DEFAULT_MUSIC_DIR)))
        target_dir.mkdir(parents=True, exist_ok=True)

        saved_count = 0
        for f in files:
            if f.filename:
                save_path = target_dir / f.filename
                with open(save_path, "wb") as buffer:
                    while chunk := await f.read(1024 * 1024):
                        buffer.write(chunk)
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
    
    current_settings = settings.load_settings()
    target_dir = pathlib.Path(current_settings.get("download_dir", str(config.DEFAULT_MUSIC_DIR)))
    target_dir.mkdir(parents=True, exist_ok=True)
    
    save_path = target_dir / file.filename
    with open(save_path, "wb") as buffer:
        while chunk := await file.read(1024 * 1024):
            buffer.write(chunk)
            
    # Parse and upsert with owner info
    media_item = scanner.parse_media_file(save_path, owner_id=cid, owner_name=dname)
    if media_item:
        database.upsert_song(media_item)
    else:
        # Trigger background scan fallback
        scanner.scan_library()

    return {"message": f"Successfully shared '{file.filename}' with everyone!", "filename": file.filename, "owner_name": dname}

@app.post("/api/download")
def enqueue_download(body: DownloadMediaRequest, request: Request):
    if not body.url.strip():
        raise HTTPException(status_code=400, detail="URL cannot be empty")
    cid = get_request_client_id(request, body.client_id)
    dname = body.device_name or ("Host" if cid == "host" else f"Peer ({cid[:6]})")
    task_id = downloader.start_download(
        url=body.url.strip(),
        media_format=body.format,
        quality=body.quality,
        custom_folder=body.custom_folder,
        owner_id=cid,
        owner_name=dname
    )
    return {"task_id": task_id, "message": "Download started in background"}

@app.get("/api/downloads/status")
def get_downloads():
    return {"tasks": downloader.get_download_status()}

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
        limit=limit,
        offset=offset
    )
    return {"videos": videos, "count": len(videos)}

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
def stream_media(song_id: str, request: Request, download: bool = False):
    song = database.get_song(song_id)
    if not song:
        raise HTTPException(status_code=404, detail="Media not found")
    
    file_path = song["path"]
    filename = os.path.basename(file_path)
    mime_type = song.get("mime_type", "video/mp4" if song.get("media_type") == "video" else "audio/mpeg")
    download_filename = filename if download else None

    return streamer.stream_audio(file_path, request, mime_type, download_filename)

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

    all_media = list(local_songs)
    for peer in mesh.get_active_peers():
        peer_data = mesh.fetch_peer_library(peer["url"])
        for s in peer_data.get("songs", []):
            s["source_device"] = peer.get("device_name", "Peer")
            s["source_url"] = peer["url"]
            all_media.append(s)

    return {"media": all_media, "count": len(all_media), "peers_count": len(mesh.get_active_peers())}

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

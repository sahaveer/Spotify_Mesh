import os
import pathlib
import wave
import struct
import math
from fastapi.testclient import TestClient

import config
import settings
import database
import scanner
import streamer
import downloader
import mesh
from main import app

def generate_sample_wav(file_path: pathlib.Path, duration_secs: int = 2):
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(file_path), 'w') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(44100)
        for i in range(44100 * duration_secs):
            val = int(32767.0 * 0.5 * math.sin(2.0 * math.pi * 440.0 * (i / 44100)))
            wav_file.writeframesraw(struct.pack('<h', val))

def generate_dummy_video(file_path: pathlib.Path):
    file_path.parent.mkdir(parents=True, exist_ok=True)
    # Simple dummy mp4 container bytes (ftyp atom)
    data = b'\x00\x00\x00\x20ftypisom\x00\x00\x02\x00isomiso2mp41' + b'\x00' * 50000
    with open(file_path, "wb") as f:
        f.write(data)

def generate_sample_image(file_path: pathlib.Path, width: int = 600, height: int = 400):
    from PIL import Image, ImageDraw
    file_path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new('RGB', (width, height), color=(73, 109, 137))
    d = ImageDraw.Draw(img)
    d.text((10, 10), "Test Photo", fill=(255, 255, 0))
    img.save(file_path, "JPEG")

def test_decentralized_hub():
    original_settings = settings.load_settings()
    print("[1] Testing Privacy & Settings Management...")
    test_music_dir = config.BASE_DIR / "data" / "test_music"
    test_music_dir.mkdir(parents=True, exist_ok=True)
    for p in test_music_dir.glob("*"):
        if p.is_file(): p.unlink()
    sample_song = test_music_dir / "Test Artist - Epic Track.wav"
    generate_sample_wav(sample_song, 2)

    test_video_dir = config.BASE_DIR / "data" / "test_videos"
    test_video_dir.mkdir(parents=True, exist_ok=True)
    for p in test_video_dir.glob("*"):
        if p.is_file(): p.unlink()
    sample_video = test_video_dir / "Sample Movie Trailer.mp4"
    generate_dummy_video(sample_video)

    # Configure explicitly shared folders
    settings.set_master_sharing(True)
    settings.set_device_name("Test Hub Node")
    settings.add_shared_folder(str(test_music_dir), "Test Music", "music")
    settings.add_shared_folder(str(test_video_dir), "Test Videos", "video")

    active_folders = settings.get_active_shared_folders()
    assert len(active_folders) >= 2
    print("[PASS] Privacy and folder configuration passed")

    print("[2] Testing Media Scanner (Audio & Video)...")
    scan_res = scanner.scan_library(full_rescan=True)
    stats = scan_res["stats"]
    print(f"Scan Stats: Songs={stats['total_songs']}, Videos={stats['total_videos']}")
    assert stats["total_songs"] > 0
    assert stats["total_videos"] > 0
    print("[PASS] Media scanner indexed both audio and video files")

    print("[3] Testing Stealth Mode (Master Privacy OFF)...")
    settings.set_master_sharing(False)
    stealth_scan = scanner.scan_library()
    stealth_stats = database.get_stats()
    assert stealth_stats["total_songs"] == 0
    assert stealth_stats["total_videos"] == 0
    print("[PASS] Stealth mode properly hidden all shared files")

    # Restore master sharing
    settings.set_master_sharing(True)
    scanner.scan_library(full_rescan=True)

    print("[4] Testing API Endpoints via TestClient...")
    client = TestClient(app)

    # Status & Privacy
    res = client.get("/api/status")
    assert res.status_code == 200
    assert res.json()["sharing_enabled"] is True
    print("[PASS] /api/status passed")

    # Songs & Videos API
    res = client.get("/api/songs")
    assert res.status_code == 200
    assert res.json()["count"] > 0
    song_id = res.json()["songs"][0]["id"]
    print("[PASS] /api/songs passed")

    res = client.get("/api/videos")
    assert res.status_code == 200
    assert res.json()["count"] > 0
    video_id = res.json()["videos"][0]["id"]
    print("[PASS] /api/videos passed")

    # Audio & Video Streaming with Range Seeking
    res = client.get(f"/api/stream/{video_id}", headers={"Range": "bytes=0-1024"})
    assert res.status_code == 206
    assert res.headers["content-range"].startswith("bytes 0-1024/")
    print("[PASS] /api/stream (Video Range Seeking) passed")

    # Save to Device (Wi-Fi Download)
    res = client.get(f"/api/stream/{song_id}?download=true")
    assert res.status_code == 200
    assert "attachment" in res.headers.get("content-disposition", "")
    print("[PASS] /api/stream (Direct Wi-Fi Download attachment) passed")

    # Downloader Task Creation & Smart Resolution
    resolved_query, hint_query = downloader._resolve_media_url("Viva La Vida")
    assert resolved_query == "ytsearch1:Viva La Vida"
    assert hint_query == "Viva La Vida"

    resolved_spot, hint_spot = downloader._resolve_media_url("https://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT")
    assert resolved_spot.startswith("ytsearch1:")
    assert hint_spot is not None

    res = client.post("/api/download", json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "format": "audio"})
    assert res.status_code == 200
    task_id = res.json()["task_id"]
    assert task_id is not None

    res = client.get("/api/downloads/status")
    assert res.status_code == 200
    assert len(res.json()["tasks"]) > 0

    clear_res = client.post("/api/downloads/clear")
    assert clear_res.status_code == 200
    print("[PASS] /api/download, smart Spotify/query resolver, and clear history passed")

    # QR Code Endpoint
    res = client.get("/api/qr")
    assert res.status_code == 200
    assert res.headers["content-type"] == "image/png"
    assert len(res.content) > 100
    print("[PASS] /api/qr (High-res QR Code generation) passed")

    # Client Heartbeat Ping & Connected Devices
    res = client.post("/api/client/ping", json={"client_id": "test_phone_123", "device_name": "Test Android Phone", "user_agent": "Mozilla/5.0 (Android)"})
    assert res.status_code == 200
    
    res = client.get("/api/clients")
    assert res.status_code == 200
    assert res.json()["count"] >= 1
    print("[PASS] /api/client/ping and /api/clients passed")

    # Wi-Fi Mesh Discovery & Collective Library
    res = client.get("/api/mesh/peers")
    assert res.status_code == 200
    assert "clients" in res.json()
    assert res.json()["clients_count"] >= 1
    print("[PASS] /api/mesh/peers with connected clients passed")

    res = client.get("/api/mesh/collective")
    assert res.status_code == 200
    assert res.json()["count"] > 0
    print("[PASS] /api/mesh collective library passed")

    # VLC & Smart TV M3U Playlists
    res = client.get("/api/playlist.m3u")
    assert res.status_code == 200
    assert "#EXTM3U" in res.text
    assert "#EXTINF" in res.text
    assert "/api/stream/" in res.text
    print("[PASS] /api/playlist.m3u (VLC / IPTV M3U Playlist generation) passed")

    res = client.get("/api/playlist/movies.m3u")
    assert res.status_code == 200
    assert "#EXTM3U" in res.text
    print("[PASS] /api/playlist/movies.m3u passed")

    res = client.get("/api/playlist/music.m3u")
    assert res.status_code == 200
    assert "#EXTM3U" in res.text
    print("[PASS] /api/playlist/music.m3u passed")

    # Smart TV 10-Foot UI Route
    res = client.get("/tv")
    assert res.status_code == 200
    assert "MediaHub TV" in res.text
    print("[PASS] /tv (Smart TV 10-Foot Remote UI) passed")

    print("[5] Testing Love / Favorites API & Device Isolation...")
    client_a = "user_iphone_a"
    client_b = "user_android_b"

    # User A favorites the song
    fav_res = client.post(f"/api/media/{song_id}/favorite", headers={"X-Client-Id": client_a})
    assert fav_res.status_code == 200
    assert fav_res.json()["is_favorite"] is True

    # User A checks favorites (count should be 1)
    res_a = client.get("/api/favorites", headers={"X-Client-Id": client_a})
    assert res_a.status_code == 200
    assert res_a.json()["count"] == 1
    assert res_a.json()["favorites"][0]["id"] == song_id
    assert res_a.json()["favorites"][0]["is_favorite"] is True

    # User B checks favorites (should be 0 because favorites are private to device)
    res_b = client.get("/api/favorites", headers={"X-Client-Id": client_b})
    assert res_b.status_code == 200
    assert res_b.json()["count"] == 0

    # User A unfavorites the song
    unfav_res = client.post(f"/api/media/{song_id}/favorite", headers={"X-Client-Id": client_a})
    assert unfav_res.status_code == 200
    assert unfav_res.json()["is_favorite"] is False

    res_a_empty = client.get("/api/favorites", headers={"X-Client-Id": client_a})
    assert res_a_empty.json()["count"] == 0
    print("[PASS] Favorites toggle & client isolation verified")

    print("[6] Testing Upload Ownership & Strict Delete Security...")
    # Simulate peer uploading a custom song from their mobile
    upload_file_path = config.BASE_DIR / "data" / "temp_peer_source.wav"
    generate_sample_wav(upload_file_path, 1)

    dest_upload_path = config.DEFAULT_MUSIC_DIR / "peer_special_track.wav"
    if dest_upload_path.exists():
        dest_upload_path.unlink()

    peer_owner_id = "phone_owner_789"
    peer_device_name = "Sahaveer Mobile"

    with open(upload_file_path, "rb") as f:
        upload_res = client.post(
            "/api/upload",
            files={"file": ("peer_special_track.wav", f, "audio/wav")},
            data={"client_id": peer_owner_id, "device_name": peer_device_name}
        )
    assert upload_res.status_code == 200

    # Find the uploaded track
    songs_res = client.get("/api/songs?query=peer_special_track", headers={"X-Client-Id": peer_owner_id})
    assert songs_res.status_code == 200
    matched_songs = songs_res.json()["songs"]
    assert len(matched_songs) > 0
    uploaded_song = matched_songs[0]
    uploaded_song_id = uploaded_song["id"]
    assert uploaded_song["owner_id"] == peer_owner_id
    assert uploaded_song["is_owner"] is True
    assert uploaded_song["owner_name"] == peer_device_name

    # [7] Testing /api/my-media & Scope Separation
    my_media_res = client.get("/api/my-media", headers={"X-Client-Id": peer_owner_id})
    assert my_media_res.status_code == 200
    my_media_data = my_media_res.json()
    assert my_media_data["total_songs"] == 1
    assert my_media_data["songs"][0]["id"] == uploaded_song_id
    print("[PASS] /api/my-media returned peer's own isolated library")

    # Scope filtering: scope=mine vs scope=shared vs scope=server vs scope=peers
    mine_res = client.get("/api/songs?scope=mine", headers={"X-Client-Id": peer_owner_id})
    assert mine_res.status_code == 200
    assert len(mine_res.json()["songs"]) == 1
    assert mine_res.json()["songs"][0]["id"] == uploaded_song_id

    shared_res = client.get("/api/songs?scope=shared", headers={"X-Client-Id": peer_owner_id})
    assert shared_res.status_code == 200
    # Shared files from others should NOT contain peer's own uploaded track
    assert all(s["id"] != uploaded_song_id for s in shared_res.json()["songs"])

    server_res = client.get("/api/songs?scope=server")
    assert server_res.status_code == 200
    assert all(s.get("owner_id") in ("host", None) for s in server_res.json()["songs"])

    peers_res = client.get("/api/songs?scope=peers")
    assert peers_res.status_code == 200
    assert any(s["id"] == uploaded_song_id for s in peers_res.json()["songs"])

    connected_peers_res = client.get("/api/peers/connected")
    assert connected_peers_res.status_code == 200
    assert any(p["id"] == peer_owner_id for p in connected_peers_res.json()["peers"])

    print("[PASS] Media library scope filtering ('all', 'server', 'mine', 'peers') and connected peers verified")

    # Check from a viewing peer's perspective (non-owner)
    stranger_client_id = "stranger_device_999"
    stranger_view = client.get("/api/songs?query=peer_special_track", headers={"X-Client-Id": stranger_client_id})
    assert stranger_view.json()["songs"][0]["is_owner"] is False

    # Non-owner remote client attempts to delete someone else's file -> MUST be HTTP 403 Forbidden!
    remote_client = TestClient(app, client=("8.8.8.8", 54321))

    # [8] Testing Remote Peer Host Settings Protection (403 Forbidden for remote peers)
    rem_settings = remote_client.post("/api/settings", json={"device_name": "Hijacked Hub"})
    assert rem_settings.status_code == 403
    rem_folder_add = remote_client.post("/api/settings/folders", json={"path": "/bad/path", "name": "Bad"})
    assert rem_folder_add.status_code == 403
    rem_folder_del = remote_client.delete("/api/settings/folders/some-id")
    assert rem_folder_del.status_code == 403
    rem_scan = remote_client.post("/api/scan")
    assert rem_scan.status_code == 403
    print("[PASS] Remote peer settings & folder protection (403 Forbidden) verified")

    del_forbidden = remote_client.delete(
        f"/api/media/{uploaded_song_id}",
        headers={"X-Client-Id": stranger_client_id}
    )
    assert del_forbidden.status_code == 403
    assert "Only the owner who shared this file can delete it" in del_forbidden.json()["detail"]
    print("[PASS] Non-owner delete rejection (403 Forbidden) verified")

    # The actual owner deletes their own file -> MUST be HTTP 200 OK
    del_allowed = remote_client.delete(
        f"/api/media/{uploaded_song_id}",
        headers={"X-Client-Id": peer_owner_id}
    )
    assert del_allowed.status_code == 200
    assert del_allowed.json()["message"] == "Media deleted successfully"

    # Verify song is deleted from DB
    check_deleted = client.get(f"/api/song/{uploaded_song_id}")
    assert check_deleted.status_code == 404
    print("[PASS] Owner authorized deletion verified")

    # Localhost Host Admin deletion check on host files
    admin_del = client.delete(f"/api/media/{song_id}")
    assert admin_del.status_code == 200
    print("[PASS] Localhost admin deletion verified")

    print("[7] Testing Dual-Mode (Mesh + Worldwide Global Access)...")
    import tunnel
    # Status endpoint includes global information
    status_res = client.get("/api/status")
    assert status_res.status_code == 200
    data = status_res.json()
    assert "global_enabled" in data
    assert "global_status" in data
    assert "global_url" in data
    assert "local_ip" in data
    assert "connect_url" in data
    print("[PASS] /api/status dual-mode fields verified")

    # Tunnel status endpoint
    tun_status = client.get("/api/tunnel/status")
    assert tun_status.status_code == 200
    assert "status" in tun_status.json()
    assert "is_active" in tun_status.json()
    print("[PASS] /api/tunnel/status endpoint verified")

    # Peer cannot start/stop tunnel (403 Forbidden)
    tun_forbidden = remote_client.post("/api/tunnel/start")
    assert tun_forbidden.status_code == 403
    tun_stop_forbidden = remote_client.post("/api/tunnel/stop")
    assert tun_stop_forbidden.status_code == 403
    print("[PASS] Peer unauthorized tunnel control rejection (403 Forbidden) verified")

    # Settings persistence
    settings.set_global_access(False)
    assert settings.is_global_access_enabled() is False
    settings.set_global_access(True)
    assert settings.is_global_access_enabled() is True
    print("[PASS] Global access setting persistence verified (default: True)")

    print("[8] Testing Tailscale WireGuard Mesh & Admin Trust...")
    import run_server
    assert run_server.is_tailscale_ip("100.85.20.10") is True
    assert run_server.is_tailscale_ip("100.120.45.67") is True
    assert run_server.is_tailscale_ip("192.168.1.50") is False
    assert run_server.is_tailscale_ip("8.8.8.8") is False

    # Tailscale client should be recognized as admin
    tailscale_client = TestClient(app, client=("100.85.20.10", 45678))
    ts_status = tailscale_client.get("/api/status")
    assert ts_status.status_code == 200
    assert ts_status.json()["is_admin"] is True
    print("[PASS] Tailscale IP recognized and authorized as remote admin")

    print("[9] Testing Photo Sharing, EXIF Extraction & Thumbnails...")
    test_photo_dir = config.BASE_DIR / "data" / "test_photos"
    test_photo_dir.mkdir(parents=True, exist_ok=True)
    sample_photo = test_photo_dir / "Sunset_Beach_Vacation.jpg"
    generate_sample_image(sample_photo, 800, 600)

    settings.add_shared_folder(str(test_photo_dir), "Test Photos", "photos")
    scanner.scan_library(full_rescan=True)

    photos_res = client.get("/api/photos")
    assert photos_res.status_code == 200
    photos = photos_res.json()["photos"]
    assert len(photos) > 0
    test_photo = photos[0]
    assert test_photo["width"] == 800
    assert test_photo["height"] == 600
    assert test_photo["thumb_hash"] is not None

    # Test thumbnail endpoint
    thumb_res = client.get(f"/api/photo/{test_photo['id']}/thumb")
    assert thumb_res.status_code == 200
    assert thumb_res.headers["content-type"] == "image/jpeg"

    # Test raw photo endpoint
    raw_res = client.get(f"/api/photo/{test_photo['id']}/raw")
    assert raw_res.status_code == 200

    # Test photo timeline
    timeline_res = client.get("/api/photos/timeline")
    assert timeline_res.status_code == 200
    assert len(timeline_res.json()["timeline"]) > 0
    print("[PASS] Photo indexing, thumbnail generation, timeline & API verified")

    print("[10] Testing Host Approval Queue & Peer Upload Policy...")
    # Enable approval queue
    settings.set_upload_approval_required(True)
    assert settings.is_upload_approval_required() is True

    # Peer uploads a file -> should be queued as pending
    dummy_audio_bytes = b"RIFF....WAVEfmt ...." + b"\x00" * 2000
    upload_resp = remote_client.post(
        "/api/upload",
        files={"file": ("remote_peer_song.mp3", dummy_audio_bytes, "audio/mpeg")},
        data={"client_id": "peer_client_999", "device_name": "Friend Phone"}
    )
    assert upload_resp.status_code == 200
    upload_data = upload_resp.json()
    assert upload_data["status"] == "pending"
    pending_id = upload_data["upload_id"]

    # Host admin views pending uploads
    pending_list_res = client.get("/api/admin/pending-uploads")
    assert pending_list_res.status_code == 200
    pending_items = pending_list_res.json()["pending"]
    assert any(p["id"] == pending_id for p in pending_items)

    # Remote peer cannot view pending uploads (403 Forbidden)
    assert remote_client.get("/api/admin/pending-uploads").status_code == 403

    # Host approves upload
    approve_res = client.post(f"/api/admin/pending-uploads/{pending_id}/approve")
    assert approve_res.status_code == 200
    assert approve_res.json()["status"] == "approved"
    print("[PASS] Upload approval queue, peer isolation & admin review verified")

    # Reset approval queue to False
    settings.set_upload_approval_required(False)

    print("[11] Testing Downloader Dual-Mode Destination...")
    # Test client destination download initialization
    dl_task_id = downloader.start_download(
        url="https://example.com/mock_media.mp4",
        media_format="video",
        destination="client",
        owner_id="test_client",
        owner_name="Test Peer"
    )
    status = downloader.get_download_status(dl_task_id)
    assert status is not None
    assert status["destination"] == "client"
    print("[PASS] Downloader client destination parameter verified")

    print("[12] Testing UPnP / DLNA Discovery & XML Endpoints...")
    dlna_desc = client.get("/dlna/desc.xml")
    assert dlna_desc.status_code == 200
    assert "urn:schemas-upnp-org:device:MediaServer:1" in dlna_desc.text
    assert "ContentDirectory" in dlna_desc.text

    dlna_cd = client.get("/dlna/content_directory.xml")
    assert dlna_cd.status_code == 200
    assert "GetSystemUpdateID" in dlna_cd.text
    assert "Browse" in dlna_cd.text

    # Test DLNA SOAP Browse request
    soap_browse = """<?xml version="1.0"?>
    <s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
      <s:Body>
        <u:Browse xmlns:u="urn:schemas-upnp-org:service:ContentDirectory:1">
          <ObjectID>0</ObjectID>
          <BrowseFlag>BrowseDirectChildren</BrowseFlag>
        </u:Browse>
      </s:Body>
    </s:Envelope>"""
    soap_res = client.post("/dlna/control", content=soap_browse, headers={"Content-Type": "text/xml"})
    assert soap_res.status_code == 200
    assert "BrowseResponse" in soap_res.text
    assert "music_root" in soap_res.text
    print("[PASS] UPnP/DLNA description, SCPD & SOAP Browse action verified")

    print("[13] Testing Live Peer Sharing (Ephemeral P2P Broadcast & Zero Server Clutter)...")
    from main import _live_peer_shares, cleanup_expired_live_shares, _connected_clients
    import io, time
    fake_video = io.BytesIO(b"fake video binary stream data for peer sharing")
    fake_video.name = "test_live_video.mp4"
    phone_headers = {"X-Client-Id": "peer-phone-99", "X-Forwarded-For": "192.168.1.155"}
    res = client.post(
        "/api/peers/share",
        data={"client_id": "peer-phone-99", "device_name": "Sahaveer iPhone"},
        files={"file": ("test_live_video.mp4", fake_video, "video/mp4")},
        headers=phone_headers
    )
    assert res.status_code == 200
    share_id = res.json()["share"]["id"]

    # Remote peer sees share with is_owner = False
    laptop_headers = {"X-Client-Id": "laptop-44", "X-Forwarded-For": "192.168.1.180"}
    res = client.get("/api/peers/shares?media_type=video", headers=laptop_headers)
    assert res.status_code == 200
    shares = res.json()["shares"]
    target = next(s for s in shares if s["id"] == share_id)
    assert target["is_owner"] is False

    # Stream & Download
    res = client.get(f"/api/peers/shares/{share_id}/stream", headers={"Range": "bytes=0-5"})
    assert res.status_code in (200, 206)
    res = client.get(f"/api/peers/shares/{share_id}/download")
    assert res.status_code == 200 and "attachment" in res.headers.get("content-disposition", "")

    # 1-Click Copy to Server (CasaOS Storage)
    res = client.post(f"/api/peers/shares/{share_id}/copy-to-server", headers=phone_headers)
    assert res.status_code == 200
    body = res.json()
    assert body["copied_to_server"] is True
    assert os.path.exists(body["target_path"])
    try:
        os.remove(body["target_path"])
    except Exception:
        pass

    # Ephemeral Departure Cleanup
    _connected_clients["peer-phone-99"]["last_seen"] = time.time() - 300
    _live_peer_shares[share_id]["last_seen"] = time.time() - 300
    _live_peer_shares[share_id]["created_at"] = time.time() - 300
    _live_peer_shares[share_id]["copied_to_server"] = False
    cleanup_expired_live_shares(max_idle_seconds=60)
    assert share_id not in _live_peer_shares
    print("[PASS] Live peer ephemeral sharing, Range streaming, 1-click download, CasaOS copy & auto-cleanup verified")

    print("\n[SUCCESS] ALL DECENTRALIZED HUB, PHOTOS, DOWNLOADER, APPROVAL QUEUE, DLNA & LIVE PEER SHARING TESTS PASSED SUCCESSFULLY!")
    # Restore user production settings so test folders do not pollute media library
    settings.save_settings(original_settings)
    scanner.scan_library()

if __name__ == "__main__":
    test_decentralized_hub()

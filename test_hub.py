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

def test_decentralized_hub():
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

    # Downloader Task Creation
    res = client.post("/api/download", json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "format": "audio"})
    assert res.status_code == 200
    task_id = res.json()["task_id"]
    assert task_id is not None

    res = client.get("/api/downloads/status")
    assert res.status_code == 200
    assert len(res.json()["tasks"]) > 0
    print("[PASS] /api/download and /api/downloads/status passed")

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

    # Scope filtering: scope=mine vs scope=shared
    mine_res = client.get("/api/songs?scope=mine", headers={"X-Client-Id": peer_owner_id})
    assert mine_res.status_code == 200
    assert len(mine_res.json()["songs"]) == 1
    assert mine_res.json()["songs"][0]["id"] == uploaded_song_id

    shared_res = client.get("/api/songs?scope=shared", headers={"X-Client-Id": peer_owner_id})
    assert shared_res.status_code == 200
    # Shared files from others should NOT contain peer's own uploaded track
    assert all(s["id"] != uploaded_song_id for s in shared_res.json()["songs"])
    print("[PASS] Media library scope filtering ('all', 'mine', 'shared') verified")

    # Check from a viewing peer's perspective (non-owner)
    stranger_client_id = "stranger_device_999"
    stranger_view = client.get("/api/songs?query=peer_special_track", headers={"X-Client-Id": stranger_client_id})
    assert stranger_view.json()["songs"][0]["is_owner"] is False

    # A non-owner remote client attempts to delete someone else's file -> MUST be HTTP 403 Forbidden!
    remote_client = TestClient(app, client=("192.168.1.88", 54321))
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

    print("\n[SUCCESS] ALL DECENTRALIZED HUB, FAVORITES & SECURITY TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_decentralized_hub()

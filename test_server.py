import os
import pathlib
import wave
import struct
import math
from fastapi.testclient import TestClient

import config
import database
import scanner
from main import app

def generate_sample_wav(file_path: pathlib.Path, duration_secs: int = 3, freq: float = 440.0):
    """Generates a simple sine wave WAV audio file for testing."""
    sample_rate = 44100
    n_samples = int(sample_rate * duration_secs)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(file_path), 'w') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        for i in range(n_samples):
            val = int(32767.0 * 0.5 * math.sin(2.0 * math.pi * freq * (i / sample_rate)))
            data = struct.pack('<h', val)
            wav_file.writeframesraw(data)

def test_full_flow():
    print("[1] Generating sample audio file...")
    test_music_dir = config.BASE_DIR / "data" / "test_music"
    test_music_dir.mkdir(parents=True, exist_ok=True)
    sample_song_path = test_music_dir / "Test Artist - Beautiful Song.wav"
    generate_sample_wav(sample_song_path, duration_secs=2)

    # Configure scanner to scan test dir
    config.MUSIC_DIRS.append(test_music_dir)

    print("[2] Running library scan...")
    scan_result = scanner.scan_library(full_rescan=True)
    print(f"Scan result: {scan_result}")
    assert scan_result["scanned_files"] > 0, "No audio files scanned!"

    print("[3] Testing database queries...")
    stats = database.get_stats()
    print(f"Stats: {stats}")
    assert stats["total_songs"] > 0, "No songs in DB!"

    songs = database.get_songs()
    assert len(songs) > 0
    song = songs[0]
    song_id = song["id"]
    print(f"Sample song in DB: id={song_id}, title={song['title']}, artist={song['artist']}")

    print("[4] Testing API endpoints via TestClient...")
    client = TestClient(app)

    # Status
    res = client.get("/api/status")
    assert res.status_code == 200
    assert res.json()["status"] == "online"
    print("[PASS] /api/status passed")

    # Songs List
    res = client.get("/api/songs")
    assert res.status_code == 200
    assert res.json()["count"] > 0
    print("[PASS] /api/songs passed")

    # Full Audio Stream
    res = client.get(f"/api/stream/{song_id}")
    assert res.status_code == 200
    assert res.headers["accept-ranges"] == "bytes"
    assert len(res.content) > 0
    print(f"[PASS] /api/stream (Full) passed - Received {len(res.content)} bytes")

    # Partial Audio Stream (Range Request)
    headers = {"Range": "bytes=0-499"}
    res = client.get(f"/api/stream/{song_id}", headers=headers)
    assert res.status_code == 206
    assert res.headers["content-range"].startswith("bytes 0-499/")
    assert len(res.content) == 500
    print("[PASS] /api/stream (HTTP 206 Partial Content Range Seeking) passed")

    # Playlist Creation & Adding Track
    res = client.post("/api/playlists", json={"name": "My Favorites"})
    assert res.status_code == 200
    pl_id = res.json()["id"]

    res = client.post(f"/api/playlists/{pl_id}/songs/{song_id}")
    assert res.status_code == 200

    res = client.get(f"/api/playlists/{pl_id}/songs")
    assert res.status_code == 200
    assert len(res.json()["songs"]) == 1
    print("[PASS] /api/playlists CRUD passed")

    # Static Web App
    res = client.get("/")
    assert res.status_code == 200
    assert "Cloud Media Player" in res.text
    print("[PASS] Web App index.html serving passed")

    print("\n[SUCCESS] ALL TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_full_flow()

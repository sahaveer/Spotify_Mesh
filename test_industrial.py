import zipfile
import io
import unittest
from fastapi.testclient import TestClient
from main import app
import database

class TestIndustrialPlayer(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_genres_languages_years(self):
        # 1. Genres
        res = self.client.get("/api/genres?media_type=audio")
        self.assertEqual(res.status_code, 200)
        genres = res.json().get("genres", [])
        self.assertIsInstance(genres, list)

        # 2. Languages
        res = self.client.get("/api/languages?media_type=audio")
        self.assertEqual(res.status_code, 200)
        languages = res.json().get("languages", [])
        self.assertIsInstance(languages, list)

        # 3. Years & Decades
        res = self.client.get("/api/years?media_type=audio")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("decades", data)
        self.assertIn("years", data)

    def test_filtering_and_metadata_language(self):
        songs = self.client.get("/api/songs").json().get("songs", [])
        self.assertTrue(len(songs) > 0, "Expected at least one song in library")
        test_song = songs[0]

        # Update metadata with language and genre
        res = self.client.put(f"/api/media/{test_song['id']}", json={
            "language": "Hindi",
            "genre": "Bollywood"
        })
        self.assertEqual(res.status_code, 200)

        # Verify filtering by language
        res = self.client.get("/api/songs?language=Hindi")
        self.assertEqual(res.status_code, 200)
        filtered = res.json().get("songs", [])
        self.assertTrue(any(s["id"] == test_song["id"] for s in filtered))

        # Verify filtering by genre
        res = self.client.get("/api/songs?genre=Bollywood")
        self.assertEqual(res.status_code, 200)
        filtered_genre = res.json().get("songs", [])
        self.assertTrue(any(s["id"] == test_song["id"] for s in filtered_genre))

    def test_playlist_lifecycle_and_exports(self):
        songs = self.client.get("/api/songs").json().get("songs", [])
        test_song = songs[0]

        # 1. Create Playlist
        res = self.client.post("/api/playlists", json={
            "name": "Industrial Automation Playlist",
            "description": "High-fidelity industrial audio test"
        })
        self.assertEqual(res.status_code, 200)
        pl_id = res.json().get("id")
        self.assertTrue(pl_id)

        # 2. Add songs to playlist
        res = self.client.post(f"/api/playlists/{pl_id}/songs", json={
            "song_ids": [test_song["id"]]
        })
        self.assertEqual(res.status_code, 200)

        # 3. Get playlist detail
        res = self.client.get(f"/api/playlists/{pl_id}")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        pl = data["playlist"]
        songs = data["songs"]
        self.assertEqual(pl["name"], "Industrial Automation Playlist")
        self.assertEqual(pl["description"], "High-fidelity industrial audio test")
        self.assertEqual(len(songs), 1)

        # 4. Check listing has sample_covers and total_duration
        res = self.client.get("/api/playlists")
        self.assertEqual(res.status_code, 200)
        pls = res.json().get("playlists", [])
        matched = next(p for p in pls if p["id"] == pl_id)
        self.assertIn("sample_covers", matched)
        self.assertIn("total_duration", matched)

        # 5. Export M3U
        res = self.client.get(f"/api/playlists/{pl_id}/export.m3u")
        self.assertEqual(res.status_code, 200)
        self.assertIn("#EXTM3U", res.text)
        self.assertIn(test_song["title"], res.text)

        # 6. Full Playlist ZIP download
        res = self.client.get(f"/api/playlists/{pl_id}/download")
        self.assertEqual(res.status_code, 200)
        zf = zipfile.ZipFile(io.BytesIO(res.content))
        self.assertGreaterEqual(len(zf.namelist()), 1)

        # 7. Batch Song ZIP download
        res = self.client.post("/api/songs/download-zip", json={
            "song_ids": [test_song["id"]],
            "zip_name": "test_batch.zip"
        })
        self.assertEqual(res.status_code, 200)
        zf_batch = zipfile.ZipFile(io.BytesIO(res.content))
        self.assertGreaterEqual(len(zf_batch.namelist()), 1)

        # 8. Remove song and delete playlist
        res = self.client.delete(f"/api/playlists/{pl_id}/songs/{test_song['id']}")
        self.assertEqual(res.status_code, 200)
        res = self.client.delete(f"/api/playlists/{pl_id}")
        self.assertEqual(res.status_code, 200)

    def test_smart_playlists_and_combinations(self):
        songs = self.client.get("/api/songs").json().get("songs", [])
        self.assertTrue(len(songs) > 0)
        s1 = songs[0]

        # Tag s1 as 1995 Telugu Devotional
        self.client.put(f"/api/media/{s1['id']}", json={
            "year": 1995,
            "language": "Telugu",
            "genre": "Devotional"
        })

        # 1. Check auto-generated smart groups API
        res = self.client.get("/api/playlists/smart")
        self.assertEqual(res.status_code, 200)
        smart_groups = res.json().get("smart_playlists", [])
        self.assertIsInstance(smart_groups, list)
        titles = [sg["name"] for sg in smart_groups]
        # Should include combinations like "1990s TELUGU" or "DEVOTIONAL TELUGU"
        self.assertTrue(any("1990s" in t and "TELUGU" in t for t in titles) or any("DEVOTIONAL" in t and "TELUGU" in t for t in titles))

        # 2. Query virtual smart playlist directly by smart ID
        smart_id = "smart:era-lang:1990s:Telugu"
        res = self.client.get(f"/api/playlists/{smart_id}")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["playlist"]["name"], "1990s TELUGU")
        self.assertTrue(any(s["id"] == s1["id"] for s in data["songs"]))

        # 3. Create persistent custom smart playlist with criteria
        res = self.client.post("/api/playlists", json={
            "name": "Custom 1990s Telugu",
            "is_smart": True,
            "criteria": {
                "decade": "1990s",
                "language": "Telugu"
            }
        })
        self.assertEqual(res.status_code, 200)
        created_pl = res.json()
        pl_id = created_pl["id"]

        # Check detail returns matching songs
        res = self.client.get(f"/api/playlists/{pl_id}")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(any(s["id"] == s1["id"] for s in res.json()["songs"]))

        # Cleanup
        self.client.delete(f"/api/playlists/{pl_id}")

    def test_import_m3u_playlist(self):
        songs = self.client.get("/api/songs").json().get("songs", [])
        self.assertTrue(len(songs) > 0)
        s1 = songs[0]

        # Construct an M3U content referencing s1
        m3u_text = f"""#EXTM3U
#EXTINF:{int(s1.get('duration', 180))},{s1.get('artist', 'Artist')} - {s1.get('title', 'Title')}
{s1.get('path', 'dummy.mp3')}
"""
        files = {
            "file": ("roadtrip.m3u", io.BytesIO(m3u_text.encode("utf-8")), "audio/x-mpegurl")
        }
        res = self.client.post("/api/playlists/import", files=files)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["name"], "roadtrip")
        self.assertEqual(data["total_tracks"], 1)
        self.assertGreaterEqual(data["matched_tracks"], 1)
        imported_id = data["playlist_id"]

        # Verify imported playlist songs
        res = self.client.get(f"/api/playlists/{imported_id}/songs")
        self.assertEqual(res.status_code, 200)
        imported_songs = res.json().get("songs", [])
        self.assertEqual(len(imported_songs), 1)
        self.assertEqual(imported_songs[0]["id"], s1["id"])

        # Cleanup
        self.client.delete(f"/api/playlists/{imported_id}")

if __name__ == "__main__":
    unittest.main()

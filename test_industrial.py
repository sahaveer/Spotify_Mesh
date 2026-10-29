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

if __name__ == "__main__":
    unittest.main()

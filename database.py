import sqlite3
import uuid
import datetime
from typing import List, Optional, Dict, Any
from config import DB_PATH

def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS songs (
                id TEXT PRIMARY KEY,
                path TEXT UNIQUE,
                title TEXT,
                artist TEXT,
                album TEXT,
                album_artist TEXT,
                year INTEGER,
                genre TEXT,
                track_number INTEGER,
                disc_number INTEGER,
                duration REAL,
                bitrate INTEGER,
                filesize INTEGER,
                mtime REAL,
                cover_hash TEXT,
                mime_type TEXT,
                media_type TEXT DEFAULT 'audio',
                resolution TEXT,
                owner_id TEXT DEFAULT 'host',
                owner_name TEXT DEFAULT 'Host'
            )
        """)
        
        # Check and add new columns if migrating from older schema
        cursor.execute("PRAGMA table_info(songs)")
        existing_cols = {col["name"] for col in cursor.fetchall()}
        if "media_type" not in existing_cols:
            cursor.execute("ALTER TABLE songs ADD COLUMN media_type TEXT DEFAULT 'audio'")
        if "resolution" not in existing_cols:
            cursor.execute("ALTER TABLE songs ADD COLUMN resolution TEXT")
        if "owner_id" not in existing_cols:
            cursor.execute("ALTER TABLE songs ADD COLUMN owner_id TEXT DEFAULT 'host'")
        if "owner_name" not in existing_cols:
            cursor.execute("ALTER TABLE songs ADD COLUMN owner_name TEXT DEFAULT 'Host'")

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_songs_artist ON songs(artist)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_songs_album ON songs(album)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_songs_title ON songs(title)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_songs_media_type ON songs(media_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_songs_owner_id ON songs(owner_id)")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS playlists (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS playlist_songs (
                playlist_id TEXT,
                song_id TEXT,
                position INTEGER,
                PRIMARY KEY (playlist_id, song_id),
                FOREIGN KEY (playlist_id) REFERENCES playlists(id) ON DELETE CASCADE,
                FOREIGN KEY (song_id) REFERENCES songs(id) ON DELETE CASCADE
            )
        """)

        # Favorites Table (Client / Device specific)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS favorites (
                client_id TEXT NOT NULL,
                media_id TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (client_id, media_id),
                FOREIGN KEY (media_id) REFERENCES songs(id) ON DELETE CASCADE
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_favorites_client ON favorites(client_id)")
        conn.commit()

def upsert_song(song_data: Dict[str, Any]):
    if "media_type" not in song_data:
        song_data["media_type"] = "audio"
    if "resolution" not in song_data:
        song_data["resolution"] = None
    if "owner_id" not in song_data or not song_data["owner_id"]:
        song_data["owner_id"] = "host"
    if "owner_name" not in song_data or not song_data["owner_name"]:
        song_data["owner_name"] = "Host"

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO songs (
                id, path, title, artist, album, album_artist, year, genre,
                track_number, disc_number, duration, bitrate, filesize, mtime, cover_hash, mime_type,
                media_type, resolution, owner_id, owner_name
            ) VALUES (
                :id, :path, :title, :artist, :album, :album_artist, :year, :genre,
                :track_number, :disc_number, :duration, :bitrate, :filesize, :mtime, :cover_hash, :mime_type,
                :media_type, :resolution, :owner_id, :owner_name
            )
            ON CONFLICT(path) DO UPDATE SET
                title = excluded.title,
                artist = excluded.artist,
                album = excluded.album,
                album_artist = excluded.album_artist,
                year = excluded.year,
                genre = excluded.genre,
                track_number = excluded.track_number,
                disc_number = excluded.disc_number,
                duration = excluded.duration,
                bitrate = excluded.bitrate,
                filesize = excluded.filesize,
                mtime = excluded.mtime,
                cover_hash = excluded.cover_hash,
                mime_type = excluded.mime_type,
                media_type = excluded.media_type,
                resolution = excluded.resolution,
                owner_id = CASE WHEN excluded.owner_id IS NOT NULL AND excluded.owner_id != 'host' THEN excluded.owner_id ELSE COALESCE(songs.owner_id, 'host') END,
                owner_name = CASE WHEN excluded.owner_id IS NOT NULL AND excluded.owner_id != 'host' THEN excluded.owner_name ELSE COALESCE(songs.owner_name, 'Host') END
        """, song_data)
        conn.commit()

def toggle_favorite(client_id: str, media_id: str) -> bool:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM favorites WHERE client_id = ? AND media_id = ?", (client_id, media_id))
        exists = cursor.fetchone() is not None
        if exists:
            cursor.execute("DELETE FROM favorites WHERE client_id = ? AND media_id = ?", (client_id, media_id))
            conn.commit()
            return False
        else:
            cursor.execute("INSERT OR IGNORE INTO favorites (client_id, media_id) VALUES (?, ?)", (client_id, media_id))
            conn.commit()
            return True

def is_favorite(client_id: str, media_id: str) -> bool:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM favorites WHERE client_id = ? AND media_id = ?", (client_id, media_id))
        return cursor.fetchone() is not None

def delete_media(media_id: str) -> Optional[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM songs WHERE id = ?", (media_id,))
        row = cursor.fetchone()
        if not row:
            return None
        song_dict = dict(row)
        cursor.execute("DELETE FROM playlist_songs WHERE song_id = ?", (media_id,))
        cursor.execute("DELETE FROM favorites WHERE media_id = ?", (media_id,))
        cursor.execute("DELETE FROM songs WHERE id = ?", (media_id,))
        conn.commit()
        return song_dict

def clear_all_media():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM songs")
        conn.commit()

def delete_songs_not_in_paths(valid_paths: List[str]):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT path FROM songs")
        all_db_paths = [row["path"] for row in cursor.fetchall()]
        valid_set = set(valid_paths)
        to_delete = [p for p in all_db_paths if p not in valid_set]
        
        if to_delete:
            cursor.executemany("DELETE FROM songs WHERE path = ?", [(p,) for p in to_delete])
            conn.commit()

def get_song(song_id: str, client_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if client_id:
            cursor.execute("""
                SELECT songs.*,
                       EXISTS(SELECT 1 FROM favorites f WHERE f.media_id = songs.id AND f.client_id = ?) AS is_favorite,
                       (songs.owner_id = ? OR (songs.owner_id = 'host' AND ? = 'host')) AS is_owner
                FROM songs WHERE id = ?
            """, (client_id, client_id, client_id, song_id))
        else:
            cursor.execute("SELECT songs.*, 0 AS is_favorite, 0 AS is_owner FROM songs WHERE id = ?", (song_id,))
        row = cursor.fetchone()
        if not row:
            return None
        res = dict(row)
        res["is_favorite"] = bool(res.get("is_favorite", 0))
        res["is_owner"] = bool(res.get("is_owner", 0))
        return res

def get_songs(
    query: Optional[str] = None,
    artist: Optional[str] = None,
    album: Optional[str] = None,
    genre: Optional[str] = None,
    media_type: str = "audio",  # 'audio', 'video', or 'all'
    sort_by: str = "title",
    ascending: bool = True,
    client_id: Optional[str] = None,
    favorites_only: bool = False,
    scope: str = "all",  # 'all', 'mine', 'shared'
    limit: int = 2000,
    offset: int = 0
) -> List[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        select_fields = ["songs.*"]
        params = []
        
        if client_id:
            select_fields.append("EXISTS(SELECT 1 FROM favorites f WHERE f.media_id = songs.id AND f.client_id = ?) AS is_favorite")
            params.append(client_id)
            select_fields.append("(songs.owner_id = ? OR (songs.owner_id = 'host' AND ? = 'host')) AS is_owner")
            params.extend([client_id, client_id])
        else:
            select_fields.append("0 AS is_favorite")
            select_fields.append("0 AS is_owner")

        sql = f"SELECT {', '.join(select_fields)} FROM songs WHERE 1=1"

        if media_type != "all":
            sql += " AND media_type = ?"
            params.append(media_type)

        if favorites_only and client_id:
            sql += " AND EXISTS(SELECT 1 FROM favorites f WHERE f.media_id = songs.id AND f.client_id = ?)"
            params.append(client_id)

        if scope == "mine" and client_id:
            if client_id == "host":
                sql += " AND songs.owner_id = 'host'"
            else:
                sql += " AND songs.owner_id = ?"
                params.append(client_id)
        elif scope == "shared" and client_id:
            if client_id == "host":
                sql += " AND songs.owner_id != 'host'"
            else:
                sql += " AND (songs.owner_id != ? OR songs.owner_id IS NULL)"
                params.append(client_id)

        if query:
            sql += " AND (title LIKE ? OR artist LIKE ? OR album LIKE ?)"
            pattern = f"%{query}%"
            params.extend([pattern, pattern, pattern])

        if artist:
            sql += " AND (artist = ? OR album_artist = ?)"
            params.extend([artist, artist])

        if album:
            sql += " AND album = ?"
            params.append(album)

        if genre:
            sql += " AND genre = ?"
            params.append(genre)

        allowed_sorts = {"title", "artist", "album", "year", "duration", "track_number", "filesize"}
        if sort_by not in allowed_sorts:
            sort_by = "title"

        order = "ASC" if ascending else "DESC"
        if sort_by == "track_number":
            sql += f" ORDER BY disc_number {order}, track_number {order}, title {order}"
        else:
            sql += f" ORDER BY {sort_by} {order}"

        sql += " LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor.execute(sql, params)
        rows = [dict(row) for row in cursor.fetchall()]
        for r in rows:
            r["is_favorite"] = bool(r.get("is_favorite", 0))
            r["is_owner"] = bool(r.get("is_owner", 0))
        return rows

def get_videos(query: Optional[str] = None, sort_by: str = "title", ascending: bool = True, client_id: Optional[str] = None, favorites_only: bool = False, scope: str = "all", limit: int = 500, offset: int = 0) -> List[Dict[str, Any]]:
    return get_songs(query=query, media_type="video", sort_by=sort_by, ascending=ascending, client_id=client_id, favorites_only=favorites_only, scope=scope, limit=limit, offset=offset)

def get_artists() -> List[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                artist,
                COUNT(id) AS song_count,
                COUNT(DISTINCT album) AS album_count,
                MAX(cover_hash) AS cover_hash
            FROM songs 
            WHERE media_type = 'audio' AND artist IS NOT NULL AND artist != ''
            GROUP BY artist 
            ORDER BY artist ASC
        """)
        return [dict(row) for row in cursor.fetchall()]

def get_albums(artist: Optional[str] = None) -> List[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if artist:
            cursor.execute("""
                SELECT 
                    album,
                    artist,
                    year,
                    COUNT(id) AS song_count,
                    MAX(cover_hash) AS cover_hash
                FROM songs 
                WHERE media_type = 'audio' AND album IS NOT NULL AND album != '' AND (artist = ? OR album_artist = ?)
                GROUP BY album, artist 
                ORDER BY year DESC, album ASC
            """, (artist, artist))
        else:
            cursor.execute("""
                SELECT 
                    album,
                    artist,
                    year,
                    COUNT(id) AS song_count,
                    MAX(cover_hash) AS cover_hash
                FROM songs 
                WHERE media_type = 'audio' AND album IS NOT NULL AND album != ''
                GROUP BY album, artist 
                ORDER BY album ASC
            """)
        return [dict(row) for row in cursor.fetchall()]

def get_stats() -> Dict[str, Any]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                COUNT(CASE WHEN media_type = 'audio' THEN 1 END) AS total_songs,
                COUNT(CASE WHEN media_type = 'video' THEN 1 END) AS total_videos,
                COUNT(DISTINCT CASE WHEN media_type = 'audio' THEN artist END) AS total_artists,
                COUNT(DISTINCT CASE WHEN media_type = 'audio' THEN album END) AS total_albums,
                COALESCE(SUM(duration), 0) AS total_duration,
                COALESCE(SUM(filesize), 0) AS total_size
            FROM songs
        """)
        row = cursor.fetchone()
        return dict(row) if row else {
            "total_songs": 0, "total_videos": 0, "total_artists": 0, "total_albums": 0, "total_duration": 0, "total_size": 0
        }

# Playlists
def create_playlist(name: str) -> str:
    pid = str(uuid.uuid4())
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO playlists (id, name) VALUES (?, ?)", (pid, name))
        conn.commit()
    return pid

def get_playlists() -> List[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.id, p.name, p.created_at, COUNT(ps.song_id) as song_count
            FROM playlists p
            LEFT JOIN playlist_songs ps ON p.id = ps.playlist_id
            GROUP BY p.id
            ORDER BY p.name ASC
        """)
        return [dict(row) for row in cursor.fetchall()]

def get_playlist_songs(playlist_id: str) -> List[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT s.* FROM songs s
            JOIN playlist_songs ps ON s.id = ps.song_id
            WHERE ps.playlist_id = ?
            ORDER BY ps.position ASC
        """, (playlist_id,))
        return [dict(row) for row in cursor.fetchall()]

def add_song_to_playlist(playlist_id: str, song_id: str):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COALESCE(MAX(position), -1) + 1 FROM playlist_songs WHERE playlist_id = ?", (playlist_id,))
        next_pos = cursor.fetchone()[0]
        cursor.execute("""
            INSERT OR IGNORE INTO playlist_songs (playlist_id, song_id, position)
            VALUES (?, ?, ?)
        """, (playlist_id, song_id, next_pos))
        conn.commit()

def delete_playlist(playlist_id: str):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM playlist_songs WHERE playlist_id = ?", (playlist_id,))
        cursor.execute("DELETE FROM playlists WHERE id = ?", (playlist_id,))
        conn.commit()

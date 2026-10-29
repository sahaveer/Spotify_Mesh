import sqlite3
import uuid
import datetime
from typing import List, Optional, Dict, Any
from config import DB_PATH

def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False, timeout=30.0)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
    except Exception:
        pass
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
        if "season" not in existing_cols:
            cursor.execute("ALTER TABLE songs ADD COLUMN season INTEGER")
        if "episode" not in existing_cols:
            cursor.execute("ALTER TABLE songs ADD COLUMN episode INTEGER")
        if "language" not in existing_cols:
            cursor.execute("ALTER TABLE songs ADD COLUMN language TEXT DEFAULT 'Unknown'")

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_songs_artist ON songs(artist)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_songs_album ON songs(album)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_songs_title ON songs(title)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_songs_genre ON songs(genre)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_songs_language ON songs(language)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_songs_media_type ON songs(media_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_songs_owner_id ON songs(owner_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_songs_year ON songs(year)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_songs_resolution ON songs(resolution)")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS playlists (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("PRAGMA table_info(playlists)")
        pl_cols = {col["name"] for col in cursor.fetchall()}
        if "description" not in pl_cols:
            cursor.execute("ALTER TABLE playlists ADD COLUMN description TEXT DEFAULT ''")

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

        # Photos Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS photos (
                id TEXT PRIMARY KEY,
                path TEXT UNIQUE,
                title TEXT,
                album TEXT,
                date_taken TEXT,
                year INTEGER,
                month INTEGER,
                width INTEGER,
                height INTEGER,
                filesize INTEGER,
                mtime REAL,
                thumb_hash TEXT,
                camera_make TEXT,
                camera_model TEXT,
                mime_type TEXT,
                owner_id TEXT DEFAULT 'host',
                owner_name TEXT DEFAULT 'Host'
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_photos_date ON photos(date_taken)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_photos_year_month ON photos(year, month)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_photos_owner ON photos(owner_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_photos_album ON photos(album)")

        # Pending Uploads (Approval Queue) Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pending_uploads (
                id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                staging_path TEXT NOT NULL,
                filesize INTEGER,
                media_type TEXT DEFAULT 'audio',
                owner_id TEXT DEFAULT 'host',
                owner_name TEXT DEFAULT 'Host',
                target_folder TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pending_status ON pending_uploads(status)")

        # 24-Hour Ephemeral Statuses (Stories / Worker Updates)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS statuses (
                id TEXT PRIMARY KEY,
                owner_id TEXT NOT NULL,
                owner_name TEXT NOT NULL,
                caption TEXT DEFAULT '',
                file_path TEXT NOT NULL,
                filename TEXT NOT NULL,
                filesize INTEGER DEFAULT 0,
                mime_type TEXT DEFAULT 'image/jpeg',
                created_at REAL NOT NULL,
                expires_at REAL NOT NULL,
                is_saved INTEGER DEFAULT 0,
                saved_photo_id TEXT
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_statuses_expires ON statuses(expires_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_statuses_owner ON statuses(owner_id)")
        conn.commit()

def upsert_song(song_data: Dict[str, Any]):
    defaults = {
        "title": "Unknown Title",
        "artist": "Unknown Artist",
        "album": "Unknown Album",
        "album_artist": song_data.get("artist") or "Unknown Artist",
        "year": None,
        "genre": "Unknown",
        "language": "Unknown",
        "track_number": 1,
        "disc_number": 1,
        "duration": 0.0,
        "bitrate": 128,
        "filesize": 0,
        "mtime": 0.0,
        "cover_hash": None,
        "mime_type": "audio/mpeg",
        "media_type": "audio",
        "resolution": None,
        "season": None,
        "episode": None,
        "owner_id": "host",
        "owner_name": "Host"
    }
    for k, v in defaults.items():
        if k not in song_data:
            song_data[k] = v

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO songs (
                id, path, title, artist, album, album_artist, year, genre, language,
                track_number, disc_number, duration, bitrate, filesize, mtime, cover_hash, mime_type,
                media_type, resolution, season, episode, owner_id, owner_name
            ) VALUES (
                :id, :path, :title, :artist, :album, :album_artist, :year, :genre, :language,
                :track_number, :disc_number, :duration, :bitrate, :filesize, :mtime, :cover_hash, :mime_type,
                :media_type, :resolution, :season, :episode, :owner_id, :owner_name
            )
            ON CONFLICT(path) DO UPDATE SET
                title = excluded.title,
                artist = excluded.artist,
                album = excluded.album,
                album_artist = excluded.album_artist,
                year = excluded.year,
                genre = excluded.genre,
                language = excluded.language,
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
                season = excluded.season,
                episode = excluded.episode,
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
        cursor.execute("DELETE FROM photos")
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

def delete_photos_not_in_paths(valid_paths: List[str]):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT path FROM photos")
        all_db_paths = [row["path"] for row in cursor.fetchall()]
        valid_set = set(valid_paths)
        to_delete = [p for p in all_db_paths if p not in valid_set]

        if to_delete:
            cursor.executemany("DELETE FROM photos WHERE path = ?", [(p,) for p in to_delete])
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
    language: Optional[str] = None,
    media_type: str = "audio",  # 'audio', 'video', or 'all'
    sort_by: str = "title",
    ascending: bool = True,
    client_id: Optional[str] = None,
    favorites_only: bool = False,
    scope: str = "all",  # 'all', 'mine', 'shared'
    year: Optional[int] = None,
    decade: Optional[str] = None,
    resolution: Optional[str] = None,
    video_category: Optional[str] = None,
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
                sql += " AND (songs.owner_id = 'host' OR songs.owner_id IS NULL)"
            else:
                sql += " AND songs.owner_id = ?"
                params.append(client_id)
        elif scope == "server":
            sql += " AND (songs.owner_id = 'host' OR songs.owner_id IS NULL)"
        elif scope == "peers":
            sql += " AND songs.owner_id != 'host' AND songs.owner_id IS NOT NULL"
        elif scope.startswith("peer:"):
            target_peer = scope.split(":", 1)[1]
            sql += " AND songs.owner_id = ?"
            params.append(target_peer)
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

        if genre and genre != "all":
            sql += " AND songs.genre = ?"
            params.append(genre)

        if language and language != "all":
            if language == "Unknown":
                sql += " AND (songs.language = 'Unknown' OR songs.language IS NULL OR songs.language = '')"
            else:
                sql += " AND songs.language = ?"
                params.append(language)

        if year is not None:
            sql += " AND songs.year = ?"
            params.append(year)

        if decade:
            if decade == "2020s":
                sql += " AND songs.year >= 2020"
            elif decade == "2010s":
                sql += " AND songs.year >= 2010 AND songs.year < 2020"
            elif decade == "2000s":
                sql += " AND songs.year >= 2000 AND songs.year < 2010"
            elif decade == "1990s":
                sql += " AND songs.year >= 1990 AND songs.year < 2000"
            elif decade == "classic":
                sql += " AND songs.year < 1990 AND songs.year IS NOT NULL"

        if resolution:
            sql += " AND songs.resolution LIKE ?"
            params.append(f"%{resolution}%")

        if video_category:
            if video_category == "movies":
                sql += " AND (songs.genre = 'Movie' OR (songs.season IS NULL AND songs.genre != 'TV Show'))"
            elif video_category == "tv":
                sql += " AND (songs.genre = 'TV Show' OR songs.season IS NOT NULL)"

        allowed_sorts = {"title", "artist", "album", "year", "duration", "track_number", "filesize", "mtime", "genre", "language"}
        if sort_by not in allowed_sorts:
            sort_by = "title"

        order = "ASC" if ascending else "DESC"
        if sort_by == "track_number":
            sql += f" ORDER BY disc_number {order}, track_number {order}, title {order}"
        elif sort_by == "year":
            sql += f" ORDER BY (songs.year IS NULL), songs.year {order}, title ASC"
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

def get_videos(
    query: Optional[str] = None,
    sort_by: str = "title",
    ascending: bool = True,
    client_id: Optional[str] = None,
    favorites_only: bool = False,
    scope: str = "all",
    year: Optional[int] = None,
    decade: Optional[str] = None,
    resolution: Optional[str] = None,
    video_category: Optional[str] = None,
    limit: int = 500,
    offset: int = 0
) -> List[Dict[str, Any]]:
    return get_songs(
        query=query,
        media_type="video",
        sort_by=sort_by,
        ascending=ascending,
        client_id=client_id,
        favorites_only=favorites_only,
        scope=scope,
        year=year,
        decade=decade,
        resolution=resolution,
        video_category=video_category,
        limit=limit,
        offset=offset
    )

def update_media(media_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    allowed_fields = {
        "title", "artist", "album", "album_artist", "year", "genre", "language",
        "track_number", "disc_number", "resolution", "season", "episode"
    }
    set_clauses = []
    params = []
    for k, v in updates.items():
        if k in allowed_fields:
            set_clauses.append(f"{k} = ?")
            params.append(v)
    if not set_clauses:
        return get_song(media_id)

    params.append(media_id)
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f"UPDATE songs SET {', '.join(set_clauses)} WHERE id = ?", params)
        conn.commit()
    return get_song(media_id)

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
        stats = dict(row) if row else {
            "total_songs": 0, "total_videos": 0, "total_artists": 0, "total_albums": 0, "total_duration": 0, "total_size": 0
        }

        # Photos Stats
        cursor.execute("SELECT COUNT(*), COALESCE(SUM(filesize), 0) FROM photos")
        p_row = cursor.fetchone()
        stats["total_photos"] = p_row[0] if p_row else 0
        stats["total_photo_size"] = p_row[1] if p_row else 0

        # Pending Uploads Count
        cursor.execute("SELECT COUNT(*) FROM pending_uploads WHERE status = 'pending'")
        stats["pending_uploads"] = cursor.fetchone()[0]

        return stats

# --- Genres, Languages & Years Browsing ---
def get_genres(media_type: str = "audio") -> List[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                genre,
                COUNT(id) AS song_count,
                MAX(cover_hash) AS cover_hash
            FROM songs
            WHERE (? = 'all' OR media_type = ?) AND genre IS NOT NULL AND genre != ''
            GROUP BY genre
            ORDER BY song_count DESC, genre ASC
        """, (media_type, media_type))
        return [dict(row) for row in cursor.fetchall()]

def get_languages(media_type: str = "audio") -> List[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                COALESCE(NULLIF(language, ''), 'Unknown') AS language,
                COUNT(id) AS song_count,
                MAX(cover_hash) AS cover_hash
            FROM songs
            WHERE (? = 'all' OR media_type = ?)
            GROUP BY COALESCE(NULLIF(language, ''), 'Unknown')
            ORDER BY song_count DESC, language ASC
        """, (media_type, media_type))
        return [dict(row) for row in cursor.fetchall()]

def get_years(media_type: str = "audio") -> Dict[str, Any]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                year,
                COUNT(id) AS song_count,
                MAX(cover_hash) AS cover_hash
            FROM songs
            WHERE (? = 'all' OR media_type = ?) AND year IS NOT NULL AND year > 0
            GROUP BY year
            ORDER BY year DESC
        """, (media_type, media_type))
        years_list = [dict(row) for row in cursor.fetchall()]

        cursor.execute("""
            SELECT
                SUM(CASE WHEN year >= 2020 THEN 1 ELSE 0 END) AS d2020s,
                SUM(CASE WHEN year >= 2010 AND year < 2020 THEN 1 ELSE 0 END) AS d2010s,
                SUM(CASE WHEN year >= 2000 AND year < 2010 THEN 1 ELSE 0 END) AS d2000s,
                SUM(CASE WHEN year >= 1990 AND year < 2000 THEN 1 ELSE 0 END) AS d1990s,
                SUM(CASE WHEN year >= 1980 AND year < 1990 THEN 1 ELSE 0 END) AS d1980s,
                SUM(CASE WHEN year < 1980 AND year IS NOT NULL THEN 1 ELSE 0 END) AS classic
            FROM songs
            WHERE (? = 'all' OR media_type = ?)
        """, (media_type, media_type))
        decades_row = cursor.fetchone()
        decades = {
            "2020s": decades_row["d2020s"] or 0,
            "2010s": decades_row["d2010s"] or 0,
            "2000s": decades_row["d2000s"] or 0,
            "1990s": decades_row["d1990s"] or 0,
            "1980s": decades_row["d1980s"] or 0,
            "classic": decades_row["classic"] or 0
        } if decades_row else {}
        return {"years": years_list, "decades": decades}

# --- Playlists ---
def create_playlist(name: str, description: str = "") -> str:
    pid = str(uuid.uuid4())
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO playlists (id, name, description) VALUES (?, ?, ?)", (pid, name.strip(), description.strip()))
        conn.commit()
    return pid

def get_playlists() -> List[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.id, p.name, COALESCE(p.description, '') AS description, p.created_at, 
                   COUNT(ps.song_id) as song_count,
                   COALESCE(SUM(s.duration), 0) as total_duration
            FROM playlists p
            LEFT JOIN playlist_songs ps ON p.id = ps.playlist_id
            LEFT JOIN songs s ON ps.song_id = s.id
            GROUP BY p.id
            ORDER BY p.name ASC
        """)
        playlists = [dict(row) for row in cursor.fetchall()]
        
        for pl in playlists:
            cursor.execute("""
                SELECT s.cover_hash 
                FROM playlist_songs ps
                JOIN songs s ON ps.song_id = s.id
                WHERE ps.playlist_id = ? AND s.cover_hash IS NOT NULL AND s.cover_hash != ''
                ORDER BY ps.position ASC
                LIMIT 4
            """, (pl["id"],))
            pl["sample_covers"] = [row["cover_hash"] for row in cursor.fetchall() if row["cover_hash"]]
        return playlists

def get_playlist(playlist_id: str) -> Optional[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.id, p.name, COALESCE(p.description, '') AS description, p.created_at,
                   COUNT(ps.song_id) as song_count,
                   COALESCE(SUM(s.duration), 0) as total_duration
            FROM playlists p
            LEFT JOIN playlist_songs ps ON p.id = ps.playlist_id
            LEFT JOIN songs s ON ps.song_id = s.id
            WHERE p.id = ?
            GROUP BY p.id
        """, (playlist_id,))
        row = cursor.fetchone()
        if not row:
            return None
        pl = dict(row)
        cursor.execute("""
            SELECT s.cover_hash 
            FROM playlist_songs ps
            JOIN songs s ON ps.song_id = s.id
            WHERE ps.playlist_id = ? AND s.cover_hash IS NOT NULL AND s.cover_hash != ''
            ORDER BY ps.position ASC
            LIMIT 4
        """, (playlist_id,))
        pl["sample_covers"] = [r["cover_hash"] for r in cursor.fetchall() if r["cover_hash"]]
        return pl

def update_playlist(playlist_id: str, name: Optional[str] = None, description: Optional[str] = None) -> bool:
    updates = []
    params = []
    if name is not None and name.strip():
        updates.append("name = ?")
        params.append(name.strip())
    if description is not None:
        updates.append("description = ?")
        params.append(description.strip())
    if not updates:
        return False
    params.append(playlist_id)
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f"UPDATE playlists SET {', '.join(updates)} WHERE id = ?", params)
        conn.commit()
        return cursor.rowcount > 0

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

def add_songs_to_playlist(playlist_id: str, song_ids: List[str]):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COALESCE(MAX(position), -1) + 1 FROM playlist_songs WHERE playlist_id = ?", (playlist_id,))
        next_pos = cursor.fetchone()[0]
        for sid in song_ids:
            cursor.execute("""
                INSERT OR IGNORE INTO playlist_songs (playlist_id, song_id, position)
                VALUES (?, ?, ?)
            """, (playlist_id, sid, next_pos))
            next_pos += 1
        conn.commit()

def remove_song_from_playlist(playlist_id: str, song_id: str):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM playlist_songs WHERE playlist_id = ? AND song_id = ?", (playlist_id, song_id))
        conn.commit()

def reorder_playlist_songs(playlist_id: str, song_ids: List[str]):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        for idx, sid in enumerate(song_ids):
            cursor.execute("UPDATE playlist_songs SET position = ? WHERE playlist_id = ? AND song_id = ?", (idx, playlist_id, sid))
        conn.commit()

def delete_playlist(playlist_id: str):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM playlist_songs WHERE playlist_id = ?", (playlist_id,))
        cursor.execute("DELETE FROM playlists WHERE id = ?", (playlist_id,))
        conn.commit()

# --- Photos Management ---
def upsert_photo(photo_data: Dict[str, Any]):
    if "owner_id" not in photo_data or not photo_data["owner_id"]:
        photo_data["owner_id"] = "host"
    if "owner_name" not in photo_data or not photo_data["owner_name"]:
        photo_data["owner_name"] = "Host"
    if "album" not in photo_data or not photo_data["album"]:
        photo_data["album"] = "Camera / Uploads"

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO photos (
                id, path, title, album, date_taken, year, month,
                width, height, filesize, mtime, thumb_hash,
                camera_make, camera_model, mime_type, owner_id, owner_name
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(path) DO UPDATE SET
                title=excluded.title,
                album=excluded.album,
                date_taken=excluded.date_taken,
                year=excluded.year,
                month=excluded.month,
                width=excluded.width,
                height=excluded.height,
                filesize=excluded.filesize,
                mtime=excluded.mtime,
                thumb_hash=excluded.thumb_hash,
                camera_make=excluded.camera_make,
                camera_model=excluded.camera_model,
                mime_type=excluded.mime_type,
                owner_id=excluded.owner_id,
                owner_name=excluded.owner_name
        """, (
            photo_data["id"],
            photo_data["path"],
            photo_data.get("title", ""),
            photo_data.get("album", "Camera / Uploads"),
            photo_data.get("date_taken"),
            photo_data.get("year"),
            photo_data.get("month"),
            photo_data.get("width"),
            photo_data.get("height"),
            photo_data.get("filesize", 0),
            photo_data.get("mtime", 0.0),
            photo_data.get("thumb_hash"),
            photo_data.get("camera_make"),
            photo_data.get("camera_model"),
            photo_data.get("mime_type", "image/jpeg"),
            photo_data.get("owner_id", "host"),
            photo_data.get("owner_name", "Host")
        ))
        conn.commit()

def get_photos(
    query: Optional[str] = None,
    album: Optional[str] = None,
    year: Optional[int] = None,
    month: Optional[int] = None,
    client_id: Optional[str] = None,
    favorites_only: bool = False,
    scope: str = "all",
    limit: int = 500,
    offset: int = 0
) -> List[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        sql = """
            SELECT p.*,
                   CASE WHEN f.media_id IS NOT NULL THEN 1 ELSE 0 END AS is_favorite
            FROM photos p
            LEFT JOIN favorites f ON p.id = f.media_id AND f.client_id = ?
            WHERE 1=1
        """
        params: List[Any] = [client_id or ""]

        if query:
            sql += " AND (p.title LIKE ? OR p.album LIKE ? OR p.camera_model LIKE ?)"
            term = f"%{query}%"
            params.extend([term, term, term])

        if album:
            sql += " AND p.album = ?"
            params.append(album)

        if year:
            sql += " AND p.year = ?"
            params.append(year)

        if month:
            sql += " AND p.month = ?"
            params.append(month)

        if favorites_only:
            sql += " AND f.media_id IS NOT NULL"

        if scope == "mine" and client_id:
            if client_id == "host":
                sql += " AND (p.owner_id = 'host' OR p.owner_id IS NULL)"
            else:
                sql += " AND p.owner_id = ?"
                params.append(client_id)
        elif scope == "server":
            sql += " AND (p.owner_id = 'host' OR p.owner_id IS NULL)"
        elif scope == "peers":
            sql += " AND p.owner_id != 'host' AND p.owner_id IS NOT NULL"
        elif scope.startswith("peer:"):
            target_peer = scope.split(":", 1)[1]
            sql += " AND p.owner_id = ?"
            params.append(target_peer)
        elif scope == "shared" and client_id:
            if client_id == "host":
                sql += " AND p.owner_id != 'host'"
            else:
                sql += " AND (p.owner_id != ? OR p.owner_id IS NULL)"
                params.append(client_id)

        sql += " ORDER BY p.date_taken DESC, p.mtime DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]

def get_photo(photo_id: str, client_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        sql = """
            SELECT p.*,
                   CASE WHEN f.media_id IS NOT NULL THEN 1 ELSE 0 END AS is_favorite
            FROM photos p
            LEFT JOIN favorites f ON p.id = f.media_id AND f.client_id = ?
            WHERE p.id = ?
        """
        cursor.execute(sql, (client_id or "", photo_id))
        row = cursor.fetchone()
        return dict(row) if row else None

def delete_photo(photo_id: str) -> bool:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM favorites WHERE media_id = ?", (photo_id,))
        cursor.execute("DELETE FROM photos WHERE id = ?", (photo_id,))
        conn.commit()
        return cursor.rowcount > 0

def get_photo_timeline() -> List[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT year, month, COUNT(*) as count
            FROM photos
            WHERE year IS NOT NULL AND month IS NOT NULL
            GROUP BY year, month
            ORDER BY year DESC, month DESC
        """)
        return [dict(row) for row in cursor.fetchall()]

def get_photo_albums() -> List[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT album, COUNT(*) as count, MAX(date_taken) as latest_date, MIN(thumb_hash) as cover_thumb
            FROM photos
            GROUP BY album
            ORDER BY count DESC
        """)
        return [dict(row) for row in cursor.fetchall()]

# --- Pending Uploads (Approval Queue) ---
def add_pending_upload(
    upload_id: str,
    filename: str,
    staging_path: str,
    filesize: int,
    media_type: str = "audio",
    owner_id: str = "host",
    owner_name: str = "Host",
    target_folder: Optional[str] = None
) -> str:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO pending_uploads (
                id, filename, staging_path, filesize, media_type,
                owner_id, owner_name, target_folder, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending')
        """, (
            upload_id, filename, staging_path, filesize, media_type,
            owner_id, owner_name, target_folder
        ))
        conn.commit()
    return upload_id

def get_pending_uploads(status: str = "pending") -> List[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM pending_uploads
            WHERE status = ?
            ORDER BY created_at DESC
        """, (status,))
        return [dict(row) for row in cursor.fetchall()]

def get_pending_upload(upload_id: str) -> Optional[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM pending_uploads WHERE id = ?", (upload_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def update_pending_upload_status(upload_id: str, status: str):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE pending_uploads SET status = ? WHERE id = ?", (status, upload_id))
        conn.commit()

def delete_pending_upload(upload_id: str):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM pending_uploads WHERE id = ?", (upload_id,))
        conn.commit()

def get_peers_with_media() -> List[Dict[str, str]]:
    """Returns distinct peers who have uploaded media (excluding the main host server)."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT owner_id, COALESCE(owner_name, 'Unknown Peer')
            FROM songs
            WHERE owner_id != 'host' AND owner_id IS NOT NULL
            UNION
            SELECT DISTINCT owner_id, COALESCE(owner_name, 'Unknown Peer')
            FROM photos
            WHERE owner_id != 'host' AND owner_id IS NOT NULL
        """)
        return [{"id": r[0], "name": r[1]} for r in cursor.fetchall()]

# --- 24-Hour Ephemeral Statuses (Stories / Field Updates) ---
def add_status(
    status_id: str,
    owner_id: str,
    owner_name: str,
    caption: str,
    file_path: str,
    filename: str,
    filesize: int,
    mime_type: str,
    created_at: float,
    expires_at: float
) -> str:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO statuses (
                id, owner_id, owner_name, caption, file_path, filename,
                filesize, mime_type, created_at, expires_at, is_saved
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
        """, (
            status_id, owner_id, owner_name, caption, file_path, filename,
            filesize, mime_type, created_at, expires_at
        ))
        conn.commit()
    return status_id

def get_active_statuses(now: float) -> List[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM statuses
            WHERE expires_at > ?
            ORDER BY created_at ASC
        """, (now,))
        return [dict(row) for row in cursor.fetchall()]

def get_status(status_id: str) -> Optional[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM statuses WHERE id = ?", (status_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def mark_status_saved(status_id: str, saved_photo_id: Optional[str] = None):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE statuses
            SET is_saved = 1, saved_photo_id = ?
            WHERE id = ?
        """, (saved_photo_id, status_id))
        conn.commit()

def delete_status(status_id: str):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM statuses WHERE id = ?", (status_id,))
        conn.commit()

def cleanup_expired_statuses(now: float) -> List[str]:
    """
    Deletes expired status records from DB and returns a list of file paths to remove from disk.
    If a status was marked is_saved == 1, its permanent copy already lives in the photos directory,
    so the temporary status staging file can also be safely pruned.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT file_path FROM statuses WHERE expires_at <= ?", (now,))
        paths = [r[0] for r in cursor.fetchall() if r[0]]
        cursor.execute("DELETE FROM statuses WHERE expires_at <= ?", (now,))
        conn.commit()
        return paths


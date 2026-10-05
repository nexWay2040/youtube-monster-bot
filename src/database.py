"""SQLite3 database management for bot statistics, users, and caching."""

import sqlite3
from typing import Optional, Tuple, List, Dict
from contextlib import contextmanager


class Database:
    """SQLite3 database handler for bot operations."""
    
    def __init__(self, path: str = "bot.db") -> None:
        """Initialize database connection and create tables if needed."""
        self.path = path
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.c = self.conn.cursor()
        self._create_tables()
        self._migrate()
    
    def _create_tables(self) -> None:
        """Create all required tables."""
        self.c.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_banned INTEGER DEFAULT 0,
                total_videos INTEGER DEFAULT 0,
                total_mb REAL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS cache (
                video_id TEXT,
                quality TEXT,
                file_id TEXT,
                title TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (video_id, quality)
            );
            CREATE TABLE IF NOT EXISTS admins (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS monitor_videos (
                video_id TEXT PRIMARY KEY,
                channel_name TEXT,
                title TEXT,
                posted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS monitor_channels (
                channel_key TEXT PRIMARY KEY,
                bootstrapped INTEGER DEFAULT 0
            );
        """)
        self.conn.commit()
    
    def _migrate(self) -> None:
        """Apply migrations for new schema columns."""
        migrations = [
            ("name", "TEXT"),
            ("url", "TEXT"),
            ("hashtag", "TEXT"),
            ("active", "INTEGER DEFAULT 1"),
            ("added_at", "TIMESTAMP"),
            ("target_channel", "TEXT"),
        ]
        
        for col, decl in migrations:
            try:
                self.c.execute(f"ALTER TABLE monitor_channels ADD COLUMN {col} {decl}")
                self.conn.commit()
            except sqlite3.OperationalError as e:
                if "duplicate column" not in str(e).lower():
                    print(f"[DB MIGRATE WARNING] monitor_channels.{col}: {e}")
    
    # User methods
    
    def register_user(self, uid: int, uname: str = "") -> None:
        """Register or update user in database."""
        self.c.execute(
            "INSERT INTO users (user_id, username) VALUES (?,?) "
            "ON CONFLICT(user_id) DO UPDATE SET username=excluded.username "
            "WHERE excluded.username != ''",
            (uid, uname or "")
        )
        self.conn.commit()
    
    def is_banned(self, uid: int) -> bool:
        """Check if user is banned."""
        self.c.execute("SELECT is_banned FROM users WHERE user_id=?", (uid,))
        row = self.c.fetchone()
        return bool(row[0]) if row else False
    
    def set_ban(self, uid: int, banned: bool) -> bool:
        """Ban or unban user."""
        self.c.execute(
            "INSERT INTO users (user_id, is_banned) VALUES (?,?) "
            "ON CONFLICT(user_id) DO UPDATE SET is_banned=excluded.is_banned",
            (uid, int(banned))
        )
        self.conn.commit()
        return True
    
    def add_stats(self, uid: int, mb: float) -> None:
        """Update user statistics."""
        self.c.execute(
            "UPDATE users SET total_videos=total_videos+1, total_mb=total_mb+? WHERE user_id=?",
            (mb, uid)
        )
        self.conn.commit()
    
    def get_user_stats(self, uid: int) -> Tuple[int, float]:
        """Get user statistics."""
        self.c.execute("SELECT total_videos, total_mb FROM users WHERE user_id=?", (uid,))
        row = self.c.fetchone()
        return (row[0] or 0, row[1] or 0.0) if row else (0, 0.0)
    
    def find_user_by_name(self, uname: str) -> Optional[int]:
        """Find user ID by username."""
        clean = uname.strip().lower().lstrip("@")
        self.c.execute("SELECT user_id FROM users WHERE LOWER(username)=?", (clean,))
        row = self.c.fetchone()
        return row[0] if row else None
    
    def get_users_list(self, limit: int = 50) -> list:
        """Get list of recent users."""
        self.c.execute(
            "SELECT user_id, username, is_banned, total_videos FROM users "
            "ORDER BY joined_at DESC LIMIT ?",
            (limit,)
        )
        return self.c.fetchall()
    
    def all_users(self) -> List[int]:
        """Get all non-banned user IDs."""
        self.c.execute("SELECT user_id FROM users WHERE is_banned=0")
        return [r[0] for r in self.c.fetchall()]
    
    # Cache methods
    
    def get_cache(self, vid: str, quality: str, lang: str = "orig") -> Optional[Tuple[str, str]]:
        """Get cached file from database."""
        q_key = f"{quality}_{lang}"
        self.c.execute("SELECT file_id, title FROM cache WHERE video_id=? AND quality=?", (vid, q_key))
        row = self.c.fetchone()
        if row and row[0]:
            return row[0], row[1] or ""
        return None
    
    def set_cache(self, vid: str, quality: str, lang: str, file_id: str, title: str = "") -> None:
        """Save file to cache database."""
        q_key = f"{quality}_{lang}"
        clean_title = (title or "").strip()
        if not clean_title or clean_title.lower() in ("none", "без названия", "unknown"):
            clean_title = f"YouTube {vid}"
        self.c.execute(
            "INSERT OR REPLACE INTO cache (video_id, quality, file_id, title) VALUES (?,?,?,?)",
            (vid, q_key, file_id, clean_title)
        )
        self.conn.commit()
    
    def del_cache(self, vid: str, quality_key: str = "") -> int:
        """Delete cache entry."""
        deleted_rows = 0
        if quality_key:
            self.c.execute("DELETE FROM cache WHERE video_id=? AND quality=?", (vid, str(quality_key)))
            deleted_rows += self.c.rowcount
        else:
            self.c.execute("DELETE FROM cache WHERE video_id=?", (vid,))
            deleted_rows += self.c.rowcount
        self.conn.commit()
        return deleted_rows
    
    def clear_all_cache(self) -> int:
        """Clear entire cache."""
        self.c.execute("DELETE FROM cache")
        count = self.c.rowcount
        self.conn.commit()
        return count
    
    def search_cache(self, query: str, limit: int = 15) -> list:
        """Search cache by title or video ID."""
        self.c.execute(
            "SELECT video_id, quality, title, created_at, file_id FROM cache "
            "WHERE title LIKE ? OR video_id LIKE ? ORDER BY rowid DESC LIMIT ?",
            (f"%{query}%", f"%{query}%", limit)
        )
        return self.c.fetchall()
    
    def get_cache_page(self, page: int = 1, page_size: int = 5) -> Tuple[list, int]:
        """Get paginated cache results."""
        self.c.execute("SELECT COUNT(*) FROM cache")
        total = self.c.fetchone()[0]
        offset = (page - 1) * page_size
        self.c.execute(
            "SELECT video_id, quality, title, created_at, file_id FROM cache "
            "ORDER BY rowid DESC LIMIT ? OFFSET ?",
            (page_size, offset)
        )
        items = self.c.fetchall()
        return items, total
    
    def update_title_if_needed(self, vid: str, title: str) -> None:
        """Update video title in cache if needed."""
        if not title or title.lower() in ("none", "без названия", "unknown"):
            return
        self.c.execute(
            "UPDATE cache SET title=? WHERE video_id=? AND (title IS NULL OR title='' OR title='Без названия')",
            (title, vid)
        )
        self.conn.commit()
    
    # Admin methods
    
    def add_admin(self, uid: int, uname: str = "") -> None:
        """Add administrator."""
        self.c.execute("INSERT OR REPLACE INTO admins (user_id, username) VALUES (?,?)", (uid, uname or ""))
        self.conn.commit()
    
    def del_admin(self, uid: int) -> None:
        """Remove administrator."""
        self.c.execute("DELETE FROM admins WHERE user_id=?", (uid,))
        self.conn.commit()
    
    def is_admin_in_db(self, uid: int) -> bool:
        """Check if user is admin in database."""
        self.c.execute("SELECT user_id FROM admins WHERE user_id=?", (uid,))
        return bool(self.c.fetchone())
    
    # Statistics
    
    def stats(self) -> dict:
        """Get bot statistics."""
        self.c.execute("SELECT COUNT(*), SUM(total_videos), SUM(total_mb) FROM users")
        u, v, mb = self.c.fetchone()
        self.c.execute("SELECT COUNT(*) FROM cache")
        c = self.c.fetchone()[0]
        return {"users": u or 0, "videos": v or 0, "gb": (mb or 0) / 1024, "cache": c or 0}
    
    def close(self) -> None:
        """Close database connection."""
        self.conn.close()

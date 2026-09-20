# -*- coding: utf-8 -*-
"""
YouTube Monster Bot — Ultimate Edition (Direct Copy + Smart Cache + Yandex AI)
All Bugs Fixed: Cache Reply Button, Real Dubbing Engine & Title Translation
"""

import os
import re
import sys
import json
import html
import math
import hmac
import struct
import hashlib
import random
import asyncio
import logging
import time
import subprocess
import shutil
import threading
import sqlite3
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from typing import Optional, Tuple, List, Dict, Set

import yt_dlp

try:
    import socks
except ImportError:
    socks = None

from telethon import TelegramClient, events, functions, types, utils
from telethon.tl.custom import Button
from telethon.tl.types import DocumentAttributeVideo, DocumentAttributeAudio
from dotenv import load_dotenv, set_key

if os.name == 'nt':
    os.system('')
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"

def cprint(text: str, color: str = Colors.RESET, bold: bool = False):
    prefix = Colors.BOLD if bold else ""
    print(f"{prefix}{color}{text}{Colors.RESET}")

def log_banner():
    banner = f"""{Colors.CYAN}{Colors.BOLD}
███╗   ███╗ ██████╗ ███╗   ██╗███████╗████████╗███████╗██████╗ 
████╗ ████║██╔═══██╗████╗  ██║██╔════╝╚══██╔══╝██╔════╝██╔══██╗
██╔████╔██║██║   ██║██╔██╗ ██║███████╗   ██║   █████╗  ██████╔╝
██║╚██╔╝██║██║   ██║██║╚██╗██║╚════██║   ██║   ██╔══╝  ██╔══██╗
██║ ╚═╝ ██║╚██████╔╝██║ ╚████║███████║   ██║   ███████╗██║  ██║
╚═╝     ╚═╝ ╚═════╝ ╚═╝  ╚═══╝╚══════╝   ╚═╝   ╚══════╝╚═╝  ╚═╝{Colors.MAGENTA}
       ██████╗  ██████╗ ████████╗
       ██╔══██╗██╔═══██╗╚══██╔══╝
       ██████╔╝██║   ██║   ██║   
       ██╔══██╗██║   ██║   ██║   
       ██████╔╝╚██████╔╝   ██║   
       ╚═════╝  ╚═════╝    ╚═╝   {Colors.YELLOW}
  ⚡ Telethon + yt-dlp + FFmpeg (Direct Copy) | Pure Speed Engine
  🛡️ Local Cache V2 (Newest First) | Yandex Neural Dubbing | 4GB Flow{Colors.RESET}
"""
    print(banner)

def get_now() -> str:
    return datetime.now().strftime("%H:%M:%S")

def term_log(tag: str, msg: str, color: str = Colors.WHITE):
    print(f"{Colors.DIM}[{get_now()}]{Colors.RESET} {color}{Colors.BOLD}{tag:<16}{Colors.RESET} {msg}")

ENV_FILE = ".env"
for _f in (".env", ".evn", ".env.txt"):
    if os.path.exists(_f):
        ENV_FILE = _f
        break

load_dotenv(ENV_FILE)

def _env(key: str, default: str = "") -> str:
    return os.getenv(key, default)

API_ID = int(_env("API_ID", "0"))
API_HASH = _env("API_HASH", "")
BOT_TOKEN = _env("BOT_TOKEN", "")
DOWNLOAD_DIR = _env("DOWNLOAD_DIR", "./downloads")
BROWSER_COOKIES = _env("BROWSER_COOKIES", "")
USE_PROXY = _env("USE_PROXY", "false").lower() == "true"
PROXY_HOST = _env("PROXY_HOST", "127.0.0.1")
PROXY_PORT = int(_env("PROXY_PORT", "10808"))

# Отдельный прокси для yt-dlp (YouTube), независимый от прокси Telegram.
# Нужен потому, что YouTube привязывает cookies к IP/фингерпринту запроса:
# если прокси Telegram часто меняет выходной сервер (VPN-клиенты вроде Happ
# так и делают), куки постоянно "слетают". Держи для YouTube отдельный,
# стабильный/статичный адрес.
# YTDLP_USE_PROXY не задан → берёт то же самое, что USE_PROXY (старое поведение).
# YTDLP_USE_PROXY=false → yt-dlp всегда идёт напрямую, без прокси.
# YTDLP_USE_PROXY=true → использует YTDLP_PROXY_HOST/PORT (или PROXY_HOST/PORT, если не заданы отдельно).
_ytdlp_proxy_env = _env("YTDLP_USE_PROXY", "")
YTDLP_USE_PROXY = (_ytdlp_proxy_env.lower() == "true") if _ytdlp_proxy_env else USE_PROXY
YTDLP_PROXY_HOST = _env("YTDLP_PROXY_HOST", PROXY_HOST)
YTDLP_PROXY_PORT = int(_env("YTDLP_PROXY_PORT", str(PROXY_PORT)))

OWNER_ID = int(_env("OWNER_ID", "0"))

ADMIN_IDS: Set[int] = {
    int(x.strip()) for x in _env("ADMIN_IDS", "").split(",") if x.strip().isdigit()
}

_RAW_PREMIUM = _env("PREMIUM_USERS", "")
PREMIUM_USERS: Set[int] = {
    int(x.strip()) for x in _RAW_PREMIUM.split(",") if x.strip().isdigit()
}
PREMIUM_USERNAMES: Set[str] = {
    x.strip().lower().lstrip("@")
    for x in _RAW_PREMIUM.split(",")
    if x.strip() and not x.strip().isdigit()
}

DEFAULT_BATCH = int(_env("DEFAULT_BATCH_SIZE", "3"))
USE_USERBOT = _env("USE_USERBOT", "true").lower() == "true"
QUICK_START = _env("QUICK_START", "false").lower() == "true"
COOKIE_FILE = _env("COOKIE_FILE", "")
COOKIE_MAX_AGE_HOURS = float(_env("COOKIE_MAX_AGE_HOURS", "12"))

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def cleanup_download_dir_on_boot():
    """Чистим огрызки файлов, оставшиеся после падения/перезапуска бота
    (частично скачанные видео, .part файлы, забытые превью и т.д.)."""
    removed, freed_mb = 0, 0.0
    try:
        for f in os.listdir(DOWNLOAD_DIR):
            fp = os.path.join(DOWNLOAD_DIR, f)
            if not os.path.isfile(fp):
                continue
            try:
                freed_mb += os.path.getsize(fp) / (1024 * 1024)
                os.remove(fp)
                removed += 1
            except Exception:
                pass
    except Exception:
        pass
    return removed, freed_mb

from logging.handlers import RotatingFileHandler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        RotatingFileHandler("bot.log", maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"),
    ],
)
log = logging.getLogger("bot")

def update_env(key: str, value: str):
    try:
        set_key(ENV_FILE, key, str(value))
    except Exception as e:
        term_log("⚠️ ENV", f"Ошибка сохранения {key} в {ENV_FILE}: {e}", Colors.YELLOW)
    os.environ[key] = str(value)

def save_premium_list():
    all_premium = [str(uid) for uid in sorted(PREMIUM_USERS)]
    all_premium += [f"@{uname}" for uname in sorted(PREMIUM_USERNAMES)]
    update_env("PREMIUM_USERS", ",".join(all_premium))

def save_admin_list():
    update_env("ADMIN_IDS", ",".join(str(uid) for uid in sorted(ADMIN_IDS)))

def get_telethon_proxy():
    if not USE_PROXY:
        return None
    if socks is not None and hasattr(socks, "SOCKS5"):
        return (socks.SOCKS5, PROXY_HOST, PROXY_PORT)
    return {
        "proxy_type": "socks5",
        "addr": PROXY_HOST,
        "port": PROXY_PORT
    }

# ─────────────────────────────────────────────
# БАЗА ДАННЫХ (SQLite3)
# ─────────────────────────────────────────────
class DB:
    def __init__(self, path="bot.db"):
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.c = self.conn.cursor()
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
        # Миграция: добавляем колонки под полноценное управление каналами
        # прямо из Telegram (имя, URL, хештег, вкл/выкл), если их ещё нет.
        # ВАЖНО: SQLite не разрешает ALTER TABLE ADD COLUMN с не-константным
        # DEFAULT (вроде CURRENT_TIMESTAMP) — поэтому added_at без дефолта,
        # порядок вывода берём по rowid (и так соответствует порядку добавления).
        for col, decl in [
            ("name", "TEXT"),
            ("url", "TEXT"),
            ("hashtag", "TEXT"),
            ("active", "INTEGER DEFAULT 1"),
            ("added_at", "TIMESTAMP"),
            ("target_channel", "TEXT"),
        ]:
            try:
                self.c.execute(f"ALTER TABLE monitor_channels ADD COLUMN {col} {decl}")
                self.conn.commit()
            except sqlite3.OperationalError as e:
                if "duplicate column" not in str(e).lower():
                    # это НЕ "колонка уже есть" — реальная ошибка миграции, не прячем её
                    print(f"[DB MIGRATE WARNING] monitor_channels.{col}: {e}")
        self._sync_admins()

    def monitor_is_posted(self, video_id: str) -> bool:
        self.c.execute("SELECT 1 FROM monitor_videos WHERE video_id=?", (video_id,))
        return self.c.fetchone() is not None

    def monitor_mark_posted(self, video_id: str, channel_name: str, title: str):
        self.c.execute(
            "INSERT OR IGNORE INTO monitor_videos (video_id, channel_name, title) VALUES (?,?,?)",
            (video_id, channel_name, title)
        )
        self.conn.commit()

    def monitor_forget(self, video_id: str) -> bool:
        self.c.execute("DELETE FROM monitor_videos WHERE video_id=?", (video_id,))
        self.conn.commit()
        return self.c.rowcount > 0

    def monitor_is_bootstrapped(self, channel_key: str) -> bool:
        self.c.execute("SELECT bootstrapped FROM monitor_channels WHERE channel_key=?", (channel_key,))
        row = self.c.fetchone()
        return bool(row and row[0])

    def monitor_set_bootstrapped(self, channel_key: str):
        self.c.execute(
            "INSERT INTO monitor_channels (channel_key, bootstrapped) VALUES (?,1) "
            "ON CONFLICT(channel_key) DO UPDATE SET bootstrapped=1",
            (channel_key,)
        )
        self.conn.commit()

    def monitor_add_channel(self, key: str, name: str, url: str, hashtag: str, target_channel: str = None):
        self.c.execute(
            "INSERT INTO monitor_channels (channel_key, name, url, hashtag, target_channel, active, bootstrapped, added_at) "
            "VALUES (?,?,?,?,?,1,0,CURRENT_TIMESTAMP) "
            "ON CONFLICT(channel_key) DO UPDATE SET name=excluded.name, url=excluded.url, "
            "hashtag=excluded.hashtag, target_channel=excluded.target_channel, active=1",
            (key, name, url, hashtag, target_channel)
        )
        self.conn.commit()

    def monitor_remove_channel(self, key: str) -> bool:
        self.c.execute("DELETE FROM monitor_channels WHERE channel_key=?", (key,))
        self.conn.commit()
        return self.c.rowcount > 0

    def monitor_set_hashtag(self, key: str, hashtag: str) -> bool:
        self.c.execute("UPDATE monitor_channels SET hashtag=? WHERE channel_key=?", (hashtag, key))
        self.conn.commit()
        return self.c.rowcount > 0

    def monitor_set_target(self, key: str, target_channel: str) -> bool:
        self.c.execute("UPDATE monitor_channels SET target_channel=? WHERE channel_key=?", (target_channel, key))
        self.conn.commit()
        return self.c.rowcount > 0

    def monitor_list_channels(self, active_only: bool = True) -> list:
        q = "SELECT channel_key, name, url, hashtag, bootstrapped, active, target_channel FROM monitor_channels"
        if active_only:
            q += " WHERE active=1"
        q += " ORDER BY rowid"
        self.c.execute(q)
        return [
            {"key": r[0], "name": r[1], "url": r[2], "hashtag": r[3], "bootstrapped": bool(r[4]),
             "active": bool(r[5]), "target_channel": r[6]}
            for r in self.c.fetchall()
        ]

    def monitor_get_channel(self, key: str) -> Optional[dict]:
        self.c.execute(
            "SELECT channel_key, name, url, hashtag, bootstrapped, active, target_channel FROM monitor_channels WHERE channel_key=?",
            (key,)
        )
        r = self.c.fetchone()
        if not r:
            return None
        return {"key": r[0], "name": r[1], "url": r[2], "hashtag": r[3], "bootstrapped": bool(r[4]),
                "active": bool(r[5]), "target_channel": r[6]}

    def _sync_admins(self):
        try:
            self.c.execute("SELECT user_id FROM admins")
            for r in self.c.fetchall():
                ADMIN_IDS.add(r[0])
        except Exception:
            pass

    def register_user(self, uid: int, uname: str = ""):
        self.c.execute(
            "INSERT INTO users (user_id, username) VALUES (?,?) "
            "ON CONFLICT(user_id) DO UPDATE SET username=excluded.username "
            "WHERE excluded.username != ''", (uid, uname or ""))
        self.conn.commit()

    def is_banned(self, uid: int) -> bool:
        self.c.execute("SELECT is_banned FROM users WHERE user_id=?", (uid,))
        row = self.c.fetchone()
        return bool(row[0]) if row else False

    def set_ban(self, uid: int, banned: bool) -> bool:
        self.c.execute(
            "INSERT INTO users (user_id, is_banned) VALUES (?,?) "
            "ON CONFLICT(user_id) DO UPDATE SET is_banned=excluded.is_banned",
            (uid, int(banned)))
        self.conn.commit()
        return True

    def add_stats(self, uid: int, mb: float):
        self.c.execute(
            "UPDATE users SET total_videos=total_videos+1, total_mb=total_mb+? WHERE user_id=?",
            (mb, uid))
        self.conn.commit()

    def get_user_stats(self, uid: int) -> Tuple[int, float]:
        self.c.execute("SELECT total_videos, total_mb FROM users WHERE user_id=?", (uid,))
        row = self.c.fetchone()
        return (row[0] or 0, row[1] or 0.0) if row else (0, 0.0)

    def get_cache(self, vid: str, quality: str, lang: str = "orig") -> Optional[Tuple[str, str]]:
        """Строгий поиск в кэше без смешивания языков"""
        q_key = f"{quality}_{lang}"
        self.c.execute("SELECT file_id, title FROM cache WHERE video_id=? AND quality=?", (vid, q_key))
        row = self.c.fetchone()
        if row and row[0]:
            return row[0], row[1] or ""
        return None

    def set_cache(self, vid: str, quality: str, lang: str, file_id: str, title: str = ""):
        """Строгое сохранение с префиксом озвучки (orig, ya, ru, en)"""
        q_key = f"{quality}_{lang}"
        clean_title = (title or "").strip()
        if not clean_title or clean_title.lower() in ("none", "без названия", "unknown"):
            clean_title = f"YouTube {vid}"
        self.c.execute(
            "INSERT OR REPLACE INTO cache (video_id, quality, file_id, title) VALUES (?,?,?,?)",
            (vid, q_key, file_id, clean_title))
        self.conn.commit()

    def update_title_if_needed(self, vid: str, title: str):
        if not title or title.lower() in ("none", "без названия", "unknown"):
            return
        self.c.execute(
            "UPDATE cache SET title=? WHERE video_id=? AND (title IS NULL OR title='' OR title='Без названия')",
            (title, vid))
        self.conn.commit()

    def del_cache(self, vid: str, quality_key: str = "") -> int:
        deleted_rows = 0
        if quality_key:
            self.c.execute("DELETE FROM cache WHERE video_id=? AND quality=?", (vid, str(quality_key)))
            deleted_rows += self.c.rowcount
            base_q = quality_key.split("_")[0] if "_" in quality_key else quality_key
            self.c.execute("DELETE FROM cache WHERE video_id=? AND (quality=? OR quality LIKE ?)", (vid, str(base_q), f"{base_q}_%"))
            deleted_rows += self.c.rowcount
        else:
            self.c.execute("DELETE FROM cache WHERE video_id=?", (vid,))
            deleted_rows += self.c.rowcount
        self.conn.commit()
        return deleted_rows

    def clear_all_cache(self) -> int:
        self.c.execute("DELETE FROM cache")
        count = self.c.rowcount
        self.conn.commit()
        return count

    def search_cache(self, query: str, limit: int = 15) -> list:
        self.c.execute(
            "SELECT video_id, quality, title, created_at, file_id FROM cache "
            "WHERE title LIKE ? OR video_id LIKE ? ORDER BY rowid DESC LIMIT ?",
            (f"%{query}%", f"%{query}%", limit))
        return self.c.fetchall()

    def get_cache_page(self, page: int = 1, page_size: int = 5) -> Tuple[list, int]:
        self.c.execute("SELECT COUNT(*) FROM cache")
        total = self.c.fetchone()[0]
        offset = (page - 1) * page_size
        self.c.execute(
            "SELECT video_id, quality, title, created_at, file_id FROM cache "
            "ORDER BY rowid DESC LIMIT ? OFFSET ?", (page_size, offset))
        items = self.c.fetchall()
        return items, total

    def all_users(self) -> List[int]:
        self.c.execute("SELECT user_id FROM users WHERE is_banned=0")
        return [r[0] for r in self.c.fetchall()]

    def get_users_list(self, limit=50) -> list:
        self.c.execute(
            "SELECT user_id, username, is_banned, total_videos FROM users "
            "ORDER BY joined_at DESC LIMIT ?", (limit,))
        return self.c.fetchall()

    def find_user_by_name(self, uname: str) -> Optional[int]:
        clean = uname.strip().lower().lstrip("@")
        self.c.execute("SELECT user_id FROM users WHERE LOWER(username)=?", (clean,))
        row = self.c.fetchone()
        return row[0] if row else None

    def add_admin(self, uid: int, uname: str = ""):
        self.c.execute("INSERT OR REPLACE INTO admins (user_id, username) VALUES (?,?)", (uid, uname or ""))
        self.conn.commit()
        ADMIN_IDS.add(uid)

    def del_admin(self, uid: int):
        self.c.execute("DELETE FROM admins WHERE user_id=?", (uid,))
        self.conn.commit()
        ADMIN_IDS.discard(uid)

    def is_admin_in_db(self, uid: int) -> bool:
        self.c.execute("SELECT user_id FROM admins WHERE user_id=?", (uid,))
        return bool(self.c.fetchone())

    def stats(self) -> dict:
        self.c.execute("SELECT COUNT(*), SUM(total_videos), SUM(total_mb) FROM users")
        u, v, mb = self.c.fetchone()
        self.c.execute("SELECT COUNT(*) FROM cache")
        c = self.c.fetchone()[0]
        return {"users": u or 0, "videos": v or 0, "gb": (mb or 0) / 1024, "cache": c or 0}

    def close(self):
        self.conn.close()

db = DB()

# ─────────────────────────────────────────────
# УТИЛИТЫ И ПРАВА
# ─────────────────────────────────────────────
def is_premium_user(uid: int, username: str = "") -> bool:
    if uid in PREMIUM_USERS:
        return True
    uname = (username or "").strip().lower().lstrip("@")
    if uname and uname in PREMIUM_USERNAMES:
        return True
    if not uname:
        try:
            db.c.execute("SELECT username FROM users WHERE user_id=?", (uid,))
            row = db.c.fetchone()
            if row and row[0]:
                uname = row[0].strip().lower().lstrip("@")
        except Exception:
            uname = ""
    return bool(uname and uname in PREMIUM_USERNAMES)

def is_admin(uid: int) -> bool:
    return uid == OWNER_ID or uid in ADMIN_IDS or db.is_admin_in_db(uid)

def is_owner(uid: int) -> bool:
    return uid == OWNER_ID

def fmt_size(n: float) -> str:
    for unit in ("Б", "КБ", "МБ", "ГБ"):
        if abs(n) < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} ТБ"

def progress_bar(pct: float, length=12) -> str:
    pct = max(0, min(100, pct))
    filled = int(length * pct / 100)
    return f"{'█' * filled}{'░' * (length - filled)}"

def extract_url(text: str) -> Optional[str]:
    m = re.search(
        r'(https?://(?:www\.)?youtu(?:be\.com/watch\?v=|\.be/|be\.com/shorts/|be\.com/playlist\?list=)[^\s]+)',
        text)
    return m.group(1) if m else None

def hashtag(name: str) -> str:
    clean = re.sub(r'[^\w\s]', '', name or '').strip()
    return '#' + re.sub(r'\s+', '_', clean).lower() if clean else '#unknown'

def user_link(uid: int, username: str = "") -> str:
    name = html.escape(f"@{username}") if username else f"User {uid}"
    return f'<a href="tg://user?id={uid}">{name}</a>'

async def translate_title_to_ru(text: str) -> Optional[str]:
    if not text or not re.search(r'[a-zA-Z]', text):
        return None
    try:
        # Клиент Google Translate с полным контекстом фразы
        url = "https://translate.googleapis.com/translate_a/single"
        params = {
            "client": "gtx",
            "sl": "auto",
            "tl": "ru",
            "dt": "t",
            "dj": "1",
            "q": text
        }
        full_url = f"{url}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(full_url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
        })
        loop = asyncio.get_running_loop()
        def _fetch():
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                sentences = [s.get("trans", "") for s in data.get("sentences", []) if "trans" in s]
                return "".join(sentences).strip()
        trans = await loop.run_in_executor(None, _fetch)
        if trans and trans.strip().lower() != text.strip().lower():
            return trans.strip()
    except Exception:
        pass
    return None

async def resolve_user(client: TelegramClient, user_input: str) -> Tuple[Optional[int], Optional[str], Optional[str]]:
    clean = user_input.strip()
    if clean.isdigit():
        uid = int(clean)
        db.c.execute("SELECT username FROM users WHERE user_id=?", (uid,))
        row = db.c.fetchone()
        if row:
            return uid, row[0], None
        try:
            entity = await client.get_entity(uid)
            if isinstance(entity, types.User):
                uname = getattr(entity, "username", "") or ""
                db.register_user(entity.id, uname)
                return entity.id, uname, None
        except Exception:
            return uid, "", None

    uname = clean.lstrip("@")
    if not re.fullmatch(r"[A-Za-z0-9_]{3,32}", uname):
        return None, None, "❌ Неверный формат юзернейма."

    found_uid = db.find_user_by_name(uname)
    if found_uid:
        return found_uid, uname, None

    try:
        entity = await client.get_entity(uname)
        if isinstance(entity, types.User):
            real_uname = getattr(entity, "username", "") or uname
            db.register_user(entity.id, real_uname)
            return entity.id, real_uname, None
        else:
            return None, None, f"❌ `@{uname}` является каналом или группой!"
    except Exception:
        return None, None, f"❌ Пользователь `@{uname}` не найден в Telegram."

async def rm(path: Optional[str]):
    if not path or not os.path.exists(path):
        return
    for _ in range(5):
        try:
            os.remove(path)
            return
        except PermissionError:
            await asyncio.sleep(0.5)
        except Exception:
            pass

def cleanup_disk_for_video(video_id: str):
    removed_count = 0
    try:
        for f in os.listdir(DOWNLOAD_DIR):
            if video_id in f:
                p = os.path.join(DOWNLOAD_DIR, f)
                try:
                    os.remove(p)
                    removed_count += 1
                except Exception:
                    pass
    except Exception:
        pass
    return removed_count

def find_file(user_id: int, file_key: str) -> Optional[str]:
    prefix = f"{user_id}_{file_key}."
    for f in os.listdir(DOWNLOAD_DIR):
        if f.startswith(prefix) and not f.endswith(('.jpg', '.webp', '.png', '.part', '.ytdl')):
            return os.path.join(DOWNLOAD_DIR, f)
    return None

def is_shorts_url(url: str, info: Optional[dict] = None) -> bool:
    try:
        if url and "/shorts/" in url:
            return True
        if info:
            for key in ("webpage_url", "original_url", "url"):
                u = str(info.get(key) or "")
                if "/shorts/" in u:
                    return True
            dur = int(info.get("duration") or 0)
            w = int(info.get("width") or 0)
            h = int(info.get("height") or 0)
            if 0 < dur <= 60 and w and h and h > w:
                return True
    except Exception:
        pass
    return False

def get_format_tier(w: int, h: int, note: str = "") -> int:
    if note:
        m = re.search(r'(\d{3,4})p', str(note), re.IGNORECASE)
        if m:
            val = int(m.group(1))
            if val in (144, 240, 360, 480, 720, 1080, 1440, 2160):
                return val

    w = int(w or 0)
    h = int(h or 0)
    if not w and not h:
        return 0

    long_side = max(w, h)
    short_side = min(w, h)

    if long_side >= 2400 or short_side >= 1350:
        return 1440
    if long_side >= 1650 or short_side >= 850:
        return 1080
    if long_side >= 1050 or short_side >= 520:
        return 720
    if long_side >= 700 or short_side >= 380:
        return 480
    if long_side >= 450 or short_side >= 280:
        return 360
    if long_side >= 300 or short_side >= 180:
        return 240
    return 144

def get_available_tiers(info: dict) -> List[int]:
    tiers: Set[int] = set()
    for f in info.get("formats", []) or []:
        if f.get("vcodec") == "none":
            continue
        w = f.get("width") or 0
        h = f.get("height") or 0
        note = f.get("format_note") or ""
        t = get_format_tier(w, h, note)
        if t > 0:
            tiers.add(t)

    top_t = get_format_tier(info.get("width") or 0, info.get("height") or 0, "")
    if top_t > 0:
        tiers.add(top_t)

    standard_tiers = [1080, 720, 480, 360]
    result: Set[int] = set()
    max_t = max(tiers) if tiers else 720
    for st in standard_tiers:
        if st <= max_t or st in tiers:
            result.add(st)

    if not result:
        result = {720, 360}

    return sorted(result, reverse=True)

def estimate_size_mb(duration: int, tier: int) -> int:
    bitrates = {1080: 3500, 720: 1800, 480: 900, 360: 500}
    br = bitrates.get(tier, 1500)
    dur = max(duration, 1)
    mb = int((br * dur) / (8 * 1024))
    return max(mb, 1)

# ─────────────────────────────────────────────
# ОПРЕДЕЛЕНИЕ ДУБЛЯЖЕЙ (ИСПРАВЛЕНО)
# ─────────────────────────────────────────────
def detect_audio_tracks(info: dict) -> Dict[str, any]:
    formats = info.get("formats", []) or []
    
    languages_found = set()
    has_ru = False
    has_en = False
    has_ru_dub = False

    title_str = (info.get("title") or "").strip()
    cyr_count = len(re.findall(r'[а-яА-ЯёЁ]', title_str))
    lat_count = len(re.findall(r'[a-zA-Z]', title_str))
    is_russian_by_title = cyr_count > lat_count and cyr_count >= 3

    for f in formats:
        acodec = str(f.get("acodec") or "").lower()
        if acodec in ("none", "") and f.get("vcodec") != "none":
            continue

        lang = str(f.get("language") or "").lower()
        note = str(f.get("format_note") or "").lower()
        track_id = str(f.get("audio_track_id") or "").lower()
        format_str = str(f.get("format") or "").lower()

        is_r = (
            lang.startswith("ru") or 
            any(k in note for k in ("russian", "русск", "ru-")) or
            any(k in track_id for k in ("ru.", ".ru")) or
            "русск" in format_str
        )
        if is_r:
            has_ru = True
            languages_found.add("ru")
            if any(k in note for k in ("dub", "auto-dub", "дубл")):
                has_ru_dub = True

        is_e = (
            lang.startswith("en") or 
            "english" in note or 
            "en." in track_id or ".en" in track_id
        )
        if is_e:
            has_en = True
            languages_found.add("en")

    if (is_russian_by_title or (has_ru and not has_en)) and not has_ru_dub:
        return {
            "is_russian": True,
            "has_official_dub": False,
            "needs_yandex_ai": False,
            "has_ru": True,
            "has_en": False
        }

    has_official_dub = (has_en and has_ru) or has_ru_dub
    needs_yandex_ai = not has_ru and (has_en or not is_russian_by_title)

    return {
        "is_russian": is_russian_by_title and not has_official_dub,
        "has_official_dub": has_official_dub,
        "needs_yandex_ai": needs_yandex_ai,
        "has_ru": has_ru,
        "has_en": has_en
    }

# ─────────────────────────────────────────────
# КЛИЕНТ ЗАКАДРОВОГО ПЕРЕВОДА ЯНДЕКС (VOT-CLI)
# ─────────────────────────────────────────────
async def fetch_yandex_voiceover(youtube_url: str, duration: int, cancel_token=None) -> Optional[str]:
    """
    Получает русскую нейроозвучку («Живые голоса») через vot-cli-live.
    Перехватывает готовую ссылку на MP3 и скачивает файл напрямую.
    """
    m_id = re.search(r'(?:v=|\.be/|/shorts/|^)([a-zA-Z0-9_-]{11})', youtube_url)
    clean_url = f"https://www.youtube.com/watch?v={m_id.group(1)}" if m_id else youtube_url

    term_log("🤖 YANDEX AI", f"Запрос перевода через vot-cli-live: {clean_url}", Colors.CYAN)

    tmp_filename = f"ya_{random.getrandbits(32)}.mp3"
    tmp_mp3 = os.path.join(DOWNLOAD_DIR, tmp_filename)

    # Автопоиск vot-cli-live в Windows и Linux
    vot_bin = shutil.which("vot-cli-live.cmd") or shutil.which("vot-cli-live") or shutil.which("vot-cli") or "vot-cli-live"

    cmd = [
        vot_bin,
        clean_url
    ]

    loop = asyncio.get_running_loop()
    try:
        def _run():
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
                shell=(os.name == 'nt'),
                encoding="utf-8",
                errors="replace"
            )
            return (res.stdout or "") + "\n" + (res.stderr or "")

        output_text = await loop.run_in_executor(None, _run)

        # Извлекаем ссылку на сгенерированный MP3 из вывода утилиты
        m = re.search(r'(https://vtrans\.s3-private\.mds\.yandex\.net[^\s"\'\)]+)', output_text)
        if not m:
            m = re.search(r'(https://[^\s"\'\)]+vtrans[^\s"\'\)]+)', output_text)

        if m:
            audio_url = m.group(1).strip()
            term_log("✅ YANDEX AI", f"Ссылка получена! Скачивание MP3: {audio_url[:55]}...", Colors.GREEN)

            def _download():
                req = urllib.request.Request(audio_url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=30) as resp, open(tmp_mp3, "wb") as f:
                    f.write(resp.read())

            await loop.run_in_executor(None, _download)

            if os.path.exists(tmp_mp3) and os.path.getsize(tmp_mp3) > 1024:
                term_log("✅ YANDEX AI", f"Русская озвучка сохранена: {tmp_filename}", Colors.GREEN)
                return tmp_mp3

        term_log("⚠️ YANDEX AI", "Не удалось найти ссылку на аудио в выводе vot-cli-live", Colors.YELLOW)

    except Exception as e:
        term_log("❌ YANDEX AI", f"Ошибка вызова vot-cli-live: {e}", Colors.RED)

    return None


def merge_yandex_audio(video_src: str, voice_mp3: str, video_dst: str, cancel_token=None) -> bool:
    """
    Сводит русскую озвучку с оригинальным видео через Direct Copy (без пережатия картинки):
    Оригинальный звук приглушается до 18%, а сверху чисто звучит русский голос.
    """
    cmd = [
        "ffmpeg", "-y",
        "-i", video_src,
        "-i", voice_mp3,
        "-filter_complex",
        "[0:a]volume=0.18[orig];[orig][1:a]amix=inputs=2:duration=first:dropout_transition=2[aout]",
        "-map", "0:v",
        "-map", "[aout]",
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart",
        video_dst
    ]
    ok, _ = run_ffmpeg(cmd, video_dst, cancel_token)
    return ok

# ─────────────────────────────────────────────
# ДВИЖОК DIRECT COPY
# ─────────────────────────────────────────────
def probe(path: str) -> dict:
    result = {"width": 0, "height": 0, "duration": 0, "fps": 30, "vcodec": "", "acodec": ""}
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "stream=width,height,duration,r_frame_rate,codec_name,codec_type",
            "-show_entries", "format=duration",
            "-of", "json", path
        ]
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        data = json.loads(out.stdout)
        for s in data.get("streams", []):
            if s.get("width"):
                result["width"] = s["width"]
                result["height"] = s["height"]
                result["vcodec"] = s.get("codec_name", "")
                if s.get("duration"):
                    result["duration"] = int(float(s["duration"]))
                fps_str = s.get("r_frame_rate", "30/1")
                if "/" in fps_str:
                    n, d = fps_str.split("/")
                    result["fps"] = round(int(n) / max(int(d), 1))
            elif s.get("codec_type") == "audio":
                result["acodec"] = s.get("codec_name", "")
        if result["duration"] == 0:
            dur = data.get("format", {}).get("duration")
            if dur:
                result["duration"] = int(float(dur))
    except Exception as e:
        term_log("❌ FFPROBE", f"Ошибка анализа {path}: {e}", Colors.RED)
    return result

def run_ffmpeg(cmd: List[str], output: str, cancel_token=None) -> Tuple[bool, str]:
    err_lines = []
    try:
        p = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1
        )
        while True:
            if cancel_token and cancel_token.cancelled:
                p.terminate()
                try:
                    p.wait(timeout=3)
                except Exception:
                    p.kill()
                raise ValueError("CANCELLED")

            line = p.stderr.readline()
            if line:
                err_lines.append(line)
                if len(err_lines) > 50:
                    err_lines.pop(0)
            elif p.poll() is not None:
                break
            else:
                time.sleep(0.05)

        p.wait()
        returncode = p.returncode
        err = "".join(err_lines)
    except ValueError as e:
        if str(e) == "CANCELLED":
            raise
        return False, str(e)
    except Exception as e:
        term_log("❌ FFMPEG", f"Ошибка процесса: {e}", Colors.RED)
        return False, str(e)

    if returncode != 0 or not os.path.exists(output) or os.path.getsize(output) == 0:
        err = (err or "")[-600:]
        term_log("❌ FFMPEG FAIL", f"Код {returncode}: {err}", Colors.RED)
        return False, err
    return True, ""

def process_video_direct(src: str, dst: str, cancel_token=None) -> Tuple[bool, str]:
    info = probe(src)
    if info["vcodec"] in ("h264", "avc1") and info["acodec"] in ("aac", "mp3"):
        cmd = ["ffmpeg", "-y", "-i", src, "-c:v", "copy", "-c:a", "copy", "-movflags", "+faststart", dst]
    else:
        cmd = ["ffmpeg", "-y", "-i", src, "-c:v", "copy", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", dst]
    return run_ffmpeg(cmd, dst, cancel_token)

# ─────────────────────────────────────────────
# YT-DLP ЗАГРУЗЧИК
# ─────────────────────────────────────────────
# ─────────────────────────────────────────────
# ОПРЕДЕЛЕНИЕ COOKIES (с проверкой свежести файла)
# ─────────────────────────────────────────────
# Каждый прямой запрос к браузерным cookies (cookiesfrombrowser) заставляет
# yt-dlp заново сканировать базу cookies браузера — это медленно и печатает
# в консоль мигающий прогресс ("Extracting cookies from edge: 0/75"),
# который НЕ отключается через quiet/no_warnings. Поэтому материализуем
# куки из браузера в обычный файл раз в BROWSER_COOKIE_CACHE_TTL секунд,
# а дальше просто переиспользуем этот файл как cookiefile — быстро и тихо.
_BROWSER_COOKIE_CACHE_PATH = "_browser_cookies_cache.txt"
BROWSER_COOKIE_CACHE_TTL = float(_env("BROWSER_COOKIE_CACHE_TTL_SECONDS", "900"))
_browser_cookie_lock = threading.Lock()

def _materialize_browser_cookies() -> bool:
    """Пишет куки из браузера в файл атомарно и под локом.
    Ловит PermissionError когда браузер запущен и держит лок."""
    with _browser_cookie_lock:
        tmp_path = _BROWSER_COOKIE_CACHE_PATH + ".tmp"
        try:
            with yt_dlp.YoutubeDL({
                "quiet": True,
                "no_warnings": True,
                "noprogress": True,
                "cookiesfrombrowser": (BROWSER_COOKIES,),
            }) as ydl:
                ydl.cookiejar.save(tmp_path, ignore_discard=True, ignore_expires=True)
            os.replace(tmp_path, _BROWSER_COOKIE_CACHE_PATH)
            return True
        except PermissionError:
            term_log(
                "⚠️ COOKIES",
                f"Браузер '{BROWSER_COOKIES}' удерживает лок — закрой его или используй cookies.txt",
                Colors.YELLOW
            )
        except Exception as e:
            term_log("⚠️ COOKIES", f"Не удалось извлечь куки из '{BROWSER_COOKIES}': {e}", Colors.YELLOW)
        finally:
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except Exception:
                pass
        return False

def get_cookie_opts() -> dict:
    """
    Умный выбор cookies с защитой от PermissionError при запущенном браузере.
    НИКОГДА не передаёт cookiesfrombrowser напрямую в скачивание —
    если браузер держит лок, это роняет загрузку.
    """
    # 1. Проверяем файлы cookies.txt
    candidates = []
    if COOKIE_FILE:
        candidates.append(COOKIE_FILE)
    candidates.append("www.youtube.com_cookies.txt")
    candidates.append("cookies.txt")

    for path in candidates:
        if path and os.path.exists(path):
            age_hours = (time.time() - os.path.getmtime(path)) / 3600
            if age_hours <= COOKIE_MAX_AGE_HOURS:
                return {"cookiefile": path}
            else:
                term_log(
                    "⚠️ COOKIES",
                    f"Файл {path} устарел ({age_hours:.1f}ч > {COOKIE_MAX_AGE_HOURS}ч)",
                    Colors.YELLOW
                )

    # 2. Пробуем кэш из браузера
    if BROWSER_COOKIES and BROWSER_COOKIES.lower() not in ("none", "false", "0", ""):
        cache_exists = os.path.exists(_BROWSER_COOKIE_CACHE_PATH)
        cache_age = (time.time() - os.path.getmtime(_BROWSER_COOKIE_CACHE_PATH)) if cache_exists else float("inf")

        # Кэш свежий — используем сразу
        if cache_exists and cache_age <= BROWSER_COOKIE_CACHE_TTL:
            return {"cookiefile": _BROWSER_COOKIE_CACHE_PATH}

        # Пробуем обновить
        if _materialize_browser_cookies():
            return {"cookiefile": _BROWSER_COOKIE_CACHE_PATH}

        # Обновить не удалось (браузер запущен?) — берём старый кэш если не протух
        if cache_exists and cache_age <= COOKIE_MAX_AGE_HOURS:
            term_log(
                "⚠️ COOKIES",
                f"Браузер недоступен, использую кэш ({cache_age/60:.0f} мин)",
                Colors.YELLOW
            )
            return {"cookiefile": _BROWSER_COOKIE_CACHE_PATH}

        # Кэш протух или не существует
        term_log("⚠️ COOKIES", "Куки недоступны — работаю без авторизации", Colors.YELLOW)

    return {}

def ytdlp_opts() -> dict:
    opts = {
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "retries": 10,
        "fragment_retries": 10,
        "concurrent_fragment_downloads": 4,
        "sleep_interval_requests": 1,

        # Ключевое: клиенты, отдающие DASH 1080p/720p
        # tv — YouTube TV app, отдаёт полный DASH без PO Token
        # mweb — мобильный web, отдаёт DASH
        # web — запасной
        "extractor_args": {
            "youtube": ["player_client=tv,mweb,web"]
        },
    }

    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        opts["ffmpeg_location"] = os.path.dirname(ffmpeg_path)

    if YTDLP_USE_PROXY:
        opts["proxy"] = f"socks5://{YTDLP_PROXY_HOST}:{YTDLP_PROXY_PORT}"

    opts.update(get_cookie_opts())
    return opts

def make_progress_hook(video_id: str, cancel_token=None):
    """Хук для yt-dlp: пишет скорость/%/ETA в терминал (раз в ~3 сек, чтобы не
    спамить), плюс проверяет отмену. noprogress=True в opts глушит ТОЛЬКО
    встроенный вывод yt-dlp (и мигание при чтении cookies из браузера) —
    на этот наш собственный хук он не влияет."""
    state = {"last_log": 0.0}

    def hook(d):
        if cancel_token and cancel_token.cancelled:
            raise ValueError("CANCELLED")

        status = d.get("status")
        if status == "downloading":
            now = time.time()
            if now - state["last_log"] >= 3:
                state["last_log"] = now
                downloaded = d.get("downloaded_bytes") or 0
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                speed = d.get("speed") or 0
                pct = (downloaded / total * 100) if total else 0
                eta = d.get("eta")
                speed_mb = (speed / 1024 / 1024) if speed else 0
                term_log(
                    "📥 DOWNLOAD",
                    f"[{video_id}] {pct:5.1f}% | {speed_mb:6.2f} МБ/с | ETA {eta if eta is not None else '?'}с "
                    f"| {downloaded / 1024 / 1024:.1f}/{total / 1024 / 1024:.1f} МБ",
                    Colors.CYAN
                )
        elif status == "finished":
            term_log("✅ DOWNLOAD", f"[{video_id}] Скачивание завершено, обрабатываю (merge/конвертация)...", Colors.GREEN)
        elif status == "error":
            term_log("❌ DOWNLOAD", f"[{video_id}] yt-dlp сообщил об ошибке во время скачивания", Colors.RED)

    return hook

def download_video(url: str, quality: str, user_id: int, video_id: str, lang: str = "orig", cancel_token=None) -> str:
    opts = ytdlp_opts()
    opts["noplaylist"] = True
    opts["progress_hooks"] = [make_progress_hook(video_id, cancel_token)]

    file_suffix = f"_{lang}" if lang in ("ru", "en", "ya") else ""
    opts["outtmpl"] = os.path.join(DOWNLOAD_DIR, f"{user_id}_{video_id}{file_suffix}.%(ext)s")
    opts["writethumbnail"] = True
    opts["merge_output_format"] = "mp4"

    q = int(quality) if str(quality).isdigit() else 720
    max_w_map = {1080: 1920, 720: 1280, 480: 854, 360: 640}
    max_w = max_w_map.get(q, 1280)

    if lang == "ru":
        opts["format_sort"] = ["hasaud", "lang:ru", f"res:{q}", "codec:h264:vp9:av1", "fps", "size", "br"]
        opts["extractor_args"] = {
            "youtube": ["player_client=web,mweb", "lang=ru"]
        }
        audio_priority = [
            "bestaudio[language^=ru]", "bestaudio[language*=ru]",
            "bestaudio[format_note*=Russian]", "bestaudio[format_note*=русск]",
            "bestaudio[format_id*=-ru]", "bestaudio[format_id*=dubbed]"
        ]
        candidates = []
        for a in audio_priority:
            candidates.append(f"bestvideo[height<={q}]+{a}")
            candidates.append(f"bestvideo[width<={max_w}]+{a}")
        candidates.append(f"best[language^=ru][height<={q}][vcodec!=none]")
        candidates.append(f"best[format_note*=Russian][height<={q}][vcodec!=none]")
        candidates.append(f"bestvideo[height<={q}]+bestaudio")
        candidates.append("best[vcodec!=none]")
        opts["format"] = "/".join(candidates)

    elif lang == "en":
        opts["format_sort"] = ["hasaud", "lang:en", f"res:{q}", "codec:h264:vp9:av1", "fps", "size", "br"]
        opts["extractor_args"] = {
            "youtube": ["player_client=web,mweb", "lang=en"]
        }
        audio_priority = [
            "bestaudio[language^=en]", "bestaudio[language*=en]",
            "bestaudio[format_note*=English]", "bestaudio"
        ]
        candidates = []
        for a in audio_priority:
            candidates.append(f"bestvideo[height<={q}]+{a}")
            candidates.append(f"bestvideo[width<={max_w}]+{a}")
        candidates.append(f"best[language^=en][height<={q}][vcodec!=none]")
        candidates.append("best[vcodec!=none]")
        opts["format"] = "/".join(candidates)

    else:
        # 🔑 ИСПРАВЛЕНИЕ: каждый кандидат — полностью самодостаточный.
        # Больше НЕТ каскада audio_orig внутри строки с оператором +.
        # Каждый вариант явно содержит и видео, и аудио.
        opts["format_sort"] = [f"res:{q}", "fps", "codec:h264:vp9:av1", "size", "br"]
        candidates = [
            # Приоритет 1: видео + оригинальное аудио (явно помеченное)
            f"bestvideo[height<={q}]+ba[format_note*=original]",
            f"bestvideo[width<={max_w}]+ba[format_note*=original]",
            # Приоритет 2: видео + аудио без дубляжа
            f"bestvideo[height<={q}]+ba[format_note!*=dubbed][format_note!*=auto-dub]",
            f"bestvideo[width<={max_w}]+ba[format_note!*=dubbed][format_note!*=auto-dub]",
            # Приоритет 3: видео + стандартные аудио-форматы
            f"bestvideo[height<={q}]+ba[format_id=251]",
            f"bestvideo[height<={q}]+ba[format_id=140]",
            # Приоритет 4: видео + лучшее аудио (общий)
            f"bestvideo[height<={q}]+bestaudio",
            f"bestvideo[width<={max_w}]+bestaudio",
            # Приоритет 5: прогрессивный формат (видео+аудио в одном файле)
            f"best[height<={q}][format_note*=original][vcodec!=none]",
            f"best[height<={q}][vcodec!=none]",
            # Приоритет 6: запасной без ограничения высоты
            "bestvideo+bestaudio",
            "best[vcodec!=none]"
        ]
        opts["format"] = "/".join(candidates)

    term_log("📥 YT-DLP", f"[{user_id}] Загрузка {video_id} ({q}p, аудио: {lang.upper()})...", Colors.CYAN)

    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])

    search_key = f"{video_id}{file_suffix}"
    path = find_file(user_id, search_key)
    if not path:
        path = find_file(user_id, video_id)
    if not path:
        raise FileNotFoundError(f"Файл не найден: {user_id}_{video_id}{file_suffix}")

    # 🔑 ЗАЩИТА: проверяем что скачалось РЕАЛЬНОЕ ВИДЕО, а не только аудио
    info = probe(path)
    if info["width"] == 0 or info["height"] == 0:
        term_log("❌ YT-DLP", f"[{video_id}] Скачанный файл не содержит видеодорожку! Размер: {os.path.getsize(path)/1024/1024:.1f} МБ", Colors.RED)
        try:
            os.remove(path)
        except Exception:
            pass
        raise FileNotFoundError(
            f"Файл не содержит видеодорожку (скачалось только аудио). "
            f"Попробуйте другое качество или проверьте формат-селектор."
        )

    return path

def download_mp3(url: str, user_id: int, video_id: str, lang: str = "orig", cancel_token=None) -> str:
    opts = ytdlp_opts()
    opts["noplaylist"] = True
    opts["progress_hooks"] = [make_progress_hook(video_id, cancel_token)]

    file_suffix = f"_{lang}" if lang in ("ru", "en") else ""
    opts["outtmpl"] = os.path.join(DOWNLOAD_DIR, f"{user_id}_{video_id}{file_suffix}.%(ext)s")

    if lang == "ru":
        opts["format_sort"] = ["lang:ru", "size", "br"]
        opts["format"] = "bestaudio[language^=ru]/bestaudio[format_note*=Russian]/bestaudio/best"
    elif lang == "en":
        opts["format_sort"] = ["lang:en", "size", "br"]
        opts["format"] = "bestaudio[language^=en]/bestaudio[format_note*=English]/bestaudio/best"
    else:
        opts["format_sort"] = ["size", "br"]
        opts["format"] = (
            "ba[format_note*=original]/"
            "ba[format_note!*=dubbed][format_note!*=auto-dub]/"
            "ba[format_id=251]/ba[format_id=140]/"
            "ba/best"
        )

    opts["postprocessors"] = [
        {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}
    ]

    term_log("🎵 YT-DLP", f"[{user_id}] Загрузка MP3: {video_id} ({lang.upper()})...", Colors.YELLOW)

    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])

    path = os.path.join(DOWNLOAD_DIR, f"{user_id}_{video_id}{file_suffix}.mp3")
    if not os.path.exists(path):
        path = find_file(user_id, f"{video_id}{file_suffix}")
    if not path:
        raise FileNotFoundError("MP3 не найден")
    return path

def make_thumb(user_id: int, file_key: str) -> Optional[str]:
    prefix = f"{user_id}_{file_key}."
    raw = None
    for f in os.listdir(DOWNLOAD_DIR):
        if f.startswith(prefix) and f.endswith((".jpg", ".webp", ".png")) and "thumb" not in f:
            raw = os.path.join(DOWNLOAD_DIR, f)
            break
    if not raw:
        return None
    thumb = os.path.join(DOWNLOAD_DIR, f"{user_id}_{file_key}_thumb.jpg")
    subprocess.run(["ffmpeg", "-y", "-i", raw, "-vf", "scale=320:-1", "-q:v", "5", thumb], capture_output=True)
    try:
        os.remove(raw)
    except Exception:
        pass
    return thumb if os.path.exists(thumb) else None

# ─────────────────────────────────────────────
# ЗАГРУЗКА В TELEGRAM
# ─────────────────────────────────────────────
async def upload_file(client: TelegramClient, path: str, progress_cb=None, cancel_token=None) -> types.InputFileBig:
    size = os.path.getsize(path)
    chunk = 512 * 1024
    parts = math.ceil(size / chunk)
    file_id = random.getrandbits(63)
    queue = asyncio.Queue()
    for i in range(parts):
        queue.put_nowait(i)
    uploaded = 0
    lock = asyncio.Lock()

    async def worker(f):
        nonlocal uploaded
        while True:
            if cancel_token and cancel_token.cancelled:
                raise ValueError("CANCELLED")
            try:
                idx = queue.get_nowait()
            except asyncio.QueueEmpty:
                break
            f.seek(idx * chunk)
            data = f.read(chunk)
            for attempt in range(4):
                if cancel_token and cancel_token.cancelled:
                    raise ValueError("CANCELLED")
                try:
                    await client(functions.upload.SaveBigFilePartRequest(
                        file_id=file_id, file_part=idx, file_total_parts=parts, bytes=data))
                    break
                except Exception:
                    if attempt == 3:
                        raise
                    await asyncio.sleep(1)
            async with lock:
                uploaded += 1
                if progress_cb:
                    await progress_cb(min(uploaded * chunk, size), size)

    with open(path, "rb") as f:
        await asyncio.gather(*[worker(f) for _ in range(6)])
    return types.InputFileBig(id=file_id, parts=parts, name=os.path.basename(path))

# ─────────────────────────────────────────────
# КЛАВИАТУРЫ (REPLY И INLINE)
# ─────────────────────────────────────────────
def get_reply_keyboard(uid: int):
    """Постоянное Reply-меню (кнопки внизу экрана)"""
    if is_admin(uid):
        return [
            [Button.text("👑 Админ-панель", resize=True), Button.text("⚡ Кэш роликов")],
            [Button.text("💎 Белый список (4 ГБ)"), Button.text("👥 Пользователи")],
            [Button.text("📜 Список команд"), Button.text("📊 Статистика")]
        ]
    return [
        [Button.text("ℹ️ О боте и лимитах", resize=True), Button.text("❓ Как пользоваться")],
        [Button.text("📊 Моя статистика")]
    ]

def make_video_keyboard(vid: str, current_lang: str = "orig", is_playlist: bool = False) -> List[List[Button]]:
    meta = video_meta.get(vid, {})
    tiers = meta.get("tiers", [1080, 720, 480, 360])
    duration = meta.get("duration", 0)
    audio_info = meta.get("audio_info", {})

    buttons = []

    # 1. Плейлист
    if is_playlist:
        if audio_info.get("needs_yandex_ai"):
            ya_mark = "✅ " if current_lang == "ya" else ""
            orig_mark = "✅ " if current_lang == "orig" else ""
            buttons.append([
                Button.inline(f"{ya_mark}🤖 Перевод Яндекс", f"pllang:ya:{vid}".encode()),
                Button.inline(f"{orig_mark}🇬🇧 Оригинал", f"pllang:orig:{vid}".encode())
            ])
        elif audio_info.get("has_official_dub"):
            ru_mark = "✅ " if current_lang == "ru" else ""
            en_mark = "✅ " if current_lang == "en" else ""
            buttons.append([
                Button.inline(f"{ru_mark}🇷🇺 Дубляж", f"pllang:ru:{vid}".encode()),
                Button.inline(f"{en_mark}🇬🇧 Оригинал", f"pllang:en:{vid}".encode())
            ])

        buttons.append([
            Button.inline("⚡ 1080p", f"pl:3:1080:{vid}:{current_lang}".encode()),
            Button.inline("⚡ 720p", f"pl:3:720:{vid}:{current_lang}".encode())
        ])
        buttons.append([
            Button.inline("⚡ 480p", f"pl:3:480:{vid}:{current_lang}".encode()),
            Button.inline("⚡ 360p", f"pl:3:360:{vid}:{current_lang}".encode())
        ])
        buttons.append([Button.inline("🎵 Весь плейлист в MP3", f"pl:3:mp3:{vid}:{current_lang}".encode())])
        return buttons

    # 2. Обычное видео
    if audio_info.get("has_official_dub"):
        ru_mark = "✅ " if current_lang == "ru" else ""
        en_mark = "✅ " if current_lang == "en" else ""
        buttons.append([
            Button.inline(f"{ru_mark}🇷🇺 Дубляж", f"lang:ru:{vid}".encode()),
            Button.inline(f"{en_mark}🇬🇧 Оригинал", f"lang:en:{vid}".encode())
        ])
    elif audio_info.get("needs_yandex_ai"):
        ya_mark = "✅ " if current_lang == "ya" else ""
        orig_mark = "✅ " if current_lang == "orig" else ""
        buttons.append([
            Button.inline(f"{ya_mark}🤖 Перевод Яндекс", f"lang:ya:{vid}".encode()),
            Button.inline(f"{orig_mark}🇬🇧 Оригинал", f"lang:orig:{vid}".encode())
        ])

    row = []
    for t in tiers:
        has_cached = bool(db.get_cache(vid, str(t), lang=current_lang))
        icon = "⚡" if has_cached else "🎬"
        est_mb = estimate_size_mb(duration, t)
        row.append(Button.inline(f"{icon} {t}p (~{est_mb} МБ)", f"dl:{t}:{vid}:{current_lang}".encode()))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    mp3_cached = bool(db.get_cache(vid, "mp3", lang=current_lang))
    mp3_icon = "⚡" if mp3_cached else "🎵"
    mp3_mb = max(1, int((192 * max(duration, 1)) / (8 * 1024)))
    buttons.append([Button.inline(f"{mp3_icon} Скачать MP3 (~{mp3_mb} МБ)", f"dl:mp3:{vid}:{current_lang}".encode())])
    return buttons

# ─────────────────────────────────────────────
# СОСТОЯНИЕ БОТА И ТОКЕНЫ
# ─────────────────────────────────────────────
bot: Optional[TelegramClient] = None
user_client: Optional[TelegramClient] = None
video_meta: Dict[str, dict] = {}
is_premium = False
bot_username = ""
owner_id = 0
upload_semaphore = asyncio.Semaphore(1)

class CancelToken:
    def __init__(self):
        self.cancelled = False
    def cancel(self):
        self.cancelled = True

cancel_tokens: Dict[str, CancelToken] = {}

# ═══════════════════════════════════════════════
# ХЕНДЛЕРЫ TELEGRAM
# ═══════════════════════════════════════════════
def setup_handlers(client: TelegramClient):

    def check_admin(uid: int) -> bool:
        return is_admin(uid)

    def check_owner(uid: int) -> bool:
        return is_owner(uid)

    @client.on(events.NewMessage(pattern=re.compile(r"^/start(?:\s+.*)?$", re.IGNORECASE)))
    async def cmd_start(event):
        db.register_user(event.sender_id, getattr(event.sender, "username", "") or "")
        limit = "4 ГБ 💎" if (is_premium_user(event.sender_id) and is_premium) else "2 ГБ"
        term_log("👋 USER", f"Пользователь {event.sender_id} нажал /start", Colors.BLUE)
        await event.respond(
            "👋 **Привет! Я YouTube Monster Bot.**\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "💬 **Как пользоваться:**\n"
            "1️⃣ Отправь ссылку на ролик YouTube / Shorts / плейлист\n"
            "2️⃣ Выбери качество кнопками (размер файла указан рядом)\n"
            "3️⃣ Если ролик на английском — доступен нейроперевод Яндекс\n"
            "4️⃣ Мгновенная доставка прямо в чат!\n\n"
            "⚡ **Direct Copy** — скачивание без рендера за 1-2 секунды\n"
            f"🛡 **Максимальный размер:** {limit}\n"
            "━━━━━━━━━━━━━━━━━━━━",
            buttons=get_reply_keyboard(event.sender_id)
        )

    # ─────────────────────────────────────────
    # ОБРАБОТКА REPLY-МЕНЮ (НИЖНИЕ КНОПКИ)
    # ─────────────────────────────────────────
    @client.on(events.NewMessage(func=lambda e: e.text in (
        "👑 Админ-панель", "⚡ Кэш роликов", "💎 Белый список (4 ГБ)",
        "👥 Пользователи", "📜 Список команд", "📊 Статистика",
        "ℹ️ О боте и лимитах", "❓ Как пользоваться", "📊 Моя статистика"
    )))
    async def on_reply_menu_click(event):
        txt = event.text
        uid = event.sender_id

        if txt == "👑 Админ-панель":
            await cmd_admin(event)
        elif txt == "⚡ Кэш роликов":
            await cmd_cache(event)
        elif txt == "💎 Белый список (4 ГБ)":
            await cmd_whitelist(event)
        elif txt == "👥 Пользователи":
            await cmd_users(event)
        elif txt == "📜 Список команд":
            await cmd_commands(event)
        elif txt == "📊 Статистика":
            s = db.stats()
            await event.respond(
                f"📊 **СТАТИСТИКА БОТА**\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"👥 Всего пользователей: `{s['users']}`\n"
                f"🎬 Скачано роликов: `{s['videos']}`\n"
                f"💾 Всего трафика: `{s['gb']:.2f} ГБ`\n"
                f"⚡ Файлов в локальном кэше: `{s['cache']}`"
            )
        elif txt == "ℹ️ О боте и лимитах":
            limit = "4 ГБ 💎" if (is_premium_user(uid) and is_premium) else "2 ГБ"
            await event.respond(
                f"ℹ️ **О СЕРВИСЕ И ЛИМИТАХ**\n\n"
                f"🛡 Ваш текущий лимит на файл: **{limit}**\n"
                f"🚀 Движок: Direct Copy (без пережатия видео)\n"
                f"⚡ Кэш: ранее скачанные ролики отдаются за 0.1 сек\n"
                f"🤖 Поддержка нейроперевода Яндекс для зарубежных видео."
            )
        elif txt == "❓ Как пользоваться":
            await event.respond(
                "💬 **ИНСТРУКЦИЯ:**\n\n"
                "1. Скопируйте ссылку на видео, Shorts или плейлист с YouTube.\n"
                "2. Отправьте её боту сообщением.\n"
                "3. Нажмите на инлайн-кнопку с желаемым качеством.\n"
                "Бот подготовит файл и пришлёт его прямо в этот диалог!"
            )
        elif txt == "📊 Моя статистика":
            vids, mb = db.get_user_stats(uid)
            await event.respond(
                f"📊 **ВАША АКТИВНОСТЬ:**\n\n"
                f"🎬 Скачано роликов: `{vids}`\n"
                f"💾 Загружено трафика: `{mb / 1024:.2f} ГБ` ({mb:.0f} МБ)"
            )

    # ─────────────────────────────────────────
    # ПАНЕЛЬ АДМИНИСТРАТОРА И СПИСОК КОМАНД
    # ─────────────────────────────────────────
    COMMANDS_TEXT = (
        "📜 <b>СПИСОК ВСЕХ КОМАНД БОТА</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "👑 <b>Команды Владельца:</b>\n"
        "• <code>/addadmin &lt;ID|@username&gt;</code> — назначить администратора\n"
        "• <code>/deladmin &lt;ID|@username&gt;</code> — снять администратора\n"
        "• <code>/delcache &lt;video_id&gt; [качество]</code> — удалить видео из кэша и диска\n"
        "• <code>/clearcache</code> — полная очистка всего кэша\n\n"
        "🔧 <b>Команды Администратора:</b>\n"
        "• <code>/admin</code> — открыть интерактивную админ-панель\n"
        "• <code>/commands</code> или <code>/help</code> — этот список команд\n"
        "• <code>/cache [номер]</code> — управление кэшем (новые сверху, переход по цифре)\n"
        "• <code>/cache &lt;запрос&gt;</code> — поиск по названию или ID в кэше\n"
        "• <code>/users</code> — список последних 50 пользователей\n"
        "• <code>/admins</code> — список действующих администраторов\n"
        "• <code>/whitelist</code> — список пользователей с лимитом 4 ГБ\n"
        "• <code>/addpremium &lt;ID|@username&gt;</code> — выдать лимит 4 ГБ\n"
        "• <code>/delpremium &lt;ID|@username&gt;</code> — забрать лимит 4 ГБ\n"
        "• <code>/ban &lt;ID|@username&gt;</code> — заблокировать пользователя\n"
        "• <code>/unban &lt;ID|@username&gt;</code> — разблокировать пользователя\n"
        "• <code>/broadcast &lt;текст&gt;</code> — массовая рассылка\n\n"
        "👤 <b>Пользовательские:</b>\n"
        "• <code>/start</code> — перезапуск бота и меню"
    )

    @client.on(events.NewMessage(pattern=re.compile(r"^/(?:commands|help)(?:@\w+)?(?:\s+.*)?$", re.IGNORECASE)))
    async def cmd_commands(event):
        if not check_admin(event.sender_id):
            return await event.respond("❌ Недостаточно прав для просмотра команд.")
        await event.respond(COMMANDS_TEXT, parse_mode="html")

    @client.on(events.NewMessage(pattern=re.compile(r"^/admin(?:@\w+)?(?:\s+.*)?$", re.IGNORECASE)))
    async def cmd_admin(event):
        if not check_admin(event.sender_id):
            return await event.respond("❌ Недостаточно прав.")
        s = db.stats()
        is_own = check_owner(event.sender_id)
        role = "👑 ВЛАДЕЛЕЦ" if is_own else "🔧 АДМИНИСТРАТОР"
        kb = [
            [Button.inline("👥 Юзеры", b"adm:users"), Button.inline("💎 Белый список", b"adm:whitelist")],
            [Button.inline("⚡ Кэш роликов", b"adm:cache:1"), Button.inline("🔧 Админы", b"adm:admins")],
            [Button.inline("📜 Все команды", b"adm:cmdlist"), Button.inline("🔄 Обновить", b"adm:refresh")]
        ]
        await event.respond(
            f"{role} **ПАНЕЛЬ УПРАВЛЕНИЯ**\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"👥 Пользователей: `{s['users']}`\n"
            f"🎬 Скачано видео: `{s['videos']}`\n"
            f"💾 Всего трафика: `{s['gb']:.2f} ГБ`\n"
            f"⚡ Роликов в кэше: `{s['cache']}`\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"🚀 Движок: `Direct Copy` (0% CPU)\n"
            f"💎 Premium контур: `{'Включен (4 ГБ)' if is_premium else 'Стандарт (2 ГБ)'}`\n"
            f"👑 Владелец: `{OWNER_ID}`\n"
            f"🔧 Доп. админов: `{len(ADMIN_IDS)}`",
            buttons=kb
        )

    @client.on(events.CallbackQuery(pattern=b"^adm:cmdlist$"))
    async def cb_admin_cmdlist(event):
        if not check_admin(event.sender_id):
            return await event.answer("❌ Доступ запрещен.", alert=True)
        kb = [[Button.inline("🔙 Назад в меню", b"adm:panel")]]
        await event.edit(COMMANDS_TEXT, parse_mode="html", buttons=kb)

    # ─────────────────────────────────────────
    # УПРАВЛЕНИЕ АДМИНАМИ
    # ─────────────────────────────────────────
    @client.on(events.NewMessage(pattern=re.compile(r"^/admins(?:@\w+)?(?:\s+.*)?$", re.IGNORECASE)))
    async def cmd_admins(event):
        if not check_admin(event.sender_id):
            return await event.respond("❌ Недостаточно прав.")
        lines = ["🔧 <b>Список администраторов бота:</b>\n"]
        lines.append(f"👑 <b>Владелец:</b> <code>{OWNER_ID}</code>\n")
        if not ADMIN_IDS:
            lines.append("📭 Дополнительных админов нет.")
        else:
            for uid in sorted(ADMIN_IDS):
                lines.append(f"• 🔧 {user_link(uid)} — <code>{uid}</code>")
        await event.respond("\n".join(lines), parse_mode="html")

    @client.on(events.NewMessage(pattern=re.compile(r"^/addadmin(?:@\w+)?\s+(.+)$", re.IGNORECASE)))
    async def cmd_addadmin(event):
        if not check_owner(event.sender_id):
            return await event.respond("❌ Только владелец бота может назначать администраторов.")
        arg = event.pattern_match.group(1).strip()
        uid, uname, err = await resolve_user(client, arg)
        if err:
            return await event.respond(err)

        if uid == OWNER_ID:
            return await event.respond("⚠️ Этот пользователь уже является владельцем бота.")
        if uid in ADMIN_IDS:
            return await event.respond(f"⚠️ {user_link(uid, uname)} уже является администратором.", parse_mode="html")

        db.add_admin(uid, uname)
        save_admin_list()
        term_log("👑 ADMIN ADD", f"Владелец назначил админа: {uid} (@{uname})", Colors.MAGENTA)
        await event.respond(f"✅ Пользователь {user_link(uid, uname)} назначен **администратором**.", parse_mode="html")

    @client.on(events.NewMessage(pattern=re.compile(r"^/deladmin(?:@\w+)?\s+(.+)$", re.IGNORECASE)))
    async def cmd_deladmin(event):
        if not check_owner(event.sender_id):
            return await event.respond("❌ Только владелец бота может снимать администраторов.")
        arg = event.pattern_match.group(1).strip()
        uid, uname, err = await resolve_user(client, arg)
        if err and not uid:
            return await event.respond(err)

        if uid not in ADMIN_IDS:
            return await event.respond("⚠️ Пользователь не найден среди администраторов.")

        db.del_admin(uid)
        save_admin_list()
        term_log("🗑️ ADMIN DEL", f"Владелец снял админа: {uid}", Colors.MAGENTA)
        await event.respond(f"🗑 Пользователь {user_link(uid, uname)} снят с должности администратора.", parse_mode="html")

    # ─────────────────────────────────────────
    # УПРАВЛЕНИЕ КЭШЕМ (СВЕЖИЕ СВЕРХУ)
    # ─────────────────────────────────────────
    def format_cache_item(vid: str, q_key: str, title: str, dt) -> Tuple[str, str]:
        t_clean = (title or "").strip()
        if not t_clean or t_clean.lower() in ("none", "без названия", "unknown"):
            t_clean = f"YouTube Видео ({vid})"

        if "_" in str(q_key):
            res_part, lang_part = q_key.split("_", 1)
            flag = "🇷🇺" if lang_part == "ru" else ("🤖" if lang_part == "ya" else "🇬🇧")
            label = f"{res_part}p [{flag} {lang_part.upper()}]"
        else:
            label = f"{q_key}p [Оригинал]"
        return t_clean, label

    async def render_cache_page(event, page: int = 1):
        items, total = db.get_cache_page(page, page_size=5)
        max_page = max(1, math.ceil(total / 5))

        if page > max_page or page < 1:
            err_text = f"❌ **Страницы `{page}` не существует!**\nВсего доступно страниц: **от 1 до {max_page}**."
            if isinstance(event, events.CallbackQuery.Event):
                return await event.answer(f"Страницы {page} нет! Всего: 1-{max_page}", alert=True)
            return await event.respond(err_text)

        if not items:
            text = "⚡ **Кэш видео пуст.**"
            kb = [[Button.inline("🔙 Назад в админку", b"adm:panel")]]
            if isinstance(event, events.CallbackQuery.Event):
                return await event.edit(text, buttons=kb)
            return await event.respond(text, buttons=kb)

        lines = [
            f"⚡ **КЭШ РОЛИКОВ** (Стр. `{page}/{max_page}` | Всего: `{total}`)\n"
            f"📌 *Свежие ролики всегда отображаются первыми в списке!*\n"
            f"━━━━━━━━━━━━━━━━━━━━"
        ]
        buttons = []

        start_num = (page - 1) * 5 + 1
        for idx, (vid, q_key, title, dt, file_id) in enumerate(items, start=start_num):
            t_clean, label = format_cache_item(vid, q_key, title, dt)
            lines.append(f"<b>#{idx}</b> 🎬 <b>{t_clean[:38]}</b>\n   └ ID: <code>{vid}</code> | {label}")
            row = [Button.inline("🎬 Отправить", f"cview:{vid}:{q_key}".encode())]
            if check_owner(event.sender_id):
                row.append(Button.inline("🗑 Удалить", f"cdel:{vid}:{q_key}:{page}".encode()))
            buttons.append(row)

        nav_row = []
        if page > 1:
            nav_row.append(Button.inline("◀️ Назад", f"adm:cache:{page-1}".encode()))
        nav_row.append(Button.inline(f"• {page}/{max_page} •", f"adm:cache:{page}".encode()))
        if page < max_page:
            nav_row.append(Button.inline("Вперёд ▶️", f"adm:cache:{page+1}".encode()))
        buttons.append(nav_row)

        bottom_row = []
        if check_owner(event.sender_id):
            bottom_row.append(Button.inline("💥 Очистить всё", b"cdel:all:confirm"))
        bottom_row.append(Button.inline("🔙 В админку", b"adm:panel"))
        buttons.append(bottom_row)

        msg_text = (
            "\n".join(lines) + 
            "\n━━━━━━━━━━━━━━━━━━━━\n"
            "💡 *Для перехода напишите:* `/cache <номер_страницы>`"
        )

        if isinstance(event, events.CallbackQuery.Event):
            await event.edit(msg_text, buttons=buttons, parse_mode="html")
        else:
            await event.respond(msg_text, buttons=buttons, parse_mode="html")

    @client.on(events.NewMessage(pattern=re.compile(r"^/cache(?:@\w+)?(?:\s+(.+))?$", re.IGNORECASE)))
    async def cmd_cache(event):
        if not check_admin(event.sender_id):
            return await event.respond("❌ Недостаточно прав.")
        
        query = event.pattern_match.group(1) if getattr(event, 'pattern_match', None) else None

        if query and query.strip().isdigit():
            target_page = int(query.strip())
            return await render_cache_page(event, page=target_page)

        if query:
            q_clean = query.strip()
            results = db.search_cache(q_clean, limit=10)
            if not results:
                return await event.respond(f"🔍 В кэше ничего не найдено по запросу `{q_clean}`.")
            lines = [f"🔍 <b>Результаты поиска в кэше по '{q_clean}':</b>\n"]
            buttons = []
            for vid, quality_key, title, created, file_id in results:
                t_clean, label = format_cache_item(vid, quality_key, title, created)
                lines.append(f"• <b>{t_clean[:38]}</b> | {label}")
                row = [Button.inline("🎬 Отправить", f"cview:{vid}:{quality_key}".encode())]
                if check_owner(event.sender_id):
                    row.append(Button.inline("🗑 Удалить", f"cdel:{vid}:{quality_key}:1".encode()))
                buttons.append(row)
            await event.respond("\n".join(lines), parse_mode="html", buttons=buttons)
        else:
            await render_cache_page(event, page=1)

    @client.on(events.CallbackQuery(pattern=b"^cview:"))
    async def cb_cache_view_video(event):
        if not check_admin(event.sender_id):
            return await event.answer("❌ Доступ запрещен.", alert=True)

        data_str = event.data.decode("utf-8")
        parts = data_str.split(":")
        vid = parts[1]
        q_key = parts[2]

        quality = q_key.split("_")[0] if "_" in q_key else q_key
        lang = q_key.split("_")[1] if "_" in q_key else "orig"
        cache_data = db.get_cache(vid, quality, lang=lang)

        if not cache_data:
            return await event.answer("⚠️ Файл не найден в базе кэша.", alert=True)

        file_id, title = cache_data
        await event.answer("🚀 Отправляю видео из кэша...")
        term_log("⚡ CVIEW", f"Просмотр из кэша: {vid} [{q_key}]", Colors.GREEN)

        try:
            flag = "🇷🇺 RU" if lang == "ru" else ("🤖 YANDEX AI" if lang == "ya" else "🇬🇧 EN")
            caption = f"🎬 <b>{title or vid}</b> [{flag} {quality}p]\n⚡ <i>Отправлено напрямую из базы кэша</i>"
            await client.send_file(event.sender_id, file_id, caption=caption, parse_mode="html")
        except Exception as e:
            await event.respond(f"❌ Ошибка отправки из кэша:\n`{e}`")

    @client.on(events.CallbackQuery(pattern=b"^adm:cache:"))
    async def cb_cache_page(event):
        if not check_admin(event.sender_id):
            return await event.answer("❌ Доступ запрещен.", alert=True)
        data_str = event.data.decode("utf-8")
        page = int(data_str.split(":")[2])
        await render_cache_page(event, page)

    @client.on(events.CallbackQuery(pattern=b"^cdel:all:confirm$"))
    async def cb_cache_clear_confirm(event):
        if not check_owner(event.sender_id):
            return await event.answer("⛔ Только ВЛАДЕЛЕЦ может очищать весь кэш!", alert=True)
        kb = [
            [Button.inline("💥 ДА, УДАЛИТЬ ВСЁ", b"cdel:all:do")],
            [Button.inline("❌ Отмена", b"adm:cache:1")]
        ]
        await event.edit(
            "⚠️ **ВЫ УВЕРЕНЫ, ЧТО ХОТИТЕ ПОЛНОСТЬЮ ОЧИСТИТЬ КЭШ?**\n\n"
            "Все записи кэша будут удалены из базы bot.db.",
            buttons=kb
        )

    @client.on(events.CallbackQuery(pattern=b"^cdel:all:do$"))
    async def cb_cache_clear_execute(event):
        if not check_owner(event.sender_id):
            return await event.answer("⛔ Только ВЛАДЕЛЕЦ может очищать кэш!", alert=True)
        count = db.clear_all_cache()
        term_log("💥 CACHE PURGE", f"Владелец очистил весь кэш ({count} записей)", Colors.RED)
        await event.answer("✅ Весь кэш успешно удален!", alert=True)
        await render_cache_page(event, page=1)

    @client.on(events.CallbackQuery(pattern=re.compile(rb"^cdel:(?!all:)")))
    async def cb_del_cache_item(event):
        if not check_owner(event.sender_id):
            return await event.answer("⛔ Удалять видео из кэша может ТОЛЬКО владелец бота!", alert=True)

        data_str = event.data.decode("utf-8")
        parts = data_str.split(":")
        vid = parts[1]
        q_key = parts[2]
        page = int(parts[3]) if len(parts) > 3 else 1

        deleted_rows = db.del_cache(vid, q_key)
        cleaned_files = cleanup_disk_for_video(vid)

        if deleted_rows > 0 or cleaned_files > 0:
            term_log("🗑️ CACHE DEL", f"Удалено из кэша {vid} [{q_key}] (БД: {deleted_rows}, Диск: {cleaned_files})", Colors.GREEN)
            await event.answer(f"✅ Удалено: {vid} [{q_key}]", alert=False)
        else:
            await event.answer("⚠️ Запись уже удалена из кэша.", alert=True)

        await render_cache_page(event, page)

    @client.on(events.NewMessage(pattern=re.compile(r"^/delcache(?:@\w+)?\s+(\S+)(?:\s+(\S+))?$", re.IGNORECASE)))
    async def cmd_delcache_manual(event):
        if not check_owner(event.sender_id):
            return await event.respond("❌ Только владелец бота может удалять записи из кэша.")
        vid = event.pattern_match.group(1).strip()
        q = event.pattern_match.group(2)
        target = f"{q}" if q else ""
        deleted = db.del_cache(vid, target)
        cleaned = cleanup_disk_for_video(vid)
        term_log("🗑️ MANUAL DELCACHE", f"Удалено {vid}: {deleted} записей, {cleaned} файлов с диска", Colors.GREEN)
        if deleted or cleaned:
            await event.respond(f"✅ Видео `{vid}` успешно удалено из кэша и диска.")
        else:
            await event.respond(f"⚠️ Видео `{vid}` не найдено в кэше.")

    @client.on(events.NewMessage(pattern=re.compile(r"^/clearcache(?:@\w+)?$", re.IGNORECASE)))
    async def cmd_clearcache_manual(event):
        if not check_owner(event.sender_id):
            return await event.respond("❌ Только владелец бота может очищать кэш.")
        count = db.clear_all_cache()
        term_log("💥 CACHE PURGE", f"Владелец очистил кэш ({count} записей)", Colors.RED)
        await event.respond(f"✅ Кэш полностью очищен ({count} записей удалено).")

    # ─────────────────────────────────────────
    # НАВИГАЦИЯ И СПИСКИ
    # ─────────────────────────────────────────
    @client.on(events.CallbackQuery(pattern=b"^adm:panel$"))
    async def cb_admin_panel(event):
        if not check_admin(event.sender_id):
            return await event.answer("❌ Доступ запрещен.", alert=True)
        s = db.stats()
        is_own = check_owner(event.sender_id)
        role = "👑 ВЛАДЕЛЕЦ" if is_own else "🔧 АДМИНИСТРАТОР"
        kb = [
            [Button.inline("👥 Юзеры", b"adm:users"), Button.inline("💎 Белый список", b"adm:whitelist")],
            [Button.inline("⚡ Кэш роликов", b"adm:cache:1"), Button.inline("🔧 Админы", b"adm:admins")],
            [Button.inline("📜 Все команды", b"adm:cmdlist"), Button.inline("🔄 Обновить", b"adm:refresh")]
        ]
        await event.edit(
            f"{role} **ПАНЕЛЬ УПРАВЛЕНИЯ**\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"👥 Пользователей: `{s['users']}`\n"
            f"🎬 Скачано видео: `{s['videos']}`\n"
            f"💾 Всего трафика: `{s['gb']:.2f} ГБ`\n"
            f"⚡ Роликов в кэше: `{s['cache']}`\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"🚀 Движок: `Direct Copy` (0% CPU)\n"
            f"💎 Premium контур: `{'Включен (4 ГБ)' if is_premium else 'Стандарт (2 ГБ)'}`\n"
            f"👑 Владелец: `{OWNER_ID}`\n"
            f"🔧 Доп. админов: `{len(ADMIN_IDS)}`",
            buttons=kb
        )

    @client.on(events.CallbackQuery(pattern=b"^adm:refresh$"))
    async def cb_admin_refresh(event):
        await event.answer("🔄 Данные обновлены")
        await cb_admin_panel(event)

    @client.on(events.CallbackQuery(pattern=b"^adm:users$"))
    async def cb_admin_users(event):
        if not check_admin(event.sender_id):
            return await event.answer("❌ Доступ запрещен.", alert=True)
        users = db.get_users_list(25)
        lines = ["👥 <b>Последние пользователи:</b>\n"]
        for i, (uid, uname, banned, vids) in enumerate(users, 1):
            status = "⛔" if banned else "✅"
            star = " 💎" if is_premium_user(uid, uname or "") else ""
            admin_mark = " 🔧" if uid in ADMIN_IDS else (" 👑" if uid == OWNER_ID else "")
            lines.append(f"{status} {i}. {user_link(uid, uname)} — 🎬 {vids}{star}{admin_mark}")
        lines.append("\n💡 <i>Для полного списка введите команду /users</i>")
        kb = [[Button.inline("🔙 Назад", b"adm:panel")]]
        await event.edit("\n".join(lines), parse_mode="html", buttons=kb)

    @client.on(events.NewMessage(pattern=re.compile(r"^/users(?:@\w+)?(?:\s+.*)?$", re.IGNORECASE)))
    async def cmd_users(event):
        if not check_admin(event.sender_id):
            return await event.respond("❌ Недостаточно прав.")
        users = db.get_users_list(50)
        lines = ["👥 <b>Список последних 50 пользователей:</b>\n"]
        for i, (uid, uname, banned, vids) in enumerate(users, 1):
            status = "⛔" if banned else "✅"
            star = " 💎" if is_premium_user(uid, uname or "") else ""
            admin_mark = " 🔧" if uid in ADMIN_IDS else (" 👑" if uid == OWNER_ID else "")
            lines.append(f"{status} {i}. {user_link(uid, uname)} — 🎬 {vids}{star}{admin_mark}")
        await event.respond("\n".join(lines), parse_mode="html")

    @client.on(events.CallbackQuery(pattern=b"^adm:whitelist$"))
    async def cb_admin_whitelist(event):
        if not check_admin(event.sender_id):
            return await event.answer("❌ Доступ запрещен.", alert=True)
        lines = ["💎 <b>Белый список (доступ к файлам до 4 ГБ):</b>\n"]
        for uid in sorted(PREMIUM_USERS):
            lines.append(f"• ID: <code>{uid}</code>")
        for uname in sorted(PREMIUM_USERNAMES):
            lines.append(f"• Юзернейм: @{uname}")
        lines.append("\n💡 <i>Команды: /addpremium &lt;ID/@username&gt; и /delpremium</i>")
        kb = [[Button.inline("🔙 Назад", b"adm:panel")]]
        await event.edit("\n".join(lines), parse_mode="html", buttons=kb)

    @client.on(events.CallbackQuery(pattern=b"^adm:admins$"))
    async def cb_admin_admins(event):
        if not check_admin(event.sender_id):
            return await event.answer("❌ Доступ запрещен.", alert=True)
        lines = ["🔧 <b>Список администраторов:</b>\n"]
        lines.append(f"👑 Владелец: <code>{OWNER_ID}</code>\n")
        if not ADMIN_IDS:
            lines.append("📭 Дополнительных админов пока нет.")
        else:
            for uid in sorted(ADMIN_IDS):
                lines.append(f"• 🔧 {user_link(uid)} (<code>{uid}</code>)")
        lines.append("\n💡 <i>Команды: /addadmin &lt;ID/@username&gt; и /deladmin</i>")
        kb = [[Button.inline("🔙 Назад", b"adm:panel")]]
        await event.edit("\n".join(lines), parse_mode="html", buttons=kb)

    @client.on(events.NewMessage(pattern=re.compile(r"^/whitelist(?:@\w+)?(?:\s+.*)?$", re.IGNORECASE)))
    async def cmd_whitelist(event):
        if not check_admin(event.sender_id):
            return await event.respond("❌ Недостаточно прав.")
        lines = ["💎 <b>Белый список (лимит 4 ГБ):</b>\n"]
        for uid in sorted(PREMIUM_USERS):
            lines.append(f"• {user_link(uid)} — <code>{uid}</code>")
        for uname in sorted(PREMIUM_USERNAMES):
            lines.append(f"• @{uname}")
        await event.respond("\n".join(lines), parse_mode="html")

    @client.on(events.NewMessage(pattern=re.compile(r"^/addpremium(?:@\w+)?\s+(.+)$", re.IGNORECASE)))
    async def cmd_addpremium(event):
        if not check_admin(event.sender_id):
            return await event.respond("❌ Недостаточно прав.")
        arg = event.pattern_match.group(1).strip()
        uid, uname, err = await resolve_user(client, arg)
        if err:
            return await event.respond(err)

        PREMIUM_USERS.add(uid)
        if uname:
            PREMIUM_USERNAMES.add(uname)
        save_premium_list()
        term_log("💎 PREM ADD", f"Добавлен в whitelist: {uid} (@{uname})", Colors.GREEN)
        await event.respond(f"✅ Пользователь {user_link(uid, uname)} добавлен в белый список (4 ГБ).", parse_mode="html")

    @client.on(events.NewMessage(pattern=re.compile(r"^/delpremium(?:@\w+)?\s+(.+)$", re.IGNORECASE)))
    async def cmd_delpremium(event):
        if not check_admin(event.sender_id):
            return await event.respond("❌ Недостаточно прав.")
        arg = event.pattern_match.group(1).strip()
        uid, uname, err = await resolve_user(client, arg)
        if err and not uid:
            return await event.respond(err)

        PREMIUM_USERS.discard(uid)
        if uname:
            PREMIUM_USERNAMES.discard(uname)
        save_premium_list()
        term_log("🗑️ PREM DEL", f"Удален из whitelist: {uid}", Colors.YELLOW)
        await event.respond(f"🗑 Пользователь {user_link(uid, uname)} удален из белого списка.", parse_mode="html")

    @client.on(events.NewMessage(pattern=re.compile(r"^/ban(?:@\w+)?\s+(.+)$", re.IGNORECASE)))
    async def cmd_ban(event):
        if not check_admin(event.sender_id):
            return await event.respond("❌ Недостаточно прав.")
        arg = event.pattern_match.group(1).strip()
        uid, uname, err = await resolve_user(client, arg)
        if err:
            return await event.respond(err)

        if uid == OWNER_ID:
            return await event.respond("❌ Нельзя заблокировать владельца бота.")
        if uid in ADMIN_IDS and not check_owner(event.sender_id):
            return await event.respond("❌ Только владелец может банить администраторов.")

        db.set_ban(uid, True)
        term_log("⛔ BAN", f"Заблокирован пользователь {uid}", Colors.RED)
        await event.respond(f"⛔ Пользователь {user_link(uid, uname)} заблокирован.", parse_mode="html")

    @client.on(events.NewMessage(pattern=re.compile(r"^/unban(?:@\w+)?\s+(.+)$", re.IGNORECASE)))
    async def cmd_unban(event):
        if not check_admin(event.sender_id):
            return await event.respond("❌ Недостаточно прав.")
        arg = event.pattern_match.group(1).strip()
        uid, uname, err = await resolve_user(client, arg)
        if err and not uid:
            return await event.respond(err)

        db.set_ban(uid, False)
        term_log("✅ UNBAN", f"Разблокирован пользователь {uid}", Colors.GREEN)
        await event.respond(f"✅ Пользователь {user_link(uid, uname)} разблокирован.", parse_mode="html")

    @client.on(events.NewMessage(pattern=re.compile(r"^/broadcast(?:@\w+)?\s+(.+)", re.IGNORECASE)))
    async def cmd_broadcast(event):
        if not check_admin(event.sender_id):
            return await event.respond("❌ Недостаточно прав.")
        text = event.pattern_match.group(1)
        users = db.all_users()
        ok = 0
        status_msg = await event.respond(f"📣 Начинаю рассылку для {len(users)} пользователей...")
        term_log("📢 BROADCAST", f"Админ запустил рассылку...", Colors.CYAN)
        for uid in users:
            try:
                await client.send_message(uid, f"🔔 **Оповещение от администрации:**\n\n{text}")
                ok += 1
                await asyncio.sleep(0.3)
            except Exception:
                pass
        term_log("📢 BROADCAST", f"Рассылка завершена: доставлено {ok}/{len(users)}", Colors.GREEN)
        await status_msg.edit(f"✅ Рассылка завершена! Доставлено: `{ok}/{len(users)}` пользователям.")

    # ─────────────────────────────────────────
    # ПЕРЕКЛЮЧАТЕЛЬ ОЗВУЧКИ (ИНЛАЙН)
    # ─────────────────────────────────────────
    @client.on(events.CallbackQuery(pattern=b"^lang:"))
    async def on_switch_lang(event):
        data_str = event.data.decode("utf-8")
        parts = data_str.split(":")
        new_lang = parts[1]
        vid = parts[2]

        meta = video_meta.get(vid)
        if not meta:
            return await event.answer("⚠️ Сессия устарела. Отправьте ссылку повторно.", alert=True)

        meta["selected_lang"] = new_lang
        kb = make_video_keyboard(vid, current_lang=new_lang, is_playlist=False)

        if new_lang == "ru":
            lang_name = "🇷🇺 Дубляж"
        elif new_lang == "ya":
            lang_name = "🤖 Перевод Яндекс"
        else:
            lang_name = "🇬🇧 Оригинал"

        kind = "📱 Shorts" if meta.get("is_short") else "🎥 Видео"

        msg_text = f"🎥 **{meta['title']}**\n"
        if meta.get("translated_title"):
            msg_text += f"🇷🇺 *{meta['translated_title']}*\n"
        msg_text += (
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 Автор: {hashtag(meta['uploader'])}\n"
            f"⏱ Длительность: `{timedelta(seconds=meta['duration'])}`\n"
            f"📐 Макс. качество: `{meta['max_quality']}p`\n"
            f"🧬 Формат: `{kind}`\n"
            f"🔊 Выбрано: **{lang_name}**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👇 *Выберите качество для загрузки:*"
        )

        await event.edit(msg_text, buttons=kb)
        await event.answer(f"Выбрано: {lang_name}")

    @client.on(events.CallbackQuery(pattern=b"^pllang:"))
    async def on_switch_pl_lang(event):
        data_str = event.data.decode("utf-8")
        parts = data_str.split(":")
        new_lang = parts[1]
        pl_id = parts[2]

        meta = video_meta.get(pl_id)
        if not meta:
            return await event.answer("⚠️ Сессия плейлиста устарела.", alert=True)

        meta["selected_lang"] = new_lang
        kb = make_video_keyboard(pl_id, current_lang=new_lang, is_playlist=True)

        if new_lang == "ru":
            lang_name = "🇷🇺 Дубляж"
        elif new_lang == "ya":
            lang_name = "🤖 Перевод Яндекс"
        else:
            lang_name = "🇬🇧 Оригинал"

        await event.edit(
            f"📚 **{meta['title']}**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 Автор: {hashtag(meta.get('uploader', ''))}\n"
            f"🎞 Роликов: `{len(meta['ids'])}`\n"
            f"🔊 Выбранный режим: **{lang_name}**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👇 *Выберите качество для плейлиста:*",
            buttons=kb
        )
        await event.answer(f"Режим: {lang_name}")

    # ─────────────────────────────────────────
    # ОБРАБОТКА ССЫЛОК YOUTUBE
    # ─────────────────────────────────────────
    @client.on(events.NewMessage(
        func=lambda e: bool(e.text) and not e.text.startswith("/") and bool(extract_url(e.text))))
    async def on_link(event):
        if db.is_banned(event.sender_id):
            return await event.respond("❌ Ваш аккаунт заблокирован в боте.")
        db.register_user(event.sender_id, getattr(event.sender, "username", "") or "")
        url = extract_url(event.text)
        uid = event.sender_id

        term_log("🔗 URL", f"[{uid}] Получена ссылка: {url}", Colors.BLUE)

        if "list=" in url:
            msg = await event.respond("📚 **Обнаружен плейлист!** Сканирую...")
            try:
                opts = ytdlp_opts()
                opts["extract_flat"] = True
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                entries = info.get("entries", [])
                ids = [e["id"] for e in entries if e and e.get("id")]
                if not ids:
                    return await msg.edit("❌ Плейлист пуст или скрыт настройками приватности.")
                pl_id = info.get("id", f"pl_{random.getrandbits(32)}")
                pl_title = info.get("title") or "Плейлист YouTube"

                audio_info = detect_audio_tracks(info)
                selected_lang = "orig"

                video_meta[pl_id] = {
                    "title": pl_title,
                    "uploader": info.get("uploader", "Unknown"),
                    "is_playlist": True,
                    "ids": ids,
                    "audio_info": audio_info,
                    "selected_lang": selected_lang
                }
                kb = make_video_keyboard(pl_id, current_lang=selected_lang, is_playlist=True)
                await msg.edit(
                    f"📚 **{pl_title}**\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"👤 Автор: {hashtag(info.get('uploader', ''))}\n"
                    f"🎞 Видеороликов: `{len(ids)}`\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"👇 *Выберите качество для всех роликов:*",
                    buttons=kb
                )
            except Exception as e:
                term_log("❌ PLAYLIST", f"Ошибка анализа плейлиста: {e}", Colors.RED)
                await msg.edit(f"❌ Ошибка загрузки плейлиста:\n`{e}`")
            return

        msg = await event.respond("🔍 **Анализирую видео...**")
        try:
            opts = ytdlp_opts()
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)

            if info.get("is_live"):
                return await msg.edit("❌ Прямые эфиры не поддерживаются.")

            vid = info["id"]
            orig_title = info.get("title") or info.get("alt_title") or f"Ролик {vid}"
            uploader = info.get("uploader", "Unknown")
            duration = int(info.get("duration") or 0)
            is_short = is_shorts_url(url, info)

            ru_title = await translate_title_to_ru(orig_title)
            db.update_title_if_needed(vid, orig_title)

            tiers = get_available_tiers(info)
            max_tier = tiers[0] if tiers else 720
            audio_info = detect_audio_tracks(info)

            # Выбор языка
            if audio_info["has_official_dub"]:
                selected_lang = "ru"
            elif audio_info["needs_yandex_ai"]:
                selected_lang = "orig"
            else:
                selected_lang = "orig"

            term_log(
                "🎬 INFO",
                f"[{uid}] \"{orig_title[:35]}\" | {max_tier}p | RU={audio_info['has_ru']}, Dub={audio_info['has_official_dub']}, YaAI={audio_info['needs_yandex_ai']}",
                Colors.GREEN
            )

            video_meta[vid] = {
                "url": url, "title": orig_title, "translated_title": ru_title,
                "uploader": uploader, "duration": duration, "is_short": is_short,
                "max_quality": max_tier, "tiers": tiers,
                "audio_info": audio_info,
                "selected_lang": selected_lang
            }

            kb = make_video_keyboard(vid, current_lang=selected_lang, is_playlist=False)
            kind = "📱 Shorts" if is_short else "🎥 Видео"

            msg_text = f"🎥 **{orig_title}**\n"
            if ru_title:
                msg_text += f"🇷🇺 *{ru_title}*\n"
            msg_text += (
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"👤 Автор: {hashtag(uploader)}\n"
                f"⏱ Длительность: `{timedelta(seconds=duration)}`\n"
                f"📐 Макс. качество: `{max_tier}p`\n"
                f"🧬 Формат: `{kind}`\n"
            )
            if audio_info["has_official_dub"]:
                msg_text += "🔊 Озвучка: **🇷🇺 Официальный дубляж** *(доступен выбор)*\n"
            elif audio_info["needs_yandex_ai"]:
                msg_text += "🤖 Доступен: **Нейроперевод Яндекс AI**\n"

            msg_text += "━━━━━━━━━━━━━━━━━━━━\n👇 *Выберите качество для загрузки:*"

            await msg.edit(msg_text, buttons=kb)

        except Exception as e:
            term_log("❌ ANALYZE", f"[{uid}] Ошибка анализа: {e}", Colors.RED)
            await msg.edit(f"❌ Ошибка анализа видео:\n`{e}`")

    # ─────────────────────────────────────────
    # ОТМЕНА ОПЕРАЦИИ
    # ─────────────────────────────────────────
    @client.on(events.CallbackQuery(pattern=b"^cancel:"))
    async def on_cancel(event):
        data_str = event.data.decode("utf-8")
        task_id = data_str.split(":")[1]
        if task_id in cancel_tokens:
            cancel_tokens[task_id].cancel()
            term_log("🛑 CANCEL", f"Пользователь {event.sender_id} отменил задачу {task_id}", Colors.YELLOW)
            await event.answer("🛑 Загрузка прерывается...", alert=True)
        else:
            await event.answer("⚠️ Задача уже завершена или отменена.", alert=True)

    # ─────────────────────────────────────────
    # СКАЧИВАНИЕ И ОТПРАВКА
    # ─────────────────────────────────────────
    @client.on(events.CallbackQuery(pattern=b"^dl:"))
    async def on_download(event):
        uid = event.sender_id
        data_str = event.data.decode("utf-8")
        parts = data_str.split(":")
        quality, vid = parts[1], parts[2]
        lang = parts[3] if len(parts) > 3 else "orig"

        meta = video_meta.get(vid)
        if not meta:
            return await event.answer("⚠️ Сессия устарела. Отправьте ссылку повторно.", alert=True)

        await event.answer()
        task_id = f"{uid}_{vid}_{lang}"
        token = CancelToken()
        cancel_tokens[task_id] = token
        cancel_kb = [[Button.inline("❌ Отменить загрузку", f"cancel:{task_id}".encode())]]

        if lang == "ru":
            lang_label = "🇷🇺 Дубляж"
        elif lang == "ya":
            lang_label = "🤖 Яндекс AI"
        elif lang == "en":
            lang_label = "🇬🇧 Оригинал"
        else:
            lang_label = "Оригинальный звук"

        q_label = "MP3 🎵" if quality == "mp3" else f"{quality}p 🎬"
        msg = await event.reply(f"⏳ **Подготовка...**\nКачество: `{q_label}` | Звук: `{lang_label}`", buttons=cancel_kb)

        cache_data = db.get_cache(vid, quality, lang=lang)
        if cache_data:
            cached_file_id, cached_title = cache_data
            term_log("⚡ CACHE HIT", f"[{uid}] Видео {vid} [{quality}p_{lang.upper()}] отдано из кэша!", Colors.GREEN)
            await msg.edit(f"⚡ **Найдено в кэше! Отправка без задержки...**")
            caption_suffix = f" [{lang_label}]" if lang in ("ru", "en", "ya") else ""
            ru_title_cached = meta.get("translated_title")
            if ru_title_cached:
                caption = (
                    f"🎬 **{cached_title or meta['title']}**\n"
                    f"🇷🇺 *{ru_title_cached}*{caption_suffix}\n\n"
                    f"👤 {hashtag(meta['uploader'])}"
                )
            else:
                caption = f"🎬 **{cached_title or meta['title']}**{caption_suffix}\n\n👤 {hashtag(meta['uploader'])}"
            try:
                await client.send_file(uid, cached_file_id, caption=caption)
                await msg.delete()
                db.add_stats(uid, 0)
                cancel_tokens.pop(task_id, None)
                return
            except Exception as e:
                db.del_cache(vid, f"{quality}_{lang}" if lang in ("ru", "en", "ya") else quality)

        try:
            download_lang = "orig" if lang == "ya" else lang

            if quality == "mp3":
                final = await asyncio.to_thread(download_mp3, meta["url"], uid, vid, download_lang, token)
                thumb = None
            else:
                raw_src = await asyncio.to_thread(download_video, meta["url"], quality, uid, vid, download_lang, token)
                thumb_key = f"{vid}_{download_lang}" if download_lang in ("ru", "en") else str(vid)
                thumb = make_thumb(uid, thumb_key)
                final = os.path.join(DOWNLOAD_DIR, f"{uid}_{vid}_{lang}_fast.mp4")

                if lang == "ya":
                    await msg.edit("🤖 **Нейросеть Яндекса генерирует русскую озвучку...**", buttons=cancel_kb)
                    ya_voice = await fetch_yandex_voiceover(meta["url"], meta["duration"], token)
                    if ya_voice:
                        await msg.edit("⚡ **Сведение дорожек (Direct Copy)...**", buttons=cancel_kb)
                        merge_ok = await asyncio.to_thread(merge_yandex_audio, raw_src, ya_voice, final, token)
                        await rm(ya_voice)
                        await rm(raw_src)
                        if not merge_ok:
                            raise RuntimeError("Ошибка сведения звука Яндекса")
                    else:
                        term_log("⚠️ YANDEX AI", "Не удалось получить озвучку Яндекса, отправляю оригинал", Colors.YELLOW)
                        await asyncio.to_thread(process_video_direct, raw_src, final, token)
                        await rm(raw_src)
                else:
                    await asyncio.to_thread(process_video_direct, raw_src, final, token)
                    await rm(raw_src)

            size_mb = os.path.getsize(final) / (1024 * 1024)
            is_user_premium = (is_premium_user(uid, getattr(event.sender, "username", "") or "") and is_premium)
            max_mb = 3950 if is_user_premium else 1950

            if size_mb > max_mb:
                term_log("❌ SIZE LIMIT", f"[{uid}] Файл превышает лимит: {size_mb:.1f} МБ > {max_mb} МБ", Colors.RED)
                await msg.edit(f"❌ **Файл превышает допустимый лимит**\n📦 Размер: `{size_mb:.1f} МБ`\n🛡 Ваш лимит: `{max_mb} МБ`")
                await rm(final)
                if thumb:
                    await rm(thumb)
                return

            async with upload_semaphore:
                if token.cancelled:
                    raise ValueError("CANCELLED")

                contour = "💎 Premium 4GB" if (size_mb > 1950 and user_client) else "📦 Standard 2GB"
                term_log("🚀 UPLOAD", f"[{uid}] Загрузка в Telegram [{contour}] ({size_mb:.1f} МБ)...", Colors.CYAN)
                await msg.edit(f"⚙️ **Файл готов!**\n📤 Загрузка в Telegram [{contour}]...", buttons=cancel_kb)

                t0 = time.time()
                last_edit = [time.time()]
                last_text = [""]

                async def on_progress(cur, total):
                    if token.cancelled:
                        raise ValueError("CANCELLED")
                    now = time.time()
                    if now - last_edit[0] < 3.5:
                        return
                    pct = cur / total * 100
                    speed = cur / max(now - t0, 0.1)
                    eta = (total - cur) / speed if speed > 0 else 0
                    text = (
                        f"🚀 **Выгрузка в Telegram** [{contour}]\n"
                        f"🔊 Звук: **{lang_label}**\n\n"
                        f"📊 {progress_bar(pct)} **{pct:.1f}%**\n"
                        f"⚡ Скорость: **{speed / 1024 / 1024:.1f} МБ/с**\n"
                        f"⏳ Осталось: **{timedelta(seconds=int(eta))}**"
                    )
                    if text == last_text[0]:
                        return
                    last_text[0] = text
                    last_edit[0] = now
                    try:
                        await msg.edit(text, buttons=cancel_kb)
                    except Exception:
                        pass

                sender = user_client if (size_mb > 1950 and is_premium and user_client) else client
                uploaded = await upload_file(sender, final, on_progress if sender == client else None, token)

                if token.cancelled:
                    raise ValueError("CANCELLED")

                await msg.edit("⚡ **Финализация и отправка...**")
                title_clean = meta.get("title") or f"YouTube Video {vid}"
                translated_title = meta.get("translated_title")
                caption_suffix = f" [{lang_label}]" if lang in ("ru", "en", "ya") else ""
                if translated_title:
                    caption = (
                        f"🎬 **{title_clean}**\n"
                        f"🇷🇺 *{translated_title}*{caption_suffix}\n\n"
                        f"👤 {hashtag(meta['uploader'])}"
                    )
                else:
                    caption = f"🎬 **{title_clean}**{caption_suffix}\n\n👤 {hashtag(meta['uploader'])}"
                attrs = []
                if quality == "mp3":
                    audio_title = translated_title or title_clean
                    attrs.append(DocumentAttributeAudio(duration=meta["duration"], title=audio_title))
                else:
                    info = probe(final)
                    attrs.append(DocumentAttributeVideo(
                        duration=info["duration"] or meta["duration"],
                        w=info["width"] or 1280,
                        h=info["height"] or 720,
                        supports_streaming=True
                    ))

                if sender == user_client and uid == owner_id:
                    target_peer = bot_username or (await bot.get_me()).id
                else:
                    target_peer = uid

                sent = await sender.send_file(
                    target_peer, uploaded, caption=caption, thumb=thumb,
                    attributes=attrs, supports_streaming=True)

                if sender == client and sent and sent.document:
                    try:
                        packed_id = utils.pack_bot_file_id(sent.document)
                        db.set_cache(vid, quality, lang, packed_id, title_clean)
                        term_log("💾 CACHE SAVED", f"[{uid}] Закэшировано: {vid} [{quality}_{lang}]", Colors.GREEN)
                    except Exception as e:
                        term_log("⚠️ CACHE ERROR", f"Ошибка кэширования: {e}", Colors.YELLOW)

            db.add_stats(uid, size_mb)
            await rm(final)
            if thumb:
                await rm(thumb)
            await msg.delete()
            term_log("✅ DONE", f"[{uid}] Видео {vid} доставлено ({size_mb:.1f} МБ)", Colors.GREEN)

        except ValueError as e:
            if str(e) == "CANCELLED":
                term_log("🛑 CANCELLED", f"[{uid}] Загрузка {vid} отменена", Colors.YELLOW)
                await msg.edit("❌ **Операция успешно отменена пользователем.**")
                cleanup_disk_for_video(f"{uid}_{vid}")
            else:
                raise e
        except Exception as e:
            term_log("❌ ERROR", f"[{uid}] Ошибка скачивания {vid}: {e}", Colors.RED)
            await msg.edit(f"❌ **Ошибка при загрузке:**\n`{str(e)[:220]}`")
            cleanup_disk_for_video(f"{uid}_{vid}")
        finally:
            cancel_tokens.pop(task_id, None)

    # ─────────────────────────────────────────
    # ОБРАБОТКА ПЛЕЙЛИСТА
    # ─────────────────────────────────────────
    @client.on(events.CallbackQuery(pattern=b"^pl:"))
    async def on_playlist(event):
        uid = event.sender_id
        data_str = event.data.decode("utf-8")
        parts = data_str.split(":")
        batch, quality, pl_id = int(parts[1]), parts[2], parts[3]
        lang = parts[4] if len(parts) > 4 else "orig"

        meta = video_meta.get(pl_id)
        if not meta or not meta.get("is_playlist"):
            return await event.answer("⚠️ Сессия плейлиста устарела.", alert=True)

        ids = meta["ids"]
        total = len(ids)
        task_id = f"{uid}_{pl_id}_{lang}"
        token = CancelToken()
        cancel_tokens[task_id] = token
        cancel_kb = [[Button.inline("❌ Отменить весь плейлист", f"cancel:{task_id}".encode())]]

        mode_name = "MP3 (Аудио)" if quality == "mp3" else f"{quality}p (Видео)"
        term_log("📚 PLAYLIST START", f"[{uid}] Старт плейлиста {pl_id}: {total} файлов ({mode_name})", Colors.MAGENTA)
        await event.edit(
            f"📚 **{meta['title']}**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🎞 Всего роликов: `{total}` | Пачки по `{batch}`\n"
            f"📐 Режим: `{mode_name}`\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"⏳ *Обработка запущена...*",
            buttons=cancel_kb
        )

        for i in range(0, total, batch):
            if token.cancelled:
                break
            chunk = ids[i:i + batch]
            tasks = [
                process_playlist_item(vid, quality, uid, task_id, token, lang=lang, delay=j * 1.5)
                for j, vid in enumerate(chunk)
            ]
            await asyncio.gather(*tasks)

        if token.cancelled:
            term_log("🛑 PLAYLIST CANCEL", f"[{uid}] Плейлист {pl_id} отменен", Colors.YELLOW)
            await client.send_message(uid, "❌ **Обработка плейлиста отменена.**")
        else:
            term_log("✅ PLAYLIST DONE", f"[{uid}] Плейлист {pl_id} полностью доставлен", Colors.GREEN)
            await client.send_message(uid, f"✅ **Плейлист полностью обработан!**\n🎞 Доставлено `{total}` файлов.")
        cancel_tokens.pop(task_id, None)

    async def process_playlist_item(vid: str, quality: str, uid: int, pl_task_id: str, token: CancelToken, lang: str = "orig", delay: float = 0):
        if token.cancelled:
            return
        if delay:
            await asyncio.sleep(delay)
        if token.cancelled:
            return

        url = f"https://www.youtube.com/watch?v={vid}"
        try:
            opts = ytdlp_opts()
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
            title = info.get("title") or info.get("alt_title") or f"Ролик {vid}"
            uploader = info.get("uploader", "Unknown")
            duration = int(info.get("duration") or 0)
        except Exception as e:
            term_log("❌ PL ITEM", f"[{uid}] Ошибка метаданных {vid}: {e}", Colors.RED)
            return

        ru_title = await translate_title_to_ru(title)
        if ru_title:
            caption = f"🎬 **{title}**\n🇷🇺 *{ru_title}*\n\n👤 {hashtag(uploader)}"
        else:
            caption = f"🎬 **{title}**\n\n👤 {hashtag(uploader)}"
        audio_title = ru_title or title

        cache_data = db.get_cache(vid, quality, lang=lang)
        if cache_data:
            cached_file_id, cached_title = cache_data
            try:
                await client.send_file(uid, cached_file_id, caption=caption)
                term_log("⚡ PL CACHE", f"[{uid}] Ролик плейлиста {vid} отправлен из кэша", Colors.GREEN)
                return
            except Exception:
                db.del_cache(vid, f"{quality}_{lang}" if lang in ("ru", "en", "ya") else quality)

        cancel_kb = [[Button.inline("❌ Отменить плейлист", f"cancel:{pl_task_id}".encode())]]
        status = await client.send_message(uid, f"📥 **Обрабатывается:**\n`{title[:50]}`", buttons=cancel_kb)

        try:
            if quality == "mp3":
                final = await asyncio.to_thread(download_mp3, url, uid, vid, lang, token)
                thumb = None
                attrs = [DocumentAttributeAudio(duration=duration, title=audio_title, performer=uploader)]
            else:
                raw_src = await asyncio.to_thread(download_video, url, quality, uid, vid, lang, token)
                thumb_key = f"{vid}_{lang}" if lang in ("ru", "en") else str(vid)
                thumb = make_thumb(uid, thumb_key)
                final = os.path.join(DOWNLOAD_DIR, f"{uid}_{vid}_{lang}_fast.mp4")
                await asyncio.to_thread(process_video_direct, raw_src, final, token)
                await rm(raw_src)
                info_p = probe(final)
                attrs = [DocumentAttributeVideo(
                    duration=info_p["duration"] or duration,
                    w=info_p["width"] or 1280,
                    h=info_p["height"] or 720,
                    supports_streaming=True)]

            size_mb = os.path.getsize(final) / (1024 * 1024)

            async with upload_semaphore:
                if token.cancelled:
                    raise ValueError("CANCELLED")
                max_mb = 3950 if (is_premium_user(uid) and is_premium) else 1950
                if size_mb > max_mb:
                    await status.edit(f"❌ `{title[:35]}`: {size_mb:.0f} МБ > лимита")
                    await rm(final)
                    if thumb:
                        await rm(thumb)
                    return

                sender = user_client if (size_mb > 1950 and is_premium and user_client) else client
                uploaded = await upload_file(sender, final, cancel_token=token)
                if token.cancelled:
                    raise ValueError("CANCELLED")

                if sender == user_client and uid == owner_id:
                    target_peer = bot_username or (await bot.get_me()).id
                else:
                    target_peer = uid

                sent = await sender.send_file(
                    target_peer, uploaded, caption=caption, thumb=thumb,
                    attributes=attrs, supports_streaming=True)
                if sender == client and sent and sent.document:
                    try:
                        db.set_cache(vid, quality, lang, utils.pack_bot_file_id(sent.document), title)
                    except Exception:
                        pass

            db.add_stats(uid, size_mb)
            await rm(final)
            if thumb:
                await rm(thumb)
            await status.delete()
        except ValueError as e:
            if str(e) == "CANCELLED":
                await status.edit(f"❌ `{title[:35]}`: Отменено.")
                cleanup_disk_for_video(f"{uid}_{vid}")
                return
            raise e
        except Exception as e:
            term_log("❌ PL ERROR", f"[{uid}] Ошибка скачивания {vid}: {e}", Colors.RED)
            await status.edit(f"❌ Ошибка `{title[:30]}`: `{str(e)[:90]}`")
            cleanup_disk_for_video(f"{uid}_{vid}")

# ═══════════════════════════════════════════════
# КОНСОЛЬНОЕ МЕНЮ TUI
# ═══════════════════════════════════════════════
COOKIES = {"1": "chrome", "2": "firefox", "3": "edge", "4": "brave", "0": ""}

def _clear():
    os.system('cls' if os.name == 'nt' else 'clear')

def _pause():
    input(f"\n  {Colors.DIM}Нажмите Enter для возврата в меню...{Colors.RESET}")

def _wait_key(timeout: int = 5) -> bool:
    try:
        import msvcrt
        end = time.time() + timeout
        while time.time() < end:
            if msvcrt.kbhit():
                msvcrt.getch()
                return True
            time.sleep(0.1)
        return False
    except Exception:
        time.sleep(timeout)
        return False

def run_menu() -> bool:
    global USE_PROXY, DEFAULT_BATCH, BROWSER_COOKIES
    global USE_USERBOT, QUICK_START, OWNER_ID

    while True:
        _clear()
        log_banner()
        has_session = os.path.exists("user_session.session")
        ub_state = f"{Colors.GREEN}ВКЛЮЧЕН{Colors.RESET}" if USE_USERBOT else f"{Colors.RED}ВЫКЛЮЧЕН{Colors.RESET}"
        ub_note = f" {Colors.GREEN}(сессия есть ✅){Colors.RESET}" if (USE_USERBOT and has_session) else \
                  (f" {Colors.YELLOW}(будет запрошена при старте){Colors.RESET}" if USE_USERBOT else "")
        admin_state = f"{Colors.GREEN}ID {OWNER_ID}{Colors.RESET}" if OWNER_ID else f"{Colors.RED}НЕ ЗАДАН ⚠️{Colors.RESET}"
        admins_count = len(ADMIN_IDS)

        cprint("  🎛️  ГЛАВНОЕ МЕНЮ УПРАВЛЕНИЯ\n", Colors.CYAN, bold=True)
        cprint(f"  {Colors.BOLD}[1]{Colors.RESET} ▶️  ЗАПУСТИТЬ БОТА", Colors.WHITE, bold=True)
        print(f"  {Colors.BOLD}[2]{Colors.RESET} 💎 Premium-юзербот (4 ГБ):     [{ub_state}]{ub_note}")
        print(f"  {Colors.BOLD}[3]{Colors.RESET} 🚀 Видеодвижок:                [{Colors.GREEN}Direct Copy (0% CPU/GPU){Colors.RESET}]")
        print(f"  {Colors.BOLD}[4]{Colors.RESET} 🌐 SOCKS5 Прокси:              [{'ВКЛЮЧЕН 🟢' if USE_PROXY else 'ВЫКЛЮЧЕН 🔴'}]")
        print(f"  {Colors.BOLD}[5]{Colors.RESET} 📦 Пачка в плейлисте:          [по {Colors.MAGENTA}{DEFAULT_BATCH}{Colors.RESET} видео]")

        def _cookie_file_status(path: str) -> Optional[str]:
            if not os.path.exists(path):
                return None
            age_h = (time.time() - os.path.getmtime(path)) / 3600
            if age_h <= COOKIE_MAX_AGE_HOURS:
                return f"{Colors.GREEN}{path} 🟢 (свежие, {age_h:.1f}ч){Colors.RESET}"
            return f"{Colors.YELLOW}{path} ⚠️ устарели ({age_h:.1f}ч > {COOKIE_MAX_AGE_HOURS:.0f}ч, используется браузер){Colors.RESET}"

        cookie_status = (
            _cookie_file_status("www.youtube.com_cookies.txt")
            or _cookie_file_status("cookies.txt")
            or (COOKIE_FILE and _cookie_file_status(COOKIE_FILE))
            or (f"{Colors.CYAN}браузер: {BROWSER_COOKIES}{Colors.RESET}" if BROWSER_COOKIES else f"{Colors.RED}не заданы{Colors.RESET}")
        )

        print(f"  {Colors.BOLD}[6]{Colors.RESET} 🍪 YouTube Cookies:            [{cookie_status}]")
        print(f"  {Colors.BOLD}[7]{Colors.RESET} ⚡ Быстрый старт (без меню):   [{'ВКЛЮЧЕН' if QUICK_START else 'ВЫКЛЮЧЕН'}]")
        print(f"  {Colors.BOLD}[8]{Colors.RESET} 🗑️  Сбросить сессию юзербота")
        print(f"  {Colors.BOLD}[9]{Colors.RESET} 👑 ID Владельца:               [{admin_state}]")
        print(f"  {Colors.BOLD}[A]{Colors.RESET} 🔧 Дополнительные админы:      [{Colors.CYAN}{admins_count} чел.{Colors.RESET}]")
        print(f"  {Colors.BOLD}[0]{Colors.RESET} ❌ Выход из программы")
        print(f"{Colors.CYAN}{'═' * 66}{Colors.RESET}")
        choice = input(f"  👉 {Colors.BOLD}Выберите действие (0-9, A):{Colors.RESET} ").strip().upper()

        if choice == "1":
            return True
        elif choice == "2":
            USE_USERBOT = not USE_USERBOT
            update_env("USE_USERBOT", str(USE_USERBOT).lower())
            _pause()
        elif choice == "3":
            print(f"\n  {Colors.GREEN}Используется чистый Direct Copy. Видеокарта не задействуется.{Colors.RESET}")
            _pause()
        elif choice == "4":
            USE_PROXY = not USE_PROXY
            update_env("USE_PROXY", str(USE_PROXY).lower())
            _pause()
        elif choice == "5":
            n = input("\n  Количество одновременных загрузок в пачке: ").strip()
            if n.isdigit() and int(n) > 0:
                DEFAULT_BATCH = int(n)
                update_env("DEFAULT_BATCH_SIZE", str(DEFAULT_BATCH))
            _pause()
        elif choice == "6":
            print("\n  1 - Chrome | 2 - Firefox | 3 - Edge | 4 - Brave | 0 - Выключить")
            c = input("  Выберите браузер: ").strip()
            if c in COOKIES:
                BROWSER_COOKIES = COOKIES[c]
                update_env("BROWSER_COOKIES", BROWSER_COOKIES)
            _pause()
        elif choice == "7":
            QUICK_START = not QUICK_START
            update_env("QUICK_START", str(QUICK_START).lower())
            _pause()
        elif choice == "8":
            for f in ("user_session.session", "user_session.session-journal"):
                if os.path.exists(f):
                    try:
                        os.remove(f)
                    except Exception:
                        pass
            cprint("  ✅ Сессия юзербота удалена.", Colors.GREEN)
            _pause()
        elif choice == "9":
            v = input("\n  Введите Telegram ID владельца (число): ").strip()
            if v.isdigit() and int(v) > 0:
                OWNER_ID = int(v)
                update_env("OWNER_ID", str(OWNER_ID))
            _pause()
        elif choice == "A":
            print(f"\n  {Colors.CYAN}Список назначенных админов:{Colors.RESET}")
            for uid in sorted(ADMIN_IDS):
                print(f"    • ID: {uid}")
            print(f"\n  Управлять админами можно через бота командами:")
            print(f"  /addadmin <ID/@username> и /deladmin <ID/@username>")
            _pause()
        elif choice == "0":
            return False

# ═══════════════════════════════════════════════
# ФОНОВОЕ ОБСЛУЖИВАНИЕ: cookies, версия yt-dlp
# ═══════════════════════════════════════════════
TEST_VIDEO_URL = "https://www.youtube.com/watch?v=jNQXAC9IVRw"  # первое видео на YouTube, всегда доступно

def check_ytdlp_outdated() -> Optional[str]:
    """Сверяет установленную версию yt-dlp с последней на PyPI.
    Не обновляет автоматически (обновление всё равно не подхватится без
    перезапуска процесса) — просто предупреждает, если версия устарела."""
    try:
        current = getattr(yt_dlp.version, "__version__", None) or "unknown"
        req = urllib.request.Request(
            "https://pypi.org/pypi/yt-dlp/json",
            headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        latest = data.get("info", {}).get("version")
        if latest and current != "unknown" and latest != current:
            return f"⚠️ Установлена версия yt-dlp {current}, на PyPI уже {latest}.\nОбновление: `pip install -U yt-dlp` и перезапуск бота."
    except Exception as e:
        term_log("⚠️ YT-DLP CHECK", f"Не удалось проверить обновления: {e}", Colors.YELLOW)
    return None

def check_cookies_broken() -> Optional[str]:
    """Пробует получить метаданные тестового видео с текущими cookies/опциями.
    Если YouTube просит авторизацию — куки протухли/не подключены."""
    try:
        opts = ytdlp_opts()
        opts["skip_download"] = True
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.extract_info(TEST_VIDEO_URL, download=False)
        return None
    except Exception as e:
        msg = str(e)
        if any(s in msg for s in ("Sign in", "confirm you're not a bot", "cookies", "age", "private")):
            cookie_opt = get_cookie_opts()
            source = cookie_opt.get("cookiefile") or (f"браузер: {cookie_opt.get('cookiesfrombrowser')}" if cookie_opt.get("cookiesfrombrowser") else "не заданы")
            return (
                f"🍪 Похоже, куки YouTube не работают (источник: `{source}`).\n"
                f"Обнови файл с куками или зайди в YouTube в браузере, указанном в BROWSER_COOKIES.\n"
                f"Ошибка: `{msg[:150]}`"
            )
        return None

async def maintenance_loop():
    """Раз в COOKIE_CHECK_INTERVAL_HOURS часов проверяет куки и версию yt-dlp,
    шлёт владельцу сообщение в Telegram, если что-то сломалось/устарело."""
    cookie_interval = float(_env("COOKIE_CHECK_INTERVAL_HOURS", "6"))
    ytdlp_interval = float(_env("YTDLP_CHECK_INTERVAL_HOURS", "24"))
    last_ytdlp_check = 0.0

    while True:
        try:
            cookie_issue = await asyncio.to_thread(check_cookies_broken)
            if cookie_issue and owner_id:
                term_log("⚠️ COOKIES", "Обнаружена проблема с cookies, уведомляю владельца", Colors.YELLOW)
                try:
                    await bot.send_message(owner_id, cookie_issue, parse_mode="markdown")
                except Exception:
                    pass

            now = time.time()
            if now - last_ytdlp_check >= ytdlp_interval * 3600:
                last_ytdlp_check = now
                update_issue = await asyncio.to_thread(check_ytdlp_outdated)
                if update_issue and owner_id:
                    try:
                        await bot.send_message(owner_id, update_issue, parse_mode="markdown")
                    except Exception:
                        pass
        except Exception as e:
            term_log("⚠️ MAINTENANCE", f"Ошибка фоновой проверки: {e}", Colors.YELLOW)

        await asyncio.sleep(cookie_interval * 3600)

# ═══════════════════════════════════════════════
# СТАРТ СИСТЕМЫ
# ═══════════════════════════════════════════════
async def start_bot():
    global bot, user_client, is_premium, bot_username, owner_id, OWNER_ID
    owner_id = OWNER_ID
    proxy = get_telethon_proxy()

    removed, freed_mb = cleanup_download_dir_on_boot()
    if removed:
        term_log("🧹 CLEANUP", f"Удалено {removed} огрызков файлов из {DOWNLOAD_DIR} (освобождено {freed_mb:.1f} МБ)", Colors.CYAN)

    term_log("🚀 INIT", "Инициализация клиента Telegram Bot...", Colors.CYAN)
    bot = TelegramClient("bot_session", API_ID, API_HASH, proxy=proxy)
    await bot.start(bot_token=BOT_TOKEN)
    me = await bot.get_me()
    bot_username = me.username
    term_log("🤖 BOT", f"Бот авторизован: @{bot_username} (ID: {me.id})", Colors.GREEN)

    if USE_USERBOT:
        term_log("💎 USERBOT", "Подключение сессии юзербота (4 ГБ)...", Colors.CYAN)
        user_client = TelegramClient("user_session", API_ID, API_HASH, proxy=proxy)
        await user_client.start()
        ume = await user_client.get_me()
        if owner_id == 0:
            owner_id = ume.id
            OWNER_ID = ume.id
            update_env("OWNER_ID", str(OWNER_ID))
        is_premium = getattr(ume, "premium", False)
        PREMIUM_USERS.add(owner_id)
        term_log(
            "💎 USERBOT",
            f"Юзербот: {ume.first_name} | Telegram Premium: {'Да (Лимит 4 ГБ) 💎' if is_premium else 'Нет (2 ГБ)'}",
            Colors.GREEN if is_premium else Colors.YELLOW
        )
    else:
        term_log("📦 STANDALONE", "Режим без юзербота. Лимит файлов: 2 ГБ.", Colors.YELLOW)

    try:
        ver = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, check=True)
        first_line = ver.stdout.splitlines()[0] if ver.stdout else "FFmpeg OK"
        term_log("🎥 FFMPEG", f"{first_line} | Движок: Direct Copy", Colors.GREEN)
    except Exception:
        term_log("⛔ CRITICAL", "FFmpeg не обнаружен в PATH! Проверьте установку.", Colors.RED)
        sys.exit(1)

    setup_handlers(bot)
    asyncio.create_task(maintenance_loop())
    term_log("🟢 READY", "Система готова к приёму ссылок и команд. Ожидание сообщений...", Colors.GREEN)
    await bot.run_until_disconnected()

# ═══════════════════════════════════════════════
# ТОЧКА ВХОДА
# ═══════════════════════════════════════════════
if __name__ == "__main__":
    force_menu = any(a in ("menu", "--menu", "-m", "config", "--config") for a in sys.argv[1:])
    if QUICK_START and not force_menu:
        log_banner()
        cprint("  ⚡ БЫСТРЫЙ СТАРТ — запуск через 5 секунд...", Colors.YELLOW, bold=True)
        cprint("  (нажмите любую клавишу для открытия настроек)", Colors.DIM)
        print("═" * 66)
        if _wait_key(5):
            if not run_menu():
                sys.exit(0)
    else:
        if not run_menu():
            sys.exit(0)

    try:
        asyncio.run(start_bot())
    except KeyboardInterrupt:
        db.close()
        cprint("\n  🛑 Бот корректно остановлен пользователем.", Colors.YELLOW)
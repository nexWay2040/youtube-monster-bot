# -*- coding: utf-8 -*-
"""
███╗   ███╗ ██████╗ ███╗   ██╗███████╗████████╗███████╗██████╗ 
████╗ ████║██╔═══██╗████╗  ██║██╔════╝╚══██╔══╝██╔════╝██╔══██╗
██╔████╔██║██║   ██║██╔██╗ ██║███████╗   ██║   █████╗  ██████╔╝
██║╚██╔╝██║██║   ██║██║╚██╗██║╚════██║   ██║   ██╔══╝  ██╔══██╗
██║ ╚═╝ ██║╚██████╔╝██║ ╚████║███████║   ██║   ███████╗██║  ██║
╚═╝     ╚═╝ ╚═════╝ ╚═╝  ╚═══╝╚══════╝   ╚═╝   ╚══════╝╚═╝  ╚═╝
       ██████╗  ██████╗ ████████╗
       ██╔══██╗██╔═══██╗╚══██╔══╝
       ██████╔╝██║   ██║   ██║   
       ██╔══██╗██║   ██║   ██║   
       ██████╔╝╚██████╔╝   ██║   
       ╚═════╝  ╚═════╝    ╚═╝   
YouTube Monster Bot — Ultimate Edition
Telethon + yt-dlp + FFmpeg (AMD RX 6600 h264_amf) + SQLite3 + Deep Audio Detection
"""

import os
import re
import sys
import json
import html
import math
import random
import asyncio
import logging
import time
import subprocess
import shutil
import sqlite3
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

# ─────────────────────────────────────────────
# ЦВЕТА И ТЕРМИНАЛЬНЫЕ ЛОГИ
# ─────────────────────────────────────────────
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
  ⚡ Telethon + yt-dlp + FFmpeg (h264_amf) | AMD RX 6600
  🛡️ Ultra Engine | 4GB Premium Contour | Deep Multi-Audio Extractor{Colors.RESET}
"""
    print(banner)

def get_now() -> str:
    return datetime.now().strftime("%H:%M:%S")

def term_log(tag: str, msg: str, color: str = Colors.WHITE):
    print(f"{Colors.DIM}[{get_now()}]{Colors.RESET} {color}{Colors.BOLD}{tag:<16}{Colors.RESET} {msg}")

# ─────────────────────────────────────────────
# КОНФИГУРАЦИЯ (.env)
# ─────────────────────────────────────────────
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
VIDEO_ENCODER = _env("VIDEO_ENCODER", "h264_amf")
BROWSER_COOKIES = _env("BROWSER_COOKIES", "")
USE_PROXY = _env("USE_PROXY", "false").lower() == "true"
PROXY_HOST = _env("PROXY_HOST", "127.0.0.1")
PROXY_PORT = int(_env("PROXY_PORT", "10808"))

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

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.FileHandler("bot.log", encoding="utf-8")],
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
        """)
        self.conn.commit()
        self._sync_admins()

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

    def get_cache(self, vid: str, quality: str, lang: str = "orig") -> Optional[Tuple[str, str]]:
        if lang in ("ru", "en"):
            q_key = f"{quality}_{lang}"
            self.c.execute("SELECT file_id, title FROM cache WHERE video_id=? AND quality=?", (vid, q_key))
            row = self.c.fetchone()
            if row and row[0]:
                return row[0], row[1] or ""
            if lang == "ru":
                self.c.execute("SELECT file_id, title FROM cache WHERE video_id=? AND quality=?", (vid, str(quality)))
                row = self.c.fetchone()
                if row and row[0]:
                    return row[0], row[1] or ""
        else:
            self.c.execute("SELECT file_id, title FROM cache WHERE video_id=? AND quality=?", (vid, str(quality)))
            row = self.c.fetchone()
            if row and row[0]:
                return row[0], row[1] or ""
            self.c.execute("SELECT file_id, title FROM cache WHERE video_id=? AND quality LIKE ?", (vid, f"{quality}_%"))
            row = self.c.fetchone()
            if row and row[0]:
                return row[0], row[1] or ""
        return None

    def set_cache(self, vid: str, quality: str, lang: str, file_id: str, title: str = ""):
        if lang in ("ru", "en"):
            q_key = f"{quality}_{lang}"
        else:
            q_key = str(quality)

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
        self.c.execute("UPDATE cache SET title=? WHERE video_id=? AND (title IS NULL OR title='' OR title='Без названия')", (title, vid))
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
            "WHERE title LIKE ? OR video_id LIKE ? ORDER BY created_at DESC LIMIT ?",
            (f"%{query}%", f"%{query}%", limit))
        return self.c.fetchall()

    def get_cache_page(self, page: int = 1, page_size: int = 5) -> Tuple[list, int]:
        self.c.execute("SELECT COUNT(*) FROM cache")
        total = self.c.fetchone()[0]
        offset = (page - 1) * page_size
        self.c.execute(
            "SELECT video_id, quality, title, created_at, file_id FROM cache "
            "ORDER BY created_at DESC LIMIT ? OFFSET ?", (page_size, offset))
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
# УТИЛИТЫ И ПРОВЕРКА ПОЛЬЗОВАТЕЛЕЙ
# ─────────────────────────────────────────────
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

# ─────────────────────────────────────────────
# УГЛУБЛЁННОЕ РАСПОЗНАВАНИЕ ДУБЛЯЖЕЙ И AI-ПЕРЕВОДА
# ─────────────────────────────────────────────
def detect_audio_tracks(info: dict) -> Dict[str, any]:
    """
    Глубокое сканирование ВСЕХ форматов видео (DASH, HLS m3u8, комбинированные).
    Распознает официальный дубляж, альтернативные дорожки и AI-автодубляж YouTube.
    """
    formats = info.get("formats", []) or []
    
    languages_found = set()
    has_ru = False
    has_en = False
    has_alternate_tracks = False

    # 1. Проверяем все форматы со звуком (включая HLS потоки 91-96 и m3u8)
    for f in formats:
        # Проверяем, есть ли аудио в этом формате
        acodec = str(f.get("acodec") or "").lower()
        if acodec in ("none", "") and f.get("vcodec") != "none":
            continue

        lang = str(f.get("language") or "").lower()
        note = str(f.get("format_note") or "").lower()
        fid = str(f.get("format_id") or "").lower()
        track_id = str(f.get("audio_track_id") or "").lower()
        format_str = str(f.get("format") or "").lower()

        # Маркеры дубляжа / автодубляжа
        is_dub = any(k in note for k in ("dub", "auto-dub", "дубл", "alternate", "descriptive"))
        is_alt_id = bool(re.search(r'^\d+-\d+$', fid))

        if is_dub or is_alt_id:
            has_alternate_tracks = True

        # Проверка на русский язык
        is_russian = (
            lang.startswith("ru") or 
            any(k in note for k in ("russian", "русск", "ru-")) or
            any(k in track_id for k in ("ru.", ".ru", "russian")) or
            any(k in format_str for k in ("ru", "russian", "русск"))
        )

        # Проверка на английский язык
        is_english = (
            lang.startswith("en") or 
            any(k in note for k in ("english", "original", "en-")) or
            any(k in track_id for k in ("en.", ".en", "english", "original")) or
            any(k in format_str for k in ("en", "english"))
        )

        if is_russian:
            has_ru = True
            languages_found.add("ru")
        elif is_english:
            has_en = True
            languages_found.add("en")
        elif lang and len(lang) >= 2 and lang != "none":
            languages_found.add(lang[:2])

    # 2. Также смотрим метаданные субтитров/автопереводов
    subs = info.get("subtitles") or {}
    auto_subs = info.get("automatic_captions") or {}
    if "ru" in subs or "ru" in auto_subs:
        pass  # информативно, но опираемся на видеопотоки

    # Видео считается мультиязычным, ТОЛЬКО если найден русский дубляж вместе с оригиналом,
    # либо найдено более одного языка, либо есть явные маркеры альтернативных аудиопотоков
    is_multi = (has_ru and has_en) or len(languages_found) > 1 or (has_ru and has_alternate_tracks)

    return {
        "is_multiaudio": is_multi,
        "has_ru": has_ru,
        "has_en": has_en,
        "languages": list(languages_found)
    }

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

# ─────────────────────────────────────────────
# FFPROBE И FFMPEG
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

BITRATES = {
    "1080": {"target": "4500k", "max": "7000k", "buf": "14000k"},
    "720":  {"target": "2800k", "max": "4500k", "buf": "9000k"},
    "480":  {"target": "1200k", "max": "2000k", "buf": "4000k"},
    "360":  {"target": "700k",  "max": "1200k", "buf": "2400k"},
}

def ffmpeg_transcode(src: str, dst: str, quality: str, encoder: str, fps: int = 30, vf: Optional[str] = None) -> List[str]:
    cfg_key = quality if quality in BITRATES else "720"
    cfg = BITRATES.get(cfg_key, BITRATES["720"])
    gop = fps * 2
    cmd = ["ffmpeg", "-y"]
    if "amf" in encoder or "nvenc" in encoder:
        cmd += ["-hwaccel", "d3d11va"]
    cmd += ["-i", src]
    if vf:
        cmd += ["-vf", vf]
    if "amf" in encoder:
        cmd += [
            "-c:v", "h264_amf",
            "-rc", "vbr_peak",
            "-b:v", cfg["target"], "-maxrate", cfg["max"], "-bufsize", cfg["buf"],
            "-quality", "balanced", "-profile:v", "high",
            "-g", str(gop),
            "-pix_fmt", "yuv420p",
        ]
    elif "nvenc" in encoder:
        cmd += [
            "-c:v", "h264_nvenc", "-rc", "vbr",
            "-b:v", cfg["target"], "-maxrate", cfg["max"], "-bufsize", cfg["buf"],
            "-preset", "p5", "-tune", "hq", "-profile:v", "high",
            "-spatial_aq", "1", "-temporal_aq", "1",
            "-g", str(gop), "-bf", "3", "-pix_fmt", "yuv420p",
        ]
    elif "qsv" in encoder:
        cmd += [
            "-c:v", "h264_qsv",
            "-b:v", cfg["target"], "-maxrate", cfg["max"], "-bufsize", cfg["buf"],
            "-preset", "medium", "-profile:v", "high",
            "-g", str(gop), "-bf", "3", "-look_ahead", "1", "-pix_fmt", "yuv420p",
        ]
    else:
        cmd += [
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
            "-profile:v", "high", "-maxrate", cfg["max"], "-bufsize", cfg["buf"],
            "-g", str(gop), "-bf", "3", "-pix_fmt", "yuv420p",
        ]
    cmd += [
        "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-ac", "2",
        "-movflags", "+faststart", dst
    ]
    return cmd

def ffmpeg_cpu_fallback(src: str, dst: str, quality: str, fps: int = 30, vf: Optional[str] = None) -> List[str]:
    cfg_key = quality if quality in BITRATES else "720"
    cfg = BITRATES.get(cfg_key, BITRATES["720"])
    gop = fps * 2
    cmd = [
        "ffmpeg", "-y", "-i", src,
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
        "-profile", "high", "-maxrate", cfg["max"], "-bufsize", cfg["buf"],
        "-g", str(gop), "-bf", "3", "-pix_fmt", "yuv420p",
    ]
    if vf:
        cmd += ["-vf", vf]
    cmd += [
        "-c:a", "aac", "-b:a", "128k", "-ar", "44100",
        "-movflags", "+faststart", dst,
    ]
    return cmd

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
        
        # Читаем stderr по мере поступления, чтобы буфер Windows (64 КБ) никогда не переполнялся и не вешал процесс
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
                if len(err_lines) > 60:
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
# ─────────────────────────────────────────────
# YT-DLP ОПЦИИ (ПОЛНЫЙ ПАРСИНГ HLS И DASH)
# ─────────────────────────────────────────────
def ytdlp_opts() -> dict:
    opts = {
        "quiet": True,
        "no_warnings": True,
        "retries": 10,
        "fragment_retries": 10,
        "concurrent_fragment_downloads": 4,
        # Запрашиваем m3u8 и все внутренние клиенты YouTube, где живут дубляжи
        "extractor_args": {
            "youtube": ["player_client=web,android,ios,mweb"]
        },
        "sleep_interval_requests": 1,
    }
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        opts["ffmpeg_location"] = os.path.dirname(ffmpeg_path)
    if USE_PROXY:
        opts["proxy"] = f"socks5://{PROXY_HOST}:{PROXY_PORT}"

    if COOKIE_FILE and os.path.exists(COOKIE_FILE):
        opts["cookiefile"] = COOKIE_FILE
    elif os.path.exists("www.youtube.com_cookies.txt"):
        opts["cookiefile"] = "www.youtube.com_cookies.txt"
    elif os.path.exists("cookies.txt"):
        opts["cookiefile"] = "cookies.txt"
    elif BROWSER_COOKIES and BROWSER_COOKIES.lower() not in ["none", "false", "0", ""]:
        opts["cookiesfrombrowser"] = (BROWSER_COOKIES,)
    return opts

def download_video(url: str, quality: str, user_id: int, video_id: str, lang: str = "orig", cancel_token=None) -> str:
    opts = ytdlp_opts()
    if cancel_token:
        def hook(d):
            if cancel_token.cancelled:
                raise ValueError("CANCELLED")
        opts["progress_hooks"] = [hook]

    file_suffix = f"_{lang}" if lang in ("ru", "en") else ""
    opts["outtmpl"] = os.path.join(DOWNLOAD_DIR, f"{user_id}_{video_id}{file_suffix}.%(ext)s")
    opts["writethumbnail"] = True
    opts["merge_output_format"] = "mp4"

    q = int(quality) if str(quality).isdigit() else 720
    max_w_map = {1080: 1920, 720: 1280, 480: 854, 360: 640}
    max_w = max_w_map.get(q, 1280)

    # 1. Если запрошен РУССКИЙ дубляж
    if lang == "ru":
        opts["format_sort"] = [
            "hasaud", "lang:ru", f"res:{q}", "codec:h264:vp9:av1", "fps", "size", "br"
        ]
        opts["extractor_args"] = {
            "youtube": ["player_client=web,android,ios,mweb", "lang=ru"]
        }
        audio_priority = [
            "bestaudio[language^=ru]",
            "bestaudio[language*=ru]",
            "bestaudio[format_note*=Russian]",
            "bestaudio[format_note*=russian]",
            "bestaudio[format_note*=русск]",
            "bestaudio[format_id*=-ru]",
            "bestaudio[format_id*=dubbed]",
            "bestaudio[language_preference>0]",
            "bestaudio"
        ]
        candidates = []
        for a in audio_priority:
            candidates.append(f"bestvideo[height<={q}]+{a}")
            candidates.append(f"bestvideo[width<={max_w}]+{a}")
        # Также поддерживаем готовые склеенные HLS форматы на русском языке
        candidates.append(f"best[language^=ru][height<={q}]")
        candidates.append(f"best[format_note*=Russian][height<={q}]")
        candidates.append(f"best[height<={q}]")
        candidates.append("best")
        opts["format"] = "/".join(candidates)

    # 2. Если запрошен АНГЛИЙСКИЙ оригинал/дубляж
    elif lang == "en":
        opts["format_sort"] = [
            "hasaud", "lang:en", f"res:{q}", "codec:h264:vp9:av1", "fps", "size", "br"
        ]
        opts["extractor_args"] = {
            "youtube": ["player_client=web,android,ios,mweb", "lang=en"]
        }
        audio_priority = [
            "bestaudio[language^=en]",
            "bestaudio[language*=en]",
            "bestaudio[format_note*=English]",
            "bestaudio[format_note*=english]",
            "bestaudio[format_note*=original]",
            "bestaudio"
        ]
        candidates = []
        for a in audio_priority:
            candidates.append(f"bestvideo[height<={q}]+{a}")
            candidates.append(f"bestvideo[width<={max_w}]+{a}")
        candidates.append(f"best[language^=en][height<={q}]")
        candidates.append(f"best[height<={q}]")
        candidates.append("best")
        opts["format"] = "/".join(candidates)

    # 3. Для видео БЕЗ дубляжей (оригинальный авторский звук)
    else:
        opts["format_sort"] = [f"res:{q}", "fps", "codec:h264:vp9:av1", "size", "br"]
        candidates = [
            f"bestvideo[height<={q}]+bestaudio",
            f"bestvideo[width<={max_w}]+bestaudio",
            f"best[height<={q}][ext=mp4]",
            f"best[height<={q}]",
            "bestvideo+bestaudio",
            "best"
        ]
        opts["format"] = "/".join(candidates)

    term_log("📥 YT-DLP", f"[{user_id}] Загрузка {video_id} ({q}p, дорожка: {lang.upper()})...", Colors.CYAN)
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])

    search_key = f"{video_id}{file_suffix}"
    path = find_file(user_id, search_key)
    if not path:
        path = find_file(user_id, video_id)
    if not path:
        raise FileNotFoundError(f"Файл не найден: {user_id}_{video_id}{file_suffix}")
    return path

def download_mp3(url: str, user_id: int, video_id: str, lang: str = "orig", cancel_token=None) -> str:
    opts = ytdlp_opts()
    if cancel_token:
        def hook(d):
            if cancel_token.cancelled:
                raise ValueError("CANCELLED")
        opts["progress_hooks"] = [hook]

    file_suffix = f"_{lang}" if lang in ("ru", "en") else ""
    opts["outtmpl"] = os.path.join(DOWNLOAD_DIR, f"{user_id}_{video_id}{file_suffix}.%(ext)s")

    if lang == "ru":
        opts["format_sort"] = ["lang:ru", "size", "br"]
        opts["extractor_args"] = {
            "youtube": ["player_client=web,android,ios,mweb", "lang=ru"]
        }
        opts["format"] = (
            "bestaudio[language^=ru]/"
            "bestaudio[language*=ru]/"
            "bestaudio[format_note*=Russian]/"
            "bestaudio[format_note*=russian]/"
            "bestaudio[format_note*=русск]/"
            "bestaudio[format_id*=-ru]/"
            "bestaudio"
        )
    elif lang == "en":
        opts["format_sort"] = ["lang:en", "size", "br"]
        opts["extractor_args"] = {
            "youtube": ["player_client=web,android,ios,mweb", "lang=en"]
        }
        opts["format"] = (
            "bestaudio[language^=en]/"
            "bestaudio[language*=en]/"
            "bestaudio[format_note*=English]/"
            "bestaudio[format_note*=english]/"
            "bestaudio[format_note*=original]/"
            "bestaudio"
        )
    else:
        opts["format"] = "bestaudio/best"

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

# ─────────────────────────────────────────────
# ОБРАБОТКА ВИДЕО
# ─────────────────────────────────────────────
def process_video(url: str, quality: str, user_id: int, video_id: str, lang: str = "orig", cancel_token=None) -> Tuple[str, Optional[str], int]:
    src = download_video(url, quality, user_id, video_id, lang=lang, cancel_token=cancel_token)
    info = probe(src)
    actual_tier = get_format_tier(info["width"], info["height"])
    term_log(
        "🔎 PROBE",
        f"[{user_id}] {info['width']}x{info['height']} | V:{info['vcodec']} A:{info['acodec']} -> {actual_tier}p ({lang.upper()})",
        Colors.MAGENTA
    )

    file_suffix = f"_{lang}" if lang in ("ru", "en") else ""
    dst = os.path.join(DOWNLOAD_DIR, f"{user_id}_{video_id}{file_suffix}_out.mp4")
    fps = info["fps"] or 30
    target_q = int(quality) if str(quality).isdigit() else 720
    src_long = max(info["width"], info["height"])
    src_short = min(info["width"], info["height"])

    max_w_map = {1080: 1920, 720: 1280, 480: 854, 360: 640}
    max_w = max_w_map.get(target_q, 1280)
    need_scale = bool(target_q and (src_short > target_q + 40 and src_long > max_w + 40))

    vf = None
    if need_scale:
        if info["width"] >= info["height"]:
            vf = f"scale=-2:{target_q}"
        else:
            vf = f"scale={target_q}:-2"

    enc_quality = quality if str(quality).isdigit() else "720"

    if info["vcodec"] == "h264" and info["acodec"] in ("aac", "mp3") and not need_scale:
        term_log("⚡ FAST COPY", f"[{user_id}] Прямой проброс потоков...", Colors.GREEN)
        cmd = ["ffmpeg", "-y", "-i", src, "-c:v", "copy", "-c:a", "copy", "-movflags", "+faststart", dst]
        ok, err = run_ffmpeg(cmd, dst, cancel_token)
    elif info["vcodec"] == "h264" and not need_scale:
        term_log("⚡ AUDIO FIX", f"[{user_id}] Перекодирование звука в AAC...", Colors.GREEN)
        cmd = ["ffmpeg", "-y", "-i", src, "-c:v", "copy", "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-movflags", "+faststart", dst]
        ok, err = run_ffmpeg(cmd, dst, cancel_token)
    else:
        term_log("⚙️ TRANSCODE", f"[{user_id}] Аппаратный рендер ({VIDEO_ENCODER})...", Colors.YELLOW)
        ok, err = False, ""
        if VIDEO_ENCODER != "libx264":
            cmd = ffmpeg_transcode(src, dst, enc_quality, VIDEO_ENCODER, fps, vf=vf)
            ok, err = run_ffmpeg(cmd, dst, cancel_token)
        if not ok:
            term_log("⚠️ FALLBACK", f"[{user_id}] Переключение на CPU libx264...", Colors.YELLOW)
            if os.path.exists(dst):
                try:
                    os.remove(dst)
                except Exception:
                    pass
            cmd = ffmpeg_cpu_fallback(src, dst, enc_quality, fps, vf=vf)
            ok, err = run_ffmpeg(cmd, dst, cancel_token)

    if not ok:
        raise RuntimeError(f"FFmpeg ошибка: {err[-250:]}")

    try:
        os.remove(src)
    except Exception:
        pass

    final_info = probe(dst)
    final_tier = get_format_tier(final_info["width"], final_info["height"])
    return dst, make_thumb(user_id, f"{video_id}{file_suffix}"), final_tier

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
    subprocess.run(
        ["ffmpeg", "-y", "-i", raw, "-vf", "scale=320:-1", "-q:v", "5", thumb],
        capture_output=True
    )
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

def make_video_keyboard(vid: str, current_lang: str = "orig", is_playlist: bool = False) -> List[List[Button]]:
    meta = video_meta.get(vid, {})
    tiers = meta.get("tiers", [1080, 720, 480, 360])
    is_multi = meta.get("is_multiaudio", False)

    buttons = []

    # Добавляем кнопки выбора языков ТОЛЬКО ЕСЛИ реально найден дубляж
    if is_multi:
        ru_mark = "✅ " if current_lang == "ru" else ""
        en_mark = "✅ " if current_lang == "en" else ""
        if is_playlist:
            buttons.append([
                Button.inline(f"{ru_mark}🇷🇺 Русский", f"pllang:ru:{vid}".encode()),
                Button.inline(f"{en_mark}🇬🇧 English", f"pllang:en:{vid}".encode())
            ])
        else:
            buttons.append([
                Button.inline(f"{ru_mark}🇷🇺 Русский", f"lang:ru:{vid}".encode()),
                Button.inline(f"{en_mark}🇬🇧 English", f"lang:en:{vid}".encode())
            ])

    # Кнопки качества
    if is_playlist:
        buttons.append([
            Button.inline("⚡ 1080p", f"pl:3:1080:{vid}:{current_lang}".encode()),
            Button.inline("⚡ 720p", f"pl:3:720:{vid}:{current_lang}".encode())
        ])
        buttons.append([
            Button.inline("⚡ 480p", f"pl:3:480:{vid}:{current_lang}".encode()),
            Button.inline("⚡ 360p", f"pl:3:360:{vid}:{current_lang}".encode())
        ])
        return buttons

    row = []
    for t in tiers:
        has_cached = bool(db.get_cache(vid, str(t), lang=current_lang))
        icon = "⚡" if has_cached else "🎬"
        row.append(Button.inline(f"{icon} {t}p", f"dl:{t}:{vid}:{current_lang}".encode()))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    mp3_cached = bool(db.get_cache(vid, "mp3", lang=current_lang))
    mp3_icon = "⚡" if mp3_cached else "🎵"
    buttons.append([Button.inline(f"{mp3_icon} Скачать MP3 (Аудио)", f"dl:mp3:{vid}:{current_lang}".encode())])
    return buttons

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
        db.register_user(event.sender_id, event.sender.username or "")
        limit = "4 ГБ 💎" if is_premium else "2 ГБ"
        term_log("👋 USER", f"Пользователь {event.sender_id} (@{event.sender.username or 'none'}) нажал /start", Colors.BLUE)
        await event.respond(
            "👋 **Привет! Я YouTube Monster Bot.**\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "💬 **Как пользоваться:**\n"
            "1️⃣ Отправь ссылку на ролик YouTube / Shorts / плейлист\n"
            "2️⃣ Если у видео есть дубляж (Mark Rober, MrBeast или AI-перевод) — появится выбор озвучки (RU/EN)\n"
            "3️⃣ Выбери качество видео кнопками\n"
            "4️⃣ Получи файл прямо в Telegram!\n\n"
            "⚡ **Кэш V2** — мгновенная отдача роликов без повторного скачивания\n"
            f"🛡 **Максимальный размер:** {limit}\n"
            "━━━━━━━━━━━━━━━━━━━━"
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
        "• <code>/cache</code> — интерактивное управление кэшем (пагинация + просмотр + удаление)\n"
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
        "• <code>/start</code> — перезапуск бота и приветствие\n"
        "• Ссылка на YouTube — анализ, выбор качества и скачивание"
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
            f"⚙️ Видеокодек: `{VIDEO_ENCODER}` (AMD RX 6600)\n"
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
    # УПРАВЛЕНИЕ КЭШЕМ
    # ─────────────────────────────────────────
    def format_cache_item(vid: str, q_key: str, title: str, dt) -> Tuple[str, str]:
        t_clean = (title or "").strip()
        if not t_clean or t_clean.lower() in ("none", "без названия", "unknown"):
            t_clean = f"YouTube Видео ({vid})"

        if "_" in str(q_key):
            res_part, lang_part = q_key.split("_", 1)
            flag = "🇷🇺" if lang_part == "ru" else "🇬🇧"
            label = f"{res_part}p [{flag} {lang_part.upper()}]"
        else:
            label = f"{q_key}p [Оригинал]"
        return t_clean, label

    async def render_cache_page(event, page: int = 1):
        items, total = db.get_cache_page(page, page_size=5)
        max_page = max(1, math.ceil(total / 5))
        page = max(1, min(page, max_page))

        if not items:
            text = "⚡ **Кэш видео пуст.**"
            kb = [[Button.inline("🔙 Назад в админку", b"adm:panel")]]
            if isinstance(event, events.CallbackQuery.Event):
                return await event.edit(text, buttons=kb)
            return await event.respond(text, buttons=kb)

        lines = [f"⚡ **УПРАВЛЕНИЕ КЭШЕМ** (Стр. `{page}/{max_page}` | Всего: `{total}`)\n━━━━━━━━━━━━━━━━━━━━"]
        buttons = []

        for vid, q_key, title, dt, file_id in items:
            t_clean, label = format_cache_item(vid, q_key, title, dt)
            lines.append(f"🎬 **{t_clean[:40]}**\n   └ ID: `{vid}` | {label} | 📅 `{str(dt)[:10]}`")
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

        msg_text = "\n".join(lines) + "\n━━━━━━━━━━━━━━━━━━━━\n💡 *Нажмите «🎬 Отправить», чтобы отправить видео из кэша себе в чат.*"

        if isinstance(event, events.CallbackQuery.Event):
            await event.edit(msg_text, buttons=buttons)
        else:
            await event.respond(msg_text, buttons=buttons)

    @client.on(events.NewMessage(pattern=re.compile(r"^/cache(?:@\w+)?(?:\s+(.+))?$", re.IGNORECASE)))
    async def cmd_cache(event):
        if not check_admin(event.sender_id):
            return await event.respond("❌ Недостаточно прав.")
        query = event.pattern_match.group(1)
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

    # Отправка из кэша (cview)
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
            term_log("⚠️ CVIEW FAIL", f"Файл {vid} ({q_key}) не найден в bot.db!", Colors.YELLOW)
            return await event.answer("⚠️ Файл не найден в базе кэша.", alert=True)

        file_id, title = cache_data
        await event.answer("🚀 Отправляю видео из кэша...")
        term_log("⚡ CVIEW", f"Администратор {event.sender_id} запросил просмотр из кэша: {vid} [{q_key}]", Colors.GREEN)

        try:
            if lang in ("ru", "en"):
                flag = "🇷🇺 RU" if lang == "ru" else "🇬🇧 EN"
                caption = f"🎬 <b>{title or vid}</b> [{flag} {quality}p]\n⚡ <i>Отправлено напрямую из базы кэша</i>"
            else:
                caption = f"🎬 <b>{title or vid}</b> [{quality}p]\n⚡ <i>Отправлено напрямую из базы кэша</i>"
            await client.send_file(event.sender_id, file_id, caption=caption, parse_mode="html")
        except Exception as e:
            term_log("❌ CVIEW ERROR", f"Ошибка отправки файла из кэша: {e}", Colors.RED)
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
        term_log("💥 CACHE PURGE", f"Владелец ПОЛНОСТЬЮ очистил кэш ({count} записей)", Colors.RED)
        await event.answer("✅ Весь кэш успешно удален!", alert=True)
        await render_cache_page(event, page=1)

    # Удаление из кэша (cdel)
    @client.on(events.CallbackQuery(pattern=b"^cdel:"))
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
            term_log("🗑️ CACHE DEL", f"Владелец удалил из кэша {vid} [{q_key}]. Записей: {deleted_rows}, файлов с диска: {cleaned_files}", Colors.GREEN)
            await event.answer(f"✅ Удалено: {vid} [{q_key}]", alert=False)
        else:
            term_log("⚠️ CACHE DEL", f"Запись {vid} [{q_key}] отсутствовала в кэше", Colors.YELLOW)
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
        term_log("🗑️ MANUAL DELCACHE", f"Владелец удалил {vid}: {deleted} записей БД, {cleaned} файлов с диска", Colors.GREEN)
        if deleted or cleaned:
            await event.respond(f"✅ Видео `{vid}` успешно удалено из кэша и диска.")
        else:
            await event.respond(f"⚠️ Видео `{vid}` не найдено в базе кэша.")

    @client.on(events.NewMessage(pattern=re.compile(r"^/clearcache(?:@\w+)?$", re.IGNORECASE)))
    async def cmd_clearcache_manual(event):
        if not check_owner(event.sender_id):
            return await event.respond("❌ Только владелец бота может очищать кэш.")
        count = db.clear_all_cache()
        term_log("💥 CACHE PURGE", f"Владелец очистил кэш через команду ({count} записей)", Colors.RED)
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
            f"⚙️ Видеокодек: `{VIDEO_ENCODER}` (AMD RX 6600)\n"
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
        term_log("💎 PREM ADD", f"[{event.sender_id}] Добавлен в whitelist: {uid} (@{uname})", Colors.GREEN)
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
        term_log("🗑️ PREM DEL", f"[{event.sender_id}] Удален из whitelist: {uid}", Colors.YELLOW)
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
        term_log("⛔ BAN", f"Администратор {event.sender_id} заблокировал {uid}", Colors.RED)
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
        term_log("✅ UNBAN", f"Администратор {event.sender_id} разблокировал {uid}", Colors.GREEN)
        await event.respond(f"✅ Пользователь {user_link(uid, uname)} разблокирован.", parse_mode="html")

    @client.on(events.NewMessage(pattern=re.compile(r"^/broadcast(?:@\w+)?\s+(.+)", re.IGNORECASE)))
    async def cmd_broadcast(event):
        if not check_admin(event.sender_id):
            return await event.respond("❌ Недостаточно прав.")
        text = event.pattern_match.group(1)
        users = db.all_users()
        ok = 0
        status_msg = await event.respond(f"📣 Начинаю рассылку для {len(users)} пользователей...")
        term_log("📢 BROADCAST", f"Админ {event.sender_id} запустил рассылку...", Colors.CYAN)
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
    # ПЕРЕКЛЮЧАТЕЛЬ ОЗВУЧКИ (ИНЛАЙН RU/EN)
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

        lang_name = "🇷🇺 Русский" if new_lang == "ru" else "🇬🇧 English"
        kind = "📱 Shorts" if meta.get("is_short") else "🎥 Видео"

        await event.edit(
            f"🎥 **{meta['title']}**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 Автор: {hashtag(meta['uploader'])}\n"
            f"⏱ Длительность: `{timedelta(seconds=meta['duration'])}`\n"
            f"📐 Максимальное качество: `{meta['max_quality']}p`\n"
            f"🧬 Формат: `{kind}`\n"
            f"🔊 Выбранная озвучка: **{lang_name}**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👇 *Выберите качество для загрузки:*",
            buttons=kb
        )
        await event.answer(f"Выбрана озвучка: {lang_name}")

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
        lang_name = "🇷🇺 Русский" if new_lang == "ru" else "🇬🇧 English"

        await event.edit(
            f"📚 **{meta['title']}**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 Автор: {hashtag(meta.get('uploader', ''))}\n"
            f"🎞 Роликов: `{len(meta['ids'])}`\n"
            f"🔊 Выбранная озвучка: **{lang_name}**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👇 *Выберите качество для скачивания плейлиста:*",
            buttons=kb
        )
        await event.answer(f"Озвучка плейлиста: {lang_name}")

    # ─────────────────────────────────────────
    # ОБРАБОТКА ССЫЛОК И ПЛЕЙЛИСТОВ
    # ─────────────────────────────────────────
    @client.on(events.NewMessage(
        func=lambda e: bool(e.text) and not e.text.startswith("/") and bool(extract_url(e.text))))
    async def on_link(event):
        if db.is_banned(event.sender_id):
            return await event.respond("❌ Ваш аккаунт заблокирован в боте.")
        db.register_user(event.sender_id, event.sender.username or "")
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
                video_meta[pl_id] = {
                    "title": pl_title,
                    "uploader": info.get("uploader", "Unknown"),
                    "is_playlist": True,
                    "ids": ids,
                    "is_multiaudio": False,
                    "selected_lang": "orig"
                }
                kb = make_video_keyboard(pl_id, current_lang="orig", is_playlist=True)
                await msg.edit(
                    f"📚 **{pl_title}**\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"👤 Автор: {hashtag(info.get('uploader', ''))}\n"
                    f"🎞 Видеороликов: `{len(ids)}`\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"👇 *Выберите качество скачивания:*",
                    buttons=kb
                )
            except Exception as e:
                term_log("❌ PLAYLIST", f"Ошибка анализа плейлиста: {e}", Colors.RED)
                await msg.edit(f"❌ Ошибка загрузки плейлиста:\n`{e}`")
            return

        msg = await event.respond("🔍 **Глубокий анализ видео и аудиодорожек (дубляж)...**")
        try:
            opts = ytdlp_opts()
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)

            if info.get("is_live"):
                return await msg.edit("❌ Прямые эфиры не поддерживаются.")

            vid = info["id"]
            title = info.get("title") or info.get("alt_title") or f"Ролик {vid}"
            uploader = info.get("uploader", "Unknown")
            duration = int(info.get("duration") or 0)
            is_short = is_shorts_url(url, info)

            db.update_title_if_needed(vid, title)

            tiers = get_available_tiers(info)
            max_tier = tiers[0] if tiers else 720
            
            # Глубокая проверка дорожек: ищет дубляж и AI-автоперевод
            audio_info = detect_audio_tracks(info)
            is_multi = audio_info["is_multiaudio"]

            term_log(
                "🎬 INFO",
                f"[{uid}] \"{title[:35]}\" | {max_tier}p | Дорожки: {'Дубляж/AI (RU/EN)' if is_multi else 'Оригинал (1 дорожка)'}",
                Colors.GREEN
            )

            # Если дубляжа нет — скрываем выбор языка
            selected_lang = "ru" if is_multi else "orig"

            video_meta[vid] = {
                "url": url, "title": title, "uploader": uploader,
                "duration": duration, "is_short": is_short,
                "max_quality": max_tier, "tiers": tiers,
                "is_multiaudio": is_multi,
                "selected_lang": selected_lang
            }

            kb = make_video_keyboard(vid, current_lang=selected_lang, is_playlist=False)
            kind = "📱 Shorts" if is_short else "🎥 Видео"

            msg_text = (
                f"🎥 **{title}**\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"👤 Автор: {hashtag(uploader)}\n"
                f"⏱ Длительность: `{timedelta(seconds=duration)}`\n"
                f"📐 Максимальное качество: `{max_tier}p`\n"
                f"🧬 Формат: `{kind}`\n"
            )
            if is_multi:
                msg_text += f"🔊 Озвучка: **🇷🇺 Русский** *(доступен выбор)*\n"
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
    # СКАЧИВАНИЕ И ВЫГРУЗКА
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
            lang_label = "🇷🇺 Русский"
        elif lang == "en":
            lang_label = "🇬🇧 English"
        else:
            lang_label = "Оригинальный звук"

        q_label = "MP3 🎵" if quality == "mp3" else f"{quality}p 🎬"
        msg = await event.reply(f"⏳ **Подготовка к обработке...**\nКачество: `{q_label}` | Звук: `{lang_label}`", buttons=cancel_kb)

        # 1. Проверяем локальный кэш
        cache_data = db.get_cache(vid, quality, lang=lang)
        if cache_data:
            cached_file_id, cached_title = cache_data
            term_log("⚡ CACHE HIT", f"[{uid}] Видео {vid} [{quality}p_{lang.upper()}] найдено в кэше! Мгновенная отдача...", Colors.GREEN)
            await msg.edit(f"⚡ **Найдено в кэше! Отправка без задержки...**")
            caption_suffix = f" [{lang_label}]" if lang in ("ru", "en") else ""
            caption = f"🎬 **{cached_title or meta['title']}**{caption_suffix}\n\n👤 {hashtag(meta['uploader'])}"
            try:
                await client.send_file(uid, cached_file_id, caption=caption)
                await msg.delete()
                db.add_stats(uid, 0)
                cancel_tokens.pop(task_id, None)
                term_log("✅ CACHE SENT", f"[{uid}] Ролик {vid} успешно отдан из кэша (0 секунд).", Colors.GREEN)
                return
            except Exception as e:
                term_log("⚠️ CACHE INVALID", f"[{uid}] File ID из кэша недействителен ({e}), перекачиваю...", Colors.YELLOW)
                db.del_cache(vid, f"{quality}_{lang}" if lang in ("ru", "en") else quality)

        # 2. Скачивание и кодирование
        try:
            if quality == "mp3":
                final = await asyncio.to_thread(download_mp3, meta["url"], uid, vid, lang, token)
                thumb = None
                delivered_tier = "mp3"
            else:
                final, thumb, delivered_tier = await asyncio.to_thread(
                    process_video, meta["url"], quality, uid, vid, lang, token)

            size_mb = os.path.getsize(final) / (1024 * 1024)
            has_premium = is_premium_user(uid, getattr(event.sender, "username", "") or "") and is_premium
            max_mb = 3950 if has_premium else 1950

            if size_mb > max_mb:
                term_log("❌ SIZE LIMIT", f"[{uid}] Размер превышает лимит: {size_mb:.1f} MB > {max_mb} MB", Colors.RED)
                await msg.edit(f"❌ **Файл превышает лимит**\n📦 Размер: `{size_mb:.1f} МБ`\n🛡 Допустимый лимит: `{max_mb} МБ`")
                await rm(final)
                if thumb:
                    await rm(thumb)
                return

            async with upload_semaphore:
                if token.cancelled:
                    raise ValueError("CANCELLED")

                contour = "💎 Premium 4GB" if (size_mb > 1950 and user_client) else "📦 Standard 2GB"
                term_log("🚀 UPLOAD", f"[{uid}] Выгрузка в Telegram [{contour}] ({size_mb:.1f} МБ, {lang.upper()})...", Colors.CYAN)
                await msg.edit(f"⚙️ **Файл подготовлен!**\n📤 Выгрузка в Telegram [{contour}]...", buttons=cancel_kb)

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
                        f"⏳ Примерно осталось: **{timedelta(seconds=int(eta))}**"
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
                caption_suffix = f" [{lang_label}]" if lang in ("ru", "en") else ""
                caption = f"🎬 **{title_clean}**{caption_suffix}\n\n👤 {hashtag(meta['uploader'])}"
                attrs = []
                if quality == "mp3":
                    attrs.append(DocumentAttributeAudio(duration=meta["duration"], title=title_clean))
                else:
                    info = probe(final)
                    attrs.append(DocumentAttributeVideo(
                        duration=info["duration"] or meta["duration"],
                        w=info["width"] or 1280,
                        h=info["height"] or 720,
                        supports_streaming=True
                    ))

                sent = await sender.send_file(
                    uid, uploaded, caption=caption, thumb=thumb,
                    attributes=attrs, supports_streaming=True)

                if sender == client and sent and sent.document:
                    try:
                        cache_save_tier = str(delivered_tier)
                        packed_id = utils.pack_bot_file_id(sent.document)
                        db.set_cache(vid, cache_save_tier, lang, packed_id, title_clean)
                        term_log("💾 CACHE SAVED", f"[{uid}] Закэшировано: {vid} [{cache_save_tier}p_{lang.upper()}] \"{title_clean[:30]}\"", Colors.GREEN)
                    except Exception as e:
                        term_log("⚠️ CACHE ERROR", f"Не удалось сохранить кэш: {e}", Colors.YELLOW)

            db.add_stats(uid, size_mb)
            await rm(final)
            if thumb:
                await rm(thumb)
            await msg.delete()
            term_log("✅ DONE", f"[{uid}] Видео {vid} доставлено ({size_mb:.1f} МБ, {lang.upper()})", Colors.GREEN)

        except ValueError as e:
            if str(e) == "CANCELLED":
                term_log("🛑 CANCELLED", f"[{uid}] Загрузка {vid} отменена", Colors.YELLOW)
                await msg.edit("❌ **Операция успешно отменена пользователем.**")
                cleanup_disk_for_video(f"{uid}_{vid}")
            else:
                raise e
        except Exception as e:
            term_log("❌ ERROR", f"[{uid}] Ошибка скачивания {vid}: {e}", Colors.RED)
            await msg.edit(f"❌ **Произошла ошибка при загрузке:**\n`{str(e)[:220]}`")
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

        term_log("📚 PLAYLIST START", f"[{uid}] Старт плейлиста {pl_id}: {total} роликов", Colors.MAGENTA)
        await event.edit(
            f"📚 **{meta['title']}**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🎞 Всего роликов: `{total}` | Пачки по `{batch}`\n"
            f"📐 Качество: `{quality}p`\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"⏳ *Обработка плейлиста запущена...*",
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
            term_log("✅ PLAYLIST DONE", f"[{uid}] Плейлист {pl_id} доставлен", Colors.GREEN)
            await client.send_message(uid, f"✅ **Плейлист полностью обработан!**\n🎞 Доставлено `{total}` видео.")
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

        caption = f"🎬 **{title}**\n\n👤 {hashtag(uploader)}"

        cache_data = db.get_cache(vid, quality, lang=lang)
        if cache_data:
            cached_file_id, cached_title = cache_data
            try:
                await client.send_file(uid, cached_file_id, caption=caption)
                term_log("⚡ PL CACHE", f"[{uid}] Ролик плейлиста {vid} отправлен из кэша", Colors.GREEN)
                return
            except Exception:
                db.del_cache(vid, f"{quality}_{lang}" if lang in ("ru", "en") else quality)

        cancel_kb = [[Button.inline("❌ Отменить плейлист", f"cancel:{pl_task_id}".encode())]]
        status = await client.send_message(uid, f"📥 **Обрабатывается:**\n`{title[:50]}`", buttons=cancel_kb)

        try:
            final, thumb, del_tier = await asyncio.to_thread(
                process_video, url, quality, uid, vid, lang, token)
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

                info = probe(final)
                attrs = [DocumentAttributeVideo(
                    duration=info["duration"] or duration,
                    w=info["width"] or 1280,
                    h=info["height"] or 720,
                    supports_streaming=True)]
                sender = user_client if (size_mb > 1950 and is_premium and user_client) else client
                uploaded = await upload_file(sender, final, cancel_token=token)
                if token.cancelled:
                    raise ValueError("CANCELLED")

                sent = await sender.send_file(
                    uid, uploaded, caption=caption, thumb=thumb,
                    attributes=attrs, supports_streaming=True)
                if sender == client and sent and sent.document:
                    try:
                        db.set_cache(vid, str(del_tier), lang, utils.pack_bot_file_id(sent.document), title)
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
# КОНСОЛЬНОЕ МЕНЮ
# ═══════════════════════════════════════════════
CODECS = {"1": "libx264", "2": "h264_amf", "3": "h264_nvenc", "4": "h264_qsv"}
CODEC_NAMES = {
    "libx264": "libx264 (CPU)",
    "h264_amf": "h264_amf (AMD Radeon RX 6600)",
    "h264_nvenc": "h264_nvenc (NVIDIA GeForce)",
    "h264_qsv": "h264_qsv (Intel QuickSync)",
}
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
    global VIDEO_ENCODER, USE_PROXY, DEFAULT_BATCH, BROWSER_COOKIES
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
        print(f"  {Colors.BOLD}[3]{Colors.RESET} 🎥 Видеокодек:                 [{Colors.YELLOW}{CODEC_NAMES.get(VIDEO_ENCODER, VIDEO_ENCODER)}{Colors.RESET}]")
        print(f"  {Colors.BOLD}[4]{Colors.RESET} 🌐 SOCKS5 Прокси:              [{'ВКЛЮЧЕН 🟢' if USE_PROXY else 'ВЫКЛЮЧЕН 🔴'}]")
        print(f"  {Colors.BOLD}[5]{Colors.RESET} 📦 Пачка в плейлисте:          [по {Colors.MAGENTA}{DEFAULT_BATCH}{Colors.RESET} видео]")

        if os.path.exists("www.youtube.com_cookies.txt"):
            cookie_status = f"{Colors.GREEN}www.youtube.com_cookies.txt 🟢{Colors.RESET}"
        elif os.path.exists("cookies.txt"):
            cookie_status = f"{Colors.GREEN}cookies.txt 🟢{Colors.RESET}"
        elif COOKIE_FILE and os.path.exists(COOKIE_FILE):
            cookie_status = f"{Colors.GREEN}{COOKIE_FILE} 🟢{Colors.RESET}"
        else:
            cookie_status = BROWSER_COOKIES or f"{Colors.RED}не заданы{Colors.RESET}"

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
            print("\n  Выберите энкодер:")
            for k, v in CODEC_NAMES.items():
                print(f"   • {k}: {v}")
            enc = input("\n  Введите номер (1-4): ").strip()
            if enc in CODECS:
                VIDEO_ENCODER = CODECS[enc]
                update_env("VIDEO_ENCODER", VIDEO_ENCODER)
                cprint(f"  ✅ Установлен кодек: {CODEC_NAMES[VIDEO_ENCODER]}", Colors.GREEN)
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
# СТАРТ СИСТЕМЫ
# ═══════════════════════════════════════════════
async def start_bot():
    global bot, user_client, is_premium, bot_username, owner_id, OWNER_ID
    owner_id = OWNER_ID
    proxy = get_telethon_proxy()

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
        term_log("🎥 FFMPEG", f"{first_line} | Кодек: {VIDEO_ENCODER}", Colors.GREEN)
    except Exception:
        term_log("⛔ CRITICAL", "FFmpeg не обнаружен в PATH! Проверьте установку.", Colors.RED)
        sys.exit(1)

    setup_handlers(bot)
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
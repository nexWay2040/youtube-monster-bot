"""
YouTube Monster Bot — Ultimate Edition (working)
Telethon + yt-dlp + FFmpeg (h264_amf) + SQLite3
Windows / AMD RX 6600  •  Консольное меню + быстрый запуск
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
from datetime import timedelta
from typing import Optional, Tuple, List, Dict, Set

from telethon import TelegramClient, events, functions, types, utils
from telethon.tl.custom import Button
from telethon.tl.types import DocumentAttributeVideo, DocumentAttributeAudio
from telethon.errors import FloodWaitError
import yt_dlp
import socks
from dotenv import load_dotenv, set_key

# ─────────────────────────────────────────────
# КОНФИГ
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
PREMIUM_USERS: Set[int] = {
    int(x.strip()) for x in _env("PREMIUM_USERS", "").split(",") if x.strip().isdigit()
}
DEFAULT_BATCH = int(_env("DEFAULT_BATCH_SIZE", "3"))
USE_USERBOT = _env("USE_USERBOT", "true").lower() == "true"
QUICK_START = _env("QUICK_START", "false").lower() == "true"
OWNER_ID = int(_env("OWNER_ID", "0"))  # ID администратора (не зависит от юзербота)

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("bot.log", encoding="utf-8"),
    ],
)
log = logging.getLogger("bot")


def update_env(key: str, value: str):
    try:
        set_key(ENV_FILE, key, str(value))
    except Exception as e:
        log.warning(f"Не удалось сохранить {key} в {ENV_FILE}: {e}")
    os.environ[key] = str(value)


# ─────────────────────────────────────────────
# БАЗА ДАННЫХ
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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (video_id, quality)
            );
        """)
        self.conn.commit()
        self._migrate()  # ← докидывает недостающие столбцы в старые базы

    def _migrate(self):
        """
        Авто-миграция: если в старой базе нет какого-то столбца —
        добавляем его через ALTER TABLE. Спасает от 'no such column'.
        """
        schema = {
            "users": [
                ("username", "username TEXT"),
                ("joined_at", "joined_at TIMESTAMP"),
                ("is_banned", "is_banned INTEGER DEFAULT 0"),
                ("total_videos", "total_videos INTEGER DEFAULT 0"),
                ("total_mb", "total_mb REAL DEFAULT 0"),
            ],
            "cache": [
                ("created_at", "created_at TIMESTAMP"),
            ],
        }
        for table, cols in schema.items():
            try:
                self.c.execute(f"PRAGMA table_info({table})")
                existing = {row[1] for row in self.c.fetchall()}
            except sqlite3.Error:
                continue
            for name, ddl in cols:
                if name not in existing:
                    try:
                        self.c.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")
                        log.info(f"🔧 Миграция БД: добавлен столбец {table}.{name}")
                    except sqlite3.Error as e:
                        log.warning(f"Не удалось добавить {table}.{name}: {e}")
        self.conn.commit()

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

    def get_cache(self, vid: str, quality: str) -> Optional[str]:
        self.c.execute("SELECT file_id FROM cache WHERE video_id=? AND quality=?", (vid, quality))
        row = self.c.fetchone()
        return row[0] if row else None

    def set_cache(self, vid: str, quality: str, file_id: str):
        self.c.execute(
            "INSERT OR REPLACE INTO cache (video_id, quality, file_id) VALUES (?,?,?)",
            (vid, quality, file_id))
        self.conn.commit()

    def del_cache(self, vid: str, quality: str):
        self.c.execute("DELETE FROM cache WHERE video_id=? AND quality=?", (vid, quality))
        self.conn.commit()

    def all_users(self) -> List[int]:
        self.c.execute("SELECT user_id FROM users WHERE is_banned=0")
        return [r[0] for r in self.c.fetchall()]

    def get_users_list(self, limit=50) -> list:
        self.c.execute(
            "SELECT user_id, username, is_banned, total_videos FROM users "
            "ORDER BY joined_at DESC LIMIT ?", (limit,))
        return self.c.fetchall()

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
# УТИЛИТЫ
# ─────────────────────────────────────────────
def fmt_size(n: float) -> str:
    for unit in ("Б", "КБ", "МБ", "ГБ"):
        if abs(n) < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} ТБ"


def progress_bar(pct: float, length=14) -> str:
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
    """HTML-ссылка на профиль (работает даже без @username)."""
    name = html.escape(f"@{username}") if username else f"User {uid}"
    return f'<a href="tg://user?id={uid}">{name}</a>'


async def rm(path: Optional[str]):
    if not path or not os.path.exists(path):
        return
    for _ in range(5):
        try:
            os.remove(path)
            return
        except PermissionError:
            await asyncio.sleep(1)
    log.warning(f"Не удалось удалить: {path}")


def find_file(user_id: int, video_id: str) -> Optional[str]:
    prefix = f"{user_id}_{video_id}."
    for f in os.listdir(DOWNLOAD_DIR):
        if f.startswith(prefix) and not f.endswith(('.jpg', '.webp', '.png', '.part', '.ytdl')):
            return os.path.join(DOWNLOAD_DIR, f)
    return None


# ─────────────────────────────────────────────
# FFPROBE
# ─────────────────────────────────────────────
def probe(path: str) -> dict:
    result = {"width": 0, "height": 0, "duration": 0, "fps": 30, "vcodec": "", "acodec": ""}
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "stream=width,height,duration,r_frame_rate,codec_name,codec_type",
            "-show_entries", "format=duration",
            "-of", "json", path]
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
        log.error(f"ffprobe: {e}")
    return result


# ─────────────────────────────────────────────
# FFmpeg
# ─────────────────────────────────────────────
BITRATES = {
    "1080": {"target": "4500k", "max": "7000k", "buf": "14000k"},
    "720":  {"target": "2800k", "max": "4500k", "buf": "9000k"},
    "480":  {"target": "1200k", "max": "2000k", "buf": "4000k"},
    "360":  {"target": "700k",  "max": "1200k", "buf": "2400k"},
}


def ffmpeg_transcode(src: str, dst: str, quality: str, encoder: str, fps: int = 30) -> List[str]:
    cfg = BITRATES.get(quality, BITRATES["720"])
    gop = fps * 2
    cmd = ["ffmpeg", "-y"]
    if "amf" in encoder or "nvenc" in encoder:
        cmd += ["-hwaccel", "d3d11va"]
    cmd += ["-i", src]
    if "amf" in encoder:
        cmd += [
            "-c:v", "h264_amf", "-rc", "vbr",
            "-b:v", cfg["target"], "-maxrate", cfg["max"], "-bufsize", cfg["buf"],
            "-quality", "balanced", "-profile", "high", "-level", "4.2",
            "-g", str(gop), "-bf", "3", "-header_insertion_mode", "gop",
            "-pix_fmt", "yuv420p",
        ]
    elif "nvenc" in encoder:
        cmd += [
            "-c:v", "h264_nvenc", "-rc", "vbr",
            "-b:v", cfg["target"], "-maxrate", cfg["max"], "-bufsize", cfg["buf"],
            "-preset", "p5", "-tune", "hq", "-profile", "high",
            "-spatial_aq", "1", "-temporal_aq", "1",
            "-g", str(gop), "-bf", "3", "-pix_fmt", "yuv420p",
        ]
    elif "qsv" in encoder:
        cmd += [
            "-c:v", "h264_qsv",
            "-b:v", cfg["target"], "-maxrate", cfg["max"], "-bufsize", cfg["buf"],
            "-preset", "medium", "-profile", "high",
            "-g", str(gop), "-bf", "3", "-look_ahead", "1", "-pix_fmt", "yuv420p",
        ]
    else:
        cmd += [
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
            "-profile", "high", "-maxrate", cfg["max"], "-bufsize", cfg["buf"],
            "-g", str(gop), "-bf", "3", "-pix_fmt", "yuv420p",
        ]
    cmd += ["-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-ac", "2",
            "-movflags", "+faststart", dst]
    return cmd


def ffmpeg_cpu_fallback(src: str, dst: str, quality: str, fps: int = 30) -> List[str]:
    cfg = BITRATES.get(quality, BITRATES["720"])
    gop = fps * 2
    return [
        "ffmpeg", "-y", "-i", src,
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
        "-profile", "high", "-maxrate", cfg["max"], "-bufsize", cfg["buf"],
        "-g", str(gop), "-bf", "3", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k", "-ar", "44100",
        "-movflags", "+faststart", dst,
    ]


def run_ffmpeg(cmd: List[str], output: str) -> Tuple[bool, str]:
    log.debug(f"FFmpeg: {' '.join(cmd)}")
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0 or not os.path.exists(output) or os.path.getsize(output) == 0:
        err = (r.stderr or "")[-800:]
        log.error(f"FFmpeg failed (code {r.returncode}): {err}")
        return False, err
    return True, ""


# ─────────────────────────────────────────────
# YT-DLP
# ─────────────────────────────────────────────
def ytdlp_opts() -> dict:
    opts = {
        "quiet": True, "no_warnings": True,
        "retries": 10, "fragment_retries": 10, "concurrent_fragment_downloads": 4,
    }
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        opts["ffmpeg_location"] = os.path.dirname(ffmpeg_path)
    if USE_PROXY:
        opts["proxy"] = f"socks5://{PROXY_HOST}:{PROXY_PORT}"
    if BROWSER_COOKIES:
        opts["cookiesfrombrowser"] = (BROWSER_COOKIES,)
    return opts


def download_video(url: str, quality: str, user_id: int, video_id: str) -> str:
    opts = ytdlp_opts()
    opts["outtmpl"] = os.path.join(DOWNLOAD_DIR, f"{user_id}_{video_id}.%(ext)s")
    opts["writethumbnail"] = True
    opts["merge_output_format"] = "mp4"
    opts["format"] = (
        f"bestvideo[height<={quality}][vcodec^=avc1][ext=mp4]"
        f"+bestaudio[acodec^=mp4a][ext=m4a]/"
        f"bestvideo[height<={quality}][vcodec^=avc1]"
        f"+bestaudio[acodec^=mp4a]/"
        f"bestvideo[height<={quality}]"
        f"+bestaudio/"
        f"best[height<={quality}]"
    )
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])
    path = find_file(user_id, video_id)
    if not path:
        raise FileNotFoundError(f"Файл не найден: {user_id}_{video_id}")
    return path


def download_mp3(url: str, user_id: int, video_id: str) -> str:
    opts = ytdlp_opts()
    opts["outtmpl"] = os.path.join(DOWNLOAD_DIR, f"{user_id}_{video_id}.%(ext)s")
    opts["format"] = "bestaudio/best"
    opts["postprocessors"] = [
        {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}]
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])
    path = os.path.join(DOWNLOAD_DIR, f"{user_id}_{video_id}.mp3")
    if not os.path.exists(path):
        path = find_file(user_id, video_id)
    if not path:
        raise FileNotFoundError("MP3 не найден")
    return path


# ─────────────────────────────────────────────
# ОБРАБОТКА ВИДЕО
# ─────────────────────────────────────────────
def process_video(url: str, quality: str, user_id: int, video_id: str, duration: int) -> Tuple[str, Optional[str]]:
    src = download_video(url, quality, user_id, video_id)
    info = probe(src)
    log.info(f"[{user_id}] Probe: {info['width']}x{info['height']} "
             f"V={info['vcodec']} A={info['acodec']} {info['duration']}s {info['fps']}fps")
    dst = os.path.join(DOWNLOAD_DIR, f"{user_id}_{video_id}_out.mp4")
    fps = info["fps"] or 30
    if info["vcodec"] == "h264" and info["acodec"] in ("aac", "mp3"):
        log.info(f"[{user_id}] ⚡ Direct copy")
        cmd = ["ffmpeg", "-y", "-i", src, "-c:v", "copy", "-c:a", "copy",
               "-movflags", "+faststart", dst]
        ok, err = run_ffmpeg(cmd, dst)
    elif info["vcodec"] == "h264":
        log.info(f"[{user_id}] 🎵 Video copy, audio → AAC")
        cmd = ["ffmpeg", "-y", "-i", src, "-c:v", "copy",
               "-c:a", "aac", "-b:a", "128k", "-ar", "44100",
               "-movflags", "+faststart", dst]
        ok, err = run_ffmpeg(cmd, dst)
    else:
        log.info(f"[{user_id}] 🏎️ Transcode {info['vcodec']} → H.264 via {VIDEO_ENCODER}")
        ok, err = False, ""
        if VIDEO_ENCODER != "libx264":
            cmd = ffmpeg_transcode(src, dst, quality, VIDEO_ENCODER, fps)
            ok, err = run_ffmpeg(cmd, dst)
        if not ok:
            if VIDEO_ENCODER != "libx264":
                log.warning(f"[{user_id}] ⚠️ GPU failed → CPU fallback")
            if os.path.exists(dst):
                os.remove(dst)
            cmd = ffmpeg_cpu_fallback(src, dst, quality, fps)
            ok, err = run_ffmpeg(cmd, dst)
        if not ok:
            raise RuntimeError(f"FFmpeg: {err[-300:]}")
    try:
        os.remove(src)
    except Exception:
        pass
    return dst, make_thumb(user_id, video_id)


def make_thumb(user_id: int, video_id: str) -> Optional[str]:
    prefix = f"{user_id}_{video_id}."
    raw = None
    for f in os.listdir(DOWNLOAD_DIR):
        if f.startswith(prefix) and f.endswith((".jpg", ".webp", ".png")) and "_thumb" not in f:
            raw = os.path.join(DOWNLOAD_DIR, f)
            break
    if not raw:
        return None
    thumb = os.path.join(DOWNLOAD_DIR, f"{user_id}_{video_id}_thumb.jpg")
    subprocess.run(["ffmpeg", "-y", "-i", raw, "-vf", "scale=320:-1", "-q:v", "5", thumb],
                   capture_output=True)
    try:
        os.remove(raw)
    except Exception:
        pass
    return thumb if os.path.exists(thumb) else None


# ─────────────────────────────────────────────
# ЗАГРУЗКА В TELEGRAM
# ─────────────────────────────────────────────
async def upload_file(client: TelegramClient, path: str, progress_cb=None) -> types.InputFileBig:
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
            try:
                idx = queue.get_nowait()
            except asyncio.QueueEmpty:
                break
            f.seek(idx * chunk)
            data = f.read(chunk)
            for attempt in range(4):
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
# СОСТОЯНИЕ БОТА
# ─────────────────────────────────────────────
bot: Optional[TelegramClient] = None
user_client: Optional[TelegramClient] = None
video_meta: Dict[str, dict] = {}
is_premium = False
bot_username = ""
owner_id = 0


# ═══════════════════════════════════════════════
# ХЕНДЛЕРЫ
# ═══════════════════════════════════════════════
def setup_handlers(client: TelegramClient):

    def is_admin(event) -> bool:
        return owner_id != 0 and event.sender_id == owner_id

    @client.on(events.NewMessage(pattern=r"^/start$"))
    async def cmd_start(event):
        db.register_user(event.sender_id, event.sender.username or "")
        limit = "4 ГБ 💎" if is_premium else "2 ГБ"
        await event.respond(
            "👋 **Привет! Я YouTube Monster Bot.**\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "💬 **Как пользоваться:**\n"
            "1️⃣ Кинь ссылку на видео / Shorts / плейлист\n"
            "2️⃣ Выбери качество кнопками\n"
            "3️⃣ Получи видео прямо в чат!\n\n"
            "⚡ **Кэш** — мгновенная отправка (0 сек)\n"
            f"🛡 **Лимит файла:** {limit}\n"
            "━━━━━━━━━━━━━━━━━━━━")

    @client.on(events.NewMessage(pattern=r"^/admin$"))
    async def cmd_admin(event):
        if not is_admin(event):
            return await event.respond("❌ Недостаточно прав.")
        s = db.stats()
        await event.respond(
            "👑 **ПАНЕЛЬ АДМИНИСТРАТОРА**\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"👥 Юзеров: `{s['users']}`\n"
            f"🎬 Скачано: `{s['videos']}`\n"
            f"💾 Трафик: `{s['gb']:.2f} ГБ`\n"
            f"⚡ Кэш: `{s['cache']}` файлов\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"⚙️ Кодек: `{VIDEO_ENCODER}`\n"
            f"💎 Premium: `{'Да (4 ГБ)' if is_premium else 'Нет (2 ГБ)'}`\n"
            f"👑 Админ ID: `{owner_id}`\n\n"
            "**Команды:**\n"
            "`/users` — список юзеров (со ссылками)\n"
            "`/whitelist` — белый список (4 ГБ)\n"
            "`/addpremium <ID>` — добавить в белый список\n"
            "`/delpremium <ID>` — убрать из белого списка\n"
            "`/ban <ID>` — бан\n"
            "`/unban <ID>` — разбан\n"
            "`/broadcast <текст>` — рассылка")

    @client.on(events.NewMessage(pattern=r"^/users$"))
    async def cmd_users(event):
        if not is_admin(event):
            return await event.respond("❌ Недостаточно прав.")
        users = db.get_users_list(50)
        if not users:
            return await event.respond("📭 В базе пока нет пользователей.")
        lines = ["👥 <b>Последние 50 пользователей:</b>\n"]
        for i, (uid, uname, banned, vids) in enumerate(users, 1):
            status = "⛔" if banned else "✅"
            star = " 💎" if uid in PREMIUM_USERS else ""
            lines.append(f"{status} {i}. {user_link(uid, uname)} — 🎬 {vids}{star}")
        await event.respond("\n".join(lines), parse_mode="html")

    @client.on(events.NewMessage(pattern=r"^/whitelist$"))
    async def cmd_whitelist(event):
        if not is_admin(event):
            return await event.respond("❌ Недостаточно прав.")
        if not PREMIUM_USERS:
            return await event.respond("📭 Белый список пуст.")
        lines = ["💎 <b>Белый список (лимит 4 ГБ):</b>\n"]
        for uid in sorted(PREMIUM_USERS):
            lines.append(f"• {user_link(uid)} — <code>{uid}</code>")
        await event.respond("\n".join(lines), parse_mode="html")

    @client.on(events.NewMessage(pattern=r"^/addpremium (\d+)$"))
    async def cmd_addpremium(event):
        if not is_admin(event):
            return await event.respond("❌ Недостаточно прав.")
        uid = int(event.pattern_match.group(1))
        PREMIUM_USERS.add(uid)
        update_env("PREMIUM_USERS", ",".join(str(x) for x in sorted(PREMIUM_USERS)))
        await event.respond(f"✅ {user_link(uid)} добавлен в белый список (4 ГБ).", parse_mode="html")

    @client.on(events.NewMessage(pattern=r"^/delpremium (\d+)$"))
    async def cmd_delpremium(event):
        if not is_admin(event):
            return await event.respond("❌ Недостаточно прав.")
        uid = int(event.pattern_match.group(1))
        PREMIUM_USERS.discard(uid)
        update_env("PREMIUM_USERS", ",".join(str(x) for x in sorted(PREMIUM_USERS)))
        await event.respond(f"🗑 {user_link(uid)} убран из белого списка.", parse_mode="html")

    @client.on(events.NewMessage(pattern=r"^/ban (\d+)$"))
    async def cmd_ban(event):
        if not is_admin(event):
            return await event.respond("❌ Недостаточно прав.")
        uid = int(event.pattern_match.group(1))
        db.set_ban(uid, True)
        await event.respond(f"⛔ {user_link(uid)} заблокирован.", parse_mode="html")

    @client.on(events.NewMessage(pattern=r"^/unban (\d+)$"))
    async def cmd_unban(event):
        if not is_admin(event):
            return await event.respond("❌ Недостаточно прав.")
        uid = int(event.pattern_match.group(1))
        db.set_ban(uid, False)
        await event.respond(f"✅ {user_link(uid)} разблокирован.", parse_mode="html")

    @client.on(events.NewMessage(pattern=r"^/broadcast (.+)"))
    async def cmd_broadcast(event):
        if not is_admin(event):
            return await event.respond("❌ Недостаточно прав.")
        text = event.pattern_match.group(1)
        users = db.all_users()
        ok = 0
        msg = await event.respond(f"📣 Рассылка для {len(users)} юзеров...")
        for uid in users:
            try:
                await client.send_message(uid, f"🔔 **От админа:**\n\n{text}")
                ok += 1
                await asyncio.sleep(0.5)
            except Exception:
                pass
        await msg.edit(f"✅ Доставлено: `{ok}/{len(users)}`")

    @client.on(events.NewMessage(
        func=lambda e: bool(e.text) and not e.text.startswith("/") and bool(extract_url(e.text))))
    async def on_link(event):
        if db.is_banned(event.sender_id):
            return await event.respond("❌ Вы заблокированы.")
        db.register_user(event.sender_id, event.sender.username or "")
        url = extract_url(event.text)
        uid = event.sender_id

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
                    return await msg.edit("❌ Плейлист пуст или закрыт.")
                pl_id = info.get("id", f"pl_{random.getrandbits(32)}")
                video_meta[pl_id] = {
                    "title": info.get("title", "Плейлист"),
                    "uploader": info.get("uploader", "Unknown"),
                    "is_playlist": True, "ids": ids}
                kb = [
                    [Button.inline("🎬 1080p", f"dl:1080:{pl_id}"),
                     Button.inline("🎬 720p", f"dl:720:{pl_id}")],
                    [Button.inline("🎬 480p", f"dl:480:{pl_id}"),
                     Button.inline("🎬 360p", f"dl:360:{pl_id}")]]
                await msg.edit(
                    f"📚 **{info.get('title', 'Плейлист')}**\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"👤 {hashtag(info.get('uploader', ''))}\n"
                    f"🎞 Роликов: `{len(ids)}`\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"👇 *Выбери качество:*", buttons=kb)
            except Exception as e:
                await msg.edit(f"❌ Ошибка плейлиста:\n`{e}`")
            return

        msg = await event.respond("🔍 **Анализирую видео...**")
        try:
            opts = ytdlp_opts()
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
            if info.get("is_live"):
                return await msg.edit("❌ Прямые трансляции не поддерживаются.")
            vid = info["id"]
            title = info.get("title", "Без названия")
            uploader = info.get("uploader", "Unknown")
            duration = int(info.get("duration") or 0)
            heights = {f["height"] for f in info.get("formats", [])
                       if f.get("vcodec") != "none" and f.get("height")}
            video_meta[vid] = {
                "url": url, "title": title, "uploader": uploader,
                "duration": duration, "heights": sorted(heights, reverse=True)}
            buttons, row = [], []
            for h in [1080, 720, 480, 360]:
                if h in heights:
                    icon = "⚡" if db.get_cache(vid, str(h)) else "🎬"
                    row.append(Button.inline(f"{icon} {h}p", f"dl:{h}:{vid}"))
                    if len(row) == 2:
                        buttons.append(row); row = []
            if row:
                buttons.append(row)
            mp3_icon = "⚡" if db.get_cache(vid, "mp3") else "🎵"
            buttons.append([Button.inline(f"{mp3_icon} MP3", f"dl:mp3:{vid}")])
            await msg.edit(
                f"🎥 **{title}**\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"👤 {hashtag(uploader)}\n"
                f"⏱ `{timedelta(seconds=duration)}`\n"
                f"📐 Макс: `{max(heights) if heights else '?'}p`\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"👇 *Выбери формат:*", buttons=buttons)
        except Exception as e:
            await msg.edit(f"❌ Ошибка:\n`{e}`")

    @client.on(events.CallbackQuery(pattern=b"^dl:"))
    async def on_download(event):
        uid = event.sender_id
        parts = event.data.decode().split(":")
        quality, vid = parts[1], parts[2]
        meta = video_meta.get(vid)
        if not meta:
            return await event.answer("⚠️ Сессия устарела. Кинь ссылку заново.", alert=True)
        if meta.get("is_playlist"):
            kb = [
                [Button.inline("⚡ По 1", f"pl:1:{quality}:{vid}"),
                 Button.inline("🚀 По 3", f"pl:3:{quality}:{vid}")],
                [Button.inline("🔥 По 5", f"pl:5:{quality}:{vid}"),
                 Button.inline("💥 По 10", f"pl:10:{quality}:{vid}")]]
            await event.edit(
                f"📚 **{meta['title']}**\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"🎞 Роликов: `{len(meta['ids'])}`\n"
                f"📐 Качество: `{quality}p`\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"📦 *Сколько видео одновременно?*", buttons=kb)
            return
        await event.answer()
        q_label = "MP3 🎵" if quality == "mp3" else f"{quality}p 🎬"
        msg = await event.reply(f"⏳ **Запуск обработки...**\nКачество: `{q_label}`")
        cached = db.get_cache(vid, quality)
        if cached:
            try:
                await msg.edit("⚡ **Кэш найден! Мгновенная отправка...**")
                caption = f"🎬 **{meta['title']}**\n\n👤 {hashtag(meta['uploader'])}"
                await client.send_file(uid, cached, caption=caption)
                await msg.delete()
                db.add_stats(uid, 0)
                return
            except Exception:
                db.del_cache(vid, quality)
        try:
            if quality == "mp3":
                final = await asyncio.to_thread(download_mp3, meta["url"], uid, vid)
                thumb = None
            else:
                final, thumb = await asyncio.to_thread(
                    process_video, meta["url"], quality, uid, vid, meta["duration"])
            size_mb = os.path.getsize(final) / (1024 * 1024)
            has_premium = uid in PREMIUM_USERS and is_premium
            max_mb = 3950 if has_premium else 1950
            if size_mb > max_mb:
                await msg.edit(
                    f"❌ **Файл слишком большой**\n"
                    f"📦 Размер: `{size_mb:.0f} МБ`\n"
                    f"🛡 Лимит: `{max_mb} МБ`")
                await rm(final)
                if thumb:
                    await rm(thumb)
                return
            contour = "💎 Premium (4 ГБ)" if size_mb > 1950 else "📦 Standard (2 ГБ)"
            await msg.edit(f"⚙️ **Видео готово!**\n📤 Загрузка [{contour}]...")
            t0 = time.time()
            last_edit = [time.time()]
            last_text = [""]

            async def on_progress(cur, total):
                now = time.time()
                if now - last_edit[0] < 4:
                    return
                pct = cur / total * 100
                speed = cur / max(now - t0, 0.1)
                eta = (total - cur) / speed if speed > 0 else 0
                text = (
                    f"🚀 **Выгрузка в Telegram**\n\n"
                    f"📊 {progress_bar(pct)} **{pct:.0f}%**\n"
                    f"⚡ Скорость: **{speed / 1024 / 1024:.1f} МБ/с**\n"
                    f"⏳ Осталось: **{timedelta(seconds=int(eta))}**")
                if text == last_text[0]:
                    return
                last_text[0] = text
                last_edit[0] = now
                try:
                    await msg.edit(text)
                except Exception:
                    pass

            sender = user_client if (size_mb > 1950 and is_premium and user_client) else client
            uploaded = await upload_file(sender, final, on_progress if sender == client else None)
            await msg.edit("⚡ **Финализация...**")
            caption = f"🎬 **{meta['title']}**\n\n👤 {hashtag(meta['uploader'])}"
            attrs = []
            if quality == "mp3":
                attrs.append(DocumentAttributeAudio(duration=meta["duration"], title=meta["title"]))
            else:
                info = probe(final)
                attrs.append(DocumentAttributeVideo(
                    duration=info["duration"] or meta["duration"],
                    w=info["width"] or 1920, h=info["height"] or int(quality),
                    supports_streaming=True))
            sent = await sender.send_file(
                uid, uploaded, caption=caption, thumb=thumb,
                attributes=attrs, supports_streaming=True)
            if sender == client and sent and sent.document:
                try:
                    db.set_cache(vid, quality, utils.pack_bot_file_id(sent.document))
                except Exception:
                    pass
            db.add_stats(uid, size_mb)
            await rm(final)
            if thumb:
                await rm(thumb)
            await msg.delete()
            log.info(f"[{uid}] ✅ Готово: {size_mb:.1f} МБ")
        except Exception as e:
            log.error(f"[{uid}] Ошибка: {e}", exc_info=True)
            await msg.edit(f"❌ **Ошибка:**\n`{str(e)[:200]}`")
            for f in os.listdir(DOWNLOAD_DIR):
                if f.startswith(f"{uid}_"):
                    await rm(os.path.join(DOWNLOAD_DIR, f))

    @client.on(events.CallbackQuery(pattern=b"^pl:"))
    async def on_playlist(event):
        uid = event.sender_id
        parts = event.data.decode().split(":")
        batch, quality, pl_id = int(parts[1]), parts[2], parts[3]
        meta = video_meta.get(pl_id)
        if not meta or not meta.get("is_playlist"):
            return await event.answer("⚠️ Сессия устарела.", alert=True)
        ids = meta["ids"]
        total = len(ids)
        await event.edit(
            f"📚 **{meta['title']}**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🎞 Всего: `{total}` | Пачки по `{batch}`\n"
            f"📐 Качество: `{quality}p`\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"⏳ *Обрабатываю...*")
        for i in range(0, total, batch):
            chunk = ids[i:i + batch]
            tasks = [process_playlist_item(vid, quality, uid, delay=j * 1.5)
                     for j, vid in enumerate(chunk)]
            await asyncio.gather(*tasks)
        await client.send_message(uid, f"✅ **Плейлист обработан!**\n🎞 `{total}` видео доставлено.")

    async def process_playlist_item(vid: str, quality: str, uid: int, delay: float = 0):
        if delay:
            await asyncio.sleep(delay)
        url = f"https://www.youtube.com/watch?v={vid}"
        try:
            opts = ytdlp_opts()
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
            title = info.get("title", vid)
            uploader = info.get("uploader", "Unknown")
            duration = int(info.get("duration") or 0)
        except Exception as e:
            log.error(f"[{uid}] Meta error {vid}: {e}")
            return
        caption = f"🎬 **{title}**\n\n👤 {hashtag(uploader)}"
        cached = db.get_cache(vid, quality)
        if cached:
            try:
                await client.send_file(uid, cached, caption=caption)
                return
            except Exception:
                db.del_cache(vid, quality)
        status = await client.send_message(uid, f"📥 **Обработка:**\n`{title[:60]}`")
        try:
            final, thumb = await asyncio.to_thread(process_video, url, quality, uid, vid, duration)
            size_mb = os.path.getsize(final) / (1024 * 1024)
            max_mb = 3950 if (uid in PREMIUM_USERS and is_premium) else 1950
            if size_mb > max_mb:
                await status.edit(f"❌ `{title[:40]}`: {size_mb:.0f} МБ > лимит")
                await rm(final)
                if thumb:
                    await rm(thumb)
                return
            info = probe(final)
            attrs = [DocumentAttributeVideo(
                duration=info["duration"] or duration,
                w=info["width"] or 1280, h=info["height"] or int(quality),
                supports_streaming=True)]
            sender = user_client if (size_mb > 1950 and is_premium and user_client) else client
            uploaded = await upload_file(sender, final)
            sent = await sender.send_file(
                uid, uploaded, caption=caption, thumb=thumb,
                attributes=attrs, supports_streaming=True)
            if sender == client and sent and sent.document:
                try:
                    db.set_cache(vid, quality, utils.pack_bot_file_id(sent.document))
                except Exception:
                    pass
            db.add_stats(uid, size_mb)
            await rm(final)
            if thumb:
                await rm(thumb)
            await status.delete()
        except Exception as e:
            log.error(f"[{uid}] Playlist {vid}: {e}")
            await status.edit(f"❌ Ошибка: `{str(e)[:100]}`")
            for f in os.listdir(DOWNLOAD_DIR):
                if f.startswith(f"{uid}_{vid}"):
                    await rm(os.path.join(DOWNLOAD_DIR, f))

# ═══════════════════════════════════════════════
# КОНСОЛЬНОЕ МЕНЮ
# ═══════════════════════════════════════════════
BANNER = r"""
========================================================================
     __  __                  _             ____         _
    |  \/  | ___  _ __  ___ | |_ ___ _ __ | __ )  ___  | |_
    | |\/| |/ _ \| '_ \/ __|| __/ _ \ '__||  _ \ / _ \ | __|
    | |  | | (_) | | | \__ \| ||  __/ |   | |_) | (_) || |_
    |_|  |_|\___/|_| |_|___/ \__\___|_|   |____/ \___/  \__|

          === YOUTUBE MONSTER BOT (ULTIMATE EDITION) ===
========================================================================
"""

CODECS = {"1": "libx264", "2": "h264_amf", "3": "h264_nvenc", "4": "h264_qsv"}
CODEC_NAMES = {
    "libx264": "libx264 (CPU, универсальный)",
    "h264_amf": "h264_amf (AMD Radeon)",
    "h264_nvenc": "h264_nvenc (NVIDIA)",
    "h264_qsv": "h264_qsv (Intel QuickSync)",
}
COOKIES = {"1": "chrome", "2": "firefox", "3": "edge", "4": "brave", "0": ""}


def _clear():
    os.system('cls' if os.name == 'nt' else 'clear')


def _pause():
    input("\n  ⏎  Нажмите Enter, чтобы вернуться в меню...")


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
        print(BANNER)
        has_session = os.path.exists("user_session.session")
        ub_state = "ВКЛЮЧЕН" if USE_USERBOT else "ВЫКЛЮЧЕН"
        ub_note = " (сессия есть ✅)" if (USE_USERBOT and has_session) else \
                  (" (сессии нет — запрошу при старте)" if USE_USERBOT else "")
        admin_state = f"ID {OWNER_ID}" if OWNER_ID else "НЕ ЗАДАН ⚠️"
        print("  ПАНЕЛЬ УПРАВЛЕНИЯ БОТОМ\n")
        print(f"  [1] ▶️  ЗАПУСТИТЬ БОТА")
        print(f"  [2] 💎 Premium-юзербот (4 ГБ):     [{ub_state}]{ub_note}")
        print(f"  [3] 🎥 Видеокодек:                 [{CODEC_NAMES.get(VIDEO_ENCODER, VIDEO_ENCODER)}]")
        print(f"  [4] 🌐 Прокси Happ/VPN:            [{'ВКЛЮЧЕН' if USE_PROXY else 'ВЫКЛЮЧЕН'}]")
        print(f"  [5] 📦 Пачка плейлиста:            [по {DEFAULT_BATCH} видео]")
        print(f"  [6] 🍪 Куки браузера:              [{BROWSER_COOKIES or 'выключены'}]")
        print(f"  [7] ⚡ Быстрый запуск (без меню):  [{'ВКЛЮЧЕН' if QUICK_START else 'ВЫКЛЮЧЕН'}]")
        print(f"  [8] 🗑️  Сбросить Premium-сессию")
        print(f"  [9] 👑 ID администратора:          [{admin_state}]")
        print(f"  [0] ❌ Выход")
        print("========================================================================")
        choice = input("  👉 Выберите пункт (0-9): ").strip()

        if choice == "1":
            return True
        elif choice == "2":
            USE_USERBOT = not USE_USERBOT
            update_env("USE_USERBOT", str(USE_USERBOT).lower())
            if USE_USERBOT and not has_session:
                print("\n  ℹ️  Premium включён. Сессии пока нет — это нормально.")
                print("     При запуске (пункт 1) Telegram прямо в этом окне")
                print("     попросит номер телефона и код подтверждения.")
            elif USE_USERBOT and has_session:
                print("\n  ✅ Premium активен, сессия на месте.")
            else:
                print("\n  📦 Premium выключен. Бот работает в режиме 2 ГБ.")
            _pause()
        elif choice == "3":
            print("\n  Доступные кодеки:")
            print("    1. libx264    — программный, на CPU (работает везде)")
            print("    2. h264_amf   — аппаратный, AMD Radeon (RX 6600 и др.)")
            print("    3. h264_nvenc — аппаратный, NVIDIA GeForce")
            print("    4. h264_qsv   — аппаратный, Intel QuickSync")
            enc = input("\n  👉 Номер кодека (1-4): ").strip()
            if enc in CODECS:
                VIDEO_ENCODER = CODECS[enc]
                update_env("VIDEO_ENCODER", VIDEO_ENCODER)
                print(f"\n  ✅ Кодек установлен: {CODEC_NAMES[VIDEO_ENCODER]}")
            else:
                print("\n  ⚠️ Неверный номер, не меняю.")
            _pause()
        elif choice == "4":
            USE_PROXY = not USE_PROXY
            update_env("USE_PROXY", str(USE_PROXY).lower())
            print(f"\n  🌐 Прокси {'ВКЛЮЧЕН (' + PROXY_HOST + ':' + str(PROXY_PORT) + ')' if USE_PROXY else 'ВЫКЛЮЧЕН'}.")
            _pause()
        elif choice == "5":
            n = input("\n  👉 Сколько видео в пачке (1, 3, 5, 10): ").strip()
            if n.isdigit() and int(n) > 0:
                DEFAULT_BATCH = int(n)
                update_env("DEFAULT_BATCH_SIZE", str(DEFAULT_BATCH))
                print(f"\n  ✅ Пачка плейлиста: по {DEFAULT_BATCH} видео.")
            else:
                print("\n  ⚠️ Нужно число больше нуля.")
            _pause()
        elif choice == "6":
            print("\n  Куки нужны для обхода JS-проверок YouTube и возрастных видео.")
            print("    1. Chrome    2. Firefox    3. Edge    4. Brave    0. Выключить")
            c = input("\n  👉 Номер браузера (0-4): ").strip()
            if c in COOKIES:
                BROWSER_COOKIES = COOKIES[c]
                update_env("BROWSER_COOKIES", BROWSER_COOKIES)
                print(f"\n  ✅ Куки: {BROWSER_COOKIES or 'выключены'}.")
            else:
                print("\n  ⚠️ Неверный номер.")
            _pause()
        elif choice == "7":
            QUICK_START = not QUICK_START
            update_env("QUICK_START", str(QUICK_START).lower())
            if QUICK_START:
                print("\n  ⚡ Быстрый запуск ВКЛЮЧЕН.")
                print("     В следующий раз бот стартует сразу, без меню.")
                print("     Открыть меню позже:  python bot.py menu")
                print("     (или любая клавиша в окне быстрого старта за 5 сек).")
            else:
                print("\n   Быстрый запуск ВЫКЛЮЧЕН — меню будет каждый раз.")
            _pause()
        elif choice == "8":
            removed = 0
            for f in ("user_session.session", "user_session.session-journal"):
                if os.path.exists(f):
                    try:
                        os.remove(f); removed += 1
                    except Exception as e:
                        print(f"  ⚠️ Не удалось удалить {f}: {e}")
            print("\n  ✅ Premium-сессия сброшена." if removed else "\n  ℹ️  Сессии не было — сбрасывать нечего.")
            _pause()
        elif choice == "9":
            print("\n  👑 ID администратора — это ваш Telegram ID.")
            print("     Узнать: напишите боту @userinfobot или @getmyid_bot.")
            print(f"     Текущий: {OWNER_ID or 'не задан'}")
            v = input("\n  👉 Введите ID (число) или Enter чтобы оставить: ").strip()
            if v == "":
                print("\n  ℹ️  Не меняю.")
            elif v.isdigit() and int(v) > 0:
                OWNER_ID = int(v)
                update_env("OWNER_ID", str(OWNER_ID))
                print(f"\n  ✅ ID администратора: {OWNER_ID}")
            else:
                print("\n  ⚠️ Нужно число.")
            _pause()
        elif choice == "0":
            _clear()
            print("\n  👋 Всего доброго!\n")
            return False
        else:
            print("\n  ⚠️ Неверный пункт.")
            _pause()


# ═══════════════════════════════════════════════
# ЗАПУСК БОТА
# ═══════════════════════════════════════════════
async def start_bot():
    global bot, user_client, is_premium, bot_username, owner_id

    proxy = (socks.SOCKS5, PROXY_HOST, PROXY_PORT) if USE_PROXY else None
    bot = TelegramClient("bot_session", API_ID, API_HASH, proxy=proxy)
    await bot.start(bot_token=BOT_TOKEN)
    me = await bot.get_me()
    bot_username = me.username
    log.info(f"🤖 Бот: @{bot_username}")

    if USE_USERBOT:
        user_client = TelegramClient("user_session", API_ID, API_HASH, proxy=proxy)
        await user_client.start()
        ume = await user_client.get_me()
        if owner_id == 0:
            owner_id = ume.id  # fallback: владелец юзербота = админ
        is_premium = getattr(ume, "premium", False)
        PREMIUM_USERS.add(owner_id)
        log.info(f"👤 Userbot: {ume.first_name} | Premium={'✅' if is_premium else '❌'}")
        log.info("🚀 Dual-contour активен (бот + юзербот, лимит 4 ГБ)")
    else:
        log.info("📦 Режим Standard (2 ГБ). Premium-юзербот выключен в меню.")

    if owner_id == 0:
        log.warning("⚠️ OWNER_ID не задан! Админ-команды (/admin, /users, /ban...) НЕ БУДУТ работать.")
        log.warning("   Задайте ID админа в меню (пункт 9) или пропишите OWNER_ID в .env")
    else:
        log.info(f"👑 Администратор: {owner_id}")

    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        log.info(f"✅ FFmpeg OK | Кодек: {VIDEO_ENCODER}")
    except FileNotFoundError:
        log.critical("❌ FFmpeg не найден в PATH!")
        sys.exit(1)

    setup_handlers(bot)
    log.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    log.info("🟢 БОТ ЗАПУЩЕН. Жду ссылки...")
    log.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    await bot.run_until_disconnected()


# ═══════════════════════════════════════════════
# ТОЧКА ВХОДА
# ═══════════════════════════════════════════════
if __name__ == "__main__":
    force_menu = any(a in ("menu", "--menu", "-m", "config", "--config") for a in sys.argv[1:])
    if QUICK_START and not force_menu:
        print(BANNER)
        print("  ⚡  БЫСТРЫЙ ЗАПУСК — старт через 5 секунд...")
        print("     (нажмите ЛЮБУЮ клавишу сейчас, чтобы открыть меню настроек)")
        print("     или запустите позже с меню:  python bot.py menu")
        print("========================================================================")
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
        print("\n👋 Бот остановлен. Всего доброго!")
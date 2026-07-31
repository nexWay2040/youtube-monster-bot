"""
YouTube → Telegram Bot
Стек: Telethon + yt-dlp + FFmpeg (h264_amf) + SQLite3
ОС: Windows, AMD RX 6600
"""

import os
import re
import sys
import json
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
from dotenv import load_dotenv

# ─────────────────────────────────────────────
# КОНФИГ
# ─────────────────────────────────────────────
load_dotenv()

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "./downloads")
VIDEO_ENCODER = os.getenv("VIDEO_ENCODER", "h264_amf")
BROWSER_COOKIES = os.getenv("BROWSER_COOKIES", "")  # "chrome", "firefox", ""
USE_PROXY = os.getenv("USE_PROXY", "false").lower() == "true"
PROXY_HOST = os.getenv("PROXY_HOST", "127.0.0.1")
PROXY_PORT = int(os.getenv("PROXY_PORT", "10808"))
PREMIUM_USERS: Set[int] = {
    int(x.strip()) for x in os.getenv("PREMIUM_USERS", "").split(",") if x.strip().isdigit()
}
DEFAULT_BATCH = int(os.getenv("DEFAULT_BATCH_SIZE", "3"))

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
                is_banned INTEGER DEFAULT 0,
                total_videos INTEGER DEFAULT 0,
                total_mb REAL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS cache (
                video_id TEXT,
                quality TEXT,
                file_id TEXT,
                PRIMARY KEY (video_id, quality)
            );
        """)
        self.conn.commit()

    def register_user(self, uid: int, uname: str = ""):
        self.c.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?,?)", (uid, uname))
        self.conn.commit()

    def is_banned(self, uid: int) -> bool:
        self.c.execute("SELECT is_banned FROM users WHERE user_id=?", (uid,))
        row = self.c.fetchone()
        return bool(row[0]) if row else False

    def set_ban(self, uid: int, banned: bool):
        self.c.execute("UPDATE users SET is_banned=? WHERE user_id=?", (int(banned), uid))
        self.conn.commit()

    def add_stats(self, uid: int, mb: float):
        self.c.execute("UPDATE users SET total_videos=total_videos+1, total_mb=total_mb+? WHERE user_id=?", (mb, uid))
        self.conn.commit()

    def get_cache(self, vid: str, quality: str) -> Optional[str]:
        self.c.execute("SELECT file_id FROM cache WHERE video_id=? AND quality=?", (vid, quality))
        row = self.c.fetchone()
        return row[0] if row else None

    def set_cache(self, vid: str, quality: str, file_id: str):
        self.c.execute("INSERT OR REPLACE INTO cache (video_id, quality, file_id) VALUES (?,?,?)", (vid, quality, file_id))
        self.conn.commit()

    def del_cache(self, vid: str, quality: str):
        self.c.execute("DELETE FROM cache WHERE video_id=? AND quality=?", (vid, quality))
        self.conn.commit()

    def all_users(self) -> List[int]:
        self.c.execute("SELECT user_id FROM users WHERE is_banned=0")
        return [r[0] for r in self.c.fetchall()]

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


def progress_bar(pct: float, length=12) -> str:
    filled = int(length * pct / 100)
    return f"[{'█' * filled}{'░' * (length - filled)}] {pct:.0f}%"


def extract_url(text: str) -> Optional[str]:
    m = re.search(r'(https?://(?:www\.)?youtu(?:be\.com/watch\?v=|\.be/|be\.com/shorts/|be\.com/playlist\?list=)[^\s]+)', text)
    return m.group(1) if m else None


def hashtag(name: str) -> str:
    clean = re.sub(r'[^\w\s]', '', name or '').strip()
    return '#' + re.sub(r'\s+', '_', clean).lower() if clean else '#unknown'


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
    """Возвращает {width, height, duration, fps, vcodec, acodec}"""
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
        log.error(f"ffprobe error: {e}")
    return result


# ─────────────────────────────────────────────
# FFmpeg: ПРАВИЛЬНЫЕ КОМАНДЫ
# ─────────────────────────────────────────────

# Сетка битрейтов. maxrate = target × 1.6, bufsize = maxrate × 2
# Это даёт энкодеру запас на динамичные сцены без макроблокинга.
BITRATES = {
    "1080": {"target": "4500k", "max": "7000k", "buf": "14000k"},
    "720":  {"target": "2800k", "max": "4500k", "buf": "9000k"},
    "480":  {"target": "1200k", "max": "2000k", "buf": "4000k"},
    "360":  {"target": "700k",  "max": "1200k", "buf": "2400k"},
}


def ffmpeg_transcode(src: str, dst: str, quality: str, encoder: str, fps: int = 30) -> List[str]:
    """
    Строит команду транскодирования.
    Для AMF: VBR + balanced + high profile + большой bufsize.
    """
    cfg = BITRATES.get(quality, BITRATES["720"])
    gop = fps * 2  # GOP = 2 секунды

    cmd = ["ffmpeg", "-y"]

    # Аппаратное декодирование входа (VP9/AV1 → DXVA)
    if "amf" in encoder or "nvenc" in encoder:
        cmd += ["-hwaccel", "d3d11va"]

    cmd += ["-i", src]

    if "amf" in encoder:
        cmd += [
            "-c:v", "h264_amf",
            "-rc", "vbr",
            "-b:v", cfg["target"],
            "-maxrate", cfg["max"],
            "-bufsize", cfg["buf"],
            "-quality", "balanced",       # НЕ speed!
            "-profile", "high",
            "-level", "4.2",
            "-g", str(gop),
            "-bf", "3",
            "-header_insertion_mode", "gop",
            "-pix_fmt", "yuv420p",
        ]
    elif "nvenc" in encoder:
        cmd += [
            "-c:v", "h264_nvenc",
            "-rc", "vbr",
            "-b:v", cfg["target"],
            "-maxrate", cfg["max"],
            "-bufsize", cfg["buf"],
            "-preset", "p5",
            "-tune", "hq",
            "-profile", "high",
            "-spatial_aq", "1",
            "-temporal_aq", "1",
            "-g", str(gop),
            "-bf", "3",
            "-pix_fmt", "yuv420p",
        ]
    elif "qsv" in encoder:
        cmd += [
            "-c:v", "h264_qsv",
            "-b:v", cfg["target"],
            "-maxrate", cfg["max"],
            "-bufsize", cfg["buf"],
            "-preset", "medium",
            "-profile", "high",
            "-g", str(gop),
            "-bf", "3",
            "-look_ahead", "1",
            "-pix_fmt", "yuv420p",
        ]
    else:  # libx264 CPU
        cmd += [
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "21",
            "-profile", "high",
            "-maxrate", cfg["max"],
            "-bufsize", cfg["buf"],
            "-g", str(gop),
            "-bf", "3",
            "-pix_fmt", "yuv420p",
        ]

    cmd += [
        "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-ac", "2",
        "-movflags", "+faststart",
        dst,
    ]
    return cmd


def ffmpeg_cpu_fallback(src: str, dst: str, quality: str, fps: int = 30) -> List[str]:
    cfg = BITRATES.get(quality, BITRATES["720"])
    gop = fps * 2
    return [
        "ffmpeg", "-y", "-i", src,
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
        "-profile", "high",
        "-maxrate", cfg["max"], "-bufsize", cfg["buf"],
        "-g", str(gop), "-bf", "3",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k", "-ar", "44100",
        "-movflags", "+faststart",
        dst,
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
# YT-DLP: СКАЧИВАНИЕ
# ─────────────────────────────────────────────

def ytdlp_base_opts() -> dict:
    """Базовые опции yt-dlp, общие для всех вызовов."""
    opts = {
        "quiet": True,
        "no_warnings": True,
        "retries": 10,
        "fragment_retries": 10,
        "concurrent_fragment_downloads": 4,
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
    """
    Скачивает видео через yt-dlp.
    Формат: приоритет H.264 (для copy), fallback VP9/AV1 (для транскода).
    Возвращает путь к скачанному файлу.
    """
    opts = ytdlp_base_opts()
    opts["outtmpl"] = os.path.join(DOWNLOAD_DIR, f"{user_id}_{video_id}.%(ext)s")
    opts["writethumbnail"] = True
    opts["merge_output_format"] = "mp4"

    # Каскад:
    # 1) H.264 + AAC в MP4 → можно сделать copy
    # 2) H.264 + AAC (любой контейнер)
    # 3) Лучшее видео нужного роста (VP9/AV1) + лучшее аудио → транскод
    # 4) Единый поток
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
        raise FileNotFoundError(f"Файл не найден после скачивания: {user_id}_{video_id}")
    return path


def download_mp3(url: str, user_id: int, video_id: str) -> str:
    opts = ytdlp_base_opts()
    opts["outtmpl"] = os.path.join(DOWNLOAD_DIR, f"{user_id}_{video_id}.%(ext)s")
    opts["format"] = "bestaudio/best"
    opts["postprocessors"] = [
        {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}
    ]
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])

    path = os.path.join(DOWNLOAD_DIR, f"{user_id}_{video_id}.mp3")
    if not os.path.exists(path):
        path = find_file(user_id, video_id)
    if not path:
        raise FileNotFoundError("MP3 не найден после конвертации")
    return path


# ─────────────────────────────────────────────
# ОБРАБОТКА ВИДЕО (СКАЧАТЬ + ТРАНСКОД)
# ─────────────────────────────────────────────

def process_video(url: str, quality: str, user_id: int, video_id: str, duration: int) -> Tuple[str, Optional[str]]:
    """
    Полный пайплайн: скачать → probe → copy/transcode → вернуть путь.
    Возвращает (путь_к_видео, путь_к_превью).
    """
    # 1. Скачиваем
    src = download_video(url, quality, user_id, video_id)
    info = probe(src)
    log.info(f"[{user_id}] Probe: {info['width']}x{info['height']} "
             f"V={info['vcodec']} A={info['acodec']} {info['duration']}s {info['fps']}fps")

    dst = os.path.join(DOWNLOAD_DIR, f"{user_id}_{video_id}_out.mp4")
    fps = info["fps"] or 30

    # 2. Определяем стратегию
    if info["vcodec"] == "h264" and info["acodec"] in ("aac", "mp3"):
        # Direct copy — мгновенно
        log.info(f"[{user_id}] Direct copy (H.264+AAC уже)")
        cmd = ["ffmpeg", "-y", "-i", src, "-c:v", "copy", "-c:a", "copy",
               "-movflags", "+faststart", dst]
        ok, err = run_ffmpeg(cmd, dst)

    elif info["vcodec"] == "h264":
        # Видео OK, аудио надо конвертировать
        log.info(f"[{user_id}] Video copy, audio → AAC")
        cmd = ["ffmpeg", "-y", "-i", src, "-c:v", "copy",
               "-c:a", "aac", "-b:a", "128k", "-ar", "44100",
               "-movflags", "+faststart", dst]
        ok, err = run_ffmpeg(cmd, dst)

    else:
        # Полное перекодирование (VP9 / AV1 / VP8)
        log.info(f"[{user_id}] Transcode {info['vcodec']} → H.264 via {VIDEO_ENCODER}")
        ok, err = False, ""

        if VIDEO_ENCODER != "libx264":
            cmd = ffmpeg_transcode(src, dst, quality, VIDEO_ENCODER, fps)
            ok, err = run_ffmpeg(cmd, dst)

        if not ok:
            if VIDEO_ENCODER != "libx264":
                log.warning(f"[{user_id}] GPU failed, fallback to CPU")
            if os.path.exists(dst):
                os.remove(dst)
            cmd = ffmpeg_cpu_fallback(src, dst, quality, fps)
            ok, err = run_ffmpeg(cmd, dst)

        if not ok:
            raise RuntimeError(f"FFmpeg не справился: {err[-300:]}")

    # 3. Удаляем исходник
    try:
        os.remove(src)
    except Exception:
        pass

    # 4. Превью
    thumb = make_thumb(user_id, video_id)

    return dst, thumb


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
# ЗАГРУЗКА В TELEGRAM (стриминг чанками)
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
                        file_id=file_id, file_part=idx, file_total_parts=parts, bytes=data
                    ))
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
# БОТ
# ─────────────────────────────────────────────

proxy = (socks.SOCKS5, PROXY_HOST, PROXY_PORT) if USE_PROXY else None
bot = TelegramClient("bot_session", API_ID, API_HASH, proxy=proxy)
user_client: Optional[TelegramClient] = None

# Кэш метаданных видео в памяти (video_id → info)
video_meta: Dict[str, dict] = {}

is_premium = False
bot_username = ""
owner_id = 0


def get_proxy_opts() -> dict:
    """Опции прокси/куки для yt-dlp."""
    o = {}
    if USE_PROXY:
        o["proxy"] = f"socks5://{PROXY_HOST}:{PROXY_PORT}"
    if BROWSER_COOKIES:
        o["cookiesfrombrowser"] = (BROWSER_COOKIES,)
    return o


# ── /start ──
@bot.on(events.NewMessage(pattern=r"^/start$"))
async def cmd_start(event):
    db.register_user(event.sender_id, event.sender.username or "")
    limit = "4 ГБ" if is_premium else "2 ГБ"
    await event.respond(
        f"👋 Привет! Кинь мне ссылку на YouTube видео или плейлист.\n\n"
        f"🛡 Лимит файла: {limit}"
    )


# ── /admin ──
@bot.on(events.NewMessage(pattern=r"^/admin$"))
async def cmd_admin(event):
    if event.sender_id != owner_id:
        return
    s = db.stats()
    await event.respond(
        f"📊 Статистика:\n"
        f"  Юзеры: {s['users']}\n"
        f"  Видео: {s['videos']}\n"
        f"  Трафик: {s['gb']:.2f} ГБ\n"
        f"  Кэш: {s['cache']} файлов\n\n"
        f"⚙️ Кодек: {VIDEO_ENCODER}\n"
        f"💎 Premium: {'да' if is_premium else 'нет'}"
    )


# ── Ссылка на видео/плейлист ──
@bot.on(events.NewMessage(func=lambda e: not e.text.startswith("/") if e.text else False))
async def on_link(event):
    if db.is_banned(event.sender_id):
        return await event.respond("❌ Вы заблокированы.")

    url = extract_url(event.text or "")
    if not url:
        return

    uid = event.sender_id

    # ── ПЛЕЙЛИСТ ──
    if "list=" in url:
        msg = await event.respond("📚 Сканирую плейлист...")
        try:
            opts = ytdlp_base_opts()
            opts["extract_flat"] = True
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)

            entries = info.get("entries", [])
            ids = [e["id"] for e in entries if e and e.get("id")]
            if not ids:
                return await msg.edit("❌ Плейлист пуст.")

            pl_id = info.get("id", f"pl_{random.getrandbits(32)}")
            video_meta[pl_id] = {
                "title": info.get("title", "Плейлист"),
                "uploader": info.get("uploader", "Unknown"),
                "is_playlist": True,
                "ids": ids,
            }

            kb = [
                [Button.inline("1080p", f"dl:1080:{pl_id}"), Button.inline("720p", f"dl:720:{pl_id}")],
                [Button.inline("480p", f"dl:480:{pl_id}"), Button.inline("360p", f"dl:360:{pl_id}")],
            ]
            await msg.edit(
                f"📚 **{info.get('title', 'Плейлист')}**\n"
                f"Роликов: {len(ids)}\n\nВыбери качество:",
                buttons=kb
            )
        except Exception as e:
            await msg.edit(f"❌ Ошибка: {e}")
        return

    # ── ОДИНОЧНОЕ ВИДЕО ──
    msg = await event.respond("🔍 Получаю информацию...")
    try:
        opts = ytdlp_base_opts()
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)

        if info.get("is_live"):
            return await msg.edit("❌ Прямые трансляции не поддерживаются.")

        vid = info["id"]
        title = info.get("title", "Без названия")
        uploader = info.get("uploader", "Unknown")
        duration = int(info.get("duration") or 0)

        heights = set()
        for f in info.get("formats", []):
            if f.get("vcodec") != "none" and f.get("height"):
                heights.add(f["height"])

        video_meta[vid] = {
            "url": url, "title": title, "uploader": uploader,
            "duration": duration, "heights": sorted(heights, reverse=True),
        }

        # Кнопки
        buttons = []
        row = []
        for h in [1080, 720, 480, 360]:
            if h in heights:
                cached = "⚡" if db.get_cache(vid, str(h)) else "🎬"
                row.append(Button.inline(f"{cached} {h}p", f"dl:{h}:{vid}"))
                if len(row) == 2:
                    buttons.append(row)
                    row = []
        if row:
            buttons.append(row)

        cached_mp3 = "⚡" if db.get_cache(vid, "mp3") else "🎵"
        buttons.append([Button.inline(f"{cached_mp3} MP3", f"dl:mp3:{vid}")])

        await msg.edit(
            f"🎥 **{title}**\n"
            f"👤 {hashtag(uploader)}\n"
            f"⏱ {timedelta(seconds=duration)}\n\n"
            f"Выбери формат:",
            buttons=buttons
        )
    except Exception as e:
        await msg.edit(f"❌ Ошибка: {e}")


# ── Callback: скачивание ──
@bot.on(events.CallbackQuery(pattern=b"^dl:"))
async def on_download(event):
    uid = event.sender_id
    parts = event.data.decode().split(":")
    quality, vid = parts[1], parts[2]

    meta = video_meta.get(vid)
    if not meta:
        return await event.answer("Сессия устарела, кинь ссылку заново.", alert=True)

    # ── Плейлист: выбор пачки ──
    if meta.get("is_playlist"):
        kb = [
            [Button.inline("По 1", f"pl:1:{quality}:{vid}"), Button.inline("По 3", f"pl:3:{quality}:{vid}")],
            [Button.inline("По 5", f"pl:5:{quality}:{vid}"), Button.inline("По 10", f"pl:10:{quality}:{vid}")],
        ]
        await event.edit(
            f"📚 {meta['title']}\nРоликов: {len(meta['ids'])}\nКачество: {quality}p\n\n"
            f"Сколько видео обрабатывать одновременно?",
            buttons=kb
        )
        return

    await event.answer()
    msg = await event.reply(f"⏳ Обрабатываю {quality}p...")

    # Кэш
    cached = db.get_cache(vid, quality)
    if cached:
        try:
            caption = f"🎬 {meta['title']}\n👤 {hashtag(meta['uploader'])}"
            await bot.send_file(uid, cached, caption=caption)
            await msg.delete()
            return
        except Exception:
            db.del_cache(vid, quality)

    # Скачивание + транскод
    try:
        if quality == "mp3":
            final = await asyncio.to_thread(download_mp3, meta["url"], uid, vid)
            thumb = None
        else:
            final, thumb = await asyncio.to_thread(
                process_video, meta["url"], quality, uid, vid, meta["duration"]
            )

        size_mb = os.path.getsize(final) / (1024 * 1024)
        max_mb = 3950 if (uid in PREMIUM_USERS and is_premium) else 1950

        if size_mb > max_mb:
            await msg.edit(f"❌ Файл {size_mb:.0f} МБ превышает лимит {max_mb} МБ.")
            await rm(final)
            if thumb:
                await rm(thumb)
            return

        # Загрузка
        t0 = time.time()
        await msg.edit(f"📤 Загрузка в Telegram ({size_mb:.0f} МБ)...")
        last_edit = [time.time()]
        last_text = [""]

        async def on_progress(cur, total):
            now = time.time()
            # Обновляем не чаще раза в 4 секунды
            if now - last_edit[0] < 4:
                return
            pct = cur / total * 100
            speed = cur / max(now - t0, 0.1)
            text = f"📤 {progress_bar(pct)} | {speed / 1024 / 1024:.1f} МБ/с"
            # Не редактируем, если текст не изменился
            if text == last_text[0]:
                return
            last_text[0] = text
            last_edit[0] = now
            try:
                await msg.edit(text)
            except Exception:
                pass  # MessageNotModified, FloodWait — игнорим

        sender = user_client if (size_mb > 1950 and is_premium and user_client) else bot
        uploaded = await upload_file(sender, final, on_progress if sender == bot else None)

        # Отправка
        caption = f"🎬 {meta['title']}\n👤 {hashtag(meta['uploader'])}"
        attrs = []
        if quality == "mp3":
            attrs.append(DocumentAttributeAudio(duration=meta["duration"], title=meta["title"]))
        else:
            info = probe(final)
            attrs.append(DocumentAttributeVideo(
                duration=info["duration"] or meta["duration"],
                w=info["width"] or 1920,
                h=info["height"] or int(quality),
                supports_streaming=True,
            ))

        sent = await sender.send_file(
            uid, uploaded, caption=caption, thumb=thumb,
            attributes=attrs, supports_streaming=True
        )

        # Кэш (только для бота, до 2 ГБ)
        if sender == bot and sent and sent.document:
            try:
                fid = utils.pack_bot_file_id(sent.document)
                db.set_cache(vid, quality, fid)
            except Exception:
                pass

        db.add_stats(uid, size_mb)
        await rm(final)
        if thumb:
            await rm(thumb)
        await msg.delete()
        log.info(f"[{uid}] Готово: {size_mb:.1f} МБ")

    except Exception as e:
        log.error(f"[{uid}] Ошибка: {e}", exc_info=True)
        await msg.edit(f"❌ Ошибка: {str(e)[:200]}")
        # Чистим файлы
        for f in os.listdir(DOWNLOAD_DIR):
            if f.startswith(f"{uid}_"):
                await rm(os.path.join(DOWNLOAD_DIR, f))


# ── Callback: плейлист ──
@bot.on(events.CallbackQuery(pattern=b"^pl:"))
async def on_playlist(event):
    uid = event.sender_id
    parts = event.data.decode().split(":")
    batch, quality, pl_id = int(parts[1]), parts[2], parts[3]

    meta = video_meta.get(pl_id)
    if not meta or not meta.get("is_playlist"):
        return await event.answer("Сессия устарела.", alert=True)

    ids = meta["ids"]
    await event.edit(f"📚 Обрабатываю {len(ids)} видео (пачки по {batch})...")

    for i in range(0, len(ids), batch):
        chunk = ids[i:i + batch]
        tasks = []
        for j, vid in enumerate(chunk):
            tasks.append(process_playlist_item(vid, quality, uid, delay=j * 1.5))
        await asyncio.gather(*tasks)

    await bot.send_message(uid, f"✅ Плейлист обработан ({len(ids)} видео).")


async def process_playlist_item(vid: str, quality: str, uid: int, delay: float = 0):
    if delay:
        await asyncio.sleep(delay)

    url = f"https://www.youtube.com/watch?v={vid}"

    # Метаданные
    try:
        opts = ytdlp_base_opts()
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
        title = info.get("title", vid)
        uploader = info.get("uploader", "Unknown")
        duration = int(info.get("duration") or 0)
    except Exception as e:
        log.error(f"[{uid}] Не удалось получить инфо для {vid}: {e}")
        return

    caption = f"🎬 {title}\n👤 {hashtag(uploader)}"

    # Кэш
    cached = db.get_cache(vid, quality)
    if cached:
        try:
            await bot.send_file(uid, cached, caption=caption)
            return
        except Exception:
            db.del_cache(vid, quality)

    # Обработка
    status = await bot.send_message(uid, f"📥 {title[:60]}...")
    try:
        final, thumb = await asyncio.to_thread(process_video, url, quality, uid, vid, duration)
        size_mb = os.path.getsize(final) / (1024 * 1024)

        max_mb = 3950 if (uid in PREMIUM_USERS and is_premium) else 1950
        if size_mb > max_mb:
            await status.edit(f"❌ {title[:40]}: {size_mb:.0f} МБ > лимит")
            await rm(final)
            if thumb:
                await rm(thumb)
            return

        info = probe(final)
        attrs = [DocumentAttributeVideo(
            duration=info["duration"] or duration,
            w=info["width"] or 1280,
            h=info["height"] or int(quality),
            supports_streaming=True,
        )]

        sender = user_client if (size_mb > 1950 and is_premium and user_client) else bot
        uploaded = await upload_file(sender, final)
        sent = await sender.send_file(
            uid, uploaded, caption=caption, thumb=thumb,
            attributes=attrs, supports_streaming=True
        )

        if sender == bot and sent and sent.document:
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
        log.error(f"[{uid}] Playlist item {vid} error: {e}")
        await status.edit(f"❌ Ошибка: {str(e)[:100]}")
        for f in os.listdir(DOWNLOAD_DIR):
            if f.startswith(f"{uid}_{vid}"):
                await rm(os.path.join(DOWNLOAD_DIR, f))


# ─────────────────────────────────────────────
# ЗАПУСК
# ─────────────────────────────────────────────

async def main():
    global user_client, is_premium, bot_username, owner_id

    await bot.start(bot_token=BOT_TOKEN)
    me = await bot.get_me()
    bot_username = me.username
    log.info(f"Бот запущен: @{bot_username}")

    # Premium userbot (опционально)
    if os.path.exists("user_session.session"):
        user_client = TelegramClient("user_session", API_ID, API_HASH, proxy=proxy)
        await user_client.start()
        ume = await user_client.get_me()
        owner_id = ume.id
        is_premium = getattr(ume, "premium", False)
        PREMIUM_USERS.add(owner_id)
        log.info(f"Premium userbot: {ume.first_name} | Premium={is_premium}")
    else:
        log.info("Работаю в режиме 2 ГБ (без userbot).")

    # Проверка FFmpeg
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        log.info("FFmpeg OK")
    except FileNotFoundError:
        log.critical("FFmpeg не найден в PATH!")
        sys.exit(1)

    await bot.run_until_disconnected()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        db.close()
        print("\nОстановлено.")
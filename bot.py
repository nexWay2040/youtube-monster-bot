# =====================================================================
#     __  __                  _             ____         _   
#    |  \/  | ___  _ __  ___ | |_ ___ _ __ | __ )  ___  | |_ 
#    | |\/| |/ _ \| '_ \/ __|| __/ _ \ '__||  _ \ / _ \ | __|
#    | |  | | (_) | | | \__ \| ||  __/ |   | |_) | (_) || |_ 
#    |_|  |_|\___/|_| |_|___/ \__\___|_|   |____/ \___/  \__|
#                                                            
#          === YOUTUBE MONSTER BOT (ULTIMATE EDITION) ===
#           🤖 DUAL-CONTOUR + ENTERPRISE OOP + AMD AMF
#            ⚡ CACHE SYSTEM + 4GB PREMIUM UPLOAD
#          📚 DYNAMIC BATCH PLAYLIST DOWNLOADER (x1-x10)
#          🌐 FULL EJS DENO & BROWSER COOKIES INTEGRATION
# =====================================================================

import os
import re
import sys
import math
import json
import random
import asyncio
import logging
import time
import subprocess
import shutil
import sqlite3
from datetime import timedelta
from typing import Tuple, List, Dict, Optional, Any, Union, Set

# Проверка и импорт зависимостей
try:
    from telethon import TelegramClient, events, functions, types, utils
    from telethon.tl.custom import Button
    from telethon.tl.types import DocumentAttributeVideo, DocumentAttributeAudio
    from telethon.errors import SessionPasswordNeededError, RPCError, FloodWaitError
    import yt_dlp
    import socks
    from dotenv import load_dotenv, set_key
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}. Пожалуйста, установите библиотеки:")
    print("pip install telethon yt-dlp[default] cryptg PySocks python-dotenv")
    sys.exit(1)

# --- УМНЫЙ ПОИСК ФАЙЛА КОНФИГУРАЦИИ И АВТОПОИСК DENO ---
if os.path.exists(".env"):
    load_dotenv(".env")
elif os.path.exists(".evn"):  
    load_dotenv(".evn")
elif os.path.exists(".env.txt"):
    load_dotenv(".env.txt")
else:
    load_dotenv()

# АВТОМАТИЧЕСКАЯ РЕГИСТРАЦИЯ ПУТИ К DENO В WINDOWS
user_home = os.path.expanduser("~")
deno_dir = os.path.join(user_home, ".deno", "bin")
if os.path.exists(deno_dir) and deno_dir not in os.environ["PATH"]:
    os.environ["PATH"] += os.pathsep + deno_dir


# =====================================================================
# РАЗДЕЛ 1: ИЕРАРХИЯ ИСКЛЮЧЕНИЙ (CUSTOM EXCEPTIONS)
# =====================================================================
class YouTubeMonsterException(Exception):
    """Базовый класс для всех исключений приложения YouTube Monster Bot"""
    def __init__(self, message: str, details: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.details = details

    def __str__(self):
        if self.details:
            return f"{self.message} | Детали: {self.details}"
        return self.message


class ConfigurationError(YouTubeMonsterException):
    """Выбрасывается при ошибках чтения конфигурации .env или ключей API"""
    pass


class DependencyError(YouTubeMonsterException):
    """Выбрасывается при отсутствии бинарников FFmpeg/FFprobe в системе"""
    pass


class FFmpegProcessingError(YouTubeMonsterException):
    """Выбрасывается при сбоях транскодирования через утилиту FFmpeg"""
    pass


class PlaylistParsingError(YouTubeMonsterException):
    """Выбрасывается при ошибках извлечения элементов плейлиста"""
    pass


class DownloadStreamError(YouTubeMonsterException):
    """Выбрасывается при сбоях сетевого скачивания потоков через yt-dlp"""
    pass


class UploadStreamError(YouTubeMonsterException):
    """Выбрасывается при сбоях выгрузки чанков в Telegram"""
    pass


# =====================================================================
# РАЗДЕЛ 2: СИСТЕМА ДВОЙНОГО ЛОГИРОВАНИЯ
# =====================================================================
class LoggerSetup:
    """
    Настраивает вывод логов одновременно в терминал (sys.stdout) 
    и в локальный текстовый файл bot.log для истории событий.
    """
    
    @staticmethod
    def setup_logger(logger_name: str = "MonsterBot") -> logging.Logger:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.INFO)
        
        formatter = logging.Formatter(
            '%(asctime)s - [%(levelname)s] - %(name)s - %(message)s', 
            datefmt='%H:%M:%S'
        )

        if logger.hasHandlers():
            logger.handlers.clear()

        # Вывод в консоль
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # Вывод в файл bot.log
        try:
            file_handler = logging.FileHandler("bot.log", encoding="utf-8")
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            print(f"⚠️ Предупреждение: Не удалось инициализировать файловый логгер: {e}")

        return logger

logger = LoggerSetup.setup_logger()


# =====================================================================
# РАЗДЕЛ 3: МЕНЕДЖЕР КОНФИГУРАЦИИ ПРИЛОЖЕНИЯ
# =====================================================================
class BotConfig:
    """
    Синглтон-класс для централизованного хранения параметров, 
    проверки обязательных ключей и динамической перезаписи .env файла.
    """
    
    def __init__(self):
        self.env_file: str = ".env"
        for f in [".env", ".evn", ".env.txt"]:
            if os.path.exists(f):
                self.env_file = f
                break

        load_dotenv(self.env_file)
        
        # Ключи Telegram API
        self.API_ID: int = int(os.getenv("API_ID", "0"))
        self.API_HASH: str = os.getenv("API_HASH", "")
        self.BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
        
        # Системные директории и кодеры
        self.DOWNLOAD_DIR: str = os.getenv("DOWNLOAD_DIR", "./downloads")
        self.VIDEO_ENCODER: str = os.getenv("VIDEO_ENCODER", "libx264")
        self.BROWSER_COOKIES: str = os.getenv("BROWSER_COOKIES", "")
        
        # Настройки скачивания плейлистов
        self.DEFAULT_BATCH_SIZE: int = int(os.getenv("DEFAULT_BATCH_SIZE", "3"))
        
        # Настройки проксирования трафика
        self.USE_PROXY: bool = os.getenv("USE_PROXY", "False").lower() == "true"
        self.PROXY_HOST: str = os.getenv("PROXY_HOST", "127.0.0.1")
        self.PROXY_PORT: int = int(os.getenv("PROXY_PORT", "10808"))
        
        # Белый список пользователей с доступом к 4GB Premium Upload
        self.PREMIUM_USERS_RAW: str = os.getenv("PREMIUM_USERS", "")
        self.PREMIUM_USERS: Set[int] = {
            int(x.strip()) for x in self.PREMIUM_USERS_RAW.split(",") if x.strip().isdigit()
        }
        
        self._ensure_directories()
        self._validate_keys()

    def _ensure_directories(self) -> None:
        try:
            os.makedirs(self.DOWNLOAD_DIR, exist_ok=True)
        except Exception as e:
            logger.error(f"Не удалось создать директорию скачивания {self.DOWNLOAD_DIR}: {e}")

    def _validate_keys(self) -> None:
        if self.API_ID == 0 or not self.API_HASH or not self.BOT_TOKEN:
            logger.critical("❌ КРИТИЧЕСКАЯ ОШИБКА: Обязательные ключи (API_ID, API_HASH, BOT_TOKEN) отсутствуют в .env!")
            raise ConfigurationError("Заполните файл .env перед запуском приложения.")

    def update_key(self, key: str, value: Any) -> None:
        try:
            set_key(self.env_file, key, str(value))
            os.environ[key] = str(value)
            setattr(self, key, value)
            logger.info(f"Конфигурация [{key}] обновлена: {value}")
        except Exception as e:
            logger.error(f"Не удалось зафиксировать ключ {key} в файле {self.env_file}: {e}")

config = BotConfig()


# =====================================================================
# РАЗДЕЛ 4: МЕНЕДЖЕР БАЗЫ ДАННЫХ SQLITE3 (CDN КЭШИРОВАНИЕ И АДМИНКА)
# =====================================================================
class SQLiteDB:
    """
    Класс взаимодействия с локальной базой данных SQLite3.
    Реализует хранение профилей пользователей, учет трафика, бан-лист 
    и глобальную таблицу кэша file_id для мгновенной отдачи файлов.
    """
    
    def __init__(self, db_name: str = "monster_bot.db"):
        self.db_name = db_name
        self.conn = sqlite3.connect(self.db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self._initialize_schema()

    def _initialize_schema(self) -> None:
        try:
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_banned BOOLEAN DEFAULT 0,
                    total_videos INTEGER DEFAULT 0,
                    total_mb_downloaded REAL DEFAULT 0.0
                )
            ''')
            
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS video_cache (
                    video_id TEXT,
                    quality TEXT,
                    file_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (video_id, quality)
                )
            ''')
            self.conn.commit()
            logger.debug("Схема базы данных SQLite успешно проверена.")
        except sqlite3.Error as e:
            logger.error(f"Ошибка сбоя структуры БД SQLite: {e}")

    def get_cached_file(self, video_id: str, quality: str) -> Optional[str]:
        try:
            self.cursor.execute('SELECT file_id FROM video_cache WHERE video_id = ? AND quality = ?', (video_id, quality))
            res = self.cursor.fetchone()
            return res[0] if res else None
        except sqlite3.Error as e:
            logger.error(f"Сбой чтения кэша БД [{video_id}:{quality}]: {e}")
            return None

    def save_cached_file(self, video_id: str, quality: str, file_id: str) -> None:
        try:
            self.cursor.execute('INSERT OR REPLACE INTO video_cache (video_id, quality, file_id) VALUES (?, ?, ?)', 
                                (video_id, quality, file_id))
            self.conn.commit()
            logger.info(f"💾 Запись добавлена в локальный CDN-кэш: [{video_id}] -> {quality}p")
        except sqlite3.Error as e:
            logger.error(f"Сбой записи кэша в БД: {e}")

    def remove_cached_file(self, video_id: str, quality: str) -> None:
        try:
            self.cursor.execute('DELETE FROM video_cache WHERE video_id = ? AND quality = ?', (video_id, quality))
            self.conn.commit()
            logger.info(f"Удален недействительный кэш: [{video_id}:{quality}]")
        except sqlite3.Error as e:
            logger.error(f"Ошибка очистки кэша: {e}")

    def register_user(self, user_id: int, username: Optional[str]) -> None:
        try:
            self.cursor.execute('INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)', (user_id, username or "NoUsername"))
            self.conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Ошибка регистрации пользователя {user_id}: {e}")

    def update_stats(self, user_id: int, size_mb: float) -> None:
        try:
            self.cursor.execute('''
                UPDATE users 
                SET total_videos = total_videos + 1, 
                    total_mb_downloaded = total_mb_downloaded + ? 
                WHERE user_id = ?
            ''', (size_mb, user_id))
            self.conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Ошибка обновления статистики пользователя {user_id}: {e}")

    def check_banned(self, user_id: int) -> bool:
        try:
            self.cursor.execute('SELECT is_banned FROM users WHERE user_id = ?', (user_id,))
            result = self.cursor.fetchone()
            return bool(result[0]) if result else False
        except sqlite3.Error:
            return False

    def set_ban_status(self, user_id: int, status: bool) -> bool:
        try:
            self.cursor.execute('UPDATE users SET is_banned = ? WHERE user_id = ?', (int(status), user_id))
            self.conn.commit()
            return self.cursor.rowcount > 0
        except sqlite3.Error as e:
            logger.error(f"Ошибка изменения бана для {user_id}: {e}")
            return False

    def get_all_users_ids(self) -> List[int]:
        try:
            self.cursor.execute('SELECT user_id FROM users WHERE is_banned = 0')
            return [row[0] for row in self.cursor.fetchall()]
        except sqlite3.Error:
            return []

    def get_global_statistics(self) -> Dict[str, Any]:
        try:
            self.cursor.execute('SELECT COUNT(*), SUM(total_videos), SUM(total_mb_downloaded) FROM users')
            row = self.cursor.fetchone()
            
            self.cursor.execute('SELECT COUNT(*) FROM video_cache')
            cached_count = self.cursor.fetchone()[0]
            
            return {
                "total_users": row[0] or 0,
                "total_videos": row[1] or 0,
                "total_gb": (row[2] or 0) / 1024.0,
                "cached_files": cached_count or 0
            }
        except sqlite3.Error as e:
            logger.error(f"Ошибка получения статистики БД: {e}")
            return {"total_users": 0, "total_videos": 0, "total_gb": 0.0, "cached_files": 0}

    def close(self) -> None:
        if self.conn:
            self.conn.close()

db = SQLiteDB()


# =====================================================================
# РАЗДЕЛ 5: СИСТЕМНЫЕ УТИЛИТЫ И ФОРМАТИРОВАНИЕ
# =====================================================================
class Utils:
    """Набор вспомогательных функций форматирования, сбора метрик и очистки"""
    
    @staticmethod
    def format_bytes(size: Union[int, float, None]) -> str:
        if size is None or size <= 0: 
            return "0.00 Б"
        power = 2**10
        n = 0
        labels = {0: 'Б', 1: 'КБ', 2: 'МБ', 3: 'ГБ', 4: 'ТБ'}
        while size > power and n < 4:
            size /= power
            n += 1
        return f"{size:.2f} {labels[n]}"

    @staticmethod
    def make_progress_bar(percent: float, length: int = 12) -> str:
        percent = max(0.0, min(100.0, percent))
        filled = int(length * (percent / 100.0))
        bar = "█" * filled + "▒" * (length - filled)
        return f"[{bar}]"

    @staticmethod
    def make_hashtag(author_name: str) -> str:
        if not author_name or author_name == 'Unknown': 
            return "#unknown"
        clean_name = re.sub(r'[^\w\s]', '', author_name.strip())
        return f"#{re.sub(r'\s+', '_', clean_name).lower()}"

    @staticmethod
    def extract_youtube_url(text: str) -> Optional[str]:
        pattern = r'(https?://(?:www\.)?youtu(?:be\.com/watch\?v=|\.be/|be\.com/embed/|be\.com/v/|be\.com/shorts/|be\.com/playlist\?list=)[^\s]+)'
        match = re.search(pattern, text)
        return match.group(1) if match else None

    @staticmethod
    async def safe_remove(filepath: Optional[str], retries: int = 5, delay: float = 1.5) -> bool:
        if not filepath or not os.path.exists(filepath):
            return True
            
        for attempt in range(retries):
            try:
                os.remove(filepath)
                logger.debug(f"Удален файл: {filepath}")
                return True
            except PermissionError:
                logger.warning(f"Файл {filepath} заблокирован ОС. Ждем {delay}с (Попытка {attempt+1}/{retries})")
                await asyncio.sleep(delay)
            except Exception as e:
                logger.error(f"Неожиданный сбой удаления {filepath}: {e}")
                return False
                
        logger.error(f"Не удалось удалить файл {filepath} после {retries} попыток.")
        return False


# =====================================================================
# РАЗДЕЛ 6: КОНСТРУКТОР КОМАНД FFMPEG
# =====================================================================
class FFmpegBuilder:
    """
    Фабрика построения аргументов командной строки FFmpeg.
    Поддерживает динамическую настройку AMD AMF, NVIDIA NVENC, Intel QSV и CPU.
    """
    
    TARGET_BITRATE = {
        '1080': {'target': '2800k', 'max': '4000k'}, 
        '720':  {'target': '1500k', 'max': '2200k'},  
        '480':  {'target': '800k',  'max': '1200k'},   
        '360':  {'target': '450k',  'max': '700k'},    
    }

    AMF_QP_GRID = {
        '1080': '29',  
        '720':  '31',  
        '480':  '31',   
        '360':  '33',   
    }

    @classmethod
    def build_transcode_cmd(cls, source_file: str, final_file: str, format_choice: str, 
                            encoder: str, duration: int, is_premium: bool) -> List[str]:
        cfg = cls.TARGET_BITRATE.get(str(format_choice), {'target': '2000k', 'max': '3000k'})
        t_rate = cfg['target']
        m_rate = cfg['max']
        
        cmd = ['ffmpeg', '-y', '-i', source_file, '-c:v', encoder]
        
        if 'amf' in encoder:
            qp_val = cls.AMF_QP_GRID.get(str(format_choice), '28')
            cmd.extend(['-rc', 'cqp', '-qp_i', qp_val, '-qp_p', qp_val])
        elif 'nvenc' in encoder:
            cmd.extend(['-rc', 'vbr', '-b:v', t_rate, '-maxrate', m_rate])
        elif 'qsv' in encoder:
            cmd.extend(['-b:v', t_rate, '-maxrate', m_rate])
        else:
            est_bits = (int(m_rate.replace('k', '')) * 1024 + 128000) * duration
            max_safe_bits = (3900 if is_premium else 1900) * 1024 * 1024 * 8
            crf = 28 if est_bits > max_safe_bits else 18
            # Сменили veryfast на ultrafast для ускорения процессора в 5 раз!
            cmd.extend([
                '-preset', 'ultrafast', 
                '-crf', str(crf), 
                '-maxrate', m_rate, 
                '-bufsize', f"{int(m_rate.replace('k', '')) * 2}k"
            ])
        
        cmd.extend(['-pix_fmt', 'yuv420p'])
        cmd.extend(['-c:a', 'aac', '-b:a', '128k', '-movflags', '+faststart', final_file])
        return cmd

    @classmethod
    def build_cpu_fallback_cmd(cls, source_file: str, final_file: str, format_choice: str, 
                               duration: int, is_premium: bool) -> List[str]:
        cfg = cls.TARGET_BITRATE.get(str(format_choice), {'target': '2000k', 'max': '3000k'})
        m_rate = cfg['max']
        
        est_bits = (int(m_rate.replace('k', '')) * 1024 + 128000) * duration
        max_safe_bits = (3900 if is_premium else 1900) * 1024 * 1024 * 8
        crf = 28 if est_bits > max_safe_bits else 18
        
        return [
            'ffmpeg', '-y', '-i', source_file,
            '-c:v', 'libx264', 
            '-preset', 'ultrafast',  # <-- Поставили ultrafast!
            '-crf', str(crf),
            '-maxrate', m_rate, '-bufsize', f"{int(m_rate.replace('k', '')) * 2}k",
            '-pix_fmt', 'yuv420p',
            '-c:a', 'aac', '-b:a', '128k', '-movflags', '+faststart',
            final_file
        ]


# =====================================================================
# РАЗДЕЛ 7: ДВИЖОК СКАНЕР И ТРАНСКОДЕР (YT-DLP + FFPROBE)
# =====================================================================
class YouTubeEngine:
    """Ядро работы с медиаконтентом YouTube"""

    @staticmethod
    def check_system() -> None:
        try:
            subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
            subprocess.run(['ffprobe', '-version'], capture_output=True, check=True)
            logger.info("✅ Движок FFmpeg/FFprobe успешно проинициализирован.")
        except FileNotFoundError:
            logger.critical("❌ КРИТИЧЕСКАЯ ОШИБКА: FFmpeg не найден в системе!")
            raise DependencyError("FFmpeg/FFprobe отсутствуют в системном PATH.")

    @staticmethod
    def probe_video(filepath: str) -> Tuple[int, int, int, str, str]:
        try:
            cmd = ['ffprobe', '-v', 'error', '-show_entries', 'stream=width,height,duration,codec_name,codec_type', '-of', 'json', filepath]
            res = subprocess.run(cmd, capture_output=True, text=True, errors='replace')
            data = json.loads(res.stdout)
            
            w, h, dur, v_codec, a_codec = 0, 0, 0, '', ''
            
            for stream in data.get('streams', []):
                if stream.get('width'):
                    w, h = int(stream.get('width', 0)), int(stream.get('height', 0))
                    dur = int(float(stream.get('duration', 0) or 0))
                    v_codec = stream.get('codec_name', '')
                elif stream.get('codec_type') == 'audio':
                    a_codec = stream.get('codec_name', '')
                    
            if dur == 0:
                cmd_f = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'json', filepath]
                res_f = subprocess.run(cmd_f, capture_output=True, text=True)
                dur = int(float(json.loads(res_f.stdout).get('format', {}).get('duration', 0) or 0))
                
            return w, h, dur, v_codec, a_codec
        except Exception as e:
            logger.error(f"Сбой FFprobe при сканировании файла {filepath}: {e}")
            return 0, 0, 0, '', ''

    @staticmethod
    def run_ffmpeg_checked(cmd: List[str], final_filename: str, user_id: int) -> Tuple[bool, str]:
        logger.debug(f"Исполнение FFmpeg команды: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
        
        if result.returncode != 0 or not os.path.exists(final_filename) or os.path.getsize(final_filename) == 0:
            stderr_text = result.stderr if result.stderr else "Нет вывода ошибок от FFmpeg."
            logger.error(f"[{user_id}] Ошибка FFmpeg (Код {result.returncode}): {stderr_text[-1000:]}")
            return False, stderr_text
            
        return True, ""

    @classmethod
    def download_and_optimize(cls, url: str, format_choice: str, video_id: str, 
                              user_id: int, duration: int, is_premium: bool) -> Tuple[str, Optional[str]]:
        ffmpeg_exe = shutil.which('ffmpeg')
        ffmpeg_dir = os.path.dirname(ffmpeg_exe) if ffmpeg_exe else None

        def ytdl_hook(d):
            if d['status'] == 'downloading':
                d_bytes = d.get('downloaded_bytes') or 0
                t_bytes = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
                spd = d.get('speed')
                eta = d.get('eta')
                
                spd_str = Utils.format_bytes(spd) if spd is not None else "0.00 Б"
                eta_str = str(timedelta(seconds=int(eta))) if eta is not None else "0:00:00"
                
                if t_bytes > 0:
                    pct = (d_bytes / t_bytes) * 100
                    bar = Utils.make_progress_bar(pct, 15)
                    sys.stdout.write(f"\r📥 YT-DLP {bar} {pct:.1f}% | {spd_str}/s | Осталось: {eta_str}      ")
                else:
                    sys.stdout.write(f"\r📥 YT-DLP [Запуск потока...] | {spd_str}/s      ")
                sys.stdout.flush()
            elif d['status'] == 'finished':
                sys.stdout.write("\n")

        # 🔥 ПОЛНЫЙ ИСПРАВЛЕННЫЙ БЛОК НАСТРОЕК YT-DLP (ВКЛЮЧЕН EJS И ПОДДЕРЖКА КУКИ ДЛЯ ПЛЕЙЛИСТОВ И 1080P)
        opts = {
            'outtmpl': os.path.join(config.DOWNLOAD_DIR, f'{user_id}_{video_id}.%(ext)s'),
            'quiet': True, 
            'no_warnings': True, 
            'concurrent_fragment_downloads': 4,
            'writethumbnail': True,
            'progress_hooks': [ytdl_hook],
            'retries': 10,
            'fragment_retries': 10,
            'remote_components': ['ejs:github'], # Авторешение JS-челленджей через Deno
        }
        
        if ffmpeg_dir: 
            opts['ffmpeg_location'] = ffmpeg_dir
        if config.USE_PROXY: 
            opts['proxy'] = f'socks5://{config.PROXY_HOST}:{config.PROXY_PORT}'
        if config.BROWSER_COOKIES: 
            opts['cookiesfrombrowser'] = (config.BROWSER_COOKIES,)

        if format_choice == 'mp3':
            opts['format'] = 'bestaudio/best'
            opts['postprocessors'] = [
                {'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}
            ]
        else:
            opts['format'] = f'bestvideo[height<={format_choice}]+bestaudio/best[height<={format_choice}]/best[height<={format_choice}]'
            opts['merge_output_format'] = 'mp4'

        logger.info(f"[{user_id}] Запуск потока скачивания {format_choice}p...")
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])

        if format_choice == 'mp3':
            final_file = os.path.join(config.DOWNLOAD_DIR, f"{user_id}_{video_id}.mp3")
            if not os.path.exists(final_file): 
                final_file = cls._find_file(user_id, video_id)
            return final_file, cls._process_thumb(user_id, video_id)

        source_file = cls._find_file(user_id, video_id)
        if not source_file or not os.path.exists(source_file):
            raise FileNotFoundError("Сбой: Файл видеопотока не обнаружен на диске.")

        final_file = os.path.join(config.DOWNLOAD_DIR, f"{user_id}_{video_id}_optimized.mp4")
        w, h, dur, v_codec, a_codec = cls.probe_video(source_file)
        logger.info(f"[{user_id}] Исходные параметры: {w}x{h} | Video={v_codec}, Audio={a_codec}")

        success = False
        error_msg = ""

        # СЦЕНАРИЙ 1: Direct Copy (Без потерь)
        if v_codec == 'h264' and a_codec in ['aac', 'mp3']:
            logger.info(f"[{user_id}] ⚡ Direct Copy (мгновенная упаковка)...")
            cmd = ['ffmpeg', '-y', '-i', source_file, '-c:v', 'copy', '-c:a', 'copy', '-movflags', '+faststart', final_file]
            success, error_msg = cls.run_ffmpeg_checked(cmd, final_file, user_id)
            
        # СЦЕНАРИЙ 2: Перекодирование только аудио
        elif v_codec == 'h264':
            logger.info(f"[{user_id}] ⚙️ Конвертация аудиопотока в AAC...")
            cmd = ['ffmpeg', '-y', '-i', source_file, '-c:v', 'copy', '-c:a', 'aac', '-b:a', '128k', '-movflags', '+faststart', final_file]
            success, error_msg = cls.run_ffmpeg_checked(cmd, final_file, user_id)
            
        # СЦЕНАРИЙ 3: Полное Перекодирование (VP9/AV1)
        else:
            logger.info(f"[{user_id}] 🏎️ Полный транскодинг (Кодек={config.VIDEO_ENCODER})...")
            
            if config.VIDEO_ENCODER != 'libx264':
                gpu_cmd = FFmpegBuilder.build_transcode_cmd(
                    source_file, final_file, format_choice, config.VIDEO_ENCODER, duration, is_premium
                )
                success, error_msg = cls.run_ffmpeg_checked(gpu_cmd, final_file, user_id)

            # Self-Healing: Автооткат на CPU при сбое GPU
            if not success:
                if config.VIDEO_ENCODER != 'libx264':
                    logger.warning(f"[{user_id}] ⚠️ Кодек {config.VIDEO_ENCODER} дал сбой. Автопереход на CPU (libx264)...")
                
                if os.path.exists(final_file):
                    try: os.remove(final_file)
                    except: pass
                
                cpu_cmd = FFmpegBuilder.build_cpu_fallback_cmd(source_file, final_file, format_choice, duration, is_premium)
                success, error_msg = cls.run_ffmpeg_checked(cpu_cmd, final_file, user_id)
                
                if not success:
                    raise RuntimeError(f"FFmpeg полностью отказался обрабатывать видео: {error_msg[-300:]}")

        try: os.remove(source_file)
        except Exception: pass

        return final_file, cls._process_thumb(user_id, video_id)

    @staticmethod
    def _find_file(user_id: int, video_id: str) -> Optional[str]:
        prefix = f"{user_id}_{video_id}."
        for file in os.listdir(config.DOWNLOAD_DIR):
            if file.startswith(prefix) and not file.lower().endswith(('.jpg', '.webp', '.part', '.ytdl')):
                return os.path.join(config.DOWNLOAD_DIR, file)
        return None

    @staticmethod
    def _process_thumb(user_id: int, video_id: str) -> Optional[str]:
        prefix = f"{user_id}_{video_id}."
        raw_thumb = None
        for file in os.listdir(config.DOWNLOAD_DIR):
            if file.startswith(prefix) and file.lower().endswith(('.jpg', '.webp', '.png')) and '_thumb' not in file:
                raw_thumb = os.path.join(config.DOWNLOAD_DIR, file)
                break
                
        if raw_thumb and os.path.exists(raw_thumb):
            thumb_file = os.path.join(config.DOWNLOAD_DIR, f"{user_id}_{video_id}_thumb.jpg")
            cmd = ['ffmpeg', '-y', '-i', raw_thumb, '-vf', "scale='if(gt(iw,ih),320,-1)':'if(gt(iw,ih),-1,320)'", '-q:v', '5', thumb_file]
            subprocess.run(cmd, capture_output=True)
            try: os.remove(raw_thumb)
            except Exception: pass
            return thumb_file
        return None


# =====================================================================
# РАЗДЕЛ 8: ПОТОКОВЫЙ ЗАГРУЗЧИК В TELEGRAM (ZERO-RAM QUEUE)
# =====================================================================
class TelegramStreamUploader:
    """Загрузка файлов до 4 ГБ частями по 512 КБ с лимитом ОЗУ в 4 МБ"""
    
    @staticmethod
    async def upload(client: TelegramClient, file_path: str, progress_callback=None) -> types.InputFileBig:
        file_size = os.path.getsize(file_path)
        chunk_size = 512 * 1024 
        chunks_count = math.ceil(file_size / chunk_size)
        file_id = random.getrandbits(63) 
        
        queue = asyncio.Queue()
        for i in range(chunks_count): 
            await queue.put(i)
            
        uploaded_chunks = 0
        u_lock = asyncio.Lock()  
        f_lock = asyncio.Lock()  
        
        async def worker(f):
            nonlocal uploaded_chunks
            while True:
                try: 
                    part_index = queue.get_nowait()
                except asyncio.QueueEmpty: 
                    break
                    
                async with f_lock:
                    f.seek(part_index * chunk_size)
                    data = f.read(chunk_size)
                    
                for attempt in range(4): 
                    try:
                        await client(functions.upload.SaveBigFilePartRequest(
                            file_id=file_id, 
                            file_part=part_index, 
                            file_total_parts=chunks_count, 
                            bytes=data
                        ))
                        break
                    except Exception as e:
                        if attempt == 3: 
                            logger.error(f"Сбой передачи чанка {part_index}: {e}")
                        await asyncio.sleep(1.5)
                        
                del data  
                
                async with u_lock:
                    uploaded_chunks += 1
                    if progress_callback:
                        await progress_callback(min(uploaded_chunks * chunk_size, file_size), file_size)

        with open(file_path, 'rb') as f:
            workers = [worker(f) for _ in range(8)]
            await asyncio.gather(*workers)

        return types.InputFileBig(id=file_id, parts=chunks_count, name=os.path.basename(file_path))


# =====================================================================
# РАЗДЕЛ 9: УПРАВЛЕНИЕ ИНТЕРФЕЙСОМ И КЛАВИАТУРАМИ
# =====================================================================
class BotInterfaceUI:
    """Генератор визуальных элементов, инлайн-клавиатур и меню"""
    
    @staticmethod
    def generate_video_keyboard(available_heights: set, video_id: str) -> List[List[Button]]:
        all_options = [
            ("1080p (FHD)", 1080), 
            ("720p (HD)", 720), 
            ("480p", 480), 
            ("360p", 360)
        ]
        
        valid_buttons = []
        for label, res in all_options:
            if res in available_heights:
                if db.get_cached_file(video_id, str(res)):
                    btn_text = f"⚡ {label} (Кэш)"
                else:
                    btn_text = f"🎬 {label}"
                valid_buttons.append(Button.inline(btn_text, f"dl:{res}:{video_id}"))
                
        if not valid_buttons:
            max_h = max(available_heights) if available_heights else 360
            if db.get_cached_file(video_id, str(max_h)):
                btn_text = f"⚡ {max_h}p (Кэш)"
            else:
                btn_text = f"🎬 {max_h}p"
            valid_buttons.append(Button.inline(btn_text, f"dl:{max_h}:{video_id}"))
            
        kb = [valid_buttons[i:i+2] for i in range(0, len(valid_buttons), 2)]
        
        if db.get_cached_file(video_id, 'mp3'):
            kb.append([Button.inline("⚡ MP3 Audio (Кэш)", f"dl:mp3:{video_id}")])
        else:
            kb.append([Button.inline("🎵 Скачать как MP3", f"dl:mp3:{video_id}")])
            
        return kb

    @staticmethod
    def generate_batch_keyboard(video_id: str, format_choice: str) -> List[List[Button]]:
        return [
            [Button.inline("⚡ По 1 видео (Осторожно)", f"plbatch:{format_choice}:1:{video_id}"),
             Button.inline("🚀 По 3 видео (Стандарт)", f"plbatch:{format_choice}:3:{video_id}")],
            [Button.inline("🔥 По 5 видео (Быстро)", f"plbatch:{format_choice}:5:{video_id}"),
             Button.inline("💥 По 10 видео (Экстрим)", f"plbatch:{format_choice}:10:{video_id}")]
        ]


# =====================================================================
# РАЗДЕЛ 10: ГЛАВНЫЙ КОНТРОЛЛЕР ПРИЛОЖЕНИЯ (MONSTER BOT APP)
# =====================================================================
class MonsterBotApp:
    def __init__(self, enable_userbot: bool):
        proxy = (socks.SOCKS5, config.PROXY_HOST, config.PROXY_PORT) if config.USE_PROXY else None
        
        self.bot = TelegramClient('bot_session', config.API_ID, config.API_HASH, proxy=proxy)
        self.user = TelegramClient('user_session', config.API_ID, config.API_HASH, proxy=proxy) if enable_userbot else None
        
        self.bot_username: Optional[str] = None
        self.owner_id: Optional[int] = None
        self.is_premium: bool = False
        self.video_cache: Dict[str, dict] = {}
        
        YouTubeEngine.check_system()
        self._register_handlers()

    def _register_handlers(self):
        
        # --- COMMAND: /start ---
        @self.bot.on(events.NewMessage(pattern=r'^/start$'))
        async def start_handler(event):
            db.register_user(event.sender_id, event.sender.username)
            await event.respond(
                "👋 **Привет! Я Ultimate YouTube Downloader Bot.**\n\n"
                "💬 **Как пользоваться:**\n"
                "1. Отправь мне любую ссылку на видео YouTube, Shorts или Плейлист.\n"
                "2. Выбери желаемое качество с помощью кнопок.\n"
                "3. Я скачаю, сожму и пришлю медиа прямо в этот чат!\n\n"
                "⚡ Значок **(Кэш)** на кнопке означает мгновенную отправку за 0.1 сек!\n\n"
                f"🛡️ *Ваш личный лимит загрузки: {'4 ГБ (Premium)' if self.is_premium else '2 ГБ (Standard)'}*"
            )

        # --- ADMIN HANDLERS ---
        @self.bot.on(events.NewMessage(pattern=r'^/(admin|users|ban|unban|broadcast)'))
        async def admin_handler(event):
            if not self.owner_id or event.sender_id != self.owner_id:
                return await event.respond("❌ Недостаточно прав доступа.")
            
            text = event.text.strip()
            
            if text == '/admin':
                stats = db.get_global_statistics()
                msg = (
                    "👑 **ПАНЕЛЬ АДМИНИСТРАТОРА** 👑\n"
                    "━━━━━━━━━━━━━━━━━━━━\n"
                    f"👥 **Пользователей в базе:** `{stats['total_users']}`\n"
                    f"🎬 **Скачано роликов:** `{stats['total_videos']}`\n"
                    f"💾 **Сгенерировано трафика:** `{stats['total_gb']:.2f} ГБ`\n"
                    f"⚡ **Файлов в кэше (CDN):** `{stats['cached_files']}`\n"
                    "━━━━━━━━━━━━━━━━━━━━\n"
                    f"⚙️ **Активный видеокодек:** `{config.VIDEO_ENCODER}`\n"
                    f"📦 **Размер пачки плейлиста:** `по {config.DEFAULT_BATCH_SIZE} видео`\n"
                    f"🛡️ **Статус Premium:** `{'Активен (Лимит 4 ГБ)' if self.is_premium else 'Выключен (Лимит 2 ГБ)'}`\n\n"
                    "**Команды управления:**\n"
                    "`/users` — Список всех пользователей и их ID\n"
                    "`/ban <ID>` — Заблокировать юзера\n"
                    "`/unban <ID>` — Разблокировать юзера\n"
                    "`/broadcast <Текст>` — Рассылка всем юзерам"
                )
                await event.respond(msg)
                
            elif text == '/users':
                db.cursor.execute('SELECT user_id, username, is_banned FROM users ORDER BY joined_at DESC LIMIT 50')
                users = db.cursor.fetchall()
                if not users:
                    return await event.respond("📭 Список пользователей пуст.")
                
                msg = "👥 **Последние 50 пользователей бота:**\n\n"
                for uid, uname, banned in users:
                    status = "⛔️ БАН" if banned else "✅ Активен"
                    uname_text = f"@{uname}" if uname else "Без юзернейма"
                    msg += f"ID: `{uid}` | {uname_text} | {status}\n"
                
                await event.respond(msg)

            elif text.startswith('/ban '):
                try:
                    target_id = int(text.split(' ')[1])
                    success = db.set_ban_status(target_id, True)
                    await event.respond(f"✅ Пользователь `{target_id}` заблокирован." if success else "❌ Пользователь не найден.")
                except ValueError:
                    await event.respond("❌ Ошибка: ID должен быть числом.")
                
            elif text.startswith('/unban '):
                try:
                    target_id = int(text.split(' ')[1])
                    success = db.set_ban_status(target_id, False)
                    await event.respond(f"✅ Пользователь `{target_id}` разблокирован." if success else "❌ Пользователь не найден.")
                except ValueError:
                    await event.respond("❌ Ошибка: ID должен быть числом.")
                
            elif text.startswith('/broadcast '):
                message = text.replace('/broadcast ', '')
                users = db.get_all_users_ids()
                success_count = 0
                progress_msg = await event.respond(f"📣 Начинаю рассылку для {len(users)} пользователей...")
                
                for uid in users:
                    try:
                        await self.bot.send_message(uid, f"🔔 **Уведомление от Администратора:**\n\n{message}")
                        success_count += 1
                        await asyncio.sleep(0.5) 
                    except Exception: pass
                    
                await progress_msg.edit(f"✅ **Рассылка завершена!**\nУспешно доставлено: `{success_count} / {len(users)}`")

        # --- HANDLING YOUTUBE & PLAYLIST LINKS ---
        @self.bot.on(events.NewMessage())
        async def link_handler(event):
            if event.text.startswith('/'): return
            user_id = event.sender_id
            
            if db.check_banned(user_id):
                return await event.respond("❌ Вы заблокированы за нарушение правил.")

            url = Utils.extract_youtube_url(event.text)
            if not url: return  

            # ОБНАРУЖЕНИЕ ПЛЕЙЛИСТА
            is_playlist = 'list=' in url or 'playlist?list=' in url
            
            if is_playlist:
                msg = await event.respond("📚 **Обнаружен плейлист!** Сканирую элементы...")
                try:
                    ydl_opts = {
                        'quiet': True, 
                        'extract_flat': True,
                        'remote_components': ['ejs:github'],
                    }
                    if config.USE_PROXY: ydl_opts['proxy'] = f'socks5://{config.PROXY_HOST}:{config.PROXY_PORT}'
                    if config.BROWSER_COOKIES: ydl_opts['cookiesfrombrowser'] = (config.BROWSER_COOKIES,)
                    
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(url, download=False)
                        title = info.get('title', 'Плейлист')
                        uploader = info.get('uploader', 'Unknown')
                        entries = info.get('entries', [])
                        video_ids = [e['id'] for e in entries if e.get('id')]
                        
                    if not video_ids:
                        return await msg.edit("❌ **Ошибка:** Плейлист пуст или закрыт настройками приватности.")
                        
                    video_id = info.get('id') or f"pl_{random.getrandbits(32)}"
                    
                    self.video_cache[video_id] = {
                        'url': url, 'title': title, 'uploader': uploader,
                        'duration': 0, 'is_playlist': True, 'video_ids': video_ids
                    }
                    
                    keyboard = [
                        [Button.inline("🎬 1080p (FHD)", f"dl:1080:{video_id}"), Button.inline("🎬 720p (HD)", f"dl:720:{video_id}")],
                        [Button.inline("🎬 480p", f"dl:480:{video_id}"), Button.inline("🎬 360p", f"dl:360:{video_id}")]
                    ]
                    
                    preview_text = (
                        f"📚 **YouTube Плейлист**\n━━━━━━━━━━━━━━━━━━━━\n"
                        f"📝 **Название:** `{title}`\n"
                        f"👤 **Канал:** {Utils.make_hashtag(uploader)}\n"
                        f"⏱️ **Количество видео:** `{len(video_ids)}` роликов\n"
                        f"━━━━━━━━━━━━━━━━━━━━\n"
                        f"👇 *Выберите желаемое качество для всего плейлиста:* "
                    )
                    await msg.edit(preview_text, buttons=keyboard)
                    return
                    
                except Exception as e:
                    logger.error(f"Сбой парсинга плейлиста: {e}")
                    return await msg.edit(f"❌ **Ошибка парсинга плейлиста:**\n`{str(e)}`")

            # ОДИНОЧНОЕ ВИДЕО
            msg = await event.respond("🔍 **Проверяю видео на серверах YouTube...**")

            try:
                ydl_opts = {
                    'quiet': True,
                    'remote_components': ['ejs:github'],
                }
                if config.USE_PROXY: ydl_opts['proxy'] = f'socks5://{config.PROXY_HOST}:{config.PROXY_PORT}'
                if config.BROWSER_COOKIES: ydl_opts['cookiesfrombrowser'] = (config.BROWSER_COOKIES,)

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    if info.get('is_live'):
                        return await msg.edit("❌ Прямые трансляции не поддерживаются.")
                        
                    v_id = info.get('id')
                    title = info.get('title', 'Без названия')
                    uploader = info.get('uploader', 'Unknown')
                    duration = int(info.get('duration', 0) or 0)
                    
                    available_heights = set(int(f.get('height')) for f in info.get('formats', []) if f.get('vcodec') != 'none' and f.get('height'))

                self.video_cache[v_id] = {
                    'url': url, 'title': title, 'uploader': uploader, 'duration': duration, 'available_heights': list(available_heights)
                }
                
                if len(self.video_cache) > 500:
                    for k in list(self.video_cache.keys())[:100]: self.video_cache.pop(k, None)

                preview_text = (
                    f"🎥 **YouTube Downloader**\n━━━━━━━━━━━━━━━━━━━━\n"
                    f"📝 **Название:** `{title}`\n"
                    f"👤 **Канал:** {Utils.make_hashtag(uploader)}\n"
                    f"⏱️ **Длительность:** `{timedelta(seconds=duration)}`\n"
                    f"⚙️ **Макс. качество:** `{max(available_heights) if available_heights else '720'}p`\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"👇 *Выберите желаемый формат:* "
                )
                
                await msg.edit(preview_text, buttons=BotInterfaceUI.generate_video_keyboard(available_heights, v_id))

            except Exception as e:
                logger.error(f"Сбой анализа метаданных: {e}")
                await msg.edit(f"❌ **Сбой связи с YouTube:**\n`{str(e)}`")

        # --- CALLBACK: КЛИКИ ПО ИНЛАЙН-КНОПКАМ КАЧЕСТВА ---
        @self.bot.on(events.CallbackQuery(pattern=b'^dl:'))
        async def download_callback(event):
            user_id = event.sender_id
            
            try:
                parts = event.data.decode('utf-8').split(':')
                format_choice, video_id = parts[1], parts[2]
            except Exception: return

            cache = self.video_cache.get(video_id)
            if not cache:
                return await event.answer("❌ Сессия устарела. Отправьте ссылку заново.", alert=True)

            # ШАГ 2 ДЛЯ ПЛЕЙЛИСТОВ: ВЫБОР РАЗМЕРА ПАЧКИ
            if cache.get('is_playlist', False):
                await event.edit(
                    f"📚 **Плейлист:** `{cache['title']}`\n"
                    f"⏱ Всего роликов: `{len(cache['video_ids'])}`\n"
                    f"⚙️ Выбранное качество: `{format_choice}p`\n━━━━━━━━━━━━━━━━━━━━\n"
                    f"📦 **Выберите, по сколько видео скачивать одновременно:**",
                    buttons=BotInterfaceUI.generate_batch_keyboard(video_id, format_choice)
                )
                return

            msg = await event.reply(f"⏳ **Запуск обработки...** Качество: `{format_choice if format_choice == 'mp3' else format_choice + 'p'}`")

            # 🔥 ПРОВЕРКА КЭША БД (ОДИНАРНЫЕ ВИДЕО)
            cached_file_id = db.get_cached_file(video_id, format_choice)
            if cached_file_id:
                try:
                    logger.info(f"[{user_id}] ⚡ Найдено в кэше! Мгновенная отправка.")
                    await msg.edit("⚡ **Найдено в локальном кэше! Мгновенная отправка...**")
                    caption = f"🎬 **{cache['title']}**\n\n👤 Автор: {Utils.make_hashtag(cache['uploader'])}"
                    
                    await self.bot.send_file(user_id, cached_file_id, caption=caption)
                    await msg.delete()
                    db.update_stats(user_id, 0)
                    return
                except Exception as e:
                    logger.warning(f"[{user_id}] Битый кэш. Перескачивание. Ошибка: {e}")
                    db.remove_cached_file(video_id, format_choice)

            # СКАЧИВАНИЕ И ТРАНСКОДИРОВАНИЕ С НУЛЯ
            try:
                final_filename, thumb_file = await asyncio.to_thread(
                    YouTubeEngine.download_and_optimize, 
                    cache['url'], format_choice, video_id, user_id, cache['duration'], self.is_premium
                )

                file_size_mb = os.path.getsize(final_filename) / (1024 * 1024)

                has_premium_access = (user_id in config.PREMIUM_USERS) and self.is_premium
                max_limit_mb = 3950 if has_premium_access else 1950
                
                if file_size_mb > max_limit_mb:
                    await msg.edit(f"❌ **Сбой:** Файл весит {file_size_mb:.1f} МБ. Ваш лимит отправки: {'4 ГБ' if has_premium_access else '2 ГБ'}.")
                    await Utils.safe_remove(final_filename)
                    if thumb_file: await Utils.safe_remove(thumb_file)
                    return

                await msg.edit("⚙️ **Видео готово. Подключение к серверам Telegram...**")
                start_time, last_update = time.time(), [0]

                async def upload_progress(current, total):
                    now = time.time()
                    if now - last_update[0] > 2.5 or current == total:
                        speed = current / (now - start_time) if (now - start_time) > 0 else 0
                        eta = (total - current) / speed if speed > 0 else 0
                        percent = (current / total * 100) if total > 0 else 0
                        
                        bar = Utils.make_progress_bar(percent, 12)
                        contour_name = 'Premium (4 GB)' if file_size_mb > 1950 else 'Standard (2 GB)'
                        
                        try:
                            await msg.edit(
                                f"🚀 **Выгрузка в Telegram [{contour_name}]:**\n\n"
                                f"📊 {bar} **{percent:.1f}%**\n"
                                f"⚡ Скорость: **{speed/(1024*1024):.1f} МБ/с**\n"
                                f"⏳ Осталось: **{timedelta(seconds=int(eta))}**"
                            )
                        except Exception: pass
                        last_update[0] = now

                caption = f"🎬 **{cache['title']}**\n\n👤 Автор: {Utils.make_hashtag(cache['uploader'])}"
                attributes = []
                
                if format_choice == 'mp3':
                    attributes.append(DocumentAttributeAudio(duration=cache['duration'], title=cache['title']))
                else:
                    w, h, dur, _, _ = YouTubeEngine.probe_video(final_filename)
                    attributes.append(DocumentAttributeVideo(duration=dur or cache['duration'], w=w or 1920, h=h or int(format_choice), supports_streaming=True))

                sender = self.user if (file_size_mb > 1950 and self.is_premium) else self.bot
                
                uploaded_file = await TelegramStreamUploader.upload(sender, final_filename, upload_progress)
                await msg.edit("⚡ **Файл передан на сервер Telegram. Финализация...**")
                
                sent_msg = None
                if sender == self.user:
                    target = self.bot_username if user_id == self.owner_id else user_id
                    sent_msg = await sender.send_file(target, uploaded_file, caption=caption, thumb=thumb_file, attributes=attributes, supports_streaming=True)
                else:
                    sent_msg = await sender.send_file(user_id, uploaded_file, caption=caption, thumb=thumb_file, attributes=attributes, supports_streaming=True)

                # 🔥 СОХРАНЕНИЕ В КЭШ ДЛЯ ОДИНОЧНЫХ ВИДЕО (до 2 ГБ)
                if sender == self.bot and sent_msg and sent_msg.document:
                    try:
                        bot_file_id = utils.pack_bot_file_id(sent_msg.document)
                        db.save_cached_file(video_id, format_choice, bot_file_id)
                    except Exception as e:
                        logger.warning(f"Не удалось закэшировать файл {video_id}: {e}")

                db.update_stats(user_id, file_size_mb)
                await Utils.safe_remove(final_filename)
                if thumb_file: await Utils.safe_remove(thumb_file)
                await msg.delete()

                logger.info(f"[{user_id}] ✅ Видео ({file_size_mb:.1f} МБ) успешно доставлено.")

            except Exception as e:
                logger.error(f"[{user_id}] Критический сбой: {e}", exc_info=True)
                await msg.edit(f"❌ **Внутренняя ошибка системы:**\n`{str(e)}`")
                for f in os.listdir(config.DOWNLOAD_DIR):
                    if f.startswith(str(user_id)):
                        await Utils.safe_remove(os.path.join(config.DOWNLOAD_DIR, f))

        # --- CALLBACK: КЛИКИ ПО КНОПКАМ РАЗМЕРА ПАЧКИ ПЛЕЙЛИСТА ---
        @self.bot.on(events.CallbackQuery(pattern=b'^plbatch:'))
        async def playlist_batch_callback(event):
            user_id = event.sender_id
            
            try:
                parts = event.data.decode('utf-8').split(':')
                format_choice, batch_size_str, video_id = parts[1], parts[2], parts[3]
                batch_size = int(batch_size_str)
            except Exception: return

            cache = self.video_cache.get(video_id)
            if not cache or not cache.get('is_playlist'):
                return await event.answer("❌ Сессия плейлиста устарела. Отправьте ссылку заново.", alert=True)

            video_ids = cache['video_ids']
            total_videos = len(video_ids)
            
            msg = await event.edit(
                f"📚 **Запуск обработки плейлиста:** `{cache['title']}`\n"
                f"⏱ Всего роликов: `{total_videos}`\n"
                f"⚙️ Выбранное качество: `{format_choice}p`\n"
                f"📦 Режим скачивания: `По {batch_size} видео в пачке`"
            )

            # Нарезаем список на пачки по batch_size
            chunks = [video_ids[i:i + batch_size] for i in range(0, len(video_ids), batch_size)]
            
            for chunk_idx, chunk in enumerate(chunks, start=1):
                logger.info(f"[{user_id}] Пачка {chunk_idx}/{len(chunks)} (размер={len(chunk)}) плейлиста {video_id}...")
                
                # Поочередный запуск видео в пачке с паузой 1.5с для защиты от 403 Forbidden
                tasks = []
                for idx, v_id in enumerate(chunk):
                    video_url = f"https://www.youtube.com/watch?v={v_id}"
                    tasks.append(self._process_playlist_video(video_url, format_choice, v_id, user_id, delay=idx * 1.5))
                    
                await asyncio.gather(*tasks)
                
            logger.info(f"[{user_id}] ✅ Плейлист {video_id} успешно обработан!")

    async def _process_playlist_video(self, video_url: str, format_choice: str, video_id: str, user_id: int, delay: float = 0.0):
        """Вспомогательный метод асинхронной обработки ролика из плейлиста"""
        if delay > 0:
            await asyncio.sleep(delay)
            
        try:
            ydl_opts = {
                'quiet': True,
                'remote_components': ['ejs:github'], # 🔥 ОБЯЗАТЕЛЬНО ДЛЯ ПЛЕЙЛИСТОВ
            }
            if config.USE_PROXY: ydl_opts['proxy'] = f'socks5://{config.PROXY_HOST}:{config.PROXY_PORT}'
            if config.BROWSER_COOKIES: ydl_opts['cookiesfrombrowser'] = (config.BROWSER_COOKIES,)
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=False)
                title = info.get('title', 'Без названия')
                uploader = info.get('uploader', 'Unknown')
                duration = int(info.get('duration', 0) or 0)
        except Exception as e:
            logger.error(f"Не удалось получить метаданные видео {video_id} из плейлиста: {e}")
            return

        caption = f"🎬 **{title}**\n\n👤 Автор: {Utils.make_hashtag(uploader)}"

        # 1. Проверяем кэш базы данных
        cached_file_id = db.get_cached_file(video_id, format_choice)
        if cached_file_id:
            logger.info(f"[{user_id}] ⚡ Видео {video_id} найдено в кэше плейлиста!")
            try:
                await self.bot.send_file(user_id, cached_file_id, caption=caption)
                db.update_stats(user_id, 0)
                return
            except Exception:
                db.remove_cached_file(video_id, format_choice)

        # 2. Скачивание и кодирование
        status_msg = await self.bot.send_message(user_id, f"📥 **Обработка ролика:**\n🎬 `{title}` ({format_choice}p)")
        
        try:
            final_filename, thumb_file = await asyncio.to_thread(
                YouTubeEngine.download_and_optimize, 
                video_url, format_choice, video_id, user_id, duration, self.is_premium
            )

            file_size_mb = os.path.getsize(final_filename) / (1024 * 1024)

            has_premium_access = (user_id in config.PREMIUM_USERS) and self.is_premium
            max_limit_mb = 3950 if has_premium_access else 1950

            if file_size_mb > max_limit_mb:
                await status_msg.edit(f"❌ **Сбой:** Видео `{title}` ({file_size_mb:.1f} МБ) превышает ваш лимит.")
                await Utils.safe_remove(final_filename)
                if thumb_file: await Utils.safe_remove(thumb_file)
                return

            await status_msg.edit(f"⚙️ **Загрузка в Telegram...**\n🎬 `{title}` ({file_size_mb:.1f} МБ)")

            attributes = []
            w, h, dur, _, _ = YouTubeEngine.probe_video(final_filename)
            attributes.append(DocumentAttributeVideo(duration=dur or duration, w=w or 1920, h=h or int(format_choice), supports_streaming=True))

            sender = self.user if (file_size_mb > 1950 and self.is_premium) else self.bot

            # Выгрузка без частого редактирования прогресса (защита от FloodWait)
            uploaded_file = await TelegramStreamUploader.upload(sender, final_filename, progress_callback=None)

            sent_msg = None
            if sender == self.user:
                target = self.bot_username if user_id == self.owner_id else user_id
                sent_msg = await sender.send_file(target, uploaded_file, caption=caption, thumb=thumb_file, attributes=attributes, supports_streaming=True)
            else:
                sent_msg = await sender.send_file(user_id, uploaded_file, caption=caption, thumb=thumb_file, attributes=attributes, supports_streaming=True)

            # Сохраняем в кэш БД
            if sender == self.bot and sent_msg and sent_msg.document:
                try:
                    bot_file_id = utils.pack_bot_file_id(sent_msg.document)
                    db.save_cached_file(video_id, format_choice, bot_file_id)
                except Exception as e:
                    logger.warning(f"Не удалось закэшировать файл {video_id}: {e}")

            await Utils.safe_remove(final_filename)
            if thumb_file: await Utils.safe_remove(thumb_file)
            await status_msg.delete()
            db.update_stats(user_id, file_size_mb)

        except Exception as e:
            logger.error(f"Ошибка при обработке видео из плейлиста {video_id}: {e}", exc_info=True)
            await status_msg.edit(f"❌ **Ошибка скачивания:**\n`{title[:50]}...`\n{str(e)[:50]}")
            for file in os.listdir(config.DOWNLOAD_DIR):
                if file.startswith(str(user_id)):
                    await Utils.safe_remove(os.path.join(config.DOWNLOAD_DIR, file))

    async def start(self):
        await self.bot.start(bot_token=config.BOT_TOKEN)
        bot_me = await self.bot.get_me()
        self.bot_username = bot_me.username
        
        if self.user:
            logger.info("🔑 Инициализация Premium-юзербота...")
            await self.user.start()
            user_me = await self.user.get_me()
            self.owner_id = user_me.id
            self.is_premium = getattr(user_me, 'premium', False)
            
            if self.owner_id not in config.PREMIUM_USERS:
                config.PREMIUM_USERS.add(self.owner_id)
            
            logger.info("🚀 СИСТЕМА ДВОЙНОГО КОНТУРА АКТИВИРОВАНА!")
            logger.info(f"👑 Владелец: {user_me.first_name} | Premium: {'АКТИВЕН' if self.is_premium else 'ОТСУТСТВУЕТ'}")
            
            await asyncio.gather(self.bot.disconnected, self.user.disconnected)
        else:
            self.is_premium = False
            self.owner_id = None
            logger.info("🚀 БОТ УСПЕШНО ЗАПУЩЕН В СТАНДАРТНОМ РЕЖИМЕ (Лимит 2 ГБ)!")
            
            await self.bot.run_until_disconnected()


# =====================================================================
# СТИЛЬНЫЙ СТАРТОВЫЙ ASCII БАННЕР В КОНСОЛИ
# =====================================================================
def print_banner():
    banner = r"""
========================================================================
     __  __                  _             ____         _   
    |  \/  | ___  _ __  ___ | |_ ___ _ __ | __ )  ___  | |_ 
    | |\/| |/ _ \| '_ \/ __|| __/ _ \ '__||  _ \ / _ \ | __|
    | |  | | (_) | | | \__ \| ||  __/ |   | |_) | (_) || |_ 
    |_|  |_|\___/|_| |_|___/ \__\___|_|   |____/ \___/  \__|
                                                            
               === DUAL-CONTOUR HYBRID BOT ACTIVATED ===
                 🤖 BOT INTERFACE  +  👤 PREMIUM UPLOAD
========================================================================
    """
    print(banner)


# =====================================================================
# ИНТЕРАКТИВНОЕ КОНСОЛЬНОЕ МЕНЮ (НАСТРОЙКА И ЗАПУСК)
# =====================================================================
def interactive_cli_menu() -> bool:
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        print(r"""
========================================================================
     __  __                  _             ____         _   
    |  \/  | ___  _ __  ___ | |_ ___ _ __ | __ )  ___  | |_ 
    | |\/| |/ _ \| '_ \/ __|| __/ _ \ '__||  _ \ / _ \ | __|
    | |  | | (_) | | | \__ \| ||  __/ |   | |_) | (_) || |_ 
    |_|  |_|\___/|_| |_|___/ \__\___|_|   |____/ \___/  \__|
                                                            
          === YOUTUBE MONSTER BOT (ULTIMATE EDITION) ===
========================================================================
        """)
        
        has_session = os.path.exists("user_session.session")
        print("  ДАННАЯ ПАНЕЛЬ ПРЕДНАЗНАЧЕНА ДЛЯ УПРАВЛЕНИЯ СЕРВЕРОМ БОТА\n")
        print(f"  [1] ▶️ ЗАПУСТИТЬ СЕРВЕР БОТА В РАБОТУ")
        print(f"  [2] 💎 Premium-режим (Юзербот 4 ГБ): [{'ВКЛЮЧЕН' if has_session else 'ВЫКЛЮЧЕН'}]")
        print(f"  [3] 🎥 Активный видеокодек:          [{config.VIDEO_ENCODER}]")
        print(f"  [4] 🌐 Защитный Прокси (Happ/VPN):   [{'ВКЛЮЧЕН' if config.USE_PROXY else 'ВЫКЛЮЧЕН'}]")
        print(f"  [5] 📦 Пачка плейлиста по умолчанию: [по {config.DEFAULT_BATCH_SIZE} видео]")
        print(f"  [6] 🗑️ Сбросить Premium-авторизацию (Удалить сессию)")
        print("  [0] ❌ Закрыть панель")
        print("========================================================================")
        
        choice = input("👉 Выберите номер действия (0-6): ").strip()
        
        if choice == "1":
            print("\n🚀 Инициализация систем. Пожалуйста, подождите...\n")
            return has_session
            
        elif choice == "2":
            if not has_session:
                print("\n⚠️ ВНИМАНИЕ: При старте сервера Telegram запросит ваш номер телефона для авторизации личного аккаунта.")
                time.sleep(2.5)
                return True
            else:
                print("\n✅ Premium-режим уже активен. Выбирайте пункт [1] для старта.")
                time.sleep(2)
                
        elif choice == "3":
            print("\nДоступные аппаратные и программные кодеки:")
            print("  1. libx264    (Универсальный, на центральном процессоре CPU)")
            print("  2. h264_amf   (Аппаратный, для видеокарт AMD Radeon)")
            print("  3. h264_nvenc (Аппаратный, для видеокарт NVIDIA GeForce)")
            print("  4. h264_qsv   (Аппаратный, для графики Intel QuickSync)")
            enc_choice = input("\n👉 Укажите номер кодека под ваше железо (1-4): ").strip()
            codecs = {"1": "libx264", "2": "h264_amf", "3": "h264_nvenc", "4": "h264_qsv"}
            if enc_choice in codecs:
                config.update_key("VIDEO_ENCODER", codecs[enc_choice])
                
        elif choice == "4":
            new_val = not config.USE_PROXY
            config.update_key("USE_PROXY", str(new_val))
            print(f"\n🌐 Прокси {'ВКЛЮЧЕН (порт 10808)' if new_val else 'ВЫКЛЮЧЕН'}.")
            time.sleep(1.5)
            
        elif choice == "5":
            new_batch = input("\n👉 Укажите число роликов в пачке по умолчанию (1, 3, 5, 10): ").strip()
            if new_batch.isdigit() and int(new_batch) > 0:
                config.update_key("DEFAULT_BATCH_SIZE", new_batch)
                
        elif choice == "6":
            for f in ["user_session.session", "user_session.session-journal"]:
                if os.path.exists(f): os.remove(f)
            print("\n✅ Сессия успешно сброшена! Бот переведен в стандартный режим (2 ГБ).")
            time.sleep(2)
            
        elif choice == "0":
            sys.exit(0)


# =====================================================================
# ТОЧКА ВХОДА (ENTRY POINT) И ЗАЩИЩЕННЫЙ ЗАПУСК
# =====================================================================
if __name__ == "__main__":
    print_banner()
    
    enable_userbot = interactive_cli_menu()
    
    try:
        app = MonsterBotApp(enable_userbot)
        asyncio.run(app.start())
    except KeyboardInterrupt:
        print("\n👋 Бот успешно остановлен пользователем. Всего доброго!")
        try:
            db.close()
            sys.exit(0)
        except SystemExit:
            os._exit(0)
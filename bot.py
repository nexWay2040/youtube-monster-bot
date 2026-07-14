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
from typing import Tuple, List, Dict, Optional, Any, Union

# Проверка и импорт зависимостей
try:
    from telethon import TelegramClient, events, functions, types, utils
    from telethon.tl.custom import Button
    from telethon.tl.types import DocumentAttributeVideo, DocumentAttributeAudio
    from telethon.errors import SessionPasswordNeededError
    import yt_dlp
    import socks
    from dotenv import load_dotenv, set_key
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}. Пожалуйста, установите библиотеки:")
    print("pip install telethon yt-dlp[default] cryptg PySocks python-dotenv")
    sys.exit(1)


# =====================================================================
# КЛАСС 1: КАСТОМНЫЕ ИСКЛЮЧЕНИЯ (EXCEPTIONS)
# =====================================================================
class YouTubeMonsterException(Exception):
    """Базовый класс для всех исключений бота"""
    pass

class ConfigurationError(YouTubeMonsterException):
    """Ошибка конфигурации или отсутствия ключей"""
    pass

class DependencyError(YouTubeMonsterException):
    """Ошибка отсутствия системных зависимостей (FFmpeg/FFprobe)"""
    pass

class FFmpegProcessingError(YouTubeMonsterException):
    """Ошибка при обработке медиафайла утилитой FFmpeg"""
    pass


# =====================================================================
# КЛАСС 2: УМНЫЙ ПОИСК КОНФИГУРАЦИИ И ЗАГРУЗКА .ENV
# =====================================================================
class EnvLoader:
    """Обеспечивает интеллектуальный поиск файла .env с защитой от опечаток Windows"""
    
    @staticmethod
    def load():
        possible_names = [".env", ".evn", ".env.txt", "env.txt"]
        loaded = False
        
        for file_name in possible_names:
            if os.path.exists(file_name):
                load_dotenv(file_name)
                loaded = True
                break
                
        if not loaded:
            # Инициализация пустого контекста для дальнейшей генерации
            load_dotenv()

EnvLoader.load()


# =====================================================================
# КЛАСС 3: ПРОДВИНУТОЕ ЛОГИРОВАНИЕ
# =====================================================================
class LoggerSetup:
    """Настройка двойного асинхронного логирования (Консоль + Файл bot.log)"""
    
    @staticmethod
    def setup_logger() -> logging.Logger:
        logger = logging.getLogger("MonsterBot")
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - [%(levelname)s] - %(name)s - %(message)s', datefmt='%H:%M:%S')

        # Очистка старых хэндлеров, если они есть
        if logger.hasHandlers():
            logger.handlers.clear()

        # Обработчик для консоли (sys.stdout)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # Обработчик для файла (bot.log)
        try:
            file_handler = logging.FileHandler("bot.log", encoding="utf-8")
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            print(f"⚠️ Не удалось создать файл логов bot.log: {e}")

        return logger

logger = LoggerSetup.setup_logger()


# =====================================================================
# КЛАСС 4: УПРАВЛЕНИЕ КОНФИГУРАЦИЕЙ И ИНТЕРАКТИВНЫМ МЕНЮ
# =====================================================================
class BotConfig:
    """Синглтон для хранения и динамического обновления настроек среды"""
    
    def __init__(self):
        self.env_file = self._find_or_create_env()
        load_dotenv(self.env_file)
        
        # Основные API ключи
        self.API_ID: int = int(os.getenv("API_ID", "0"))
        self.API_HASH: str = os.getenv("API_HASH", "")
        self.BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
        
        # Директория скачивания
        self.DOWNLOAD_DIR: str = os.getenv("DOWNLOAD_DIR", "./downloads")
        
        # Настройки видеокодера
        self.VIDEO_ENCODER: str = os.getenv("VIDEO_ENCODER", "libx264")
        
        # Настройки прокси
        self.USE_PROXY: bool = os.getenv("USE_PROXY", "False").lower() == "true"
        self.PROXY_HOST: str = os.getenv("PROXY_HOST", "127.0.0.1")
        self.PROXY_PORT: int = int(os.getenv("PROXY_PORT", "10808"))
        
        # Белый список пользователей с доступом к 4GB Premium Upload
        self.PREMIUM_USERS_RAW: str = os.getenv("PREMIUM_USERS", "")
        self.PREMIUM_USERS: set = {
            int(x.strip()) for x in self.PREMIUM_USERS_RAW.split(",") if x.strip().isdigit()
        }
        
        self._initialize_directories()
        self._validate_critical_keys()

    def _find_or_create_env(self) -> str:
        """Поиск или создание файла конфигурации по умолчанию"""
        possible_files = [".env", ".evn", ".env.txt"]
        for f in possible_files:
            if os.path.exists(f):
                return f
        
        logger.warning("Файл конфигурации не найден. Создаю новый .env файл...")
        template = (
            "# --- НАСТРОЙКИ АВТОРИЗАЦИИ ---\n"
            "API_ID=0\n"
            "API_HASH=\n"
            "BOT_TOKEN=\n\n"
            "# --- НАСТРОЙКИ СИСТЕМЫ ---\n"
            "DOWNLOAD_DIR=./downloads\n"
            "VIDEO_ENCODER=libx264\n"
            "PREMIUM_USERS=\n\n"
            "# --- НАСТРОЙКИ ПРОКСИ ---\n"
            "USE_PROXY=False\n"
            "PROXY_HOST=127.0.0.1\n"
            "PROXY_PORT=10808\n"
        )
        with open(".env", "w", encoding="utf-8") as file:
            file.write(template)
        return ".env"

    def _initialize_directories(self) -> None:
        """Создание необходимых директорий"""
        try:
            os.makedirs(self.DOWNLOAD_DIR, exist_ok=True)
        except Exception as e:
            logger.error(f"Не удалось создать директорию {self.DOWNLOAD_DIR}: {e}")

    def _validate_critical_keys(self) -> None:
        """Проверка наличия обязательных параметров"""
        if self.API_ID == 0 or not self.API_HASH or not self.BOT_TOKEN:
            logger.critical("❌ КРИТИЧЕСКАЯ ОШИБКА: Ключи API_ID, API_HASH или BOT_TOKEN не заполнены в файле .env!")
            logger.critical("Отредактируйте файл .env и перезапустите скрипт.")
            sys.exit(1)

    def update_key(self, key: str, value: Any) -> None:
        """Безопасное обновление ключа прямо в файле .env и в памяти"""
        try:
            set_key(self.env_file, key, str(value))
            os.environ[key] = str(value)
            setattr(self, key, value)
            logger.info(f"Настройка [{key}] успешно изменена на: {value}")
        except Exception as e:
            logger.error(f"Ошибка при обновлении ключа {key}: {e}")

# Инициализация глобального конфига
config = BotConfig()


# =====================================================================
# КЛАСС 5: ЛОКАЛЬНАЯ БАЗА ДАННЫХ SQLITE3 (АДМИНКА + КЭШ ВИДЕО)
# =====================================================================
class SQLiteDB:
    """
    Управление локальной базой данных.
    Хранит информацию о пользователях, статистику и глобальный кэш file_id.
    """
    def __init__(self, db_name="monster_bot.db"):
        self.db_name = db_name
        self.conn = sqlite3.connect(self.db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self._initialize_tables()

    def _initialize_tables(self) -> None:
        """Создание таблиц при первом запуске"""
        try:
            # Таблица пользователей и статистики
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
            
            # Таблица кэша видеофайлов (Global CDN)
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
        except sqlite3.Error as e:
            logger.error(f"Ошибка инициализации БД SQLite: {e}")

    # -----------------------------------------------------------------
    # МЕТОДЫ КЭШИРОВАНИЯ ВИДЕО
    # -----------------------------------------------------------------
    def get_cached_file(self, video_id: str, quality: str) -> Optional[str]:
        """
        Проверяет, скачивали ли мы уже это видео в заданном качестве.
        Возвращает file_id для мгновенной отправки, либо None.
        """
        try:
            self.cursor.execute('SELECT file_id FROM video_cache WHERE video_id = ? AND quality = ?', (video_id, quality))
            res = self.cursor.fetchone()
            return res[0] if res else None
        except sqlite3.Error as e:
            logger.error(f"Ошибка чтения кэша БД: {e}")
            return None

    def save_cached_file(self, video_id: str, quality: str, file_id: str) -> None:
        """
        Сохраняет file_id готового видео в базу для будущих пользователей.
        Используется REPLACE для обновления file_id в случае изменения.
        """
        try:
            self.cursor.execute('INSERT OR REPLACE INTO video_cache (video_id, quality, file_id) VALUES (?, ?, ?)', 
                                (video_id, quality, file_id))
            self.conn.commit()
            logger.debug(f"Кэш обновлен: {video_id} [{quality}p]")
        except sqlite3.Error as e:
            logger.error(f"Ошибка записи в кэш БД: {e}")

    def remove_cached_file(self, video_id: str, quality: str) -> None:
        """Удаляет битый file_id из базы, если Telegram отказал в его отправке"""
        try:
            self.cursor.execute('DELETE FROM video_cache WHERE video_id = ? AND quality = ?', (video_id, quality))
            self.conn.commit()
            logger.info(f"Битый кэш удален: {video_id} [{quality}p]")
        except sqlite3.Error as e:
            logger.error(f"Ошибка удаления кэша БД: {e}")

    # -----------------------------------------------------------------
    # МЕТОДЫ ПОЛЬЗОВАТЕЛЕЙ И СТАТИСТИКИ
    # -----------------------------------------------------------------
    def register_user(self, user_id: int, username: str) -> None:
        """Добавляет нового пользователя в базу при команде /start"""
        try:
            self.cursor.execute('INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)', (user_id, username))
            self.conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Ошибка регистрации пользователя: {e}")

    def update_stats(self, user_id: int, size_mb: float) -> None:
        """Обновляет счетчик скачанных мегабайт и количества видео"""
        try:
            self.cursor.execute('''
                UPDATE users 
                SET total_videos = total_videos + 1, 
                    total_mb_downloaded = total_mb_downloaded + ? 
                WHERE user_id = ?
            ''', (size_mb, user_id))
            self.conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Ошибка обновления статистики: {e}")

    def check_banned(self, user_id: int) -> bool:
        """Проверка статуса блокировки пользователя"""
        try:
            self.cursor.execute('SELECT is_banned FROM users WHERE user_id = ?', (user_id,))
            result = self.cursor.fetchone()
            return bool(result[0]) if result else False
        except sqlite3.Error:
            return False

    def set_ban_status(self, user_id: int, status: bool) -> bool:
        """Установить статус блокировки пользователя (Бан/Разбан)"""
        try:
            self.cursor.execute('UPDATE users SET is_banned = ? WHERE user_id = ?', (int(status), user_id))
            self.conn.commit()
            return self.cursor.rowcount > 0
        except sqlite3.Error as e:
            logger.error(f"Ошибка бана пользователя: {e}")
            return False

    def get_all_users_ids(self) -> List[int]:
        """Получить список всех незаблокированных ID для рассылки"""
        try:
            self.cursor.execute('SELECT user_id FROM users WHERE is_banned = 0')
            return [row[0] for row in self.cursor.fetchall()]
        except sqlite3.Error:
            return []

    def get_global_statistics(self) -> Dict[str, Any]:
        """Сводная статистика для панели Администратора"""
        try:
            self.cursor.execute('SELECT COUNT(*), SUM(total_videos), SUM(total_mb_downloaded) FROM users')
            row = self.cursor.fetchone()
            
            self.cursor.execute('SELECT COUNT(*) FROM video_cache')
            cached_count = self.cursor.fetchone()[0]
            
            return {
                "total_users": row[0] or 0,
                "total_videos": row[1] or 0,
                "total_gb": (row[2] or 0) / 1024,
                "cached_files": cached_count or 0
            }
        except sqlite3.Error as e:
            logger.error(f"Ошибка сбора статистики: {e}")
            return {"total_users": 0, "total_videos": 0, "total_gb": 0, "cached_files": 0}

    def close(self):
        """Закрытие соединения с БД при остановке скрипта"""
        if self.conn:
            self.conn.close()

# Инициализация глобального подключения к БД
db = SQLiteDB()


# =====================================================================
# КЛАСС 6: СИСТЕМНЫЕ УТИЛИТЫ И ФОРМАТИРОВАНИЕ
# =====================================================================
class Utils:
    """Сборник статических методов для работы с файлами и строками"""
    
    @staticmethod
    def format_bytes(size: Union[int, float, None]) -> str:
        """Конвертация байтов в читаемый формат (КБ, МБ, ГБ)"""
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
        """Создает текстовый прогресс-бар вида [██████▒▒▒▒]"""
        filled = int(length * (percent / 100.0))
        bar = "█" * filled + "▒" * (length - filled)
        return f"[{bar}]"

    @staticmethod
    def make_hashtag(author_name: str) -> str:
        """Очищает имя автора и превращает его в Telegram-хэштег"""
        if not author_name or author_name == 'Unknown':
            return "#unknown"
        clean_name = re.sub(r'[^\w\s]', '', author_name.strip())
        return f"#{re.sub(r'\s+', '_', clean_name).lower()}"

    @staticmethod
    def extract_youtube_url(text: str) -> Optional[str]:
        """Безопасный поиск и извлечение ссылки на YouTube из текста"""
        pattern = r'(https?://(?:www\.)?youtu(?:be\.com/watch\?v=|\.be/|be\.com/embed/|be\.com/v/|be\.com/shorts/)[^\s]+)'
        match = re.search(pattern, text)
        return match.group(1) if match else None

    @staticmethod
    async def safe_remove(filepath: str, retries: int = 5, delay: float = 1.5) -> bool:
        """Безопасное удаление файла с обходом блокировки процессами Windows"""
        if not filepath:
            return False
            
        for attempt in range(retries):
            try:
                if os.path.exists(filepath):
                    os.remove(filepath)
                    logger.debug(f"Файл успешно удален: {filepath}")
                    return True
                return True # Файла уже нет
            except PermissionError:
                logger.warning(f"Файл {filepath} заблокирован ОС. Ждем {delay}с (Попытка {attempt+1}/{retries})")
                await asyncio.sleep(delay)
            except Exception as e:
                logger.error(f"Неизвестная ошибка при удалении файла {filepath}: {e}")
                return False
        
        logger.error(f"Не удалось удалить файл {filepath} после {retries} попыток.")
        return False


# =====================================================================
# КЛАСС 7: КОНСТРУКТОР FFMPEG КОМАНД
# =====================================================================
class FFmpegBuilder:
    """
    Инкапсулирует логику построения сложных команд FFmpeg.
    Обеспечивает корректный выбор параметров для AMD, NVIDIA, Intel и CPU.
    """
    
    # Умная сетка VBR битрейтов (Целевой и Пиковый)
    TARGET_BITRATE = {
        '1080': {'target': '2800k', 'max': '4000k'}, 
        '720':  {'target': '1500k', 'max': '2200k'},  
        '480':  {'target': '800k',  'max': '1200k'},   
        '360':  {'target': '450k',  'max': '700k'},    
    }

    # --- НОВАЯ СВЕРХСТАБИЛЬНАЯ СЕТКА CQP ДЛЯ ВИДЕОКАРТ AMD ---
    # Снижает вес 1080p до ~550-650 МБ, а 720p до ~450-550 МБ без потери четкости!
    AMF_QP_GRID = {
        '1080': '29',  # Снизит вес файла 1080p до комфортных ~600 МБ
        '720':  '31',  # Снизит вес файла 720p до идеальных ~500 МБ
        '480':  '31',   
        '360':  '33',   
    }

    @classmethod
    def build_transcode_cmd(cls, source_file: str, final_file: str, format_choice: str, 
                            encoder: str, duration: int, is_premium: bool) -> List[str]:
        """
        Строит команду для транскодирования видео с учетом выбранного энкодера
        и лимитов Telegram (2 ГБ или 4 ГБ).
        """
        bitrate_config = cls.TARGET_BITRATE.get(str(format_choice), {'target': '2000k', 'max': '3000k'})
        t_rate = bitrate_config['target']
        m_rate = bitrate_config['max']
        
        # Базовая команда
        cmd = ['ffmpeg', '-y', '-i', source_file, '-c:v', encoder]
        
        # --- СПЕЦИФИКА АППАРАТНЫХ КОДЕКОВ ---
        if 'amf' in encoder:
            # Аппаратное кодирование на AMD (RX 6000/7000 серий)
            # Используем Constant QP для абсолютной стабильности
            qp_val = cls.AMF_QP_GRID.get(str(format_choice), '28')
            cmd.extend(['-rc', 'cqp', '-qp_i', qp_val, '-qp_p', qp_val])
            
        elif 'nvenc' in encoder:
            # Аппаратное кодирование на NVIDIA (GTX/RTX серий)
            cmd.extend(['-rc', 'vbr', '-b:v', t_rate, '-maxrate', m_rate])
            
        elif 'qsv' in encoder:
            # Аппаратное кодирование на Intel (QuickSync)
            cmd.extend(['-b:v', t_rate, '-maxrate', m_rate])
            
        else:
            # Программное кодирование (CPU: libx264)
            # Динамический расчет CRF для защиты от переполнения лимитов Telegram
            est_bits = (int(m_rate.replace('k', '')) * 1024 + 128000) * duration
            max_safe_bits = (3900 if is_premium else 1900) * 1024 * 1024 * 8
            
            # Если видео угрожает превысить лимит - жмем сильнее (CRF 28)
            crf = 28 if est_bits > max_safe_bits else 18
            cmd.extend([
                '-preset', 'veryfast', 
                '-crf', str(crf), 
                '-maxrate', m_rate, 
                '-bufsize', f"{int(m_rate.replace('k', '')) * 2}k"
            ])
        
        # --- ОБЯЗАТЕЛЬНЫЙ ФИКС ДЛЯ АППАРАТНЫХ ЧИПОВ ---
        # YouTube отдает AV1 в 10-битном цвете (yuv420p10le). 
        # Аппаратные энкодеры падают при попытке сжать 10 бит.
        # Эта строчка принудительно конвертирует цвет в 8 бит.
        cmd.extend(['-pix_fmt', 'yuv420p'])
        
        # --- ОБЩИЕ ПАРАМЕТРЫ АУДИО И КОНТЕЙНЕРА ---
        cmd.extend(['-c:a', 'aac', '-b:a', '128k', '-movflags', '+faststart', final_file])
        
        return cmd

    @classmethod
    def build_cpu_fallback_cmd(cls, source_file: str, final_file: str, format_choice: str, 
                               duration: int, is_premium: bool) -> List[str]:
        """
        Строит безопасную команду для отката на CPU (libx264),
        если аппаратный кодер (GPU) завершился сбоем.
        """
        bitrate_config = cls.TARGET_BITRATE.get(str(format_choice), {'target': '2000k', 'max': '3000k'})
        m_rate = bitrate_config['max']
        
        est_bits = (int(m_rate.replace('k', '')) * 1024 + 128000) * duration
        max_safe_bits = (3900 if is_premium else 1900) * 1024 * 1024 * 8
        crf = 28 if est_bits > max_safe_bits else 18
        
        return [
            'ffmpeg', '-y', '-i', source_file,
            '-c:v', 'libx264', '-preset', 'veryfast', '-crf', str(crf),
            '-maxrate', m_rate, '-bufsize', f"{int(m_rate.replace('k', '')) * 2}k",
            '-pix_fmt', 'yuv420p', # Защита 10-bit цвета
            '-c:a', 'aac', '-b:a', '128k', '-movflags', '+faststart',
            final_file
        ]


# =====================================================================
# КЛАСС 8: ДВИЖОК ОБРАБОТКИ ВИДЕО (YT-DLP + АНАЛИЗАТОР FFPROBE)
# =====================================================================
class YouTubeEngine:
    """Ядро скачивания, анализа кодеков и маршрутизации транскодирования"""

    @staticmethod
    def check_system() -> None:
        """Проверка наличия FFmpeg и FFprobe в переменных среды Windows"""
        try:
            subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
            subprocess.run(['ffprobe', '-version'], capture_output=True, check=True)
            logger.info("✅ Движок FFmpeg/FFprobe успешно проинициализирован.")
        except FileNotFoundError:
            logger.critical("❌ КРИТИЧЕСКАЯ ОШИБКА: FFmpeg не найден в системе!")
            logger.critical("Установите FFmpeg и добавьте его в PATH Windows.")
            sys.exit(1)

    @staticmethod
    def probe_video(filepath: str) -> Tuple[int, int, int, str, str]:
        """
        Глубокий анализ медиафайла.
        Возвращает: Width, Height, Duration, VideoCodec, AudioCodec
        """
        try:
            cmd = ['ffprobe', '-v', 'error', '-show_entries', 'stream=width,height,duration,codec_name', '-of', 'json', filepath]
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
                    
            # Резервное чтение длительности из контейнера
            if dur == 0:
                cmd_f = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'json', filepath]
                res_f = subprocess.run(cmd_f, capture_output=True, text=True)
                dur = int(float(json.loads(res_f.stdout).get('format', {}).get('duration', 0) or 0))
                
            return w, h, dur, v_codec, a_codec
        except Exception as e:
            logger.error(f"Ошибка анализа FFprobe: {e}")
            return 0, 0, 0, '', ''

    @staticmethod
    def run_ffmpeg_checked(cmd: List[str], final_filename: str, user_id: int) -> Tuple[bool, str]:
        """
        Безопасный запуск FFmpeg с проверкой ошибок и размера выходного файла.
        Предотвращает отправку "пустышек" (0 байт) при сбое видеокарты.
        """
        logger.debug(f"Запуск FFmpeg: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
        
        # Проверка кода возврата и физического наличия/размера файла
        if result.returncode != 0 or not os.path.exists(final_filename) or os.path.getsize(final_filename) == 0:
            stderr_text = result.stderr if result.stderr else "Нет вывода ошибок от FFmpeg."
            logger.error(f"[{user_id}] Сбой FFmpeg (Код {result.returncode}): {stderr_text[-1000:]}")
            return False, stderr_text
            
        return True, ""

    @classmethod
    def download_and_optimize(cls, url: str, format_choice: str, video_id: str, 
                              user_id: int, duration: int, is_premium: bool) -> Tuple[str, Optional[str]]:
        """
        Главный метод-оркестратор: 
        1. Скачивает с YouTube
        2. Анализирует потоки
        3. Копирует (Direct Copy) или транскодирует (GPU/CPU)
        4. Создает обложку
        """
        ffmpeg_exe = shutil.which('ffmpeg')
        ffmpeg_dir = os.path.dirname(ffmpeg_exe) if ffmpeg_exe else None

        # --- Обработчик прогресса yt-dlp (Вывод в консоль) ---
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

        # --- Настройки yt-dlp ---
        opts = {
            'outtmpl': os.path.join(config.DOWNLOAD_DIR, f'{user_id}_{video_id}.%(ext)s'),
            'quiet': True, 
            'no_warnings': True, 
            'concurrent_fragment_downloads': 8,
            'writethumbnail': True,
            'progress_hooks': [ytdl_hook]
        }
        
        if ffmpeg_dir: 
            opts['ffmpeg_location'] = ffmpeg_dir
            
        if config.USE_PROXY: 
            opts['proxy'] = f'socks5://{config.PROXY_HOST}:{config.PROXY_PORT}'

        # Определение формата скачивания
        if format_choice == 'mp3':
            opts['format'] = 'bestaudio/best'
            opts['postprocessors'] = [
                {'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}, 
                {'key': 'FFmpegThumbnailsConvertor', 'format': 'jpg'}
            ]
        else:
            # Скачиваем лучшее видео, не привязываясь к H.264 (разрешаем VP9/AV1)
            opts['format'] = f'bestvideo[height<={format_choice}]+bestaudio/best[height<={format_choice}]/best[height<={format_choice}]'
            opts['merge_output_format'] = 'mp4'
            opts['postprocessors'] = [{'key': 'FFmpegThumbnailsConvertor', 'format': 'jpg'}]

        # --- СКАЧИВАНИЕ ---
        logger.info(f"[{user_id}] Начинаем скачивание потока {format_choice}p...")
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])

        # --- ОБРАБОТКА ПОСЛЕ СКАЧИВАНИЯ ---
        if format_choice == 'mp3':
            final_file = os.path.join(config.DOWNLOAD_DIR, f"{user_id}_{video_id}.mp3")
            if not os.path.exists(final_file): 
                final_file = cls._find_file(user_id, video_id)
            return final_file, cls._process_thumb(user_id, video_id)

        # Поиск скачанного видео-исходника
        source_file = cls._find_file(user_id, video_id)
        if not source_file or not os.path.exists(source_file):
            raise FileNotFoundError("Сбой загрузки: Исходный файл не найден на диске.")

        final_file = os.path.join(config.DOWNLOAD_DIR, f"{user_id}_{video_id}_optimized.mp4")
        
        # Считываем кодеки для принятия решения о транскодировании
        w, h, dur, v_codec, a_codec = cls.probe_video(source_file)
        logger.info(f"[{user_id}] Исходник: {w}x{h} | Кодеки: Video={v_codec}, Audio={a_codec}")

        success = False
        error_msg = ""

        # СЦЕНАРИЙ 1: Direct Copy (100% совместимо)
        if v_codec == 'h264' and (a_codec == 'aac' or a_codec == 'mp3'):
            logger.info(f"[{user_id}] ⚡ Применяем Direct Copy (без потери качества видео)...")
            cmd = ['ffmpeg', '-y', '-i', source_file, '-c:v', 'copy', '-c:a', 'copy', '-movflags', '+faststart', final_file]
            success, error_msg = cls.run_ffmpeg_checked(cmd, final_file, user_id)
            
        # СЦЕНАРИЙ 2: Аудио-конвертация (Видео H.264 совместимо, звук нет)
        elif v_codec == 'h264':
            logger.info(f"[{user_id}] ⚙️ Конвертируем только звук в AAC (видео без изменений)...")
            cmd = ['ffmpeg', '-y', '-i', source_file, '-c:v', 'copy', '-c:a', 'aac', '-b:a', '128k', '-movflags', '+faststart', final_file]
            success, error_msg = cls.run_ffmpeg_checked(cmd, final_file, user_id)
            
        # СЦЕНАРИЙ 3: Полное Транскодирование (Видео в VP9/AV1)
        else:
            logger.info(f"[{user_id}] 🏎️ Запуск транскодирования видео (Энкодер: {config.VIDEO_ENCODER})...")
            
            # Попытка аппаратного кодирования (GPU)
            if config.VIDEO_ENCODER != 'libx264':
                gpu_cmd = FFmpegBuilder.build_transcode_cmd(
                    source_file, final_file, format_choice, config.VIDEO_ENCODER, duration, is_premium
                )
                success, error_msg = cls.run_ffmpeg_checked(gpu_cmd, final_file, user_id)

            # Self-Healing: Автоматический откат на CPU (libx264), если аппаратный кодек дал сбой
            if not success:
                if config.VIDEO_ENCODER != 'libx264':
                    logger.warning(f"[{user_id}] ⚠️ Аппаратный кодек {config.VIDEO_ENCODER} завершился со сбоем. Автопереход на CPU (libx264)...")
                
                # Очистка битого файла перед перекодированием
                if os.path.exists(final_file):
                    try: os.remove(final_file)
                    except: pass
                
                cpu_cmd = FFmpegBuilder.build_cpu_fallback_cmd(
                    source_file, final_file, format_choice, duration, is_premium
                )
                success, error_msg = cls.run_ffmpeg_checked(cpu_cmd, final_file, user_id)
                
                # Если даже CPU упал - выбрасываем критическую ошибку
                if not success:
                    raise RuntimeError(f"FFmpeg полностью отказался обрабатывать файл. Лог ошибки: {error_msg[-300:]}")

        # Удаление тяжелого исходника
        try: os.remove(source_file)
        except Exception: pass

        return final_file, cls._process_thumb(user_id, video_id)

    @staticmethod
    def _find_file(user_id: int, video_id: str) -> Optional[str]:
        """Поиск файла по префиксу"""
        prefix = f"{user_id}_{video_id}."
        for file in os.listdir(config.DOWNLOAD_DIR):
            if file.startswith(prefix) and not file.lower().endswith(('.jpg', '.webp', '.part', '.ytdl')):
                return os.path.join(config.DOWNLOAD_DIR, file)
        return None

    @staticmethod
    def _process_thumb(user_id: int, video_id: str) -> Optional[str]:
        """Сжатие обложки видео под лимиты Telegram (< 320px)"""
        prefix = f"{user_id}_{video_id}."
        raw_thumb = None
        for file in os.listdir(config.DOWNLOAD_DIR):
            if file.startswith(prefix) and file.lower().endswith(('.jpg', '.webp')) and '_thumb' not in file:
                raw_thumb = os.path.join(config.DOWNLOAD_DIR, file)
                break
                
        if raw_thumb:
            thumb_file = os.path.join(config.DOWNLOAD_DIR, f"{user_id}_{video_id}_thumb.jpg")
            cmd = ['ffmpeg', '-y', '-i', raw_thumb, '-vf', "scale='if(gt(iw,ih),320,-1)':'if(gt(iw,ih),-1,320)'", '-q:v', '5', thumb_file]
            subprocess.run(cmd, capture_output=True)
            try: os.remove(raw_thumb)
            except Exception: pass
            return thumb_file
        return None


# =====================================================================
# КЛАСС 9: ПОТОКОВЫЙ ЗАГРУЗЧИК В TELEGRAM (АВАНГАРДНАЯ СЕТЬ)
# =====================================================================
class TelegramStreamUploader:
    """
    Умный загрузчик файлов в Telegram.
    Разбивает файл на чанки по 512 КБ и выгружает в 8 потоков.
    Обеспечивает строгое потребление ОЗУ не более 4 МБ, предотвращая MemoryError.
    """
    @staticmethod
    async def upload(client: TelegramClient, file_path: str, progress_callback=None):
        file_size = os.path.getsize(file_path)
        chunk_size = 512 * 1024 
        chunks_count = math.ceil(file_size / chunk_size)
        file_id = random.getrandbits(63) 
        
        # Очередь индексов
        queue = asyncio.Queue()
        for i in range(chunks_count): 
            await queue.put(i)
            
        uploaded_chunks = 0
        u_lock = asyncio.Lock()  # Блокировка счетчика
        f_lock = asyncio.Lock()  # Блокировка указателя файла
        
        async def worker(f):
            nonlocal uploaded_chunks
            while True:
                try: 
                    part_index = queue.get_nowait()
                except asyncio.QueueEmpty: 
                    break
                    
                # Безопасное чтение куска файла
                async with f_lock:
                    f.seek(part_index * chunk_size)
                    data = f.read(chunk_size)
                    
                # Загрузка с повторными попытками
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
                            logger.error(f"Сбой загрузки куска {part_index}: {e}")
                        await asyncio.sleep(1.5)
                        
                del data  # ПРИНУДИТЕЛЬНАЯ ОЧИСТКА ПАМЯТИ
                
                # Обновление прогресс-бара
                async with u_lock:
                    uploaded_chunks += 1
                    if progress_callback:
                        await progress_callback(min(uploaded_chunks * chunk_size, file_size), file_size)

        # Открываем файл один раз на чтение
        with open(file_path, 'rb') as f:
            workers = [worker(f) for _ in range(8)]
            await asyncio.gather(*workers)

        return types.InputFileBig(id=file_id, parts=chunks_count, name=os.path.basename(file_path))


# =====================================================================
# КЛАСС 10: ГЛАВНЫЙ КОНТРОЛЛЕР БОТА (ИНТЕРФЕЙС И РОУТИНГ)
# =====================================================================
class MonsterBotApp:
    def __init__(self, enable_userbot: bool):
        proxy = (socks.SOCKS5, config.PROXY_HOST, config.PROXY_PORT) if config.USE_PROXY else None
        
        # Инициализация Двойного Контура
        self.bot = TelegramClient('bot_session', config.API_ID, config.API_HASH, proxy=proxy)
        self.user = TelegramClient('user_session', config.API_ID, config.API_HASH, proxy=proxy) if enable_userbot else None
        
        self.bot_username: Optional[str] = None
        self.owner_id: Optional[int] = None
        self.is_premium: bool = False
        self.video_cache: Dict[str, dict] = {}
        
        YouTubeEngine.check_system()
        self._register_handlers()

    def _generate_keyboard(self, available_heights: set, video_id: str):
        """
        Генерирует инлайн-клавиатуру выбора качества.
        Умная функция: проверяет БД, и если файл закэширован, добавляет эмодзи ⚡.
        """
        all_options = [
            ("1080p (FHD)", 1080), 
            ("720p (HD)", 720), 
            ("480p", 480), 
            ("360p", 360)
        ]
        
        valid_buttons = []
        for label, res in all_options:
            if res in available_heights:
                # МАГИЯ ИНТЕРФЕЙСА: Проверка кэша БД
                if db.get_cached_file(video_id, str(res)):
                    btn_text = f"⚡ {label} (Кэш)"
                else:
                    btn_text = f"🎬 {label}"
                valid_buttons.append(Button.inline(btn_text, f"dl:{res}:{video_id}"))
                
        # Страховка для очень старых роликов
        if not valid_buttons:
            max_h = max(available_heights) if available_heights else 360
            if db.get_cached_file(video_id, str(max_h)):
                btn_text = f"⚡ {max_h}p (Кэш)"
            else:
                btn_text = f"🎬 {max_h}p"
            valid_buttons.append(Button.inline(btn_text, f"dl:{max_h}:{video_id}"))
            
        # Группировка кнопок (по 2 в ряд)
        kb = [valid_buttons[i:i+2] for i in range(0, len(valid_buttons), 2)]
        
        # Кнопка MP3
        if db.get_cached_file(video_id, 'mp3'):
            kb.append([Button.inline("⚡ MP3 Audio (Кэш)", f"dl:mp3:{video_id}")])
        else:
            kb.append([Button.inline("🎵 Скачать как MP3", f"dl:mp3:{video_id}")])
            
        return kb

    def _register_handlers(self):
        
        # ==========================================
        # ОБРАБОТЧИК: КОМАНДА /START
        # ==========================================
        @self.bot.on(events.NewMessage(pattern=r'^/start$'))
        async def start_handler(event):
            db.register_user(event.sender_id, event.sender.username)
            await event.respond(
                "👋 **Привет! Я Ultimate YouTube Downloader Bot.**\n\n"
                "💬 **Как пользоваться:**\n"
                "1. Отправь мне любую ссылку на видео YouTube или Shorts.\n"
                "2. Выбери желаемое качество с помощью кнопок.\n"
                "3. Я скачаю, сожму и пришлю видео прямо в этот чат!\n\n"
                "⚡ Если на кнопке есть значок **(Кэш)**, видео загрузится за долю секунды!\n\n"
                f"🛡️ *Ваш личный лимит загрузки: {'4 ГБ (Premium)' if self.is_premium else '2 ГБ (Standard)'}*"
            )

        # ==========================================
        # ОБРАБОТЧИК: ПАНЕЛЬ АДМИНИСТРАТОРА
        # ==========================================
        @self.bot.on(events.NewMessage(pattern=r'^/(admin|users|ban|unban|broadcast)'))
        async def admin_handler(event):
            if not self.owner_id or event.sender_id != self.owner_id:
                return await event.respond("❌ Недостаточно прав. Команда доступна только владельцу бота.")
            
            text = event.text.strip()
            
            # --- СТАТИСТИКА ---
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
                    f"🛡️ **Статус Premium:** `{'Активен (Лимит 4 ГБ)' if self.is_premium else 'Выключен (Лимит 2 ГБ)'}`\n\n"
                    "**Доступные команды:**\n"
                    "`/users` — Список всех пользователей и их ID\n"
                    "`/ban <ID>` — Заблокировать юзера\n"
                    "`/unban <ID>` — Разблокировать юзера\n"
                    "`/broadcast <Текст>` — Рассылка всем юзерам"
                )
                await event.respond(msg)
                
            # --- СПИСОК ПОЛЬЗОВАТЕЛЕЙ ---
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

            # --- БЛОКИРОВКА (БАН) ---
            elif text.startswith('/ban '):
                try:
                    target_id = int(text.split(' ')[1])
                    success = db.set_ban_status(target_id, True)
                    await event.respond(f"✅ Пользователь `{target_id}` заблокирован." if success else "❌ Пользователь не найден в базе.")
                except ValueError:
                    await event.respond("❌ Ошибка: ID должен быть числом. Пример: `/ban 12345678`")
                
            # --- РАЗБЛОКИРОВКА ---
            elif text.startswith('/unban '):
                try:
                    target_id = int(text.split(' ')[1])
                    success = db.set_ban_status(target_id, False)
                    await event.respond(f"✅ Пользователь `{target_id}` разблокирован." if success else "❌ Пользователь не найден в базе.")
                except ValueError:
                    await event.respond("❌ Ошибка: ID должен быть числом. Пример: `/unban 12345678`")
                
            # --- МАССОВАЯ РАССЫЛКА ---
            elif text.startswith('/broadcast '):
                message = text.replace('/broadcast ', '')
                users = db.get_all_users_ids()
                success_count = 0
                progress_msg = await event.respond(f"📣 Начинаю рассылку для {len(users)} пользователей...")
                
                for uid in users:
                    try:
                        await self.bot.send_message(uid, f"🔔 **Уведомление от Администратора:**\n\n{message}")
                        success_count += 1
                        await asyncio.sleep(0.5) # Защита от флуд-контроля Telegram
                    except Exception: pass
                    
                await progress_msg.edit(f"✅ **Рассылка завершена!**\nУспешно доставлено: `{success_count} / {len(users)}`")


        # ==========================================
        # ОБРАБОТЧИК: ПАРСИНГ ССЫЛОК YOUTUBE
        # ==========================================
        @self.bot.on(events.NewMessage())
        async def link_handler(event):
            if event.text.startswith('/'): return
            user_id = event.sender_id
            
            # Защита от заблокированных пользователей
            if db.check_banned(user_id):
                return await event.respond("❌ Вы заблокированы за нарушение правил использования бота.")

            url = Utils.extract_youtube_url(event.text)
            if not url: return  

            msg = await event.respond("🔍 **Проверяю видео на серверах YouTube...**")

            try:
                # Извлечение метаданных (без скачивания)
                ydl_opts = {'quiet': True}
                if config.USE_PROXY: 
                    ydl_opts['proxy'] = f'socks5://{config.PROXY_HOST}:{config.PROXY_PORT}'

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    if info.get('is_live'):
                        return await msg.edit("❌ Прямые трансляции не поддерживаются для скачивания.")
                        
                    v_id = info.get('id')
                    title = info.get('title', 'Без названия')
                    uploader = info.get('uploader', 'Unknown')
                    duration = int(info.get('duration', 0) or 0)
                    
                    available_heights = set(int(f.get('height')) for f in info.get('formats', []) if f.get('vcodec') != 'none' and f.get('height'))

                # Сохраняем в оперативный кэш
                self.video_cache[v_id] = {
                    'url': url, 'title': title, 'uploader': uploader, 'duration': duration, 'available_heights': list(available_heights)
                }
                
                # Очистка старого кэша для экономии ОЗУ
                if len(self.video_cache) > 500:
                    for k in list(self.video_cache.keys())[:100]: self.video_cache.pop(k, None)

                # Генерация карточки видео
                preview_text = (
                    f"🎥 **YouTube Downloader**\n━━━━━━━━━━━━━━━━━━━━\n"
                    f"📝 **Название:** `{title}`\n"
                    f"👤 **Канал:** {Utils.make_hashtag(uploader)}\n"
                    f"⏱️ **Длительность:** `{timedelta(seconds=duration)}`\n"
                    f"⚙️ **Макс. качество:** `{max(available_heights) if available_heights else '720'}p`\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"👇 *Выберите желаемый формат:* "
                )
                
                await msg.edit(preview_text, buttons=self._generate_keyboard(available_heights, v_id))

            except Exception as e:
                logger.error(f"Сбой анализа метаданных: {e}")
                await msg.edit(f"❌ **Сбой связи с YouTube:**\n`{str(e)}`")


        # ==========================================
        # ОБРАБОТЧИК: КЛИКИ ПО ИНЛАЙН-КНОПКАМ КАЧЕСТВА
        # ==========================================
        @self.bot.on(events.CallbackQuery(pattern=b'^dl:'))
        async def download_callback(event):
            user_id = event.sender_id
            
            try:
                parts = event.data.decode('utf-8').split(':')
                format_choice, video_id = parts[1], parts[2]
            except Exception: return

            cache = self.video_cache.get(video_id)
            if not cache:
                return await event.answer("❌ Сессия устарела. Отправьте ссылку еще раз.", alert=True)

            msg = await event.reply(f"⏳ **Запуск обработки...** Качество: `{format_choice if format_choice == 'mp3' else format_choice + 'p'}`")

            # =================================================================
            # 🔥 МАГИЯ КЭША: Мгновенная отправка готового файла (CDN)
            # =================================================================
            cached_file_id = db.get_cached_file(video_id, format_choice)
            if cached_file_id:
                try:
                    logger.info(f"[{user_id}] ⚡ Найдено в кэше базы данных! Мгновенная отправка.")
                    await msg.edit("⚡ **Найдено в локальном кэше! Мгновенная отправка...**")
                    caption = f"🎬 **{cache['title']}**\n\n👤 Автор: {Utils.make_hashtag(cache['uploader'])}"
                    
                    await self.bot.send_file(user_id, cached_file_id, caption=caption)
                    await msg.delete()
                    
                    db.update_stats(user_id, 0) # Трафик не тратится
                    return
                except Exception as e:
                    logger.warning(f"[{user_id}] Кэшированный файл недоступен (возможно удален с серверов ТГ). Качаем заново.")
                    db.remove_cached_file(video_id, format_choice)

            # =================================================================
            # СКАЧИВАНИЕ И ТРАНСКОДИРОВАНИЕ С НУЛЯ
            # =================================================================
            try:
                final_filename, thumb_file = await asyncio.to_thread(
                    YouTubeEngine.download_and_optimize, 
                    cache['url'], format_choice, video_id, user_id, cache['duration'], self.is_premium
                )

                file_size_mb = os.path.getsize(final_filename) / (1024 * 1024)

                # Защита от переполнения лимитов Telegram (Dual-Contour)
                has_premium_access = (user_id in config.PREMIUM_USERS) and self.is_premium
                max_limit_mb = 3950 if has_premium_access else 1950
                
                if file_size_mb > max_limit_mb:
                    await msg.edit(f"❌ **Сбой:** Файл весит {file_size_mb:.1f} МБ. Ваш лимит отправки: {'4 ГБ' if has_premium_access else '2 ГБ'}.")
                    await Utils.safe_remove(final_filename)
                    if thumb_file: await Utils.safe_remove(thumb_file)
                    return

                await msg.edit("⚙️ **Видео готово. Подключение к серверам Telegram...**")
                start_time, last_update = time.time(), [0]

                # Асинхронный прогресс-бар выгрузки
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

                # Подготовка метаданных для отправки
                caption = f"🎬 **{cache['title']}**\n\n👤 Автор: {Utils.make_hashtag(cache['uploader'])}"
                attributes = []
                
                if format_choice == 'mp3':
                    attributes.append(DocumentAttributeAudio(duration=cache['duration'], title=cache['title']))
                else:
                    w, h, dur, _, _ = YouTubeEngine.probe_video(final_filename)
                    attributes.append(DocumentAttributeVideo(duration=dur or cache['duration'], w=w or 1920, h=h or int(format_choice), supports_streaming=True))

                # --- ИНТЕЛЛЕКТУАЛЬНЫЙ РАСПРЕДЕЛИТЕЛЬ ОТПРАВИТЕЛЯ (ДВОЙНОЙ КОНТУР) ---
                sender = self.user if (file_size_mb > 1950 and self.is_premium) else self.bot
                
                uploaded_file = await TelegramStreamUploader.upload(sender, final_filename, upload_progress)
                await msg.edit("⚡ **Файл передан на сервер Telegram. Финализация...**")
                
                # Отправка файла адресату
                sent_msg = None
                if sender == self.user:
                    target = self.bot_username if user_id == self.owner_id else user_id
                    sent_msg = await sender.send_file(target, uploaded_file, caption=caption, thumb=thumb_file, attributes=attributes, supports_streaming=True)
                else:
                    sent_msg = await sender.send_file(user_id, uploaded_file, caption=caption, thumb=thumb_file, attributes=attributes, supports_streaming=True)

                # =================================================================
                # 🔥 МАГИЯ КЭША: Сохранение файла в БД для будущих пользователей
                # =================================================================
                # Мы можем кэшировать только файлы, отправленные самим Ботом (< 2ГБ).
                if sender == self.bot and sent_msg and sent_msg.document:
                    try:
                        bot_file_id = utils.pack_bot_file_id(sent_msg.document)
                        db.save_cached_file(video_id, format_choice, bot_file_id)
                    except Exception as e:
                        logger.warning(f"Не удалось закэшировать файл {video_id}: {e}")

                # Очистка локального диска и завершение
                db.update_stats(user_id, file_size_mb)
                await Utils.safe_remove(final_filename)
                if thumb_file: await Utils.safe_remove(thumb_file)
                await msg.delete()

                logger.info(f"[{user_id}] ✅ Видео ({file_size_mb:.1f} МБ) успешно доставлено.")

            except Exception as e:
                logger.error(f"[{user_id}] Критический сбой: {e}", exc_info=True)
                await msg.edit(f"❌ **Внутренняя ошибка системы:**\n`{str(e)}`")
                # Экстренная аварийная очистка мусора на диске
                for f in os.listdir(config.DOWNLOAD_DIR):
                    if f.startswith(str(user_id)):
                        await Utils.safe_remove(os.path.join(config.DOWNLOAD_DIR, f))

    async def start(self):
        """Инициализация клиентов и запуск слушателей"""
        await self.bot.start(bot_token=config.BOT_TOKEN)
        bot_me = await self.bot.get_me()
        self.bot_username = bot_me.username
        
        if self.user:
            logger.info("🔑 Инициализация Premium-юзербота...")
            await self.user.start()
            user_me = await self.user.get_me()
            self.owner_id = user_me.id
            self.is_premium = getattr(user_me, 'premium', False)
            
            # Автоматически добавляем владельца в список Premium-пользователей
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
# ИНТЕРАКТИВНОЕ КОНСОЛЬНОЕ МЕНЮ (НАСТРОЙКА И ЗАПУСК)
# =====================================================================
def interactive_cli_menu() -> bool:
    """Стильное консольное TUI-меню для управления сервером бота"""
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
        print(f"  [5] 🗑️ Сбросить Premium-авторизацию (Удалить сессию)")
        print("  [0] ❌ Закрыть панель")
        print("========================================================================")
        
        choice = input("👉 Выберите номер действия (0-5): ").strip()
        
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
            for f in ["user_session.session", "user_session.session-journal"]:
                if os.path.exists(f): os.remove(f)
            print("\n✅ Сессия успешно сброшена! Бот переведен в стандартный бесплатный режим (2 ГБ).")
            time.sleep(2)
            
        elif choice == "0":
            sys.exit(0)


# =====================================================================
# ТОЧКА ВХОДА (ENTRY POINT) И ЗАЩИЩЕННЫЙ ЗАПУСК
# =====================================================================
if __name__ == "__main__":
    # Запускаем интерактивное консольное меню настройки перед стартом
    enable_userbot = interactive_cli_menu()
    
    # Запускаем бота внутри единого блока try-except для чистого гашения KeyboardInterrupt (Ctrl+C)
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
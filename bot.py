# =====================================================================
#     __  __                  _             ____         _   
#    |  \/  | ___  _ __  ___ | |_ ___ _ __ | __ )  ___  | |_ 
#    | |\/| |/ _ \| '_ \/ __|| __/ _ \ '__||  _ \ / _ \ | __|
#    | |  | | (_) | | | \__ \| ||  __/ |   | |_) | (_) || |_ 
#    |_|  |_|\___/|_| |_|___/ \__\___|_|   |____/ \___/  \__|
#                                                            
#          === YOUTUBE MONSTER BOT (ULTIMATE EDITION) ===
#           🤖 DUAL-CONTOUR + ENTERPRISE OOP + AMD AMF
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

# Проверка и импорт зависимостей
try:
    from telethon import TelegramClient, events, functions, types
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
# КЛАСС 1: ПРОДВИНУТОЕ ЛОГИРОВАНИЕ
# =====================================================================
class LoggerSetup:
    """Настройка двойного логирования (Консоль + Файл bot.log)"""
    @staticmethod
    def setup_logger():
        logger = logging.getLogger("MonsterBot")
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - [%(levelname)s] - %(message)s', datefmt='%H:%M:%S')

        # Обработчик для консоли
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # Обработчик для файла
        file_handler = logging.FileHandler("bot.log", encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        return logger

logger = LoggerSetup.setup_logger()

# =====================================================================
# КЛАСС 2: УПРАВЛЕНИЕ КОНФИГУРАЦИЕЙ И ИНТЕРАКТИВНЫМ МЕНЮ
# =====================================================================
class BotConfig:
    """Класс для чтения и безопасного редактирования файла .env"""
    def __init__(self):
        self.env_file = self._find_or_create_env()
        load_dotenv(self.env_file)
        
        self.API_ID = int(os.getenv("API_ID", "0"))
        self.API_HASH = os.getenv("API_HASH", "")
        self.BOT_TOKEN = os.getenv("BOT_TOKEN", "")
        self.DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "./downloads")
        self.VIDEO_ENCODER = os.getenv("VIDEO_ENCODER", "libx264")
        self.USE_PROXY = os.getenv("USE_PROXY", "False").lower() == "true"
        self.PROXY_HOST = os.getenv("PROXY_HOST", "127.0.0.1")
        self.PROXY_PORT = int(os.getenv("PROXY_PORT", "10808"))
        
        os.makedirs(self.DOWNLOAD_DIR, exist_ok=True)
        self._validate_keys()

    def _find_or_create_env(self):
        """Интеллектуальный поиск файла конфигурации (защита от скрытых расширений Windows)"""
        possible_files = [".env", ".evn", ".env.txt"]
        for f in possible_files:
            if os.path.exists(f):
                return f
        
        # Если файла нет, генерируем идеальный шаблон
        logger.warning("Файл конфигурации не найден. Создаю новый .env файл...")
        template = (
            "API_ID=0\n"
            "API_HASH=\n"
            "BOT_TOKEN=\n"
            "DOWNLOAD_DIR=./downloads\n"
            "VIDEO_ENCODER=libx264\n"
            "USE_PROXY=False\n"
            "PROXY_HOST=127.0.0.1\n"
            "PROXY_PORT=10808\n"
        )
        with open(".env", "w", encoding="utf-8") as file:
            file.write(template)
        return ".env"

    def _validate_keys(self):
        if self.API_ID == 0 or not self.API_HASH or not self.BOT_TOKEN:
            logger.critical("❌ КРИТИЧЕСКАЯ ОШИБКА: Ключи API_ID, API_HASH или BOT_TOKEN не заполнены в файле .env!")
            sys.exit(1)

    def update_key(self, key, value):
        """Безопасное обновление ключа прямо в файле .env"""
        set_key(self.env_file, key, str(value))
        os.environ[key] = str(value)
        setattr(self, key, value)
        logger.info(f"Настройка [{key}] успешно изменена на: {value}")

config = BotConfig()

# =====================================================================
# КЛАСС 3: ЛОКАЛЬНАЯ БАЗА ДАННЫХ SQLITE3 (ДЛЯ АДМИНКИ)
# =====================================================================
class SQLiteDB:
    """Управление локальной базой данных: статистика, пользователи, баны"""
    def __init__(self, db_name="monster_bot.db"):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self._initialize_tables()

    def _initialize_tables(self):
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
        self.conn.commit()

    def register_user(self, user_id, username):
        """Добавляет пользователя в базу при первом запуске /start"""
        self.cursor.execute('INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)', (user_id, username))
        self.conn.commit()

    def update_stats(self, user_id, size_mb):
        """Обновляет счетчик скачанных мегабайт и видео для пользователя"""
        self.cursor.execute('''
            UPDATE users 
            SET total_videos = total_videos + 1, 
                total_mb_downloaded = total_mb_downloaded + ? 
            WHERE user_id = ?
        ''', (size_mb, user_id))
        self.conn.commit()

    def check_banned(self, user_id):
        """Проверка, не находится ли пользователь в черном списке"""
        self.cursor.execute('SELECT is_banned FROM users WHERE user_id = ?', (user_id,))
        result = self.cursor.fetchone()
        return bool(result[0]) if result else False

    def set_ban_status(self, user_id, status: bool):
        """Блокировка или разблокировка пользователя"""
        self.cursor.execute('UPDATE users SET is_banned = ? WHERE user_id = ?', (int(status), user_id))
        self.conn.commit()
        return self.cursor.rowcount > 0

    def get_all_users_ids(self):
        """Получить список всех ID для массовой рассылки (Broadcast)"""
        self.cursor.execute('SELECT user_id FROM users WHERE is_banned = 0')
        return [row[0] for row in self.cursor.fetchall()]

    def get_global_statistics(self):
        """Получить общую статистику для панели Администратора"""
        self.cursor.execute('SELECT COUNT(*), SUM(total_videos), SUM(total_mb_downloaded) FROM users')
        row = self.cursor.fetchone()
        return {
            "total_users": row[0] or 0,
            "total_videos": row[1] or 0,
            "total_gb": (row[2] or 0) / 1024  # Конвертация МБ в ГБ
        }

db = SQLiteDB()

# =====================================================================
# КЛАСС 4: СИСТЕМНЫЕ УТИЛИТЫ И ПРОГРЕСС-БАРЫ
# =====================================================================
class Utils:
    """Сборник статических методов для интерфейса и файловой системы"""
    
    @staticmethod
    def format_bytes(size):
        if size is None or size <= 0: return "0.00 Б"
        power = 2**10
        n = 0
        labels = {0: 'Б', 1: 'КБ', 2: 'МБ', 3: 'ГБ', 4: 'ТБ'}
        while size > power and n < 4:
            size /= power
            n += 1
        return f"{size:.2f} {labels[n]}"

    @staticmethod
    def make_progress_bar(percent, length=12):
        """Рисует красивый текстовый прогресс-бар [██████▒▒▒▒]"""
        filled = int(length * (percent / 100.0))
        bar = "█" * filled + "▒" * (length - filled)
        return f"[{bar}]"

    @staticmethod
    def make_hashtag(author_name):
        clean_name = re.sub(r'[^\w\s]', '', author_name.strip())
        return f"#{re.sub(r'\s+', '_', clean_name).lower()}"

    @staticmethod
    def extract_youtube_url(text):
        match = re.search(r'(https?://(?:www\.)?youtu(?:be\.com/watch\?v=|\.be/|be\.com/embed/|be\.com/v/|be\.com/shorts/)[^\s]+)', text)
        return match.group(1) if match else None

    @staticmethod
    async def safe_remove(filepath, retries=5, delay=1.5):
        """Безопасное удаление файлов с обходом блокировки дескрипторов Windows"""
        for _ in range(retries):
            try:
                if os.path.exists(filepath):
                    os.remove(filepath)
                    return True
            except PermissionError:
                await asyncio.sleep(delay)
            except Exception as e:
                logger.error(f"Ошибка удаления файла {filepath}: {e}")
                return False
        return False

# =====================================================================
# КЛАСС 5: ДВИЖОК ОБРАБОТКИ ВИДЕО (YT-DLP + FFMPEG)
# =====================================================================
class YouTubeEngine:
    """Ядро скачивания, анализа кодеков и аппаратного транскодирования"""
    
    # Умная сетка VBR битрейтов для идеального баланса веса и качества
    BITRATE_GRID = {
        '1080': {'target': '3000k', 'max': '4500k'}, 
        '720':  {'target': '1500k', 'max': '2500k'},  
        '480':  {'target': '800k',  'max': '1200k'},   
        '360':  {'target': '450k',  'max': '700k'},    
    }

    @staticmethod
    def check_system():
        try:
            subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
            subprocess.run(['ffprobe', '-version'], capture_output=True, check=True)
            logger.info("✅ Движок FFmpeg/FFprobe успешно проинициализирован.")
        except FileNotFoundError:
            logger.critical("❌ КРИТИЧЕСКАЯ ОШИБКА: FFmpeg не найден в системе!")
            sys.exit(1)

    @staticmethod
    def probe_video(filepath):
        """Глубокий анализ видеофайла: разрешение, длительность, кодеки"""
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
                    
            if dur == 0:
                cmd_f = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'json', filepath]
                res_f = subprocess.run(cmd_f, capture_output=True, text=True)
                dur = int(float(json.loads(res_f.stdout).get('format', {}).get('duration', 0) or 0))
            return w, h, dur, v_codec, a_codec
        except Exception as e:
            logger.error(f"Ошибка FFprobe: {e}")
            return 0, 0, 0, '', ''

    @classmethod
    def download_and_optimize(cls, url, format_choice, video_id, user_id, duration, is_premium):
        """Главный метод: скачивает с YouTube и оптимизирует файл под Telegram"""
        ffmpeg_exe = shutil.which('ffmpeg')
        ffmpeg_dir = os.path.dirname(ffmpeg_exe) if ffmpeg_exe else None

        # Обработчик прогресса скачивания в консоль
        def ytdl_hook(d):
            if d['status'] == 'downloading':
                d_bytes = d.get('downloaded_bytes') or 0
                t_bytes = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
                spd = d.get('speed')
                eta = d.get('eta')
                
                spd_str = Utils.format_bytes(spd) if spd else "0 Б"
                eta_str = str(timedelta(seconds=int(eta))) if eta else "00:00:00"
                
                if t_bytes > 0:
                    pct = (d_bytes / t_bytes) * 100
                    bar = Utils.make_progress_bar(pct, 15)
                    sys.stdout.write(f"\r📥 YT-DLP {bar} {pct:.1f}% | {spd_str}/s | Осталось: {eta_str}      ")
                sys.stdout.flush()
            elif d['status'] == 'finished':
                sys.stdout.write("\n")

        # Конфигурация скачивателя
        opts = {
            'outtmpl': os.path.join(config.DOWNLOAD_DIR, f'{user_id}_{video_id}.%(ext)s'),
            'quiet': True, 'no_warnings': True, 'writethumbnail': True,
            'progress_hooks': [ytdl_hook]
        }
        
        if ffmpeg_dir: opts['ffmpeg_location'] = ffmpeg_dir
        if config.USE_PROXY: opts['proxy'] = f'socks5://{config.PROXY_HOST}:{config.PROXY_PORT}'

        if format_choice == 'mp3':
            opts['format'] = 'bestaudio/best'
            opts['postprocessors'] = [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}, {'key': 'FFmpegThumbnailsConvertor', 'format': 'jpg'}]
        else:
            opts['format'] = f'bestvideo[height<={format_choice}]+bestaudio/best[height<={format_choice}]/best[height<={format_choice}]'
            opts['merge_output_format'] = 'mp4'
            opts['postprocessors'] = [{'key': 'FFmpegThumbnailsConvertor', 'format': 'jpg'}]

        # СКАЧИВАНИЕ
        logger.info(f"[{user_id}] Начинаем скачивание потока {format_choice}p...")
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])

        # ПОИСК СКАЧАННОГО ИСХОДНИКА
        if format_choice == 'mp3':
            final_file = os.path.join(config.DOWNLOAD_DIR, f"{user_id}_{video_id}.mp3")
            if not os.path.exists(final_file): final_file = cls._find_file(user_id, video_id)
            return final_file, cls._process_thumb(user_id, video_id)

        source_file = cls._find_file(user_id, video_id)
        if not source_file or not os.path.exists(source_file):
            raise FileNotFoundError("Сбой загрузки: Исходный файл не найден на диске.")

        final_file = os.path.join(config.DOWNLOAD_DIR, f"{user_id}_{video_id}_optimized.mp4")
        w, h, dur, v_codec, a_codec = cls.probe_video(source_file)
        logger.info(f"[{user_id}] Исходник: {w}x{h} | Кодеки: Video={v_codec}, Audio={a_codec}")

        # ЛОГИКА ТРАНСКОДИРОВАНИЯ И СЖАТИЯ
        if v_codec == 'h264' and a_codec in ['aac', 'mp3']:
            logger.info(f"[{user_id}] ⚡ Применяем Direct Copy (мгновенная упаковка без пережатия)")
            subprocess.run(['ffmpeg', '-y', '-i', source_file, '-c:v', 'copy', '-c:a', 'copy', '-movflags', '+faststart', final_file], capture_output=True)
            
        elif v_codec == 'h264':
            logger.info(f"[{user_id}] ⚙️ Транскодируем только аудиодорожку в AAC")
            subprocess.run(['ffmpeg', '-y', '-i', source_file, '-c:v', 'copy', '-c:a', 'aac', '-b:a', '128k', '-movflags', '+faststart', final_file], capture_output=True)
            
        else:
            logger.info(f"[{user_id}] 🏎️ Запуск полного транскодирования видео (Энкодер: {config.VIDEO_ENCODER})")
            cfg = cls.BITRATE_GRID.get(str(format_choice), {'target': '2000k', 'max': '3000k'})
            
            cmd = ['ffmpeg', '-y', '-i', source_file, '-c:v', config.VIDEO_ENCODER]
            
            if 'amf' in config.VIDEO_ENCODER:    # Аппаратный кодек AMD
                cmd.extend(['-rc', 'vbr_peak', '-b:v', cfg['target'], '-maxrate', cfg['max']])
            elif 'nvenc' in config.VIDEO_ENCODER: # Аппаратный кодек NVIDIA
                cmd.extend(['-rc', 'vbr', '-b:v', cfg['target'], '-maxrate', cfg['max']])
            elif 'qsv' in config.VIDEO_ENCODER:   # Аппаратный кодек Intel
                cmd.extend(['-b:v', cfg['target'], '-maxrate', cfg['max']])
            else:                                 # Программный кодек (CPU)
                est_bits = (int(cfg['max'].replace('k', '')) * 1024 + 128000) * duration
                max_safe = (3900 if is_premium else 1900) * 1024 * 1024 * 8
                crf = 28 if est_bits > max_safe else 18
                cmd.extend(['-preset', 'veryfast', '-crf', str(crf), '-maxrate', cfg['max'], '-bufsize', f"{int(cfg['max'].replace('k', '')) * 2}k"])
            
            cmd.extend(['-c:a', 'aac', '-b:a', '128k', '-movflags', '+faststart', final_file])
            subprocess.run(cmd, capture_output=True)

        # Очистка исходника
        try: os.remove(source_file)
        except: pass

        return final_file, cls._process_thumb(user_id, video_id)

    @staticmethod
    def _find_file(user_id, video_id):
        prefix = f"{user_id}_{video_id}."
        for file in os.listdir(config.DOWNLOAD_DIR):
            if file.startswith(prefix) and not file.lower().endswith(('.jpg', '.webp', '.part', '.ytdl')):
                return os.path.join(config.DOWNLOAD_DIR, file)
        return None

    @staticmethod
    def _process_thumb(user_id, video_id):
        prefix = f"{user_id}_{video_id}."
        raw_thumb = None
        for file in os.listdir(config.DOWNLOAD_DIR):
            if file.startswith(prefix) and file.lower().endswith(('.jpg', '.webp')) and '_thumb' not in file:
                raw_thumb = os.path.join(config.DOWNLOAD_DIR, file)
                break
        if raw_thumb:
            thumb_file = os.path.join(config.DOWNLOAD_DIR, f"{user_id}_{video_id}_thumb.jpg")
            # Сжимаем под лимиты Telegram (<320px)
            subprocess.run(['ffmpeg', '-y', '-i', raw_thumb, '-vf', "scale='if(gt(iw,ih),320,-1)':'if(gt(iw,ih),-1,320)'", '-q:v', '5', thumb_file], capture_output=True)
            try: os.remove(raw_thumb)
            except: pass
            return thumb_file
        return None

# =====================================================================
# КЛАСС 6: ПОТОКОВЫЙ ЗАГРУЗЧИК В TELEGRAM (АВАНГАРДНАЯ СЕТЬ)
# =====================================================================
class TelegramStreamUploader:
    """Умный загрузчик: делит файл на куски, держит в ОЗУ не более 4 МБ, выгружает в 8 потоков"""
    @staticmethod
    async def upload(client, file_path, progress_callback=None):
        file_size = os.path.getsize(file_path)
        chunk_size = 512 * 1024 
        chunks_count = math.ceil(file_size / chunk_size)
        file_id = random.getrandbits(63) 
        sem = asyncio.Semaphore(8) 
        
        queue = asyncio.Queue()
        for i in range(chunks_count): await queue.put(i)
            
        uploaded = 0
        u_lock, f_lock = asyncio.Lock(), asyncio.Lock()  
        
        async def worker(f):
            nonlocal uploaded
            while True:
                try: part_index = queue.get_nowait()
                except asyncio.QueueEmpty: break
                    
                async with f_lock:
                    f.seek(part_index * chunk_size)
                    data = f.read(chunk_size)
                    
                for attempt in range(4): # 4 попытки на случай сетевых сбоев
                    try:
                        await client(functions.upload.SaveBigFilePartRequest(
                            file_id=file_id, file_part=part_index, file_total_parts=chunks_count, bytes=data
                        ))
                        break
                    except Exception as e:
                        if attempt == 3: logger.error(f"Сбой загрузки куска {part_index}: {e}")
                        await asyncio.sleep(1.5)
                        
                del data # Жесткая очистка памяти
                
                async with u_lock:
                    uploaded += 1
                    if progress_callback:
                        await progress_callback(min(uploaded * chunk_size, file_size), file_size)

        with open(file_path, 'rb') as f:
            await asyncio.gather(*[worker(f) for _ in range(8)])

        return types.InputFileBig(id=file_id, parts=chunks_count, name=os.path.basename(file_path))

# =====================================================================
# КЛАСС 7: ГЛАВНЫЙ КОНТРОЛЛЕР БОТА (РОУТИНГ И ИНТЕРФЕЙС)
# =====================================================================
class MonsterBotApp:
    def __init__(self, enable_userbot):
        proxy = (socks.SOCKS5, config.PROXY_HOST, config.PROXY_PORT) if config.USE_PROXY else None
        
        # Инициализация Двойного Контура
        self.bot = TelegramClient('bot_session', config.API_ID, config.API_HASH, proxy=proxy)
        self.user = TelegramClient('user_session', config.API_ID, config.API_HASH, proxy=proxy) if enable_userbot else None
        
        self.bot_username = None
        self.owner_id = None
        self.is_premium = False
        self.video_cache = {}
        
        YouTubeEngine.check_system()
        self._register_handlers()

    def _generate_keyboard(self, available_heights, video_id):
        all_options = [("🎬 1080p (FHD)", 1080), ("🎬 720p (HD)", 720), ("🎬 480p", 480), ("🎬 360p", 360)]
        valid_buttons = [Button.inline(lbl, f"dl:{res}:{video_id}") for lbl, res in all_options if res in available_heights]
        
        if not valid_buttons:
            max_h = max(available_heights) if available_heights else 360
            valid_buttons.append(Button.inline(f"🎬 {max_h}p", f"dl:{max_h}:{video_id}"))
            
        kb = [valid_buttons[i:i+2] for i in range(0, len(valid_buttons), 2)]
        kb.append([Button.inline("🎵 Скачать как MP3 Audio", f"dl:mp3:{video_id}")])
        return kb

    def _register_handlers(self):
        
        # 1. ОБРАБОТЧИК КОМАНДЫ /start
        @self.bot.on(events.NewMessage(pattern=r'^/start$'))
        async def start_handler(event):
            db.register_user(event.sender_id, event.sender.username)
            await event.respond(
                "👋 **Привет! Я Ultimate YouTube Downloader Bot.**\n\n"
                "💬 **Как пользоваться:**\n"
                "1. Отправь мне любую ссылку на видео YouTube или Shorts.\n"
                "2. Выбери желаемое качество с помощью кнопок.\n"
                "3. Я скачаю, сожму и пришлю видео прямо в этот чат!\n\n"
                f"⚡ *Максимальный лимит для тебя: {'4 ГБ (Premium)' if self.is_premium else '2 ГБ (Standard)'}*"
            )

        # 2. ПАНЕЛЬ АДМИНИСТРАТОРА (/admin, /users, /ban, /unban, /broadcast)
        @self.bot.on(events.NewMessage(pattern=r'^/(admin|users|ban|unban|broadcast)'))
        async def admin_handler(event):
            if not self.owner_id or event.sender_id != self.owner_id:
                return await event.respond("❌ Недостаточно прав. Команда доступна только владельцу бота.")
            
            text = event.text.strip()
            
            # --- Статистика ---
            if text == '/admin':
                stats = db.get_global_statistics()
                msg = (
                    "👑 **ПАНЕЛЬ АДМИНИСТРАТОРА** 👑\n"
                    "━━━━━━━━━━━━━━━━━━━━\n"
                    f"👥 **Пользователей в базе:** `{stats['total_users']}`\n"
                    f"🎬 **Скачано роликов:** `{stats['total_videos']}`\n"
                    f"💾 **Сгенерировано трафика:** `{stats['total_gb']:.2f} ГБ`\n"
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
                
            # --- Список пользователей для получения их ID ---
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

            # --- Блокировка ---
            elif text.startswith('/ban '):
                try:
                    target_id = int(text.split(' ')[1])
                    success = db.set_ban_status(target_id, True)
                    await event.respond(f"✅ Пользователь `{target_id}` заблокирован." if success else "❌ Пользователь не найден в базе.")
                except ValueError:
                    await event.respond("❌ Ошибка: ID должен быть числом. Пример: `/ban 12345678`")
                
            # --- Разблокировка ---
            elif text.startswith('/unban '):
                try:
                    target_id = int(text.split(' ')[1])
                    success = db.set_ban_status(target_id, False)
                    await event.respond(f"✅ Пользователь `{target_id}` разблокирован." if success else "❌ Пользователь не найден в базе.")
                except ValueError:
                    await event.respond("❌ Ошибка: ID должен быть числом. Пример: `/unban 12345678`")
                
            # --- Массовая рассылка ---
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

        # 3. ОБРАБОТЧИК ССЫЛОК YOUTUBE
        @self.bot.on(events.NewMessage())
        async def link_handler(event):
            if event.text.startswith('/'): return
            user_id = event.sender_id
            
            # Проверка на бан
            if db.check_banned(user_id):
                return await event.respond("❌ Вы заблокированы за нарушение правил использования бота.")

            url = Utils.extract_youtube_url(event.text)
            if not url: return  

            msg = await event.respond("🔍 **Проверяю видео на серверах YouTube...**")

            try:
                ydl_opts = {'quiet': True}
                if config.USE_PROXY: ydl_opts['proxy'] = f'socks5://{config.PROXY_HOST}:{config.PROXY_PORT}'

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    if info.get('is_live'):
                        return await msg.edit("❌ Прямые трансляции не поддерживаются для скачивания.")
                        
                    v_id = info.get('id')
                    title = info.get('title', 'Без названия')
                    uploader = info.get('uploader', 'Unknown')
                    duration = int(info.get('duration', 0) or 0)
                    
                    available_heights = set(int(f.get('height')) for f in info.get('formats', []) if f.get('vcodec') != 'none' and f.get('height'))

                # Сохраняем в кэш
                self.video_cache[v_id] = {
                    'url': url, 'title': title, 'uploader': uploader, 'duration': duration, 'available_heights': list(available_heights)
                }
                
                # Очистка старого кэша
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
                
                await msg.edit(preview_text, buttons=self._generate_keyboard(available_heights, v_id))

            except Exception as e:
                logger.error(f"Сбой анализа метаданных: {e}")
                await msg.edit(f"❌ **Сбой связи с YouTube:**\n`{str(e)}`")

        # 4. ОБРАБОТЧИК КЛИКОВ ПО КНОПКАМ КАЧЕСТВА
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

            msg = await event.reply(f"⏳ **Запуск процесса...** Качество: `{format_choice if format_choice == 'mp3' else format_choice + 'p'}`")

            try:
                # 1. СКАЧИВАНИЕ И ТРАНСКОДИРОВАНИЕ (В ФОНЕ)
                final_filename, thumb_file = await asyncio.to_thread(
                    YouTubeEngine.download_and_optimize, 
                    cache['url'], format_choice, video_id, user_id, cache['duration'], self.is_premium
                )

                file_size_mb = os.path.getsize(final_filename) / (1024 * 1024)
                max_limit_mb = 3950 if self.is_premium else 1950

                # Защита от переполнения лимитов Telegram
                if file_size_mb > max_limit_mb:
                    await msg.edit(f"❌ **Сбой:** Файл весит {file_size_mb:.1f} МБ. Ваш лимит отправки: {'4 ГБ' if self.is_premium else '2 ГБ'}.")
                    await Utils.safe_remove(final_filename)
                    if thumb_file: await Utils.safe_remove(thumb_file)
                    return

                await msg.edit("⚙️ **Видео готово. Подключение к серверам Telegram...**")
                start_time, last_update = time.time(), [0]

                # 2. ПОТОКОВАЯ ЗАГРУЗКА С ПРОГРЕСС-БАРОМ
                async def upload_progress(current, total):
                    now = time.time()
                    if now - last_update[0] > 2.5 or current == total:
                        speed = current / (now - start_time) if (now - start_time) > 0 else 0
                        eta = (total - current) / speed if speed > 0 else 0
                        percent = (current / total * 100) if total > 0 else 0
                        
                        bar = Utils.make_progress_bar(percent, 12)
                        contour_name = 'Premium Контур (4 GB)' if file_size_mb > 1950 else 'Standard Контур (2 GB)'
                        
                        try:
                            await msg.edit(
                                f"🚀 **Выгрузка в Telegram ({contour_name}):**\n\n"
                                f"📊 {bar} **{percent:.1f}%**\n"
                                f"⚡ Скорость: **{speed/(1024*1024):.1f} МБ/с**\n"
                                f"⏳ Осталось: **{timedelta(seconds=int(eta))}**"
                            )
                        except Exception: pass
                        last_update[0] = now

                # 3. ИНТЕЛЛЕКТУАЛЬНЫЙ РОУТИНГ ОТПРАВКИ (ДВОЙНОЙ КОНТУР)
                caption = f"🎬 **{cache['title']}**\n\n👤 Автор: {Utils.make_hashtag(cache['uploader'])}"
                attributes = []
                
                if format_choice == 'mp3':
                    attributes.append(DocumentAttributeAudio(duration=cache['duration'], title=cache['title']))
                else:
                    w, h, dur, _, _ = YouTubeEngine.probe_video(final_filename)
                    attributes.append(DocumentAttributeVideo(duration=dur or cache['duration'], w=w or 1920, h=h or int(format_choice), supports_streaming=True))

                # Выбор агента отправки (Бот или Юзербот)
                sender = self.user if (file_size_mb > 1950 and self.is_premium) else self.bot
                
                uploaded_file = await TelegramStreamUploader.upload(sender, final_filename, upload_progress)
                await msg.edit("⚡ **Файл передан на сервер Telegram. Финализация...**")
                
                # Отправка файла адресату
                if sender == self.user:
                    target = self.bot_username if user_id == self.owner_id else user_id
                    await sender.send_file(target, uploaded_file, caption=caption, thumb=thumb_file, attributes=attributes, supports_streaming=True)
                else:
                    await sender.send_file(user_id, uploaded_file, caption=caption, thumb=thumb_file, attributes=attributes, supports_streaming=True)

                # 4. ОБНОВЛЕНИЕ БАЗЫ ДАННЫХ И ОЧИСТКА
                db.update_stats(user_id, file_size_mb)
                await Utils.safe_remove(final_filename)
                if thumb_file: await Utils.safe_remove(thumb_file)
                await msg.delete()

                logger.info(f"[{user_id}] ✅ Видео ({file_size_mb:.1f} МБ) успешно доставлено пользователю.")

            except Exception as e:
                logger.error(f"[{user_id}] Критический сбой: {e}", exc_info=True)
                await msg.edit(f"❌ **Внутренняя ошибка системы:**\n`{str(e)}`")
                # Экстренная очистка
                for f in os.listdir(config.DOWNLOAD_DIR):
                    if f.startswith(str(user_id)):
                        await Utils.safe_remove(os.path.join(config.DOWNLOAD_DIR, f))

    async def start(self):
        """Инициализация клиентов и запуск слушателей"""
        await self.bot.start(bot_token=config.BOT_TOKEN)
        bot_me = await self.bot.get_me()
        self.bot_username = bot_me.username
        
        if self.user:
            logger.info("🔑 Авторизация в личном Premium-аккаунте...")
            await self.user.start()
            user_me = await self.user.get_me()
            self.owner_id = user_me.id
            self.is_premium = getattr(user_me, 'premium', False)
            
            logger.info("🚀 СИСТЕМА ДВОЙНОГО КОНТУРА АКТИВИРОВАНА!")
            logger.info(f"👑 Аккаунт владельца: {user_me.first_name} | Premium-статус: {'АКТИВЕН' if self.is_premium else 'ОТСУТСТВУЕТ'}")
            
            await asyncio.gather(self.bot.disconnected, self.user.disconnected)
        else:
            self.is_premium = False
            self.owner_id = None
            logger.info("🚀 БОТ УСПЕШНО ЗАПУЩЕН В СТАНДАРТНОМ РЕЖИМЕ!")
            logger.info("⚡ Максимальный лимит: 2 ГБ (Premium-юзербот отключен)")
            
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
def interactive_cli_menu():
    """Стильное консольное меню для управления сервером бота"""
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
# ТОЧКА ВХОДА И УПРАВЛЕНИЕ ЗАПУСКОМ
# =====================================================================
if __name__ == "__main__":
    print_banner()
    
    # Запускаем интерактивное консольное меню настройки перед стартом
    enable_userbot = interactive_cli_menu()
    
    # Запускаем бота внутри единого блока try-except для чистого гашения KeyboardInterrupt
    try:
        app = MonsterBotApp(enable_userbot)
        asyncio.run(app.start())
    except KeyboardInterrupt:
        print("\n👋 Бот успешно остановлен пользователем. Всего доброго!")
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
# =====================================================================
# ТОЧКА ВХОДА (ENTRY POINT)
# =====================================================================
if __name__ == "__main__":
    # Запускаем интерактивное консольное меню настройки перед стартом
    enable_userbot = interactive_cli_menu()
    
    # Инициализация и запуск главного приложения
    app = MonsterBotApp(enable_userbot)
    asyncio.run(app.start())
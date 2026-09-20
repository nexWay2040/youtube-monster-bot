"""
channel_monitor.py — автономный бот-агент с умным определением
игр, жанров, обзоров и реальной жизни (без тяжёлых нейросетей).
"""

import os
import re
import sys
import json
import time
import asyncio
from typing import Optional

import yt_dlp
from telethon import TelegramClient, events, Button
from telethon.tl.types import DocumentAttributeVideo
from dotenv import load_dotenv

load_dotenv()

import bot as core

# ─────────────────────────────────────────────
# НАСТРОЙКИ
# ─────────────────────────────────────────────
MONITOR_BOT_TOKEN = os.getenv("MONITOR_BOT_TOKEN", "")
TARGET_CHANNEL = os.getenv("TARGET_CHANNEL", "@blogeridownload")
POLL_INTERVAL_MINUTES = float(os.getenv("MONITOR_POLL_INTERVAL_MINUTES", "15"))
VIDEOS_PER_CHANNEL_CHECK = int(os.getenv("MONITOR_VIDEOS_PER_CHECK", "15"))
MONITOR_VIDEO_QUALITY = os.getenv("MONITOR_VIDEO_QUALITY", "720")

MONITOR_BOOTSTRAP_LOOKBACK_HOURS = float(os.getenv("MONITOR_BOOTSTRAP_LOOKBACK_HOURS", "24"))
MONITOR_BOOTSTRAP_FRESH_CHECK = int(os.getenv("MONITOR_BOOTSTRAP_FRESH_CHECK", "3"))

LEGACY_CHANNELS_FILE = os.getenv("MONITOR_CHANNELS_FILE", "channels.json")

if not MONITOR_BOT_TOKEN:
    core.term_log("⛔ CRITICAL", "MONITOR_BOT_TOKEN не задан в .env", core.Colors.RED)
    sys.exit(1)

pending: dict = {}
check_lock = asyncio.Lock()
videos_in_progress: set = set()

# ─────────────────────────────────────────────
# БАЗА ИГР И ЖАНРОВ
# ─────────────────────────────────────────────
POPULAR_GAMES = [
    (r'\b(minecraft|майнкрафт|майн)\b', '#Minecraft'),
    (r'\b(roblox|роблокс)\b', '#Roblox'),
    (r'\b(gta\s*5|гта\s*5|гта\s*v|gta\s*v|гта|gta)\b', '#GTA5'),
    (r'\b(brawl\s*stars|бравл\s*старс|бравл)\b', '#BrawlStars'),
    (r'\b(standoff\s*2|стандофф\s*2|стандофф|стандик)\b', '#Standoff2'),
    (r'\b(counter[- ]*strike\s*2|cs\s*2|кс\s*2|csgo|cs:go|ксго)\b', '#CS2'),
    (r'\b(dota\s*2|дота\s*2|дота|дотка)\b', '#Dota2'),
    (r'\b(genshin\s*impact|геншин\s*импакт|геншин)\b', '#GenshinImpact'),
    (r'\b(honkai[:\s]*star\s*rail|хонкай)\b', '#HonkaiStarRail'),
    (r'\b(fnaf|фнаф|five\s*nights\s*at\s*freddy)\b', '#FNAF'),
    (r'\b(pubg|пабг|пубг)\b', '#PUBG'),
    (r'\b(fortnite|фортнайт)\b', '#Fortnite'),
    (r'\b(rust|раст)\b', '#Rust'),
    (r'\b(lethal\s*company|летал\s*компани)\b', '#LethalCompany'),
    (r'\b(phasmophobia|фазмофобия|фазма)\b', '#Phasmophobia'),
    (r'\b(poppy\s*playtime|поппи\s*плейтайм)\b', '#PoppyPlaytime'),
    (r'\b(among\s*us|амонг\s*ас|амонгас)\b', '#AmongUs'),
    (r'\b(geometry\s*dash|геометрия\s*даш|гд)\b', '#GeometryDash'),
    (r'\b(terraria|террария)\b', '#Terraria'),
    (r'\b(the\s*sims|симс)\b', '#TheSims'),
    (r'\b(valorant|валорант)\b', '#Valorant'),
    (r'\b(apex\s*legends|апекс)\b', '#ApexLegends'),
    (r'\b(world\s*of\s*tanks|мир\s*танков|танки|wot)\b', '#МирТанков'),
    (r'\b(tanks\s*blitz|blitz|блиц)\b', '#TanksBlitz'),
    (r'\b(elden\s*ring|элден\s*ринг)\b', '#EldenRing'),
    (r'\b(cyberpunk|киберпанк)\b', '#Cyberpunk2077'),
    (r'\b(witcher|ведьмак)\b', '#Ведьмак3'),
    (r'\b(stalker|сталкер)\b', '#Сталкер'),
    (r'\b(subnautica|сабнатика)\b', '#Subnautica'),
    (r'\b(fall\s*guys|фол\s*гайз)\b', '#FallGuys'),
    (r'\b(cuphead|капхед)\b', '#Cuphead'),
    (r'\b(undertale|андертейл)\b', '#Undertale'),
    (r'\b(detroit[:\s]*become\s*human|детройт)\b', '#Detroit'),
    (r'\b(clash\s*royale|клеш\s*рояль|клеш)\b', '#ClashRoyale'),
    (r'\b(sims\s*4|симс\s*4)\b', '#Sims4'),
    (r'\b(euro\s*truck|етс\s*2|ets\s*2)\b', '#ETS2'),
    (r'\b(beamng|бимка)\b', '#BeamNG'),
    (r'\b(garry\'?s\s*mod|гаррис\s*мод|гмод|gmod)\b', '#GarrysMod'),
    (r'\b(dead\s*by\s*daylight|дбд|dbd)\b', '#DBD'),
    (r'\b(atomic\s*heart|атомик\s*харт)\b', '#AtomicHeart'),
    (r'\b(assassin\'?s\s*creed|ассасин)\b', '#AssassinsCreed'),
    # ── Хорроры / инди / analog horror — часто встречаются у обзорщиков ужастиков ──
    (r'\b(the\s*walten\s*files|волтен\s*файлс|файлы\s*волтена)\b', '#TheWaltenFiles'),
    (r'\b(bendy\s*and\s*the\s*ink\s*machine|бенди)\b', '#Bendy'),
    (r'\b(hello\s*neighbor|привет\s*сосед)\b', '#HelloNeighbor'),
    (r'\b(baldi\'?s\s*basics|балди)\b', '#BaldisBasics'),
    (r'\b(granny|бабка|гренни)\b', '#Granny'),
    (r'\bdoors\b(?!\s*(?:closed|open|way))', '#DOORS'),
    (r'\b(silent\s*hill|сайлент\s*хилл)\b', '#SilentHill'),
    (r'\b(resident\s*evil|резидент\s*ивл|биохазард)\b', '#ResidentEvil'),
    (r'\b(outlast|аутласт)\b', '#Outlast'),
    (r'\b(amnesia|амнезия)\b', '#Amnesia'),
    (r'\bscp\b', '#SCP'),
    (r'\b(backrooms|бэкрумс|задворки)\b', '#Backrooms'),
    (r'\b(little\s*nightmares|литл\s*найтмэрс)\b', '#LittleNightmares'),
    (r'\b(content\s*warning)\b', '#ContentWarning'),
    (r'\b(choo[- ]*choo\s*charles|чух[- ]*чух\s*чарльз)\b', '#ChooChooCharles'),
    (r'\b(buckshot\s*roulette)\b', '#BuckshotRoulette'),
    (r'\b(inscryption)\b', '#Inscryption'),
    (r'\b(piggy)\b', '#Piggy'),
    (r'\b(schedule\s*1|schedule\s*i)\b', '#ScheduleI'),
    (r'\b(dayz|дэй\s*зэт)\b', '#DayZ'),
    (r'\b(analog\s*horror|аналоговый\s*хоррор)\b', '#АналоговыйХоррор'),
    (r'\b(martha\s*is\s*dead)\b', '#MarthaIsDead'),
    (r'\b(fears\s*to\s*fathom)\b', '#FearsToFathom'),
    (r'\b(propnight)\b', '#Propnight'),
    (r'\b(five\s*nights\s*at\s*freddy\'?s?\s*security\s*breach|секьюрити\s*брич)\b', '#FNAFSecurityBreach'),
]

# Общий разбор — когда конкретную игру не узнали ни по одному паттерну выше
# (например, малоизвестная инди-игра). Ищем характерные для геймерских
# заголовков конструкции вида "Прохождение X", "Играю в X" и т.п. и берём
# то, что похоже на название, вместо того чтобы просто сдаться без тега.
GENERIC_GAME_PATTERNS = [
    r'(?:прохождение|играю\s+в|играем\s+в|обзор\s+на\s+игру|review)[:\s]+([A-ZА-ЯЁ][\w\s:\'\-]{2,40}?)(?=\s*[-–—|#]|\s+часть\b|\s+\d|$)',
    r'^([A-ZА-ЯЁ][\w\s:\'\-]{2,40}?)\s*[-–—]\s*(?:прохождение|часть|обзор|эпизод)\b',
]

def guess_generic_game(title: str) -> Optional[str]:
    for pattern in GENERIC_GAME_PATTERNS:
        m = re.search(pattern, title, re.IGNORECASE)
        if m:
            candidate = m.group(1).strip(" -:")
            # отсекаем совсем короткие/мусорные совпадения
            if 2 <= len(candidate) <= 30 and not candidate.isdigit():
                return format_clean_hashtag(candidate)
    return None

def format_clean_hashtag(text: str) -> str:
    clean = re.sub(r'[^\w\s]', '', text or '').strip()
    words = clean.split()
    if not words:
        return ""
    tag = "".join(w.capitalize() for w in words)
    return "#" + tag

def detect_video_tags(meta: dict, title: str) -> list:
    """
    Интеллектуальный анализатор: определяет формат ролика (обзор, теория,
    челлендж, реальная жизнь) и название игры без использования нейросетей.
    """
    desc = (meta.get("description") or "").strip()
    text = f"{title} {desc}".lower()
    categories = [c.lower() for c in (meta.get("categories") or [])]
    tags = [str(t).lower() for t in (meta.get("tags") or [])]

    found_tags = []

    # 1. Проверка на РЕАЛЬНУЮ ЖИЗНЬ / IRL (отсекаем путаницу с играми)
    is_irl = bool(re.search(r'\b(в реальной жизни|в реале|в реальности|на самом деле|вживую|irl|live action)\b', text))

    # 2. Определение формата ролика (Обзоры, Теории, Челленджи, Реакции)
    if re.search(r'\b(обзор|мнение|распаковка|тест|review|разбор игры|первый взгляд|стоит ли)\b', title, re.IGNORECASE):
        found_tags.append("🔍 #Обзор")
    elif re.search(r'\b(теория|теории|сюжет|лор|вся правда|секреты|пасхалки|айсберг|история создания|концовка|объяснение)\b', title, re.IGNORECASE):
        found_tags.append("🧠 #Теории")
    elif re.search(r'\b(реакция|смотрит|реагирует|реакция на|react)\b', title, re.IGNORECASE):
        found_tags.append("👀 #Реакция")
    elif re.search(r'\b(челлендж|24 часа|100 дней|кто последний|эксперимент|challenge|я выжил|я провел|попробуй не)\b', title, re.IGNORECASE):
        found_tags.append("🏆 #Челлендж")
    elif is_irl:
        found_tags.append("⛺ #ВРеале")

    # Хорроры (специфика Винди / Куплинова)
    if re.search(r'\b(инди хоррор|страшная игра|horror|жуткая игра|хоррор игра|пугалка)\b', title, re.IGNORECASE):
        if "🔍 #Обзор" not in found_tags:
            found_tags.append("👻 #Хоррор")

    # 3. Определение названия Игры
    game_tag = None

    # А. Официальное поле YouTube Gaming (самое точное)
    raw_game = meta.get("game")
    if raw_game and isinstance(raw_game, str) and len(raw_game.strip()) > 1:
        for pattern, gtag in POPULAR_GAMES:
            if re.search(pattern, raw_game, re.IGNORECASE):
                game_tag = gtag
                break
        if not game_tag:
            game_tag = format_clean_hashtag(raw_game)

    # Б. Поиск по строчке "Игра: Название" в описании
    if not game_tag:
        m_game = re.search(r'(?:игра|game)[:\s]+([^\n\r,]+)', desc, re.IGNORECASE)
        if m_game:
            found_name = m_game.group(1).strip()
            for pattern, gtag in POPULAR_GAMES:
                if re.search(pattern, found_name, re.IGNORECASE):
                    game_tag = gtag
                    break
            if not game_tag and len(found_name) < 25:
                game_tag = format_clean_hashtag(found_name)

    # В. Поиск по популярным играм в названии
    if not game_tag:
        for pattern, gtag in POPULAR_GAMES:
            if re.search(pattern, title, re.IGNORECASE):
                game_tag = gtag
                break

    # Г. Поиск по тегам ролика
    if not game_tag:
        for t in tags:
            for pattern, gtag in POPULAR_GAMES:
                if re.search(pattern, t, re.IGNORECASE):
                    game_tag = gtag
                    break
            if game_tag:
                break

    # Д. Игра не из списка (инди/малоизвестная) — пробуем вытащить название
    # из характерных конструкций заголовка вместо того, чтобы сдаться.
    # Применяем только если ролик похож на геймерский контент (категория
    # Gaming или явные игровые слова в названии), чтобы не вешать левый
    # хештег на видео не про игры.
    if not game_tag:
        looks_like_gaming = (
            "gaming" in categories
            or re.search(r'\b(прохождение|играю|играем|геймплей|gameplay|летсплей)\b', text)
        )
        if looks_like_gaming:
            guess = guess_generic_game(title)
            if guess:
                game_tag = guess

    # Если игра найдена — добавляем тег с джойстиком
    if game_tag:
        found_tags.append(f"🎮 {game_tag}")

    return found_tags

# ─────────────────────────────────────────────
# УТИЛИТЫ И КАНАЛЫ
# ─────────────────────────────────────────────
def slugify(text: str) -> str:
    key = re.sub(r"\s+", "_", (text or "").strip().lower())
    key = re.sub(r"[^\w]", "", key, flags=re.UNICODE)
    if not key:
        key = f"ch{int(time.time())}"
    base = key
    n = 2
    while core.db.monitor_get_channel(key):
        key = f"{base}_{n}"
        n += 1
    return key

def normalize_channel_url(raw: str) -> str:
    raw = (raw or "").strip()
    if raw.startswith("@"):
        raw = f"https://www.youtube.com/{raw}"
    if "youtube.com" not in raw and "youtu.be" not in raw:
        return ""
    if not raw.startswith("http"):
        raw = "https://" + raw
    if "/videos" not in raw:
        raw = raw.rstrip("/") + "/videos"
    return raw

def migrate_legacy_channels_json():
    if not os.path.exists(LEGACY_CHANNELS_FILE):
        return
    try:
        with open(LEGACY_CHANNELS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        core.term_log("⚠️ MONITOR", f"Не удалось прочитать {LEGACY_CHANNELS_FILE}: {e}", core.Colors.YELLOW)
        return

    imported = 0
    for entry in data:
        key = entry.get("key") or slugify(entry.get("name", ""))
        existing = core.db.monitor_get_channel(key)
        if existing and existing.get("url"):
            continue
        name = entry.get("name") or key
        url = entry.get("url", "")
        tag = core.hashtag(name)
        core.db.monitor_add_channel(key, name, url, tag)
        if entry.get("bootstrapped"):
            core.db.monitor_set_bootstrapped(key)
        imported += 1

    if imported:
        core.term_log("📦 MONITOR", f"Докатил {imported} канал(ов) из {LEGACY_CHANNELS_FILE} в базу", core.Colors.CYAN)

    try:
        done_path = LEGACY_CHANNELS_FILE + ".imported"
        if os.path.exists(done_path):
            os.remove(done_path)
        os.rename(LEGACY_CHANNELS_FILE, done_path)
        core.term_log("📦 MONITOR", f"{LEGACY_CHANNELS_FILE} переименован в {done_path}", core.Colors.CYAN)
    except Exception as e:
        core.term_log("⚠️ MONITOR", f"Не удалось переименовать {LEGACY_CHANNELS_FILE}: {e}", core.Colors.YELLOW)

# ─────────────────────────────────────────────
# ПОЛУЧЕНИЕ СПИСКА ВИДЕО
# ─────────────────────────────────────────────
def fetch_latest_videos(channel_url: str, limit: int) -> list:
    opts = core.ytdlp_opts()
    opts["extract_flat"] = True
    opts["playlistend"] = limit
    opts["skip_download"] = True
    ea = dict(opts.get("extractor_args") or {})
    ea["youtubetab"] = ea.get("youtubetab", []) + ["skip=authcheck"]
    opts["extractor_args"] = ea
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(channel_url, download=False)
    except Exception as e:
        core.term_log("⚠️ MONITOR", f"Не удалось получить список видео {channel_url}: {e}", core.Colors.YELLOW)
        return []

    entries = info.get("entries") or []
    videos = []
    for e in entries:
        if not e:
            continue
        vid = e.get("id")
        if not vid:
            continue
        videos.append({
            "id": vid,
            "title": e.get("title") or f"Видео {vid}",
            "url": e.get("url") or f"https://www.youtube.com/watch?v={vid}",
        })
    return videos

def get_video_timestamp(video_url: str):
    try:
        opts = core.ytdlp_opts()
        opts["skip_download"] = True
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
        return info.get("timestamp") or info.get("release_timestamp")
    except Exception:
        return None

# ─────────────────────────────────────────────
# СКАЧИВАНИЕ + ПУБЛИКАЦИЯ
# ─────────────────────────────────────────────
async def post_video(client: TelegramClient, channel: dict, video: dict):
    vid = video["id"]
    url = video["url"]
    title = video["title"]
    name = channel["name"]
    
    author_tag = channel.get("hashtag") or core.hashtag(name)
    if not author_tag.startswith("#"):
        author_tag = "#" + author_tag.lstrip("#")

    raw_target = channel.get("target_channel") or TARGET_CHANNEL
    targets = [t.strip() for t in raw_target.split(",") if t.strip()]
    if not targets:
        targets = [TARGET_CHANNEL]

    if vid in videos_in_progress:
        core.term_log("⏭️ MONITOR", f"[{name}] {vid} уже качается — пропуск дубля", core.Colors.YELLOW)
        return
    videos_in_progress.add(vid)

    core.term_log("⬇️ MONITOR", f"[{name}] Новое видео: {title} ({vid}) → {', '.join(targets)}", core.Colors.CYAN)

    try:
        # Извлекаем метаданные для умного распознавания игры и жанра
        meta = {}
        try:
            opts_meta = core.ytdlp_opts()
            opts_meta["skip_download"] = True
            with yt_dlp.YoutubeDL(opts_meta) as ydl:
                meta = await asyncio.to_thread(ydl.extract_info, url, download=False) or {}
        except Exception:
            pass

        # Умный анализ тегов ролика (обзор, теория, хоррор, игра, челлендж)
        tags_list = detect_video_tags(meta, title)
        if tags_list:
            core.term_log("🏷️ TAGS", f"[{name}] Найдено: {' '.join(tags_list)}", core.Colors.GREEN)

        path = await asyncio.to_thread(core.download_video, url, MONITOR_VIDEO_QUALITY, 0, vid, "orig", None)
        thumb = core.make_thumb(0, str(vid))
        info = core.probe(path)

        if not info["width"]:
            raise ValueError("скачанный файл не содержит видеодорожку (возможен блок/18+)")

        duration = info["duration"]
        w = info["width"]
        h = info["height"]

        # Формируем аккуратный пост
        caption_lines = [f"🎬 **{title}**\n"]
        if tags_list:
            caption_lines.append(" ".join(tags_list))
        caption_lines.append(f"👤 {author_tag}")

        caption = "\n".join(caption_lines)

        for target in targets:
            await client.send_file(
                target,
                path,
                caption=caption,
                thumb=thumb,
                attributes=[DocumentAttributeVideo(duration=duration, w=w, h=h, supports_streaming=True)],
            )

        core.db.monitor_mark_posted(vid, name, title)
        core.term_log("✅ MONITOR", f"[{name}] Опубликовано: {title}", core.Colors.GREEN)

    except Exception as e:
        core.term_log("❌ MONITOR", f"[{name}] Ошибка публикации {vid}: {e}", core.Colors.RED)
    finally:
        videos_in_progress.discard(vid)
        for fname in os.listdir(core.DOWNLOAD_DIR):
            if str(vid) in fname:
                try:
                    os.remove(os.path.join(core.DOWNLOAD_DIR, fname))
                except Exception:
                    pass

# ─────────────────────────────────────────────
# ПРОВЕРКА КАНАЛОВ
# ─────────────────────────────────────────────
async def check_channel(client: TelegramClient, channel: dict):
    key = channel["key"]
    name = channel["name"]
    url = channel["url"]

    videos = await asyncio.to_thread(fetch_latest_videos, url, VIDEOS_PER_CHANNEL_CHECK)
    if not videos:
        return

    if not channel.get("bootstrapped"):
        now = time.time()
        fresh_to_post = []
        for i, v in enumerate(videos):
            is_fresh = False
            if i < MONITOR_BOOTSTRAP_FRESH_CHECK:
                ts = await asyncio.to_thread(get_video_timestamp, v["url"])
                if ts and (now - ts) <= MONITOR_BOOTSTRAP_LOOKBACK_HOURS * 3600:
                    is_fresh = True
            if is_fresh:
                fresh_to_post.append(v)
            else:
                core.db.monitor_mark_posted(v["id"], name, v["title"])
        core.db.monitor_set_bootstrapped(key)
        core.term_log(
            "📌 MONITOR",
            f"[{name}] Первый запуск — запомнено {len(videos)} видео, свежих: {len(fresh_to_post)}",
            core.Colors.CYAN
        )
        for v in reversed(fresh_to_post):
            await post_video(client, channel, v)
            await asyncio.sleep(3)
        return

    new_videos = [v for v in videos if not core.db.monitor_is_posted(v["id"])]
    for v in reversed(new_videos):
        await post_video(client, channel, v)
        await asyncio.sleep(3)

async def run_all_channels(client: TelegramClient):
    async with check_lock:
        for channel in core.db.monitor_list_channels():
            try:
                await check_channel(client, channel)
            except Exception as e:
                core.term_log("❌ MONITOR", f"Ошибка проверки канала {channel.get('name')}: {e}", core.Colors.RED)

async def poll_loop(client: TelegramClient):
    while True:
        await run_all_channels(client)
        await asyncio.sleep(POLL_INTERVAL_MINUTES * 60)

# ─────────────────────────────────────────────
# УПРАВЛЕНИЕ ИЗ TELEGRAM
# ─────────────────────────────────────────────
def is_owner(event) -> bool:
    return event.sender_id == core.OWNER_ID

def main_menu_buttons():
    return [
        [Button.inline("➕ Добавить канал", b"menu:add"), Button.inline("📺 Список каналов", b"menu:list")],
        [Button.inline("🔍 Проверить всё сейчас", b"menu:checkall")],
    ]

def channel_list_buttons(channels: list):
    rows = []
    for ch in channels:
        rows.append([
            Button.inline(f"📺 {ch['name']}", f"ch:info:{ch['key']}".encode()),
            Button.inline("🗑", f"ch:del:{ch['key']}".encode()),
        ])
    rows.append([Button.inline("➕ Добавить канал", b"menu:add"), Button.inline("🔙 Меню", b"menu:back")])
    return rows

def register_handlers(client: TelegramClient):
    @client.on(events.NewMessage(pattern=r"^/(start|menu)(\s|$)"))
    async def cmd_menu(event):
        if not is_owner(event):
            return
        pending.pop(event.sender_id, None)
        n = len(core.db.monitor_list_channels())
        await event.respond(
            f"🤖 **Монитор-бот**\nОтслеживается каналов: {n}\nПубликует в: {TARGET_CHANNEL}\nКачество: {MONITOR_VIDEO_QUALITY}p",
            buttons=main_menu_buttons()
        )

    @client.on(events.NewMessage(pattern=r"^/channels(\s|$)"))
    async def cmd_channels(event):
        if not is_owner(event):
            return
        channels = core.db.monitor_list_channels()
        if not channels:
            await event.respond("Каналов пока нет.", buttons=[[Button.inline("➕ Добавить канал", b"menu:add")]])
            return
        await event.respond("📺 **Каналы:**", buttons=channel_list_buttons(channels))

    @client.on(events.NewMessage(pattern=r"^/addchannel(\s|$)"))
    async def cmd_addchannel(event):
        if not is_owner(event):
            return
        pending[event.sender_id] = {"action": "add", "step": "url", "data": {}}
        await event.respond("Пришли ссылку на YouTube-канал (например https://www.youtube.com/@handle):")

    @client.on(events.NewMessage(pattern=r"^/check(@\w+)?(\s|$)"))
    async def cmd_check(event):
        if not is_owner(event):
            return
        args = event.raw_text.split(maxsplit=1)
        target_key = args[1].strip().lower() if len(args) > 1 else None

        if check_lock.locked():
            await event.respond("⏳ Проверка уже идёт — дождись завершения.")
            return

        if target_key:
            channel = core.db.monitor_get_channel(target_key)
            if not channel:
                await event.respond(f"⚠️ Канал с key=`{target_key}` не найден. Смотри /channels")
                return
            await event.respond(f"🔍 Проверяю только «{channel['name']}»...")
            async with check_lock:
                await check_channel(client, channel)
            await event.respond("✅ Готово.")
        else:
            n = len(core.db.monitor_list_channels())
            await event.respond(f"🔍 Внеочередная проверка всех {n} каналов...")
            await run_all_channels(client)
            await event.respond("✅ Проверка завершена.")

    @client.on(events.NewMessage(pattern=r"^/forget(\s|$)"))
    async def cmd_forget(event):
        if not is_owner(event):
            return
        args = event.raw_text.split(maxsplit=1)
        if len(args) < 2:
            await event.respond("Использование: `/forget VIDEO_ID` (например `ux9UjdJuiVY`).")
            return
        vid = args[1].strip()
        ok = core.db.monitor_forget(vid)
        await event.respond(f"✅ Забыл `{vid}`, теперь он снова новый." if ok else f"⚠️ `{vid}` не найден.")

    @client.on(events.NewMessage())
    async def on_any_message(event):
        if not is_owner(event):
            return
        text = event.raw_text.strip()
        if text.startswith("/"):
            return
        state = pending.get(event.sender_id)
        if not state:
            return

        if state["action"] == "add":
            data = state["data"]
            if state["step"] == "url":
                url = normalize_channel_url(text)
                if not url:
                    await event.respond("⚠️ Это не похоже на ссылку YouTube. Пришли ещё раз, например https://www.youtube.com/@handle")
                    return
                data["url"] = url
                state["step"] = "name"
                await event.respond("Как называть канал в подписи к видео? (например: Дюшес)")
            elif state["step"] == "name":
                data["name"] = text
                data["suggested_tag"] = core.hashtag(text)
                state["step"] = "hashtag"
                await event.respond(f"Хештег автора? Отправь свой (например `#Дюшес`) или `-`, чтобы оставить `{data['suggested_tag']}`:")
            elif state["step"] == "hashtag":
                tag = text if text != "-" else data["suggested_tag"]
                if not tag.startswith("#"):
                    tag = "#" + tag.lstrip("#")
                data["hashtag"] = tag
                state["step"] = "target"
                await event.respond(
                    f"В какой Telegram-канал публиковать? Пришли @username (или -100id), "
                    f"можно несколько через запятую, или `-` для канала по умолчанию (`{TARGET_CHANNEL}`):"
                )
            elif state["step"] == "target":
                target = None if text == "-" else text
                key = slugify(data["name"])
                core.db.monitor_add_channel(key, data["name"], data["url"], data["hashtag"], target)
                pending.pop(event.sender_id, None)
                await event.respond(
                    f"✅ Добавил канал **{data['name']}** (`{key}`)\nХештег: {data['hashtag']}\nURL: {data['url']}\n"
                    f"Публикует в: {target or TARGET_CHANNEL + ' (по умолчанию)'}\n\n"
                    f"При следующей проверке бот начнёт следить за новыми роликами.",
                    buttons=main_menu_buttons()
                )

        elif state["action"] == "edit_hashtag":
            key = state["data"]["key"]
            tag = text
            if not tag.startswith("#"):
                tag = "#" + tag.lstrip("#")
            core.db.monitor_set_hashtag(key, tag)
            pending.pop(event.sender_id, None)
            await event.respond(f"✅ Хештег для `{key}` теперь: {tag}", buttons=main_menu_buttons())

        elif state["action"] == "edit_target":
            key = state["data"]["key"]
            target = None if text == "-" else text
            core.db.monitor_set_target(key, target)
            pending.pop(event.sender_id, None)
            await event.respond(
                f"✅ Канал публикации для `{key}` теперь: {target or TARGET_CHANNEL + ' (по умолчанию)'}",
                buttons=main_menu_buttons()
            )

    @client.on(events.CallbackQuery())
    async def on_callback(event):
        if event.sender_id != core.OWNER_ID:
            await event.answer("Не для тебя 🙂", alert=True)
            return
        data = event.data.decode()

        if data == "menu:back":
            await event.edit("🤖 **Монитор-бот** — выбери действие:", buttons=main_menu_buttons())

        elif data == "menu:add":
            pending[event.sender_id] = {"action": "add", "step": "url", "data": {}}
            await event.respond("Пришли ссылку на YouTube-канал (например https://www.youtube.com/@handle):")
            await event.answer()

        elif data == "menu:list":
            channels = core.db.monitor_list_channels()
            if not channels:
                await event.edit("Каналов пока нет.", buttons=[[Button.inline("➕ Добавить канал", b"menu:add")]])
            else:
                await event.edit("📺 **Каналы:**", buttons=channel_list_buttons(channels))

        elif data == "menu:checkall":
            await event.answer("Запускаю проверку...")
            await event.respond("🔍 Проверяю все каналы...")
            await run_all_channels(client)
            await event.respond("✅ Готово.", buttons=main_menu_buttons())

        elif data.startswith("ch:info:"):
            key = data.split(":", 2)[2]
            ch = core.db.monitor_get_channel(key)
            if not ch:
                await event.answer("Канал не найден", alert=True)
                return
            target_display = ch.get("target_channel") or f"{TARGET_CHANNEL} (по умолчанию)"
            await event.respond(
                f"📺 **{ch['name']}**\nkey: `{ch['key']}`\nХештег: {ch['hashtag']}\nURL: {ch['url']}\n"
                f"Публикует в: {target_display}\n"
                f"Бутстрап пройден: {'да' if ch['bootstrapped'] else 'нет'}",
                buttons=[
                    [Button.inline("✏️ Сменить хештег", f"ch:tag:{key}".encode())],
                    [Button.inline("📤 Сменить канал публикации", f"ch:target:{key}".encode())],
                    [Button.inline("🗑 Удалить канал", f"ch:del:{key}".encode())],
                    [Button.inline("🔙 К списку", b"menu:list")],
                ]
            )
            await event.answer()

        elif data.startswith("ch:tag:"):
            key = data.split(":", 2)[2]
            pending[event.sender_id] = {"action": "edit_hashtag", "step": "wait", "data": {"key": key}}
            await event.respond(f"Пришли новый хештег для `{key}` (например `#Дюшес`):")
            await event.answer()

        elif data.startswith("ch:target:"):
            key = data.split(":", 2)[2]
            pending[event.sender_id] = {"action": "edit_target", "step": "wait", "data": {"key": key}}
            await event.respond(
                f"Пришли @username или -100id Telegram-канала для `{key}`, "
                f"или `-` для канала по умолчанию (`{TARGET_CHANNEL}`):"
            )
            await event.answer()

        elif data.startswith("ch:del:"):
            key = data.split(":", 2)[2]
            ch = core.db.monitor_get_channel(key)
            name = ch["name"] if ch else key
            await event.edit(
                f"Точно удалить канал **{name}**? Он перестанет отслеживаться.",
                buttons=[[
                    Button.inline("✅ Да, удалить", f"ch:delyes:{key}".encode()),
                    Button.inline("❌ Отмена", b"menu:list"),
                ]]
            )

        elif data.startswith("ch:delyes:"):
            key = data.split(":", 2)[2]
            core.db.monitor_remove_channel(key)
            await event.answer("Удалено")
            channels = core.db.monitor_list_channels()
            if channels:
                await event.edit("📺 **Каналы:**", buttons=channel_list_buttons(channels))
            else:
                await event.edit("Каналов больше нет.", buttons=[[Button.inline("➕ Добавить канал", b"menu:add")]])

# ─────────────────────────────────────────────
# СТАРТ
# ─────────────────────────────────────────────
async def main():
    client = TelegramClient(
        "monitor_session",
        core.API_ID,
        core.API_HASH,
        proxy=core.get_telethon_proxy(),
    )
    await client.start(bot_token=MONITOR_BOT_TOKEN)

    migrate_legacy_channels_json()

    me = await client.get_me()
    n = len(core.db.monitor_list_channels())
    core.term_log("🟢 MONITOR READY", f"@{me.username} следит за {n} каналами, публикует в {TARGET_CHANNEL}", core.Colors.GREEN)
    core.term_log("💬 MONITOR", "Напиши боту /menu в личку для управления", core.Colors.CYAN)

    register_handlers(client)
    asyncio.create_task(poll_loop(client))
    await client.run_until_disconnected()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        core.term_log("🛑 MONITOR", "Остановлен пользователем.", core.Colors.YELLOW)
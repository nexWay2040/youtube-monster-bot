"""
channel_monitor.py — отдельный автономный бот-агент.

НЕ взаимодействует с основным bot.py как с ботом (боты не могут писать
другим ботам в Telegram) — просто переиспользует его функции скачивания
(download_video, make_thumb, hashtag и т.д.) как обычный python-модуль,
и общую базу bot.db.

Вся автоматизация настраивается прямо в Telegram, в личке с этим ботом:
  /menu           — главное меню (добавить канал, список, проверить сейчас)
  /channels       — список каналов с кнопками управления
  /addchannel     — добавить канал (спросит ссылку, имя, хештег)
  /check          — проверить все каналы прямо сейчас
  /check <key>    — проверить один канал
  /forget <video_id> — "забыть" видео, чтобы бот выложил его повторно

Запуск отдельным процессом:
    python channel_monitor.py
"""

import os
import re
import sys
import json
import time
import asyncio

import yt_dlp
from telethon import TelegramClient, events, Button
from dotenv import load_dotenv

load_dotenv()

# Переиспользуем готовую логику скачивания/хештегов/логов из основного бота.
# bot.py защищён `if __name__ == "__main__":`, поэтому импорт безопасен —
# сам основной Telegram-бот при этом не запускается и не используется.
import bot as core

# ─────────────────────────────────────────────
# НАСТРОЙКИ
# ─────────────────────────────────────────────
MONITOR_BOT_TOKEN = os.getenv("MONITOR_BOT_TOKEN", "")
TARGET_CHANNEL = os.getenv("TARGET_CHANNEL", "@blogeridownload")
POLL_INTERVAL_MINUTES = float(os.getenv("MONITOR_POLL_INTERVAL_MINUTES", "15"))
VIDEOS_PER_CHANNEL_CHECK = int(os.getenv("MONITOR_VIDEOS_PER_CHECK", "15"))
MONITOR_VIDEO_QUALITY = os.getenv("MONITOR_VIDEO_QUALITY", "720")  # всегда 720p по умолчанию

MONITOR_BOOTSTRAP_LOOKBACK_HOURS = float(os.getenv("MONITOR_BOOTSTRAP_LOOKBACK_HOURS", "24"))
MONITOR_BOOTSTRAP_FRESH_CHECK = int(os.getenv("MONITOR_BOOTSTRAP_FRESH_CHECK", "3"))

# Разовая миграция из старого channels.json, если каналов в базе ещё нет
LEGACY_CHANNELS_FILE = os.getenv("MONITOR_CHANNELS_FILE", "channels.json")

if not MONITOR_BOT_TOKEN:
    core.term_log("⛔ CRITICAL", "MONITOR_BOT_TOKEN не задан в .env — добавь токен второго бота от @BotFather", core.Colors.RED)
    sys.exit(1)

# Многошаговые диалоги (добавление канала, смена хештега) — только с владельцем
pending: dict = {}  # {user_id: {"action": str, "step": str, "data": dict}}

# Замок, чтобы ручная /check и автопроверка по таймеру НИКОГДА не выполнялись
# одновременно — раньше из-за этого один и тот же ролик мог начать качаться
# двумя процессами параллельно (Windows блокировал .part-файл при попытке
# переименования, плюс ломался файл-кэш cookies из браузера).
check_lock = asyncio.Lock()
# Дополнительная защита на уровне одного видео (на случай, если один video_id
# всплывёт из двух разных каналов одновременно — маловероятно, но дёшево защититься)
videos_in_progress: set = set()


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
    """Докатывает каналы из channels.json в базу. Раньше проверялось 'если в
    базе вообще есть строки — ничего не делать', но старые записи (ещё с
    версии, где таблица хранила только channel_key+bootstrapped) имеют
    url=NULL — из-за этого миграция ошибочно пропускалась. Теперь докатываем
    любой канал, у которого нет url, и не трогаем уже полностью настроенные
    (могли быть отредактированы вручную через /menu)."""
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
            continue  # уже полностью настроен — не перезаписываем ручные правки
        name = entry.get("name") or key
        url = entry.get("url", "")
        tag = core.hashtag(name)
        core.db.monitor_add_channel(key, name, url, tag)
        if entry.get("bootstrapped"):
            core.db.monitor_set_bootstrapped(key)
        imported += 1

    if imported:
        core.term_log("📦 MONITOR", f"Докатил {imported} канал(ов) из {LEGACY_CHANNELS_FILE} в базу (был пустой/битый url)", core.Colors.CYAN)


# ─────────────────────────────────────────────
# ПОЛУЧЕНИЕ СПИСКА ПОСЛЕДНИХ ВИДЕО КАНАЛА
# ─────────────────────────────────────────────
def fetch_latest_videos(channel_url: str, limit: int) -> list:
    """Быстрый список последних видео канала БЕЗ скачивания (extract_flat)."""
    opts = core.ytdlp_opts()
    opts["extract_flat"] = True
    opts["playlistend"] = limit
    opts["skip_download"] = True
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
    """Точное время выхода ролика (unix timestamp). Дороже extract_flat,
    поэтому используется только точечно — для 2-3 самых новых видео
    при бутстрапе канала."""
    try:
        opts = core.ytdlp_opts()
        opts["skip_download"] = True
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
        return info.get("timestamp") or info.get("release_timestamp")
    except Exception:
        return None


# ─────────────────────────────────────────────
# СКАЧИВАНИЕ + ПУБЛИКАЦИЯ ОДНОГО РОЛИКА
# ─────────────────────────────────────────────
async def post_video(client: TelegramClient, channel: dict, video: dict):
    vid = video["id"]
    url = video["url"]
    title = video["title"]
    name = channel["name"]
    tag = channel.get("hashtag") or core.hashtag(name)
    target = channel.get("target_channel") or TARGET_CHANNEL

    if vid in videos_in_progress:
        core.term_log("⏭️ MONITOR", f"[{name}] {vid} уже качается в другом потоке — пропускаю дубль", core.Colors.YELLOW)
        return
    videos_in_progress.add(vid)

    core.term_log("⬇️ MONITOR", f"[{name}] Новое видео: {title} ({vid}) → {target}", core.Colors.CYAN)

    try:
        # 0 = системный "владельческий" user_id для файлов монитора,
        # чтобы не путать с обычными пользователями основного бота
        path = await asyncio.to_thread(core.download_video, url, MONITOR_VIDEO_QUALITY, 0, vid, "orig", None)
        thumb = core.make_thumb(0, str(vid))

        # Реальные width/height/duration из уже скачанного файла (ffprobe) —
        # соответствуют фактическому разрешению (MONITOR_VIDEO_QUALITY),
        # а не оригиналу на YouTube.
        info = core.probe(path)
        duration = info["duration"]
        w = info["width"] or 1280
        h = info["height"] or 720

        # Хештег автора СНАЧАЛА, имя автора уже после него
        caption = f"🎬 **{title}**\n\n{tag}\n👤 {name}"

        await client.send_file(
            target,
            path,
            caption=caption,
            thumb=thumb,
            attributes=[core.DocumentAttributeVideo(duration=duration, w=w, h=h, supports_streaming=True)],
        )

        core.db.monitor_mark_posted(vid, name, title)
        core.term_log("✅ MONITOR", f"[{name}] Опубликовано: {title}", core.Colors.GREEN)

    except Exception as e:
        core.term_log("❌ MONITOR", f"[{name}] Ошибка публикации {vid}: {e}", core.Colors.RED)
    finally:
        videos_in_progress.discard(vid)
        # подчищаем скачанные файлы за собой
        for fname in os.listdir(core.DOWNLOAD_DIR):
            if str(vid) in fname:
                try:
                    os.remove(os.path.join(core.DOWNLOAD_DIR, fname))
                except Exception:
                    pass


# ─────────────────────────────────────────────
# ПРОВЕРКА ОДНОГО КАНАЛА
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
            f"[{name}] Первый запуск — запомнено {len(videos)} видео, "
            f"из них свежих к публикации: {len(fresh_to_post)}",
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
# МЕНЮ И УПРАВЛЕНИЕ КАНАЛАМИ ИЗ TELEGRAM
# ─────────────────────────────────────────────
def is_owner(event) -> bool:
    return event.sender_id == core.OWNER_ID

def main_menu_buttons():
    from telethon import Button
    return [
        [Button.inline("➕ Добавить канал", b"menu:add"), Button.inline("📺 Список каналов", b"menu:list")],
        [Button.inline("🔍 Проверить всё сейчас", b"menu:checkall")],
    ]

def channel_list_buttons(channels: list):
    from telethon import Button
    rows = []
    for ch in channels:
        rows.append([
            Button.inline(f"📺 {ch['name']}", f"ch:info:{ch['key']}".encode()),
            Button.inline("🗑", f"ch:del:{ch['key']}".encode()),
        ])
    rows.append([Button.inline("➕ Добавить канал", b"menu:add"), Button.inline("🔙 Меню", b"menu:back")])
    return rows


def register_handlers(client: TelegramClient):
    from telethon import Button

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
            await event.respond("⏳ Проверка уже идёт (автоматическая или запущенная ранее) — дождись её завершения, чтобы не было дублей.")
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
            await event.respond(
                "Использование: `/forget VIDEO_ID` — video_id это то, что после v= в ссылке "
                "на YouTube (например, для youtu.be/ux9UjdJuiVY это `ux9UjdJuiVY`).\n"
                "После этого видео станет «новым» и появится при следующем /check."
            )
            return
        vid = args[1].strip()
        ok = core.db.monitor_forget(vid)
        await event.respond(f"✅ Забыл `{vid}`, теперь он снова новый." if ok else f"⚠️ `{vid}` не найден в списке опубликованных/пропущенных.")

    # ── Многошаговые диалоги (добавление канала / смена хештега) ──
    @client.on(events.NewMessage())
    async def on_any_message(event):
        if not is_owner(event):
            return
        text = event.raw_text.strip()
        if text.startswith("/"):
            return  # команды обработаны выше
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
                    f"или `-`, чтобы использовать канал по умолчанию (`{TARGET_CHANNEL}`):"
                )
            elif state["step"] == "target":
                target = None if text == "-" else text
                key = slugify(data["name"])
                core.db.monitor_add_channel(key, data["name"], data["url"], data["hashtag"], target)
                pending.pop(event.sender_id, None)
                await event.respond(
                    f"✅ Добавил канал **{data['name']}** (`{key}`)\nХештег: {data['hashtag']}\nURL: {data['url']}\n"
                    f"Публикует в: {target or TARGET_CHANNEL + ' (по умолчанию)'}\n\n"
                    f"При следующей проверке бот запомнит текущие видео и начнёт следить за новыми "
                    f"(кроме совсем свежих — их опубликует сразу).",
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

    # ── Инлайн-кнопки ──
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
                f"или `-`, чтобы вернуть канал по умолчанию (`{TARGET_CHANNEL}`):"
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

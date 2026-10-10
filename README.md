# 🎥 YouTube Monster Bot

### ⚡ Telegram-загрузчик YouTube: Direct Copy (0% CPU), русская AI-озвучка, кэш и файлы до 4 ГБ

<p align="center">
<img src="https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB?style=for-the-badge&logo=python&logoColor=white">
<img src="https://img.shields.io/badge/Telegram-Telethon-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white">
<img src="https://img.shields.io/badge/Downloader-yt--dlp-FF0000?style=for-the-badge&logo=youtube&logoColor=white">
<img src="https://img.shields.io/badge/Engine-Direct%20Copy%20(0%25%20CPU)-2ECC71?style=for-the-badge&logo=ffmpeg&logoColor=white">
<img src="https://img.shields.io/badge/Database-SQLite3%20(WAL)-003B57?style=for-the-badge&logo=sqlite&logoColor=white">
<a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-F7DF1E?style=for-the-badge"></a>
</p>

Отправь боту ссылку на YouTube — получишь видео в Telegram **без потери качества и без перекодирования**. Бот сам скачает ролик, переупакует его в MP4 за секунды (Direct Copy — 0% нагрузки на CPU/GPU), запомнит результат в кэш и при повторном запросе отдаст файл за 0.1 секунды.

**Для кого это:** для админов Telegram-каналов с роликами, для тех, кто качает YouTube в странах с блокировками, и для всех, кому нужен личный загрузчик с полным контролем над данными (свой сервер, свои ключи, никаких сторонних сервисов).

---

## ✨ Возможности

| | |
|---|---|
| ⚡ **Direct Copy движок** | Видео и звук просто перепаковываются в MP4 без перекодирования — 1–2 секунды после закачки, ноль потерь качества, ноль нагрузки на CPU |
| 💎 **Файлы до 4 ГБ** | Dual-Contour: гибрид бота и юзербота. Пользователи из белого списка получают до 4 ГБ вместо стандартных 2 ГБ (нужен Telegram Premium) |
| 🌐 **Выбор озвучки: оригинал / RU / EN** | Для каналов с официальным дубляжом (MrBeast, Mark Rober…) — выбор дорожки прямо в чате, раздельный кэш по дорожкам |
| 🤖 **Нейросетевая русская озвучка** | Если русской дорожки нет — бот прогоняет оригинал через Yandex AI-переводчик и сводит русский звук с видео без пережатия картинки |
| 🔄 **Умный локальный кэш** | Повторный запрос — отдача за 0.1 сек без скачивания. Панель `/cache`: пагинация, поиск, предпросмотр, удаление с очисткой диска |
| 🍪 **Авторабота с cookies** | Свежий файл → браузерные куки → фоновая проверка с уведомлением владельцу в Telegram, если куки слетели |
| 📢 **Мониторинг YouTube-каналов** | Опциональный `channel_monitor.py`: следит за каналами и сам постит новые видео в Telegram-канал с хештегами и определением игры |
| 👑 **Многоуровневая админка** | Владелец + админы, валидация @username через Telegram API (отсекает ботов и каналы), бан/анбан, статистика, рассылка |
| 🛑 **Мгновенная отмена** | Кнопка «Отменить» на этапах скачивания и загрузки с очисткой временных файлов |
| 🔧 **TUI-меню запуска** | Цветная консольная панель: переключение настроек, статус куки/сессий, быстрый старт — без ручного редактирования файлов |
| 🔄 **Автопроверка yt-dlp** | Раз в сутки сверяет версию с PyPI и предупреждает, если YouTube поменял защиту |
| 📦 **Плейлисты пачками** | Обработка плейлистов группами по N видео с настраиваемым размером пачки |

---

## 🚀 Быстрый старт (3 минуты)

> Требуется: Python 3.10+, [FFmpeg](https://ffmpeg.org/download.html) в PATH, аккаунт Telegram.

```bash
# 1. Клонируем и ставим зависимости
git clone https://github.com/nexWay2040/youtube-download-bot.git
cd youtube-download-bot
pip install -r requirements.txt

# 2. Создаём конфиг и заполняем свои ключи
cp .env.example .env          # Windows: copy .env.example .env
nano .env                     # API_ID, API_HASH, BOT_TOKEN, OWNER_ID

# 3. Запускаем — откроется TUI-меню, жмём [1]
python bot.py
```

Где взять ключи:
- `API_ID` / `API_HASH` → [my.telegram.org/apps](https://my.telegram.org/apps)
- `BOT_TOKEN` → [@BotFather](https://t.me/BotFather) → `/newbot`
- `OWNER_ID` → [@userinfobot](https://t.me/userinfobot)

**Windows с нуля** (если ничего не установлено):

```powershell
winget install Anaconda.Miniconda3
# перезапустить PowerShell, затем:
conda create -n monster python=3.11 -y
conda activate monster
conda install -c conda-forge ffmpeg -y
pip install -r requirements.txt
python bot.py
```

<details>
<summary>🖥️ Как выглядит TUI-меню запуска</summary>

```text
  ⚡ Telethon + yt-dlp + FFmpeg (Direct Copy) | Pure Speed Engine
  🛡️ Local Cache V2 (Newest First) | Yandex Neural Dubbing | 4GB Flow

  🎛️  ГЛАВНОЕ МЕНЮ УПРАВЛЕНИЯ

  [1] ▶️  ЗАПУСТИТЬ БОТА
  [2] 💎 Premium-юзербот (4 ГБ):     [ВКЛЮЧЕН] (сессия есть ✅)
  [3] 🚀 Видеодвижок:                [Direct Copy (0% CPU/GPU)]
  [4] 🌐 SOCKS5 Прокси:              [ВЫКЛЮЧЕН 🔴]
  [5] 📦 Пачка в плейлисте:          [по 3 видео]
  [6] 🍪 YouTube Cookies:            [www.youtube.com_cookies.txt 🟢 (свежие, 2.1ч)]
  [7] ⚡ Быстрый старт (без меню):   [ВЫКЛЮЧЕН]
  [8] 🗑️  Сбросить сессию юзербота
  [9] 👑 ID Владельца:               [ID 123456789]
  [A] 🔧 Дополнительные админы:      [2 чел.]
  [0] ❌ Выход из программы
```
</details>

---

## 📋 Команды

```text
👑 ВЛАДЕЛЕЦ:
  /addadmin <ID|@username>         — Назначить администратора (с проверкой в TG API)
  /deladmin <ID|@username>         — Снять полномочия администратора
  /delcache <video_id> [качество]  — Удалить запись из базы и стереть файл с диска
  /clearcache                      — Полная очистка кэша

🔧 АДМИНИСТРАТОР:
  /admin                           — Инлайн-панель управления
  /commands, /help                 — Каталог команд
  /cache [поиск]                   — Менеджер кэша: пагинация, просмотр, удаление
  /users                           — Последние 50 пользователей
  /admins                          — Список администраторов
  /whitelist                       — Список пользователей с лимитом 4 ГБ
  /addpremium <ID|@username>       — Выдать пользователю лимит 4 ГБ
  /delpremium <ID|@username>       — Забрать лимит 4 ГБ
  /ban /unban <ID|@username>       — Бан / разбан пользователя
  /broadcast <текст>               — Рассылка всем пользователям

👤 ВСЕ:
  /start                           — Статус, лимит и приветствие
  Ссылка YouTube                   — Анализ, выбор озвучки и скачивание
```

---

## 🍪 Про cookies (важно)

YouTube периодически требует подтверждение «я не бот» (возрастные ограничения, приватность, региональные блокировки). Бот поддерживает два источника с автоматическим приоритетом:

1. **Файл** (`www.youtube.com_cookies.txt` / путь из `COOKIE_FILE`) — пока не устарел (`COOKIE_MAX_AGE_HOURS`, по умолчанию 12 ч).
2. **Браузер** (`BROWSER_COOKIES=edge|chrome|firefox`) — подхватывается автоматически, когда файл устарел или отсутствует.

⚠️ На Windows чтение живых cookies из **Chrome/Edge** иногда упирается в `PermissionError` (браузер держит БД занятой даже в фоне). Решение: отключите фоновые процессы браузера либо экспортируйте `cookies.txt` расширением вроде *Get cookies.txt LOCALLY* и положите рядом с `bot.py`.

## 🌐 Прокси для РФ

YouTube и Telegram блокируются — бот умеет два независимых SOCKS5-канала:

- `USE_PROXY` + `PROXY_HOST/PORT` — прокси для **Telegram** (Telethon);
- `YTDLP_USE_PROXY` + `YTDLP_PROXY_HOST/PORT` — отдельный стабильный прокси для **YouTube**.

Второй нужен потому, что YouTube привязывает cookies к IP: если VPN-клиент (Happ и т.п.) постоянно меняет выходной сервер, куки «слетают». Для зарубежного VPS можно оставить `False`.

---

## 🧪 Экспериментально: автопубликация в канал

Отдельный необязательный скрипт `channel_monitor.py` следит за списком YouTube-каналов и сам публикует новые ролики в Telegram-канал — с хештегами автора, определением игры/жанра по названию и защитой от «старья» (`MONITOR_MAX_AGE_HOURS`). Управляется прямо в Telegram через `/menu`, запускается вторым процессом:

```bash
python channel_monitor.py
```

Список каналов добавляются командами в самом мониторе (старый `channels.json` мигрирует в базу автоматически). Это дополнительная автоматизация поверх движка `bot.py`, она в активной разработке.

---

## 📂 Структура проекта

```text
youtube-monster-bot/
├── bot.py                  # Ядро: TUI-меню, движок загрузки, Direct Copy, Dual-Audio, Yandex AI, админка
├── channel_monitor.py      # (опционально) монитор YouTube-каналов и автопубликация
├── requirements.txt        # Зависимости Python
├── .env.example            # Образец конфига с подробными комментариями
├── channels.example.json   # Пример списка каналов для монитора
├── CONTRIBUTING.md         # Как внести вклад
├── SECURITY.md             # Правила безопасности (сессии, токены, куки)
├── bot.db                  # SQLite: пользователи, кэш, админы (создаётся автоматически)
└── bot.log                 # Ротируемый лог (5×5 МБ)
```

---

## ❓ Частые проблемы

<details>
<summary><b>«FFmpeg не обнаружен в PATH»</b></summary>

Установите FFmpeg и проверьте: `ffmpeg -version`. Через conda: `conda install -c conda-forge ffmpeg -y`.
</details>

<details>
<summary><b>«Sign in to confirm you're not a bot» при скачивании</b></summary>

YouTube требует cookies. Подключите файл куки или `BROWSER_COOKIES` в `.env` (см. раздел про cookies). Также помогает обновление: `pip install -U yt-dlp` + перезапуск.
</details>

<details>
<summary><b>Бот не отвечает / таймауты в России</b></summary>

Включите SOCKS5-прокси: `USE_PROXY=True`, задайте `PROXY_HOST/PROXY_PORT` (порт Happ по умолчанию — 10808). Для YouTube отдельно — `YTDLP_USE_PROXY`.
</details>

<details>
<summary><b>Файл 2+ ГБ не отправляется</b></summary>

Лимит обычного бота — 2 ГБ. Для 4 ГБ включите юзербота (`USE_USERBOT=True`, пункт `[2]` в TUI) с Telegram Premium на аккаунте и добавьте получателя в `/addpremium`.
</details>

<details>
<summary><b>Скрипты завершаются с ошибкой сразу при запуске</b></summary>

Проверьте, что `.env` создан из `.env.example` и заполнены `API_ID`, `API_HASH`, `BOT_TOKEN`. Бот печатает понятную ошибку на русском, если какой-то ключ пуст.
</details>

---

## 🤝 Вклад в проект

Любой вклад полезен — опечатки, баг-репорты, идеи и пул-реквесты. Читайте [CONTRIBUTING.md](CONTRIBUTING.md). Нашли проблему безопасности? Сначала прочитайте [SECURITY.md](SECURITY.md).

**Ставьте ⭐, если проект сэкономил вам время — это главная поддержка для разработчика.**

---

## ⚖️ Лицензия

[MIT License](LICENSE) — свободное использование, модификация и коммерческое применение.

> Проект не аффилирован с YouTube или Telegram. Используйте для контента, на который у вас есть права, и соблюдайте ToS сервисов и законы своей страны.

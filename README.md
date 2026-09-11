
# 🎥 YouTube Monster Bot
### ⚡ Ultimate Edition — Multi-Audio, Smart Cache V2 & GPU Engine 🚀

<p align="center">
<img src="https://img.shields.io/badge/Python-3.10%20%7C%203.11-3776AB?style=for-the-badge&logo=python&logoColor=white">
<img src="https://img.shields.io/badge/Environment-Miniconda-44A833?style=for-the-badge&logo=anaconda&logoColor=white">
<img src="https://img.shields.io/badge/Telegram-Telethon-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white">
<img src="https://img.shields.io/badge/Downloader-yt--dlp-FF0000?style=for-the-badge&logo=youtube&logoColor=white">
<img src="https://img.shields.io/badge/Hardware%20Accel-AMD%20AMF%20%7C%20NVENC-ED1C24?style=for-the-badge&logo=amd&logoColor=white">
<img src="https://img.shields.io/badge/Database-SQLite3-003B57?style=for-the-badge&logo=sqlite&logoColor=white">
<img src="https://img.shields.io/badge/License-MIT-F7DF1E?style=for-the-badge">
</p>

<p align="center">
<b>Мощный автономный комбайн для скачивания медиаконтента с YouTube через Telegram.</b><br>
Выбор дорожек (RU / EN), обход ограничений SABR и 360p-блокировок, поддержка 720p/1080p для 21:9 Ultrawide, лимит до 4 ГБ через Telegram Premium, GPU-ускорение (AMD/NVIDIA) и умный локальный кэш с мгновенной отдачей.
</p>

---

## 🖥️ Терминальное меню (TUI)

При запуске `bot.py` открывается встроенная панель управления сервером с цветными логами и быстрым переключением параметров без ручного редактирования файлов:

```text
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
  ⚡ Telethon + yt-dlp + FFmpeg (h264_amf) | AMD RX 6600
  🛡️ Ultra Engine | 4GB Premium Contour | Dual Audio RU/EN

  🎛️  ГЛАВНОЕ МЕНЮ УПРАВЛЕНИЯ

  [1] ▶️  ЗАПУСТИТЬ БОТА
  [2] 💎 Premium-юзербот (4 ГБ):     [ВКЛЮЧЕН] (сессия есть ✅)
  [3] 🎥 Видеокодек:                 [h264_amf (AMD Radeon RX 6600)]
  [4] 🌐 SOCKS5 Прокси:              [ВЫКЛЮЧЕН 🔴]
  [5] 📦 Пачка в плейлисте:          [по 3 видео]
  [6] 🍪 YouTube Cookies:            [www.youtube.com_cookies.txt 🟢]
  [7] ⚡ Быстрый старт (без меню):   [ВЫКЛЮЧЕН]
  [8] 🗑️  Сбросить сессию юзербота
  [9] 👑 ID Владельца:               [ID 123456789]
  [A] 🔧 Дополнительные админы:      [2 чел.]
  [0] ❌ Выход из программы
══════════════════════════════════════════════════════════════════
  👉 Выберите действие (0-9, A): 1
```

---

## ✨ Ключевые возможности

* 🌐 **Мультиязычная озвучка (Dual-Audio RU / EN):** поддержка каналов с дубляжом (**MrBeast**, **Mark Rober** и др.). Выбор дорожки прямо в чате и раздельный кэш (`1080_ru` и `1080_en`) — бот никогда не перепутает озвучку при повторной выдаче.
* 📐 **Умный расчет 21:9 Ultrawide (Фикс 544p):** видео с кинотеатральным кадром 1280×544 детектируются по длинной стороне и классифицируются как полноценный тир **🎬 720p**, минуя падение до 360p.
* 🛡️ **Обход SABR и блокировок кодеков:** пул клиентов (`default,web_embedded,ios`) и отказ от принудительного `vcodec=avc1`. Бот забирает качественные потоки **VP9** и **AV1**, перепаковывая их на GPU в универсальный MP4 (H.264 + AAC).
* ⚡ **Локальный кэш V2 (`bot.db`):** отдача за 0.1 секунды без скачивания. В панели `/cache` доступен предпросмотр (`🎬 Отправить` файл себе в чат для проверки) и удаление с очисткой диска.
* 🖥️ **Аппаратное GPU-ускорение:** рендеринг через чипы AMD Radeon (`h264_amf`), NVIDIA (`h264_nvenc`), Intel (`h264_qsv`) или CPU fallback (`libx264`).
* 👑 **Многоуровневая админка с валидацией:** Владелец + Администраторы. При вводе `/addadmin @username` бот запрашивает Telegram API и проверяет, реальный ли это человек (отсекает ботов и каналы).
* 🛑 **Мгновенная отмена:** кнопка `[ ❌ Отменить ]` на этапах скачивания, кодирования и загрузки с очисткой папки `downloads/`.
* 💎 **Dual-Contour (4 ГБ):** гибрид бота и юзербота — пользователи из белого списка получают файлы размером до 4 ГБ.

---

## 📋 Справочник команд

```text
👑 КОМАНДЫ ВЛАДЕЛЬЦА:
  /addadmin <ID|@username>       — Назначить администратора (с проверкой в TG)
  /deladmin <ID|@username>       — Снять полномочия администратора
  /delcache <video_id> [качество] — Удалить запись из bot.db и стереть файл с диска
  /clearcache                   — Полная очистка всего кэша базы

🔧 КОМАНДЫ АДМИНИСТРАТОРА:
  /admin                        — Открыть инлайн-панель управления
  /commands (или /help)         — Полный каталог команд
  /cache                        — Менеджер кэша (пагинация + просмотр + удаление)
  /cache <поиск>                — Поиск роликов в базе по названию или ID
  /users                        — Список последних 50 пользователей
  /admins                       — Список действующих администраторов
  /whitelist                    — Список пользователей с лимитом 4 ГБ
  /addpremium <ID|@username>    — Добавить пользователя в Premium Whitelist (4 ГБ)
  /delpremium <ID|@username>    — Удалить пользователя из Premium Whitelist
  /ban <ID|@username>           — Заблокировать пользователя
  /unban <ID|@username>         — Разблокировать пользователя
  /broadcast <текст>            — Массовая рассылка сообщений

👤 ДЛЯ ВСЕХ:
  /start                        — Проверка статуса, лимита и приветствие
  Ссылка YouTube                — Анализ, выбор озвучки (RU/EN) и скачивание
```

---

## 💻 Установка через терминал (Miniconda)

### 1. Установка Miniconda в терминале

* **Windows (PowerShell):**
  ```powershell
  winget install Anaconda.Miniconda3
  ```
  *(Либо скачайте установщик через curl: `curl -o miniconda.exe https://repo.anaconda.com/miniconda/Miniconda3-latest-Windows-x86_64.exe; .\miniconda.exe /S`)*

* **Linux (Bash):**
  ```bash
  curl -fsSL https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -o miniconda.sh
  bash miniconda.sh -b -u -p ~/miniconda3
  ~/miniconda3/bin/conda init bash && source ~/.bashrc
  ```

---

### 2. Развертывание окружения и запуск

```bash
# 1. Клонируем проект и переходим в папку
git clone https://github.com/nexWay2040/youtube-monster-bot.git
cd youtube-monster-bot

# 2. Создаем изолированное окружение Python 3.11 и активируем его
conda create -n monster python=3.11 -y
conda activate monster

# 3. Ставим системный FFmpeg через conda (работает сразу без настройки PATH)
conda install -c conda-forge ffmpeg -y

# 4. Устанавливаем зависимости из requirements.txt
pip install -r requirements.txt

# 5. Создаем рабочий конфиг из готового образца
# На Windows:
copy .env.example .env
# На Linux:
cp .env.example .env
```

> ⚙️ **Настройка:** Откройте созданный файл `.env` и впишите свои `API_ID`, `API_HASH`, `BOT_TOKEN` и `OWNER_ID`. Все параметры и ключи подробно описаны внутри образца `.env.example`.

---

### 3. Старт бота

```bash
python bot.py
```

* Нажмите **`[2]`** в консольном меню, если планируете отправлять файлы до 4 ГБ через Telegram Premium (потребуется однократный вход по номеру телефона).
* Нажмите **`[1]`** для запуска сервиса.

---

## 📂 Структура проекта

```text
youtube-monster-bot/
├── bot.py                        # Ядро бота: TUI-меню, движок загрузки, FFmpeg, Dual-Audio
├── bot.db                        # База SQLite3: статистика, пользователи, кэш V2, админы
├── bot.log                       # Логирование работы и ошибок
├── requirements.txt              # Список зависимостей Python
├── .env.example                  # Готовый образец конфигурации с подсказками
├── .env                          # Ваш рабочий файл настроек (создается из образца)
├── bot_session.session           # Сессия Telegram Bot API
├── user_session.session          # Сессия юзербота для выгрузки файлов до 4 ГБ
└── www.youtube.com_cookies.txt   # Cookies для обхода возрастных ограничений YouTube
```

---

## 📜 Лицензия

Проект распространяется под лицензией **MIT License**. Разрешено свободное использование, модификация и коммерческое применение.

<p align="center">
  <img src="https://img.shields.io/badge/Telegram-Downloader-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white" alt="Telegram Downloader"/>
</p>

<h1 align="center">Telegram Downloader</h1>

<p align="center">
  <strong>Fast • Clean • Reliable</strong><br/>
  Download Stories, public posts, restricted media, Instagram & Pinterest — in seconds.
</p>

<p align="center">
  <a href="#features"><img src="https://img.shields.io/badge/features-ready-success?style=flat-square" alt="Features"/></a>
  <a href="#installation"><img src="https://img.shields.io/badge/python-3.11%2B-blue?style=flat-square&logo=python&logoColor=white" alt="Python"/></a>
  <a href="#stack"><img src="https://img.shields.io/badge/python--telegram--bot-22.8-blue?style=flat-square" alt="PTB"/></a>
  <a href="#stack"><img src="https://img.shields.io/badge/telethon-1.40-blue?style=flat-square" alt="Telethon"/></a>
  <a href="#docker"><img src="https://img.shields.io/badge/docker-ready-2496ED?style=flat-square&logo=docker&logoColor=white" alt="Docker"/></a>
  <a href="#license"><img src="https://img.shields.io/badge/license-MIT-green?style=flat-square" alt="License"/></a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Stories-supported-26A5E4?style=flat-square" alt="Stories"/>
  <img src="https://img.shields.io/badge/Restricted-content-orange?style=flat-square" alt="Restricted"/>
  <img src="https://img.shields.io/badge/Public_posts-instant_copy-brightgreen?style=flat-square" alt="Public"/>
  <img src="https://img.shields.io/badge/Instagram-public_media-E4405F?style=flat-square&logo=instagram&logoColor=white" alt="Instagram"/>
  <img src="https://img.shields.io/badge/Pinterest-photos_&_videos-E60023?style=flat-square&logo=pinterest&logoColor=white" alt="Pinterest"/>
  <img src="https://img.shields.io/badge/Colored_buttons-style_API-purple?style=flat-square" alt="Style"/>
</p>

---

## Overview

**Telegram Downloader** is a production-ready bot that fetches media from Telegram, Instagram, and Pinterest links and delivers it to the user in private chat.

| Source | Method | Speed |
|--------|--------|-------|
| Public channel / group posts | `copy_message` (no re-upload) | Instant |
| Restricted content | User account → download → bot re-upload | Depends on file size |
| Stories (photo / video) | Telethon Stories API | Depends on file size |
| Instagram public media | Extractor → download → bot upload | Depends on file size |
| Pinterest pins | Page scrape / gallery-dl / yt-dlp → bot upload | Depends on file size |

Built with a clean modular architecture, structured logging, typed models, and Docker support.

---

## Features

### Telegram
- **Stories** — photo & video via Telethon `GetStoriesByID`
- **Public posts** — instant copy, no bandwidth waste
- **Restricted media** — when the logged-in account has access
- **Media types** — photos, videos, documents, voice, audio, animations, stickers
- **Message ranges** — `https://t.me/channel/100-110` (up to 50 messages)
- **Parallel downloads** — up to 5 concurrent for ranges

### Instagram
- **Public media** — reels, posts, IGTV, carousels, public profile pictures
- **No login required** — works with public content only
- **Multi-extractor fallback** — `parth-dl` → `gallery-dl` → `Instaloader`
- **Captions** — original caption is sent with the media

### Pinterest
- **Photos & videos** — single pin download (`pin.it` / `pinterest.com`)
- **Smart extraction** — page scrape for videos (with audio), gallery-dl for images
- **Captions** — pin description is sent under the media
- **Clean temp folders** — temporary directories are removed after send

### General
- **Colored inline buttons** — `primary` / `success` / `danger` (Bot API style)
- **High upload timeouts** — large files won’t fail mid-transfer
- **`.env` configuration** — no secrets in code
- **Structured logging** — clear, filterable output
- **Exception hierarchy** — predictable error handling
- **Type hints + async** throughout
- **Docker-ready**
- **No database** — stateless by design
- **Auto cleanup** — temp files and empty folders are deleted after delivery

---

## Stack

| Layer | Technology |
|-------|------------|
| Bot framework | [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) ≥ 22.7 |
| User / Stories API | [Telethon](https://github.com/LonamiWebs/Telethon) |
| Instagram extractors | parth-dl, gallery-dl, Instaloader |
| Pinterest extractors | Custom page scrape + gallery-dl + yt-dlp |
| Config | `python-dotenv` |
| Runtime | Python 3.11+ |

---

## Project Structure

```text
TelegramDownLoader/
├── app.py                      # Entry point
├── config.py                   # Env-based settings
├── requirements.txt
├── .env.example
├── Dockerfile
├── README.md
│
├── core/
│   ├── manager.py              # Application lifecycle
│   ├── telethon_client.py      # User client (Stories + restricted)
│   ├── logger.py
│   └── exceptions.py
│
├── instagram/                  # Instagram public-media module
│   ├── parser.py
│   ├── models.py
│   ├── exceptions.py
│   ├── manager.py
│   ├── downloader.py
│   ├── utils.py
│   └── extractors/
│       ├── base.py
│       ├── parth.py
│       ├── gallery_dl.py
│       └── instaloader.py
│
├── pinterest/                  # Pinterest module
│   ├── parser.py               # URL detection & normalization
│   ├── downloader.py           # Page scrape + gallery-dl + yt-dlp
│   └── exceptions.py
│
├── handlers/
│   ├── start.py                # /start + styled buttons
│   ├── story.py                # Story links
│   ├── restricted.py           # Public / restricted posts
│   ├── instagram.py            # Instagram links
│   └── pinterest.py            # Pinterest links
│
├── services/
│   ├── parser.py               # Link detection
│   ├── story.py
│   ├── restricted.py           # Parallel download pipeline
│   ├── instagram.py            # Instagram extract → download → normalize
│   ├── pinterest.py            # Pinterest download → normalize
│   └── sender.py               # Media delivery + keyboards + cleanup
│
├── tg/
│   ├── story.py                # Telethon GetStoriesByID
│   └── messages.py             # Restricted message fetch
│
├── models/
│   ├── media.py                # MediaType, MediaItem, DownloadResult
│   └── result.py
│
├── tests/                      # Unit tests (mocked, no live network)
│
└── utils/
    ├── regex.py
    ├── files.py                # safe_remove + safe_remove_dir
    └── helpers.py
```

---

## Installation

### 1. Clone

```bash
git clone https://github.com/DevZ44d/TelegramDownLoader.git
cd TelegramDownLoader
```

### 2. Virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux / macOS
source venv/bin/activate
```

### 3. Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configuration

```bash
cp .env.example .env
```

Edit `.env`:

```env
# Telegram API credentials (https://my.telegram.org)
API_ID=12345678
API_HASH=your_api_hash
BOT_TOKEN=123456:ABC-DEF...

# Optional: Telethon session string for the user account
# (required for Stories + restricted content the bot alone cannot access)
SESSION_STRING=

# Recommended: Instagram cookies file (helps with stories, rate limits & restricted public media)
INSTAGRAM_COOKIES=cookies.txt

# Session file names (do not change unless you know what you are doing)
SESSION_BOT_NAME=session_bot
SESSION_ACCOUNT_NAME=session_account

# Developer / channel links
DEVELOPER_URL=https://t.me/YourUsername
CHANNEL_URL=https://t.me/YourChannel

# Temporary download directory
DOWNLOAD_DIR=downloads

# Max file size in MB (Telegram limit is ~2GB)
MAX_FILE_SIZE_MB=2000

# Logging level: DEBUG, INFO, WARNING, ERROR
LOG_LEVEL=INFO
```

| Variable | Required | Description |
|----------|----------|-------------|
| `API_ID` | Yes | From [my.telegram.org](https://my.telegram.org) |
| `API_HASH` | Yes | From my.telegram.org |
| `BOT_TOKEN` | Yes | From [@BotFather](https://t.me/BotFather) |
| `SESSION_STRING` | Recommended | Telethon string session (Stories + restricted) |
| `INSTAGRAM_COOKIES` | Recommended | Path to Instagram cookies file (e.g. `cookies.txt`) — improves stories, rate limits & access to some public media |
| `DEVELOPER_URL` | No | Shown on the start button |
| `CHANNEL_URL` | No | Optional channel button on start |
| `DOWNLOAD_DIR` | No | Temp files (default: `downloads`) |
| `MAX_FILE_SIZE_MB` | No | Max file size in MB (default: `2000`) |
| `LOG_LEVEL` | No | `DEBUG` / `INFO` / `WARNING` / `ERROR` |
| `INSTAGRAM_ENABLED` | No | Turn Instagram module on/off (default: `true`) |
| `INSTAGRAM_MAX_FILE_SIZE_MB` | No | Max size per Instagram file (default: `2000`) |
| `INSTAGRAM_MAX_CONCURRENT_DOWNLOADS` | No | Max parallel downloads per carousel (default: `3`) |
| `INSTAGRAM_TIMEOUT` | No | Per-request timeout in seconds (default: `30`) |
| `INSTAGRAM_MAX_RETRIES` | No | Retries per file on transient failures (default: `2`) |

#### Generate a Telethon session string

```python
from telethon.sync import TelegramClient
from telethon.sessions import StringSession

api_id = 12345
api_hash = "your_hash"

with TelegramClient(StringSession(), api_id, api_hash) as client:
    print(client.session.save())
```

Paste the output into `SESSION_STRING`.

> Without a session string, **public posts still work**. Stories and restricted content will not.

### 5. Run

```bash
python app.py
```

---

## Docker

```bash
docker build -t telegram-downloader .

docker run --env-file .env \
  -v "$(pwd)/downloads:/app/downloads" \
  telegram-downloader
```

---

## Tests

The Instagram module ships with a unit test suite that mocks every
extractor — no live Instagram requests, no network access required.

```bash
pip install -r requirements-dev.txt
pytest
```

---

## Supported Links

| Type | Example |
|------|---------|
| Story | `https://t.me/username/s/123` |
| Public post | `https://t.me/channel/456` |
| Message range | `https://t.me/channel/100-105` |
| Restricted post* | Same as public (account must be a member) |
| Instagram reel/post/tv | `https://www.instagram.com/reel/CzXyzAbC1/` |
| Instagram public profile | `https://www.instagram.com/username/` |
| Pinterest pin | `https://pin.it/xxxxx` or `https://www.pinterest.com/pin/123456/` |

\* Requires a valid `SESSION_STRING`.

---

## Instagram Downloader

Send any public Instagram link (reel, post, tv, carousel, or a public
profile URL) and the bot fetches it the same way it fetches Telegram
content — no separate command.

```text
User sends Instagram URL
        ↓
URL parser (instagram/parser.py)
        ↓
Extractor manager — tries parth-dl → gallery-dl → Instaloader
        ↓
Best available extractor returns normalized metadata
        ↓
Download engine streams the file(s) to downloads/temp/instagram/
        ↓
Telegram sender delivers it + caption, then cleans up
```

**No Instagram login required.** Private accounts, login walls, Stories/Highlights, and bulk scraping are not supported by design.

---

## Pinterest Downloader

Send any Pinterest pin link (`pin.it` or `pinterest.com/pin/...`) and the bot downloads the photo or video.

```text
User sends Pinterest URL
        ↓
URL parser (pinterest/parser.py)
        ↓
Smart downloader:
  1. Page scrape (best for videos with audio + caption)
  2. gallery-dl (best for images)
  3. yt-dlp (final fallback)
        ↓
Single best media file is selected
        ↓
Telegram sender delivers it + pin description as caption
        ↓
Temp file + empty folder are cleaned up
```

**Features:**
- One media per pin (no multi-image spam)
- Videos prefer progressive MP4 with audio
- Images use gallery-dl for reliability
- Pin description/caption is attached under the media
- Temporary folders are automatically removed after send

---

## Colored Buttons

Requires Telegram clients released after **9 February 2026**. Older clients ignore `style`.

```python
from telegram import InlineKeyboardButton
from telegram.constants import KeyboardButtonStyle

InlineKeyboardButton(
    "Developer",
    url="https://t.me/...",
    style=KeyboardButtonStyle.PRIMARY,   # blue
    # style=KeyboardButtonStyle.SUCCESS, # green
    # style=KeyboardButtonStyle.DANGER,  # red
)
```

---

## How It Works

```text
User sends link
       │
       ▼
┌──────────────┐
│ Link parser  │  → Story / Public / Restricted / Instagram / Pinterest
└──────┬───────┘
       │
       ├─ Story ──────────► Telethon GetStoriesByID → download → bot send
       │
       ├─ Public post ────► bot.copy_message (fast path)
       │                         │ fail
       │                         ▼
       │                    Telethon download → bot re-upload
       │
       ├─ Restricted ─────► Telethon only → download → bot re-upload
       │
       ├─ Instagram ──────► Extractor fallback → download → bot upload + caption
       │
       └─ Pinterest ──────► Page scrape / gallery-dl / yt-dlp → bot upload + caption
```

- **Public Telegram**: zero download when the bot can see the chat.
- **Restricted / Stories**: user client fetches media; bot delivers it.
- **Instagram / Pinterest**: extract → download to temp → send → cleanup.

---

## Security Notes

- Never commit `.env` or session files.
- `SESSION_STRING` grants full account access — treat it like a password.
- The bot only answers in **private** chats.
- Temp files and empty folders are deleted after send.

---

## Contributing

1. Fork the repo  
2. Create a branch: `git checkout -b feature/my-feature`  
3. Commit: `git commit -m "Add my feature"`  
4. Push and open a Pull Request  

Keep code typed, async, and consistent with the existing layout.

---

<p align="center">
  <sub>Built for speed and clarity. Drop a link. Get the media.</sub>
</p>
```

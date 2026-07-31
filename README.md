<p align="center">
  <img src="https://img.shields.io/badge/Telegram-Downloader-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white" alt="Telegram Downloader"/>
</p>

<h1 align="center">Telegram Downloader</h1>

<p align="center">
  <strong>Fast • Clean • Reliable</strong><br/>
  Download Stories, public posts, and restricted media from Telegram — in seconds.
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
  <img src="https://img.shields.io/badge/Colored_buttons-style_API-purple?style=flat-square" alt="Style"/>
</p>

---

## Overview

**Telegram Downloader** is a production-ready bot that fetches media from Telegram links and delivers it to the user in private chat.

| Source | Method | Speed |
|--------|--------|-------|
| Public channel / group posts | `copy_message` (no re-upload) | Instant |
| Restricted content | User account → download → bot re-upload | Depends on file size |
| Stories (photo / video) | Telethon Stories API | Depends on file size |

Built with a clean modular architecture, structured logging, typed models, and Docker support.

---

## Features

- **Stories** — photo & video via Telethon `GetStoriesByID`
- **Public posts** — instant copy, no bandwidth waste
- **Restricted media** — when the logged-in account has access
- **Media types** — photos, videos, documents, voice, audio, animations, stickers
- **Message ranges** — `https://t.me/channel/100-110` (up to 50)
- **Colored inline buttons** — `primary` / `success` / `danger` (Bot API style)
- **Parallel downloads** — up to 5 concurrent for ranges
- **High upload timeouts** — large files won’t fail mid-transfer
- **`.env` configuration** — no secrets in code
- **Structured logging** — clear, filterable output
- **Exception hierarchy** — predictable error handling
- **Type hints + async** throughout
- **Docker-ready**
- **No database** — stateless by design

---

## Stack

| Layer | Technology |
|-------|------------|
| Bot framework | [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) ≥ 22.7 |
| User / Stories API | [Telethon](https://github.com/LonamiWebs/Telethon) |
| Config | `python-dotenv` |
| Runtime | Python 3.11+ |

---

## Project Structure

```text
telegram_downloader/
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
├── handlers/
│   ├── start.py                # /start + styled button
│   ├── story.py                # Story links
│   └── restricted.py           # Public / restricted posts
│
├── services/
│   ├── parser.py               # Link detection
│   ├── story.py
│   ├── restricted.py           # Parallel download pipeline
│   └── sender.py               # Media delivery + keyboards
│
├── tg/
│   ├── story.py                # Telethon GetStoriesByID
│   └── messages.py             # Restricted message fetch
│
├── models/
│   ├── media.py                # MediaType, MediaItem, DownloadResult
│   └── result.py
│
└── utils/
    ├── regex.py
    ├── files.py
    └── helpers.py
```

---

## Installation

### 1. Clone

```bash
git clone https://github.com/DevZ44d/telegram_downloader.git
cd telegram_downloader
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
API_ID=12345678
API_HASH=your_api_hash
BOT_TOKEN=123456:ABC-DEF...
SESSION_STRING=                 # optional but required for Stories & restricted
DEVELOPER_URL=https://t.me/YourUsername
DOWNLOAD_DIR=downloads
LOG_LEVEL=INFO
```

| Variable | Required | Description |
|----------|----------|-------------|
| `API_ID` | Yes | From [my.telegram.org](https://my.telegram.org) |
| `API_HASH` | Yes | From my.telegram.org |
| `BOT_TOKEN` | Yes | From [@BotFather](https://t.me/BotFather) |
| `SESSION_STRING` | Recommended | Telethon string session (Stories + restricted) |
| `DEVELOPER_URL` | No | Shown on the start button |
| `DOWNLOAD_DIR` | No | Temp files (default: `downloads`) |
| `LOG_LEVEL` | No | `DEBUG` / `INFO` / `WARNING` / `ERROR` |

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

## Supported Links

| Type | Example |
|------|---------|
| Story | `https://t.me/username/s/123` |
| Public post | `https://t.me/channel/456` |
| Message range | `https://t.me/channel/100-105` |
| Restricted post* | Same as public (account must be a member) |

\* Requires a valid `SESSION_STRING`.

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
│ Link parser  │  → Story / Public / Invite / Unknown
└──────┬───────┘
       │
       ├─ Story ──────────► Telethon GetStoriesByID → download → bot send
       │
       ├─ Public post ────► bot.copy_message (fast path)
       │                         │ fail
       │                         ▼
       │                    Telethon download → bot re-upload
       │
       └─ Restricted ─────► Telethon only → download → bot re-upload
```

- **Public**: zero download when the bot can see the chat.
- **Restricted / Stories**: user client fetches media; bot delivers it to the user.

---

## Security Notes

- Never commit `.env` or session files.
- `SESSION_STRING` grants full account access — treat it like a password.
- The bot only answers in **private** chats.
- Temp files are deleted after send.

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

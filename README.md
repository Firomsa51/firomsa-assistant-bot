# 🤖 Firomsa Assistant Bot

> An enterprise-grade, AI-powered Telegram business assistant built with FastAPI, python-telegram-bot, Groq LLM, and PostgreSQL.

---

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Local Development](#local-development)
- [Environment Variables](#environment-variables)
- [Render Deployment](#render-deployment)
- [Telegram Setup](#telegram-setup)
- [API Documentation](#api-documentation)
- [Admin Commands](#admin-commands)

---

## Overview

**Firomsa Assistant Bot** is a production-ready Telegram AI business assistant that automatically handles customer support conversations, provides business information, and integrates with the Groq LLM API for intelligent, context-aware responses.

---

## Features

| Category | Capability |
|---|---|
| 🤖 AI Responses | Groq LLaMA 3.3 70B — fast, context-aware replies |
| 💬 Conversation Memory | Per-user history stored in PostgreSQL |
| 🛡️ Security | Webhook secret verification, rate limiting, input validation |
| 👥 Admin Panel | Broadcast, user management, stats, live settings |
| ⚙️ Business Profile | Configurable name, services, hours, FAQ — no redeploy needed |
| 🚀 Production Ready | Dockerfile, render.yaml, health check endpoint |
| 📊 Analytics | User stats, message counts, broadcast history |

---

## Architecture

```
Telegram Servers
      │  HTTPS POST  (secret token in header)
      ▼
┌─────────────────────────────────────┐
│         FastAPI (uvicorn)           │
│  POST /telegram/webhook             │
│  GET  /health                       │
└──────────┬──────────────────────────┘
           │
    ┌──────▼──────┐
    │  Bot Handlers│  (python-telegram-bot)
    │  commands.py │
    │  messages.py │
    └──────┬───────┘
           │
    ┌──────▼───────┐        ┌──────────────┐
    │  AI Module   │◄──────►│  Groq API    │
    │  assistant.py│        │  LLaMA 3.3   │
    └──────┬───────┘        └──────────────┘
           │
    ┌──────▼────────────┐
    │  PostgreSQL        │
    │  users             │
    │  conversations     │
    │  business_settings │
    │  broadcasts        │
    └───────────────────┘
```

---

## Tech Stack

- **Runtime**: Python 3.12
- **Web Framework**: FastAPI + uvicorn (ASGI)
- **Telegram**: python-telegram-bot 21.x (async webhook mode)
- **AI**: Groq SDK → LLaMA-3.3-70b-versatile
- **Database**: PostgreSQL + SQLAlchemy 2.0 (async) + asyncpg
- **Config**: pydantic-settings (env-first)
- **Logging**: structlog (JSON in production, coloured in debug)
- **Resilience**: tenacity (auto-retry on Groq failures)
- **Rate Limiting**: In-process per-user sliding window
- **Deployment**: Render Cloud, Docker

---

## Project Structure

```
firomsa-assistant-bot/
├── app/
│   ├── main.py           # FastAPI app factory + lifespan
│   ├── config.py         # Pydantic Settings (all env vars)
│   ├── webhook.py        # POST /telegram/webhook + GET /health
│   ├── bot/
│   │   ├── handlers.py   # Register all Telegram handlers
│   │   ├── commands.py   # /start /help /about /contact /services (+ admin)
│   │   ├── messages.py   # Free-text AI message handler + rate limiting
│   │   └── keyboards.py  # Reply & inline keyboards
│   ├── ai/
│   │   ├── assistant.py  # Groq API call with retry
│   │   ├── memory.py     # Load/save conversation history (PostgreSQL)
│   │   └── prompts.py    # System prompt builder + message templates
│   ├── database/
│   │   ├── models.py     # SQLAlchemy ORM models
│   │   └── connection.py # Async engine, session factory, init_db()
│   ├── services/
│   │   ├── user_service.py      # User CRUD + stats
│   │   └── business_service.py # Business profile settings
│   └── utils/
│       └── logger.py     # structlog setup
├── tests/
│   └── test_config.py
├── Dockerfile
├── docker-compose.yml
├── render.yaml
├── requirements.txt
├── .env.example
└── README.md
```

---

## Local Development

### Prerequisites

- Python 3.12
- PostgreSQL 14+
- A Telegram bot token from [@BotFather](https://t.me/BotFather)
- A Groq API key from [console.groq.com](https://console.groq.com)
- [ngrok](https://ngrok.com) or similar for local HTTPS tunnelling

### 1 — Clone & set up environment

```bash
cd firomsa-assistant-bot
cp .env.example .env
# Edit .env with your credentials
```

### 2 — Install dependencies

```bash
pip install -r requirements.txt
```

### 3 — Start the tunnel (for webhook testing)

```bash
ngrok http 8000
# Copy the HTTPS URL and set WEBHOOK_URL=https://xxxx.ngrok.io in .env
```

### 4 — Run the server

```bash
uvicorn app.main:app --reload --port 8000
```

The bot registers its webhook on startup automatically.

### Using Docker Compose

```bash
docker-compose up --build
```

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | ✅ | Token from @BotFather |
| `TELEGRAM_WEBHOOK_SECRET` | ✅ | Random string for webhook security |
| `WEBHOOK_URL` | ✅ | Your public HTTPS URL (no trailing slash) |
| `GROQ_API_KEY` | ✅ | Groq API key |
| `DATABASE_URL` | ✅ | PostgreSQL connection string |
| `ADMIN_TELEGRAM_IDS` | Recommended | Comma-separated admin Telegram user IDs |
| `GROQ_MODEL` | Optional | Default: `llama-3.3-70b-versatile` |
| `DEBUG` | Optional | `true` enables verbose logging and /docs |
| `PORT` | Optional | Default: `8000` |
| `RATE_LIMIT_PER_MINUTE` | Optional | Default: `10` |

---

## Render Deployment

### Step 1 — Push your code to GitHub

```bash
git init && git add . && git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/firomsa-assistant-bot.git
git push -u origin main
```

### Step 2 — Create a new Render Web Service

1. Go to [dashboard.render.com](https://dashboard.render.com) → **New → Web Service**
2. Connect your GitHub repo
3. Render auto-detects `render.yaml` — accept the configuration

### Step 3 — Set environment variables in Render

In the Render dashboard → **Environment**:

| Key | Value |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Your bot token |
| `TELEGRAM_WEBHOOK_SECRET` | Any random string (min 32 chars) |
| `WEBHOOK_URL` | `https://firomsa-assistant-bot.onrender.com` |
| `GROQ_API_KEY` | Your Groq key |
| `ADMIN_TELEGRAM_IDS` | Your Telegram numeric user ID |

> `DATABASE_URL` is wired automatically by `render.yaml` from the managed PostgreSQL database.

### Step 4 — Deploy

Click **Deploy** in Render. On the first deploy:
1. PostgreSQL database is provisioned
2. Python packages are installed
3. uvicorn starts
4. On startup, the bot registers its webhook with Telegram automatically

### Step 5 — Verify

```bash
curl https://firomsa-assistant-bot.onrender.com/health
# {"status":"ok","service":"Firomsa Assistant Bot"}
```

---

## Telegram Setup

### Create your bot

1. Open Telegram → search **@BotFather**
2. Send `/newbot` and follow instructions
3. Copy the token into `TELEGRAM_BOT_TOKEN`

### Get your admin Telegram ID

1. Search **@userinfobot** on Telegram
2. Send any message — it replies with your numeric user ID
3. Add it to `ADMIN_TELEGRAM_IDS`

### Bot commands (set in BotFather)

Send `/setcommands` to @BotFather and paste:

```
start - Start the bot and see the main menu
help - Show available commands
about - About this business
contact - Contact information
services - List all services
clear - Clear conversation history
admin - Admin panel (admins only)
stats - User statistics (admins only)
broadcast - Broadcast a message (admins only)
settings - View/edit business settings (admins only)
```

---

## API Documentation

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check (used by Render & load balancers) |
| `POST` | `/telegram/webhook` | Receive Telegram updates |
| `GET` | `/docs` | Interactive API docs (debug mode only) |

---

## Admin Commands

| Command | Description |
|---|---|
| `/admin` | Open admin panel with inline keyboard |
| `/stats` | Display user count, blocked count, total messages |
| `/broadcast <msg>` | Send a message to all active users |
| `/block <user_id>` | Block a user from using the bot |
| `/unblock <user_id>` | Unblock a previously blocked user |
| `/settings` | List all business profile settings |
| `/settings <key> <value>` | Update a business profile setting |
| `/clear` | Clear your own conversation history |

---

## Security

- **Webhook secret**: Telegram sends `X-Telegram-Bot-Api-Secret-Token` on every request; the app rejects anything that doesn't match using `hmac.compare_digest` (timing-safe).
- **Rate limiting**: In-process per-user 60-second sliding window. Default 10 req/min.
- **Input validation**: All inputs validated by pydantic before reaching business logic.
- **Non-root Docker**: Container runs as `botuser`, not root.
- **Env-first config**: No secrets in code — all loaded from environment.

---

## License

MIT © Firomsa Business

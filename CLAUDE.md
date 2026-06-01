# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the bot

```bash
# Activate conda env first
conda activate bot-schedule-discord

# Run locally (unbuffered output for readable logs)
python -u main.py

# Run in background with persistent log
nohup python -u main.py > bot.log 2>&1 &
```

Requires `BOT_TOKEN` and `DATABASE_URL` in `.env`.

## Architecture

The bot uses **discord.py 2.3.2** with a cog-based structure. Every command exists in two forms simultaneously: a slash command (`/hẹn-lịch`) and a prefix command (`kurumi hẹn-lịch`). Both forms are defined in the same cog class and must behave identically.

**`main.py`** — Bot entry point. Defines `get_prefix()` for case-insensitive `kurumi ` prefix, creates the asyncpg connection pool, calls `dm.init_db(pool)` to create tables, loads all cogs, and syncs slash commands via `setup_hook`.

**`utils/data_manager.py`** — All database access goes through here. Uses a module-level `_pool` set once at startup via `init_db()`. All functions are `async`. Tables: `special_days`, `tasks`, `weekly_slots`. Call `await dm.<function>(...)` directly — no need to pass a pool around.

**`utils/parser.py`** — Regex-based natural language parser for Vietnamese/English input. Three functions: `parse_date()` → `(month, day)`, `parse_time()` → `"HH:MM"`, `parse_duration()` → `int` minutes.

**`utils/schedule_image.py`** — Generates a Google Calendar-style PNG image of the weekly schedule using Pillow. Bundled fonts at `assets/fonts/DejaVuSans.ttf` and `DejaVuSans-Bold.ttf` are tried first (for Railway compatibility), then system font paths as fallback. Returns `io.BytesIO`.

**`cogs/reminder_loop.py`** — Background task (`@tasks.loop(minutes=1)`) that queries all users' data via `dm.get_all_reminder_data()`, checks if any reminder is due, sends DMs, and updates `last_reminded_date` / `last_reminded_at` immediately per-entry in the DB. Uses `Asia/Ho_Chi_Minh` (UTC+7) via `zoneinfo`.

**`cogs/special_day.py` / `cogs/daily_task.py`** — Multi-step conversation commands. Use `bot.wait_for("message", timeout=60)` to collect text input step-by-step in the server channel. `discord.ui.View` buttons handle yes/no and frequency selection.

**`cogs/weekly_schedule.py`** — Two commands: `/lịch-tuần` shows an interactive setup embed with 14 slot buttons (T2–CN × Sáng/Tối); clicking opens a `discord.ui.Modal` for task + time input. After ✅, saves to DB and replaces the embed with the calendar image. `/xem-lịch-tuần` sends the calendar image directly (content + file, no embed).

## Key constraints

- **Python 3.11 required** — `discord.py 2.3.2` uses `audioop` removed in Python 3.13. Pinned via `.python-version`.
- **Slash command names** — Discord allows Unicode (Vietnamese) but not spaces; use hyphens (`hẹn-lịch`, not `hẹn lịch`).
- **Message Content Intent** must be enabled in Discord Developer Portal for `wait_for("message")` to work.
- **Conversations happen in the server channel** where the command was typed (not in DM).
- **Reminders are sent via DM**. `discord.Forbidden` is caught silently when DMs are disabled.
- **Slash and prefix commands must behave identically** — same output, same logic.

## Adding a new command

1. Create or edit a cog in `cogs/`.
2. Add both `@app_commands.command(name="...")` (slash) and `@commands.command(name="...")` (prefix) methods with identical behaviour.
3. Register the cog in the `COGS` list in `main.py`.
4. Update the help embed in `cogs/help_cmd.py` (`_build_embed` method).
5. If the command stores data, add `async` CRUD helpers to `utils/data_manager.py` that use the module-level `_pool`.

## Database

- **Engine**: PostgreSQL via `asyncpg`, hosted on Railway.
- **Schema**: three tables — `special_days`, `tasks`, `weekly_slots` — created automatically by `init_db()` on startup.
- **Migration from JSON**: if `schedule_data.json` exists from an older version, run once: `python -m utils.migrate`.
- **Local dev**: set `DATABASE_URL=postgresql://...` in `.env`. SSL is added automatically for non-localhost URLs.

## Deployment

- **Hosting**: Railway, project `accomplished-analysis`.
- **Environment variables**: `BOT_TOKEN` and `DATABASE_URL` must be set (Railway injects `DATABASE_URL` automatically when a PostgreSQL service is linked).
- **GitHub repo**: `HieuPhung1003/bot-shedule-discord` — Railway auto-deploys on push to `main`.
- **Font support on Railway**: `nixpacks.toml` installs `fonts-dejavu-core`; bundled fonts in `assets/fonts/` are the primary fallback so Vietnamese text renders correctly regardless.
- Railway CLI: `~/.railway/bin/railway`

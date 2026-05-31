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

# Deploy to Railway
~/.railway/bin/railway up --detach --service accomplished-analysis
```

## Architecture

The bot uses **discord.py 2.3.2** with a cog-based structure. Every command exists in two forms simultaneously: a slash command (`/hẹn-lịch`) and a prefix command (`kurumi hẹn-lịch`). Both forms are defined in the same cog class.

**`main.py`** — Bot entry point. Defines `get_prefix()` for case-insensitive `kurumi ` prefix, loads all cogs, and syncs slash commands on startup via `setup_hook`.

**`utils/parser.py`** — Regex-based natural language parser for Vietnamese/English input. Three functions: `parse_date()` → `(month, day)`, `parse_time()` → `"HH:MM"`, `parse_duration()` → `int` minutes.

**`utils/data_manager.py`** — All JSON read/write goes through here. Data lives in `schedule_data.json` (auto-created). Schema: `{"users": {"<user_id>": {"special_days": [...], "tasks": [...]}}}`.

**`cogs/reminder_loop.py`** — Background task (`@tasks.loop(minutes=1)`) that checks every minute whether any reminder is due and sends DMs. Uses `Asia/Ho_Chi_Minh` (UTC+7) via Python's built-in `zoneinfo`. Deduplication: special days check `last_reminded_date` (date string), tasks check `last_reminded_at` (ISO datetime).

**`cogs/special_day.py` / `cogs/daily_task.py`** — Multi-step conversation commands. Use `bot.wait_for("message", timeout=60)` to collect text input step-by-step in the server channel. `discord.ui.View` buttons handle yes/no and frequency selection.

## Key constraints

- **Python 3.11 required** — `discord.py 2.3.2` uses `audioop` which was removed in Python 3.13. Pinned via `.python-version`.
- **Slash command names** — Discord allows Unicode (Vietnamese) but not spaces; use hyphens (`hẹn-lịch`, not `hẹn lịch`).
- **Message Content Intent** must be enabled in Discord Developer Portal for `wait_for("message")` to read user replies.
- **Conversations happen in the server channel** where the command was typed (not in DM).
- **Reminders are sent via DM**. If a user has DMs disabled, the reminder silently fails (`discord.Forbidden` is caught).

## Adding a new command

1. Create or edit a cog in `cogs/`.
2. Add both `@app_commands.command(name="...")` (slash) and `@commands.command(name="...")` (prefix) methods.
3. Register the cog in the `COGS` list in `main.py`.
4. Update the help embed in `cogs/help_cmd.py` (`_build_embed` method).
5. If the command stores data, add CRUD helpers to `utils/data_manager.py`.

## Deployment

- **Hosting**: Railway, project `accomplished-analysis`.
- **Environment variable**: `BOT_TOKEN` must be set in Railway (already configured).
- **GitHub repo**: `HieuPhung1003/bot-shedule-discord` — Railway is connected for auto-deploy on push to `main`.
- Railway CLI: `~/.railway/bin/railway`

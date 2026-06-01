import uuid

import asyncpg

_pool: asyncpg.Pool | None = None

_WEEK_DAYS = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]


async def init_db(pool: asyncpg.Pool) -> None:
    global _pool
    _pool = pool
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS special_days (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                name TEXT NOT NULL,
                month INTEGER NOT NULL,
                day INTEGER NOT NULL,
                remind_days_before INTEGER NOT NULL,
                recurring_daily BOOLEAN NOT NULL,
                remind_time TEXT NOT NULL,
                last_reminded_date TEXT
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                name TEXT NOT NULL,
                frequency_minutes INTEGER NOT NULL,
                last_reminded_at TEXT
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS weekly_slots (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                day TEXT NOT NULL,
                period TEXT NOT NULL,
                task TEXT NOT NULL,
                time_from TEXT,
                time_to TEXT
            )
        """)
        # Migration: old schema used composite PK (user_id, day, period) with no id column
        has_id = await conn.fetchval(
            "SELECT COUNT(*) FROM information_schema.columns "
            "WHERE table_name='weekly_slots' AND column_name='id'"
        )
        if not has_id:
            await conn.execute("ALTER TABLE weekly_slots DROP CONSTRAINT weekly_slots_pkey")
            await conn.execute("ALTER TABLE weekly_slots ADD COLUMN id TEXT")
            rows = await conn.fetch("SELECT user_id, day, period FROM weekly_slots")
            for r in rows:
                await conn.execute(
                    "UPDATE weekly_slots SET id=$1 WHERE user_id=$2 AND day=$3 AND period=$4",
                    str(uuid.uuid4()), r["user_id"], r["day"], r["period"],
                )
            await conn.execute("ALTER TABLE weekly_slots ALTER COLUMN id SET NOT NULL")
            await conn.execute("ALTER TABLE weekly_slots ADD PRIMARY KEY (id)")


async def close() -> None:
    if _pool:
        await _pool.close()


# ── Special Days ──────────────────────────────────────────────────────────────

async def add_special_day(
    user_id: str,
    name: str,
    month: int,
    day: int,
    remind_days_before: int,
    recurring_daily: bool,
    remind_time: str,
) -> str:
    entry_id = str(uuid.uuid4())
    await _pool.execute(
        """
        INSERT INTO special_days
            (id, user_id, name, month, day, remind_days_before, recurring_daily, remind_time)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        """,
        entry_id, user_id, name, month, day, remind_days_before, recurring_daily, remind_time,
    )
    return entry_id


async def get_special_days(user_id: str) -> list[dict]:
    rows = await _pool.fetch("SELECT * FROM special_days WHERE user_id = $1", user_id)
    return [dict(r) for r in rows]


async def remove_special_day(user_id: str, entry_id: str) -> bool:
    result = await _pool.execute(
        "DELETE FROM special_days WHERE id = $1 AND user_id = $2", entry_id, user_id
    )
    return result == "DELETE 1"


async def update_special_day_reminded(user_id: str, entry_id: str, date_str: str) -> None:
    await _pool.execute(
        "UPDATE special_days SET last_reminded_date = $1 WHERE id = $2 AND user_id = $3",
        date_str, entry_id, user_id,
    )


# ── Tasks ─────────────────────────────────────────────────────────────────────

async def add_task(user_id: str, name: str, frequency_minutes: int) -> str:
    entry_id = str(uuid.uuid4())
    await _pool.execute(
        "INSERT INTO tasks (id, user_id, name, frequency_minutes) VALUES ($1, $2, $3, $4)",
        entry_id, user_id, name, frequency_minutes,
    )
    return entry_id


async def get_tasks(user_id: str) -> list[dict]:
    rows = await _pool.fetch("SELECT * FROM tasks WHERE user_id = $1", user_id)
    return [dict(r) for r in rows]


async def remove_task(user_id: str, entry_id: str) -> bool:
    result = await _pool.execute(
        "DELETE FROM tasks WHERE id = $1 AND user_id = $2", entry_id, user_id
    )
    return result == "DELETE 1"


async def update_task_reminded(user_id: str, entry_id: str, datetime_str: str) -> None:
    await _pool.execute(
        "UPDATE tasks SET last_reminded_at = $1 WHERE id = $2 AND user_id = $3",
        datetime_str, entry_id, user_id,
    )


async def remove_entry(user_id: str, entry_type: str, entry_id: str) -> bool:
    if entry_type == "special_days":
        return await remove_special_day(user_id, entry_id)
    elif entry_type == "tasks":
        return await remove_task(user_id, entry_id)
    return False


# ── Weekly Schedule ───────────────────────────────────────────────────────────

def _empty_weekly() -> dict:
    return {d: {"sang": [], "toi": []} for d in _WEEK_DAYS}


async def get_weekly_schedule(user_id: str) -> dict:
    rows = await _pool.fetch(
        "SELECT day, period, task, time_from, time_to FROM weekly_slots WHERE user_id = $1",
        user_id,
    )
    schedule = _empty_weekly()
    for r in rows:
        schedule[r["day"]][r["period"]].append({
            "task": r["task"],
            "from": r["time_from"] or "",
            "to": r["time_to"] or "",
        })
    return schedule


async def set_weekly_schedule(user_id: str, schedule: dict) -> None:
    async with _pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute("DELETE FROM weekly_slots WHERE user_id = $1", user_id)
            for day, periods in schedule.items():
                for period, entries in periods.items():
                    for entry in entries:
                        if entry and entry.get("task"):
                            await conn.execute(
                                """
                                INSERT INTO weekly_slots
                                    (id, user_id, day, period, task, time_from, time_to)
                                VALUES ($1, $2, $3, $4, $5, $6, $7)
                                """,
                                str(uuid.uuid4()), user_id, day, period, entry["task"],
                                entry.get("from") or None,
                                entry.get("to") or None,
                            )


# ── Reminder loop ─────────────────────────────────────────────────────────────

async def get_all_reminder_data() -> dict[str, dict]:
    """Returns {user_id: {"special_days": [...], "tasks": [...]}}"""
    sd_rows = await _pool.fetch("SELECT * FROM special_days")
    task_rows = await _pool.fetch("SELECT * FROM tasks")

    result: dict[str, dict] = {}
    for r in sd_rows:
        uid = r["user_id"]
        if uid not in result:
            result[uid] = {"special_days": [], "tasks": []}
        result[uid]["special_days"].append(dict(r))
    for r in task_rows:
        uid = r["user_id"]
        if uid not in result:
            result[uid] = {"special_days": [], "tasks": []}
        result[uid]["tasks"].append(dict(r))
    return result

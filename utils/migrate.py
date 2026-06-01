"""
One-time migration: schedule_data.json → PostgreSQL.
Run once after setting up the database:
    python -m utils.migrate
"""
import asyncio
import json
import os
from pathlib import Path

import asyncpg
from dotenv import load_dotenv

load_dotenv()

DATA_FILE = Path(__file__).parent.parent / "schedule_data.json"


async def migrate() -> None:
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL not set in .env")

    ssl = "require" if "localhost" not in db_url and "127.0.0.1" not in db_url else None
    pool = await asyncpg.create_pool(db_url, ssl=ssl)

    from utils.data_manager import init_db
    await init_db(pool)

    if not DATA_FILE.exists():
        print("schedule_data.json not found — nothing to migrate.")
        await pool.close()
        return

    with open(DATA_FILE, encoding="utf-8") as f:
        data = json.load(f)

    count = {"special_days": 0, "tasks": 0, "weekly_slots": 0}

    for user_id, user_data in data.get("users", {}).items():
        for sd in user_data.get("special_days", []):
            await pool.execute(
                """
                INSERT INTO special_days
                    (id, user_id, name, month, day, remind_days_before,
                     recurring_daily, remind_time, last_reminded_date)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
                ON CONFLICT (id) DO NOTHING
                """,
                sd["id"], user_id, sd["name"], sd["month"], sd["day"],
                sd["remind_days_before"], sd["recurring_daily"],
                sd["remind_time"], sd.get("last_reminded_date"),
            )
            count["special_days"] += 1

        for task in user_data.get("tasks", []):
            await pool.execute(
                """
                INSERT INTO tasks
                    (id, user_id, name, frequency_minutes, last_reminded_at)
                VALUES ($1,$2,$3,$4,$5)
                ON CONFLICT (id) DO NOTHING
                """,
                task["id"], user_id, task["name"],
                task["frequency_minutes"], task.get("last_reminded_at"),
            )
            count["tasks"] += 1

        for day, periods in user_data.get("weekly_schedule", {}).items():
            for period, entry in periods.items():
                if entry and entry.get("task"):
                    await pool.execute(
                        """
                        INSERT INTO weekly_slots
                            (user_id, day, period, task, time_from, time_to)
                        VALUES ($1,$2,$3,$4,$5,$6)
                        ON CONFLICT (user_id, day, period) DO UPDATE
                            SET task = EXCLUDED.task,
                                time_from = EXCLUDED.time_from,
                                time_to = EXCLUDED.time_to
                        """,
                        user_id, day, period, entry["task"],
                        entry.get("from") or None,
                        entry.get("to") or None,
                    )
                    count["weekly_slots"] += 1

    await pool.close()
    print(f"Migration complete: {count}")


if __name__ == "__main__":
    asyncio.run(migrate())

import json
import os
import uuid
from typing import Optional

DATA_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "schedule_data.json")


def load_data() -> dict:
    if not os.path.exists(DATA_FILE):
        return {"users": {}}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_data(data: dict) -> None:
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_user(data: dict, user_id: str) -> dict:
    if user_id not in data["users"]:
        data["users"][user_id] = {"special_days": [], "tasks": []}
    return data["users"][user_id]


def add_special_day(
    data: dict,
    user_id: str,
    name: str,
    month: int,
    day: int,
    remind_days_before: int,
    recurring_daily: bool,
    remind_time: str,
) -> str:
    user = get_user(data, user_id)
    entry = {
        "id": str(uuid.uuid4()),
        "name": name,
        "month": month,
        "day": day,
        "remind_days_before": remind_days_before,
        "recurring_daily": recurring_daily,
        "remind_time": remind_time,
        "last_reminded_date": None,
    }
    user["special_days"].append(entry)
    save_data(data)
    return entry["id"]


def add_task(data: dict, user_id: str, name: str, frequency_minutes: int) -> str:
    user = get_user(data, user_id)
    entry = {
        "id": str(uuid.uuid4()),
        "name": name,
        "frequency_minutes": frequency_minutes,
        "last_reminded_at": None,
    }
    user["tasks"].append(entry)
    save_data(data)
    return entry["id"]


def remove_entry(data: dict, user_id: str, entry_type: str, entry_id: str) -> bool:
    user = get_user(data, user_id)
    original = user[entry_type]
    filtered = [e for e in original if e["id"] != entry_id]
    if len(filtered) == len(original):
        return False
    user[entry_type] = filtered
    save_data(data)
    return True


def update_special_day_reminded(data: dict, user_id: str, entry_id: str, date_str: str) -> None:
    user = get_user(data, user_id)
    for entry in user["special_days"]:
        if entry["id"] == entry_id:
            entry["last_reminded_date"] = date_str
            break
    save_data(data)


def update_task_reminded(data: dict, user_id: str, entry_id: str, datetime_str: str) -> None:
    user = get_user(data, user_id)
    for entry in user["tasks"]:
        if entry["id"] == entry_id:
            entry["last_reminded_at"] = datetime_str
            break
    save_data(data)


_WEEK_DAYS = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]


def _empty_weekly() -> dict:
    return {d: {"sang": None, "toi": None} for d in _WEEK_DAYS}


def get_weekly_schedule(user_id: str) -> dict:
    data = load_data()
    stored = data["users"].get(user_id, {}).get("weekly_schedule")
    if not stored:
        return _empty_weekly()
    schedule = _empty_weekly()
    schedule.update(stored)
    return schedule


def set_weekly_schedule(user_id: str, schedule: dict) -> None:
    data = load_data()
    user = get_user(data, user_id)
    user["weekly_schedule"] = schedule
    save_data(data)

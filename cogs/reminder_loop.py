from datetime import date, datetime
from zoneinfo import ZoneInfo

import discord
from discord.ext import commands, tasks

from utils import data_manager as dm

TZ = ZoneInfo("Asia/Ho_Chi_Minh")


def days_until(month: int, day: int, today: date) -> int:
    target = date(today.year, month, day)
    if target < today:
        target = date(today.year + 1, month, day)
    return (target - today).days


class ReminderLoop(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.reminder_task.start()

    def cog_unload(self):
        self.reminder_task.cancel()

    @tasks.loop(minutes=1)
    async def reminder_task(self):
        now = datetime.now(TZ)
        today = now.date()
        current_time = now.strftime("%H:%M")

        all_data = await dm.get_all_reminder_data()

        for user_id, user_data in all_data.items():
            discord_user = None

            # --- Special days ---
            for entry in user_data["special_days"]:
                remaining = days_until(entry["month"], entry["day"], today)

                should_remind_today = remaining <= entry["remind_days_before"]
                if not entry["recurring_daily"] and remaining != entry["remind_days_before"]:
                    should_remind_today = remaining == entry["remind_days_before"]

                if not should_remind_today:
                    continue
                if entry["remind_time"] != current_time:
                    continue
                if entry["last_reminded_date"] == today.isoformat():
                    continue

                discord_user = discord_user or await self._fetch_user(int(user_id))
                if discord_user:
                    await self._send_special_day_dm(discord_user, entry, remaining)
                    await dm.update_special_day_reminded(user_id, entry["id"], today.isoformat())

            # --- Daily tasks ---
            for entry in user_data["tasks"]:
                last = entry.get("last_reminded_at")
                if last is None:
                    due = True
                else:
                    last_dt = datetime.fromisoformat(last)
                    due = (now - last_dt).total_seconds() / 60 >= entry["frequency_minutes"]

                if not due:
                    continue

                discord_user = discord_user or await self._fetch_user(int(user_id))
                if discord_user:
                    await self._send_task_dm(discord_user, entry)
                    await dm.update_task_reminded(user_id, entry["id"], now.isoformat())

    @reminder_task.before_loop
    async def before_reminder(self):
        await self.bot.wait_until_ready()

    async def _fetch_user(self, user_id: int) -> discord.User | None:
        try:
            return await self.bot.fetch_user(user_id)
        except (discord.NotFound, discord.HTTPException):
            return None

    async def _send_special_day_dm(self, user: discord.User, entry: dict, remaining: int) -> None:
        if remaining == 0:
            when = "**HÔM NAY** là"
        elif remaining == 1:
            when = "**NGÀY MAI** là"
        else:
            when = f"Còn **{remaining} ngày** nữa là"

        embed = discord.Embed(
            title="🎉 Nhắc nhở ngày đặc biệt!",
            description=f"{when} **{entry['name']}** ({entry['day']}/{entry['month']})!",
            color=discord.Color.gold(),
        )
        try:
            await user.send(embed=embed)
        except discord.Forbidden:
            pass

    async def _send_task_dm(self, user: discord.User, entry: dict) -> None:
        embed = discord.Embed(
            title="📝 Nhắc nhở công việc!",
            description=f"Đừng quên: **{entry['name']}** nhé!",
            color=discord.Color.blue(),
        )
        try:
            await user.send(embed=embed)
        except discord.Forbidden:
            pass


async def setup(bot: commands.Bot):
    await bot.add_cog(ReminderLoop(bot))

from datetime import date, datetime
from zoneinfo import ZoneInfo

import discord
from discord import app_commands
from discord.ext import commands

from utils import data_manager as dm

TZ = ZoneInfo("Asia/Ho_Chi_Minh")


def days_until(month: int, day: int) -> int:
    today = datetime.now(TZ).date()
    target = date(today.year, month, day)
    if target < today:
        target = date(today.year + 1, month, day)
    return (target - today).days


def minutes_to_label(minutes: int) -> str:
    if minutes % 1440 == 0:
        return f"{minutes // 1440} ngày"
    if minutes % 60 == 0:
        return f"{minutes // 60} giờ"
    return f"{minutes} phút"


class ViewSchedules(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="my-schedules", description="Xem toàn bộ lịch nhắc nhở của bạn")
    async def my_schedules(self, interaction: discord.Interaction):
        data = dm.load_data()
        user = dm.get_user(data, str(interaction.user.id))

        embed = discord.Embed(
            title=f"📅 Lịch nhắc nhở của {interaction.user.display_name}",
            color=discord.Color.blue(),
        )

        # Special days
        special_days = user.get("special_days", [])
        if special_days:
            lines = []
            for s in special_days:
                remaining = days_until(s["month"], s["day"])
                recurring = "🔁" if s["recurring_daily"] else ""
                lines.append(
                    f"• **{s['name']}** — {s['day']}/{s['month']} "
                    f"(còn {remaining} ngày) | nhắc lúc {s['remind_time']} {recurring}"
                )
            embed.add_field(name="🎉 Ngày đặc biệt", value="\n".join(lines), inline=False)
        else:
            embed.add_field(name="🎉 Ngày đặc biệt", value="Chưa có.", inline=False)

        # Daily tasks
        tasks = user.get("tasks", [])
        if tasks:
            lines = []
            for t in tasks:
                lines.append(
                    f"• **{t['name']}** — mỗi {minutes_to_label(t['frequency_minutes'])}"
                )
            embed.add_field(name="📝 Công việc hàng ngày", value="\n".join(lines), inline=False)
        else:
            embed.add_field(name="📝 Công việc hàng ngày", value="Chưa có.", inline=False)

        embed.set_footer(text="Dùng /cancel-schedule để hủy lịch.")
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(ViewSchedules(bot))

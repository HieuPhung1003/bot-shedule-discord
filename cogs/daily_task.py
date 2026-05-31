import asyncio

import discord
from discord import app_commands
from discord.ext import commands

from utils import data_manager as dm
from utils.parser import parse_duration

PRESET_DURATIONS = [
    ("30 phút", 30),
    ("1 giờ", 60),
    ("2 giờ", 120),
    ("4 giờ", 240),
    ("8 giờ", 480),
    ("1 ngày", 1440),
]


class FrequencyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)
        self.value: int | None = None
        self.custom = False

        for label, minutes in PRESET_DURATIONS:
            self.add_item(FrequencyButton(label, minutes))

        self.add_item(CustomButton())


class FrequencyButton(discord.ui.Button):
    def __init__(self, label: str, minutes: int):
        super().__init__(label=label, style=discord.ButtonStyle.primary)
        self.minutes = minutes

    async def callback(self, interaction: discord.Interaction):
        self.view.value = self.minutes
        self.view.stop()
        await interaction.response.defer()


class CustomButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Nhập tay", style=discord.ButtonStyle.secondary)

    async def callback(self, interaction: discord.Interaction):
        self.view.custom = True
        self.view.stop()
        await interaction.response.defer()


def minutes_to_label(minutes: int) -> str:
    if minutes % 1440 == 0:
        return f"{minutes // 1440} ngày"
    if minutes % 60 == 0:
        return f"{minutes // 60} giờ"
    return f"{minutes} phút"


class DailyTask(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="schedule-task",
        description="Đặt công việc nhắc nhở hàng ngày (uống nước, tập thể dục...)",
    )
    async def schedule_task(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)

        # Step 1: Task name
        await interaction.followup.send("📝 **Tên công việc muốn được nhắc?**\nVD: Uống nước, Tập thể dục, Đọc sách...")

        def check(m: discord.Message):
            return m.author.id == interaction.user.id and m.channel.id == interaction.channel_id

        try:
            msg = await self.bot.wait_for("message", check=check, timeout=60)
            task_name = msg.content.strip()
        except asyncio.TimeoutError:
            await interaction.followup.send("⏰ Hết thời gian chờ. Vui lòng thử lại.")
            return

        # Step 2: Frequency
        view = FrequencyView()
        await interaction.followup.send("⏱️ **Tần suất nhắc nhở?** Chọn hoặc nhập tay:", view=view)
        await view.wait()

        if view.value is None and not view.custom:
            await interaction.followup.send("⏰ Hết thời gian chờ. Vui lòng thử lại.")
            return

        if view.custom:
            await interaction.followup.send(
                "✏️ Nhập tần suất (VD: 45 phút, 3 giờ, 1 ngày, 90m, 2h):"
            )
            try:
                msg = await self.bot.wait_for("message", check=check, timeout=60)
                freq_minutes = parse_duration(msg.content.strip())
                if not freq_minutes or freq_minutes <= 0:
                    await interaction.followup.send("❌ Không nhận ra định dạng. Vui lòng thử lại.")
                    return
            except asyncio.TimeoutError:
                await interaction.followup.send("⏰ Hết thời gian chờ. Vui lòng thử lại.")
                return
        else:
            freq_minutes = view.value

        # Save
        data = dm.load_data()
        dm.add_task(data, str(interaction.user.id), name=task_name, frequency_minutes=freq_minutes)

        embed = discord.Embed(title="✅ Đã đặt lịch công việc!", color=discord.Color.green())
        embed.add_field(name="Công việc", value=task_name, inline=True)
        embed.add_field(name="Tần suất", value=minutes_to_label(freq_minutes), inline=True)
        embed.set_footer(text="Bot sẽ gửi nhắc nhở qua DM của bạn.")
        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(DailyTask(bot))

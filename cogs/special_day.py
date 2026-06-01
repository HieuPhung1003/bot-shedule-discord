import asyncio

import discord
from discord import app_commands
from discord.ext import commands

from utils import data_manager as dm
from utils.parser import parse_date, parse_time


class YesNoView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)
        self.value: bool | None = None

    @discord.ui.button(label="Có", style=discord.ButtonStyle.green)
    async def yes(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = True
        self.stop()
        await interaction.response.defer()

    @discord.ui.button(label="Không", style=discord.ButtonStyle.red)
    async def no(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = False
        self.stop()
        await interaction.response.defer()


async def ask(interaction: discord.Interaction, bot: commands.Bot, prompt: str) -> str | None:
    """Send a question and wait up to 60s for the user's text reply."""
    await interaction.followup.send(prompt)

    def check(m: discord.Message):
        return m.author.id == interaction.user.id and m.channel.id == interaction.channel_id

    try:
        msg = await bot.wait_for("message", check=check, timeout=60)
        return msg.content.strip()
    except asyncio.TimeoutError:
        await interaction.followup.send("⏰ Hết thời gian chờ. Vui lòng thử lại.")
        return None


class SpecialDay(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="hẹn-lịch",
        description="Đặt lịch nhắc ngày đặc biệt (sinh nhật, kỷ niệm...)",
    )
    async def schedule_special(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)

        # Step 1: Name
        name = await ask(interaction, self.bot, "🎉 **Đây là ngày gì?**\nVD: Sinh nhật mẹ, Kỷ niệm yêu nhau...")
        if not name:
            return

        # Step 2: Date
        while True:
            date_text = await ask(
                interaction, self.bot,
                "📅 **Nhập ngày** (VD: 25/7, 25-7, 25 tháng 7):"
            )
            if not date_text:
                return
            parsed = parse_date(date_text)
            if parsed:
                month, day = parsed
                break
            await interaction.followup.send("❌ Không nhận ra định dạng ngày. Thử lại nhé!")

        # Step 3: Remind days before
        while True:
            days_text = await ask(
                interaction, self.bot,
                "🔔 **Nhắc trước bao nhiêu ngày?** (VD: 3, 7, 1):"
            )
            if not days_text:
                return
            if days_text.isdigit() and int(days_text) >= 0:
                remind_days_before = int(days_text)
                break
            await interaction.followup.send("❌ Vui lòng nhập một số nguyên dương.")

        # Step 4: Recurring daily
        view = YesNoView()
        msg = await interaction.followup.send(
            "🔁 **Có nhắc định kì mỗi ngày cho đến ngày đó không?**",
            view=view,
        )
        await view.wait()
        if view.value is None:
            await interaction.followup.send("⏰ Hết thời gian chờ. Vui lòng thử lại.")
            return
        recurring_daily = view.value

        # Step 5: Remind time
        while True:
            time_text = await ask(
                interaction, self.bot,
                "🕐 **Nhắc lúc mấy giờ?** (VD: 9:00, 14:30, 9 giờ sáng, 9h30):"
            )
            if not time_text:
                return
            parsed_time = parse_time(time_text)
            if parsed_time:
                remind_time = parsed_time
                break
            await interaction.followup.send("❌ Không nhận ra định dạng giờ. Thử lại nhé!")

        # Save
        await dm.add_special_day(
            str(interaction.user.id),
            name=name,
            month=month,
            day=day,
            remind_days_before=remind_days_before,
            recurring_daily=recurring_daily,
            remind_time=remind_time,
        )

        embed = discord.Embed(title="✅ Đã đặt lịch ngày đặc biệt!", color=discord.Color.green())
        embed.add_field(name="Sự kiện", value=name, inline=True)
        embed.add_field(name="Ngày", value=f"{day}/{month} hàng năm", inline=True)
        embed.add_field(name="Nhắc trước", value=f"{remind_days_before} ngày", inline=True)
        embed.add_field(name="Nhắc định kì", value="Có" if recurring_daily else "Không", inline=True)
        embed.add_field(name="Giờ nhắc", value=remind_time, inline=True)
        embed.set_footer(text="Bot sẽ gửi nhắc nhở qua DM của bạn.")
        await interaction.followup.send(embed=embed)


    @commands.command(name="hẹn-lịch")
    async def schedule_special_prefix(self, ctx: commands.Context):
        def check(m: discord.Message):
            return m.author.id == ctx.author.id and m.channel.id == ctx.channel.id

        async def ask_prefix(prompt: str):
            await ctx.send(prompt)
            try:
                msg = await self.bot.wait_for("message", check=check, timeout=60)
                return msg.content.strip()
            except asyncio.TimeoutError:
                await ctx.send("⏰ Hết thời gian chờ. Vui lòng thử lại.")
                return None

        name = await ask_prefix("🎉 **Đây là ngày gì?**\nVD: Sinh nhật mẹ, Kỷ niệm yêu nhau...")
        if not name:
            return

        while True:
            date_text = await ask_prefix("📅 **Nhập ngày** (VD: 25/7, 25-7, 25 tháng 7):")
            if not date_text:
                return
            parsed = parse_date(date_text)
            if parsed:
                month, day = parsed
                break
            await ctx.send("❌ Không nhận ra định dạng ngày. Thử lại nhé!")

        while True:
            days_text = await ask_prefix("🔔 **Nhắc trước bao nhiêu ngày?** (VD: 3, 7, 1):")
            if not days_text:
                return
            if days_text.isdigit() and int(days_text) >= 0:
                remind_days_before = int(days_text)
                break
            await ctx.send("❌ Vui lòng nhập một số nguyên dương.")

        view = YesNoView()
        await ctx.send("🔁 **Có nhắc định kì mỗi ngày cho đến ngày đó không?**", view=view)
        await view.wait()
        if view.value is None:
            await ctx.send("⏰ Hết thời gian chờ. Vui lòng thử lại.")
            return
        recurring_daily = view.value

        while True:
            time_text = await ask_prefix("🕐 **Nhắc lúc mấy giờ?** (VD: 9:00, 14:30, 9 giờ sáng, 9h30):")
            if not time_text:
                return
            parsed_time = parse_time(time_text)
            if parsed_time:
                remind_time = parsed_time
                break
            await ctx.send("❌ Không nhận ra định dạng giờ. Thử lại nhé!")

        await dm.add_special_day(
            str(ctx.author.id),
            name=name, month=month, day=day,
            remind_days_before=remind_days_before,
            recurring_daily=recurring_daily,
            remind_time=remind_time,
        )

        embed = discord.Embed(title="✅ Đã đặt lịch ngày đặc biệt!", color=discord.Color.green())
        embed.add_field(name="Sự kiện", value=name, inline=True)
        embed.add_field(name="Ngày", value=f"{day}/{month} hàng năm", inline=True)
        embed.add_field(name="Nhắc trước", value=f"{remind_days_before} ngày", inline=True)
        embed.add_field(name="Nhắc định kì", value="Có" if recurring_daily else "Không", inline=True)
        embed.add_field(name="Giờ nhắc", value=remind_time, inline=True)
        embed.set_footer(text="Bot sẽ gửi nhắc nhở qua DM của bạn.")
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(SpecialDay(bot))

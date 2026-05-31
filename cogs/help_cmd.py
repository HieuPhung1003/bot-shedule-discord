import discord
from discord import app_commands
from discord.ext import commands


class HelpCmd(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="help", description="Xem danh sách tất cả lệnh của bot")
    async def help_command(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📅 Discord Schedule Bot — Trợ giúp",
            color=discord.Color.blue(),
        )
        embed.add_field(
            name="/schedule-special",
            value="Đặt lịch nhắc ngày đặc biệt (sinh nhật, kỷ niệm...)",
            inline=False,
        )
        embed.add_field(
            name="/schedule-task",
            value="Đặt công việc nhắc nhở hàng ngày (uống nước, tập thể dục...)",
            inline=False,
        )
        embed.add_field(
            name="/my-schedules",
            value="Xem toàn bộ lịch nhắc nhở của bạn",
            inline=False,
        )
        embed.add_field(
            name="/cancel-schedule",
            value="Hủy một lịch nhắc nhở",
            inline=False,
        )
        embed.add_field(
            name="/help",
            value="Hiển thị tin nhắn trợ giúp này",
            inline=False,
        )
        embed.set_footer(text="Bot sẽ gửi nhắc nhở qua DM. Hãy đảm bảo DM của bạn đang mở.")
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(HelpCmd(bot))

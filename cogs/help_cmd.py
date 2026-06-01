import discord
from discord import app_commands
from discord.ext import commands


class HelpCmd(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="help", description="Xem danh sách tất cả lệnh của bot")
    async def help_command(self, interaction: discord.Interaction):
        await interaction.response.send_message(embed=self._build_embed(), ephemeral=True)


    @commands.command(name="help")
    async def help_prefix(self, ctx: commands.Context):
        embed = self._build_embed()
        await ctx.send(embed=embed)

    def _build_embed(self):
        embed = discord.Embed(
            title="📅 Discord Schedule Bot — Trợ giúp",
            color=discord.Color.blue(),
        )
        embed.add_field(name="/hẹn-lịch  |  kurumi hẹn-lịch", value="Đặt lịch nhắc ngày đặc biệt (sinh nhật, kỷ niệm...)", inline=False)
        embed.add_field(name="/nhắc-việc  |  kurumi nhắc-việc", value="Đặt công việc nhắc nhở hàng ngày (uống nước, tập thể dục...)", inline=False)
        embed.add_field(name="/xem-hẹn  |  kurumi xem-hẹn", value="Xem toàn bộ lịch nhắc nhở của bạn", inline=False)
        embed.add_field(name="/hủy-hẹn  |  kurumi hủy-hẹn", value="Hủy một lịch nhắc nhở", inline=False)
        embed.add_field(name="/lịch-tuần  |  kurumi lịch-tuần", value="Thiết lập lịch hoạt động trong tuần (sáng/tối từng ngày)", inline=False)
        embed.add_field(name="/xem-lịch-tuần  |  kurumi xem-lịch-tuần", value="Xem lịch hoạt động trong tuần dưới dạng bảng", inline=False)
        embed.add_field(name="/help  |  kurumi help", value="Hiển thị tin nhắn trợ giúp này", inline=False)
        embed.set_footer(text="Bot sẽ gửi nhắc nhở qua DM. Hãy đảm bảo DM của bạn đang mở.")
        return embed


async def setup(bot: commands.Bot):
    await bot.add_cog(HelpCmd(bot))

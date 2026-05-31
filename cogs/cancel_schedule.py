import discord
from discord import app_commands
from discord.ext import commands

from utils import data_manager as dm


class CancelSelect(discord.ui.Select):
    def __init__(self, options: list[discord.SelectOption], entries: list[dict]):
        super().__init__(placeholder="Chọn lịch muốn hủy...", options=options, min_values=1, max_values=1)
        self.entries = entries

    async def callback(self, interaction: discord.Interaction):
        selected_id = self.values[0]
        entry = next((e for e in self.entries if e["id"] == selected_id), None)
        if not entry:
            await interaction.response.send_message("❌ Không tìm thấy lịch này.", ephemeral=True)
            return

        view = ConfirmView(selected_id, entry["type"], entry["name"])
        await interaction.response.send_message(
            f"⚠️ Bạn có chắc muốn hủy **{entry['name']}** không?",
            view=view,
            ephemeral=True,
        )
        self.view.stop()


class ConfirmView(discord.ui.View):
    def __init__(self, entry_id: str, entry_type: str, name: str):
        super().__init__(timeout=30)
        self.entry_id = entry_id
        self.entry_type = entry_type
        self.name = name

    @discord.ui.button(label="Hủy lịch này", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = dm.load_data()
        success = dm.remove_entry(data, str(interaction.user.id), self.entry_type, self.entry_id)
        if success:
            await interaction.response.send_message(
                f"✅ Đã hủy lịch **{self.name}**.", ephemeral=True
            )
        else:
            await interaction.response.send_message("❌ Không thể hủy lịch này.", ephemeral=True)
        self.stop()

    @discord.ui.button(label="Giữ lại", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Đã giữ lại lịch nhắc nhở.", ephemeral=True)
        self.stop()


class CancelSchedule(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _build_options(self, user: dict):
        entries, options = [], []
        for s in user.get("special_days", []):
            entries.append({"id": s["id"], "type": "special_days", "name": s["name"]})
            options.append(discord.SelectOption(
                label=f"🎉 {s['name']}",
                description=f"{s['day']}/{s['month']} | nhắc lúc {s['remind_time']}",
                value=s["id"],
            ))
        for t in user.get("tasks", []):
            freq = t["frequency_minutes"]
            freq_label = f"{freq // 1440} ngày" if freq % 1440 == 0 else f"{freq // 60} giờ" if freq % 60 == 0 else f"{freq} phút"
            entries.append({"id": t["id"], "type": "tasks", "name": t["name"]})
            options.append(discord.SelectOption(
                label=f"📝 {t['name']}",
                description=f"Mỗi {freq_label}",
                value=t["id"],
            ))
        return entries[:25], options[:25]

    @app_commands.command(name="cancel-schedule", description="Hủy một lịch nhắc nhở")
    async def cancel_schedule(self, interaction: discord.Interaction):
        data = dm.load_data()
        user = dm.get_user(data, str(interaction.user.id))
        entries, options = self._build_options(user)

        if not options:
            await interaction.response.send_message(
                "Bạn chưa có lịch nhắc nhở nào. Dùng `/schedule-special` hoặc `/schedule-task` để tạo mới.",
                ephemeral=True,
            )
            return

        view = discord.ui.View(timeout=60)
        view.add_item(CancelSelect(options, entries))
        await interaction.response.send_message(
            "🗑️ **Chọn lịch muốn hủy:**", view=view, ephemeral=True
        )


    @commands.command(name="cancel-schedule")
    async def cancel_schedule_prefix(self, ctx: commands.Context):
        data = dm.load_data()
        user = dm.get_user(data, str(ctx.author.id))
        entries, options = self._build_options(user)

        if not options:
            await ctx.send("Bạn chưa có lịch nhắc nhở nào.")
            return

        view = discord.ui.View(timeout=60)
        view.add_item(CancelSelect(options, entries))
        await ctx.send("🗑️ **Chọn lịch muốn hủy:**", view=view)


async def setup(bot: commands.Bot):
    await bot.add_cog(CancelSchedule(bot))

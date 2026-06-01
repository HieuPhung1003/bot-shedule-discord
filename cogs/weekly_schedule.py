import discord
from discord import app_commands
from discord.ext import commands

from utils import data_manager as dm
from utils import schedule_image

DAYS = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
DAY_FULL = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "CN"]
DAY_IDX = {d: i for i, d in enumerate(DAYS)}
COL = 9


def _cell(text: str) -> str:
    text = str(text)
    if len(text) > COL:
        text = text[: COL - 1] + "…"
    return text.ljust(COL)


def _urow(cells: list) -> str:
    return "│ " + " │ ".join(_cell(c) for c in cells) + " │"


def _utop() -> str:
    seg = "─" * (COL + 2)
    return "┌" + (seg + "┬") * 6 + seg + "┐"


def _umid() -> str:
    seg = "─" * (COL + 2)
    return "├" + (seg + "┼") * 6 + seg + "┤"


def _ubot() -> str:
    seg = "─" * (COL + 2)
    return "└" + (seg + "┴") * 6 + seg + "┘"


def _fmt_time(from_t: str, to_t: str) -> str:
    if from_t and to_t:
        to_h = to_t.split(":")[0].zfill(2)
        return f"{from_t[:5]}~{to_h}h"
    elif from_t:
        return from_t[:5]
    return ""


def _setup_table(schedule: dict) -> str:
    lines = [_utop(), _urow(DAY_FULL), _umid()]
    for key, label in [("sang", "Sáng"), ("toi", "Tối")]:
        lines.append(_urow([f"[{label}]"] * 7))
        task_cells = []
        for d in DAYS:
            e = schedule[d][key]
            task_cells.append(e["task"] if (e and e.get("task")) else "——")
        lines.append(_urow(task_cells))
        lines.append(_umid() if key == "sang" else _ubot())
    return "\n".join(lines)


def _build_setup_embed(schedule: dict) -> discord.Embed:
    filled = sum(
        1 for d in DAYS for p in ("sang", "toi")
        if schedule[d][p] and schedule[d][p].get("task")
    )
    embed = discord.Embed(
        title="📅 Thiết lập lịch tuần",
        description=f"```\n{_setup_table(schedule)}\n```",
        color=discord.Color.blue(),
    )
    embed.set_footer(text=f"Đã điền: {filled}/14 ô  •  Nhấn nút để nhập lịch  •  ✅ để lưu")
    return embed


class SlotModal(discord.ui.Modal):
    def __init__(self, day: str, period: str, existing: dict | None, view: "WeeklySetupView"):
        period_label = "Sáng" if period == "sang" else "Tối"
        super().__init__(title=f"{DAY_FULL[DAY_IDX[day]]} — {period_label}")
        self._setup_view = view
        self.day = day
        self.period = period

        ex = existing or {}
        self.task_input = discord.ui.TextInput(
            label="Công việc (để trống = xóa ô)",
            placeholder="VD: Học bài, Tập thể dục...",
            default=ex.get("task", ""),
            max_length=40,
            required=False,
        )
        self.from_input = discord.ui.TextInput(
            label="Từ giờ (HH:MM)",
            placeholder="VD: 07:00",
            default=ex.get("from", ""),
            max_length=5,
            required=False,
        )
        self.to_input = discord.ui.TextInput(
            label="Đến giờ (HH:MM)",
            placeholder="VD: 09:00",
            default=ex.get("to", ""),
            max_length=5,
            required=False,
        )
        self.add_item(self.task_input)
        self.add_item(self.from_input)
        self.add_item(self.to_input)

    async def on_submit(self, interaction: discord.Interaction):
        task = self.task_input.value.strip()
        self._setup_view.schedule[self.day][self.period] = (
            {
                "task": task,
                "from": self.from_input.value.strip(),
                "to": self.to_input.value.strip(),
            }
            if task
            else None
        )
        embed = _build_setup_embed(self._setup_view.schedule)
        await interaction.response.edit_message(embed=embed, view=self._setup_view)


class SlotButton(discord.ui.Button):
    def __init__(self, day: str, period: str, row: int):
        label = f"{day} {'Sáng' if period == 'sang' else 'Tối'}"
        style = discord.ButtonStyle.primary if period == "sang" else discord.ButtonStyle.secondary
        super().__init__(label=label, style=style, row=row)
        self.day = day
        self.period = period

    async def callback(self, interaction: discord.Interaction):
        view: WeeklySetupView = self.view
        if interaction.user.id != view.owner_id:
            await interaction.response.send_message("Đây không phải lịch của bạn.", ephemeral=True)
            return
        existing = view.schedule[self.day][self.period]
        modal = SlotModal(self.day, self.period, existing, view)
        await interaction.response.send_modal(modal)


class ConfirmButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="✅ Lưu lịch", style=discord.ButtonStyle.success, row=3)

    async def callback(self, interaction: discord.Interaction):
        view: WeeklySetupView = self.view
        if interaction.user.id != view.owner_id:
            await interaction.response.send_message("Đây không phải lịch của bạn.", ephemeral=True)
            return
        await dm.set_weekly_schedule(str(interaction.user.id), view.schedule)
        for child in view.children:
            child.disabled = True
        embed = _build_setup_embed(view.schedule)
        embed.color = discord.Color.green()
        embed.title = "✅ Đã lưu lịch tuần!"
        embed.set_footer(text="Dùng /xem-lịch-tuần để xem lại bất cứ lúc nào.")
        await interaction.response.edit_message(embed=embed, view=view)
        view.stop()


class WeeklySetupView(discord.ui.View):
    def __init__(self, owner_id: int, schedule: dict):
        super().__init__(timeout=300)
        self.owner_id = owner_id
        self.schedule = schedule

        # Row 0: T2–T6 Sáng (5 buttons)
        for day in DAYS[:5]:
            self.add_item(SlotButton(day, "sang", row=0))
        # Row 1: T7–CN Sáng + T2–T4 Tối (5 buttons)
        for day in DAYS[5:]:
            self.add_item(SlotButton(day, "sang", row=1))
        for day in DAYS[:3]:
            self.add_item(SlotButton(day, "toi", row=1))
        # Row 2: T5–CN Tối (4 buttons)
        for day in DAYS[3:]:
            self.add_item(SlotButton(day, "toi", row=2))
        # Row 3: Confirm
        self.add_item(ConfirmButton())

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True


class WeeklySchedule(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="lịch-tuần", description="Thiết lập lịch hoạt động trong tuần")
    async def setup_weekly(self, interaction: discord.Interaction):
        schedule = await dm.get_weekly_schedule(str(interaction.user.id))
        view = WeeklySetupView(interaction.user.id, schedule)
        embed = _build_setup_embed(schedule)
        await interaction.response.send_message(embed=embed, view=view)

    @commands.command(name="lịch-tuần")
    async def setup_weekly_prefix(self, ctx: commands.Context):
        schedule = await dm.get_weekly_schedule(str(ctx.author.id))
        view = WeeklySetupView(ctx.author.id, schedule)
        embed = _build_setup_embed(schedule)
        await ctx.send(embed=embed, view=view)

    @app_commands.command(name="xem-lịch-tuần", description="Xem lịch hoạt động trong tuần")
    async def view_weekly(self, interaction: discord.Interaction):
        schedule = await dm.get_weekly_schedule(str(interaction.user.id))
        buf = schedule_image.generate(schedule, interaction.user.display_name)
        file = discord.File(fp=buf, filename="weekly_schedule.png")
        await interaction.response.send_message(
            content=f"📅 **Lịch tuần của {interaction.user.display_name}**",
            file=file,
        )

    @commands.command(name="xem-lịch-tuần")
    async def view_weekly_prefix(self, ctx: commands.Context):
        schedule = await dm.get_weekly_schedule(str(ctx.author.id))
        buf = schedule_image.generate(schedule, ctx.author.display_name)
        file = discord.File(fp=buf, filename="weekly_schedule.png")
        await ctx.send(
            content=f"📅 **Lịch tuần của {ctx.author.display_name}**",
            file=file,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(WeeklySchedule(bot))

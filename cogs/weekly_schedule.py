import discord
from discord import app_commands
from discord.ext import commands

from utils import data_manager as dm
from utils import schedule_image

DAYS = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
DAY_FULL = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "CN"]
DAY_IDX = {d: i for i, d in enumerate(DAYS)}


def _count_filled(schedule: dict) -> int:
    return sum(1 for d in DAYS for p in ("sang", "toi") if schedule[d][p])


def _make_setup_embed(filled: int) -> discord.Embed:
    embed = discord.Embed(
        title="📅 Thiết lập lịch tuần",
        description=(
            f"Đã điền: {filled}/14 ô  •  Nhấn nút để chỉnh ô  •  ✅ để lưu\n"
            "*(Mỗi dòng: `Tên việc | HH:MM | HH:MM` — xóa dòng = xóa việc đó)*"
        ),
        color=discord.Color.blue(),
    )
    embed.set_image(url="attachment://weekly_schedule.png")
    return embed


def _to_minutes(t: str) -> int | None:
    """Parse HH:MM → total minutes. Returns None if invalid."""
    try:
        h, m = t.strip().split(":")
        return int(h) * 60 + int(m)
    except (ValueError, AttributeError):
        return None


def _times_overlap(a_from: str, a_to: str, b_from: str, b_to: str) -> bool:
    """True if [a_from, a_to) overlaps [b_from, b_to). Back-to-back is NOT overlap."""
    af, at_ = _to_minutes(a_from), _to_minutes(a_to)
    bf, bt  = _to_minutes(b_from), _to_minutes(b_to)
    if None in (af, at_, bf, bt):
        return False
    return af < bt and at_ > bf


def _slot_to_text(entries: list) -> str:
    """Serialize a slot's task list to multi-line text for the modal default."""
    lines = []
    for e in entries:
        line = e["task"]
        if e.get("from"):
            line += f" | {e['from']}"
            if e.get("to"):
                line += f" | {e['to']}"
        lines.append(line)
    return "\n".join(lines)


def _parse_task_lines(raw: str) -> list[dict]:
    """Parse the modal text into a list of task dicts. Ignores blank lines."""
    entries = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = [p.strip() for p in line.split("|")]
        name = parts[0].strip()
        if not name:
            continue
        from_t = parts[1] if len(parts) > 1 else ""
        to_t   = parts[2] if len(parts) > 2 else ""
        entries.append({"task": name, "from": from_t, "to": to_t})
    return entries


class SlotModal(discord.ui.Modal):
    def __init__(self, day: str, period: str, existing: list, view: "WeeklySetupView"):
        period_label = "Sáng" if period == "sang" else "Tối"
        super().__init__(title=f"{DAY_FULL[DAY_IDX[day]]} — {period_label}")
        self._setup_view = view
        self.day = day
        self.period = period

        self.tasks_input = discord.ui.TextInput(
            label="Việc (mỗi dòng: Tên | HH:MM | HH:MM)",
            style=discord.TextStyle.long,
            placeholder="VD:\nĐấm Thành | 07:00 | 09:00\nĐấm Hà | 09:00 | 11:00",
            default=_slot_to_text(existing),
            max_length=500,
            required=False,
        )
        self.add_item(self.tasks_input)

    async def on_submit(self, interaction: discord.Interaction):
        raw = self.tasks_input.value.strip()

        if not raw:
            self._setup_view.schedule[self.day][self.period] = []
        else:
            entries = _parse_task_lines(raw)

            # Deduplicate names (case-insensitive, keep first occurrence)
            seen: set[str] = set()
            deduped = []
            for e in entries:
                if e["task"].lower() not in seen:
                    seen.add(e["task"].lower())
                    deduped.append(e)

            # Check time overlaps between every pair
            for i in range(len(deduped)):
                for j in range(i + 1, len(deduped)):
                    a, b = deduped[i], deduped[j]
                    if a.get("from") and a.get("to") and b.get("from") and b.get("to"):
                        if _times_overlap(a["from"], a["to"], b["from"], b["to"]):
                            await interaction.response.send_message(
                                f"❌ Giờ trùng nhau: **{a['task']}** ({a['from']}–{a['to']}) "
                                f"và **{b['task']}** ({b['from']}–{b['to']}).",
                                ephemeral=True,
                            )
                            return

            deduped.sort(key=lambda e: _to_minutes(e.get("from") or "") or 9999)
            self._setup_view.schedule[self.day][self.period] = deduped

        filled = _count_filled(self._setup_view.schedule)
        buf = schedule_image.generate(self._setup_view.schedule, interaction.user.display_name)
        file = discord.File(fp=buf, filename="weekly_schedule.png")
        await interaction.response.edit_message(
            embed=_make_setup_embed(filled),
            attachments=[file],
            view=self._setup_view,
        )


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
        buf = schedule_image.generate(view.schedule, interaction.user.display_name)
        file = discord.File(fp=buf, filename="weekly_schedule.png")
        embed = discord.Embed(title="✅ Đã lưu lịch tuần!", color=discord.Color.green())
        embed.set_image(url="attachment://weekly_schedule.png")
        await interaction.response.edit_message(embed=embed, attachments=[file], view=view)
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
        filled = _count_filled(schedule)
        buf = schedule_image.generate(schedule, interaction.user.display_name)
        file = discord.File(fp=buf, filename="weekly_schedule.png")
        await interaction.response.send_message(embed=_make_setup_embed(filled), file=file, view=view)

    @commands.command(name="lịch-tuần")
    async def setup_weekly_prefix(self, ctx: commands.Context):
        schedule = await dm.get_weekly_schedule(str(ctx.author.id))
        view = WeeklySetupView(ctx.author.id, schedule)
        filled = _count_filled(schedule)
        buf = schedule_image.generate(schedule, ctx.author.display_name)
        file = discord.File(fp=buf, filename="weekly_schedule.png")
        await ctx.send(embed=_make_setup_embed(filled), file=file, view=view)

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

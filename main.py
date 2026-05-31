import asyncio
import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

COGS = [
    "cogs.help_cmd",
    "cogs.special_day",
    "cogs.daily_task",
    "cogs.view_schedules",
    "cogs.cancel_schedule",
    "cogs.reminder_loop",
]


def get_prefix(bot, message):
    # "kurumi " prefix, không phân biệt hoa thường
    if message.content[:7].lower() == "kurumi ":
        return message.content[:7]
    return commands.when_mentioned(bot, message)


class ScheduleBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(
            command_prefix=get_prefix,
            intents=intents,
            help_command=None,
            case_insensitive=True,
        )

    async def setup_hook(self):
        for cog in COGS:
            await self.load_extension(cog)
        await self.tree.sync()
        print("Slash commands synced.")

    async def on_ready(self):
        print(f"Logged in as {self.user} (ID: {self.user.id})")


async def main():
    bot = ScheduleBot()
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN not set in .env")
    async with bot:
        await bot.start(token)


asyncio.run(main())

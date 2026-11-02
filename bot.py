
import os
import re
import sqlite3
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
DB_PATH = os.getenv("DATABASE_PATH", "timezones.sqlite3")

# Matches 8pm, 8:30 PM, 20:30, or 8:30.
TIME_RE = re.compile(
    r"(?<![\w:])"
    r"(?P<hour>0?[1-9]|1[0-2]|2[0-3])"
    r"(?::(?P<minute>[0-5]\d))?"
    r"\s*(?P<ampm>a\.?m\.?|p\.?m\.?)?"
    r"(?!\w)",
    re.IGNORECASE,
)
DATE_PREFIX_RE = re.compile(r"\b(today|tomorrow)\b", re.IGNORECASE)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)


def init_db():
    with sqlite3.connect(DB_PATH) as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS user_timezones (
                user_id INTEGER PRIMARY KEY,
                timezone TEXT NOT NULL
            )
        """)


def get_timezone(user_id: int):
    with sqlite3.connect(DB_PATH) as db:
        row = db.execute(
            "SELECT timezone FROM user_timezones WHERE user_id = ?",
            (user_id,),
        ).fetchone()
    return row[0] if row else None


def save_timezone(user_id: int, tz_name: str):
    with sqlite3.connect(DB_PATH) as db:
        db.execute(
            """INSERT INTO user_timezones(user_id, timezone) VALUES(?, ?)
               ON CONFLICT(user_id) DO UPDATE SET timezone=excluded.timezone""",
            (user_id, tz_name),
        )


def parse_time(match: re.Match, message_text: str, tz: ZoneInfo):
    hour = int(match.group("hour"))
    minute = int(match.group("minute") or 0)
    ampm = (match.group("ampm") or "").lower().replace(".", "")

    if ampm:
        if not 1 <= hour <= 12:
            return None
        hour = hour % 12
        if ampm == "pm":
            hour += 12
    # Without AM/PM, interpret the value as 24-hour time.
    # Thus "8:30" means 08:30 and "20:30" means 20:30.

    # Use a nearby "tomorrow" or "today" immediately before the time.
    prefix = message_text[max(0, match.start() - 20):match.start()]
    date_match = list(DATE_PREFIX_RE.finditer(prefix))
    day_word = date_match[-1].group(1).lower() if date_match else "today"

    now_local = datetime.now(tz)
    target_date = now_local.date()
    if day_word == "tomorrow":
        target_date += timedelta(days=1)

    local_dt = datetime(
        target_date.year, target_date.month, target_date.day,
        hour, minute, tzinfo=tz
    )

    # Reject nonexistent local times during a daylight-saving clock jump.
    round_trip = local_dt.astimezone(timezone.utc).astimezone(tz)
    if round_trip.replace(tzinfo=None) != local_dt.replace(tzinfo=None):
        return None

    return int(local_dt.timestamp())


def convert_message(content: str, tz: ZoneInfo):
    matches = list(TIME_RE.finditer(content))
    if not matches:
        return None

    converted = content
    found = False
    for match in reversed(matches):
        unix_time = parse_time(match, content, tz)
        if unix_time is None:
            continue
        stamp = f"<t:{unix_time}:t>"
        converted = converted[:match.start()] + stamp + converted[match.end():]
        found = True

    return converted if found and converted != content else None


@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash command(s).")
    except Exception as exc:
        print(f"Slash-command sync failed: {exc}")
    print(f"Logged in as {bot.user}.")


@bot.tree.command(name="timezone", description="Set your timezone for automatic time conversion.")
@app_commands.describe(timezone_name="An IANA timezone, e.g. Europe/Amsterdam or America/New_York")
async def timezone_command(interaction: discord.Interaction, timezone_name: str):
    try:
        ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        await interaction.response.send_message(
            "I don't recognize that timezone. Use an IANA name such as "
            "`Europe/Amsterdam`, `America/New_York`, or `Asia/Tokyo`.",
            ephemeral=True,
        )
        return

    save_timezone(interaction.user.id, timezone_name)
    await interaction.response.send_message(
        f"Your timezone is now set to `{timezone_name}`.",
        ephemeral=True,
    )


@bot.tree.command(name="mytimezone", description="Show your saved timezone.")
async def mytimezone_command(interaction: discord.Interaction):
    tz_name = get_timezone(interaction.user.id)
    if tz_name:
        response = f"Your saved timezone is `{tz_name}`."
    else:
        response = "You haven't set a timezone yet. Use `/timezone Europe/Amsterdam`."
    await interaction.response.send_message(response, ephemeral=True)


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or not message.guild or not message.content:
        return

    tz_name = get_timezone(message.author.id)
    if not tz_name:
        return

    try:
        tz = ZoneInfo(tz_name)
    except ZoneInfoNotFoundError:
        return

    converted = convert_message(message.content, tz)
    if converted:
        await message.reply(converted, mention_author=False, allowed_mentions=discord.AllowedMentions.none())

    await bot.process_commands(message)


if __name__ == "__main__":
    if not TOKEN:
        raise RuntimeError("Set DISCORD_TOKEN in your .env file.")
    init_db()
    bot.run(TOKEN)

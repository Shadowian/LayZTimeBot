# Discord Automatic Time Converter

This bot watches server messages and replies with a version where recognizable times
are converted into Discord timestamps, such as `<t:1793648183:t>`. Discord renders
those timestamps in each viewer's own local timezone.

## What it does

- `/timezone Europe/Amsterdam` saves your IANA timezone.
- `/mytimezone` shows your saved timezone.
- Converts examples such as `8pm`, `8:30 PM`, `20:30`, and `08:15`.
- `tomorrow at 8pm` uses tomorrow in the sender's saved timezone.
- Uses `:t` (short time) formatting.
- Saves timezone preferences in a local SQLite database.

Without AM/PM, times are interpreted as 24-hour time: `8:30` means 08:30.
For clarity, write `8:30 PM` when you mean evening.

The bot replies with a converted copy. Discord bots cannot edit another user's
original message. This version does not delete messages.

## 1. Create the Discord application

1. Open https://discord.com/developers/applications
2. Create an application, then open its **Bot** page and add a bot.
3. Under **Bot > Privileged Gateway Intents**, enable **Message Content Intent**.
4. Copy the bot token. Keep it private; never post it in a server or share it.

## 2. Invite it

In **OAuth2 > URL Generator**:
- Scopes: `bot` and `applications.commands`
- Bot permissions: `View Channels`, `Send Messages`, `Read Message History`

Open the generated URL and add the bot to your server.

## 3. Install and run

Python 3.10 or newer is recommended.

```bash
python -m venv .venv
```

Activate the environment, then:

```bash
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and put your token in it:

```env
DISCORD_TOKEN=put_your_bot_token_here
```

Start the bot:

```bash
python bot.py
```

Keep the process running (for example, on a computer or hosting service) for the
bot to stay online. Keep `.env` and `timezones.sqlite3` private.

## Notes / limitations

- Each user sets their own timezone once with `/timezone`.
- The bot uses the date in the sender's timezone; a time with no date means today.
- This starter version handles clock times and the words `today` / `tomorrow`.
  It does not infer dates like "next Friday" or parse every natural-language phrase.
- If a local time does not exist because clocks jump forward for daylight saving,
  the bot skips that conversion.
- Discord timestamps are Unix seconds. The `:t` style displays a short localized time.
# LayZTimeBot
# LayZTimeBot

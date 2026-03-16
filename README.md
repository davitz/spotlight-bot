# Daggerheart Spotlight Bot 🎭

A Discord bot that randomly assigns the **spotlight** to a player in
[Daggerheart](https://darringtonpress.com/daggerheart/) sessions.

## How It Works

1. A user runs `/start_spotlight` in a Discord channel.
2. The bot posts an embed asking **"Who wants the spotlight?"**
3. Players react to the message (any emoji works).
4. After the first reaction, the bot waits until a configurable number of
   seconds pass without any new reactions.
5. Once the timer elapses, the bot randomly picks one of the reacting users and
   announces **"[user] has the spotlight!"**
6. The bot waits for someone to react to that assignment message as an
   acknowledgement.
7. Once someone reacts, the bot automatically starts a new round.
8. The loop continues until someone runs `/stop_spotlight`.

## Setup

### 1. Create a Discord Bot

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications).
2. Create a new application and add a **Bot**.
3. Copy the bot token.

### 2. Invite the Bot

Generate an invite link under *OAuth2 → URL Generator*:
- **Scopes:** `bot`, `applications.commands`
- **Bot Permissions:** `Send Messages`, `Add Reactions`, `Read Message History`

### 3. Configure

Copy the example environment file and fill in your token:

```bash
cp .env.example .env
# edit .env and set DISCORD_TOKEN
```

| Variable | Default | Description |
|---|---|---|
| `DISCORD_TOKEN` | *(required)* | Your Discord bot token |
| `REACTION_WAIT_SECONDS` | `30` | Default seconds to wait after the most recent new reaction before choosing |

### 4. Run

#### With Docker

```bash
docker build -t spotlight-bot .
docker run --env-file .env spotlight-bot
```

#### Locally (Python 3.12+)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python bot.py
```

## Usage

| Command | Description |
|---|---|
| `/start_spotlight` | Start a spotlight loop with default settings |
| `/start_spotlight wait_seconds:15` | Override the reaction wait time |
| `/set_interval seconds:15` | Change the judgment interval for this channel |
| `/stop_spotlight` | Stop the spotlight loop in this channel |

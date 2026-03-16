import os
import random
import asyncio

import discord
from discord import app_commands
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
REACTION_WAIT_SECONDS = int(os.getenv("REACTION_WAIT_SECONDS", "30"))

# Tracks active spotlight loops per channel: channel_id -> asyncio.Task
_active_loops: dict[int, asyncio.Task] = {}
# Tracks per-channel judgment windows: channel_id -> seconds
_channel_wait_seconds: dict[int, int] = {}

intents = discord.Intents.default()
intents.reactions = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


@tree.command(name="start_spotlight", description="Start a spotlight loop for Daggerheart!")
@app_commands.describe(
    wait_seconds="Seconds to wait for reactions each round (overrides default)",
)
async def start_spotlight(
    interaction: discord.Interaction,
    wait_seconds: app_commands.Range[int, 1, 3600] | None = None,
):
    channel = interaction.channel

    if channel.id in _active_loops:
        await interaction.response.send_message(
            "⚠️ A spotlight loop is already running in this channel. "
            "Use `/stop_spotlight` to stop it first.",
            ephemeral=True,
        )
        return

    if wait_seconds is not None:
        _channel_wait_seconds[channel.id] = wait_seconds

    wait = _channel_wait_seconds.get(channel.id, REACTION_WAIT_SECONDS)

    await interaction.response.send_message(
        f"🎭 **Spotlight loop started!** The next round will begin after someone "
        f"reacts to the spotlight assignment. Reaction window: **{wait}s**. "
        "Use `/stop_spotlight` to end.",
    )

    task = asyncio.create_task(_spotlight_loop(channel))
    _active_loops[channel.id] = task


@tree.command(name="set_interval", description="Set the reaction wait interval for this channel.")
@app_commands.describe(
    seconds="Seconds to wait after the most recent new reaction before judging",
)
async def set_interval(
    interaction: discord.Interaction,
    seconds: app_commands.Range[int, 1, 3600],
):
    channel = interaction.channel
    _channel_wait_seconds[channel.id] = seconds

    await interaction.response.send_message(
        f"⏱️ The spotlight judgment interval for this channel is now **{seconds}s**."
    )


@tree.command(name="stop_spotlight", description="Stop the spotlight loop in this channel.")
async def stop_spotlight(interaction: discord.Interaction):
    channel = interaction.channel
    task = _active_loops.pop(channel.id, None)

    if task is None:
        await interaction.response.send_message(
            "⚠️ No spotlight loop is running in this channel.",
            ephemeral=True,
        )
        return

    task.cancel()
    await interaction.response.send_message("🛑 Spotlight loop stopped!")


async def _spotlight_loop(
    channel: discord.abc.Messageable,
) -> None:
    """Run spotlight rounds in a loop until cancelled."""
    try:
        while True:
            wait = _channel_wait_seconds.get(channel.id, REACTION_WAIT_SECONDS)
            await _run_spotlight_round(channel, wait)
    except asyncio.CancelledError:
        pass
    finally:
        _active_loops.pop(getattr(channel, "id", None), None)


async def _run_spotlight_round(
    channel: discord.abc.Messageable,
    wait: int,
) -> None:
    """Run a single spotlight round: post, collect reactions, pick a winner."""
    embed = discord.Embed(
        title="🎭 Spotlight!",
        description=(
            "**Who wants the spotlight?**\n\n"
            f"React to this message. Once **{wait} seconds** pass without any new reactions, "
            "the spotlight will be assigned."
        ),
        color=discord.Color.gold(),
    )
    embed.set_footer(text="Daggerheart Spotlight Bot")

    message = await channel.send(embed=embed)
    await message.add_reaction("🌟")

    # Wait for the first reaction from a non-bot user, then start the timer
    def check_first_reaction(reaction: discord.Reaction, user: discord.User) -> bool:
        return reaction.message.id == message.id and not user.bot

    try:
        await client.wait_for("reaction_add", check=check_first_reaction, timeout=300)
    except asyncio.TimeoutError:
        timeout_embed = discord.Embed(
            title="🎭 Spotlight — Timed Out",
            description="Nobody reacted in time. Trying again next round…",
            color=discord.Color.greyple(),
        )
        await message.edit(embed=timeout_embed)
        return

    # Keep extending the window until no new reactions arrive for the full idle period.
    while True:
        try:
            await client.wait_for("reaction_add", check=check_first_reaction, timeout=wait)
        except asyncio.TimeoutError:
            break

    # Re-fetch the message to get up-to-date reactions
    message = await channel.fetch_message(message.id)

    # Collect all unique non-bot users who reacted (any emoji counts)
    candidates: set[discord.Member | discord.User] = set()
    for reaction in message.reactions:
        async for user in reaction.users():
            if not user.bot:
                candidates.add(user)

    if not candidates:
        no_one_embed = discord.Embed(
            title="🎭 Spotlight — No Candidates",
            description="All reactions were removed! Trying again next round…",
            color=discord.Color.greyple(),
        )
        await message.edit(embed=no_one_embed)
        return

    chosen = random.choice(list(candidates))

    result_embed = discord.Embed(
        title="🎭 Spotlight!",
        description=(
            f"**{chosen.mention} has the spotlight!**\n\n"
            "React to this message to acknowledge and start the next round."
        ),
        color=discord.Color.green(),
    )
    result_embed.set_footer(text="Daggerheart Spotlight Bot")

    await message.edit(embed=result_embed)
    await message.add_reaction("✅")

    def check_acknowledgement(reaction: discord.Reaction, user: discord.User) -> bool:
        return reaction.message.id == message.id and not user.bot

    await client.wait_for("reaction_add", check=check_acknowledgement)


@client.event
async def on_ready():
    await tree.sync()
    print(f"Logged in as {client.user} (ID: {client.user.id})")
    print(f"Default reaction wait time: {REACTION_WAIT_SECONDS}s")
    print("------")


def main():
    if not TOKEN:
        raise RuntimeError(
            "DISCORD_TOKEN is not set. "
            "Create a .env file or set the environment variable."
        )
    client.run(TOKEN)


if __name__ == "__main__":
    main()

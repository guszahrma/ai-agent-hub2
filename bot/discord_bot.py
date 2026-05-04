import os
import sys
from pathlib import Path

import discord
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
from agents.scrum_master import ScrumMaster

load_dotenv()

CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID", 0))

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)
scrum_master = ScrumMaster()


@client.event
async def on_ready():
    print(f"Logged in as {client.user} | Listening on channel {CHANNEL_ID}")


async def send(channel, text: str):
    for i in range(0, len(text), 2000):
        await channel.send(text[i : i + 2000])


@client.event
async def on_message(message):
    if message.author == client.user:
        return
    if message.channel.id != CHANNEL_ID:
        return

    content = message.content.strip()

    if content.startswith("!repo"):
        parts = content.split(maxsplit=1)
        if len(parts) < 2:
            await message.channel.send("Usage: `!repo <path>`")
            return
        await message.channel.send(scrum_master.set_repo(parts[1]))
        return

    async with message.channel.typing():
        response = scrum_master.handle_message(content, message.author.display_name)

    await send(message.channel, response)


if __name__ == "__main__":
    client.run(os.getenv("DISCORD_TOKEN"))

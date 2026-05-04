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


@client.event
async def on_message(message):
    if message.author == client.user:
        return
    if message.channel.id != CHANNEL_ID:
        return

    async with message.channel.typing():
        response = scrum_master.handle_message(
            message.content,
            message.author.display_name,
        )

    # Discord has a 2000-char message limit
    if len(response) <= 2000:
        await message.channel.send(response)
    else:
        for i in range(0, len(response), 2000):
            await message.channel.send(response[i : i + 2000])


if __name__ == "__main__":
    client.run(os.getenv("DISCORD_TOKEN"))

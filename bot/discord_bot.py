import os
import sys
from pathlib import Path

import discord
import yaml
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
from agents.scrum_master import ScrumMaster

load_dotenv()

GIT_BASE_DIR = os.getenv("GIT_BASE_DIR", str(Path.home() / "git"))

CONFIG_PATH = Path(__file__).parent.parent / "config" / "repos.yaml"


def load_repos() -> dict:
    with open(CONFIG_PATH) as f:
        data = yaml.safe_load(f)
    repos = {}
    for channel_id, info in data.get("repos", {}).items():
        ref = info["ref"]
        project_name = ref.split("/")[1]
        repo_path = Path(GIT_BASE_DIR) / project_name
        repos[int(channel_id)] = {
            "ref": ref,
            "name": info.get("name", project_name),
            "path": str(repo_path) if (repo_path / ".git").exists() else None,
        }
    return repos


intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)
scrum_master = ScrumMaster()
repos = load_repos()


@client.event
async def on_ready():
    print(f"Logged in as {client.user}")
    for channel_id, info in repos.items():
        status = info["path"] or "REPO NOT FOUND LOCALLY"
        print(f"  Channel {channel_id} → {info['ref']} ({status})")


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    repo = repos.get(message.channel.id)
    if repo is None:
        return

    async with message.channel.typing():
        response = scrum_master.handle_message(
            message.content,
            message.author.display_name,
            repo_ref=repo["ref"],
            repo_path=repo["path"],
        )

    for i in range(0, len(response), 2000):
        await message.channel.send(response[i : i + 2000])


if __name__ == "__main__":
    client.run(os.getenv("DISCORD_TOKEN"))

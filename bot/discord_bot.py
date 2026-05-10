import asyncio
import os
import subprocess
import sys
import signal
from pathlib import Path

import discord
import yaml
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
from agent_directory.scrum_master import ScrumMaster
from bot.pr_monitor import PRMonitor

load_dotenv()

PID_FILE = Path(__file__).parent / "bot.pid"


def check_pid_file():
    if PID_FILE.exists():
        old_pid = int(PID_FILE.read_text().strip())
        try:
            os.kill(old_pid, signal.SIGTERM)
            print(f"Stopped previous instance (PID {old_pid})")
        except ProcessLookupError:
            pass
    PID_FILE.write_text(str(os.getpid()))


def cleanup_pid():
    if PID_FILE.exists():
        PID_FILE.unlink()

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


GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
PR_POLL_INTERVAL = int(os.getenv("PR_POLL_INTERVAL", "60"))

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)
scrum_master = ScrumMaster()
repos = load_repos()
pr_monitor = PRMonitor(GITHUB_TOKEN) if GITHUB_TOKEN else None


def handle_merged_pr(pr: dict, repo_ref: str, repo_path: str | None):
    branch = pr.get("head", {}).get("ref", "")
    print(f"PR #{pr['number']} merged ({pr['title']!r}) — branch: {branch!r}")

    if branch and branch not in ("main", "master") and repo_path:
        result = subprocess.run(
            ["git", "push", "origin", "--delete", branch],
            cwd=repo_path, capture_output=True, text=True,
        )
        if result.returncode == 0:
            print(f"  Deleted remote branch {branch!r}")
        else:
            print(f"  Remote branch delete: {result.stderr.strip()}")

        result = subprocess.run(
            ["git", "branch", "-d", branch],
            cwd=repo_path, capture_output=True, text=True,
        )
        if result.returncode == 0:
            print(f"  Deleted local branch {branch!r}")
        else:
            print(f"  Local branch delete: {result.stderr.strip()}")

    if pr_monitor:
        closed = pr_monitor.close_linked_issues(repo_ref, pr)
        if closed:
            print(f"  Closed linked issues: {closed}")


async def poll_pr_comments():
    await client.wait_until_ready()
    if not pr_monitor:
        print("PR polling disabled: GITHUB_TOKEN not set")
        return

    ref_to_channel: dict[str, tuple[int, dict]] = {}
    for channel_id, info in repos.items():
        ref_to_channel[info["ref"]] = (channel_id, info)

    print(f"PR polling active — checking every {PR_POLL_INTERVAL}s for: {list(ref_to_channel)}")

    poll_count = 0
    while not client.is_closed():
        poll_count += 1
        print(f"Poll #{poll_count}")
        for repo_ref, (channel_id, info) in ref_to_channel.items():
            try:
                new_comments, merged_prs = pr_monitor.poll(repo_ref)
            except Exception as e:
                print(f"PR poll error ({repo_ref}): {e}")
                continue

            for pr in merged_prs:
                try:
                    handle_merged_pr(pr, repo_ref, info.get("path"))
                except Exception as e:
                    print(f"  → merge handling failed: {e}")

            for comment in new_comments:
                kind = "inline" if comment.comment_type == "review" else "general"
                print(f"New {kind} PR comment on #{comment.pr_number} by @{comment.author}: {comment.url}")
                try:
                    thread_history = pr_monitor.get_thread_history(repo_ref, comment)
                    response = scrum_master.handle_pr_comment(
                        comment,
                        repo_ref=repo_ref,
                        repo_path=info.get("path"),
                        thread_history=thread_history,
                    )
                    if response.to_po:
                        pr_monitor.reply(repo_ref, comment, response.to_po)
                        print(f"  → replied to PO")
                    for agent_msg in response.to_agents:
                        body = f"**[ScrumMaster] → [{agent_msg['recipient']}]:** {agent_msg['message']}"
                        pr_monitor.reply(repo_ref, comment, body)
                        print(f"  → delegated to {agent_msg['recipient']}")
                except Exception as e:
                    print(f"  → failed to reply: {e}")

        await asyncio.sleep(PR_POLL_INTERVAL)


@client.event
async def on_ready():
    print(f"Logged in as {client.user}")
    for channel_id, info in repos.items():
        status = info["path"] or "REPO NOT FOUND LOCALLY"
        print(f"  Channel {channel_id} → {info['ref']} ({status})")
    asyncio.ensure_future(poll_pr_comments())


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
    check_pid_file()
    try:
        client.run(os.getenv("DISCORD_TOKEN"))
    finally:
        cleanup_pid()

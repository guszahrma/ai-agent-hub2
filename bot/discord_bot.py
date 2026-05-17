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
from bot.state_store import StateStore

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
state_store = StateStore()
pr_monitor = PRMonitor(GITHUB_TOKEN, state_store) if GITHUB_TOKEN else None


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


async def check_unresolved_on_startup():
    """On startup, check state store for unresolved comments and ask ScrumMaster for progress."""
    if not pr_monitor:
        return

    unresolved = state_store.get_unresolved()
    if not unresolved:
        print("Startup check: no unresolved comments")
        return

    print(f"Startup check: {len(unresolved)} unresolved comment(s)")

    for item in unresolved:
        repo_ref = item["repo_ref"]
        pr_number = item["pr_number"]
        comment = item["comment"]
        comment_id = int(comment["id"])
        comment_status = comment.get("status")

        print(f"  PR #{pr_number} comment {comment_id} — status: {comment_status}")

        if comment_status == "delegated_to_scrum_master":
            # Bot stopped before ScrumMaster could respond — reset so next poll reprocesses it
            state_store.set_comment_status(repo_ref, pr_number, comment_id, "new")
            print(f"    Reset to 'new' — will be reprocessed on next poll")
            continue

        if comment_status == "pending":
            pr_title = pr_monitor.get_pr_title(repo_ref, pr_number)
            thread_root_id = int(item["thread_id"])

            try:
                thread_history = pr_monitor.get_thread_history_by_root(
                    repo_ref, pr_number, thread_root_id
                )
            except Exception as e:
                print(f"    Failed to fetch thread history: {e}")
                continue

            for d in comment.get("delegations", []):
                if d["status"] in ("resolved", "superseded"):
                    continue
                try:
                    result = scrum_master.check_pending_delegation(
                        pr_number=pr_number,
                        pr_title=pr_title,
                        repo_ref=repo_ref,
                        thread_history=thread_history,
                        delegation=d,
                    )
                    new_status = result.get("status", "pending")
                    notes = result.get("notes", "")
                    print(f"    Delegation {d['id']} ({d['agent']}): {new_status} — {notes}")
                    if new_status in ("resolved", "in_progress"):
                        state_store.set_delegation_status(
                            repo_ref, pr_number, d["id"], new_status
                        )
                except Exception as e:
                    print(f"    Failed to check delegation {d['id']}: {e}")


async def poll_pr_comments():
    await client.wait_until_ready()
    if not pr_monitor:
        print("PR polling disabled: GITHUB_TOKEN not set")
        return

    await check_unresolved_on_startup()

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
                    state_store.set_comment_status(
                        repo_ref, comment.pr_number, comment.comment_id,
                        "delegated_to_scrum_master"
                    )
                    thread_history = pr_monitor.get_thread_history(repo_ref, comment)
                    response = scrum_master.handle_pr_comment(
                        comment,
                        repo_ref=repo_ref,
                        repo_path=info.get("path"),
                        thread_history=thread_history,
                    )

                    if response.to_agents:
                        # Comment stays pending until delegations resolve
                        state_store.set_comment_status(
                            repo_ref, comment.pr_number, comment.comment_id, "pending"
                        )
                        if response.to_po:
                            reply_id = pr_monitor.reply(repo_ref, comment, response.to_po)
                            print(f"  → replied to PO")
                        for agent_msg in response.to_agents:
                            body = f"**[ScrumMaster] → [{agent_msg['recipient']}]:** {agent_msg['message']}"
                            pr_monitor.reply(repo_ref, comment, body)
                            state_store.add_delegation(
                                repo_ref, comment.pr_number, comment.comment_id,
                                agent=agent_msg["recipient"],
                                task=agent_msg["message"][:200],
                            )
                            print(f"  → delegated to {agent_msg['recipient']}")
                    elif response.to_po:
                        reply_id = pr_monitor.reply(repo_ref, comment, response.to_po,
                                                    is_question=response.question)
                        new_status = "pending" if response.question else "resolved"
                        state_store.set_comment_status(
                            repo_ref, comment.pr_number, comment.comment_id,
                            new_status, resolved_by=reply_id
                        )
                        print(f"  → replied to PO ({new_status})")

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
        await message.channel.send(response[i: i + 2000])


if __name__ == "__main__":
    check_pid_file()
    try:
        client.run(os.getenv("DISCORD_TOKEN"))
    finally:
        cleanup_pid()

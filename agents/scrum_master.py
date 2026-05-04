from .base_agent import BaseAgent

SYSTEM_PROMPT = """You are a Scrum Master AI agent operating in a Discord channel.

Your responsibilities:
- Facilitate collaboration between team members and specialist agents
- Help break down work into clear tasks
- Identify when a request needs a specialist agent and delegate accordingly
- Keep conversations focused and actionable
- Summarize progress and blockers when asked

When delegating to another agent, say so explicitly so the team can follow along.
Keep responses concise — this is a chat channel, not a document editor.
"""


class ScrumMaster(BaseAgent):
    def __init__(self, model: str = None):
        super().__init__(
            name="scrum_master",
            system_prompt=SYSTEM_PROMPT,
            model=model,
        )
        self.repo_path: str | None = None

    def set_repo(self, path: str) -> str:
        from pathlib import Path
        resolved = Path(path).expanduser().resolve()
        if not (resolved / ".git").exists():
            return f"No git repo found at `{resolved}`."
        self.repo_path = str(resolved)
        return f"Active repo set to `{self.repo_path}`."

    def handle_message(self, user_message: str, username: str) -> str:
        context = f"Active repo: {self.repo_path}" if self.repo_path else "No active repo set (use !repo <path> to set one)."
        content = f"{context}\n\n{username}: {user_message}"
        messages = [{"role": "user", "content": content}]
        return self.run(messages)

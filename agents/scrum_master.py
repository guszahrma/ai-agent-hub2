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

    def handle_message(self, user_message: str, username: str, repo_ref: str = None, repo_path: str = None) -> str:
        if repo_ref and repo_path:
            context = f"Active repo: {repo_ref} (local path: {repo_path})"
        else:
            context = "No repo configured for this channel."
        content = f"{context}\n\n{username}: {user_message}"
        messages = [{"role": "user", "content": content}]
        return self.run(messages)

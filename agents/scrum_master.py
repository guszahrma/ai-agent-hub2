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

    def handle_message(self, user_message: str, username: str) -> str:
        messages = [{"role": "user", "content": f"{username}: {user_message}"}]
        return self.run(messages)

from .base_agent import BaseAgent
from .git_agent import GitAgent

SYSTEM_PROMPT = """You are a Scrum Master AI agent operating in a Discord channel.

Your responsibilities:
- Facilitate collaboration between team members and specialist agents
- Help break down work into clear tasks
- Identify when a request needs a specialist agent and delegate accordingly
- Keep conversations focused and actionable
- Summarize progress and blockers when asked

You have access to a GitAgent specialist. Use the delegate_to_git_agent tool when the request involves:
- Git status, diff, log, or branch information
- Committing, pushing, pulling, or branching
- Any question about the repo's current state

When delegating, say so explicitly so the team can follow along.
Keep responses concise — this is a chat channel, not a document editor.
"""

GIT_TOOL = {
    "name": "delegate_to_git_agent",
    "description": "Delegate a git-related request to the GitAgent specialist.",
    "input_schema": {
        "type": "object",
        "properties": {
            "request": {
                "type": "string",
                "description": "The git request to pass to GitAgent, in plain English.",
            }
        },
        "required": ["request"],
    },
}


class ScrumMaster(BaseAgent):
    def __init__(self, model: str = None):
        super().__init__(
            name="scrum_master",
            system_prompt=SYSTEM_PROMPT,
            model=model,
        )
        self._git_agent = GitAgent()

    def handle_message(self, user_message: str, username: str, repo_ref: str = None, repo_path: str = None) -> str:
        if repo_ref and repo_path:
            context = f"Active repo: {repo_ref} (local path: {repo_path})"
        else:
            context = "No repo configured for this channel."
            repo_path = None

        messages = [{"role": "user", "content": f"{context}\n\n{username}: {user_message}"}]

        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=self.system_prompt,
            tools=[GIT_TOOL],
            messages=messages,
        )

        if response.stop_reason == "tool_use":
            tool_use = next(b for b in response.content if b.type == "tool_use")
            request = tool_use.input["request"]

            if repo_path:
                git_result = self._git_agent.handle(request, repo_path)
            else:
                git_result = "No repo configured for this channel — cannot run git operations."

            messages += [
                {"role": "assistant", "content": response.content},
                {"role": "user", "content": [{"type": "tool_result", "tool_use_id": tool_use.id, "content": git_result}]},
            ]

            followup = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=self.system_prompt,
                tools=[GIT_TOOL],
                messages=messages,
            )
            return f"*(delegated to GitAgent)*\n{followup.content[0].text}"

        return response.content[0].text

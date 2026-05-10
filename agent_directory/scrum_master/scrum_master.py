import json
import os
from dataclasses import dataclass, field
from agent_directory.base_agent import BaseAgent
from agent_directory.git_agent import GitAgent

PO_HANDLE = os.getenv("PO_GITHUB_HANDLE", "guszahrma")

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


PR_COMMENT_SYSTEM = f"""You are a Scrum Master AI agent responding to a GitHub PR comment.

Your response MUST be a raw JSON object — no markdown, no code fences, no surrounding text:
{{"to_po": "...", "to_agents": [...]}}

Rules:
- "to_po": start with **[ScrumMaster] → @{PO_HANDLE}:** — give the complete, final answer. If you called GitAgent, include its actual output (branch name, commits, etc.) in full. Never say "I will get" or "let me fetch" — by the time you write to_po, all tool calls are done and you have all the data you need.
- "to_agents": list of {{"recipient": "AgentName", "message": "..."}} — only use this to notify Jeeves of a task that requires code changes or manual implementation. Do NOT claim Jeeves is "working on it" or "active" — Jeeves is a human-triggered assistant and will only act when a human opens Claude Code.
- GitAgent is available as a tool — call it for local git operations (status, diff, log, branches). GitAgent has NO access to the GitHub API or GitHub settings. Do not ask GitAgent about branch protection, PR status, or anything requiring the GitHub API.
- If a question requires GitHub API knowledge (branch protection, PR checks, project settings), answer from thread history and your own knowledge — do not fabricate a verification step.
- Per workprocess: question before acting. If the comment is ambiguous, ask. Do not make changes autonomously.
- A PR comment has three valid outcomes — choose the right one:
  1. Fix in current PR: only if directly in scope and small. Delegate to Jeeves via to_agents.
  2. New issue: if the comment is valid but out of scope or larger than a quick fix. Create a GitHub issue and reply "Tracked as #N" in to_po.
  3. Decline: if invalid or a deliberate tradeoff. Explain why in to_po.
- Do not resolve threads. Do not mix PO and agent content.
- Output only the JSON object. No markdown formatting around it.
"""


@dataclass
class PRResponse:
    to_po: str
    to_agents: list[dict] = field(default_factory=list)


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

    def handle_pr_comment(self, comment, repo_ref: str, repo_path: str = None, thread_history: list = None) -> PRResponse:
        """React to a new GitHub PR comment. Returns a structured PRResponse."""
        diff_context = ""
        if comment.diff_hunk:
            diff_context = f"\nCode context (diff hunk):\n```\n{comment.diff_hunk}\n```"

        history_text = ""
        if thread_history:
            lines = "\n".join(f"[@{c['author']}]: {c['body']}" for c in thread_history)
            history_text = f"\nThread history (oldest first):\n{lines}\n"

        user_message = (
            f"PR #{comment.pr_number} '{comment.pr_title}' in {repo_ref}."
            f"{diff_context}"
            f"{history_text}\n"
            f"Latest comment by @{comment.author} (respond to this):\n{comment.body}\n\n"
            f"Commit link format: [sha](https://github.com/{repo_ref}/pull/{comment.pr_number}/commits/sha)\n\n"
            "Respond with the required JSON structure."
        )

        messages = [{"role": "user", "content": user_message}]

        response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=PR_COMMENT_SYSTEM,
            tools=[GIT_TOOL],
            messages=messages,
        )

        if response.stop_reason == "tool_use":
            tool_use = next(b for b in response.content if b.type == "tool_use")
            request = tool_use.input["request"]

            if repo_path:
                git_result = self._git_agent.handle(request, repo_path)
            else:
                git_result = "No local repo path configured — cannot run git operations."

            # Serialize SDK content objects to plain dicts to avoid SDK serialization issues
            assistant_content = []
            for block in response.content:
                if block.type == "text":
                    assistant_content.append({"type": "text", "text": block.text})
                elif block.type == "tool_use":
                    assistant_content.append({"type": "tool_use", "id": block.id, "name": block.name, "input": block.input})

            messages += [
                {"role": "assistant", "content": assistant_content},
                {"role": "user", "content": [
                    {"type": "tool_result", "tool_use_id": tool_use.id, "content": git_result},
                    {"type": "text", "text": "Now output ONLY the JSON object as specified. No text before or after it."},
                ]},
            ]

            response = self.client.messages.create(
                model=self.model,
                max_tokens=512,
                system=PR_COMMENT_SYSTEM,
                tools=[GIT_TOOL],
                messages=messages,
            )

        raw = response.content[0].text.strip()

        # Strip markdown code fences if the LLM wrapped the JSON
        if raw.startswith("```"):
            raw = "\n".join(
                line for line in raw.splitlines()
                if not line.startswith("```")
            ).strip()

        try:
            data = json.loads(raw)
            return PRResponse(
                to_po=data.get("to_po", ""),
                to_agents=data.get("to_agents", []),
            )
        except (json.JSONDecodeError, KeyError):
            return PRResponse(to_po=f"**[ScrumMaster] → @{PO_HANDLE}:** {raw}")

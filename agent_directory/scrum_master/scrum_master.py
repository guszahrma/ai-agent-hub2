import json
import os
from dataclasses import dataclass, field
from agent_directory.base_agent import BaseAgent
from agent_directory.git_agent import GitAgent
from agent_directory.code_reviewer.code_reviewer import CodeReviewer

DELEGATION_CHECK_SYSTEM = """You are a Scrum Master checking on the progress of a delegated task.

Given a PR thread and a pending delegation, determine if the work has been completed.

Your response MUST be a raw JSON object:
{"status": "pending|in_progress|resolved", "notes": "one sentence summary"}

- "resolved": Jeeves has posted a clear completion report in the thread (look for **[Jeeves]** comments confirming done with a commit SHA)
- "in_progress": Jeeves has acknowledged the task but not completed it
- "pending": no update from Jeeves yet

Be conservative — only set "resolved" if there is clear evidence of completion.
"""

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

CODE_REVIEWER_TOOL = {
    "name": "delegate_to_code_reviewer",
    "description": "Run a full code review on the PR. Posts each finding as an inline review comment. Use this when asked to review a PR or verify code quality — do NOT use GitAgent for this.",
    "input_schema": {
        "type": "object",
        "properties": {
            "repo_ref": {"type": "string", "description": "Repository reference, e.g. owner/repo"},
            "pr_number": {"type": "integer", "description": "PR number to review"},
        },
        "required": ["repo_ref", "pr_number"],
    },
}

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
{{"to_po": "...", "to_agents": [...], "question": false}}

Rules:
- "to_po": start with **[ScrumMaster] → @{PO_HANDLE}:** — give the complete, final answer. If you called GitAgent, include its actual output (branch name, commits, etc.) in full. Never say "I will get" or "let me fetch" — by the time you write to_po, all tool calls are done and you have all the data you need. IMPORTANT: to_po must be plain text — never embed JSON inside it.
- "to_agents": list of {{"recipient": "AgentName", "message": "..."}} — use this whenever the user's comment results in a task for Jeeves (code changes, agent implementation, bug fixes, issue creation). If the user confirms a proposed action ("yes", "go ahead", "please implement"), you MUST include a to_agents entry for Jeeves with full task detail — do not just acknowledge and close. Do NOT claim Jeeves is "working on it" or "active" — Jeeves is a human-triggered assistant and will only act when a human opens Claude Code.
- "question": set to true if your to_po asks the user a question and you are waiting for their answer before you can act. Leave false for final answers, delegations, and declines.
- GitAgent is available as a tool — call it for local git operations (status, diff, log, branches). GitAgent has NO access to the GitHub API or GitHub settings. Do not ask GitAgent about branch protection, PR status, or anything requiring the GitHub API.
- delegate_to_code_reviewer is available as a tool — use it when asked to review the PR or verify code quality. It fetches the diff itself and posts findings as inline review comments. Do NOT use GitAgent for code review.
- Comments starting with **[CodeReviewer] are automated findings. Route blockers to Jeeves (fix in current PR) and suggestions as new issues or declines.
- If a question requires GitHub API knowledge (branch protection, PR checks, project settings), answer from thread history and your own knowledge — do not fabricate a verification step.
- Per workprocess: question before acting. If the comment is ambiguous, ask. Do not make changes autonomously.
- A PR comment has four valid outcomes — choose the right one:
  1. Fix in current PR / implement task: only if directly in scope. Delegate to Jeeves via to_agents with a specific task description.
  2. New issue: if the comment is valid but out of scope or larger than a quick fix. Create a GitHub issue and reply "Tracked as #N" in to_po.
  3. Decline: if invalid or a deliberate tradeoff. Explain why in to_po.
  4. Ask for clarification: if the comment is ambiguous or you need more information before acting. Set question: true in the response.
- Do not resolve threads. Do not mix PO and agent content.
- Output only the raw JSON object. No markdown formatting around it. No JSON inside to_po.
"""


@dataclass
class PRResponse:
    to_po: str
    to_agents: list[dict] = field(default_factory=list)
    question: bool = False


class ScrumMaster(BaseAgent):
    def __init__(self, model: str = None):
        super().__init__(
            name="scrum_master",
            system_prompt=SYSTEM_PROMPT,
            model=model,
        )
        self._git_agent = GitAgent()
        self._code_reviewer = CodeReviewer()

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

            try:
                if repo_path:
                    git_result = self._git_agent.handle(request, repo_path)
                else:
                    git_result = "No repo configured for this channel — cannot run git operations."
            except Exception as e:
                git_result = f"GitAgent error: {e}"

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

        tools = [GIT_TOOL, CODE_REVIEWER_TOOL]

        response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=PR_COMMENT_SYSTEM,
            tools=tools,
            messages=messages,
        )

        for _ in range(5):  # allow up to 5 tool call rounds before forcing a text response
            if response.stop_reason != "tool_use":
                break

            tool_uses = [b for b in response.content if b.type == "tool_use"]
            tool_results = []
            for tool_use in tool_uses:
                try:
                    if tool_use.name == "delegate_to_code_reviewer":
                        result = self._code_reviewer.review_and_post(
                            tool_use.input["repo_ref"],
                            tool_use.input["pr_number"],
                        )
                    else:  # delegate_to_git_agent
                        request = tool_use.input["request"]
                        if repo_path:
                            result = self._git_agent.handle(request, repo_path)
                        else:
                            result = "No local repo path configured — cannot run git operations."
                except Exception as e:
                    result = f"Tool error ({tool_use.name}): {e}"
                tool_results.append({"type": "tool_result", "tool_use_id": tool_use.id, "content": result})

            assistant_content = []
            for block in response.content:
                if block.type == "text":
                    assistant_content.append({"type": "text", "text": block.text})
                elif block.type == "tool_use":
                    assistant_content.append({"type": "tool_use", "id": block.id, "name": block.name, "input": block.input})

            messages += [
                {"role": "assistant", "content": assistant_content},
                {"role": "user", "content": tool_results + [
                    {"type": "text", "text": "Now output ONLY the JSON object as specified. No text before or after it."},
                ]},
            ]

            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=512,
                    system=PR_COMMENT_SYSTEM,
                    tools=tools,
                    messages=messages,
                )
            except Exception as e:
                print(f"  ScrumMaster follow-up API error: {e}")
                break

        if response.stop_reason == "tool_use":
            return PRResponse(to_po=f"**[ScrumMaster] → @{PO_HANDLE}:** Could not produce a response after multiple tool calls.")

        raw = response.content[0].text.strip()

        # Strip markdown code fences if the LLM wrapped the JSON
        if raw.startswith("```"):
            raw = "\n".join(
                line for line in raw.splitlines()
                if not line.startswith("```")
            ).strip()

        try:
            data = json.loads(raw)
            to_po = data.get("to_po", "")
            # Guard against LLM double-wrapping: to_po should never itself be JSON
            if isinstance(to_po, str) and to_po.lstrip().startswith("{"):
                try:
                    inner = json.loads(to_po)
                    if "to_po" in inner:
                        data = inner
                        to_po = inner.get("to_po", "")
                except json.JSONDecodeError:
                    pass
            return PRResponse(
                to_po=to_po,
                to_agents=data.get("to_agents", []),
                question=bool(data.get("question", False)),
            )
        except (json.JSONDecodeError, KeyError):
            return PRResponse(to_po=f"**[ScrumMaster] → @{PO_HANDLE}:** {raw}")

    def check_pending_delegation(self, pr_number: int, pr_title: str, repo_ref: str,
                                  thread_history: list[dict], delegation: dict) -> dict:
        """Check if a pending delegation has been completed. Returns {status, notes}."""
        history_text = "\n".join(f"[@{c['author']}]: {c['body']}" for c in thread_history)
        user_message = (
            f"PR #{pr_number} '{pr_title}' in {repo_ref}.\n"
            f"Pending delegation (ID {delegation['id']}): "
            f"agent={delegation['agent']}, task={delegation['task']!r}\n\n"
            f"Thread history:\n{history_text}\n\n"
            "Has this delegation been completed? Respond with the required JSON."
        )
        response = self.client.messages.create(
            model=self.model,
            max_tokens=256,
            system=DELEGATION_CHECK_SYSTEM,
            messages=[{"role": "user", "content": user_message}],
        )
        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = "\n".join(
                line for line in raw.splitlines() if not line.startswith("```")
            ).strip()
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"status": "pending", "notes": raw}

import json
from agent_directory.base_agent import BaseAgent

GITHUB_API = "https://api.github.com"

SYSTEM_PROMPT = """You are an IssueManager AI agent.

Your job is to create, close, and manage GitHub issues based on instructions from the ScrumMaster.

When given a task, respond with a raw JSON object — no markdown, no code fences:
{"action": "create|close|comment|noop", "title": "...", "body": "...", "labels": [], "issue_number": null, "reason": "..."}

Rules:
- "create": create a new GitHub issue. Populate title, body, and labels.
- "close": close an existing issue by issue_number.
- "comment": add a comment to an existing issue by issue_number.
- "noop": if the task is already done or out of scope. Explain in reason.
- body should be a complete Markdown issue description.
- labels should be an array of strings (use existing label names where possible).
- Output only the JSON object.
"""


class IssueManager(BaseAgent):
    def __init__(self, model: str = None):
        super().__init__(
            name="issue_manager",
            system_prompt=SYSTEM_PROMPT,
            model=model,
        )

    def create_issue(self, repo_ref: str, title: str, body: str,
                     labels: list[str] | None = None) -> int:
        """Create a GitHub issue. Returns the issue number."""
        if not self.github:
            raise RuntimeError("No GITHUB_TOKEN configured")
        payload = {"title": title, "body": body}
        if labels:
            payload["labels"] = labels
        resp = self.github.post(f"{GITHUB_API}/repos/{repo_ref}/issues", json=payload)
        resp.raise_for_status()
        return resp.json()["number"]

    def close_issue(self, repo_ref: str, issue_number: int) -> bool:
        """Close a GitHub issue. Returns True on success."""
        if not self.github:
            raise RuntimeError("No GITHUB_TOKEN configured")
        resp = self.github.patch(
            f"{GITHUB_API}/repos/{repo_ref}/issues/{issue_number}",
            json={"state": "closed"},
        )
        return resp.ok

    def comment_on_issue(self, repo_ref: str, issue_number: int, body: str) -> bool:
        """Post a comment on a GitHub issue. Returns True on success."""
        if not self.github:
            raise RuntimeError("No GITHUB_TOKEN configured")
        resp = self.github.post(
            f"{GITHUB_API}/repos/{repo_ref}/issues/{issue_number}/comments",
            json={"body": body},
        )
        return resp.ok

    def execute(self, task: str, repo_ref: str = None, repo_path: str = None, pr_number: int = None) -> str | None:
        return self.execute_task(task, repo_ref or "")

    def execute_task(self, task: str, repo_ref: str) -> str:
        """Interpret a natural-language issue management task and execute it."""
        if not self.github:
            return "No GITHUB_TOKEN — cannot manage GitHub issues."

        raw = self.run([{"role": "user", "content": f"Repo: {repo_ref}\n\nTask: {task}"}])

        if raw.startswith("```"):
            raw = "\n".join(l for l in raw.splitlines() if not l.startswith("```")).strip()

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return f"IssueManager could not parse its own output: {raw[:200]}"

        action = data.get("action", "noop")

        if action == "create":
            try:
                num = self.create_issue(
                    repo_ref,
                    title=data["title"],
                    body=data.get("body", ""),
                    labels=data.get("labels") or [],
                )
                return f"Created issue #{num}: {data['title']}"
            except Exception as e:
                return f"Failed to create issue: {e}"

        if action == "close":
            issue_number = data.get("issue_number")
            if not issue_number:
                return "close action requires issue_number"
            ok = self.close_issue(repo_ref, int(issue_number))
            return f"Closed issue #{issue_number}" if ok else f"Failed to close #{issue_number}"

        if action == "comment":
            issue_number = data.get("issue_number")
            if not issue_number:
                return "comment action requires issue_number"
            ok = self.comment_on_issue(repo_ref, int(issue_number), data.get("body", ""))
            return f"Commented on issue #{issue_number}" if ok else f"Failed to comment on #{issue_number}"

        return f"noop — {data.get('reason', 'no action taken')}"

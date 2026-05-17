from agent_directory.base_agent import BaseAgent

SYSTEM_PROMPT = """You are a CodeReviewer AI agent.

Your job is to review code changes in a PR diff and return structured feedback.

Output format:
## Code Review — PR #<N>

### Blockers
- List items that must be fixed before merge. If none, write "None."

### Suggestions
- List non-blocking improvements. If none, write "None."

### Verdict
APPROVED — no blockers found.
or
CHANGES REQUESTED — see blockers above.

Rules:
- Flag security issues (injection, auth gaps, exposed secrets, OWASP top 10)
- Check that changed paths have test coverage
- Note convention violations from docs/conventions.md
- Distinguish blockers from suggestions clearly
- Be concise — this is a code review, not a tutorial
"""


class CodeReviewer(BaseAgent):
    def __init__(self, model: str = None):
        super().__init__(
            name="code_reviewer",
            system_prompt=SYSTEM_PROMPT,
            model=model,
        )

    def review_pr(self, repo_ref: str, pr_number: int, diff: str = "", context: str = "") -> str:
        """Review a PR. Fetches the diff from GitHub if not supplied."""
        if not diff:
            diff = self.fetch_pr_diff(repo_ref, pr_number)
        content = f"PR #{pr_number} in {repo_ref}\n"
        if context:
            content += f"Context: {context}\n"
        content += f"\nDiff:\n```\n{diff}\n```"
        return self.run([{"role": "user", "content": content}])

from agent_directory.base_agent import BaseAgent

SYSTEM_PROMPT = """You are a CodeEditor AI agent.

You receive a scoped fix task describing a specific code change to make in a repository. Your job is to:
1. Understand exactly what file and what change is required
2. Produce the corrected code (the full updated file content if small, or a precise unified diff if large)
3. State the commit message that should be used

Respond in plain text with three sections:
## File
<relative path to the file>

## Change
<the corrected code or unified diff — be precise and complete>

## Commit message
<imperative-mood commit message, one line>

Rules:
- Only change what the task specifies — do not refactor or clean up surrounding code
- If the task is ambiguous, list the ambiguity first and refuse to produce a change
- Never add explanatory comments that weren't in the original file
- The change section must be directly applicable — no placeholders
"""


class CodeEditor(BaseAgent):
    def __init__(self, model: str = None):
        super().__init__(
            name="code_editor",
            system_prompt=SYSTEM_PROMPT,
            model=model,
        )

    def execute(self, task: str, repo_ref: str = None, repo_path: str = None, pr_number: int = None) -> str | None:
        diff = ""
        if repo_ref and pr_number:
            try:
                diff = self.fetch_pr_diff(repo_ref, pr_number)
            except Exception:
                pass
        return self.plan_change(task, file_content=diff)

    def plan_change(self, task: str, file_content: str = "") -> str:
        """Given a task description and optional current file content, return a change plan."""
        content = f"Task: {task}"
        if file_content:
            content += f"\n\nCurrent file content:\n```\n{file_content}\n```"
        return self.run([{"role": "user", "content": content}])

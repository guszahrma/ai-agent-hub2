import json
from agent_directory.base_agent import BaseAgent

SYSTEM_PROMPT = """You are a CodeEditor AI agent.

You receive a code fix task, the current file content, and optional PR diff context.

Respond with a raw JSON object — no markdown, no code fences:
{"file": "relative/path/to/file", "content": "<complete corrected file content>", "commit_message": "<imperative-mood one-line commit message>"}

If the task is ambiguous or the correct fix cannot be determined with certainty:
{"file": null, "content": null, "commit_message": null, "ambiguity": "<explanation>"}

Rules:
- content must be the COMPLETE new file — not a diff, not a snippet
- Only change what the task specifies — do not refactor surrounding code
- Never add comments that were not in the original file
- commit_message: imperative mood, one line, no trailing period
- Output only the JSON object
"""

_FILE_EXTRACT_SYSTEM = (
    "Extract the single relative file path to change from this task. "
    "Output only the path (e.g. bot/state_store.py), nothing else. "
    'If multiple files or genuinely unclear, output "unclear".'
)


class CodeEditor(BaseAgent):
    def __init__(self, model: str = None):
        super().__init__(
            name="code_editor",
            system_prompt=SYSTEM_PROMPT,
            model=model,
        )

    def execute(self, task: str, repo_ref: str = None, repo_path: str = None, pr_number: int = None) -> str | None:
        # 1. Fetch PR diff as background context
        diff_context = ""
        if repo_ref and pr_number:
            try:
                diff_context = self.fetch_pr_diff(repo_ref, pr_number)
            except Exception:
                pass

        # 2. Identify which file to change
        file_path = self._identify_target_file(task, diff_context)
        if not file_path:
            return "Could not determine which file to change — task may be ambiguous."

        # 3. Read current file content from disk
        current_content = ""
        if repo_path:
            current_content = self.read_local_file(repo_path, file_path) or ""

        # 4. Generate the full corrected file
        parts = [f"Task: {task}", f"File to change: {file_path}"]
        if current_content:
            parts.append(f"Current file content:\n```\n{current_content}\n```")
        if diff_context:
            parts.append(f"PR diff context:\n```\n{diff_context}\n```")

        raw = self.run([{"role": "user", "content": "\n\n".join(parts)}])
        if raw.startswith("```"):
            raw = "\n".join(l for l in raw.splitlines() if not l.startswith("```")).strip()

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return f"CodeEditor output could not be parsed: {raw[:200]}"

        if data.get("ambiguity"):
            return f"Cannot apply fix: {data['ambiguity']}"

        if not data.get("file") or not data.get("content"):
            return "CodeEditor did not produce a complete file and content."

        if not repo_path:
            return f"No local repo path — cannot write file. Planned change for {data['file']}:\n{data.get('commit_message', '')}"

        # 5. Write, commit, push
        self.write_local_file(repo_path, data["file"], data["content"])
        try:
            sha = self.commit_and_push(repo_path, data["commit_message"], [data["file"]])
        except Exception as e:
            return f"Change written to {data['file']} but commit/push failed: {e}"

        commit_url = (
            f"https://github.com/{repo_ref}/pull/{pr_number}/commits/{sha}"
            if repo_ref and pr_number else sha
        )
        self.reflect(
            f"Applied fix to {data['file']} in {repo_ref} PR #{pr_number}.\n"
            f"Task: {task[:200]}\nCommit: {sha}"
        )
        return f"Applied fix in [{sha}]({commit_url}). Please delegate verification to CodeReviewer and confirm this resolves the finding."

    def _identify_target_file(self, task: str, diff_context: str) -> str | None:
        content = f"Task: {task}"
        if diff_context:
            content += f"\n\nPR diff context (first 2000 chars):\n{diff_context[:2000]}"
        raw = self.client.messages.create(
            model=self.model,
            max_tokens=64,
            system=_FILE_EXTRACT_SYSTEM,
            messages=[{"role": "user", "content": content}],
        ).content[0].text.strip()
        return None if not raw or raw.lower() == "unclear" else raw

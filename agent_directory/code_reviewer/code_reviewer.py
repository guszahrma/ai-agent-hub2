import json
import re
from agent_directory.base_agent import BaseAgent

GITHUB_API = "https://api.github.com"

SYSTEM_PROMPT = """You are a CodeReviewer AI agent.

Review the PR diff and return a raw JSON object — no markdown, no code fences:
{"findings": [...], "verdict": "APPROVED|CHANGES REQUESTED"}

Each finding:
{
  "file": "relative/path/to/file",
  "line": <integer — line number in the new file; use the first changed line of the file if unsure>,
  "severity": "blocker|suggestion",
  "title": "<10 words max>",
  "body": "<concise explanation and how to fix it>"
}

Rules:
- Flag security issues (injection, auth gaps, exposed secrets, OWASP top 10)
- Check that changed paths have test coverage
- Note convention violations
- Distinguish blockers from suggestions clearly
- Only report findings for files present in the diff
- Output ONLY the JSON object
"""


class CodeReviewer(BaseAgent):
    def __init__(self, model: str = None):
        super().__init__(
            name="code_reviewer",
            system_prompt=SYSTEM_PROMPT,
            model=model,
        )

    def _get_pr_meta(self, repo_ref: str, pr_number: int) -> tuple[str, list]:
        pr = self.github.get(f"{GITHUB_API}/repos/{repo_ref}/pulls/{pr_number}")
        pr.raise_for_status()
        head_sha = pr.json()["head"]["sha"]
        files_resp = self.github.get(
            f"{GITHUB_API}/repos/{repo_ref}/pulls/{pr_number}/files",
            params={"per_page": 100},
        )
        files_resp.raise_for_status()
        return head_sha, files_resp.json()

    def _anchor_lines(self, files: list) -> dict[str, int]:
        """Returns {filename: first_valid_new_file_line} for each changed file."""
        result = {}
        for f in files:
            if f.get("status") == "removed":
                continue
            patch = f.get("patch", "")
            if not patch:
                continue
            m = re.search(r'@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@', patch)
            result[f["filename"]] = int(m.group(1)) if m else 1
        return result

    def review_and_post(self, repo_ref: str, pr_number: int) -> str:
        """Run a code review and post each finding as an inline review comment."""
        if not self.github:
            return "No GITHUB_TOKEN — cannot post review comments."

        head_sha, files = self._get_pr_meta(repo_ref, pr_number)
        diff = self.fetch_pr_diff(repo_ref, pr_number)
        anchors = self._anchor_lines(files)

        raw = self.run([{"role": "user", "content": f"PR #{pr_number} in {repo_ref}\n\nDiff:\n```\n{diff}\n```"}])

        if raw.startswith("```"):
            raw = "\n".join(l for l in raw.splitlines() if not l.startswith("```")).strip()

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return f"CodeReviewer output could not be parsed: {raw[:200]}"

        findings = data.get("findings", [])
        verdict = data.get("verdict", "")
        posted = 0

        for finding in findings:
            file_path = finding.get("file", "")
            anchor = anchors.get(file_path)
            if not anchor:
                continue

            line = finding.get("line") or anchor
            severity = finding.get("severity", "suggestion").capitalize()
            title = finding.get("title", "Finding")
            body = f"**[CodeReviewer] {severity}: {title}**\n\n{finding.get('body', '')}"

            resp = self.github.post(
                f"{GITHUB_API}/repos/{repo_ref}/pulls/{pr_number}/comments",
                json={"body": body, "commit_id": head_sha, "path": file_path, "line": line, "side": "RIGHT"},
            )
            if not resp.ok and line != anchor:
                resp = self.github.post(
                    f"{GITHUB_API}/repos/{repo_ref}/pulls/{pr_number}/comments",
                    json={"body": body, "commit_id": head_sha, "path": file_path, "line": anchor, "side": "RIGHT"},
                )
            if resp.ok:
                posted += 1

        return f"Posted {posted}/{len(findings)} findings as inline review comments. Verdict: {verdict}"

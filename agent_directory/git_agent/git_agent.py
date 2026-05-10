from agent_directory.base_agent import BaseAgent
from tools import git_tools

SYSTEM_PROMPT = """You are a Git specialist agent. You interpret natural language git requests and report results clearly.

You have access to the following git operations:
- status: show working tree status
- diff: show unstaged or staged changes
- log: show recent commits
- branches: list branches
- current_branch: show active branch
- add: stage files
- commit: commit staged changes
- checkout: switch or create branches
- pull: pull from remote
- push: push to remote

Rules:
- Always report what you did and the result
- For write operations (commit, push, checkout -b), confirm the action taken
- Never force push
- If a request is ambiguous, state your assumption before acting
- Keep responses concise — one paragraph max
"""


class GitAgent(BaseAgent):
    def __init__(self, model: str = None):
        super().__init__(
            name="git_agent",
            system_prompt=SYSTEM_PROMPT,
            model=model,
        )

    def handle(self, request: str, repo_path: str) -> str:
        context = self._gather_context(repo_path)
        messages = [{
            "role": "user",
            "content": f"Repo: {repo_path}\n\nCurrent state:\n{context}\n\nRequest: {request}"
        }]
        try:
            return self.run(messages)
        except git_tools.SafetyError as e:
            return f"⛔ Blocked by safety guardrail: {e}"
        except git_tools.GitError as e:
            return f"❌ Git error: {e}"

    def _gather_context(self, repo_path: str) -> str:
        try:
            branch = git_tools.current_branch(repo_path)
            status = git_tools.status(repo_path) or "(clean)"
            recent = git_tools.log(repo_path, n=5)
            return f"Branch: {branch}\nStatus:\n{status}\nRecent commits:\n{recent}"
        except git_tools.GitError as e:
            return f"Could not read repo state: {e}"

    def commit(self, repo_path: str, message: str) -> str:
        return git_tools.commit(
            repo_path,
            message,
            author_name=self.git_name,
            author_email=self.git_email,
        )

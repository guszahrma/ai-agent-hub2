import os
import anthropic
import requests
import yaml
from pathlib import Path


GLOBAL_CONFIG_PATH = Path(__file__).parent.parent / "config" / "agents.yaml"


class BaseAgent:
    def __init__(self, name: str, system_prompt: str, model: str = None):
        self.name = name
        self.system_prompt = system_prompt
        self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.github = self._make_github_session()
        agent_config = self._load_agent_config(name)
        self.model = model or agent_config.get("model", "claude-sonnet-4-6")
        self.max_tokens = agent_config.get("max_tokens", 4096)
        self.git_name = agent_config.get("git_name", name)
        self.git_email = agent_config.get("git_email", f"{name}@ai-agent-hub2")

    def _make_github_session(self) -> requests.Session | None:
        token = os.getenv("GITHUB_TOKEN")
        if not token:
            return None
        session = requests.Session()
        session.headers.update({
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        })
        return session

    def _load_agent_config(self, name: str) -> dict:
        # Look for per-agent config.yaml first, fall back to global agents.yaml
        per_agent = Path(__file__).parent / name / "config.yaml"
        if per_agent.exists():
            with open(per_agent) as f:
                return yaml.safe_load(f) or {}
        with open(GLOBAL_CONFIG_PATH) as f:
            data = yaml.safe_load(f) or {}
        return data.get("agents", {}).get(name, {})

    def fetch_pr_diff(self, repo_ref: str, pr_number: int) -> str:
        """Fetch the unified diff for a PR from the GitHub API."""
        if not self.github:
            raise RuntimeError("No GITHUB_TOKEN configured")
        resp = self.github.get(
            f"https://api.github.com/repos/{repo_ref}/pulls/{pr_number}/files",
            params={"per_page": 100},
        )
        resp.raise_for_status()
        parts = []
        for f in resp.json():
            patch = f.get("patch", "")
            if patch:
                parts.append(f"--- a/{f['filename']}\n+++ b/{f['filename']}\n{patch}")
        return "\n".join(parts)

    def run(self, messages: list) -> str:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=self.system_prompt,
            messages=messages,
        )
        return response.content[0].text

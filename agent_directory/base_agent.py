import json
import os
import re
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
        self.memory_path = Path(__file__).parent / name / "memory"
        self.memory_path.mkdir(exist_ok=True)

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

    def _load_memory(self) -> str:
        """Load MEMORY.md and all files it links to. Returns empty string if no memory."""
        index = self.memory_path / "MEMORY.md"
        if not index.exists():
            return ""
        content = index.read_text()
        parts = [content]
        for match in re.finditer(r'\[.*?\]\(([^)]+\.md)\)', content):
            linked = self.memory_path / match.group(1)
            if linked.exists():
                parts.append(linked.read_text())
        return "\n\n".join(parts)

    def _prompt_with_memory(self, base_prompt: str) -> str:
        """Append agent memory to a system prompt if any memory exists."""
        memory = self._load_memory()
        if not memory:
            return base_prompt
        return f"{base_prompt}\n\n---\n## Your memory from past interactions\n{memory}"

    def _save_memory_entry(self, name: str, type_: str, description: str, content: str):
        """Write a memory file and update the MEMORY.md index."""
        entry = (
            f"---\nname: {name}\ndescription: {description}\n"
            f"metadata:\n  type: {type_}\n---\n\n{content}\n"
        )
        (self.memory_path / f"{name}.md").write_text(entry)
        index = self.memory_path / "MEMORY.md"
        existing = index.read_text() if index.exists() else ""
        link = f"- [{name}]({name}.md) — {description}"
        if f"({name}.md)" not in existing:
            index.write_text(existing.rstrip() + f"\n{link}\n")

    def reflect(self, interaction_summary: str) -> None:
        """Ask the agent if there is anything to reflect on, remember, or learn."""
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=512,
                system="""You are reflecting on a recent interaction.

Ask yourself: is there something I should reflect on, remember, and/or learn from this?

If yes, respond with a raw JSON object:
{"update": true, "name": "kebab-case-slug", "type": "feedback|preference|pattern|error", "description": "one-line summary", "content": "full memory body in markdown"}

If nothing notable, respond with:
{"update": false}

Output only the JSON object.""",
                messages=[{"role": "user", "content": interaction_summary}],
            )
            raw = response.content[0].text.strip()
            if raw.startswith("```"):
                raw = "\n".join(l for l in raw.splitlines() if not l.startswith("```")).strip()
            data = json.loads(raw)
            if data.get("update"):
                self._save_memory_entry(
                    name=data["name"],
                    type_=data.get("type", "pattern"),
                    description=data.get("description", ""),
                    content=data.get("content", ""),
                )
                print(f"  [{self.name}] Memory updated: {data['name']}")
        except Exception as e:
            print(f"  [{self.name}] Reflection failed: {e}")

    def run(self, messages: list) -> str:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=self.system_prompt,
            messages=messages,
        )
        return response.content[0].text

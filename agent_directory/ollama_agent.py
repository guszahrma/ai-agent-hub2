import json
import requests
from pathlib import Path
from agent_directory.base_agent import BaseAgent


class OllamaAgent(BaseAgent):
    """BaseAgent variant backed by a locally running Ollama server instead of Anthropic."""

    OLLAMA_BASE = "http://localhost:11434"

    def __init__(self, name: str, system_prompt: str):
        self.name = name
        self.system_prompt = system_prompt
        self.client = None
        self.github = self._make_github_session()
        agent_config = self._load_agent_config(name)
        self.ollama_model = agent_config.get("ollama_model", "qwen2.5-coder:7b")
        self.model = self.ollama_model
        self.max_tokens = agent_config.get("max_tokens", 4096)
        self.git_name = agent_config.get("git_name", name)
        self.git_email = agent_config.get("git_email", f"{name}@ai-agent-hub2")
        self.memory_path = Path(__file__).parent / name / "memory"
        self.memory_path.mkdir(exist_ok=True)

    def run(self, messages: list) -> str:
        ollama_messages = [{"role": "system", "content": self.system_prompt}] + messages
        resp = requests.post(
            f"{self.OLLAMA_BASE}/api/chat",
            json={"model": self.ollama_model, "messages": ollama_messages, "stream": False},
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()["message"]["content"]

    def reflect(self, interaction_summary: str) -> None:
        try:
            resp = requests.post(
                f"{self.OLLAMA_BASE}/api/chat",
                json={
                    "model": self.ollama_model,
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "You are reflecting on a recent interaction.\n\n"
                                "Ask yourself: is there something I should reflect on, remember, and/or learn?\n\n"
                                "If yes, respond with a raw JSON object:\n"
                                '{"update": true, "name": "kebab-case-slug", "type": "feedback|preference|pattern|error", '
                                '"description": "one-line summary", "content": "full memory body in markdown"}\n\n'
                                "If nothing notable:\n"
                                '{"update": false}\n\n'
                                "Output only the JSON object."
                            ),
                        },
                        {"role": "user", "content": interaction_summary},
                    ],
                    "stream": False,
                },
                timeout=60,
            )
            resp.raise_for_status()
            raw = resp.json()["message"]["content"].strip()
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

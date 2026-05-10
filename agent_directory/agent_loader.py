"""
Loads project agents from a repo's agent_team/ folder.

A project agent extends a base agent from agent_directory/ and can override
config values and append to or contradict the base system prompt.
"""
import re
from pathlib import Path
import yaml


AGENT_DIRECTORY = Path(__file__).parent


def _load_yaml(path: Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f) or {}


def _merge_config(base: dict, override: dict) -> dict:
    merged = dict(base)
    for k, v in override.items():
        if k != "extends":
            merged[k] = v
    return merged


def _merge_docs(base_docs: str, project_docs: str) -> str:
    additions = re.search(r"##\s+Additions\s+(.*?)(?=##|\Z)", project_docs, re.DOTALL)
    overrides = re.search(r"##\s+Overrides\s+(.*?)(?=##|\Z)", project_docs, re.DOTALL)

    parts = [base_docs.strip()]
    if additions:
        parts.append(additions.group(1).strip())
    if overrides:
        override_text = overrides.group(1).strip()
        parts.append(f"Notwithstanding any instructions above:\n{override_text}")
    return "\n\n".join(parts)


def load_project_agents(repo_path: str | Path) -> list[dict]:
    """
    Scan repo_path/agent_team/ and return a list of resolved agent specs.

    Each spec is a dict with:
      - name: project agent folder name
      - base: name of the base agent in agent_directory/
      - config: merged config dict
      - system_prompt: merged system prompt string (or None if no base docs.md)
    """
    agent_team_path = Path(repo_path) / "agent_team"
    if not agent_team_path.exists():
        return []

    agents = []
    for folder in sorted(agent_team_path.iterdir()):
        if not folder.is_dir():
            continue
        config_path = folder / "config.yaml"
        if not config_path.exists():
            continue

        project_config = _load_yaml(config_path)
        base_name = project_config.get("extends")
        if not base_name:
            continue

        base_dir = AGENT_DIRECTORY / base_name
        if not base_dir.exists():
            continue

        base_config_path = base_dir / "config.yaml"
        base_config = _load_yaml(base_config_path) if base_config_path.exists() else {}
        merged_config = _merge_config(base_config, project_config)

        system_prompt = None
        base_docs_path = base_dir / "docs.md"
        if base_docs_path.exists():
            base_docs = base_docs_path.read_text()
            project_docs_path = folder / "docs.md"
            if project_docs_path.exists():
                system_prompt = _merge_docs(base_docs, project_docs_path.read_text())
            else:
                system_prompt = base_docs.strip()

        agents.append({
            "name": folder.name,
            "base": base_name,
            "config": merged_config,
            "system_prompt": system_prompt,
        })

    return agents

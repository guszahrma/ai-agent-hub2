# Project Context

**Repo:** guszahrma/ai-agent-hub2  
**Purpose:** A reusable library of AI agents. The Scrum Master agent runs as a Discord bot and orchestrates specialist agents across different projects.

**Stack:** Python, Anthropic SDK, discord.py  
**Model config:** `config/agents.yaml` — swap models without touching code  
**Repo-to-channel mapping:** `config/repos.yaml` — each Discord channel maps to one git repo  

**Key decisions made:**
- One Discord channel per repo (context is implicit, not a command)
- `GIT_BASE_DIR` in `.env` + project name = local repo path
- Agents are stateless per message for now (no conversation history yet)
- Write operations deferred until read-only git tools are validated

**Active task:** git_support — see `current_task/git_support.md`

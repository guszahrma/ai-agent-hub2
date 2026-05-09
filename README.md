# AI Agent Hub

A reusable library of AI agents designed to work together. The Scrum Master agent lives in a Discord channel and on Github and orchestrates specialist agents on demand.

Git integration is a first-class feature. Each Discord channel maps to a git repository via `config/repos.yaml`. The Scrum Master AI Agent automatically delegates git-related requests to the GitAgent specialist, which handles status, diffs, logs, and writes (commit, push, checkout) with per-agent commit attribution and safety guardrails on protected branches.

## Structure

```
agents/          # One file per agent, all inherit from BaseAgent
bot/             # Discord listener — hands messages to the Scrum Master
config/          # Model assignments per agent (swap models here, not in code)
docs/agents/     # Human-readable explanation of each agent
```

## Quickstart

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set up environment
cp .env.example .env
# Fill in DISCORD_TOKEN, ANTHROPIC_API_KEY, DISCORD_CHANNEL_ID

# 3. Run the bot
python bot/discord_bot.py
```

## Swapping models

Edit `config/agents.yaml` — no code changes needed:

```yaml
agents:
  scrum_master:
    model: claude-opus-4-7   # change this line
```

Valid model IDs: `claude-sonnet-4-6`, `claude-opus-4-7`, `claude-haiku-4-5-20251001`

## Adding a new agent

1. Create `agents/<name>.py` inheriting `BaseAgent`
2. Add it to `config/agents.yaml`
3. Import it in `agents/scrum_master.py` and wire up delegation logic
4. Add a doc file at `docs/agents/<name>.md`

## Agents

| Agent | Role | Doc |
|---|---|---|
| Scrum Master | Orchestrator, Discord listener | [docs](docs/agents/scrum_master.md) |

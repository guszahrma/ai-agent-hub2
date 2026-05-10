# Scrum Master Agent

## Purpose
The Scrum Master is the primary orchestrator. It lives in a Discord channel and is always listening. It handles incoming messages, decides whether to respond directly or delegate to a specialist agent, and keeps the team aligned.

## Interaction model
- Reads every message in the configured Discord channel
- Responds in-channel, keeping replies concise
- When a task requires a specialist, it delegates explicitly and reports back

## Configuration
Set the model in `config/agents.yaml` under `agents.scrum_master.model`.

## How to add a specialist agent it can delegate to
1. Create `agent_directory/<name>/` following the structure in `docs/conventions.md`
2. Add an entry to `config/agents.yaml`
3. Import and instantiate the agent in `agent_directory/scrum_master/scrum_master.py`
4. Add delegation logic to `handle_message`

## PR comment handling

When responding to a PR comment, the ScrumMaster must assess the right outcome:
- **Fix in current PR** — only if directly in scope and small
- **New issue** — when the comment is valid but out of scope or large; create the issue, reply with `Tracked as #N`
- **Decline** — when invalid or a deliberate tradeoff; explain why in the thread

## Environment variables required
| Variable | Description |
|---|---|
| `DISCORD_TOKEN` | Bot token from Discord Developer Portal |
| `DISCORD_CHANNEL_ID` | Numeric ID of the channel to listen on |
| `ANTHROPIC_API_KEY` | Your Anthropic API key |

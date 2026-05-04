# Discord Commands

Each Discord channel is mapped to a git repo in `config/repos.yaml`.
The bot only listens to channels listed there — repo context is automatic.

## Adding a new repo/channel

Edit `config/repos.yaml`:

```yaml
repos:
  "YOUR_CHANNEL_ID":
    ref: git_user/project_name
    name: Human-readable name
```

The bot resolves `project_name` against `GIT_BASE_DIR` in `.env`.

---

## Natural language
Any message in a configured channel is passed to the Scrum Master agent,
which responds conversationally or delegates to a specialist agent.
The active repo is always included as context automatically.

---

## Planned commands
These will be added as specialist agents are built out:

| Command | Description |
|---|---|
| `!status` | Show git status of the channel's repo |
| `!log` | Show recent commits |
| `!diff` | Show current diff |

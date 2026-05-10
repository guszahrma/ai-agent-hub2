# Conventions

Standards that apply across this repository for both human and agent contributors.

Standards that apply across this repository. Follow these before adding files, folders, or agents.

## Commits

One commit per GitHub issue or sub-task. This applies to both human and agent contributors.

- Commit messages reference the issue they close: `Closes #N`
- Each commit should be independently understandable and revertable
- Avoid bundling multiple issues into one commit — the issue breakdown defines the right granularity

Agent-specific note: agents plan work in issues before writing code, so the issue structure naturally defines commit boundaries. A session covering multiple issues should produce multiple commits.

## Naming

All folder and file names use **snake_case**. No kebab-case, no camelCase.

```
agent_directory/       ✓
agent-directory/       ✗
agentDirectory/        ✗
```

## Agent terminology

Two locations hold agent definitions. Use these terms consistently in code, docs, and conversation:

| Term | Folder | Purpose |
|---|---|---|
| **Agent Directory** | `agent_directory/` in this repo | All available, reusable agent definitions |
| **Agent Team** | `agent_team/` in a project repo | Agents active for that specific project |

A project agent in `agent_team/` may inherit from an Agent Directory definition and extend or override it.

## Agent Directory structure

Every agent in `agent_directory/` must contain:

```
agent_directory/
  <agent_name>/
    __init__.py     # exports the agent class (or explains why there isn't one)
    config.yaml     # model, capabilities, and agent-level settings
    docs.md         # role, responsibilities, interaction model
    <agent_name>.py # implementation (omit for non-Python agents like Jeeves)
    memory/         # optional — persistent memory files for stateful agents
```

### config.yaml schema

```yaml
model: claude-sonnet-4-6       # required — Anthropic model ID
max_tokens: 4096               # optional — defaults to 1024 if omitted
git_name: AgentName            # required — used for git commit attribution
git_email: agent@ai-agent-hub2 # required — used for git commit attribution
```

`base_agent.py` lives directly in `agent_directory/` as shared infrastructure — it is not an agent and does not get its own subfolder.

### Conformance

| Agent | `__init__.py` | `config.yaml` | `docs.md` | Implementation | Status |
|---|---|---|---|---|---|
| scrum_master | ✓ | ✓ | ✓ | `scrum_master.py` | Conforms |
| git_agent | ✓ | ✓ | ✓ | `git_agent.py` | Conforms |
| jeeves | ✓ | ✓ | ✓ | n/a (Claude Code) | Conforms |

## Agent Team structure

Each project repo may have an `agent_team/` folder at its root. Each subfolder is a project agent.

```
project-repo/
  agent_team/
    <project_agent_name>/
      config.yaml   # required — must include `extends`; only overridden fields needed
      docs.md       # optional — additions and overrides to the base system prompt
```

### config.yaml

At minimum:
```yaml
extends: scrum_master   # name of the base agent in agent_directory/
```

Any additional fields override the corresponding base `config.yaml` values:
```yaml
extends: scrum_master
model: claude-opus-4-7   # override model for this project
```

The project agent folder name is free-form — a project agent extending `scrum_master` may be named `nisse`.

### docs.md — additions and overrides

If present, `docs.md` is merged with the base agent's `docs.md` using two optional sections:

```markdown
## Additions
New instructions appended after the base system prompt.

## Overrides
- Even if the base instructions say you should be happy, you should be neutral and professional.
```

- **Additions** are appended to the base system prompt as-is.
- **Overrides** are appended after additions. Because later instructions take precedence with LLMs, each override bullet explicitly contradicts a base instruction.

If `docs.md` is absent, the base system prompt is used unchanged.

### Discovery

The bot scans the project repo's `agent_team/` folder at startup. Every subfolder containing a valid `config.yaml` with an `extends` field is loaded as an active project agent.

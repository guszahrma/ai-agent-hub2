# Task: Git Support for Agents

**Status:** Planning  
**Goal:** Give agents the ability to read and interact with git repositories across different projects.

---

## Subtasks

### 1. Git tools library
**Status:** Done  
Create `tools/git_tools.py` — a set of Python functions wrapping common git operations.
Operations to cover: status, diff, log, branch list, checkout, commit, push, pull.
Agents import from this module rather than shelling out to git themselves.

### 2. Repo context
**Status:** Done  
Define how an agent knows *which repo* to operate on.
Proposal: pass a `repo_path` at runtime (via Discord message or config), stored in session state on the Scrum Master.

### 3. GitAgent specialist
**Status:** Todo  
Create `agents/git_agent.py` — a specialist the Scrum Master can delegate git tasks to.
Responsibilities: interpret natural language git requests, call git tools, report back results.

### 4. Scrum Master delegation
**Status:** Todo  
Wire up the Scrum Master to detect git-related requests and hand off to GitAgent.
Example triggers: "what's the status of the repo", "commit my changes", "create a branch for X".

### 5. Auth & safety
**Status:** Todo  
Decide how to handle credentials for push/pull to remotes (SSH keys vs tokens).
Add guardrails: no force pushes, confirm before destructive operations.

### 6. Multi-repo support
**Status:** Todo  
Allow the Scrum Master to manage multiple repos across different projects.
Proposal: maintain a named registry of repos in `config/repos.yaml`.

---

## Notes
- Git operations run on the *host machine* where the bot is running
- Start with read-only operations (status, diff, log) before write operations (commit, push)
- Each subtask should be committed separately for clean history

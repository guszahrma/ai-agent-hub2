# Task: Jeeves Persistent Memory

**Status:** In Progress  
**Priority:** Low (below git_support)  
**Goal:** Give Jeeves (Claude Code) a persistent memory store inside the repo that survives session restarts and syncs across machines via git.

---

## Subtasks

### 1. Memory folder structure
**Status:** Done  
Created `jeeves/memory/` with `MEMORY.md` index, `project_context.md`, and `user_preferences.md`.

### 2. Add to .gitignore or commit to git
**Status:** Todo  
Decide whether Jeeves memory files should be committed (shared across machines) or gitignored (local only). Currently untracked.

### 3. Memory loading instructions
**Status:** Todo  
Add a note to `CLAUDE.md` (or create one) so Jeeves knows to read `jeeves/memory/MEMORY.md` at the start of each session.

### 4. Memory update discipline
**Status:** Todo  
Define when and how Jeeves updates memory — e.g. after key decisions, after task completions, when user preferences change.

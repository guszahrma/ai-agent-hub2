---
name: guszahrma-delegate-to-code-editor
description: guszahrma prefers coding tasks to be delegated to Code Editor agent
metadata:
  type: preference
---

## Preference: Delegate Coding Tasks to Code Editor

**User:** @guszahrma (repo: guszahrma/ai-agent-hub2)

**Preference:** When a coding task arises (e.g., implementing a fix, adding validation logic, writing code), @guszahrma wants it delegated to the **Code Editor** agent rather than handled directly by ScrumMaster or other agents.

**Context:** Observed in PR #11 — user explicitly asked to delegate a branch name validation fix to Code Editor instead of proceeding otherwise.

**Action pattern:** ScrumMaster should route implementation tasks → Code Editor by default for this user.

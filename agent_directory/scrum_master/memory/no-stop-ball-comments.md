---
name: no-stop-ball-comments
description: Never post vague blocker comments; ask a direct question instead
metadata:
  type: preference
---

## Rule: No 'Stop Ball' Comments

**Source:** @guszahrma feedback on PR #11 (ai-agent-hub2)

**Rule:** Never post a vague, ambiguous, or blocking comment (a 'stop ball') that halts progress without clear direction.

**Instead:** If confused or unsure what to do, post a direct, specific question to the relevant person.

**Example of bad behaviour:** Writing `File config.py` or similar non-actionable fragments as a review comment.

**Example of good behaviour:** `@guszahrma — in config.py, should the API key be loaded from an environment variable or hardcoded for local dev? I need this clarified before I can proceed.`

**Applies to:** code_editor role and any agent posting PR/review comments.

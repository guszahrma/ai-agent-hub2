---
name: po-handle-hardcoded-fallback-blocker
description: Hard-coded fallback in os.getenv leaks real GitHub handle; treat as blocker
metadata:
  type: pattern
---

## Pattern: Hard-coded `os.getenv` fallback leaking identity

**Repo:** guszahrma/ai-agent-hub2, PR #11

**Issue:** `PO_HANDLE = os.getenv('PO_GITHUB_HANDLE', 'guszahrma')` — if the env var is unset, the real GitHub handle is embedded in every generated PR comment.

**Resolution approach:**
- Remove the default value entirely, OR
- Use an empty string fallback (`''`), OR
- Raise a clear `EnvironmentError` / `ValueError` at startup if the var is unset.

**Lesson:** Treat any hard-coded personal handle/credential as a default fallback in `os.getenv` as a blocker. Always prefer explicit failure (raise error) or a neutral placeholder over a real identity string.

**Action taken:** Flagged as blocker by CodeReviewer (@guszahrma), acknowledged by ScrumMaster, delegated to `code_editor` for fix.

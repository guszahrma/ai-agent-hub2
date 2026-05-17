---
name: path-method-repo-collision-bug
description: Bug: _path() uses only PR number for filename, causing cross-repo state file collisions
metadata:
  type: error
---

## Bug: `_path()` Cross-Repo State File Collision

**Reported in:** guszahrma/ai-agent-hub2, PR #11
**Reporter:** @guszahrma (via CodeReviewer agent)
**Severity:** Blocker

### Problem
The `_path(self, pr_number)` method builds filenames using only the PR number (e.g., `comment_state_5.json`). If two different repositories both have a PR #5, they will overwrite each other's state files.

### Fix
Incorporate `repo_ref` into the filename to namespace state files per repo:
```python
def _path(self, pr_number):
    safe_repo = self.repo_ref.replace('/', '_')
    return f"comment_state_{safe_repo}_{pr_number}.json"
```

### Status
- Confirmed blocker by CodeReviewer
- ScrumMaster acknowledged and delegated fix to code_editor agent


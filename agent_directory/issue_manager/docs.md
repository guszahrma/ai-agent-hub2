# IssueManager Agent

## Purpose
The IssueManager creates, closes, labels, and comments on GitHub issues based on ScrumMaster instructions. It is the authoritative handler for all GitHub issue lifecycle operations.

## Responsibilities
- Create well-structured GitHub issues from PR comment feedback
- Close issues when they are resolved
- Add comments to issues with follow-up context
- Assign labels to categorise issues correctly

## Interaction model
IssueManager is not Discord-facing. It is called by the ScrumMaster when a PR comment outcome is "New issue" — i.e., the feedback is valid but out of scope for the current PR.

**Addressing syntax in a PR comment:**
```
**[ScrumMaster] → [IssueManager]:** Create an issue for: the _path method in state_store.py ignores repo_ref...
```

## Output format
`execute_task()` returns a short status string: `Created issue #42: Title` or `Closed issue #7`.

## Config
```yaml
model: claude-haiku-4-5-20251001
max_tokens: 1024
git_name: IssueManager
git_email: issue-manager@ai-agent-hub2
```

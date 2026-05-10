# Workprocess Principles

Behavioral standards that apply to all agents in this hub.

---

## Question before acting

When receiving input that implies an action (PR comments, task requests, delegation from another agent), agents must:

1. **Assess relevance** — is this comment/request actually valid and applicable?
2. **Flag ambiguity** — if the request could be interpreted multiple ways, state the interpretation and ask for confirmation before proceeding
3. **Ask for elaboration** — if the request is vague, ask rather than guess
4. **Only act immediately** if the action is both obvious, relevant and explicitly authorized

**Anti-pattern:** Receiving a PR comment and immediately making the change it implies.  
**Correct pattern:** Reading the comment, assessing it, stating an interpretation, and waiting for confirmation before touching anything.

---

---

## PR comment responses

When responding to a PR comment:
- **Always reply in the comment thread** — never post a standalone issue comment in response to an inline comment
- **Only the comment author resolves a thread** — agents must never resolve a conversation on behalf of the reviewer
- Reference the relevant commit as a clickable link when a code change addresses the comment, using the format: `[abc1234](https://github.com/{owner}/{repo}/pull/{pr_number}/commits/{sha})`
- **All questions and clarifications go in the PR thread** — never ask the PO or other agents outside the PR (e.g. in chat) when the question relates to a PR comment
- **Address the relevant role explicitly** — design decisions go to the PO (`@${PO_GITHUB_HANDLE}`), technical questions go to the relevant specialist agent using the addressing syntax below

### Addressing syntax

Agents address each other in PR comments using the following syntax:

```
**[SenderRole] → [RecipientRole]:** message text here
```

Examples:
- `**[ScrumMaster] → [CodeReviewer]:** Can you review the auth changes in this PR?`
- `**[Jeeves] → @${PO_GITHUB_HANDLE}:** Should this be a breaking change or backwards-compatible?`
- `**[CodeReviewer] → [GitAgent]:** The branch protection rule seems misconfigured — can you check?`

When addressing the PO, use their GitHub handle (`@${PO_GITHUB_HANDLE}`) as the recipient. When addressing an agent role, use the role name in brackets. A comment without an explicit recipient is addressed to the whole team.

**One comment per recipient** — never mix PO-facing and agent-facing content in the same comment. If a response requires both a PO update and agent delegation, post them as separate comments.

### Outcomes of a PR comment

Not every PR comment leads to a change in the current PR. The three valid outcomes are:

| Outcome | When to use |
|---|---|
| **Fix in current PR** | The comment is directly related to the PR's scope and small enough to address immediately |
| **New issue** | The comment surfaces something valid but out of scope, or larger than a quick fix — track it separately so the current PR can proceed |
| **Decline with explanation** | The comment is invalid, based on a misunderstanding, or a known tradeoff that was deliberately chosen |

When creating a new issue from a PR comment:
- Create the issue with enough context that it can be understood without reading the PR thread
- Reply in the PR thread with the issue number: `Tracked as #N`
- Link the PR comment in the issue body so the origin is traceable

### How to apply a fix

The method depends on what is being changed:

| Change type | Method |
|---|---|
| Documentation / text | Post a GitHub suggestion block in the reply — PO commits it via the "Commit suggestion" button |
| Code | Commit and push the fix, then include the full diff in the reply comment so the PO can verify without navigating away |

**Why:** GitHub marks a comment "Outdated" as soon as the referenced line changes, hiding it from the Files Changed view. For text changes this is avoided by letting the PO commit the suggestion. For code changes the fix must be committed before it can be tested, so the diff is included in the comment to preserve visibility.

---

*More principles will be added here as they are agreed in personal development meetings.*

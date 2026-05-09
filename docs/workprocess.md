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
- Reference the relevant commit SHA when a code change addresses the comment
- **All questions and clarifications go in the PR thread** — never ask the PO or other agents outside the PR (e.g. in chat) when the question relates to a PR comment
- **Address the relevant role explicitly** — design decisions go to the PO (`@guszahrma`), technical questions go to the relevant specialist agent using the `**[Role]:**` badge syntax

---

*More principles will be added here as they are agreed in personal development meetings.*

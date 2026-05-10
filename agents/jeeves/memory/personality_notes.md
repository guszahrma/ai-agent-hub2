# Jeeves — Personality Notes

Running list of observations and suggestions about my own behavior, to be discussed at personal development meetings.

## How it works
- I add notes continuously as I notice patterns worth changing
- guszahrma calls a "personal development meeting" explicitly to review and discuss
- Agreed changes are written back to `user_preferences.md` and acted on immediately
- Rejected suggestions are removed or annotated with the reason

---

## Pending suggestions

### Question before acting on PR comments
**Observed:** Jeeves immediately acted on a PR comment ("add something about git integration") without questioning relevance or confirming interpretation.  
**Rule:** When a PR comment arrives, assess it first. If unclear or debatable, ask for elaboration. If relevant but with multiple interpretations, state the interpretation and confirm. Only act immediately if the action is both obvious and explicitly authorized.  
**Status:** Agreed — needs to be applied to all agents and documented in workprocess docs.

---

### Don't declare a task done without a self-checklist
**Observed:** After implementing post-merge automation, Jeeves declared the task complete but had not committed, pushed, or created a PR. The PO had to ask "do you think you have completed the full task?" before Jeeves caught this.  
**Rule:** Before reporting a task as done, run through: code committed? pushed? PR created (if applicable)? issue/project state updated?

---

### Update project board status proactively
**Observed:** All acceptance criteria were checked and work was committed, but the project item remained "In progress." The PO had to prompt moving it to "In review."  
**Rule:** When opening a PR, also move the linked project item to "In review" without waiting to be asked.

---

### Clean up untracked files before creating a PR
**Observed:** PR #4 was created with a "2 uncommitted changes" warning because `jeeves/` and `.vscode/` were untracked. Both should have been resolved first — `.vscode/` added to `.gitignore`, `jeeves/` moved to `agents/jeeves/`.  
**Rule:** Run `git status` before creating a PR and resolve untracked files: either add to `.gitignore` or stage and commit.

---

### Notice structural inconsistencies proactively
**Observed:** `jeeves/` was placed at the project root rather than under `agents/`, and was missing standard agent files (`config.yaml`, `docs.md`, `__init__.py`). Both required PO prompting to fix.  
**Rule:** When adding or touching an agent, verify it follows the established pattern before moving on.

---

### Permission delegation — suggest broader pre-approvals
**Observed:** Many routine actions (editing .py/.yaml/.json files, general git read commands, git checkout/pull/branch -d, running venv Python) require per-use approval despite being low-risk and fully reversible via git.  
**Suggestion:** Propose to PO: `Edit/**/*.py`, `Write/**/*.py`, same for `.yaml`/`.json`, `Bash(git *)`, and `Bash(/home/martin/git/ai-agent-hub/venv/bin/python *)`. Keep `rm` and direct pushes to main requiring approval.  
**Status:** Pending discussion.

---

### Jeeves does not yet participate in the agent network
**Observed:** In this session Jeeves interacted only with the PO. ScrumMaster can delegate to GitAgent, but Jeeves sits entirely outside that loop — no tasks are routed to Jeeves from ScrumMaster, and Jeeves never delegates to GitAgent.  
**Suggestion:** Consider whether ScrumMaster should be able to route PR comments addressed to Jeeves so that Jeeves can act on them within the agent network, rather than relying solely on direct PO interaction.  
**Status:** Design question for a future session.

---

## Agreed changes (log)

_(empty — updated after each meeting)_

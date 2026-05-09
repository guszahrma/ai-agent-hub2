# Task: Agent PR Workflow

**Status:** Todo  
**Priority:** Medium  
**Goal:** Define and implement the full PR lifecycle for agents — branching, sign-offs, and Scrum Master as PR coordinator. PO (Tinarm) does the final GitHub approve + merge.

---

## Design

### Branching
- Each agent works on its own branch: `agent/<role>/<short-description>`
- Branch is cut from the current feature branch, not directly from `main`
- Agent opens a PR when ready

### Role badges
All agents post under the single GitHub bot account but prefix every comment with their role:
```
**[CodeReviewer]:** LGTM ✅
**[ScrumMaster]:** @CodeReviewer please review auth changes.
```

### Sign-off flow
1. Agent opens PR
2. Scrum Master posts review requests to required roles (configurable per PR type)
3. Each required role posts `✅ LGTM` or `❌ Changes requested`
4. Scrum Master tracks sign-offs; when all done, posts: `**[ScrumMaster]:** All roles signed off. Ready for PO approval. @Tinarm`
5. PO (Tinarm) does final GitHub approve + merge

### Merge protection
- Merging to `main` always requires PO approval (enforced via GitHub branch protection rules)
- Scrum Master cannot merge to `main` autonomously

---

## Subtasks

### 1. Define required reviewers per PR type
**Status:** Todo  
E.g. docs-only PR → CodeReviewer. Code PR → CodeReviewer + GitAgent. Workflow PR → all roles.

### 2. Implement Scrum Master PR monitoring
**Status:** Todo  
Scrum Master polls or webhooks GitHub PR comments, tracks sign-offs per role, posts summary when complete.

### 3. Implement agent branch creation
**Status:** Todo  
Agents create branches following the `agent/<role>/<description>` convention via git_tools.

### 4. Set up GitHub branch protection on main
**Status:** Todo  
Require at least one human approval before merge to `main`.

### 5. Document in docs/workprocess.md
**Status:** Todo  
Add the full PR lifecycle as a section in the workprocess doc.

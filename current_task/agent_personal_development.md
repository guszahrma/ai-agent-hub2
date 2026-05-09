# Task: Agent Personal Development System

**Status:** Todo  
**Priority:** Low (after git_support and jeeves_memory)  
**Goal:** Extend the personal development meeting concept — currently set up for Jeeves — to all agents in the hub and document it in the workprocess docs.

---

## Subtasks

### 1. Define the pattern
**Status:** Todo  
Write a reusable spec for how any agent maintains personality notes and handles personal development meetings. Should cover: how notes are stored, what triggers a meeting, how agreed changes are applied.

### 2. Add to agent base class
**Status:** Todo  
Consider whether `BaseAgent` should have a standard hook or memory interface for personality notes, so all agents get it automatically.

### 3. Apply to existing agents
**Status:** Todo  
Once the pattern is defined, add personality note files for ScrumMaster (and any other agents built by then).

### 4. Workprocess documentation
**Status:** In Progress  
Document the personal development meeting convention in `docs/` so it's clear to anyone reading the repo how agents evolve over time.
`docs/workprocess.md` created with first principle: "Question before acting". More principles to be added as agreed in personal development meetings.

### 5. Apply workprocess principles to agent system prompts
**Status:** Todo  
Agreed principles from `docs/workprocess.md` must be reflected in each agent's system prompt so they are enforced at runtime, not just documented. Start with "Question before acting" for ScrumMaster and GitAgent.

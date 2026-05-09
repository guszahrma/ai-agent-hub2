# Task: Bot Trigger Mechanism

**Status:** Todo  
**Priority:** High (cost control — currently every message burns API credits)  
**Goal:** Make the bot respond selectively rather than on every message, to avoid unnecessary Anthropic API calls.

---

## Subtasks

### 1. Define trigger rules
**Status:** Todo  
Decide what triggers a response. Proposal:
- `@BotName` mention always triggers
- `!` commands always trigger
- All other messages are ignored

### 2. Implement in discord_bot.py
**Status:** Todo  
Add trigger check before calling `scrum_master.handle_message()`.

### 3. Update docs/discord_commands.md
**Status:** Todo  
Document the trigger rules clearly so users know how to interact with the bot.
